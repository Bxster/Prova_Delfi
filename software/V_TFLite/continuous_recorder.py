#!/home/delfi/Prova_Delfi/.venv/bin/python3
"""
Continuous Audio Recorder
Registra continuamente l'audio dal jack-ring-socket-server e salva in un file WAV quando viene fermato.
"""

import socket
import struct
import numpy as np
import wave
import signal
import sys
import os
from datetime import datetime
from pathlib import Path

# Import configurazioni
from config import (
    RING_HOST, RING_PORT, SAMPLE_RATE_DEFAULT,
    LOGS_DIR, TIMESTAMP_FMT
)

class ContinuousRecorder:
    def __init__(self):
        self.recording = True
        self.audio_buffer = []
        self.sample_rate = SAMPLE_RATE_DEFAULT
        self.channels = 2  # Stereo
        
        # Percorso di salvataggio
        self.logs_dir = Path(LOGS_DIR)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Registra i segnali di terminazione
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print("=" * 60)
        print("🎙️  Continuous Audio Recorder")
        print("=" * 60)
        print(f"📁 Logs directory: {self.logs_dir}")
        print(f"🎵 Sample rate: {self.sample_rate} Hz")
        print(f"🔊 Channels: {self.channels} (stereo)")
        print("🔴 Recording started...")
        print("=" * 60)
    
    def _signal_handler(self, signum, frame):
        """Gestisce i segnali di terminazione per salvare il file prima di uscire."""
        print(f"\n📥 Received signal {signum}, stopping recorder...")
        self.recording = False
    
    def _save_recording(self):
        """Salva la registrazione in un file WAV."""
        if not self.audio_buffer:
            print("⚠️  No audio data to save.")
            return
        
        # Crea il nome del file con timestamp
        timestamp = datetime.now().strftime(TIMESTAMP_FMT)
        filename = f"continuous_recording_{timestamp}.wav"
        filepath = self.logs_dir / filename
        
        try:
            # Converti il buffer in un array numpy
            audio_data = np.concatenate(self.audio_buffer, axis=0)
            
            # Assicurati che sia in formato int16
            if audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            
            # Salva come file WAV
            with wave.open(str(filepath), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            # Calcola statistiche
            duration_sec = len(audio_data) / (self.sample_rate * self.channels)
            size_mb = filepath.stat().st_size / (1024 * 1024)
            
            print("\n" + "=" * 60)
            print("✅ Recording saved successfully!")
            print("=" * 60)
            print(f"📄 File: {filename}")
            print(f"📁 Path: {filepath}")
            print(f"⏱️  Duration: {duration_sec:.2f} seconds")
            print(f"💾 Size: {size_mb:.2f} MB")
            print(f"🔊 Sample rate: {self.sample_rate} Hz")
            print(f"🎵 Channels: {self.channels}")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error saving recording: {e}")
            import traceback
            traceback.print_exc()
    
    def _connect_to_ring_server(self):
        """Si connette al jack-ring-socket-server."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((RING_HOST, RING_PORT))
        return sock
    
    def _receive_audio_chunk(self, sock):
        """Riceve un chunk di audio dal ring server."""
        try:
            # Ricevi l'header (4 bytes = size del chunk)
            header = sock.recv(4)
            if len(header) < 4:
                return None
            
            chunk_size = struct.unpack('!I', header)[0]
            
            # Ricevi i dati audio
            audio_data = b''
            while len(audio_data) < chunk_size:
                packet = sock.recv(chunk_size - len(audio_data))
                if not packet:
                    return None
                audio_data += packet
            
            # Converti in numpy array (stereo int16)
            # Il formato è interleaved: [L, R, L, R, ...]
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            return samples
            
        except socket.timeout:
            return None
        except Exception as e:
            print(f"Error receiving chunk: {e}")
            return None
    
    def start(self):
        """Avvia la registrazione continua."""
        try:
            # Connessione al ring server
            sock = self._connect_to_ring_server()
            sock.settimeout(1.0)  # Timeout per permettere controlli periodici
            
            print("🔗 Connected to jack-ring-socket-server")
            
            # Loop di registrazione
            while self.recording:
                chunk = self._receive_audio_chunk(sock)
                
                if chunk is not None and len(chunk) > 0:
                    self.audio_buffer.append(chunk)
                    
                    # Log periodico (ogni ~10 secondi)
                    total_samples = sum(len(c) for c in self.audio_buffer)
                    if total_samples % (self.sample_rate * self.channels * 10) < (self.sample_rate * self.channels):
                        duration = total_samples / (self.sample_rate * self.channels)
                        print(f"🎙️  Recording... {duration:.1f}s")
            
            # Chiudi la connessione
            sock.close()
            
            # Salva la registrazione
            self._save_recording()
            
        except ConnectionRefusedError:
            print("❌ Cannot connect to jack-ring-socket-server.")
            print("   Make sure the server is running on {}:{}".format(RING_HOST, RING_PORT))
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error during recording: {e}")
            import traceback
            traceback.print_exc()
            # Prova comunque a salvare quello che è stato registrato
            self._save_recording()
            sys.exit(1)

def main():
    recorder = ContinuousRecorder()
    recorder.start()

if __name__ == "__main__":
    main()
