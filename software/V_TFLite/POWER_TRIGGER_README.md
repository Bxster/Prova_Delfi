# Power Trigger Module

## Descrizione

Il modulo `power_trigger.py` implementa un sistema di pre-analisi audio che attiva trigger su due canali (sinistro e destro) in base a soglie di ampiezza e frequenza.

## Flusso di Funzionamento

```
Buffer Audio Stereo
    ↓
Power Trigger (Canale Sinistro)  |  Power Trigger (Canale Destro)
    ↓                                    ↓
Trigger Sinistro?                   Trigger Destro?
    ↓                                    ↓
    ├─ Entrambi attivati → TDOA → Detection sul canale più vicino
    ├─ Solo sinistro → Detection solo canale sinistro
    ├─ Solo destro → Detection solo canale destro
    └─ Nessuno → Skip
```

## Componenti Principali

### Classe `PowerTrigger`

Gestisce l'analisi dei trigger su entrambi i canali.

#### Parametri di Configurazione

```python
AMPLITUDE_THRESHOLD = 0.05      # Soglia RMS (da calibrare)
FREQUENCY_THRESHOLD_MIN = 5000  # Frequenza minima (Hz)
FREQUENCY_THRESHOLD_MAX = 25000 # Frequenza massima (Hz)
POWER_THRESHOLD = -40           # Soglia potenza in dB (da calibrare)
```

#### Metodi Principali

- **`check_trigger(signal, channel_name)`**: Verifica se il trigger si attiva per un canale
  - Calcola RMS, potenza in dB e frequenza dominante
  - Ritorna un dizionario con le informazioni del trigger

- **`process_stereo_buffer(left_channel, right_channel)`**: Processa il buffer stereo
  - Analizza entrambi i canali
  - Determina l'azione da intraprendere (TDOA, left_only, right_only, none)
  - Ritorna il risultato con i dettagli

### Funzioni Ausiliarie

- **`run_tdoa_analysis(wav_file_path)`**: Esegue l'analisi TDOA usando `direzione.py`
- **`get_nearest_channel(left, right, direction)`**: Ritorna il canale più vicino alla sorgente

## Utilizzo

### Uso Standalone

```python
from power_trigger import PowerTrigger
import numpy as np

# Inizializza il trigger
sample_rate = 192000
trigger = PowerTrigger(sample_rate)

# Processa il buffer stereo
result = trigger.process_stereo_buffer(left_channel, right_channel)

# Controlla il risultato
if result['action'] == 'tdoa':
    print("Esegui TDOA")
elif result['action'] == 'left_only':
    print("Detection solo canale sinistro")
elif result['action'] == 'right_only':
    print("Detection solo canale destro")
else:
    print("Nessun trigger attivato")
```

### Integrazione con Detector

Usa il file `detector_v3_with_trigger.py` che integra il power trigger nel flusso di detection:

```bash
python3 detector_v3_with_trigger.py
```

## Calibrazione delle Soglie

Le soglie devono essere calibrate in base all'ambiente e ai microfoni utilizzati:

1. **AMPLITUDE_THRESHOLD**: Aumentare se ci sono falsi positivi, diminuire se mancano rilevamenti
2. **POWER_THRESHOLD**: Aumentare per essere più selettivi sul rumore di fondo
3. **FREQUENCY_THRESHOLD_MIN/MAX**: Adattare alla banda di frequenza del target

### Procedura di Calibrazione

1. Registra campioni audio con e senza il target
2. Esegui il power trigger su questi campioni
3. Analizza i valori di RMS, potenza e frequenza dominante
4. Ajusta le soglie per ottenere il miglior trade-off tra sensibilità e specificità

## Output del Power Trigger

```python
{
    'left_triggered': bool,          # Trigger sinistro attivato
    'right_triggered': bool,         # Trigger destro attivato
    'left_info': {
        'triggered': bool,
        'rms': float,
        'power_db': float,
        'dominant_freq': float
    },
    'right_info': {
        'triggered': bool,
        'rms': float,
        'power_db': float,
        'dominant_freq': float
    },
    'action': str,                   # 'tdoa', 'left_only', 'right_only', 'none'
    'channel_to_analyze': str        # 'left', 'right', 'both', 'none'
}
```

## Logging

Il modulo supporta il logging su file. Passa il percorso del file di log al costruttore:

```python
trigger = PowerTrigger(
    sample_rate=192000,
    log_file_path="/home/pi/data/trigger_log.txt"
)
```

## Integrazione con TDOA

Quando entrambi i trigger si attivano:

1. Il buffer stereo viene salvato temporaneamente
2. Viene eseguito `direzione.py` per calcolare TDOA e angolo
3. In base alla direzione, viene selezionato il canale più vicino
4. La detection viene eseguita solo su quel canale

## Note Importanti

- Il power trigger è il primo step della pipeline
- Se nessun trigger si attiva, la detection viene saltata (risparmio computazionale)
- Il TDOA viene eseguito solo se entrambi i trigger si attivano
- La frequenza dominante viene calcolata usando FFT
- Tutti i calcoli sono in tempo reale
