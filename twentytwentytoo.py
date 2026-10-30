#!/usr/bin/env python3
"""TwentyTwentyToo: a 20-20-20 eye-break reminder for Bazzite (and any Linux desktop).

Every 20 minutes it chimes, sends a notification and covers each monitor with a
20 second countdown reminding you to look at something ~20 feet (6 m) away.
"""

import math
import os
import struct
import sys
import time
import wave

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

APP_ID = "io.github.twentytwentytoo.TwentyTwentyToo"
APP_NAME = "TwentyTwentyToo"
DEFAULT_INTERVAL = 20 * 60
DEFAULT_BREAK_LENGTH = 20
TICK_MS = 250
# If the wall clock jumps this far between ticks the machine was suspended,
# and you were away from the screen anyway, so the countdown starts over.
SUSPEND_GAP_SECONDS = 60

CSS = """
window.break-overlay {
  background-color: rgba(8, 12, 20, 0.94);
}
window.break-overlay .headline {
  font-size: 44px;
  font-weight: 800;
  color: #e8f1ff;
}
window.break-overlay .hint {
  font-size: 20px;
  color: #9fb3c8;
}
window.break-overlay .countdown {
  font-size: 168px;
  font-weight: 800;
  font-feature-settings: "tnum";
  color: #7dd3fc;
}
window.break-overlay progressbar trough,
window.break-overlay progressbar progress {
  min-height: 8px;
  border-radius: 4px;
}
window.break-overlay progressbar progress {
  background-color: #7dd3fc;
}
window.break-overlay button {
  font-size: 16px;
  padding: 8px 24px;
}
.next-break {
  font-size: 56px;
  font-weight: 800;
  font-feature-settings: "tnum";
}
.dim {
  opacity: 0.7;
}
"""


