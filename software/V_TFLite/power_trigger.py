#!/home/delfi/Prova_Delfi/.venv/bin/python3
"""
Power Trigger Module
Pre-analizza i dati audio dai due canali (sinistro e destro) e attiva i trigger
se ampiezza/frequenza superano le soglie definite.
Gestisce la logica di TDOA e detection in base ai trigger attivati.
"""

import numpy as np
import logging

from scipy.signal import butter, filtfilt

from config import (
    PROMINENCE_BAND_MIN_HZ, PROMINENCE_BAND_MAX_HZ, PROMINENCE_THRESHOLD_DB,
    MIN_FREQ, MAX_FREQ, SPEED_OF_SOUND, MICROPHONE_DISTANCE,
    HIGH_PASS_CUTOFF_HZ, INVERT_PHASE, TDOA_CENTER_THRESHOLD_SEC
)

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


def _apply_highpass_filter(signal, sample_rate, cutoff_hz):
    """
    Applica un filtro high-pass Butterworth al segnale.
    In caso di errore (es. frequenza di taglio troppo alta), ritorna il segnale originale.
    
    Args:
        signal: Segnale audio mono
        sample_rate: Frequenza di campionamento (Hz)
        cutoff_hz: Frequenza di taglio del filtro (Hz)
    
    Returns:
        Segnale filtrato (o originale in caso di errore)
    """
    nyquist = 0.5 * sample_rate
    # Verifica che la frequenza di taglio sia valida
    if cutoff_hz >= nyquist or cutoff_hz <= 0:
        return signal
    try:
        normal_cutoff = cutoff_hz / nyquist
        b, a = butter(4, normal_cutoff, btype='high', analog=False)
        return filtfilt(b, a, signal)
    except ValueError:
        # Se filtfilt fallisce (segnale troppo corto, ecc.), ritorna l'originale
        return signal


def _cross_spectrum_gcc_phat(left_channel, right_channel, sample_rate, max_tdoa_samples):
    """
    Calcola TDOA usando GCC-PHAT (Generalized Cross-Correlation with Phase Transform).
    Applica windowing per ridurre spectral leakage.
    
    Args:
        left_channel: Segnale canale sinistro (già filtrato)
        right_channel: Segnale canale destro (già filtrato)
        sample_rate: Frequenza di campionamento (Hz)
        max_tdoa_samples: Massimo ritardo in campioni
    
    Returns:
        TDOA in secondi
    """
    n_samples = len(left_channel)
    
    # Applica finestra di Hanning per ridurre spectral leakage
    window = np.hanning(n_samples)
    left_windowed = left_channel * window
    right_windowed = right_channel * window
    
    # FFT con padding a potenza di 2
    n_fft = 2 ** int(np.ceil(np.log2(2 * n_samples)))
    
    SIG1 = np.fft.rfft(left_windowed, n=n_fft)
    SIG2 = np.fft.rfft(right_windowed, n=n_fft)
    
    # Filtro frequenziale per eliminare rumori fuori banda
    freqs = np.fft.rfftfreq(n_fft, d=1/sample_rate)
    band_mask = (freqs >= MIN_FREQ) & (freqs <= MAX_FREQ)
    SIG1[~band_mask] = 0
    SIG2[~band_mask] = 0
    
    # Cross-spettro con normalizzazione GCC-PHAT
    R = SIG1 * np.conj(SIG2)
    R /= (np.abs(R) + 1e-10)  # Phase transform
    
    # Correlazione inversa nel dominio del tempo
    cc = np.fft.irfft(R, n_fft)
    cc = np.fft.fftshift(cc)
    
    # Limita la correlazione al massimo TDOA fisicamente possibile
    center = len(cc) // 2
    cc_limited = cc[center - max_tdoa_samples : center + max_tdoa_samples]
    
    # Trova il picco della correlazione
    delay = np.argmax(cc_limited) - max_tdoa_samples
    
    return delay / sample_rate


def compute_tdoa_direct(left_channel, right_channel, sample_rate):
    """
    Calcola TDOA direttamente sui buffer audio (senza subprocess).
    Gestisce inversione di fase, filtering robusto e overflow dell'arcsin.
    
    Args:
        left_channel: Segnale canale sinistro
        right_channel: Segnale canale destro
        sample_rate: Frequenza di campionamento (Hz)
    
    Returns:
        dict: {
            'success': bool,
            'direction': str ('sinistra', 'destra', 'centro'),
            'angle': float (gradi),
            'tdoa_sec': float (ritardo in secondi),
            'error': str (messaggio errore se success=False)
        }
    """
    try:
        # Converti in float per elaborazione
        left = left_channel.astype(np.float64)
        right = right_channel.astype(np.float64)
        
        # Gestione inversione di fase (se configurata)
        if INVERT_PHASE:
            right = -right
        
        # Applica filtro high-pass (robusto, non fallisce)
        left = _apply_highpass_filter(left, sample_rate, HIGH_PASS_CUTOFF_HZ)
        right = _apply_highpass_filter(right, sample_rate, HIGH_PASS_CUTOFF_HZ)
        
        # Calcola massimo TDOA teorico in campioni
        max_tdoa_samples = int((MICROPHONE_DISTANCE / SPEED_OF_SOUND) * sample_rate) + 1
        
        # Calcola TDOA con GCC-PHAT
        tdoa = _cross_spectrum_gcc_phat(left, right, sample_rate, max_tdoa_samples)
        
        # Calcola l'angolo con protezione overflow arcsin
        sin_arg = (tdoa * SPEED_OF_SOUND) / MICROPHONE_DISTANCE
        sin_arg_clamped = np.clip(sin_arg, -1.0, 1.0)  # Previene domain error
        angle_rad = np.arcsin(sin_arg_clamped)
        angle_deg = float(np.degrees(angle_rad))
        
        # Determina la direzione
        if abs(tdoa) < TDOA_CENTER_THRESHOLD_SEC:
            direction = 'centro'
            angle_deg = 0.0
        elif tdoa > 0:
            direction = 'sinistra'
        else:
            direction = 'destra'
            angle_deg = abs(angle_deg)
        
        return {
            'success': True,
            'direction': direction,
            'angle': round(angle_deg, 2),
            'tdoa_sec': round(tdoa, 5),
            'error': ''
        }
        
    except Exception as e:
        return {
            'success': False,
            'direction': 'unknown',
            'angle': 0.0,
            'tdoa_sec': 0.0,
            'error': str(e)
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

