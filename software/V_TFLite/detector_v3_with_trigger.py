#!/home/delfi/Prova_Delfi/.venv/bin/python3
"""
Detector V3 con Power Trigger Integration
Integra il power trigger nel flusso di detection esistente.
"""

import asyncio
from scipy.io import wavfile
from socket import *
import numpy as np
import logging
import time
import os
import sys
import json

# Importa il modulo power trigger
from power_trigger import PowerTrigger, compute_tdoa_direct, get_nearest_channel

from config import RING_HOST, RING_PORT, WINDOW_SEC, HALF_WINDOW, SERVER_PORT_BASE, DETECTION_THRESHOLD, DETECTION_MIN_THRESHOLD, DETECTIONS_BELOW_THRESHOLD_DIR, LOG_FILE_PATH, DETECTIONS_DIR, TDOA_WIN_SEC, WINDOW_SAVE_MODE, WINDOW_SAVES_DIR

# Funzione per ottenere il nome del file di log
def get_log_file_path():
    date_str = time.strftime("%Y-%m-%d_%H:%M:%S")
    log_file_path = LOG_FILE_PATH
    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w") as log_file:
            log_file.write("Detection Log Created on: {}\n\n".format(date_str))
    
    return log_file_path

log_file_path = get_log_file_path()


def save_detection_json(filepath_base: str, trigger_result: dict, tdoa_result: dict = None, score: float = None, detected: bool = False):
    """
    Salva un file JSON con i risultati della detection accanto al WAV.
    
    Args:
        filepath_base: Percorso base (senza estensione) per il file JSON
        trigger_result: Risultato del power trigger
        tdoa_result: Risultato TDOA (opzionale)
        score: Score della detection TFLite
        detected: True se la soglia è stata superata
    """
    # Determina direction e angle
    if tdoa_result:
        direction = tdoa_result.get('direction', None)
        angle_deg = tdoa_result.get('angle', None)
    elif trigger_result.get('action') == 'left_only':
        direction = "sinistra"
        angle_deg = -90.0
    elif trigger_result.get('action') == 'right_only':
        direction = "destra"
        angle_deg = 90.0
    else:
        direction = None
        angle_deg = None
    
    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "trigger": {
            "left": trigger_result.get('left_triggered', False),
            "right": trigger_result.get('right_triggered', False),
            "action": trigger_result.get('action', 'none')
        },
        "direction": direction,
        "angle_deg": angle_deg,
        "detected": detected,
        "score": round(score, 4) if score is not None else None
    }
    
    json_path = filepath_base + ".json"
    try:
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Error saving JSON: {e}\n")


def save_analysis_window(left_block, right_block, sample_rate, window_counter, trigger_result=None):
    """
    Salva una finestra di analisi come file WAV con metadati.
    
    Args:
        left_block: Array numpy del canale sinistro
        right_block: Array numpy del canale destro
        sample_rate: Sample rate in Hz
        window_counter: Contatore progressivo della finestra
        trigger_result: Risultato del trigger (opzionale, per metadata)
    """
    try:
        os.makedirs(WINDOW_SAVES_DIR, exist_ok=True)
        
        # Timestamp + counter per nome file univoco
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename_base = f"window_{timestamp}_{window_counter:06d}"
        filepath_base = os.path.join(WINDOW_SAVES_DIR, filename_base)
        
        # Converti float32 a int16 se necessario
        if left_block.dtype == np.float32:
            left_int16 = (left_block * 32767).astype(np.int16)
        else:
            left_int16 = left_block.astype(np.int16)
            
        if right_block.dtype == np.float32:
            right_int16 = (right_block * 32767).astype(np.int16)
        else:
            right_int16 = right_block.astype(np.int16)
        
        # Crea stereo array
        stereo_array = np.stack((left_int16, right_int16), axis=-1)
        
        # Salva WAV
        wavfile.write(filepath_base + ".wav", sample_rate, stereo_array)
        
        # Salva metadata JSON
        metadata = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "window_counter": window_counter,
            "duration_sec": len(left_block) / sample_rate,
            "sample_rate": sample_rate,
            "samples": len(left_block)
        }
        
        if trigger_result:
            metadata["trigger"] = {
                "left": trigger_result.get('left_triggered', False),
                "right": trigger_result.get('right_triggered', False),
                "action": trigger_result.get('action', 'none')
            }
        
        with open(filepath_base + ".json", 'w') as f:
            json.dump(metadata, f, indent=2)
            
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Error saving analysis window: {e}\n")


