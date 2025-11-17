"""
Audio capture using sounddevice with selectable ALSA device; implements rolling buffer.
"""
import numpy as np
import sounddevice as sd
from config import SAMPLE_RATE_DEFAULT, CHANNELS, WINDOW_SEC, HALF_WINDOW


def capture_stream(samplerate=SAMPLE_RATE_DEFAULT,
                   channels=CHANNELS,
                   device=None):
    """
    Opens an ALSA InputStream once and yields blocks of size HALF_WINDOW (seconds).
    Supports selecting device by index or name.
    """
    # Apply device selection globally for input
    if device is not None:
        sd.default.device = (device, None)

    block_size = int(HALF_WINDOW * samplerate)
    # Use RawInputStream to avoid extra buffering
    stream = sd.RawInputStream(samplerate=samplerate,
                                channels=channels,
                                dtype='float32',
                                blocksize=block_size)
    stream.start()
    try:
        while True:
            data, overflowed = stream.read(block_size)
            if overflowed:
                # Handle overflow if needed
                pass
            # data is bytes: convert to numpy array
            arr = np.frombuffer(data, dtype=np.float32)
            yield arr
    finally:
        stream.stop()
        stream.close()


def rolling_buffer(blocks, samplerate):
    """
    Yields windows of size WINDOW_SEC, sliding by HALF_WINDOW.
    """
    buf_size = int(WINDOW_SEC * samplerate)
    half = int(HALF_WINDOW * samplerate)
    buf = np.zeros(buf_size, dtype=np.float32)
    filled = 0

    for blk in blocks:
        if filled < buf_size:
            to_copy = min(len(blk), buf_size - filled)
            buf[filled:filled+to_copy] = blk[:to_copy]
            filled += to_copy
            if filled < buf_size:
                continue
        else:
            buf[:-half] = buf[half:]
            buf[-half:] = blk[:half]
        yield buf.copy()

