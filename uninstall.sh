#!/usr/bin/env bash
# Removes TwentyTwentyToo and its autostart entry.
set -euo pipefail

APP_ID=io.github.twentytwentytoo.TwentyTwentyToo
flatpak kill "$APP_ID" 2>/dev/null || true
flatpak uninstall --user -y "$APP_ID" || true
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP_ID.desktop"
echo "TwentyTwentyToo removed."
