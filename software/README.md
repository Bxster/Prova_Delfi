# Manuale Operativo Software (DELFI)

## Panoramica

Questo manuale descrive il funzionamento del software di rilevamento DELFI installato su Raspberry Pi, includendo il flusso con Power Trigger, TDOA e classificazione via TensorFlow Lite. I riferimenti sono aggiornati alla struttura attuale del repository e ai path reali su dispositivo.

## Architettura

- Power Trigger (`power_trigger.py`)
- Detector con integrazione Trigger/TDOA (`detector_v3_with_trigger.py`)
- Task server TFLite (DSP + inferenza) (`task1_v3.py`)
- Analisi direzione/TDOA (`direzione.py`)
- Ring buffer server audio JACK (`jack-ring-socket-server`)
- Script di servizio (`run.sh`, `det.sh`, `start_jack_ring_server.sh`, `stop_all.sh`)

## Integrazione tra i file

- **Orchestrazione (`run.sh`)**
  - Configura HiFiBerry, avvia `jackd`, avvia `jack-ring-socket-server` (porta 8888), avvia `task1_v3.py` (server TCP), quindi lancia `det.sh` che esegue il detector.

- **Acquisizione audio**
  - `jack-ring-socket-server` espone via TCP i blocchi stereo float32 su `RING_HOST:RING_PORT` (default `127.0.0.1:8888`).
  - `detector_v3_with_trigger.py` si collega al ring server, invia i comandi (`nframes`, `len`, `rate`, `seconds`, `dump`) e riceve il buffer stereo.

- **Trigger e direzione**
  - `detector_v3_with_trigger.py` costruisce finestre rolling (0.8 s, hop 0.4 s) e invoca `PowerTrigger` (`power_trigger.py`) sul buffer stereo per decidere l'azione: `none`, `left_only`, `right_only`, `tdoa`.
  - Se `tdoa`: crea una finestra breve stereo e chiama `run_tdoa_analysis` (in `power_trigger.py`) che esegue `direzione.py` via `subprocess` usando il path da `config.DIREZIONE_SCRIPT`. L'output JSON di `direzione.py` viene parsato per determinare il canale più vicino.

- **Inference TFLite (scoring)**
  - Il detector invia il blocco mono selezionato a `task1_v3.py` via TCP su `127.0.0.1:<SERVER_PORT_BASE>` (default `12001`).
  - Protocollo: header `bitrate,file_size,data_size` → `ACK` → payload audio → risposta con `score` (float in testo, terminato da newline).
  - `task1_v3.py` calcola spettrogramma/immagine, esegue inferenza TFLite e restituisce lo score.

- **Soglia e salvataggio**
  - Il detector confronta lo `score` con `config.DETECTION_THRESHOLD`; se superato, salva WAV stereo in `config.DETECTIONS_DIR`.

- **Script di servizio**
  - `det.sh` avvia il detector con il Python del venv.
  - `stop_all.sh` termina in sicurezza `detector`, `task1_v3.py`, `jack-ring-socket-server` e `jackd` cercando i processi per pattern.

- **Configurazione centralizzata**
  - `config.py` definisce percorsi (modello, script, log, detections), parametri di rete (host/porte), finestre DSP, soglie trigger/detection e opzioni TDOA/UART. Tutti i moduli importano da qui.

## Requisiti

- Raspberry Pi con HiFiBerry DAC+ ADC Pro
- JACK, ALSA configurati
- Python venv: `/home/delfi/Prova_Delfi/.venv/`
- Modello TFLite presente: `software/V_TFLite/model_6_ott.tflite`

## Percorsi e File Chiave in Raspberry Pi

- Radice progetto: `/home/delfi/Prova_Delfi`
- Software: `/home/delfi/Prova_Delfi/software/V_TFLite`
- Log: `/home/delfi/Prova_Delfi/logs/`
- Detections WAV: `/home/delfi/Prova_Delfi/logs/Detections/`
- Configurazione: `software/V_TFLite/config.py`

## Parametri Principali (config.py)

- Power Trigger
  - `PROMINENCE_BAND_MIN_HZ = 4000`
  - `PROMINENCE_BAND_MAX_HZ = 26000`
  - `PROMINENCE_THRESHOLD_DB = 20.0`
