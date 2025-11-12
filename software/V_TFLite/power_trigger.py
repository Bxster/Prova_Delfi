#!/usr/bin/python3
"""
Power Trigger Module
Pre-analizza i dati audio dai due canali (sinistro e destro) e attiva i trigger
se ampiezza/frequenza superano le soglie definite.
Gestisce la logica di TDOA e detection in base ai trigger attivati.
"""

import numpy as np
from scipy.signal import butter, filtfilt
import subprocess
import json
import logging
import time
import os

# Configurazione dei parametri
AMPLITUDE_THRESHOLD = 0.05  # Soglia di ampiezza (RMS) - da calibrare
FREQUENCY_THRESHOLD_MIN = 5000  # Frequenza minima (Hz)
FREQUENCY_THRESHOLD_MAX = 25000  # Frequenza massima (Hz)
POWER_THRESHOLD = -40  # Soglia di potenza in dB - da calibrare

# Configurazione direzione
DIREZIONE_SCRIPT = "/home/pi/Ecolocalizzazione/direzione.py"


class PowerTrigger:
    """
    Classe per gestire il power trigger su due canali audio.
    """
    
    def __init__(self, sample_rate, amplitude_threshold=AMPLITUDE_THRESHOLD, 
                 power_threshold=POWER_THRESHOLD, log_file_path=None):
        """
        Inizializza il Power Trigger.
        
        Args:
            sample_rate (int): Frequenza di campionamento (Hz)
            amplitude_threshold (float): Soglia di ampiezza RMS
            power_threshold (float): Soglia di potenza in dB
            log_file_path (str): Percorso del file di log
        """
        self.sample_rate = sample_rate
        self.amplitude_threshold = amplitude_threshold
        self.power_threshold = power_threshold
        self.log_file_path = log_file_path
        
        # Setup logging
        if log_file_path:
            self.logger = self._setup_logger(log_file_path)
        else:
            self.logger = logging.getLogger(__name__)
    
    def _setup_logger(self, log_file_path):
        """Configura il logger."""
        logger = logging.getLogger(__name__)
        handler = logging.FileHandler(log_file_path, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def calculate_rms(self, signal):
        """
        Calcola il valore RMS (Root Mean Square) del segnale.
        
        Args:
            signal (numpy.ndarray): Segnale audio
            
        Returns:
            float: Valore RMS
        """
        return np.sqrt(np.mean(signal ** 2))
    
    def calculate_power_db(self, signal):
        """
        Calcola la potenza del segnale in dB.
        
        Args:
            signal (numpy.ndarray): Segnale audio
            
        Returns:
            float: Potenza in dB
        """
        rms = self.calculate_rms(signal)
        # Evita log(0)
        if rms < 1e-10:
            return -np.inf
        power_db = 20 * np.log10(rms)
        return power_db
    
    def get_dominant_frequency(self, signal):
        """
        Calcola la frequenza dominante del segnale usando FFT.
        
        Args:
            signal (numpy.ndarray): Segnale audio
            
        Returns:
            float: Frequenza dominante (Hz)
        """
        # Calcola la FFT
        fft = np.fft.fft(signal)
        magnitude = np.abs(fft)
        
        # Trova l'indice della frequenza dominante
        dominant_idx = np.argmax(magnitude)
        
        # Converte l'indice in frequenza
        freqs = np.fft.fftfreq(len(signal), 1 / self.sample_rate)
        dominant_freq = abs(freqs[dominant_idx])
        
        return dominant_freq
    
    def check_trigger(self, signal, channel_name=""):
        """
        Verifica se il trigger deve attivarsi per il segnale dato.
        
        Args:
            signal (numpy.ndarray): Segnale audio del canale
            channel_name (str): Nome del canale (per logging)
            
        Returns:
            dict: Dizionario con informazioni del trigger
                {
                    'triggered': bool,
                    'rms': float,
                    'power_db': float,
                    'dominant_freq': float
                }
        """
        rms = self.calculate_rms(signal)
        power_db = self.calculate_power_db(signal)
        dominant_freq = self.get_dominant_frequency(signal)
        
        # Verifica se il trigger si attiva
        amplitude_check = rms > self.amplitude_threshold
        power_check = power_db > self.power_threshold
        frequency_check = (FREQUENCY_THRESHOLD_MIN <= dominant_freq <= FREQUENCY_THRESHOLD_MAX)
        
        triggered = amplitude_check and power_check and frequency_check
        
        if self.logger:
            self.logger.info(
                f"[{channel_name}] RMS: {rms:.6f}, Power: {power_db:.2f}dB, "
                f"Freq: {dominant_freq:.2f}Hz, Triggered: {triggered}"
            )
        
        return {
            'triggered': triggered,
            'rms': rms,
            'power_db': power_db,
            'dominant_freq': dominant_freq
        }
    
    def process_stereo_buffer(self, left_channel, right_channel):
        """
        Processa il buffer stereo e determina quale canale analizzare.
        
        Args:
            left_channel (numpy.ndarray): Segnale del canale sinistro
            right_channel (numpy.ndarray): Segnale del canale destro
            
        Returns:
            dict: Risultato del processing
                {
                    'left_triggered': bool,
                    'right_triggered': bool,
                    'left_info': dict,
                    'right_info': dict,
                    'action': str ('tdoa', 'left_only', 'right_only', 'none'),
                    'channel_to_analyze': str ('left', 'right', 'both', 'none')
                }
        """
        # Verifica i trigger su entrambi i canali
        left_info = self.check_trigger(left_channel, "LEFT")
        right_info = self.check_trigger(right_channel, "RIGHT")
        
        left_triggered = left_info['triggered']
        right_triggered = right_info['triggered']
        
        # Determina l'azione da intraprendere
        if left_triggered and right_triggered:
            action = 'tdoa'
            channel_to_analyze = 'both'
            if self.logger:
                self.logger.info("Both triggers activated -> Performing TDOA")
        elif left_triggered:
            action = 'left_only'
            channel_to_analyze = 'left'
            if self.logger:
                self.logger.info("Left trigger only -> Detection on left channel")
        elif right_triggered:
            action = 'right_only'
            channel_to_analyze = 'right'
            if self.logger:
                self.logger.info("Right trigger only -> Detection on right channel")
        else:
            action = 'none'
            channel_to_analyze = 'none'
            if self.logger:
                self.logger.info("No triggers activated -> Skipping detection")
        
        return {
            'left_triggered': left_triggered,
            'right_triggered': right_triggered,
            'left_info': left_info,
            'right_info': right_info,
            'action': action,
            'channel_to_analyze': channel_to_analyze
        }


def run_tdoa_analysis(wav_file_path):
    """
    Esegue l'analisi TDOA usando lo script direzione.py.
    
    Args:
        wav_file_path (str): Percorso del file WAV stereo
        
    Returns:
        dict: Risultato dell'analisi TDOA
            {
                'success': bool,
                'direction': str,
                'angle': float,
                'stdout': str,
                'stderr': str
            }
    """
    try:
        result = subprocess.run(
            ["python3", DIREZIONE_SCRIPT, wav_file_path],
            text=True,
            capture_output=True,
            timeout=10
        )
        
        # Tenta di parsare l'output JSON se disponibile
        try:
            # Estrae il JSON dall'output
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if line.startswith('{'):
                    direction_data = json.loads(line)
                    return {
                        'success': True,
                        'direction': direction_data.get('direzione', 'unknown'),
                        'angle': direction_data.get('angolo', 0),
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
        except (json.JSONDecodeError, IndexError):
            pass
        
        # Se il parsing JSON fallisce, ritorna l'output grezzo
        return {
            'success': result.returncode == 0,
            'direction': 'unknown',
            'angle': 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'direction': 'unknown',
            'angle': 0,
            'stdout': '',
            'stderr': 'TDOA analysis timeout'
        }
    except Exception as e:
        return {
            'success': False,
            'direction': 'unknown',
            'angle': 0,
            'stdout': '',
            'stderr': str(e)
        }


def get_nearest_channel(left_channel, right_channel, direction):
    """
    Ritorna il canale più vicino alla sorgente sonora in base alla direzione.
    
    Args:
        left_channel (numpy.ndarray): Segnale del canale sinistro
        right_channel (numpy.ndarray): Segnale del canale destro
        direction (str): Direzione ('sinistra', 'destra', 'centro')
        
    Returns:
        numpy.ndarray: Canale più vicino
    """
    if direction.lower() in ['sinistra', 'left']:
        return left_channel
    elif direction.lower() in ['destra', 'right']:
        return right_channel
    else:  # centro
        return left_channel  # Default al canale sinistro


if __name__ == "__main__":
    # Esempio di utilizzo
    print("Power Trigger Module - Example Usage")
    
    # Parametri di test
    sample_rate = 192000
    duration = 0.6  # secondi
    
    # Crea segnali di test
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Canale sinistro: segnale silenzioso
    left_channel = 0.01 * np.sin(2 * np.pi * 10000 * t)
    
    # Canale destro: segnale forte
    right_channel = 0.1 * np.sin(2 * np.pi * 12000 * t)
    
    # Inizializza il trigger
    trigger = PowerTrigger(sample_rate)
    
    # Processa il buffer
    result = trigger.process_stereo_buffer(left_channel, right_channel)
    
    print("\n=== Power Trigger Result ===")
    print(f"Left Triggered: {result['left_triggered']}")
    print(f"Right Triggered: {result['right_triggered']}")
    print(f"Action: {result['action']}")
    print(f"Channel to Analyze: {result['channel_to_analyze']}")
