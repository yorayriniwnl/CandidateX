from cci.config import Settings


def test_settings_default_to_debug_off_and_no_shared_secret(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.DEBUG is False
    assert settings.SECRET_KEY is None
