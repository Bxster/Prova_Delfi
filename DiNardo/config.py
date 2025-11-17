# config.py
"""
Configuration module: Defines constants and default parameters.
"""
import os
from datetime import datetime

# Audio parameters
SAMPLE_RATE_DEFAULT = 192000
WINDOW_SEC = 0.8
HALF_WINDOW = WINDOW_SEC / 2
CHANNELS = 1

# DSP parameters
IMG_WIDTH = 300
IMG_HEIGHT = 150
MIN_FREQ = 5000
MAX_FREQ = 25000
NFFT = 512
OVERLAP = 0.5

# Inference defaults
THRESHOLD_DEFAULT = 0.9

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DETECTIONS_DIR = os.path.join(BASE_DIR, 'detections')

# Logger format
TIMESTAMP_FMT = '%Y%m%d-%H%M%S.%f'
LOG_DATE_FMT = '%Y%m%d'
