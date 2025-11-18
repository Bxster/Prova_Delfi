import sys
import numpy as np
import serial
import json
from scipy.io import wavfile
from scipy.signal import butter, filtfilt

from config import MIN_FREQ, MAX_FREQ, SPEED_OF_SOUND, MICROPHONE_DISTANCE

def cross_spettro_robusto(left_channel, right_channel, sample_rate, max_tdoa_samples):
    """
    Calcola la differenza temporale di arrivo (TDOA) tra due segnali audio (stereo).
    Utilizza la Real Fast Fourier Transform (RFFT) e la correlazione incrociata nel dominio delle frequenze.
    
    Parameters:
    left_channel (numpy.ndarray): Segnale audio del canale sinistro.
    right_channel (numpy.ndarray): Segnale audio del canale destro.
    sample_rate (int): Frequenza di campionamento dei segnali audio.
    max_tdoa_samples (int): Numero massimo di campioni di differenza temporale da considerare.
    
    Returns:
    float: Il valore del TDOA (Time Difference of Arrival) in secondi.
    """
    # FFT con padding a potenza di 2 per migliorare l'efficienza
    n = 2**np.ceil(np.log2(2 * len(left_channel))).astype(int)
    # n = len(left_channel) * 2 - 1
    
    # Calcola le trasformate di Fourier dei segnali
    SIG1 = np.fft.rfft(left_channel, n=n)
    SIG2 = np.fft.rfft(right_channel, n=n)
    
    # Filtro frequenziale per eliminare rumori fuori banda
    SIG1, SIG2 = frequency_filter(SIG1, SIG2, sample_rate, MIN_FREQ, MAX_FREQ, n)
    
    # Calcola il cross-spettro tra i due segnali
    R = SIG1 * np.conj(SIG2)

    # Normalizza il cross-spettro
    R /= (np.abs(R) + 1e-10)
    
    # Correlazione inversa nel dominio del tempo
    cc = np.fft.irfft(R, n)
    cc = np.fft.fftshift(cc)
    
    # Limita la correlazione al massimo TDOA
    cc = cc[len(cc)//2 - max_tdoa_samples: len(cc)//2 + max_tdoa_samples]
    
    # Trova il picco della correlazione
    delay = np.argmax(cc) - max_tdoa_samples
    
    # Calcola il TDOA in secondi
    tdoa = delay / sample_rate
    
    return tdoa

def frequency_filter(SIG1, SIG2, sample_rate, lowcut, highcut, n):
    """
    Applica un filtro passa banda ai segnali audio nei due canali (sinistro e destro) 
    per rimuovere frequenze al di fuori dell'intervallo specificato.
    
    Parameters:
    SIG1 (numpy.ndarray): Trasformata di Fourier del segnale del canale sinistro.
    SIG2 (numpy.ndarray): Trasformata di Fourier del segnale del canale destro.
    sample_rate (int): Frequenza di campionamento dei segnali audio.
    lowcut (float): Frequenza di taglio inferiore del filtro (in Hz).
    highcut (float): Frequenza di taglio superiore del filtro (in Hz).
    n (int): Numero di campioni per la FFT.
    
    Returns:
    tuple: Le due trasformate di Fourier (SIG1 e SIG2) dopo l'applicazione del filtro.
    """
    # Frequenze associate ai coefficienti della FFT
    freqs = np.fft.rfftfreq(n, d=1/sample_rate)
    
    # Azzeramento delle frequenze fuori banda
    SIG1[(freqs < lowcut) | (freqs > highcut)] = 0
    SIG2[(freqs < lowcut) | (freqs > highcut)] = 0
    
    return SIG1, SIG2

def main():
    """
    Funzione principale che legge un file audio WAV stereo, calcola il TDOA e 
    determina la direzione del suono (sinistra, destra o centrale).
    Il programma richiede come argomento il percorso del file WAV da elaborare.
    
    La funzione legge i segnali audio, applica un filtro passa alto, calcola 
    la differenza temporale di arrivo (TDOA) e poi converte il TDOA in un angolo 
    per determinare la direzione del suono rispetto ai microfoni.
    """
    try:
        # Legge il percorso del file WAV da riga di comando
        file_wav = sys.argv[1]
        sample_rate, data = wavfile.read(file_wav)

        # Verifica che il file sia stereo
        if len(data.shape) != 2 or data.shape[1] != 2:
            print("Il file WAV deve essere stereo con due canali.")

        left_channel = data[:, 0]  # Estrai il canale sinistro
        right_channel = data[:, 1]  # Estrai il canale destro

        # Calcola il massimo TDOA teorico in campioni
        max_tdoa_samples = int((MICROPHONE_DISTANCE / SPEED_OF_SOUND) * sample_rate)

        # Calcola la frequenza di Nyquist
        nyquist = 0.5 * sample_rate
        # Normalizza la frequenza di taglio rispetto alla frequenza di Nyquist
        normal_cutoff = 1000 / nyquist
        # Progetta il filtro passa alto usando il filtro di Butterworth
        b, a = butter(4, normal_cutoff, btype='high', analog=False)
        
        # Applica il filtro passa alto ai segnali audio (canale sinistro e destro)
        left_channel = filtfilt(b, a, left_channel)
        right_channel = filtfilt(b, a, right_channel)

        # Calcola il TDOA
        tdoa = cross_spettro_robusto(left_channel, right_channel, sample_rate, max_tdoa_samples)
        
        # Calcola l'angolo di provenienza del suono
        angle = np.arcsin(tdoa * SPEED_OF_SOUND / MICROPHONE_DISTANCE)
        angle_degrees = np.degrees(angle)
        print(f"Audio: {file_wav}")

        # Determina la direzione del suono
        if tdoa < 0.000061 and tdoa > -0.000061:
            result = "Il suono arriva esattamente dal centro (0-3 gradi)"
            result_2 = {"direzione": "centro", "angolo": 0}
        elif tdoa > 0:
            result = f"Il suono proviene da sinistra con un angolo di {angle_degrees:.2f} gradi"
            result_2 = {"direzione": "sinistra", "angolo": round(angle_degrees, 2)}
        else:
            result = f"Il suono proviene da destra con un angolo di {abs(angle_degrees):.2f} gradi"
            result_2 = {"direzione": "destra", "angolo": round(abs(angle_degrees), 2)}

        # Converti il dizionario in stringa JSON
        result_json = json.dumps(result_2)

        # Invio del JSON tramite UART
        uart = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)
        uart.write(result_json.encode())

        print(f"{result}\n")
    except Exception as e:
        print("Rilevazione fallita")
        print(f"Errore: {e}")

# Avvia l'esecuzione del programma
if __name__ == "__main__":
    main()
