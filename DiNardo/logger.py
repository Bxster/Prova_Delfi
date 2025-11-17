"""
Detection logger: filesystem operations and timestamped logging.
"""
import os
from datetime import datetime
from config import DETECTIONS_DIR, TIMESTAMP_FMT, LOG_DATE_FMT
import numpy as np

class DetectionLogger:
    def __init__(self, threshold):
        self.threshold = threshold

    def log(self, prediction, image, audio_block, sr):
        now = datetime.now()
        date_str = now.strftime(LOG_DATE_FMT)
        ts_str = now.strftime(TIMESTAMP_FMT)[:-3]  # centiseconds
        base = os.path.join(DETECTIONS_DIR, date_str)
        data_dir = os.path.join(base, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # append to log
        log_path = os.path.join(base, 'detections.log')
        with open(log_path, 'a') as f:
            f.write(f"{ts_str}\t{prediction:.3f}\n")

        # save image and audio
        img_path = os.path.join(data_dir, f"{ts_str}.png")
        wav_path = os.path.join(data_dir, f"{ts_str}.wav")
        image.save(img_path)
        # write WAV
        from scipy.io.wavfile import write
        write(wav_path, sr, (audio_block * np.iinfo(np.int16).max).astype(np.int16))

