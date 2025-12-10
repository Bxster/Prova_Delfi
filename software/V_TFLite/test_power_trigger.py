#!/home/delfi/Prova_Delfi/.venv/bin/python3
"""
CLI di test per PowerTrigger, TDOA e Detection TFLite.
Usa gli stessi parametri del config e accetta in input:
- un file WAV stereo (--stereo), oppure
- due file WAV mono (--left, --right).
Opzioni:
- --tdoa: esegue anche l'analisi TDOA per determinare la direzione del suono
- --detect: esegue anche la detection TFLite sul canale appropriato
Stampa il risultato del trigger per verifiche rapide da terminale.
"""
import argparse
import sys
import numpy as np
from scipy.io import wavfile

# Moduli progetto
from power_trigger import PowerTrigger, compute_tdoa_direct
from config import (
    PROMINENCE_BAND_MIN_HZ, PROMINENCE_BAND_MAX_HZ, PROMINENCE_THRESHOLD_DB,
    DETECTION_THRESHOLD
)


def to_float(x: np.ndarray) -> np.ndarray:
    if x.dtype == np.float32:
        return x
    if x.dtype == np.float64:
        return x.astype(np.float32)
    if x.dtype == np.int16:
        return (x.astype(np.float32) / 32768.0)
    if x.dtype == np.int32:
        return (x.astype(np.float32) / 2147483648.0)
    # fallback
    return x.astype(np.float32)


def load_inputs(args):
    if args.stereo:
        fs, data = wavfile.read(args.stereo)
        if data.ndim != 2 or data.shape[1] != 2:
            raise ValueError("Il file passato con --stereo deve essere stereo (2 canali)")
        left = to_float(data[:, 0])
        right = to_float(data[:, 1])
        return fs, left, right
    if args.left and args.right:
        fsL, left = wavfile.read(args.left)
        fsR, right = wavfile.read(args.right)
        if fsL != fsR:
            raise ValueError("I due WAV hanno sample rate differenti")
        if left.ndim == 2:
            left = left[:, 0]
        if right.ndim == 2:
            right = right[:, 0]
        left = to_float(left)
        right = to_float(right)
        n = min(len(left), len(right))
        return fsL, left[:n], right[:n]
    raise ValueError("Specificare --stereo <file> oppure --left <file> --right <file>")