def get_sample():
    """Ottiene i campioni audio dai due canali."""
    size_of_float = 4
    
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((RING_HOST, RING_PORT))
        s.sendall(b"nframes")
        nframes = int(s.recv(256).decode("utf8").split("\n")[0])
        s.sendall(b"len")
        nblocks = int(s.recv(256).decode('utf8').split("\n")[0])
        s.sendall(b"rate")
        samplerate = int(s.recv(256).decode('utf8').split("\n")[0])
        s.sendall(b"seconds")
        blocksize = size_of_float * nframes * 2
        s.sendall(b"dump")
        
        for i in range(nblocks):
            if i == 0:
                data = s.recv(blocksize)
            else:
                data = data + s.recv(blocksize)
    
    myblock = np.frombuffer(data, dtype=np.float32)
    stereo_data = myblock.reshape(-1, 2)
    
    with open(log_file_path, "a") as log_file:
        log_file.write(f"LEN: {len(stereo_data)}\n")
    
    left_channel = stereo_data[:, 0]
    right_channel = stereo_data[:, 1]
    
    return samplerate, left_channel, right_channel


async def send_wavefile(num, wave, bitrate, result):
    """Invia il file audio al server per la detection."""
    global RING_HOST
    global SERVER_PORT_BASE
    
    try:
        data_size = wave.itemsize
        wave_content = wave.tobytes()
        port = SERVER_PORT_BASE + int(num)
        
        with open(log_file_path, "a") as log_file:
            log_file.write(f"CONNECTION PORT: {port}\n")
        
        file_size = len(wave_content)
        reader, writer = await asyncio.open_connection(RING_HOST, port)
        
        writer.write(f"{bitrate},{file_size},{data_size}".encode())
        await writer.drain()
        
        ack = await reader.read(3)
        if ack != b'ACK':
            print("Errore: ACK non ricevuto")
            writer.close()
            return
        
        writer.write(wave_content)
        await writer.drain()
        
        response = await reader.read()
        result[num] = response
        
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"ERRORE send_wavefile: {e}\n")


    


async def perform_detection_block(block, br):
    """
    Esegue la detection inviando un singolo blocco al task server.
    Ritorna la risposta grezza del server (bytes).
    """
    results = [None]
    await send_wavefile(0, block, br, results)
    return results[0]


