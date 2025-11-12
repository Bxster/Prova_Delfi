import asyncio
from scipy.io import wavfile
from socket import *
import numpy as np
import logging
import time
import RPi.GPIO as GPIO
import os

serverName = "127.0.0.1"
serverPort = 12001

# Funzione per ottenere il nome del file di log
def get_log_file_path():
    # Formatta la data e l'ora per il nome del file
    date_str = time.strftime("%Y-%m-%d_%H:%M:%S")
    log_file_path = f"/home/pi/data/detection_log.txt"
    
    # Se il file non esiste, crealo
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w") as log_file:
            log_file.write("Detection Log Created on: {}\n\n".format(date_str))
    
    return log_file_path

# Ottieni il percorso del file di log
log_file_path = get_log_file_path()

# Imposta la modalità del GPIO
GPIO.setmode(GPIO.BCM)

# Imposta il pin GPIO27 (BCM) come output
pin = 27
GPIO.setup(pin, GPIO.IN)

def get_sample():
    ring_host = "127.0.0.1"  # The server's hostname or IP address
    ring_port = 8888  # The port used by the server
    size_of_float = 4
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((ring_host, ring_port))
        s.sendall(b"nframes")
        nframes = int(s.recv(256).decode("utf8").split("\n")[0])
        s.sendall(b"len")
        nblocks = int(s.recv(256).decode('utf8').split("\n")[0])
        s.sendall(b"rate")
        samplerate = int(s.recv(256).decode('utf8').split("\n")[0])
        s.sendall(b"seconds")
        seconds = int(s.recv(256).decode('utf8').split("\n")[0])  
        blocksize = size_of_float * nframes * 2
        s.sendall(b"dump")
        for i in range(nblocks):
            if i == 0:
                data = s.recv(blocksize)
            else:
                data = data + s.recv(blocksize)
    myblock = np.frombuffer(data, dtype=np.float32)
 
    # Separare i canali (sinistro e destro)
    stereo_data = myblock.reshape(-1, 2)  # (n_samples, 2) per 2 canali

    with open(log_file_path, "a") as log_file:
            log_file.write(f"LEN: {len(stereo_data)}\n")

    left_channel = stereo_data[:, 0]  # Primo canale (sinistro)
    right_channel = stereo_data[:, 1]  # Secondo canale (destro)

    return samplerate, left_channel, right_channel

async def send_wavefile(num, wave, bitrate, result):
    global serverName
    global serverPort

    try:
        # Combina i canali sinistro e destro in un unico array stereo
        data_size = wave.itemsize
        wave_content = wave.tobytes()
        port = serverPort + int(num)

        with open(log_file_path, "a") as log_file:
            log_file.write(f"CONNECTION PORT: {port}\n")

        # Ottieni il bitrate e la dimensione del file
        file_size = len(wave_content)
        # Connettiti al server
        reader, writer = await asyncio.open_connection(serverName, port)

        # Invia il bitrate e la dimensione al server
        writer.write(f"{bitrate},{file_size},{data_size}".encode())
        await writer.drain()

        # Attendi l'ACK dal server
        ack = await reader.read(3)
        if ack != b'ACK':
            print("Errore: ACK non ricevuto")
            writer.close()
            return

        # Invia il file audio al server
        writer.write(wave_content)
        await writer.drain()

        response = await reader.read()
        result[num] = response

        # Chiudi la connessione
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        with open(log_file_path, "a") as log_file:
                log_file.write(f"ERRORE: {e}")
    
if __name__ == "__main__":
    try:
        format = "%(asctime)s:%(msecs)03s  %(message)s"
        logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
        while True:
            br, left_channel, right_channel = get_sample()  # Ottenere i due canali
            i = 0  # numero di spezzone iniziale
            nsec = 0.2  # spezzone da 0.2 secondi
            # spezzone globale da 0.6 secondi (utile per confronti)
            results = [None] * 3

            blk1_left = left_channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
            #blk1_right = right_channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
            asyncio.run(send_wavefile(0, blk1_left, br, results))

            i += 1
            blk2_left = left_channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
            #blk2_right = right_channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
            asyncio.run(send_wavefile(1, blk2_left, br, results))

            i += 1
            blk3_left = left_channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
            #blk3_right = right_channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
            asyncio.run(send_wavefile(2, blk3_left, br, results))

            # Calcola la media dei risultati
            detection = (float(results[0].decode().strip('][')) +
                        float(results[1].decode().strip('][')) +
                        float(results[2].decode().strip(']['))) / 3

            if detection >= 0.5:
                timestr = "/home/pi/data/Detections/" + time.strftime("%Y-%m-%d %H:%M:%S") + ".wav"
                wavfile.write(timestr, br, np.stack((left_channel, right_channel), axis=-1))  # Salva stereo

                # Esegui il comando per il rilevamento della direzione
                import subprocess
                result = subprocess.run(
                    ["python3", "/home/pi/Progetto/direzione.py", timestr],
                    text=True,  # Per ottenere l'output come stringa
                    capture_output=True  # Per catturare output e errori
                )

                with open(log_file_path, "a") as log_file:
                    log_file.write(f"{result.stdout}\n")

                # Accendo i relay
                GPIO.setmode(GPIO.BCM)
                PIN_ALIMENTAZIONE = 17
                PIN_SINISTRO = 24
                PIN_DESTRO = 27
                GPIO.setup(PIN_ALIMENTAZIONE, GPIO.OUT)
                GPIO.setup(PIN_SINISTRO, GPIO.OUT)
                GPIO.setup(PIN_DESTRO, GPIO.OUT)
                
                # Imposta i pin a livello basso
                GPIO.output(PIN_ALIMENTAZIONE, GPIO.LOW)
                if "destra" in result.stdout:
                    GPIO.output(PIN_DESTRO, GPIO.LOW)
                elif "sinistra" in result.stdout:
                    GPIO.output(PIN_SINISTRO, GPIO.LOW)
                else:
                    GPIO.output(PIN_DESTRO, GPIO.LOW)
                    GPIO.output(PIN_SINISTRO, GPIO.LOW)
                    
                # Rimossa la riproduzione audio
                
                # Pulisce la configurazione del GPIO prima di uscire
                GPIO.setup(PIN_ALIMENTAZIONE, GPIO.IN)
                GPIO.setup(PIN_SINISTRO, GPIO.IN)
                GPIO.setup(PIN_DESTRO, GPIO.IN)
                GPIO.cleanup()

            # Scrivi il valore di detection nel file di log
            with open(log_file_path, "a") as log_file:
                log_file.write(f"Detection: {detection}\n")

            time.sleep(1)
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Exception: {e}\n")
