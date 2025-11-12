# :dolphin: LIFE DELFI: DEep Life Acoustic Finder

LIFE DELFI è un sistema avanzato di rilevamento, analisi e interazione con sorgenti acustiche subacquee, sviluppato come parte del Corso di Laboratorio di Meccatronica - Università Politecnica delle Marche.

<div align="center">
  <img src="https://github.com/LabMACS/24.25_Marrone/blob/main/image/logo.png" alt="logo">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/Raspberry%20Pi-Zero%202W-cc0000?logo=raspberry-pi&logoColor=white" alt="Raspberry Pi Zero 2W">
  <img src="https://img.shields.io/badge/Made%20with-Python%203.7%2B-blue?logo=python&logoColor=white" alt="Made with Python 3.7+">
  <img src="https://img.shields.io/badge/Made%20with-Shell-4EAA25?logo=gnu-bash&logoColor=white" alt="Shell Scripts">
  <img src="https://img.shields.io/badge/Made%20with-C-00599C?logo=c&logoColor=white" alt="C Language">
</div>

## :bookmark_tabs: Indice

1. [:dolphin: Che cos'è LIFE DELFI](#che-cose-life-delfi)
2. [:hammer_and_wrench: Requisiti Hardware](#requisiti-hardware)
3. [:computer: Requisiti Software](#requisiti-software)
4. [:file_folder: Struttura Repository](#struttura-repository)
5. [:gear: Installazione](#installazione)
6. [:test_tube: Test](#test)
7. [:busts_in_silhouette: Utilizzo Utente](#utilizzo-utente)
   - [:robot: AI Detector](#ai-detector)
   - [:studio_microphone: Audio Recording](#audio-recording)
   - [:loud_sound: Audio Output](#audio-output)
   - [:file_folder: Data Archive](#data-archive)
   - [:computer: Esempio d'utilizzo](#esempio-utilizzo)
8. [:wrench: Utilizzo Utente Esperto](#utilizzo-utente-esperto)
9. [:bar_chart: Gantt](#gantt)
10. [:clipboard: TC/TP](#tc)
11. [🎯 KPI](#kpi)
12. [:handshake: Contributors](#contributors)

<h2 id="che-cose-life-delfi">:dolphin: Che cos'è LIFE DELFI</h2>

Il progetto Life DELFI, cofinanziato dal Programma Life dell’Unione Europea, affronta la crescente problematica delle interazioni tra delfini e pesca professionale, con l’obiettivo di ridurre catture accidentali e conflitti tra pescatori e cetacei. In questo ambito, il nostro lavoro ruota attorno alla concezione e realizzazione di DELFi, un sistema innovativo che unisce ricerca scientifica, tecnologie avanzate e sostenibilità economica, promuovendo una convivenza armoniosa tra la conservazione marina e l’industria della pesca.

### :building_construction: Architettura e Funzionamento
DELFI si basa su idrofoni collegati a un Raspberry Pi Zero 2W, i quali consentono di raccogliere ed elaborare in tempo reale i segnali acustici subacquei. Un algoritmo di calcolo del TDOA (Time Difference of Arrival) determina l’orientamento della sorgente sonora, permettendo di emettere un suono nella direzione individuata. L’hardware è integrato nella “testa” di un pesce martello robotico, costituita da un tubo di plastica concavo di circa 15 x 40 cm.

![disp](https://github.com/LabMACS/24.25_Marrone/blob/main/image/dispositivo.jpg)

### :star: Caratteristiche Principali
- **Localizzazione**\
DELFi sfrutta il TDOA per identificare la posizione e la direzione d’arrivo dei suoni prodotti, in particolare quelli emessi dal delfino tursiope.
- **Classificazione Sonora**\
Un sistema basato su Machine Learning (reti neurali e modelli TensorFlow Lite) riconosce i segnali acustici dei delfini da altre fonti sottomarine.
- **Risposta Comportamentale**\
Il dispositivo può emettere suoni di possibili predatori (ad esempio, orche) per studiare la reazione e i comportamenti dei cetacei.
- **Interfaccia User-Friendly**\
Un’interfaccia grafica accessibile via Wi-Fi semplifica il lavoro dell'utente finale.

Grazie a queste funzionalità, DELFi non solo offre un approccio tecnologico avanzato ed economico alla protezione dei delfini (riducendo le catture accidentali e salvaguardando l’attrezzatura da pesca), ma risulta anche perfettamente in linea con gli obiettivi di Life DELFI, contribuendo a modelli di gestione sostenibili che tutelino sia le popolazioni di delfini sia gli interessi dei pescatori.

<h2 id="requisiti-hardware">:hammer_and_wrench: Requisiti Hardware</h2>

Di seguito sono elencati i componenti hardware necessari per la realizzazione del sistema:

- **Raspberry Pi Zero 2W**
  - Processore: ARM quad-core a 64 bit (1 GHz)
  - RAM: 512 MB SDRAM
   - - Connettività: LAN wireless 802.11 b/g/n 2,4 GHz e Bluetooth 4.2 (BLE)
   - - Porte: 1 porta micro-HDMI e 2 micro-USB
   - - GPIO: 40 pin disponibili per l’espansione (alimentazione e segnali di controllo)

- **HiFiBerry DAC+ ADC Pro**
   - Interfaccia: connessione diretta al connettore GPIO del Raspberry Pi
   - Alimentazione: sfrutta direttamente l’alimentazione fornita dal Raspberry Pi
   - Caratteristiche audio:
      - ADC 192 kHz/24 bit su due canali di ingresso
      - Preamplificatore con guadagno di 40 dB integrato

![hardware](https://github.com/LabMACS/24.25_Marrone/blob/main/image/rasp.png)

- **Preamplificatore**
   - Stadi di amplificazione:
      1. Amplificatore di tensione a guadagno unitario
      2. Filtro passa alto (Fc = 723 Hz) con guadagno di 10
      3. Stadio con guadagno variabile fino a 10 (mediante potenziometro)
   - Guadagno totale: fino a 100 dB
   - Alimentazione: 3 V con terra virtuale (VCC/2) per supportare l’alimentazione a binario singolo

- **Dischi Piezoelettrici (Idrofoni)**
   - Tipologia: dischi monofacciali da 27 mm
   - Configurazione: due canali stereo, ciascuno composto da due dischi disposti perpendicolarmente all’interno di un contenitore di plastica
   - Guadagno aggiuntivo: circuito preamplificatore SMD dedicato (circa 30 dB)

- **Sistema di Emissione Sonora**
   - Convertitore DC-DC Step-Up:
      - Aumenta la tensione da 5 V (power bank) a 12 V per l’alimentazione dell’amplificatore audio
   - Amplificatore Audio (TDA2030A):
      - Potenza in uscita: 15 W
      - Alimentazione: 12 V DC (forniti dal convertitore Step-Up)
   - Controllo Emissione: gestito direttamente dal Raspberry Pi Zero 2W tramite due relè indipendenti
   - Segnale Audio di Ingresso: fornito dal DAC dell’HiFiBerry

- **Assembly Board (PCB)**
   - Struttura portante per il posizionamento ottimale di tutti i componenti (Raspberry Pi, HiFiBerry, preamplificatori, relè, ecc.)
   - Connettori:
      - Doppio connettore a 40 pin per collegare il Raspberry Pi all’HiFiBerry
      - 4 porte GPIO e 2 connessioni I2C aggiuntive
      - Pin di alimentazione 5 V e GND dal Raspberry Pi Zero 2W (impiegati anche per il modulo relè)
   - Controllo Relè: il pin 11 (GPIO17) del Raspberry Pi Zero 2W abilita o disabilita i due relè
 
![hardware](https://github.com/LabMACS/24.25_Marrone/blob/main/image/emissione.jpeg)

Questi componenti, opportunamente integrati, costituiscono l’intero sistema di acquisizione ed emissione audio basato su Raspberry Pi Zero 2W e HiFiBerry. L’assembly board facilita la connessione e la disposizione fisica di tutte le parti. 

> Nota: Le specifiche complete dei componenti (idrofoni, amplificatori, schemi di collegamento, etc.) sono disponibili nella cartella `docs/` del repository nel documento `documentazione.pdf`.

<h2 id="requisiti-software">:computer: Requisiti Software</h2>

- **Sistema Operativo**
   - [Raspberry Pi OS Lite (32-bit)](https://www.raspberrypi.com/software/operating-systems/#raspberry-pi-os-legacy)
      - Consigliato per l’ambiente embedded su Raspberry Pi, ottimizzato per consumi e risorse ridotte.
- **Librerie Audio**
   - ALSA (Advanced Linux Sound Architecture) come libreria principale per la gestione di ingressi/uscite audio.
   - Jack Audio Connection Kit (opzionale) se si vuole sfruttare un server di connessione audio avanzato.
- **Python**
   - Python 3 (versione ≥ 3.7): consigliato l’utilizzo di ambienti virtuali (venv) per isolare le dipendenze.
   - Librerie:
      - [numpy](https://numpy.org/install/), [scipy](https://scipy.org/install/#installing-with-pip) per l’elaborazione numerica e di segnale.
      - [tensorflow-lite](https://pypi.org/project/tflite/) per l’inferenza dei modelli di Machine Learning.
      - Altre librerie di supporto (es. [pyserial](https://pypi.org/project/pyserial/) per la comunicazione UART).
- **Compilatori e Tool di Build (per Componenti C)**
   - gcc: compilatore C indispensabile per eventuali moduli o estensioni scritti in C.
   - make: gestore di build per progetti con Makefile.
 
> Nota: Per maggiori dettagli relativi all’installazione e all'utilizzo fare riferimento al `manuale_sviluppatore.pdf` disponibile nella cartella `docs/` del repository.

<h2 id="struttura-repository">:open_file_folder: Struttura repository</h2>

```
├── device2/
│   ├── ssh.txt                     # Fle per configurazione ssh secondo dispositivo
│   ├── wpa_supplicant.conf.txt     # Fle per configurazione Wi-Fi secondo dispositivo
│── docs/
│   ├── Deliverable1.xlsx           # Deliverable 1
│   ├── Deliverable2.pdf            # Deliverable 2
│   ├── Deliverable3.pdf            # Deliverable 3
│   ├── Deliverable4.pdf            # Deliverable 4
│   ├── Presentazione.pptx          # Presentazione del progetto
│   ├── Req_GANTT.pptx              # Requisiti e GANTT
│   ├── manuale_utente.pdf          # Manuale per l'utente
│   ├── manuale_operatore.pdf       # Manuale per l'utente operatore
│   ├── manuale_sviluppatore.pdf    # Manuale per l'utente sviluppatore
│   ├── documentazione.pdf          # Documentazione
│   ├── stato_dell_arte.pdf         # Relazione sullo stato dell'arte
├── image/
│   ├── imager.png                  # Raspberry Pi Imager
│   ├── interfaccia.png             # Interfaccia grafica
│   ├── dispositivo.jpg             # Dispositivo assemblato
│   ├── rasp.png                    # Raspberry + Hi-FiBerry
│   ├── emissione.jpeg              # Modulo emissione
│   ├── esempio1.png                # Esempio utilizzo modulo recording 1
│   ├── esempio2.png                # Esempio utilizzo modulo recording 2
│   ├── gantt.png                   # Gantt
│   ├── emissione.jpeg              # Modulo emissione
│   ├── logo.png              # Logo DELFI
├── software/
│   ├── cgi-bin/                    # Script Bash per il controllo del sistema
│   ├── Ecolocalizzazione/          # Modulo per il rilevamento sonoro
│       ├── Audio/                  # Audio di test
│       ├── direzione.py            # Script per la localizzazione della sorgente
│   ├── jack-ring-socket-server/    # Server per la registrazione audio stereo
│   ├── V_TFLite/                   # Algoritmi di elaborazione del segnale
├── delfi.iso.zip                   # Immagine compressa del sistema operativo custom
└── README.md                       # Documentazione del progetto
```

<h2 id="installazione">:gear: Installazione</h2>

Per avviare il sistema con l’immagine custom, seguire questi passaggi:

1. **:inbox_tray: Download Immagine**\
Scaricare il file `delfi.iso.zip` all’interno del repository.
2. **:floppy_disk: Preparazione SD**\
Utilizzare [Raspberry Pi Imager](https://www.raspberrypi.com/software/) o un software equivalente.

    - Aprire **Raspberry Pi Imager**
    - Selezionare delfi.iso come sistema operativo.
    - Selezionare la SD card come destinazione.
    - Avviare la scrittura.
 
4. **:rocket: Avvio su Raspberry Pi**\
Inserire la SD card nel Raspberry Pi e accendere il dispositivo. Il sistema si avvierà con l’immagine personalizzata.

![imager](https://github.com/LabMACS/24.25_Marrone/blob/main/image/imager.png)

Questa configurazione garantisce la corretta esecuzione delle funzionalità di registrazione, analisi e trasmissione dell’audio.

<h2 id="test">:test_tube: Test</h2>

Sono disponibili diversi test per verificare il corretto funzionamento del modulo di localizzazione senza richiedere l’installazione del sistema operativo custom.

### :clipboard: Requisiti:

- `python3` installato sul sistema.
- File audio stereo in formato `.wav` come input per la localizzazione.

### :computer: Esempio di utilizzo

1. Posizionarsi nella directory del progetto:
   ```bash
   cd software/Ecolocalizzazione
   ```
   
2. Eseguire lo script `direzione.py` passando un file audio in input:
   ```bash
   python3 direzione.py '<percorso_audio>'
   ```
   
   Se non si dispone di un file audio personalizzato, utilizzare quelli presenti nella cartella `Audio/` (es: `0gradi.wav`):
   ```bash
   python3 direzione.py 'Audio/0gradi.wav'
   ```

### :mag_right: Risultati

Il risultato della localizzazione sarà visualizzato nel terminale, ad esempio:
```java
Il suono arriva esattamente dal centro (0-3 gradi)
```

<h2 id="utilizzo-utente">:busts_in_silhouette: Utilizzo utente</h2>

Dopo l’avvio del Raspberry Pi con l’immagine custom, verrà creata automaticamente una rete Wi-Fi denominata AIDD, accessibile tramite PC o smartphone (password: delfi2024). Una volta connessi, aprire il browser e navigare all’indirizzo:
```java
http://10.0.0.1
```
Da qui, si potranno utilizzare le principali funzionalità:
1. **Registrazione e Analisi in Tempo Reale**
2. **Localizzazione della Sorgente Sonora**
3. **Emissione Audio**
4. **Visualizzazione dei Risultati e Log**
5. **Spegnimento del Dispositivo**

![interfaccia](https://github.com/LabMACS/24.25_Marrone/blob/main/image/interfaccia.png)

Di seguito, alcune delle funzionalità disponibili tramite interfaccia:

<h3 id="ai-detector">:robot: AI Detector</h2>

1. **:microphone: Acquisizione Audio**
   - L’acquisizione avviene tramite `JACK Audio Connection Kit`.
   - I dati vengono gestiti da un buffer circolare che separa i canali (sinistro e destro).

2. **:gear: Elaborazione e Trasferimento**
   - I dati audio sono inviati via socket TCP a un client Python.
   - Il segnale viene suddiviso in blocchi di 0,6 secondi.
   - Ogni blocco viene segmentato ulteriormente in blocchi da 0,2 secondi per l’elaborazione multithreading.
   - Viene generata una spettrogramma per ogni blocco, convertito in scala di grigi.

3. **:brain: Inferenza (TensorFlow Lite)**
   - Ciascuno spettrogramma viene processato da un modello TFLite.
   - L’elaborazione avviene in parallelo su tre client.
   - Se la probabilità media di rilevazione supera 0,5, si attiva la localizzazione.
   - La direzione calcolata viene utilizzata per emettere un suono verso la sorgente rilevata.
   - I risultati sono inviati in formato JSON a un secondo dispositivo tramite `UART`.

**Diagramma delle sequenze:**
<div align="center">
  <img src="https://github.com/LabMACS/24.25_Marrone/blob/main/image/sequenze_ai.png" alt="seq1", width=85%>
</div>

<h3 id="audio-recording">:studio_microphone: Audio Recording</h2>

- Registra 2 secondi di audio, elabora per 4 secondi, poi ripete il ciclo.
- Analizza i segnali di entrambi i canali per ricavare l’orientamento della sorgente usando la cross-correlazione dei loro spettrogrammi.
- Stima il TDOA (Time Difference of Arrival) per individuare la direzione del suono.

**Diagramma delle sequenze:**

<div align="center">
  <img src="https://github.com/LabMACS/24.25_Marrone/blob/main/image/sequenze_rec.png" alt="seq2" width=70%>
</div>

<h3 id="audio-output">:loud_sound: Audio Output</h2>

- Emette un audio di 30 secondi denominato orca_finale.wav, che simula il verso di un’orca.
- L’emissione avviene in stereo, ma due relè permettono di controllare i canali in modo indipendente.
- Utile per studi comportamentali su animali marini, simulando la presenza di predatori.

<h3 id="data-archive">:file_folder: Data Archive</h2>

Organizza e visualizza i file audio in due aree:

1. **Sezione di Registrazione**
   - Elenco dei file .wav acquisiti.
   - File di testo associato che registra la direzione acustica calcolata.

2. **Sottosezione di Detection**
   - Contiene i file elaborati dal sistema di rilevamento.
   - File di testo che specifica la validità della rilevazione per ogni traccia audio.

<h3 id="esempio-utilizzo">:computer: Esempio d'utilizzo</h2>

1. Avvio della registrazione:
   - Dopo aver effettuato l'accesso all'interfaccia grafica, cliccare sul blocco "Audio Recording" per avviare la registrazione.
   - Una volta avviata, il blocco cambierà colore diventando arancione, come mostrato in figura, per indicare che la registrazione è attiva.

![esempio1](https://github.com/LabMACS/24.25_Marrone/blob/main/image/esempio1.png)

2. Interruzione della registrazione:
   - Per interrompere la registrazione, cliccare nuovamente sullo stesso blocco "Audio Recording".
   - Al termine, apparirà un messaggio di conferma con la dicitura: "Audio Recording Stopped"
   - Questo messaggio conferma che la registrazione è stata interrotta correttamente.

![esempio2](https://github.com/LabMACS/24.25_Marrone/blob/main/image/esempio2.png)

<h2 id="utilizzo-utente-esperto">:wrench: Utilizzo utente esperto</h2>

Per chi desidera andare oltre l’interfaccia grafica e lavorare da terminale:

1. **:electric_plug: Connessione SSH**

   Una volta connessi alla rete AIDD, aprire il terminale e digitare:
    ```bash
    ssh pi@10.0.0.1
    ```
    
   > Password: `raspberry`.

2. **:hammer_and_wrench: Avvio e Modifica Script**

    - Gli script che gestiscono l’interfaccia si trovano in `/var/www/cgi-bin`:
      ```bash
      cd /var/www/cgi-bin
      ```
    
    - Per eseguire uno script manualmente:
      ```bash
      ./<nome_script>
      ```
      
    - Per modificare uno script direttamente da terminale:
      ```bash
      sudo nano /var/www/cgi-bin/<nome_script>
      ```
      
    - Per caricare uno script dal PC locale al Raspberry, usare `scp` (da PC locale):
      ```bash
      scp '<percorso_script_locale>' pi@10.0.0.1:'<percorso_script_da_sovrascrivere>'
      ```

3. **:clipboard: Risultati e Log**
    - Log e file audio vengono salvati in `/home/pi/data`.
    - I task `Audio Recording` e `AI Detector` producono log in formato `.log` e audio in `.wav`.
    - I file del modulo `AI Detector` sono in `/home/pi/data/Detections`

4. **:eyes: Visualizzazione Risultati**

    - Si può usare `sudo nano` per leggere un file di log:
        ```bash
        sudo nano /home/pi/data/direzione.log
        ```
      
    - In alternativa, è possibile ricevere i risultati in *tempo reale* su un secondo dispositivo via `UART`.
        1. Collegare il dispositivo via UART.
         
        2. Installare python3 sul secondo dispositivo:
            ```bash
            sudo apt update
            sudo apt upgrade
            sudo apt install python3 python3-pip
            ```

        3. Avviare lo script `UART.py` sul dispositivo secondario:
            ```bash
            python3 UART.py
            ```

   In questo modo, ogni nuovo risultato verrà trasmesso in formato JSON tramite la porta seriale.

<h2 id="gantt">📊 Gantt</h2>

![gantt](https://github.com/LabMACS/24.25_Marrone/blob/main/image/gantt.png)

Il Diagramma di Gantt è stato utilizzato come punto di riferimento per l'intera durata del progetto, consentendo una gestione efficace delle attività e dei tempi di consegna.
  - Data di inizio progetto: Lunedì 14/01/2024
  - Consegna finale: Mercoledì 18/12/2024 (coincidente con la presentazione della demo).

Durante il progetto, la programmazione è stata rispettata senza particolari ritardi, fatta eccezione per il Deliverable D3 (impermeabilità del tubo), la cui consegna è stata posticipata a causa di ritardi del fornitore.

<h2 id="tc">:clipboard: TC/TP</h2>

I seguenti test case valutano se il progetto soddisfa i requisiti e i KPI specificati, verificando il corretto funzionamento dei vari aspetti del sistema. Per ogni test, sono presentati la procedura, i criteri di accettazione e i risultati.

<div align="center">

| ID       | Test da effettuare           | Componenti da testare                                             |
|----------|------------------------------|-------------------------------------------------------------------|
| 🟦 TC_1.1   | 🎯 Accuratezza campionamento | Segnale acquisito                                                |
| 🟦 TC_1.2   | 🔇 Riduzione rumore          | Segnale acquisito                                                |
| 🟩 TC_2.1   | 📏 Precisione distanza       | Codice                                                           |
| 🟩 TC_2.2   | 📐 Precisione angolo         | Codice                                                           |
| 🟨 TC_3.1   | 💧 Impermeabilità            | Sistema completo (IP68)                                          |
| 🟨 TC_3.2   | ⚡ Stabilità elettronica     | Idrofoni<br> Preamplificatore<br> RPi Zero 2W<br> HiFiBerry DAC+ADC Pro<br> Powerbank |

</div>

- 🟦 TC1.1: Accuratezza campionamento
    - Obiettivo: Verificare la frequenza e la qualità del segnale rilevato.
    - Test Procedure (TP):
        1. Avviare la registrazione.
        2. Riprodurre un segnale di test tra 10 kHz e 90 kHz.
        3. Arrestare la registrazione.
        4. Confrontare il segnale acquisito con il segnale originale.
    - Criteri di accettazione: Il segnale acquisito deve riportare la stessa frequenza del segnale originale.
    - Risultati: ✅ OK

- 🟦 TC1.2: Riduzione rumore
    - Obiettivo: Verificare il corretto isolamento del segnale attraverso il filtraggio e l'analisi SNR.
    - Test Procedure (TP):
        1. Applicare un filtro passa-alto con una frequenza di taglio di 2 kHz per eliminare il rumore a bassa frequenza.
        2. Calcolare l'SNR del segnale acquisito su una finestra di 2 ms.
    - Criteri di accettazione: SNR > 5.25; isolamento segnali nell'intervallo 2 kHz - 96 kHz.
    - Risultati: ✅ OK

- 🟩 TC2.1: Precisione distanza
    - Obiettivo: Misurare la differenza media tra la distanza calcolata e reale con una sorgente sonora.
    - Test Procedure (TP):
        1. Posizionare una sorgente sonora a una distanza nota (es. 5 m) rispetto agli idrofoni.
        2. Emettere un segnale sonoro.
        3. Registrare la distanza calcolata dal sistema.
        4. Ripetere il processo per distanze diverse (es. 10 m e 15 m).
        5. Calcolare la differenza media tra le distanze reali e quelle calcolate.
    - Criteri di accettazione: La differenza media deve essere < 10% della distanza reale.
    - Risultati: ❌ KO (Non è stato possibile calcolare la distanza).

- 🟩 TC2.2: Precisione angolo
    - Obiettivo: Determinare l'angolo di arrivo del suono da una sorgente.
    - Test Procedure (TP):
      1. Posizionare la sorgente sonora a 0° rispetto agli idrofoni.
      2. Emettere un segnale sonoro.
      3. Registrare l'angolo calcolato dal sistema.
      4. Ripetere il test per altre angolazioni (es. 45°, 90°, 135°, 180°).
      5. Calcolare la differenza media tra l'angolo reale e quello calcolato.
    - Criteri di accettazione: Errore angolare < 10% rispetto alla posizione reale.
    - Risultati: ✅ OK

- 🟨 TC3.1: Impermeabilità
    - Obiettivo: Testare l’impermeabilità del dispositivo secondo lo standard IP68.
    - Test Procedure (TP):
      1. Posizionare il dispositivo sigillato in un acquario a una profondità di 0,2 metri per 60 minuti.
      2. Immergere il dispositivo a 1 metro di profondità in una piscina per 60 minuti.
      3. Rimuovere il dispositivo, aprirlo e verificare visivamente l'interno per segni di umidità.
      4. Testare il funzionamento dei componenti elettronici (Raspberry Pi, HiFiBerry, idrofoni, ecc.).
    - Criteri di accettazione: Nessuna infiltrazione d'acqua; piena funzionalità durante e dopo il test.
    - Risultati: ✅ OK

- 🟨 TC3.2: Stabilità elettronica
    - Obiettivo: Verificare la stabilità operativa del sistema per almeno 6 ore.
    - Test Procedure (TP):
      1. Collegare e accendere tutti i componenti del sistema.
      2. Monitorare il sistema per 6 ore, verificando che non ci siano malfunzionamenti o interruzioni.
    - Criteri di accettazione: Operatività stabile per 6 ore senza interruzioni.
    - Risultati: ✅ OK

<h2 id="kpi">🎯 KPI</h2>

Durante la pianificazione del progetto, sono stati definiti dei KPI (Key Performance Indicator) per garantire il successo del sistema. Tutti i KPI sono stati convalidati, anche se alcuni hanno richiesto più tempo a causa del ritardo nell'arrivo di alcuni materiali.

| **KPI** | **Descrizione**                                                                                      | **Metrica**                                   | **Soglia**                      | **Risultato** |
|---------|------------------------------------------------------------------------------------------------------|-----------------------------------------------|----------------------------------|---------------|
| **1.1** | Accuratezza e qualità del campionamento del segnale acustico                                         | Frequenza di campionamento                    | 192 kHz                          | ✅ OK         |
| **1.2** | Capacità di riduzione del rumore del segnale                                                         | Isolare le frequenze di interesse             | Frequenze di interesse (2 kHz - 96 kHz) | ✅ OK         |
| **2.1** | Differenza media tra la distanza calcolata e la distanza reale delle sorgenti sonore                 | Mantenere questa differenza entro un limite   | Minore del 10%                   | ❌ KO         |
| **2.2** | Accuratezza della determinazione dell'angolo di arrivo del suono                                     | Mantenere una accuratezza entro un limite     | Minore del 10%                   | ✅ OK         |
| **3.1** | Resistenza all'Acqua del Contenitore                                                                 | L'involucro deve rispettare lo standard IP68  | IP68                             | ✅ OK         |
| **3.2** | Durata della batteria in funzionamento continuo                                                      | Il sistema deve funzionare per almeno tot ore | Maggiore di 6 ore                | ✅ OK         |


<h3>📡 Campionamento del segnale</h3>

KPI 1.1: Accuratezza e qualità del campionamento del segnale acustico
  - 📖 Descrizione: Misura l’efficacia del sistema nella conversione del segnale analogico in digitale, assicurando una rappresentazione precisa e di alta qualità.
  - 🎯 Target: Frequenza di campionamento di 192 kHz.

KPI 1.2: Capacità di riduzione del rumore
  - 📖 Descrizione: Valuta l'efficacia del sistema nel ridurre il rumore ambientale e isolare le frequenze di interesse per garantire una qualità ottimale.
  - 🎯 Target: Isolamento delle frequenze tra 2 kHz - 96 kHz.

<h3>🎯 Precisione nell’ecolocalizzazione</h3>

KPI 2.1: Accuratezza nella determinazione della distanza
  - 📖 Descrizione: Misura la precisione con cui il sistema calcola la distanza delle sorgenti sonore rispetto a quella reale.
  - 🎯 Target: Differenza massima inferiore al 10% della distanza reale.

KPI 2.2: Accuratezza della determinazione dell'angolo
  - 📖 Descrizione: Valuta la precisione nella determinazione dell'angolo di arrivo del suono rispetto alla posizione reale.
  - 🎯 Target: Accuratezza entro il 10% dell'angolo reale.

<h3>💧 Resistenza e stabilità</h3>

KPI 3.1: Resistenza all'acqua del contenitore
  - 📖 Descrizione: Il contenitore del dispositivo deve essere impermeabile, proteggendo i componenti interni da infiltrazioni di liquido.
  - 🎯 Target: Standard di protezione IP68 (impermeabilità alla polvere e all'acqua).

KPI 3.2: Stabilità elettronica e durata della batteria
  - 📖 Descrizione: Il sistema deve operare stabilmente senza malfunzionamenti o interruzioni per un lungo periodo.
  - 🎯 Target: Funzionamento continuo per almeno 6 ore in laboratorio.

<h2 id="contributors">:handshake: Contributors</h2>

| Contributor Name      | GitHub                                  |
|:----------------------|:----------------------------------------|
| ⭐ **Scotini Matteo**  | [Click here](https://github.com/) |
| ⭐ **De Ritis Riccardo**   | [Click here](https://github.com/RiccardoDR) |
| ⭐ **Iannotti Andrea**   | [Click here](https://github.com/) |
