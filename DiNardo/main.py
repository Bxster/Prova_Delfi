"""
Orchestrates audio capture, DSP, inference, and logging.
Allows specifying ALSA device by index or name.
"""
import argparse
import time
import sys
from config import *
from audio_capture import capture_stream, rolling_buffer
from dsp import make_spectrogram, spectrogram_to_image, apply_sobel_vertical
from inference import TFLiteModel
from logger import DetectionLogger


def parse_args():
    parser = argparse.ArgumentParser(description='Real-time spectrogram detection')
    parser.add_argument('model_path', help='Path to TFLite model')
    parser.add_argument('--num_threads', type=int, default=1)
    parser.add_argument('--sobel', choices=['y','n'], default='n')
    parser.add_argument('--samplerate', type=int, default=SAMPLE_RATE_DEFAULT)
    parser.add_argument('--threshold', type=float, default=THRESHOLD_DEFAULT)
    parser.add_argument('--device', help='ALSA input device (index or name)', default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    # Parse device argument
    device = None
    if args.device is not None:
        try:
            device = int(args.device)
        except ValueError:
            device = args.device

    model = TFLiteModel(args.model_path, args.num_threads)
    logger = DetectionLogger(args.threshold)

    # Setup audio capture
    blocks = capture_stream(samplerate=args.samplerate,
                            channels=CHANNELS,
                            device=device)
    sr = args.samplerate
    windows = rolling_buffer(blocks, samplerate=sr)

    print(f"Starting detection on device: {device} at {sr} Hz")
    try:
        for audio_win in windows:
            start_time = time.perf_counter()
            # DSP
            Sxx_db, freqs = make_spectrogram(audio_win, sr)
            img = spectrogram_to_image(Sxx_db, freqs)
            if args.sobel == 'y':
                img = apply_sobel_vertical(img)
            # Inference
            pred = model.predict(img)
            # Logging
            if pred >= args.threshold:
                logger.log(pred, img, audio_win, sr)
            # Semaphore
            elapsed = time.perf_counter() - start_time
            wait = HALF_WINDOW - elapsed
            if wait > 0:
                time.sleep(wait)
    except KeyboardInterrupt:
        print('Stopping...')
        sys.exit(0)

if __name__ == '__main__':
    main()

