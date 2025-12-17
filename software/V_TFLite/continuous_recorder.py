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
    LOGS_DIR, TIMESTAMP_FMT, CONTINUOUS_RECORDING_ROTATION_MINUTES
)

class ContinuousRecorder:
    def __init__(self, rotation_minutes=5):
        """
        Inizializza il registratore continuo con salvataggio rotazionale.
        
        Args:
            rotation_minutes: Minuti dopo i quali salvare e iniziare un nuovo file (default: 5)
        """
        self.recording = True
        self.audio_buffer = []
        self.sample_rate = SAMPLE_RATE_DEFAULT
        self.channels = 2  # Stereo
        self.rotation_minutes = rotation_minutes
        self.rotation_seconds = rotation_minutes * 60
        self.last_save_time = datetime.now()
        self.file_counter = 0
        
        # Percorso di salvataggio
        self.logs_dir = Path(LOGS_DIR)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Registra i segnali di terminazione
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print("=" * 60)
        print("🎙️  Continuous Audio Recorder (Rolling Mode)")
        print("=" * 60)
        print(f"📁 Logs directory: {self.logs_dir}")
        print(f"🎵 Sample rate: {self.sample_rate} Hz")
        print(f"🔊 Channels: {self.channels} (stereo)")
        print(f"♻️  Auto-save: every {rotation_minutes} minutes")
        print("🔴 Recording started...")
        print("=" * 60)
    
    def _signal_handler(self, signum, frame):
        """Gestisce i segnali di terminazione per salvare il file prima di uscire."""
        print(f"\n📥 Received signal {signum}, stopping recorder...")
        self.recording = False
    
    def _save_recording(self, is_rotation=False):
        """
        Salva la registrazione in un file WAV.
        
        Args:
            is_rotation: True se è un salvataggio automatico rotazionale, False se finale
        """
        if not self.audio_buffer:
            print("⚠️  No audio data to save.")
            return
        
        # Crea il nome del file con timestamp
        timestamp = datetime.now().strftime(TIMESTAMP_FMT)
        self.file_counter += 1
        
        if is_rotation:
            filename = f"continuous_recording_{timestamp}_part{self.file_counter:03d}.wav"
        else:
            filename = f"continuous_recording_{timestamp}_final.wav"
        
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
            
            save_type = "🔄 ROTATIONAL SAVE" if is_rotation else "✅ FINAL SAVE"
            print("\n" + "=" * 60)
            print(save_type)
            print("=" * 60)
            print(f"📄 File: {filename}")
            print(f"📁 Path: {filepath}")
            print(f"⏱️  Duration: {duration_sec:.2f} seconds")
            print(f"💾 Size: {size_mb:.2f} MB")
            print(f"🔊 Sample rate: {self.sample_rate} Hz")
            print(f"🎵 Channels: {self.channels}")
            print("=" * 60)
            
            # Se è una rotazione, resetta il buffer e il timer
            if is_rotation:
                self.audio_buffer = []
                self.last_save_time = datetime.now()
                print("▶️  Continuing recording...\n")
            
        except Exception as e:
            print(f"❌ Error saving recording: {e}")
            import traceback
            traceback.print_exc()
    
    def _should_rotate(self):
        """Controlla se è il momento di salvare e ruotare."""
        elapsed = (datetime.now() - self.last_save_time).total_seconds()
        return elapsed >= self.rotation_seconds
    
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
                print(f"✅ Connected! Sample rate: {sr} Hz")
            except Exception as e:
                raise ConnectionRefusedError(f"Cannot connect: {e}")
            
            # Loop di registrazione
            while self.recording:
                try:
                    sr, stereo_data = self._get_audio_block()
                    
                    # Convert float32 to int16 for WAV storage
                    # Assuming float32 is in range [-1, 1]
                    stereo_int16 = (stereo_data * 32767).astype(np.int16)
                    
                    # Flatten to interleaved format [L, R, L, R, ...]
                    interleaved = stereo_int16.flatten()
                    
                    self.audio_buffer.append(interleaved)
                    
                    # Controlla se è il momento di rotare (salvare e continuare)
                    if self._should_rotate():
                        print(f"\n⏰ Rotation time reached ({self.rotation_minutes} minutes)")
                        self._save_recording(is_rotation=True)
                    
                    # Log periodico (ogni ~5 blocchi)
                    if len(self.audio_buffer) % 5 == 0:
                        total_samples = sum(len(c) for c in self.audio_buffer)
                        duration = total_samples / (self.sample_rate * self.channels)
                        elapsed = (datetime.now() - self.last_save_time).total_seconds()
                        remaining = self.rotation_seconds - elapsed if elapsed < self.rotation_seconds else 0
                        print(f"🎙️  Recording... {duration:.1f}s ({len(self.audio_buffer)} blocks) | Next save in: {remaining:.0f}s")
                
                except Exception as e:
                    if self.recording:
                        print(f"⚠️  Error getting block: {e}")
                        # Continue trying
                        import time
                        time.sleep(0.5)
            
            # Salva la registrazione finale
            self._save_recording(is_rotation=False)
            
        except ConnectionRefusedError:
            print("❌ Cannot connect to jack-ring-socket-server.")
            print("   Make sure the server is running on {}:{}".format(RING_HOST, RING_PORT))
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error during recording: {e}")
            import traceback
            traceback.print_exc()
            # Prova comunque a salvare quello che è stato registrato
            self._save_recording(is_rotation=False)
            sys.exit(1)

def main():
    recorder = ContinuousRecorder(rotation_minutes=CONTINUOUS_RECORDING_ROTATION_MINUTES)
    recorder.start()

if __name__ == "__main__":
    main()
