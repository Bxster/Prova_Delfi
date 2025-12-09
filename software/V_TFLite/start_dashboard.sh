#!/bin/bash
# Avvia la dashboard DELFI-HammerHead
cd "$(dirname "$0")"
source /home/delfi/Prova_Delfi/.venv/bin/activate
echo "🐬 Avvio dashboard DELFI-HammerHead..."
echo "   Apri nel browser: http://localhost:5000"
echo "   Da rete locale: http://$(hostname -I | awk '{print $1}'):5000"
python dashboard.py
