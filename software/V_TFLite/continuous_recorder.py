#!/home/delfi/Prova_Delfi/.venv/bin/python3
"""
Continuous Audio Recorder with Streaming WAV Writer
Registra continuamente l'audio dal jack-ring-socket-server scrivendo direttamente su disco.
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
        """
        Inizializza il registratore continuo con scrittura streaming su disco.
        """
        self.recording = True
        self.sample_rate = SAMPLE_RATE_DEFAULT
        self.channels = 2  # Stereo
        self.wav_file = None
        self.filepath = None
        self.blocks_written = 0
        self.start_time = datetime.now()
        
        # Percorso di salvataggio
        self.logs_dir = Path(LOGS_DIR)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Registra i segnali di terminazione
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print("=" * 60)
        print("🎙️  Continuous Audio Recorder (Streaming Mode)")
        print("=" * 60)
        print(f"📁 Logs directory: {self.logs_dir}")
        print(f"🎵 Sample rate: {self.sample_rate} Hz")
        print(f"🔊 Channels: {self.channels} (stereo)")
        print(f"💾 Mode: Direct disk write (no memory buffer)")
        print("=" * 60)
    
    def _signal_handler(self, signum, frame):
        """Gestisce i segnali di terminazione per chiudere il file WAV correttamente."""
        print(f"\n📥 Received signal {signum}, finalizing recording...")
        self.recording = False
    
    def _open_wav_file(self):
        """
        Apre un nuovo file WAV per la registrazione streaming.
        """
        # Crea il nome del file con timestamp di inizio
        timestamp = self.start_time.strftime(TIMESTAMP_FMT)
        filename = f"continuous_recording_{timestamp}.wav"
        self.filepath = self.logs_dir / filename
        
        try:
            # Apri il file WAV in modalità write
            self.wav_file = wave.open(str(self.filepath), 'wb')
            self.wav_file.setnchannels(self.channels)
            self.wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            self.wav_file.setframerate(self.sample_rate)
            
            print(f"✅ Opened WAV file: {filename}")
            print(f"🔴 Recording started...")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error opening WAV file: {e}")
            raise
    
    def _close_wav_file(self):
        """
        Chiude il file WAV e stampa le statistiche.
        """
        if self.wav_file is None:
            return
        
        try:
            # Chiudi il file (questo aggiorna automaticamente l'header con la dimensione)
            self.wav_file.close()
            
            # Calcola statistiche
            if self.filepath.exists():
                size_mb = self.filepath.stat().st_size / (1024 * 1024)
                duration_sec = (datetime.now() - self.start_time).total_seconds()
                
                print("\n" + "=" * 60)
                print("✅ RECORDING COMPLETED")
                print("=" * 60)
                print(f"📄 File: {self.filepath.name}")
                print(f"📁 Path: {self.filepath}")
                print(f"⏱️  Duration: {duration_sec:.2f} seconds ({duration_sec/60:.1f} minutes)")
                print(f"💾 Size: {size_mb:.2f} MB")
                print(f"📦 Blocks written: {self.blocks_written}")
                print(f"🔊 Sample rate: {self.sample_rate} Hz")
                print(f"🎵 Channels: {self.channels}")
                print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error closing WAV file: {e}")
            import traceback
            traceback.print_exc()
    
    def _write_audio_block(self, stereo_data):
        """
        Scrive un blocco audio direttamente nel file WAV.
        
        Args:
            stereo_data: numpy array (N, 2) con dati float32
        """
        # Convert float32 to int16 for WAV storage
        # Assuming float32 is in range [-1, 1]
        stereo_int16 = (stereo_data * 32767).astype(np.int16)
        
        # Flatten to interleaved format [L, R, L, R, ...]
        interleaved = stereo_int16.flatten()
        
        # Scrivi nel file WAV
        self.wav_file.writeframes(interleaved.tobytes())
        
        # Ogni 10 blocchi, forza la scrittura fisica su disco
        self.blocks_written += 1
        if self.blocks_written % 10 == 0:
            # Flush del buffer Python
            self.wav_file._file.flush()
            # Forza la scrittura fisica su disco (importante per spegnimenti improvvisi)
            os.fsync(self.wav_file._file.fileno())
    
    def _get_audio_block(self):
        """
        Ottiene un blocco audio dal ring server usando il protocollo corretto.
        Ritorna: (sample_rate, stereo_data) dove stereo_data è un numpy array (N, 2)
        """
        size_of_float = 4
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((RING_HOST, RING_PORT))
            
            # Query nframes
            s.sendall(b"nframes")
            nframes = int(s.recv(256).decode("utf8").split("\n")[0])
            
            # Query len (number of blocks)
            s.sendall(b"len")
            nblocks = int(s.recv(256).decode('utf8').split("\n")[0])
            
            # Query rate (sample rate)
            s.sendall(b"rate")
            samplerate = int(s.recv(256).decode('utf8').split("\n")[0])
            
            # Query seconds (not strictly needed but keeps protocol consistent)
            s.sendall(b"seconds")
            
            # Request audio dump
            blocksize = size_of_float * nframes * 2  # stereo
            s.sendall(b"dump")
            
            # Receive all blocks
            data = b''
            for i in range(nblocks):
                chunk = s.recv(blocksize)
                data += chunk
        
        # Convert to numpy array (float32 stereo interleaved)
        myblock = np.frombuffer(data, dtype=np.float32)
        stereo_data = myblock.reshape(-1, 2)
        
        return samplerate, stereo_data
    
    def start(self):
        """Avvia la registrazione continua."""
        try:
            print("🔗 Connecting to jack-ring-socket-server...")
            
            # Test connection
            try:
                sr, _ = self._get_audio_block()
                self.sample_rate = sr
                print(f"✅ Connected! Sample rate: {sr} Hz\n")
            except Exception as e:
                raise ConnectionRefusedError(f"Cannot connect: {e}")
            
            # Apri il file WAV
            self._open_wav_file()
            
            # Loop di registrazione
            while self.recording:
                try:
                    sr, stereo_data = self._get_audio_block()
                    
                    # Scrivi il blocco direttamente su disco
                    self._write_audio_block(stereo_data)
                    
                    # Log periodico (ogni 50 blocchi, circa ogni 5 secondi)
                    if self.blocks_written % 50 == 0:
                        elapsed = (datetime.now() - self.start_time).total_seconds()
                        size_mb = self.filepath.stat().st_size / (1024 * 1024) if self.filepath.exists() else 0
                        print(f"🎙️  Recording... {elapsed:.1f}s | {self.blocks_written} blocks | {size_mb:.1f} MB")
                
                except Exception as e:
                    if self.recording:
                        print(f"⚠️  Error getting/writing block: {e}")
                        # Continue trying
                        import time
                        time.sleep(0.5)
            
            # Chiudi il file WAV (finalizza l'header)
            self._close_wav_file()
            
        except ConnectionRefusedError:
            print("❌ Cannot connect to jack-ring-socket-server.")
            print(f"   Make sure the server is running on {RING_HOST}:{RING_PORT}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error during recording: {e}")
            import traceback
            traceback.print_exc()
            # Prova comunque a chiudere il file
            self._close_wav_file()
            sys.exit(1)

def main():
    recorder = ContinuousRecorder()
    recorder.start()

if __name__ == "__main__":
    main()
