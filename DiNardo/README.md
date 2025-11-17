# DiNardo — Rilevamento in tempo reale su spettrogrammi (TFLite)

## Scopo
Questo modulo esegue un rilevamento in tempo reale a partire dall’audio di ingresso. Il flusso prevede:
- acquisizione audio continua
- costruzione di uno spettrogramma e conversione in immagine in scala di grigi
- filtro opzionale di Sobel verticale
- inferenza con un modello TensorFlow Lite
- logging delle rilevazioni (immagine, audio e valore di confidenza)

## Requisiti principali
- Python 3.x
- Librerie: `numpy`, `scipy`, `Pillow` (PIL), `opencv-python` (cv2), `sounddevice`, `tflite-runtime`
- Dispositivo audio di ingresso accessibile da `sounddevice`

## Struttura dei file
- `config.py`
  Parametri globali di audio, DSP, percorsi e formati di logging.
- `audio_capture.py`
  Acquisizione audio in streaming e buffer scorrevole (sliding window).
- `dsp.py`
  DSP: calcolo spettrogramma, conversione in immagine, filtro di Sobel.
- `inference.py`
  Wrapper del modello TFLite e pre/post-processing I/O.
- `logger.py`
  Salvataggio su filesystem di log, immagini PNG e tracce WAV per ogni rilevazione.
- `main.py`
  Orchestrazione completa: parsing argomenti, acquisizione, DSP, inferenza e logging.

## Parametri chiave (da `config.py`)
- Audio
  - `SAMPLE_RATE_DEFAULT = 192000`
  - `WINDOW_SEC = 0.8` (durata finestra)
  - `HALF_WINDOW = WINDOW_SEC / 2` (passo di scorrimento = 0.4 s)
  - `CHANNELS = 1`
- DSP / Immagine
  - `IMG_WIDTH = 300`, `IMG_HEIGHT = 150`
  - `MIN_FREQ = 5000`, `MAX_FREQ = 25000` (ritaglio in frequenza)
  - `NFFT = 512`, `OVERLAP = 0.5`
- Inferenza
  - `THRESHOLD_DEFAULT = 0.9` (soglia di logging)
- Percorsi e formati
  - `DETECTIONS_DIR = <cartella>/detections`
  - Timestamp: `TIMESTAMP_FMT = '%Y%m%d-%H%M%S.%f'` (usato ai centesimi)
  - Directory data per giorno: `LOG_DATE_FMT = '%Y%m%d'`

## Flusso di esecuzione (pipeline)
1. **Acquisizione e buffering**
    - `audio_capture.capture_stream(...)` apre uno stream di input (selezionabile per indice/nome) a `SAMPLE_RATE_DEFAULT`, `CHANNELS`.
    - Lo stream produce blocchi di durata `HALF_WINDOW` secondi (hop). Il `blocksize` in frame è circa `HALF_WINDOW * SAMPLE_RATE_DEFAULT`.
    - `audio_capture.rolling_buffer(...)` mantiene un ring-buffer e costruisce finestre di lunghezza `WINDOW_SEC` con overlap 50% (passo = `HALF_WINDOW`).
    - Ogni finestra contiene ~`WINDOW_SEC * SAMPLE_RATE_DEFAULT` campioni.

2. **DSP: spettrogramma**
    - `dsp.make_spectrogram(...)` calcola lo spettrogramma con finestra Hann, `NFFT` e `OVERLAP` (overlap fra frame interni allo spettrogramma, distinto dall’overlap temporale del buffering).
    - Output: matrice di magnitudini e vettori `freqs`. Le magnitudini sono convertite in dB con offset numerico `+1e-12` per evitare `log(0)`.
    - Le bande fuori interesse vengono escluse individuando gli indici di `freqs` compresi in `[MIN_FREQ, MAX_FREQ]`.

3. **Imaging**
    - `dsp.spectrogram_to_image(...)` effettua: crop in frequenza, normalizzazione per-finestra su [0,1], scaling a [0,255], inversione verticale per avere frequenze basse in basso.
    - Ridimensiona a `IMG_WIDTH × IMG_HEIGHT` e restituisce un’immagine PIL in scala di grigi (`mode='L'`).

4. **Filtro opzionale (Sobel verticale)**
    - `dsp.apply_sobel_vertical(image)` evidenzia pattern verticali (tipici delle armoniche/pattern impulsivi), con kernel 7.
    - L’uscita viene rinormalizzata su [0,255] preservando il tipo `L`.

5. **Inferenza TFLite**
    - `inference.TFLiteModel.predict(image)` prepara il tensore: converte in `float32`, trasposta H×W → W×H, aggiunge batch e canale: forma `(1, W, H, 1)`.
    - Esegue `invoke()` e produce una confidenza (float scalare). I thread del runtime sono configurabili da CLI (`--num_threads`).

