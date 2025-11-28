#!/usr/bin/env bash
set -euo pipefail

# Installazione pacchetti di sistema
sudo apt-get update
xargs -a apt-packages.txt sudo apt-get install -y

# Ambiente virtuale Python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

# Dipendenze Python
pip install -r requirements.txt

# Compilazione del server JACK (necessita libjack-dev e build-essential)
if [ -d "jack-ring-socket-server" ]; then
  make -C jack-ring-socket-server
fi

echo "\nFatto. Note:" 
echo "- Abilita l'interfaccia seriale (raspi-config) se usi UART" 
echo "- Aggiungi l'utente al gruppo audio: sudo adduser $USER audio" 
echo "- Verifica jackd: jackd --version" 