def run_detection(signal, sample_rate):
    """
    Esegue detection TFLite direttamente (senza server).
    Importa le dipendenze solo se richiesto per evitare errori su macchine senza tflite.
    
    Returns:
        tuple: (score, spectrogram_image) oppure (None, None) se non disponibile
    """
    try:
        # Import lazy per evitare errori se tflite non è installato
        from scipy.signal import spectrogram
        from PIL import Image
        import cv2
        import tflite_runtime.interpreter as tf
        from config import MIN_FREQ, MAX_FREQ, IMG_WIDTH, IMG_HEIGHT, NFFT, OVERLAP, MODEL_PATH
    except ImportError as e:
        print(f"[WARN] Detection non disponibile: {e}")
        return None, None
    
    # Carica modello
    interpreter = tf.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    
    # DSP: waveform -> spectrogram -> image
    hop = int(NFFT * (1 - OVERLAP))
    freqs, times, Sxx = spectrogram(
        signal.astype(np.float32), fs=sample_rate, window='hann', nperseg=NFFT,
        noverlap=NFFT - hop, scaling='density', mode='magnitude'
    )
    Sxx = Sxx[: NFFT // 2, :]
    Sxx_db = 20 * np.log10(Sxx + 1e-12)
    
    # Crop frequenze
    idx_min = np.searchsorted(freqs, MIN_FREQ)
    idx_max = np.searchsorted(freqs, MAX_FREQ, side='right')
    block = Sxx_db[idx_min:idx_max]
    block = block - block.min()
    denom = block.max() if block.max() != 0 else 1.0
    block = block / denom
    img_arr = (255 * block)[::-1].astype(np.uint8)
    img = Image.fromarray(img_arr, mode='L').resize((IMG_WIDTH, IMG_HEIGHT), resample=Image.BILINEAR)
    
    # Applica filtro Sobel verticale (come nel training del modello)
    arr_sobel = np.array(img)
    sobel = cv2.Sobel(arr_sobel, cv2.CV_64F, 0, 1, ksize=7)
    sobel = cv2.normalize(sobel, None, 0, 255, cv2.NORM_MINMAX)
    img_sobel = Image.fromarray(sobel.astype(np.uint8), mode='L')
    
    # Prepara input
    input_details = interpreter.get_input_details()[0]
    _, h, w, c = input_details['shape']
    resized = img_sobel.resize((w, h), resample=Image.BILINEAR)
    arr = np.array(resized, dtype=np.float32) / 255.0
    if c == 1:
        arr = arr[:, :, None]
    elif c == 3:
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    arr = arr[None, ...].astype(np.float32)
    
    # Inference
    interpreter.set_tensor(input_details['index'], arr)
    interpreter.invoke()
    output_details = interpreter.get_output_details()
    yApp = interpreter.get_tensor(output_details[0]['index'])
    
    return float(np.squeeze(yApp)), img_sobel


def main():
    parser = argparse.ArgumentParser(description="Test PowerTrigger, TDOA e Detection da terminale")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--stereo", help="Percorso WAV stereo")
    g.add_argument("--left", help="Percorso WAV mono canale sinistro")
    parser.add_argument("--right", help="Percorso WAV mono canale destro (richiesto se usi --left)")
    parser.add_argument("--tdoa", action="store_true", help="Esegue anche l'analisi TDOA")
    parser.add_argument("--detect", action="store_true", help="Esegue anche la detection TFLite")
    args = parser.parse_args()

    fs, left, right = load_inputs(args)

    # Adatta band_max al Nyquist del file, se necessario
    nyq = fs / 2.0
    band_max_for_test = PROMINENCE_BAND_MAX_HZ
    if band_max_for_test >= nyq:
        band_max_for_test = max(PROMINENCE_BAND_MIN_HZ + 100.0, nyq - 100.0)

    trigger = PowerTrigger(
        sample_rate=fs,
        prominence_threshold_db=PROMINENCE_THRESHOLD_DB,
        band_min_hz=PROMINENCE_BAND_MIN_HZ,
        band_max_hz=band_max_for_test,
    )

    res = trigger.process_stereo_buffer(left, right)

    # Stampa risultato in modo compatto
    print("--- PowerTrigger Result ---")
    print(f"SampleRate: {fs} Hz | Durata: {len(left)/fs:.3f} s")
    print(f"Band: [{PROMINENCE_BAND_MIN_HZ}, {band_max_for_test}] Hz | Threshold: {PROMINENCE_THRESHOLD_DB} dB")
    print(f"Left  -> triggered={res['left_triggered']}, prom_db={res['left_info']['prominence_db']:.2f}, peak={res['left_info']['peak_freq']:.1f} Hz")
    print(f"Right -> triggered={res['right_triggered']}, prom_db={res['right_info']['prominence_db']:.2f}, peak={res['right_info']['peak_freq']:.1f} Hz")
    print(f"Action: {res['action']} | Channel: {res['channel_to_analyze']}")
    
    # Esegui TDOA se richiesto o se entrambi i trigger sono attivi
    direction = None
    if args.tdoa or res['action'] == 'tdoa':
        print("\n--- TDOA Analysis ---")
        tdoa_result = compute_tdoa_direct(left, right, fs)
        print(f"Success: {tdoa_result['success']}")
        print(f"Direction: {tdoa_result['direction']}")
        print(f"Angle: {tdoa_result['angle']}°")
        print(f"TDOA: {tdoa_result['tdoa_sec']*1e6:.2f} µs ({int(tdoa_result['tdoa_sec']*fs)} samples)")
        if tdoa_result['error']:
            print(f"Error: {tdoa_result['error']}")
        direction = tdoa_result['direction']
    
    # Esegui Detection se richiesto
    if args.detect:
        import os
        import time
        
        print("\n--- Detection TFLite ---")
        # Scegli canale in base a TDOA o trigger
        if direction in ['sinistra', 'left'] or res['action'] == 'left_only':
            channel_name = 'LEFT'
            signal = left
        elif direction in ['destra', 'right'] or res['action'] == 'right_only':
            channel_name = 'RIGHT'
            signal = right
        else:
            channel_name = 'LEFT (default)'
            signal = left
        
        print(f"Channel: {channel_name}")
        score, spectrogram_img = run_detection(signal, fs)
        if score is not None:
            print(f"Score: {score:.4f}")
            print(f"Threshold: {DETECTION_THRESHOLD}")
            detected = score >= DETECTION_THRESHOLD
            print(f"Result: {'✅ DETECTED' if detected else '❌ Not detected'}")
            
            # Salva spettrogramma sempre (indipendentemente dal risultato)
            if spectrogram_img is not None:
                test_dir = os.path.join(os.path.dirname(__file__), 'test')
                os.makedirs(test_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                result_tag = "OK" if detected else "NO"
                filename = f"spectrogram_{timestamp}_{result_tag}_score{score:.2f}.png"
                filepath = os.path.join(test_dir, filename)
                spectrogram_img.save(filepath)
                print(f"📁 Spettrogramma salvato: {filepath}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)
