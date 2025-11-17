"""
Digital signal processing: spectrogram, image conversion, Sobel.
"""
import numpy as np
from scipy.signal import spectrogram
from PIL import Image
import cv2
from config import IMG_WIDTH, IMG_HEIGHT, MIN_FREQ, MAX_FREQ, NFFT, OVERLAP

# Spectrogram
def make_spectrogram(signal, sr, nfft=NFFT, overlap=OVERLAP):
    hop = int(nfft * (1 - overlap))
    freqs, times, Sxx = spectrogram(signal, fs=sr,
                                    window='hann', nperseg=nfft,
                                    noverlap=nfft-hop, scaling='density',
                                    mode='magnitude')
    Sxx = Sxx[:nfft//2, :]
    return 20*np.log10(Sxx + 1e-12), freqs

# To grayscale PIL Image
def spectrogram_to_image(Sxx_db, freqs, min_f=MIN_FREQ,
                         max_f=MAX_FREQ, w=IMG_WIDTH, h=IMG_HEIGHT):
    idx_min = np.searchsorted(freqs, min_f)
    idx_max = np.searchsorted(freqs, max_f, side='right')
    block = Sxx_db[idx_min:idx_max]
    block -= block.min(); block /= block.max()
    img_arr = (255 * block)[::-1].astype(np.uint8)  # flip Y
    img = Image.fromarray(img_arr, mode='L')
    return img.resize((w, h), resample=Image.BILINEAR)

# Sobel filter (vertical)
def apply_sobel_vertical(image):
    arr = np.array(image)
    sobel = cv2.Sobel(arr, cv2.CV_64F, 0, 1, ksize=7)
    sobel = cv2.normalize(sobel, None, 0, 255, cv2.NORM_MINMAX)
    return Image.fromarray(sobel.astype(np.uint8), mode='L')

