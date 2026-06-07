from alpha_os.bridges.detector import hermes_installed, openclaw_installed


def test_runtime_install_flags_are_boolean():
    assert isinstance(hermes_installed(), bool)
    assert isinstance(openclaw_installed(), bool)