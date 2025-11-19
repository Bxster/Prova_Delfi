# Centralized configuration for V_TFLite (no imports in code yet)

# --- Paths (Raspberry Pi defaults) ---
PROJECT_ROOT = "/home/pi/Prova_Delfi"
V_TFLITE_DIR = "/home/pi/V_TFLite"
DATA_DIR = "/home/pi/data"
MODEL_PATH = f"{V_TFLITE_DIR}/model.tflite"
LOG_FILE_PATH = f"{DATA_DIR}/detection_log.txt"
DETECTIONS_DIR = f"{DATA_DIR}/Detections"
DIREZIONE_SCRIPT = f"{PROJECT_ROOT}/software/V_TFLite/direzione.py"

# --- Power Trigger ---
PROMINENCE_BAND_MIN_HZ = 3000
PROMINENCE_BAND_MAX_HZ = 25000
PROMINENCE_THRESHOLD_DB = 12.0

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
DETECTION_THRESHOLD = 0.5

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
THRESHOLD_DEFAULT = 0.9

# --- Logger formats (DiNardo style) ---
TIMESTAMP_FMT = "%Y%m%d-%H%M%S.%f"
LOG_DATE_FMT = "%Y%m%d"
