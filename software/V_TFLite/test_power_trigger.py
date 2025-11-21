#!/usr/bin/python3
"""
CLI di test per PowerTrigger.
Usa gli stessi parametri del config e accetta in input:
- un file WAV stereo (--stereo), oppure
- due file WAV mono (--left, --right).
Stampa il risultato del trigger per verifiche rapide da terminale.
"""
import argparse
import os
import sys
import numpy as np
from scipy.io import wavfile

# Moduli progetto
from power_trigger import PowerTrigger
from config import (PROMINENCE_BAND_MIN_HZ, PROMINENCE_BAND_MAX_HZ, PROMINENCE_THRESHOLD_DB)

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


def main():
    parser = argparse.ArgumentParser(description="Test PowerTrigger da terminale")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--stereo", help="Percorso WAV stereo")
    g.add_argument("--left", help="Percorso WAV mono canale sinistro")
    parser.add_argument("--right", help="Percorso WAV mono canale destro (richiesto se usi --left)")
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
    print(f"SampleRate: {fs} Hz")
    print(f"Band: [{PROMINENCE_BAND_MIN_HZ}, {band_max_for_test}] Hz | Threshold: {PROMINENCE_THRESHOLD_DB} dB")
    print(f"Left  -> triggered={res['left_triggered']}, prom_db={res['left_info']['prominence_db']:.2f}, peak={res['left_info']['peak_freq']:.1f} Hz")
    print(f"Right -> triggered={res['right_triggered']}, prom_db={res['right_info']['prominence_db']:.2f}, peak={res['right_info']['peak_freq']:.1f} Hz")
    print(f"Action: {res['action']} | Channel: {res['channel_to_analyze']}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)
