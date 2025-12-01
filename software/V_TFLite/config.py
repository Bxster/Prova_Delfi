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
DIREZIONE_SCRIPT = f"{APP_DIR}/V_TFLite/direzione.py"

# Logs and detections
LOG_FILE_PATH = f"{LOGS_DIR}/detection_log.txt"
DETECTIONS_DIR = f"{LOGS_DIR}/Detections"

# --- Power Trigger ---
PROMINENCE_BAND_MIN_HZ = 4000
PROMINENCE_BAND_MAX_HZ = 26000
PROMINENCE_THRESHOLD_DB = 20.0

# --- TDOA / Direction ---
TDOA_TIMEOUT_SEC = 10
SPEED_OF_SOUND = 1460 # Velocità del suono in aria 330, in acqua 1460 (m/s)
MICROPHONE_DISTANCE = 0.46 # Distanza tra i microfoni (metri)
HIGH_PASS_CUTOFF_HZ = 1000
UART_PORT = "/dev/serial0"
UART_BAUD = 9600
ENABLE_UART = True # altrimenti False

# --- Networking / IPC ---
RING_HOST = "127.0.0.1"
RING_PORT = 8888
SERVER_PORT_BASE = 12001
# SERVER_PORTS = [12001, 12002, 12003]

# --- Detection threshold (current pipeline) ---
DETECTION_THRESHOLD = 0.7

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