- TDOA/Direzione
  - `DIREZIONE_SCRIPT = "/home/delfi/Prova_Delfi/software/V_TFLite/direzione.py"`
  - `TDOA_TIMEOUT_SEC = 10`
  - `TDOA_WIN_SEC = 0.04`
  - `SPEED_OF_SOUND = 1460`, `MICROPHONE_DISTANCE = 0.46`
  - `HIGH_PASS_CUTOFF_HZ = 1000`
  - `ENABLE_UART = False`
- Networking/IPC
  - `RING_HOST = "127.0.0.1"`, `RING_PORT = 8888`
  - `SERVER_PORT_BASE = 12001`
- Detection
  - `DETECTION_THRESHOLD = 0.7`
- DSP/Imaging
  - `WINDOW_SEC = 0.8`, `HALF_WINDOW = 0.4`
  - `IMG_WIDTH = 300`, `IMG_HEIGHT = 150`
  - `MIN_FREQ = 5000`, `MAX_FREQ = 25000`
  - `NFFT = 512`, `OVERLAP = 0.5`

## Avvio Rapido (tutto automatico)

1. Avviare lo script `run.sh` (gestisce JACK, ring server, task e detector):
   ```bash
   bash /home/delfi/Prova_Delfi/software/V_TFLite/run.sh
   ```
2. Lo script:
   - configura HiFiBerry
   - avvia JACK (192 kHz)
   - avvia ring server su 8888
   - avvia `task1_v3.py`
   - avvia il detector tramite `det.sh`

Per arrestare tutti i processi:
```bash
bash /home/delfi/Prova_Delfi/software/V_TFLite/stop_all.sh
```

## Avvio Manuale (passo-passo)

1. JACK + Ring server
   ```bash
   /usr/bin/jackd -R -dalsa -dhw:<card_id> -p512 -r192000 -n7 &
   /home/delfi/Prova_Delfi/software/jack-ring-socket-server/jack-ring-socket-server --port 8888 --seconds 2 &
   ```
2. Task server TFLite
   ```bash
   /home/delfi/Prova_Delfi/.venv/bin/python3 /home/delfi/Prova_Delfi/software/V_TFLite/task1_v3.py &
   ```
3. Detector con Power Trigger + TDOA
   ```bash
   /home/delfi/Prova_Delfi/software/V_TFLite/det.sh
   # oppure
   /home/delfi/Prova_Delfi/.venv/bin/python3 /home/delfi/Prova_Delfi/software/V_TFLite/detector_v3_with_trigger.py
   ```

## Flusso di Elaborazione

- ring server fornisce blocchi stereo (float32)
- detector costruisce finestre 0.8 s (hop 0.4 s)
- Power Trigger valuta ciascun canale e decide:
  - `none`: salta la detection
  - `left_only`/`right_only`: detection sul canale attivo
  - `tdoa`: salva finestra stereo corta (`TDOA_WIN_SEC`), esegue `direzione.py`, sceglie il canale più vicino, effettua detection
- se score ≥ `DETECTION_THRESHOLD`, salva WAV stereo in `logs/Detections/`

## Esempi d'Uso

- TDOA su file WAV
  ```bash
  /home/delfi/Prova_Delfi/.venv/bin/python3 /home/delfi/Prova_Delfi/software/V_TFLite/direzione.py '/home/delfi/Prova_Delfi/software/Audio/0gradi.wav'
  ```
- Test rapido Power Trigger
  ```bash
  /home/delfi/Prova_Delfi/.venv/bin/python3 /home/delfi/Prova_Delfi/software/V_TFLite/test_power_trigger.py --stereo '/home/delfi/Prova_Delfi/software/Audio/centro.wav'
  # oppure con due mono
  /home/delfi/Prova_Delfi/.venv/bin/python3 /home/delfi/Prova_Delfi/software/V_TFLite/test_power_trigger.py --left '/home/delfi/Prova_Delfi/software/Audio/left.wav' --right '/home/delfi/Prova_Delfi/software/Audio/right.wav'
  ```

## Logging e Output

- Log detector: `/home/delfi/Prova_Delfi/logs/detection_log.txt`
- Detections: `/home/delfi/Prova_Delfi/logs/Detections/*.wav`
- Il Power Trigger può loggare su file se `log_file_path` è fornito al costruttore

