import ast
import os
import wave
from pathlib import Path

import pytest
from gi.repository import GLib

import twentytwentytoo as ttt

SOURCE = Path(ttt.__file__).read_text()
HAS_DISPLAY = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def translated_strings():
    """Every string literal passed to _() in the app."""
    return {
        node.args[0].value
        for node in ast.walk(ast.parse(SOURCE))
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "_"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }


@pytest.mark.parametrize("language", sorted(ttt.TRANSLATIONS))
def test_translation_is_complete(language):
    table = ttt.TRANSLATIONS[language]
    used = translated_strings()
    assert used - table.keys() == set(), "missing translations"
    assert table.keys() - used == set(), "translations for strings the app no longer uses"
    for english, translated in table.items():
        for placeholder in ("{count}", "{seconds}"):
            assert (placeholder in english) == (placeholder in translated), english


@pytest.mark.parametrize(
    ("language_env", "expected"),
    [("nl_NL.UTF-8", "nl"), ("sw_KE", "sw"), ("fr_CA.UTF-8", "fr"), ("en_GB.UTF-8", "en"), ("C", "en"), ("xx", "en")],
)
def test_pick_language(monkeypatch, language_env, expected):
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANGUAGE", language_env)
    assert ttt.pick_language() == expected


@pytest.mark.parametrize(("seconds", "expected"), [(0, "00:00"), (-3, "00:00"), (59.2, "01:00"), (1200, "20:00")])
def test_format_mmss(seconds, expected):
    assert ttt.format_mmss(seconds) == expected


def test_chime_is_a_valid_wav(tmp_path):
    path = tmp_path / "chime.wav"
    ttt.Sounds.write_chime(str(path), ttt.Sounds.NOTES["start"])
    with wave.open(str(path)) as chime:
        assert chime.getnchannels() == 1
        assert 0.5 < chime.getnframes() / chime.getframerate() < 2


@pytest.mark.skipif(not HAS_DISPLAY, reason="needs a display (run under xvfb-run)")
def test_full_break_cycle():
    app = ttt.TwentyTwentyToo()
    seen = {}

    def watch():
        if app.in_break:
            seen["break_windows"] = len(app.break_windows)
        if app.breaks_taken:
            app.quit()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    GLib.timeout_add(100, watch)
    GLib.timeout_add_seconds(30, app.quit)  # safety net so a regression can't hang CI
    app.run(["twentytwentytoo", "--background", "--interval", "5", "--break-length", "2"])

    assert seen.get("break_windows", 0) >= 1, "break overlay never appeared"
    assert app.breaks_taken == 1
    assert not app.in_break and app.break_windows == []
