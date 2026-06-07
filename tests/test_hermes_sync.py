from alpha_os.voice.hermes_sync import DEFAULT_WAKE, VOICE_DEFAULTS, apply_voice_config


def test_voice_defaults_include_auto_tts():
    assert VOICE_DEFAULTS["auto_tts"] is True
    assert VOICE_DEFAULTS["tts_provider"] == "edge"


def test_apply_voice_config_writes_alpha_wake(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    config_path = hermes_home / "config.yaml"
    config_path.write_text("alpha_os:\n  wake_word: old\n", encoding="utf-8")

    alpha_home = tmp_path / ".alpha-os"
    alpha_home.mkdir()

    monkeypatch.setattr("alpha_os.config.HERMES_HOME", hermes_home)
    monkeypatch.setattr("alpha_os.config.HERMES_CONFIG_PATH", config_path)
    monkeypatch.setattr("alpha_os.config.HERMES_ENV_PATH", hermes_home / ".env")
    monkeypatch.setattr("alpha_os.config.CONFIG_DIR", alpha_home)
    monkeypatch.setattr("alpha_os.config.CONFIG_PATH", alpha_home / "config.yaml")
    monkeypatch.setattr(
        "alpha_os.voice.openclaw_voicewake.openclaw_installed",
        lambda: False,
    )

    result = apply_voice_config({"wake_word": "hey alpha", "auto_tts": True})
    assert result["wake_word"] == "hey alpha"
    assert result["auto_tts"] is True
    assert "hey alpha" in config_path.read_text(encoding="utf-8")