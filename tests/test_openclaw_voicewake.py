import json

from alpha_os.voice.openclaw_voicewake import (
    normalize_triggers,
    read_voicewake,
    wake_word_to_triggers,
    write_voicewake,
)


def test_wake_word_to_triggers():
    assert wake_word_to_triggers("hey alpha") == ["hey alpha", "alpha"]
    assert wake_word_to_triggers("computer") == ["computer"]


def test_normalize_triggers_dedupes():
    assert normalize_triggers([" Hey Alpha ", "hey alpha", ""]) == ["hey alpha"]


def test_write_and_read_voicewake(tmp_path, monkeypatch):
    path = tmp_path / "settings" / "voicewake.json"
    monkeypatch.setattr(
        "alpha_os.voice.openclaw_voicewake.VOICEWAKE_PATH",
        path,
    )
    monkeypatch.setattr(
        "alpha_os.voice.openclaw_voicewake.openclaw_installed",
        lambda: True,
    )

    saved = write_voicewake(["hey alpha", "alpha"])
    assert saved["triggers"] == ["hey alpha", "alpha"]
    assert path.exists()

    loaded = read_voicewake()
    assert loaded["triggers"] == ["hey alpha", "alpha"]
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert "updatedAtMs" in on_disk