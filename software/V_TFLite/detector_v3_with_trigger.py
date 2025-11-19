#!/usr/bin/python3
"""
Detector V3 con Power Trigger Integration
Integra il power trigger nel flusso di detection esistente.
"""

import asyncio
from scipy.io import wavfile
from socket import *
import numpy as np
import logging
import time
import os
import sys

# Importa il modulo power trigger
from power_trigger import PowerTrigger, run_tdoa_analysis, get_nearest_channel

from config import RING_HOST, SERVER_PORT_BASE, DETECTION_THRESHOLD

# Funzione per ottenere il nome del file di log
def get_log_file_path():
    date_str = time.strftime("%Y-%m-%d_%H:%M:%S")
    log_file_path = f"/home/pi/data/detection_log.txt"
    
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w") as log_file:
            log_file.write("Detection Log Created on: {}\n\n".format(date_str))
    
    return log_file_path

log_file_path = get_log_file_path()


def get_sample():
    """Ottiene i campioni audio dai due canali."""
    ring_host = "127.0.0.1"
    ring_port = 8888
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
    stereo_data = myblock.reshape(-1, 2)
    
    with open(log_file_path, "a") as log_file:
        log_file.write(f"LEN: {len(stereo_data)}\n")
    
    left_channel = stereo_data[:, 0]
    right_channel = stereo_data[:, 1]
    
    return samplerate, left_channel, right_channel


async def send_wavefile(num, wave, bitrate, result):
    """Invia il file audio al server per la detection."""
    global RING_HOST
    global SERVER_PORT_BASE
    
    try:
        data_size = wave.itemsize
        wave_content = wave.tobytes()
        port = SERVER_PORT_BASE + int(num)
        
        with open(log_file_path, "a") as log_file:
            log_file.write(f"CONNECTION PORT: {port}\n")
        
        file_size = len(wave_content)
        reader, writer = await asyncio.open_connection(RING_HOST, port)
        
        writer.write(f"{bitrate},{file_size},{data_size}".encode())
        await writer.drain()
        
        ack = await reader.read(3)
        if ack != b'ACK':
            print("Errore: ACK non ricevuto")
            writer.close()
            return
        
        writer.write(wave_content)
        await writer.drain()
        
        response = await reader.read()
        result[num] = response
        
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"ERRORE send_wavefile: {e}\n")


def extract_blocks(channel, br, nsec=0.2, window_size=2048):
    """
    Estrae 3 blocchi dal canale audio.
    
    Args:
        channel (numpy.ndarray): Canale audio
        br (int): Bitrate/sample rate
        nsec (float): Durata di ogni blocco in secondi
        window_size (int): Dimensione della finestra
        
    Returns:
        tuple: (blk1, blk2, blk3)
    """
    i = 0
    blk1 = channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
    i += 1
    blk2 = channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
    i += 1
    blk3 = channel[int(i * br * nsec):int((i * br * nsec) + br * nsec * 3)]
    
    return blk1, blk2, blk3


async def perform_detection(channel, br):
    """
    Esegue la detection su un canale specifico inviando un singolo blocco al task server.
    Ritorna la risposta grezza del server (bytes).
    """
    blk1, blk2, blk3 = extract_blocks(channel, br)
    results = [None]
    # Usa il blocco centrale (blk2) per una finestra rappresentativa
    await send_wavefile(0, blk2, br, results)
    return results[0]


