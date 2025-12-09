#!/usr/bin/env python3
"""
DELFI-HammerHead Web Dashboard
Interfaccia web semplice per controllare il sistema di rilevamento delfini.
"""

from flask import Flask, Response, jsonify, render_template, request
import subprocess
import os
import time
import threading

# Import config per i path
from config import LOG_FILE_PATH, LOGS_DIR

app = Flask(__name__)

# Path agli script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_SCRIPT = os.path.join(SCRIPT_DIR, "run.sh")
STOP_SCRIPT = os.path.join(SCRIPT_DIR, "stop_all.sh")


def is_system_running():
    """Verifica se il sistema DELFI è in esecuzione controllando i processi."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "detector_v3_with_trigger.py"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


@app.route('/')
def index():
    """Pagina principale con interfaccia di controllo."""
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start_system():
    """Avvia il sistema DELFI."""
    try:
        # Esegui run.sh in background
        subprocess.Popen(
            ["bash", RUN_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return jsonify({"status": "ok", "message": "Sistema in avvio..."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/stop', methods=['POST'])
def stop_system():
    """Ferma il sistema DELFI."""
    try:
        subprocess.run(["bash", STOP_SCRIPT], capture_output=True)
        return jsonify({"status": "ok", "message": "Sistema fermato"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/status')
def get_status():
    """Ritorna lo stato del sistema."""
    running = is_system_running()
    return jsonify({
        "running": running,
        "status": "running" if running else "stopped"
    })


@app.route('/logs')
def stream_logs():
    """Stream dei log in tempo reale via Server-Sent Events."""
    def generate():
        # Assicurati che la directory dei log esista
        os.makedirs(LOGS_DIR, exist_ok=True)
        
        # Se il file non esiste, crealo
        if not os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'w') as f:
                f.write(f"Log inizializzato: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Invia le ultime 50 righe come contesto iniziale
        try:
            with open(LOG_FILE_PATH, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
                for line in last_lines:
                    yield f"data: {line.strip()}\n\n"
        except Exception as e:
            yield f"data: Errore lettura log: {e}\n\n"
        
        # Poi fai tail del file in tempo reale
        try:
            with open(LOG_FILE_PATH, 'r') as f:
                # Vai alla fine del file
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {line.strip()}\n\n"
                    else:
                        time.sleep(0.3)
        except GeneratorExit:
            pass
        except Exception as e:
            yield f"data: Errore streaming: {e}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/clear-logs', methods=['POST'])
def clear_logs():
    """Pulisce il file di log."""
    try:
        with open(LOG_FILE_PATH, 'w') as f:
            f.write(f"Log pulito: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        return jsonify({"status": "ok", "message": "Log pulito"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🐬 DELFI-HammerHead Dashboard")
    print("=" * 50)
    print(f"📁 Log file: {LOG_FILE_PATH}")
    print(f"🌐 Apri nel browser: http://localhost:5000")
    print(f"   o da rete locale: http://<raspberry-ip>:5000")
    print("=" * 50)
    
    # Avvia Flask su tutte le interfacce per accesso da rete
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
