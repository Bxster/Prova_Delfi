#!/bin/bash
APP_DIR="/home/pi/Prova_Delfi/app"
echo "run.sh avviato" >> /home/pi/flag.txt
# Imposta i parametri della HiFiBerry
sudo amixer sset "ADC Left Input" "VINL1[SE]"
sudo amixer sset "ADC Right Input" "VINR1[SE]"
sudo amixer sset "ADC" 40dB

# Get hw_id HiFiBerry
hw_id=$(aplay -l | grep -i hifiberry | sed -n 's/^card \([0-9]\+\):.*/\1/p' | head -n1)
if [ -z "$hw_id" ]; then
  hw_id=$(aplay -l | sed -n 's/^card \([0-9]\+\):.*/\1/p' | head -n1)
fi
if [ -z "$hw_id" ]; then
  hw_id=0
fi

# starting jackd
sudo /usr/bin/jackd -r -dalsa -dhw:$hw_id -p512 -r192000 -n7 &
printf "Jackd started \n"
sleep 5s

# starting jack-ring-socket-server (porta 8888, seconds ~0.8)
sudo "$APP_DIR/jack-ring-socket-server" --port 8888 --seconds 0.8 &
printf "Jack-ring-socket-server started (port 8888)\n"

sleep 10s

# trigger su entrambi i canali wav
# tdoa solo se entrambi dicono true
# detection su canale piu vicino (trasformazione wav in spettro)

# Run Task server e Detector
printf "Run Tasks \n"
/home/delfi/Prova_Delfi/.venv/bin/python3 "$APP_DIR/task1_v3.py" &
# /usr/bin/python3 /home/pi/V_TFLite/task2_v3.py &
# /usr/bin/python3 /home/pi/V_TFLite/task3_v3.py &
sleep 20s
printf "Run detector\n"
# avvia detector tramite script dedicato
sudo "$APP_DIR/det.sh" &

# Risposta finale
echo "Tutti i processi sono stati avviati con successo."
#exit 0