async def main_loop_with_trigger():
    """
    Loop principale con power trigger integration.
    """
    try:
        # Inizializza il power trigger
        br, _, _ = get_sample()
        trigger = PowerTrigger(br, log_file_path=log_file_path)
        # Rolling tails (last HALF_WINDOW seconds) per canale per allineare hop=HALF_WINDOW
        prev_left_tail = np.array([], dtype=np.float32)
        prev_right_tail = np.array([], dtype=np.float32)
        
        # Contatore per le finestre salvate
        window_counter = 0
        
        with open(log_file_path, "a") as log_file:
            log_file.write("=== Starting detector with power trigger ===\n")
            log_file.write(f"Window save mode: {WINDOW_SAVE_MODE}\n")
        
        while True:
            br, left_channel, right_channel = get_sample()
            # Costruisce finestre rolling 0.8s con hop 0.4s usando le code precedenti
            w = int(br * WINDOW_SEC)
            h = int(br * HALF_WINDOW)
            # LEFT
            eff_left = left_channel if prev_left_tail.size == 0 else np.concatenate([prev_left_tail, left_channel])
            detect_left_block = eff_left[-w:] if eff_left.size >= w else eff_left
            prev_left_tail = eff_left[-h:] if eff_left.size >= h else eff_left
            # RIGHT
            eff_right = right_channel if prev_right_tail.size == 0 else np.concatenate([prev_right_tail, right_channel])
            detect_right_block = eff_right[-w:] if eff_right.size >= w else eff_right
            prev_right_tail = eff_right[-h:] if eff_right.size >= h else eff_right
            
            # Esegui il power trigger sulla stessa finestra usata per la detection (0.8s rolling)
            trigger_result = trigger.process_stereo_buffer(detect_left_block, detect_right_block)
            
            with open(log_file_path, "a") as log_file:
                log_file.write(f"\n--- Trigger Result ---\n")
                log_file.write(f"Action: {trigger_result['action']}\n")
                log_file.write(f"Channel to analyze: {trigger_result['channel_to_analyze']}\n")
            
            # Window saving logic based on configured mode
            should_save_window = False
            
            if WINDOW_SAVE_MODE == "all":
                # Save all analyzed windows
                should_save_window = True
            elif WINDOW_SAVE_MODE == "trigger" and trigger_result['action'] != 'none':
                # Save only windows that activate the trigger
                should_save_window = True
            
            if should_save_window:
                window_counter += 1
                save_analysis_window(
                    detect_left_block, 
                    detect_right_block, 
                    br, 
                    window_counter, 
                    trigger_result
                )
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"Saved analysis window #{window_counter} (mode: {WINDOW_SAVE_MODE})\n")
            
            # Determina quale canale analizzare
            if trigger_result['action'] == 'none':
                # Nessun trigger attivato, salta la detection
                with open(log_file_path, "a") as log_file:
                    log_file.write("No triggers activated, skipping detection\n")
                    log_file.write("Detection: N/A\n")  # Completa il log per consistenza
                # IMPORTANTE: Aspetta prima di continuare, altrimenti il loop gira troppo veloce
                # e riceve sempre gli stessi dati dal ring buffer
                await asyncio.sleep(HALF_WINDOW)  # Aspetta l'hop time prima di prendere il prossimo blocco
                continue
            
            if trigger_result['action'] == 'tdoa':
                # Entrambi i trigger attivati: esegui TDOA
                with open(log_file_path, "a") as log_file:
                    log_file.write("Performing TDOA analysis...\n")
                
                # Estrae finestra per TDOA (ultimi TDOA_WIN_SEC secondi)
                tdoa_win_sec = TDOA_WIN_SEC
                n_tdoa = max(1, int(br * tdoa_win_sec))
                lc = detect_left_block[-n_tdoa:] if detect_left_block.size > n_tdoa else detect_left_block
                rc = detect_right_block[-n_tdoa:] if detect_right_block.size > n_tdoa else detect_right_block
                
                # Esegui TDOA direttamente sui buffer (no subprocess)
                tdoa_result = compute_tdoa_direct(lc, rc, br)
                
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"TDOA Result: {tdoa_result}\n")
                
                if tdoa_result['success']:
                    # Ottieni il canale più vicino
                    nearest_channel = get_nearest_channel(
                        left_channel, right_channel, tdoa_result['direction']
                    )
                    
                    # Esegui la detection sul canale più vicino usando la finestra rolling
                    if tdoa_result['direction'].lower() in ['sinistra', 'left']:
                        resp = await perform_detection_block(detect_left_block, br)
                    else:
                        resp = await perform_detection_block(detect_right_block, br)

                    # Applica la soglia su un unico score
                    if resp is not None:
                        try:
                            detection = float(resp.decode().strip())
                            with open(log_file_path, "a") as log_file:
                                log_file.write(f"Detection: {detection:.2f}\n")
                            if detection >= DETECTION_THRESHOLD:
                                # Above threshold - positive detection
                                os.makedirs(DETECTIONS_DIR, exist_ok=True)
                                filepath_base = os.path.join(DETECTIONS_DIR, time.strftime("%Y-%m-%d_%H-%M-%S"))
                                wavfile.write(filepath_base + ".wav", br, np.stack((left_channel, right_channel), axis=-1))
                                save_detection_json(filepath_base, trigger_result, tdoa_result, detection, True)
                            elif detection >= DETECTION_MIN_THRESHOLD:
                                # Below threshold but above minimum - save for analysis
                                os.makedirs(DETECTIONS_BELOW_THRESHOLD_DIR, exist_ok=True)
                                filepath_base = os.path.join(DETECTIONS_BELOW_THRESHOLD_DIR, time.strftime("%Y-%m-%d_%H-%M-%S"))
                                wavfile.write(filepath_base + ".wav", br, np.stack((left_channel, right_channel), axis=-1))
                                save_detection_json(filepath_base, trigger_result, tdoa_result, detection, False)
                                with open(log_file_path, "a") as log_file:
                                    log_file.write(f"Saved below-threshold detection (score: {detection:.2f})\n")
                        except Exception as e:
                            with open(log_file_path, "a") as log_file:
                                log_file.write(f"Error parsing detection result: {e}\n")
                else:
                    with open(log_file_path, "a") as log_file:
                        log_file.write("TDOA analysis failed\n")
            
            elif trigger_result['action'] == 'left_only':
                # Solo il trigger sinistro attivato
                with open(log_file_path, "a") as log_file:
                    log_file.write("Left trigger only, detecting on left channel\n")
                    log_file.write("TDOA Result: N/A (single channel trigger)\n")
                
                resp = await perform_detection_block(detect_left_block, br)
                if resp is not None:
                    try:
                        detection = float(resp.decode().strip())
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Detection: {detection:.2f}\n")
                        if detection >= DETECTION_THRESHOLD:
                            # Above threshold - positive detection
                            os.makedirs(DETECTIONS_DIR, exist_ok=True)
                            filepath_base = os.path.join(DETECTIONS_DIR, time.strftime("%Y-%m-%d_%H-%M-%S"))
                            wavfile.write(filepath_base + ".wav", br, np.stack((left_channel, right_channel), axis=-1))
                            save_detection_json(filepath_base, trigger_result, None, detection, True)
                        elif detection >= DETECTION_MIN_THRESHOLD:
                            # Below threshold but above minimum - save for analysis
                            os.makedirs(DETECTIONS_BELOW_THRESHOLD_DIR, exist_ok=True)
                            filepath_base = os.path.join(DETECTIONS_BELOW_THRESHOLD_DIR, time.strftime("%Y-%m-%d_%H-%M-%S"))
                            wavfile.write(filepath_base + ".wav", br, np.stack((left_channel, right_channel), axis=-1))
                            save_detection_json(filepath_base, trigger_result, None, detection, False)
                            with open(log_file_path, "a") as log_file:
                                log_file.write(f"Saved below-threshold detection (score: {detection:.2f})\n")
                    except Exception as e:
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Error parsing detection result: {e}\n")
                else:
                    with open(log_file_path, "a") as log_file:
                        log_file.write("Detection: ERROR (no response from server)\n")
            
            elif trigger_result['action'] == 'right_only':
                # Solo il trigger destro attivato
                with open(log_file_path, "a") as log_file:
                    log_file.write("Right trigger only, detecting on right channel\n")
                    log_file.write("TDOA Result: N/A (single channel trigger)\n")
                
                resp = await perform_detection_block(detect_right_block, br)
                if resp is not None:
                    try:
                        detection = float(resp.decode().strip())
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Detection: {detection:.2f}\n")
                        if detection >= DETECTION_THRESHOLD:
                            # Above threshold - positive detection
                            os.makedirs(DETECTIONS_DIR, exist_ok=True)
                            filepath_base = os.path.join(DETECTIONS_DIR, time.strftime("%Y-%m-%d_%H-%M-%S"))
                            wavfile.write(filepath_base + ".wav", br, np.stack((left_channel, right_channel), axis=-1))
                            save_detection_json(filepath_base, trigger_result, None, detection, True)
                        elif detection >= DETECTION_MIN_THRESHOLD:
                            # Below threshold but above minimum - save for analysis
                            os.makedirs(DETECTIONS_BELOW_THRESHOLD_DIR, exist_ok=True)
                            filepath_base = os.path.join(DETECTIONS_BELOW_THRESHOLD_DIR, time.strftime("%Y-%m-%d_%H-%M-%S"))
                            wavfile.write(filepath_base + ".wav", br, np.stack((left_channel, right_channel), axis=-1))
                            save_detection_json(filepath_base, trigger_result, None, detection, False)
                            with open(log_file_path, "a") as log_file:
                                log_file.write(f"Saved below-threshold detection (score: {detection:.2f})\n")
                    except Exception as e:
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Error parsing detection result: {e}\n")
                else:
                    with open(log_file_path, "a") as log_file:
                        log_file.write("Detection: ERROR (no response from server)\n")
            
            # IMPORTANTE: Aspetta l'hop time prima di processare la prossima finestra
            # Questo garantisce che processiamo esattamente ogni 0.4s (hop time)
            # senza questo sleep, il loop girerebbe troppo veloce e processerebbe
            # gli stessi dati più volte o salterebbe finestre
            await asyncio.sleep(HALF_WINDOW)
    
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Exception in main_loop_with_trigger: {e}\n")


if __name__ == "__main__":
    try:
        format = "%(asctime)s:%(msecs)03s  %(message)s"
        logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
        asyncio.run(main_loop_with_trigger())
    except KeyboardInterrupt:
        with open(log_file_path, "a") as log_file:
            log_file.write("Program interrupted by user\n")
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Fatal error: {e}\n")
