#!/usr/bin/env bash
set -euo pipefail
# Runs inside labwc graphical session; Chromium remains sandboxed.
while ! curl -fsS http://127.0.0.1:8765/state.json >/dev/null; do sleep 2; done
while true; do
  chromium --kiosk --no-first-run --noerrdialogs --user-data-dir="$HOME/.config/smartdisplay-chromium" http://127.0.0.1:8765 || true
  sleep 3
done
