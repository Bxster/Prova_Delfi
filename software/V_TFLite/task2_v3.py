#!/usr/bin/python3
import asyncio
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from PIL import Image
from moviepy.video.io.bindings import mplfig_to_npimage
import tflite_runtime.interpreter as tf  # Utilizziamo TensorFlow Lite al posto di Keras
import time
from memory_profiler import profile
#import cv2
import os
import logging

window_size = 2048
br = 192000
serverPort = 12002

fig, ax = plt.subplots(1, 1, figsize=(2.24, 2.24), dpi=100)

# Carichiamo il modello TensorFlow Lite
interpreter = tf.Interpreter(model_path='/home/pi/V_TFLite/model.tflite')
interpreter.allocate_tensors()

# Funzione per ottenere il nome del file di log
def get_log_file_path():
    # Formatta la data e l'ora per il nome del file
    date_str = time.strftime("%Y-%m-%d_%H:%M:%S")
    log_file_path = f"/home/pi/data/task2_log.txt"
    
    # Se il file non esiste, crealo
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w") as log_file:
            log_file.write("Detection Log Created on: {}\n\n".format(date_str))
    
    return log_file_path

# Ottieni il percorso del file di log
log_file_path = get_log_file_path()

def spectrogramNicolas(signal, fs, window_size=2048, overlap=1024):
    step = window_size - overlap
    bins = np.arange(0, len(signal) - window_size + 1, step)
    window = np.hanning(window_size)
    spectrogram = []
    for start in bins:
        segment = signal[start:start + window_size] * window
        spectrum = np.fft.fft(segment, n=2048)[:window_size // 2]
        magnitude = np.abs(spectrum)
        magnitude_db = 20 * np.log10(magnitude)
        spectrogram.append(magnitude_db)
    spectrogram =  np.array(spectrogram).T
    return spectrogram

def plotNicolas(spectrogram, fs, block_size, window_size=2048, min_freq=6000, max_freq=24000, rescale=1):
    freq_bins = int(max_freq / (fs / window_size))
    freq_bins_min = int(min_freq / (fs / window_size))
    #fig, ax = plt.subplots(1,1,figsize=(2.24,2.24), dpi=100)
    global fig, ax
    ax.clear()
    plt.gray()
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    plt.rcParams['axes.grid'] = False
    plt.rcParams['image.origin'] = 'lower'
    plt.rcParams['image.aspect'] = 'auto'
    ax.axis('off')
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    ax.imshow(spectrogram[freq_bins_min:freq_bins, :])
    image = Image.fromarray(mplfig_to_npimage(fig))
    #image = mplfig_to_npimage(fig)
    #plt.close()
    return image

def compute(wave, br):
    i = 0  # numero di spezzone iniziale
    nsec = 0.2  # spezzone da 0.2 secondi
    # preparo i 3 spezzoni
    blk1 = wave[int(i * br * nsec):int((i + 1) * br * nsec) + int(window_size / 2)]
    i = i + 1
    blk2 = wave[int(i * br * nsec) - int(window_size / 2):int((i + 1) * br * nsec) + int(window_size / 2)]
    i = i + 1
    blk3 = wave[int(i * br * nsec) - int(window_size / 2):int((i + 1) * br * nsec)]
    # ----------- Generazione spettrogrammi in 3 sub-blocchi ------------ #
    s1 = spectrogramNicolas(blk1, br, window_size, int(window_size / 2))
    s2 = spectrogramNicolas(blk2, br, window_size, int(window_size / 2))
    s3 = spectrogramNicolas(blk3, br, window_size, int(window_size / 2))
    # ----------- Combino i 3 spettrogrammi in uno solo ------------ #
    s = np.hstack((s1, s2, s3))
    # ----------- Renderizzo l'immagine dello spettrogramma ------------ #
    im = plotNicolas(s, br, len(s), rescale=0)
    
    # ----------- Preparo l'immagine per l'interrogazione della IA ------------ #
    im = im.resize((224, 224))  # Resize if needed
    image = np.array(im).transpose()# Convert to NumPy array
    
    #Creazuibe di un'immagine in scala di grigi
    gray_image = np.mean(image, axis=0, keepdims=True)
    # ----------- Interrogazione della IA con TensorFlow Lite ------------ #
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    expected_input_shape = input_details[0]['shape']
    
    print("Image shape before reshape:", image.shape)
    print("Expected input shape:", expected_input_shape)
    print("Gray image shape:", gray_image.shape)
    print("Input tensor shape expected by the model:", input_details[0]['shape'])
    gray_image = gray_image.transpose((1,2,0)) #Trasposta per adattare la forma corretta
    gray_image = gray_image.reshape((1, 224, 224, 1)).astype(np.float32)
    
    interpreter.set_tensor(input_details[0]['index'], gray_image)
    interpreter.invoke()

    yApp_lite = interpreter.get_tensor(output_details[0]['index'])
    return yApp_lite


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