- **Detector (`detector_v3_with_trigger.py`)**
  - File di log: definito in `config.LOG_FILE_PATH` (default: `/home/delfi/Prova_Delfi/logs/detection_log.txt`).
  - Scrive voci come: `LEN: <ncampioni>`, `CONNECTION PORT: <porta>`, blocco `--- Trigger Result ---` con `Action` e `Channel to analyze`, `Detection: <score>`, messaggi operativi (`Performing TDOA analysis...`, `No triggers activated, skipping detection`), errori/exception (`ERRORE send_wavefile: ...`, `Fatal error: ...`, `Program interrupted by user`).
  - Salvataggio WAV su detection: directory `config.DETECTIONS_DIR` (default: `/home/delfi/Prova_Delfi/logs/Detections/`), nome file `YYYY-mm-dd HH:MM:SS.wav` (stereo, SR del campione).
  - Integra il Power Trigger passando lo stesso `log_file_path` per unificare i log.

- **Power Trigger (`power_trigger.py`)**
  - Se `log_file_path` è fornito, usa un `FileHandler` sullo stesso file del detector.
  - Esempi di righe: `[LEFT] PeakFreq: <Hz>, Prom: <dB>, Triggered: <bool>` e decisioni: `Both triggers activated -> Performing TDOA`, `Left trigger only -> ...`, `No triggers activated -> Skipping detection`.

- **TDOA/Direzione (`direzione.py`)**
  - Output su stdout: una riga descrittiva e una riga JSON `{"direzione": "sinistra|destra|centro", "angolo": <gradi>}`.
  - Integrazione: il detector invoca `direzione.py` tramite `subprocess` (funzione `run_tdoa_analysis`), cattura stdout/stderr, prova a parsare il JSON e registra nel log del detector la voce `TDOA Result: {...}`.
  - File temporanei: il detector crea `/tmp/tdoa_temp_<timestamp>.wav` per la finestra breve TDOA; non vengono rimossi automaticamente.

- **Task server TFLite (`task1_v3.py`)**
  - Log su stdout: `Serving on ('127.0.0.1', <porta>)`, `Received <header> from (<client>, <port>)`.
  - IPC: server TCP su `127.0.0.1:<config.SERVER_PORT_BASE>` (default `12001`). Protocollo: il client invia header `bitrate,file_size,data_size`, riceve `ACK`, quindi invia il buffer mono; il server risponde con lo `score` float terminato da `\n`.
  - Non scrive file di log dedicati.

- **Ring buffer server JACK (`jack-ring-socket-server`)**
  - Fornisce blocchi stereo via TCP su porta `config.RING_PORT` (default `8888`). Comandi usati dal detector: `nframes`, `len`, `rate`, `seconds`, `dump`.
  - Il detector registra su log almeno `LEN: <nframe_stereo>` per ogni fetch; eventuali messaggi del ring server vanno su stdout/stderr del processo.

- **Script di servizio**
  - `run.sh`: stampa su stdout lo stato di avvio componenti; scrive un marker in `/home/delfi/flag.txt` (`"run.sh avviato"`).
  - `det.sh`: avvia il detector e stampa `Detector.py avviato.` su stdout.
  - `stop_all.sh`: stampa su stdout le fasi di terminazione processi; non genera log file.

- **Riepilogo integrazione log/output**
  - Unico file di log consolidato: `detection_log.txt` (detector + power trigger + note TDOA).
  - Output modello (score) transita via TCP tra detector e task server, non viene salvato a file salvo quando supera `DETECTION_THRESHOLD`, caso in cui il detector salva il WAV in `logs/Detections/`.
  - La stima di direzione TDOA è riportata nel log del detector e disponibile anche su stdout del processo `direzione.py` (eventuale invio JSON via UART se `ENABLE_UART=True`).

## Troubleshooting

- Nessun suono in ingresso
  - Verificare HiFiBerry e parametri `amixer`
  - Controllare che JACK sia in esecuzione e a 192 kHz
- Detector non riceve dati
  - Verificare ring server (porta 8888) e variabili `RING_HOST/RING_PORT`
- Score sempre basso
  - Controllare `MIN_FREQ/MAX_FREQ`, `NFFT`, `DETECTION_THRESHOLD`
  - Verificare modello `MODEL_PATH`
- TDOA fallisce o lento
  - Aumentare `TDOA_TIMEOUT_SEC`
  - Verificare `TDOA_WIN_SEC` e qualità del segnale

## Note

- Tutti gli script Python usano l’interprete del venv: `/home/delfi/Prova_Delfi/.venv/bin/python3`
- Le impostazioni si modificano in `software/V_TFLite/config.py`
