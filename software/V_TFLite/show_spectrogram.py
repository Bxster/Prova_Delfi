#!/usr/bin/env python3
"""
Mostra lo spettrogramma di un file WAV usando la stessa pipeline di detection.
"""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
from PIL import Image
import cv2
import matplotlib.pyplot as plt

from config import MIN_FREQ, MAX_FREQ, IMG_WIDTH, IMG_HEIGHT, NFFT, OVERLAP


def make_spectrogram(signal, sr, nfft, overlap):
    """Spectrogram: waveform -> dB spectrogram."""
    hop = int(nfft * (1 - overlap))
    freqs, times, Sxx = spectrogram(signal, fs=sr,
                                    window='hann', nperseg=nfft,
                                    noverlap=nfft-hop, scaling='density',
                                    mode='magnitude')
    Sxx = Sxx[:nfft//2, :]
    return 20*np.log10(Sxx + 1e-12), freqs


def spectrogram_to_image(Sxx_db, freqs, min_f, max_f, w, h):
    """To grayscale PIL Image."""
    idx_min = np.searchsorted(freqs, min_f)
    idx_max = np.searchsorted(freqs, max_f, side='right')
    block = Sxx_db[idx_min:idx_max]
    block -= block.min()
    block /= block.max()
    img_arr = (255 * block)[::-1].astype(np.uint8)  # flip Y
    img = Image.fromarray(img_arr, mode='L')
    return img.resize((w, h), resample=Image.BILINEAR)


def apply_sobel_vertical(image):
    """Sobel filter (vertical)."""
    arr = np.array(image)
    sobel = cv2.Sobel(arr, cv2.CV_64F, 0, 1, ksize=7)
    sobel = cv2.normalize(sobel, None, 0, 255, cv2.NORM_MINMAX)
    return Image.fromarray(sobel.astype(np.uint8), mode='L')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python show_spectrogram.py <file.wav>")
        sys.exit(1)
    
    wav_file = sys.argv[1]
    
    # Carica WAV
    sr, data = wavfile.read(wav_file)
    
    # Se stereo, prendi media
    if data.ndim == 2:
        signal = data.mean(axis=1)
    else:
        signal = data
    
    # Normalizza
    signal = signal.astype(np.float32)
    
    # Pipeline identica a test_power_trigger
    Sxx_db, freqs = make_spectrogram(signal, sr, NFFT, OVERLAP)
    img = spectrogram_to_image(Sxx_db, freqs, MIN_FREQ, MAX_FREQ, IMG_WIDTH, IMG_HEIGHT)
    img_sobel = apply_sobel_vertical(img)
    
    # Mostra
    plt.figure(figsize=(10, 6))
    plt.imshow(img_sobel, cmap='gray', aspect='auto')
    plt.title(f'{wav_file} - Spettrogramma con Sobel')
    plt.xlabel('Tempo')
    plt.ylabel('Frequenza')
    plt.tight_layout()
    plt.show()