# English strings are the keys; add a language by adding a dict here.
TRANSLATIONS = {
    "nl": {
        "Look away from the screen": "Kijk weg van het scherm",
        "Focus on something at least 20 feet (6 m) away and let your eyes relax.":
            "Richt je blik op iets op minstens 6 meter afstand en laat je ogen ontspannen.",
        "Skip (Esc)": "Overslaan (Esc)",
        "Eye break in progress": "Oogpauze bezig",
        "Paused": "Gepauzeerd",
        "Next eye break in": "Volgende oogpauze over",
        "Screen locked: the timer restarts when you're back.":
            "Scherm vergrendeld: de timer begint opnieuw als je terug bent.",
        "Breaks taken this session: {count}": "Pauzes genomen deze sessie: {count}",
        "Pause": "Pauzeren",
        "Resume": "Hervatten",
        "Break now": "Nu pauze",
        "Closing this window keeps the reminders running.\nLaunch the app again to reopen it.":
            "Als je dit venster sluit, blijven de herinneringen actief.\nStart de app opnieuw om het weer te openen.",
        "Quit": "Afsluiten",
        "Time for an eye break": "Tijd voor een oogpauze",
        "Look at something 20 feet (6 m) away for {seconds} seconds.":
            "Kijk {seconds} seconden naar iets op 6 meter afstand.",
    },
    "de": {
        "Look away from the screen": "Schau weg vom Bildschirm",
        "Focus on something at least 20 feet (6 m) away and let your eyes relax.":
            "Richte den Blick auf etwas, das mindestens 6 Meter entfernt ist, und entspanne deine Augen.",
        "Skip (Esc)": "Überspringen (Esc)",
        "Eye break in progress": "Augenpause läuft",
        "Paused": "Pausiert",
        "Next eye break in": "Nächste Augenpause in",
        "Screen locked: the timer restarts when you're back.":
            "Bildschirm gesperrt: Der Timer startet neu, wenn du zurück bist.",
        "Breaks taken this session: {count}": "Pausen in dieser Sitzung: {count}",
        "Pause": "Pausieren",
        "Resume": "Fortsetzen",
        "Break now": "Jetzt Pause",
        "Closing this window keeps the reminders running.\nLaunch the app again to reopen it.":
            "Die Erinnerungen laufen weiter, wenn du dieses Fenster schließt.\n"
            "Starte die App erneut, um es wieder zu öffnen.",
        "Quit": "Beenden",
        "Time for an eye break": "Zeit für eine Augenpause",
        "Look at something 20 feet (6 m) away for {seconds} seconds.":
            "Schau {seconds} Sekunden lang auf etwas in 6 Metern Entfernung.",
    },
    "fr": {
        "Look away from the screen": "Détournez les yeux de l'écran",
        "Focus on something at least 20 feet (6 m) away and let your eyes relax.":
            "Regardez quelque chose situé à au moins 6 mètres et laissez vos yeux se détendre.",
        "Skip (Esc)": "Passer (Échap)",
        "Eye break in progress": "Pause visuelle en cours",
        "Paused": "En pause",
        "Next eye break in": "Prochaine pause visuelle dans",
        "Screen locked: the timer restarts when you're back.":
            "Écran verrouillé : le minuteur redémarre à votre retour.",
        "Breaks taken this session: {count}": "Pauses prises cette session : {count}",
        "Pause": "Mettre en pause",
        "Resume": "Reprendre",
        "Break now": "Pause maintenant",
        "Closing this window keeps the reminders running.\nLaunch the app again to reopen it.":
            "Fermer cette fenêtre n'arrête pas les rappels.\nRelancez l'application pour la rouvrir.",
        "Quit": "Quitter",
        "Time for an eye break": "C'est l'heure d'une pause visuelle",
        "Look at something 20 feet (6 m) away for {seconds} seconds.":
            "Regardez quelque chose à 6 mètres pendant {seconds} secondes.",
    },
    "es": {
        "Look away from the screen": "Aparta la vista de la pantalla",
        "Focus on something at least 20 feet (6 m) away and let your eyes relax.":
            "Mira algo que esté al menos a 6 metros y deja que tus ojos descansen.",
        "Skip (Esc)": "Saltar (Esc)",
        "Eye break in progress": "Descanso visual en curso",
        "Paused": "En pausa",
        "Next eye break in": "Próximo descanso visual en",
        "Screen locked: the timer restarts when you're back.":
            "Pantalla bloqueada: el temporizador se reinicia cuando vuelvas.",
        "Breaks taken this session: {count}": "Descansos en esta sesión: {count}",
        "Pause": "Pausar",
        "Resume": "Reanudar",
        "Break now": "Descansar ahora",
        "Closing this window keeps the reminders running.\nLaunch the app again to reopen it.":
            "Cerrar esta ventana no detiene los recordatorios.\nAbre la aplicación de nuevo para volver a verla.",
        "Quit": "Salir",
        "Time for an eye break": "Hora de un descanso visual",
        "Look at something 20 feet (6 m) away for {seconds} seconds.":
            "Mira algo a 6 metros durante {seconds} segundos.",
    },
    "pt": {
        "Look away from the screen": "Afaste os olhos da tela",
        "Focus on something at least 20 feet (6 m) away and let your eyes relax.":
            "Olhe para algo a pelo menos 6 metros de distância e deixe seus olhos relaxarem.",
        "Skip (Esc)": "Pular (Esc)",
        "Eye break in progress": "Pausa para os olhos em andamento",
        "Paused": "Pausado",
        "Next eye break in": "Próxima pausa para os olhos em",
        "Screen locked: the timer restarts when you're back.":
            "Tela bloqueada: o temporizador recomeça quando você voltar.",
        "Breaks taken this session: {count}": "Pausas nesta sessão: {count}",
        "Pause": "Pausar",
        "Resume": "Retomar",
        "Break now": "Pausa agora",
        "Closing this window keeps the reminders running.\nLaunch the app again to reopen it.":
            "Fechar esta janela não interrompe os lembretes.\nAbra o aplicativo novamente para reabri-la.",
        "Quit": "Sair",
        "Time for an eye break": "Hora de uma pausa para os olhos",
        "Look at something 20 feet (6 m) away for {seconds} seconds.":
            "Olhe para algo a 6 metros por {seconds} segundos.",
    },
    "sw": {
        "Look away from the screen": "Angalia mbali na skrini",
        "Focus on something at least 20 feet (6 m) away and let your eyes relax.":
            "Angalia kitu kilicho umbali wa angalau mita 6 na upumzishe macho yako.",
        "Skip (Esc)": "Ruka (Esc)",
        "Eye break in progress": "Mapumziko ya macho yanaendelea",
        "Paused": "Imesitishwa",
        "Next eye break in": "Mapumziko yajayo ya macho baada ya",
        "Screen locked: the timer restarts when you're back.":
            "Skrini imefungwa: kipima muda kitaanza upya ukirudi.",
        "Breaks taken this session: {count}": "Mapumziko yaliyochukuliwa kipindi hiki: {count}",
        "Pause": "Sitisha",
        "Resume": "Endelea",
        "Break now": "Pumzika sasa",
        "Closing this window keeps the reminders running.\nLaunch the app again to reopen it.":
            "Kufunga dirisha hili hakusimamishi vikumbusho.\nFungua programu tena ili kuliona.",
        "Quit": "Ondoka",
        "Time for an eye break": "Wakati wa kupumzisha macho",
        "Look at something 20 feet (6 m) away for {seconds} seconds.":
            "Angalia kitu kilicho mita 6 mbali kwa sekunde {seconds}.",
    },
}


