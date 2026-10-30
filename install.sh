#!/usr/bin/env bash
# Builds TwentyTwentyToo as a user Flatpak, installs it and starts it on login.
# Usage: ./install.sh [--no-autostart]
set -euo pipefail

APP_ID=io.github.twentytwentytoo.TwentyTwentyToo
cd "$(dirname "$0")"

autostart=1
if [[ "${1:-}" == "--no-autostart" ]]; then
  autostart=0
fi

flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

# Bazzite is image-based, so use the Flatpak'd builder unless flatpak-builder is already on the host.
if command -v flatpak-builder >/dev/null 2>&1; then
  builder=(flatpak-builder)
else
  if ! flatpak info org.flatpak.Builder >/dev/null 2>&1; then
    flatpak install --user -y flathub org.flatpak.Builder
  fi
  builder=(flatpak run org.flatpak.Builder)
fi

"${builder[@]}" --user --install --force-clean --install-deps-from=flathub \
  --state-dir=.flatpak-builder build-dir "$APP_ID.yml"

autostart_file="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP_ID.desktop"
if [[ $autostart -eq 1 ]]; then
  mkdir -p "$(dirname "$autostart_file")"
  cat > "$autostart_file" <<DESKTOP
[Desktop Entry]
Type=Application
Name=TwentyTwentyToo
Comment=20-20-20 eye break reminder
Exec=flatpak run $APP_ID --background
Icon=$APP_ID
X-GNOME-Autostart-enabled=true
DESKTOP
  echo "Autostart enabled: $autostart_file"
fi

echo "Installed. Starting TwentyTwentyToo..."
nohup flatpak run "$APP_ID" >/dev/null 2>&1 &
