# Centralized configuration for V_TFLite (no imports in code yet)

# --- Paths (Raspberry Pi defaults) ---
PROJECT_ROOT = "/home/delfi/Prova_Delfi"
# Two-folder layout
APP_DIR = f"{PROJECT_ROOT}/software"
LOGS_DIR = f"{PROJECT_ROOT}/logs"

# Backward-compatible aliases (if some code still references old names)
V_TFLITE_DIR = APP_DIR
# DATA_DIR previously pointed to /home/pi/data; now logs live under PROJECT_ROOT/logs
DATA_DIR = LOGS_DIR

# Model and scripts
MODEL_PATH = f"{APP_DIR}/V_TFLite/model_6_ott.tflite"

# Logs and detections
LOG_FILE_PATH = f"{LOGS_DIR}/detection_log.txt"
DETECTIONS_DIR = f"{LOGS_DIR}/Detections"

# --- Power Trigger ---
PROMINENCE_BAND_MIN_HZ = 4000
PROMINENCE_BAND_MAX_HZ = 26000
PROMINENCE_THRESHOLD_DB = 20.0

# --- TDOA / Direction ---
TDOA_TIMEOUT_SEC = 10
TDOA_WIN_SEC = 0.04
SPEED_OF_SOUND = 1460  # Velocità del suono in aria 330, in acqua 1460 (m/s)
MICROPHONE_DISTANCE = 0.33  # Distanza tra i microfoni (metri)
HIGH_PASS_CUTOFF_HZ = 1000
INVERT_PHASE = False  # True se i microfoni hanno fase invertita
#TDOA_CENTER_THRESHOLD_SEC = 0.000061  # Soglia per considerare il suono "al centro" (~3 gradi in aria)
TDOA_CENTER_THRESHOLD_SEC = 0.000014  # (~3 gradi in acqua)
UART_PORT = "/dev/serial0"
UART_BAUD = 9600
ENABLE_UART = False  # altrimenti False

# --- Networking / IPC ---
RING_HOST = "127.0.0.1"
RING_PORT = 8888
SERVER_PORT_BASE = 12001
# SERVER_PORTS = [12001, 12002, 12003]

# --- Detection threshold (current pipeline) ---
DETECTION_THRESHOLD = 0.7  # Threshold for "positive" detection
DETECTION_MIN_THRESHOLD = 0.3  # Minimum score to save (for analysis of false negatives)
DETECTIONS_BELOW_THRESHOLD_DIR = f"{LOGS_DIR}/Detections_below_threshold"  # Low-score detections for analysis

# --- DiNardo-aligned DSP / windowing (for future integration) ---
SAMPLE_RATE_DEFAULT = 192000
WINDOW_SEC = 0.8
HALF_WINDOW = WINDOW_SEC / 2
IMG_WIDTH = 300
IMG_HEIGHT = 150
MIN_FREQ = 5000
MAX_FREQ = 25000
NFFT = 512
OVERLAP = 0.5
# THRESHOLD_DEFAULT = 0.9

# --- Logger formats (DiNardo style) ---
TIMESTAMP_FMT = "%Y%m%d-%H%M%S.%f"
LOG_DATE_FMT = "%Y%m%d"

# --- Continuous Recording ---
CONTINUOUS_RECORDING_ENABLED = True  # Set to False to disable continuous recording
CONTINUOUS_RECORDING_DIR = f"{LOGS_DIR}/continuous_recordings"

# --- Window Saving (Debug/Analysis) ---
# Modes: "none" (default), "all" (save all analyzed windows), "trigger" (save only triggered windows)
WINDOW_SAVE_MODE = "all"  # Options: "none", "all", "trigger"
WINDOW_SAVES_DIR = f"{LOGS_DIR}/window_saves"  # Directory for saved analysis windows