def pick_language():
    """First supported language from LANGUAGE / LC_ALL / LC_MESSAGES / LANG, else English."""
    for name in GLib.get_language_names():
        code = name.split(".")[0].split("@")[0].split("_")[0]
        if code in TRANSLATIONS:
            return code
        if code in ("en", "C"):
            break
    return "en"


STRINGS = TRANSLATIONS.get(pick_language(), {})


def _(text, **values):
    return STRINGS.get(text, text).format(**values)


def format_mmss(seconds):
    seconds = max(0, math.ceil(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class Sounds:
    """Generates two short chimes on first run and plays them through GTK's media backend."""

    NOTES = {
        "start": (659.25, 880.0),  # E5 -> A5, rising: time to look away
        "end": (880.0, 659.25),  # A5 -> E5, falling: back to it
    }

    def __init__(self):
        self.cache_dir = os.path.join(GLib.get_user_cache_dir(), "twentytwentytoo")
        self.playing = []

    def path(self, name):
        path = os.path.join(self.cache_dir, f"{name}.wav")
        if not os.path.exists(path):
            os.makedirs(self.cache_dir, exist_ok=True)
            self.write_chime(path, self.NOTES[name])
        return path

    @staticmethod
    def write_chime(path, notes, rate=44100, note_seconds=0.45, volume=0.35):
        frames = bytearray()
        for freq in notes:
            for i in range(int(rate * note_seconds)):
                t = i / rate
                envelope = math.exp(-5 * t) * min(1.0, t * 200)
                sample = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t)
                frames += struct.pack("<h", int(32767 * volume * envelope * sample / 1.3))
        with wave.open(path, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(bytes(frames))

    def play(self, name):
        try:
            media = Gtk.MediaFile.new_for_filename(self.path(name))
        except (GLib.Error, OSError) as error:
            print(f"{APP_NAME}: could not play sound: {error}", file=sys.stderr)
            return
        # Keep a reference until playback ends, otherwise it is garbage-collected mid-chime.
        self.playing.append(media)
        media.connect("notify::ended", lambda m, _p: m.get_ended() and self.playing.remove(m))
        media.play()


class ScreenLockWatcher:
    """Polls the desktop's screensaver over D-Bus so time spent locked doesn't count."""

    SERVICES = [
        ("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver"),  # KDE
        ("org.gnome.ScreenSaver", "/org/gnome/ScreenSaver", "org.gnome.ScreenSaver"),  # GNOME
    ]

    def __init__(self):
        self.locked = False
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            self.bus = None
            return
        GLib.timeout_add_seconds(5, self.poll)
        self.poll()

    def poll(self):
        self.query(0)
        return GLib.SOURCE_CONTINUE

    def query(self, index):
        if index >= len(self.SERVICES):
            self.locked = False
            return
        name, path, interface = self.SERVICES[index]
        self.bus.call(
            name, path, interface, "GetActive", None, GLib.VariantType("(b)"),
            Gio.DBusCallFlags.NO_AUTO_START, 1000, None, self.on_reply, index,
        )

    def on_reply(self, bus, result, index):
        try:
            (self.locked,) = bus.call_finish(result).unpack()
        except GLib.Error:
            self.query(index + 1)


class BreakWindow(Gtk.Window):
    """Fullscreen countdown shown on one monitor during a break."""

    def __init__(self, app, monitor):
        super().__init__(application=app, title=_("Time for an eye break"), decorated=False)
        self.add_css_class("break-overlay")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                      halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        box.append(Gtk.Label(label=_("Look away from the screen"), css_classes=["headline"]))
        box.append(Gtk.Label(label=_("Focus on something at least 20 feet (6 m) away and let your eyes relax."),
                             css_classes=["hint"], wrap=True, justify=Gtk.Justification.CENTER))
        self.countdown = Gtk.Label(css_classes=["countdown"])
        box.append(self.countdown)
        self.progress = Gtk.ProgressBar(width_request=420, halign=Gtk.Align.CENTER)
        box.append(self.progress)
        skip = Gtk.Button(label=_("Skip (Esc)"), halign=Gtk.Align.CENTER, margin_top=24)
        skip.connect("clicked", lambda _b: app.end_break(completed=False))
        box.append(skip)
        self.set_child(box)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key, app)
        self.add_controller(keys)

        if monitor is not None:
            self.fullscreen_on_monitor(monitor)
        else:
            self.fullscreen()

    def on_key(self, _controller, keyval, _keycode, _state, app):
        if keyval == Gdk.KEY_Escape:
            app.end_break(completed=False)
            return True
        return False

    def update(self, seconds_left, fraction_left):
        self.countdown.set_label(str(max(0, math.ceil(seconds_left))))
        self.progress.set_fraction(fraction_left)


class MainWindow(Gtk.ApplicationWindow):
    """Small status window: time until the next break plus pause / break-now controls."""

    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME, default_width=380, resizable=False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        self.heading = Gtk.Label(css_classes=["dim"])
        box.append(self.heading)
        self.countdown = Gtk.Label(css_classes=["next-break"])
        box.append(self.countdown)
        self.status = Gtk.Label(css_classes=["dim"], wrap=True, justify=Gtk.Justification.CENTER)
        box.append(self.status)

        buttons = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER, margin_top=8, homogeneous=True)
        self.pause_button = Gtk.Button(action_name="app.pause")
        buttons.append(self.pause_button)
        buttons.append(Gtk.Button(label=_("Break now"), action_name="app.break-now"))
        box.append(buttons)

        footer = Gtk.Label(
            label=_("Closing this window keeps the reminders running.\nLaunch the app again to reopen it."),
            css_classes=["dim", "caption"], justify=Gtk.Justification.CENTER, margin_top=12,
        )
        box.append(footer)
        box.append(Gtk.Button(label=_("Quit"), action_name="app.quit", halign=Gtk.Align.CENTER,
                              css_classes=["flat"]))
        self.set_child(box)

        self.connect("close-request", self.on_close_request)

    def on_close_request(self, _window):
        self.set_visible(False)
        return True

    def refresh(self, app):
        if app.in_break:
            self.heading.set_label(_("Eye break in progress"))
            self.countdown.set_label(format_mmss(app.break_end - time.monotonic()))
        else:
            self.heading.set_label(_("Paused") if app.paused else _("Next eye break in"))
            self.countdown.set_label(format_mmss(app.remaining()))

        if app.lock_watcher.locked and not app.paused:
            status = _("Screen locked: the timer restarts when you're back.")
        else:
            status = _("Breaks taken this session: {count}", count=app.breaks_taken)
        self.status.set_label(status)
        self.pause_button.set_label(_("Resume") if app.paused else _("Pause"))


