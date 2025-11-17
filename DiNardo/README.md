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
1. `audio_capture.capture_stream(...)` apre uno stream di input (dispositivo selezionabile per indice o nome) e fornisce blocchi di durata `HALF_WINDOW`.
2. `audio_capture.rolling_buffer(...)` costruisce una finestra di lunghezza `WINDOW_SEC`, che scorre di `HALF_WINDOW` (overlap 50%).
3. `dsp.make_spectrogram(...)` calcola lo spettrogramma (finestra Hann, `NFFT`, `OVERLAP`) e ritorna l’ampiezza in dB e i vettori di frequenza.
4. `dsp.spectrogram_to_image(...)` ritaglia la banda `[MIN_FREQ, MAX_FREQ]`, normalizza su [0, 255], inverte l’asse Y e ridimensiona a `IMG_WIDTH × IMG_HEIGHT` come immagine PIL in scala di grigi (`L`).
5. Opzionale: `dsp.apply_sobel_vertical(image)` applica Sobel verticale (kernel 7), normalizza su [0, 255] e restituisce un’immagine `L`.
6. `inference.TFLiteModel.predict(image)` converte l’immagine in `float32`, trasposta (H×W → W×H), aggiunge dimensioni batch e canale: forma `(1, W, H, 1)`, esegue `invoke()` e restituisce uno scalare di confidenza.
7. Se la confidenza ≥ soglia, `logger.DetectionLogger.log(...)`:
   - appende a `detections/<YYYYMMDD>/detections.log` la riga `timestamp\tpredizione`
   - salva immagine PNG e audio WAV in `detections/<YYYYMMDD>/data/` con nome timestamp

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