async def main_loop_with_trigger():
    """
    Loop principale con power trigger integration.
    """
    try:
        # Inizializza il power trigger
        br, _, _ = get_sample()
        trigger = PowerTrigger(br, log_file_path=log_file_path)
        
        with open(log_file_path, "a") as log_file:
            log_file.write("=== Starting detector with power trigger ===\n")
        
        while True:
            br, left_channel, right_channel = get_sample()
            
            # Esegui il power trigger
            trigger_result = trigger.process_stereo_buffer(left_channel, right_channel)
            
            with open(log_file_path, "a") as log_file:
                log_file.write(f"\n--- Trigger Result ---\n")
                log_file.write(f"Action: {trigger_result['action']}\n")
                log_file.write(f"Channel to analyze: {trigger_result['channel_to_analyze']}\n")
            
            # Determina quale canale analizzare
            if trigger_result['action'] == 'none':
                # Nessun trigger attivato, salta la detection
                with open(log_file_path, "a") as log_file:
                    log_file.write("No triggers activated, skipping detection\n")
                await asyncio.sleep(1)
                continue
            
            if trigger_result['action'] == 'tdoa':
                # Entrambi i trigger attivati: esegui TDOA
                with open(log_file_path, "a") as log_file:
                    log_file.write("Performing TDOA analysis...\n")
                
                # Salva il file stereo temporaneo per TDOA
                temp_wav_path = f"/tmp/tdoa_temp_{time.time()}.wav"
                wavfile.write(temp_wav_path, br, np.stack((left_channel, right_channel), axis=-1))
                
                # Esegui TDOA
                tdoa_result = run_tdoa_analysis(temp_wav_path)
                
                with open(log_file_path, "a") as log_file:
                    log_file.write(f"TDOA Result: {tdoa_result}\n")
                
                if tdoa_result['success']:
                    # Ottieni il canale più vicino
                    nearest_channel = get_nearest_channel(
                        left_channel, right_channel, tdoa_result['direction']
                    )
                    
                    # Esegui la detection sul canale più vicino
                    if tdoa_result['direction'].lower() in ['sinistra', 'left']:
                        resp = await perform_detection(left_channel, br)
                    else:
                        resp = await perform_detection(right_channel, br)

                    # Applica la soglia su un unico score
                    if resp is not None:
                        try:
                            detection = float(resp.decode().strip())
                            with open(log_file_path, "a") as log_file:
                                log_file.write(f"Detection: {detection}\n")
                            if detection >= DETECTION_THRESHOLD:
                                timestr = "/home/pi/data/Detections/" + time.strftime("%Y-%m-%d %H:%M:%S") + ".wav"
                                wavfile.write(timestr, br, np.stack((left_channel, right_channel), axis=-1))
                        except Exception as e:
                            with open(log_file_path, "a") as log_file:
                                log_file.write(f"Error parsing detection result: {e}\n")
                else:
                    with open(log_file_path, "a") as log_file:
                        log_file.write("TDOA analysis failed\n")
            
            elif trigger_result['action'] == 'left_only':
                # Solo il trigger sinistro attivato
                with open(log_file_path, "a") as log_file:
                    log_file.write("Left trigger only, detecting on left channel\n")
                
                resp = await perform_detection(left_channel, br)
                if resp is not None:
                    try:
                        detection = float(resp.decode().strip())
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Detection: {detection}\n")
                        if detection >= DETECTION_THRESHOLD:
                            timestr = "/home/pi/data/Detections/" + time.strftime("%Y-%m-%d %H:%M:%S") + ".wav"
                            wavfile.write(timestr, br, np.stack((left_channel, right_channel), axis=-1))
                    except Exception as e:
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Error parsing detection result: {e}\n")
            
            elif trigger_result['action'] == 'right_only':
                # Solo il trigger destro attivato
                with open(log_file_path, "a") as log_file:
                    log_file.write("Right trigger only, detecting on right channel\n")
                
                resp = await perform_detection(right_channel, br)
                if resp is not None:
                    try:
                        detection = float(resp.decode().strip())
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Detection: {detection}\n")
                        if detection >= DETECTION_THRESHOLD:
                            timestr = "/home/pi/data/Detections/" + time.strftime("%Y-%m-%d %H:%M:%S") + ".wav"
                            wavfile.write(timestr, br, np.stack((left_channel, right_channel), axis=-1))
                    except Exception as e:
                        with open(log_file_path, "a") as log_file:
                            log_file.write(f"Error parsing detection result: {e}\n")
            await asyncio.sleep(1)
    
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Exception in main_loop_with_trigger: {e}\n")


if __name__ == "__main__":
    try:
        format = "%(asctime)s:%(msecs)03s  %(message)s"
        logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
        asyncio.run(main_loop_with_trigger())
    except KeyboardInterrupt:
        with open(log_file_path, "a") as log_file:
            log_file.write("Program interrupted by user\n")
    except Exception as e:
        with open(log_file_path, "a") as log_file:
            log_file.write(f"Fatal error: {e}\n")
