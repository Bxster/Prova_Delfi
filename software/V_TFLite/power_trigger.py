#!/usr/bin/python3
"""
Power Trigger Module
Pre-analizza i dati audio dai due canali (sinistro e destro) e attiva i trigger
se ampiezza/frequenza superano le soglie definite.
Gestisce la logica di TDOA e detection in base ai trigger attivati.
"""

import numpy as np
import subprocess
import json
import logging

# Parametri per la prominenza spettrale
PROMINENCE_BAND_MIN_HZ = 3000
PROMINENCE_BAND_MAX_HZ = 25000
PROMINENCE_THRESHOLD_DB = 12.0

# Configurazione direzione
DIREZIONE_SCRIPT = "/home/pi/Prova_Delfi/software/Ecolocalizzazione/direzione.py"


class PowerTrigger:
    """
    Classe per gestire il power trigger su due canali audio.
    """

    def __init__(self, sample_rate, prominence_threshold_db=PROMINENCE_THRESHOLD_DB,
                 band_min_hz=PROMINENCE_BAND_MIN_HZ, band_max_hz=PROMINENCE_BAND_MAX_HZ,
                 log_file_path=None):
        """
        Inizializza il Power Trigger.

        Args:
            sample_rate (int): Frequenza di campionamento (Hz)
            log_file_path (str): Percorso del file di log
        """
        self.sample_rate = sample_rate
        self.prominence_threshold_db = prominence_threshold_db
        self.band_min_hz = band_min_hz
        self.band_max_hz = band_max_hz
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

    def compute_spectral_prominence(self, signal):
        """
        Calcola la prominenza del picco spettrale (dB) nella banda [band_min_hz, band_max_hz].
        Ritorna (prominence_db, peak_freq_hz).
        """
        n = len(signal)
        if n == 0:
            return -np.inf, 0.0
        window = np.hanning(n)
        sigw = signal * window
        spec = np.fft.rfft(sigw)
        mag = np.abs(spec)
        mag_db = 20 * np.log10(mag + 1e-12)
        freqs = np.fft.rfftfreq(n, 1 / self.sample_rate)
        mask = (freqs >= self.band_min_hz) & (freqs <= self.band_max_hz)
        if not np.any(mask):
            return -np.inf, 0.0
        band_mag_db = mag_db[mask]
        band_freqs = freqs[mask]
        if band_mag_db.size == 0:
            return -np.inf, 0.0
        median_db = np.median(band_mag_db)
        max_idx = int(np.argmax(band_mag_db))
        prom_db = float(band_mag_db[max_idx] - median_db)
        peak_freq = float(band_freqs[max_idx])
        return prom_db, peak_freq

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
                    'prominence_db': float,
                    'peak_freq': float
                }
        """
        prominence_db, peak_freq = self.compute_spectral_prominence(signal)
        triggered = prominence_db >= self.prominence_threshold_db
        if self.logger:
            self.logger.info(
                f"[{channel_name}] PeakFreq: {peak_freq:.2f}Hz, Prom: {prominence_db:.2f}dB, Triggered: {triggered}"
            )
        return {
            'triggered': triggered,
            'prominence_db': prominence_db,
            'peak_freq': peak_freq
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

