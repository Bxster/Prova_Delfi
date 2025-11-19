import numpy as np
from PIL import Image
from scipy.signal import spectrogram
try:  # Prefer package-relative import when available
    from . import config  # type: ignore
except Exception:  # Fallback for script/module execution in folder
    import config  # type: ignore

# Try to import TFLite interpreter
_tflite_interpreter = None

def _load_interpreter(model_path: str):
    global _tflite_interpreter
    if _tflite_interpreter is not None:
        return _tflite_interpreter
    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        # Fallback to TensorFlow if available
        try:
            import tensorflow as tf  # type: ignore
            tflite = tf.lite  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("No TFLite runtime available. Install tflite-runtime on RPi.") from e
    _tflite_interpreter = tflite.Interpreter(model_path=model_path)
    _tflite_interpreter.allocate_tensors()
    return _tflite_interpreter


def make_spectrogram(signal: np.ndarray, sr: int, nfft=NFFT, overlap=OVERLAP):
    """Compute log-magnitude spectrogram (in dB) and return (Sxx_db, freqs)."""
    hop = int(nfft * (1 - overlap))
    freqs, times, Sxx = spectrogram(
        signal,
        fs=sr,
        window="hann",
        nperseg=nfft,
        noverlap=nfft - hop,
        scaling="density",
        mode="magnitude",
    )
    Sxx = Sxx[: nfft // 2, :]
    Sxx_db = 20 * np.log10(Sxx + 1e-12)
    return Sxx_db, freqs


def spectrogram_to_image(
    Sxx_db: np.ndarray,
    freqs: np.ndarray,
    min_f: float = MIN_FREQ,
    max_f: float = MAX_FREQ,
    w: int = IMG_WIDTH,
    h: int = IMG_HEIGHT,
):
    """Convert spectrogram block to grayscale PIL image with cropping and resize."""
    idx_min = np.searchsorted(freqs, min_f)
    idx_max = np.searchsorted(freqs, max_f, side="right")
    block = Sxx_db[idx_min:idx_max]
    block = block - block.min()
    denom = block.max() if block.max() != 0 else 1.0
    block = block / denom
    img_arr = (255 * block)[::-1].astype(np.uint8)  # flip Y
    img = Image.fromarray(img_arr, mode="L")
    return img.resize((w, h), resample=Image.BILINEAR)


def waveform_to_image(signal: np.ndarray, sr: int,
                      nfft: int = NFFT, overlap: float = OVERLAP,
                      min_f: float = MIN_FREQ, max_f: float = MAX_FREQ,
                      w: int = IMG_WIDTH, h: int = IMG_HEIGHT) -> Image.Image:
    Sxx_db, freqs = make_spectrogram(signal, sr, nfft=nfft, overlap=overlap)
    return spectrogram_to_image(Sxx_db, freqs, min_f=min_f, max_f=max_f, w=w, h=h)

def _prepare_input(image: Image.Image, interpreter) -> np.ndarray:
    input_details = interpreter.get_input_details()[0]
    # Expected shape typically (1, H, W, C)
    _, h, w, c = input_details["shape"]
    # Ensure grayscale
    if image.mode != "L":
        image = image.convert("L")
    # Resize to model expected spatial dims
    resized = image.resize((w, h), resample=Image.BILINEAR)
    arr = np.array(resized, dtype=np.float32)
    # Normalize to [0,1]
    if arr.max() > 1.0:
        arr = arr / 255.0
    # Add channel dim if needed
    if c == 1:
        arr = arr[:, :, None]
    elif c == 3 and resized.mode != "RGB":
        # replicate grayscale into 3 channels if model expects RGB
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    arr = arr[None, ...].astype(np.float32)
    return arr


def score_from_mono(signal: np.ndarray, sr: int) -> float:
    """
    Compute model score from a mono waveform using DiNardo DSP pipeline.
    - Builds spectrogram (Sxx_db, freqs)
    - Converts to grayscale image (IMG_WIDTH x IMG_HEIGHT)
    - Resizes to model input and runs TFLite inference
    Returns a single float score.
    """
    interpreter = _load_interpreter(MODEL_PATH)
    img = waveform_to_image(signal, sr)
    x = _prepare_input(img, interpreter)
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]
    interpreter.set_tensor(input_details["index"], x)
    interpreter.invoke()
    out = interpreter.get_tensor(output_details["index"])
    try:
        return float(np.squeeze(out))
    except Exception:
        return float(out.ravel()[0])
