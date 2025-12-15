#!/bin/bash
set -euo pipefail

echo "Stopping DELFI processes..."

# Stop continuous recorder first (graceful shutdown to save WAV file)
if pgrep -f "V_TFLite/continuous_recorder.py" > /dev/null 2>&1; then
  echo "Stopping Continuous Recorder (saving recording)..."
  pkill -TERM -f "V_TFLite/continuous_recorder.py"
  sleep 3  # Give it time to save the WAV file
fi

kill_pattern() {
  local pattern="$1"
  local name="$2"
  if pgrep -f "$pattern" >/dev/null 2>&1; then
    echo "Stopping $name ..."
    sudo pkill -f "$pattern" || true
    sleep 1
    if pgrep -f "$pattern" >/dev/null 2>&1; then
      echo "Force killing $name ..."
      sudo pkill -9 -f "$pattern" || true
    fi
  else
    echo "$name not running."
  fi
}

# Detector (current and legacy)
kill_pattern "V_TFLite/detector_v3_with_trigger.py" "Detector"

# TFLite tasks
kill_pattern "V_TFLite/task1_v3.py" "Task1"

# Ring buffer server
kill_pattern "jack-ring-socket-server" "Jack ring socket server"
kill_pattern "start_jack_ring_server.sh" "Jack ring server launcher"

# JACK audio server
kill_pattern "/usr/bin/jackd -r -dalsa" "jackd"
kill_pattern "jackd" "jackd (generic)"

echo "All stop commands issued."