6. **Decisione e logging**
    - Se confidenza ≥ soglia (CLI `--threshold`, default `THRESHOLD_DEFAULT`), `logger.DetectionLogger.log(...)` salva:
      - riga `timestamp\tconfidenza` in `detections/<YYYYMMDD>/detections.log` (formati da `TIMESTAMP_FMT`, `LOG_DATE_FMT`)
      - PNG e WAV della finestra corrente in `detections/<YYYYMMDD>/data/` con lo stesso timestamp.

7. **Cadenza temporale**
    - Il ciclo principale rispetta la cadenza di `HALF_WINDOW`: a fine iterazione attende il tempo residuo per mantenere throughput costante (sliding a 50%).

### Note operative
- **Prestazioni**: `NFFT` maggiore migliora la risoluzione in frequenza ma aumenta il costo; `IMG_WIDTH/IMG_HEIGHT` impattano l’I/O del modello.
- **Dispositivo audio**: selezionabile via `--device` (indice o nome). Verificare la compatibilità con sample rate elevati.
- **Riproducibilità**: i file PNG/WAV e il log condividono lo stesso timestamp, utile per correlare i dati.

## Dettagli per file
- `config.py`
  - Parametri raggruppati per ambito (audio, DSP, inferenza, percorsi, formati).
  - `DETECTIONS_DIR` è relativa alla cartella del modulo.

- `audio_capture.py`
  - `capture_stream(samplerate, channels, device=None)` apre un `RawInputStream` con `dtype='float32'`, `blocksize = HALF_WINDOW*samplerate`.
  - Se `device` è impostato, viene selezionato come input; il valore può essere indice o nome.
  - `rolling_buffer(blocks, samplerate)` produce finestre lunghe `WINDOW_SEC`, con scorrimento di `HALF_WINDOW`.

- `dsp.py`
  - `make_spectrogram(signal, sr, nfft, overlap)` usa `scipy.signal.spectrogram` con finestra Hann; taglia lo spettro a `nfft//2` (componenti positive) e ritorna `20*log10(|S|+1e-12)`.
  - `spectrogram_to_image(Sxx_db, freqs, ...)` ritaglia in frequenza, normalizza 0–1, scala 0–255, inverte verticalmente e ridimensiona con bilineare.
  - `apply_sobel_vertical(image)` applica `cv2.Sobel(dx=0, dy=1, ksize=7)` e normalizza con `cv2.normalize`.

- `inference.py`
  - `TFLiteModel(model_path, num_threads)` inizializza l’`Interpreter`, alloca i tensori e memorizza dettagli di input/output.
  - `predict(image)` si aspetta un’immagine `L` (grayscale). Prepara il tensore come `(1, W, H, 1)` per il modello; la confidenza è `float`.

- `logger.py`
  - `DetectionLogger(threshold)` memorizza la soglia di triggering per il logging.
  - `log(prediction, image, audio_block, sr)` crea la cartella giornaliera, appende al log testuale e salva:
    - PNG dello spettrogramma/filtro con timestamp
    - WAV dell’audio (int16, scaling da float32 a piena dinamica)

- `main.py`
  - Argomenti CLI:
    - `model_path` (posizionale): percorso al modello `.tflite`
    - `--num_threads` (int, default 1)
    - `--sobel` (`y`|`n`, default `n`)
    - `--samplerate` (int, default `SAMPLE_RATE_DEFAULT`)
    - `--threshold` (float, default `THRESHOLD_DEFAULT`)
    - `--device` (indice o nome del dispositivo di input)
  - Loop: acquisizione → DSP → eventuale Sobel → inferenza → logging sopra soglia → attesa per rispettare cadenza `HALF_WINDOW`.

## Utilizzo
Esempio di esecuzione:

```bash
python3 main.py /percorso/al/modello.tflite \
  --num_threads 2 \
  --samplerate 192000 \
  --threshold 0.9 \
  --sobel n \
  --device 0
```

Note:
- Il parametro `--device` accetta indice o nome del dispositivo di input supportato dalla piattaforma audio (nel codice è previsto l’uso con ALSA; regolare in base al sistema in uso).
- La cartella `detections/` viene creata automaticamente accanto ai sorgenti e organizzata per giorno (`YYYYMMDD`).

## Output generati
- `detections/<YYYYMMDD>/detections.log` con righe: `YYYYMMDD-HHMMSS.ccc\t<confidenza>`
- `detections/<YYYYMMDD>/data/<timestamp>.png` immagine usata in inferenza
- `detections/<YYYYMMDD>/data/<timestamp>.wav` audio della finestra corrispondente

## Limitazioni e note
- Il modello TFLite deve essere compatibile con input grayscale a singolo canale e dimensioni `(W, H)` dopo trasposizione; adattare `spectrogram_to_image` e la preparazione del tensore se il modello richiede forme diverse.
- La frequenza di campionamento elevata (default 192 kHz) richiede dispositivi e driver adeguati.
