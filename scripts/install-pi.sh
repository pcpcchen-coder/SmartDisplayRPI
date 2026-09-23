#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$PWD" != "$HOME/SmartDisplayRPI" ]]; then
  echo 'Please clone into ~/SmartDisplayRPI before installing.' >&2; exit 1
fi
if [[ ! -d /etc/xdg/labwc ]]; then
  echo 'Requires Raspberry Pi OS Desktop with labwc.' >&2; exit 1
fi
sudo apt-get update
sudo apt-get install -y python3 chromium rsync curl
python3 smartdisplay.py init
if [[ ! -e runtime/current ]]; then python3 smartdisplay.py build; fi
# Convert first local snapshot to a symlink, so future deployments can swap atomically.
if [[ ! -L runtime/current ]]; then
  mkdir -p runtime/releases
  mv runtime/current "runtime/releases/bootstrap-$(date +%s)"
  bootstrap=$(ls -dt "$PWD"/runtime/releases/bootstrap-* | head -1)
  ln -s "$bootstrap" runtime/current
fi
mkdir -p "$HOME/.config/systemd/user" "$HOME/.config/labwc"
cat > "$HOME/.config/systemd/user/smartdisplay.service" <<EOF
[Unit]
Description=SmartDisplay local display server
[Service]
WorkingDirectory=%h/SmartDisplayRPI
ExecStart=/usr/bin/python3 %h/SmartDisplayRPI/smartdisplay.py serve
Restart=on-failure
RestartSec=3
[Install]
WantedBy=default.target
EOF
# Do not resolve the current symlink in the server: it must follow deployment swaps.
systemctl --user daemon-reload
systemctl --user enable --now smartdisplay.service
line='bash "$HOME/SmartDisplayRPI/scripts/kiosk.sh" &'
touch "$HOME/.config/labwc/autostart"
grep -Fqx "$line" "$HOME/.config/labwc/autostart" || echo "$line" >> "$HOME/.config/labwc/autostart"
echo 'Installed. Enable Desktop Auto Login and disable Screen Blanking in raspi-config; reboot when ready.'
