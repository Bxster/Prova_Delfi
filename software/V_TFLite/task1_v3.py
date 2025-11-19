#!/usr/bin/python3
import asyncio
import numpy as np
from scipy.signal import spectrogram
from PIL import Image
import tflite_runtime.interpreter as tf  # Utilizziamo TensorFlow Lite al posto di Keras
from config import MIN_FREQ, MAX_FREQ, IMG_WIDTH, IMG_HEIGHT, NFFT, OVERLAP

serverPort = 12001

"""
Task server: riceve un blocco mono, esegue DSP+TFLite e ritorna uno score.
"""

# Carichiamo il modello TensorFlow Lite
interpreter = tf.Interpreter(model_path='/home/pi/V_TFLite/model.tflite')
interpreter.allocate_tensors()

def compute(wave, br):
    # === DSP + Imaging (DiNardo-style) ===
    img = waveform_to_image(wave.astype(np.float32), br)
    # === Prepara tensore input per TFLite ===
    x = _prepare_input(img)
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    interpreter.set_tensor(input_details[0]['index'], x)
    interpreter.invoke()
    yApp_lite = interpreter.get_tensor(output_details[0]['index'])
    return yApp_lite

# ===== Inline helpers from former dinardo_adapter =====
def make_spectrogram(signal, sr, nfft=NFFT, overlap=OVERLAP):
    hop = int(nfft * (1 - overlap))
    freqs, times, Sxx = spectrogram(
        signal, fs=sr, window='hann', nperseg=nfft,
        noverlap=nfft - hop, scaling='density', mode='magnitude'
    )
    Sxx = Sxx[: nfft // 2, :]
    Sxx_db = 20 * np.log10(Sxx + 1e-12)
    return Sxx_db, freqs

def spectrogram_to_image(Sxx_db, freqs, min_f=MIN_FREQ, max_f=MAX_FREQ, w=IMG_WIDTH, h=IMG_HEIGHT):
    idx_min = np.searchsorted(freqs, min_f)
    idx_max = np.searchsorted(freqs, max_f, side='right')
    block = Sxx_db[idx_min:idx_max]
    block = block - block.min()
    denom = block.max() if block.max() != 0 else 1.0
    block = block / denom
    img_arr = (255 * block)[::-1].astype(np.uint8)  # flip Y
    img = Image.fromarray(img_arr, mode='L')
    return img.resize((w, h), resample=Image.BILINEAR)

def waveform_to_image(signal, sr, nfft=NFFT, overlap=OVERLAP, min_f=MIN_FREQ, max_f=MAX_FREQ, w=IMG_WIDTH, h=IMG_HEIGHT):
    Sxx_db, freqs = make_spectrogram(signal, sr, nfft=nfft, overlap=overlap)
    return spectrogram_to_image(Sxx_db, freqs, min_f=min_f, max_f=max_f, w=w, h=h)

def _prepare_input(image: Image.Image):
    input_details = interpreter.get_input_details()[0]
    _, h, w, c = input_details['shape']
    if image.mode != 'L':
        image = image.convert('L')
    resized = image.resize((w, h), resample=Image.BILINEAR)
    arr = np.array(resized, dtype=np.float32)
    if arr.max() > 1.0:
        arr = arr / 255.0
    if c == 1:
        arr = arr[:, :, None]
    elif c == 3 and resized.mode != 'RGB':
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    arr = arr[None, ...].astype(np.float32)
    return arr

async def handle_client(reader, writer):
    data = await reader.read(1024)
    message = data.decode()
    addr = writer.get_extra_info('peername')
    print(f"Received {message} from {addr}")

    # Dividi il messaggio per ottenere bitrate e dimensione
    bitrate, file_size, data_size = map(int, message.split(','))

    # Invia ACK al client
    writer.write(b'ACK')
    await writer.drain()

    received_data = bytearray()

    # Leggi i dati del file audio
    while len(received_data) < file_size:
        chunk = await reader.read(file_size - len(received_data))
        received_data.extend(chunk)
    if data_size == 2:
        received_data = np.frombuffer(received_data, dtype=np.int16)
    else:
        received_data = np.frombuffer(received_data, dtype=np.float32)

    yApp_lite = compute(received_data, bitrate)
    score = float(np.squeeze(yApp_lite))
    writer.write(f"{score}\n".encode())

    # Chiudi la connessione
    writer.close()

async def main():
    server = await asyncio.start_server(
        handle_client, '127.0.0.1', serverPort)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

asyncio.run(main())