class TwentyTwentyToo(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        GLib.set_application_name(APP_NAME)
        self.add_main_option("background", ord("b"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
                             "Start without showing the window (for autostart)", None)
        self.add_main_option("interval", ord("i"), GLib.OptionFlags.NONE, GLib.OptionArg.INT,
                             f"Seconds between breaks (default {DEFAULT_INTERVAL})", "SECONDS")
        self.add_main_option("break-length", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.INT,
                             f"Length of each break in seconds (default {DEFAULT_BREAK_LENGTH})", "SECONDS")

        self.interval = DEFAULT_INTERVAL
        self.break_length = DEFAULT_BREAK_LENGTH
        self.running = False
        self.paused = False
        self.paused_remaining = 0.0
        self.in_break = False
        self.break_end = 0.0
        self.next_break = 0.0
        self.last_wall = time.time()
        self.breaks_taken = 0
        self.break_windows = []

    def do_startup(self):
        Gtk.Application.do_startup(self)
        # Keep running in the background when the status window is closed.
        self.hold()

        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        for name, callback in (("pause", self.toggle_pause),
                               ("break-now", self.start_break),
                               ("quit", self.on_quit)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, cb=callback: cb())
            self.add_action(action)

        self.sounds = Sounds()
        self.lock_watcher = ScreenLockWatcher()
        self.window = MainWindow(self)

    def do_command_line(self, command_line):
        options = command_line.get_options_dict().end().unpack()
        if not self.running:
            self.interval = max(5, options.get("interval", DEFAULT_INTERVAL))
            self.break_length = max(1, options.get("break-length", DEFAULT_BREAK_LENGTH))
            self.running = True
            self.reset_timer()
            GLib.timeout_add(TICK_MS, self.tick)
        # Launching the app again while it is already running reopens the status window.
        if not options.get("background"):
            self.window.present()
        self.window.refresh(self)
        return 0

    def on_quit(self):
        self.end_break(completed=False)
        self.quit()

    def reset_timer(self):
        self.next_break = time.monotonic() + self.interval

    def remaining(self):
        if self.paused:
            return self.paused_remaining
        return max(0.0, self.next_break - time.monotonic())

    def toggle_pause(self):
        if self.in_break:
            return
        if self.paused:
            self.next_break = time.monotonic() + self.paused_remaining
            self.paused = False
        else:
            self.paused_remaining = self.remaining()
            self.paused = True
        self.window.refresh(self)

    def tick(self):
        now = time.monotonic()
        wall = time.time()
        suspended = wall - self.last_wall > SUSPEND_GAP_SECONDS
        self.last_wall = wall

        if self.in_break:
            left = self.break_end - now
            if left <= 0:
                self.end_break(completed=True)
            else:
                for window in self.break_windows:
                    window.update(left, left / self.break_length)
        elif not self.paused:
            if suspended or self.lock_watcher.locked:
                self.reset_timer()
            elif now >= self.next_break:
                self.start_break()

        if self.window.get_visible():
            self.window.refresh(self)
        return GLib.SOURCE_CONTINUE

    def start_break(self):
        if self.in_break:
            return
        self.in_break = True
        self.paused = False
        self.break_end = time.monotonic() + self.break_length
        self.sounds.play("start")

        notification = Gio.Notification.new(_("Time for an eye break"))
        notification.set_body(
            _("Look at something 20 feet (6 m) away for {seconds} seconds.", seconds=self.break_length))
        notification.set_priority(Gio.NotificationPriority.HIGH)
        self.send_notification("break", notification)

        monitors = Gdk.Display.get_default().get_monitors()
        targets = [monitors.get_item(i) for i in range(monitors.get_n_items())] or [None]
        for monitor in targets:
            window = BreakWindow(self, monitor)
            window.update(self.break_length, 1.0)
            window.present()
            self.break_windows.append(window)

    def end_break(self, completed):
        if not self.in_break:
            return
        self.in_break = False
        for window in self.break_windows:
            window.destroy()
        self.break_windows = []
        self.withdraw_notification("break")
        if completed:
            self.breaks_taken += 1
            self.sounds.play("end")
        self.reset_timer()
        self.window.refresh(self)


def main():
    return TwentyTwentyToo().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
