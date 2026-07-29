#!/usr/bin/env bash
# Keeps the three local services alive after ARMY-START has been pressed once.
set -eu

STARTER="/sdcard/ARMY/army-start-debian.sh"
LOG_DIR="/sdcard/ARMY/logs"
WATCHDOG_LOG="$LOG_DIR/army-watchdog.log"

mkdir -p "$LOG_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') watchdog started" >> "$WATCHDOG_LOG"

while true; do
  restart_needed=0
  for item in \
    "army-g4f|http://127.0.0.1:1337/v1/models" \
    "army-router|http://127.0.0.1:1340/health" \
    "army-fcc|http://127.0.0.1:8082/health"; do
    name="${item%%|*}"
    url="${item#*|}"
    if ! curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') $name failed health check; restarting" >> "$WATCHDOG_LOG"
      tmux kill-session -t "$name" 2>/dev/null || true
      restart_needed=1
    fi
  done

  if [ "$restart_needed" -eq 1 ]; then
    bash "$STARTER" >> "$WATCHDOG_LOG" 2>&1 || true
  fi
  sleep 60
done
