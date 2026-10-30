# TwentyTwentyToo

[![CI](https://github.com/joelhaasnoot/twentytwentytoo/actions/workflows/ci.yml/badge.svg)](https://github.com/joelhaasnoot/twentytwentytoo/actions/workflows/ci.yml)

A small 20-20-20 eye-break reminder for [Bazzite](https://bazzite.gg) (and any other Linux desktop).
Every **20 minutes** it plays a chime, sends a notification and covers every monitor with a
**20 second** countdown telling you to look at something 20 feet (6 m) away.

- **Status window:** shows the time until the next break, with Pause/Resume and Break now buttons.
  Closing it keeps the reminders running. Launch the app again to reopen it.
- **Break overlay:** a fullscreen countdown on each monitor. Press **Esc** or click **Skip** to dismiss it early.
- **Away time doesn't count:** locking the screen (KDE or GNOME) or suspending restarts the 20-minute countdown.

## Install on Bazzite

```bash
git clone https://github.com/joelhaasnoot/twentytwentytoo.git && cd twentytwentytoo
./install.sh
```

This builds the app as a user Flatpak on the GNOME runtime (downloaded from Flathub the first time),
installs it, adds a login autostart entry that starts it in the background, and launches it.
Use `./install.sh --no-autostart` to skip the autostart entry, and `./uninstall.sh` to remove everything.

## Run without installing

If your host Python has GTK 4 bindings (PyGObject), you can run it directly.
Shorter timings are handy for testing:

```bash
./twentytwentytoo.py --interval 10 --break-length 5
```

| Option | Default | Meaning |
| --- | --- | --- |
| `-i`, `--interval SECONDS` | 1200 | Time between breaks |
| `-l`, `--break-length SECONDS` | 20 | Length of each break |
| `-b`, `--background` | off | Start without showing the status window |

## Languages

The interface follows your desktop language: English, Dutch, German, French, Spanish, Portuguese and Swahili.
To try another one, set `LANGUAGE` (for example `LANGUAGE=sw ./twentytwentytoo.py`, or
`flatpak run --env=LANGUAGE=de io.github.twentytwentytoo.TwentyTwentyToo`).
To add a language, add a dictionary to `TRANSLATIONS` at the top of `twentytwentytoo.py`.

## Development

```bash
pipx run ruff check .
xvfb-run -a dbus-run-session -- python3 -m pytest -v   # the break-cycle test needs a display
```

CI runs lint and tests on Ubuntu, and builds the Flatpak. Each run uploads a `twentytwentytoo.flatpak`
bundle as an artifact, which you can install with `flatpak install --user twentytwentytoo.flatpak`.

## Limitations

- Works in Bazzite's **Desktop Mode**. Game Mode (the Gamescope session) only shows the focused
  Steam app, so the overlay won't appear there.
- On Wayland, apps can't force themselves above other fullscreen windows. If a fullscreen game
  keeps focus, you'll still get the chime and notification, but the overlay may sit behind the game.

## License

MIT
