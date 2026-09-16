import pytest

from app import _run_config, _secret_key_from_environment


def _clear_config_env(monkeypatch):
    for name in (
        "APP_ENV",
        "FLASK_ENV",
        "FLASK_DEBUG",
        "FLASK_SECRET_KEY",
        "HOST",
        "PORT",
        "SECRET_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_production_requires_environment_secret(monkeypatch):
    _clear_config_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")

    with pytest.raises(RuntimeError):
        _secret_key_from_environment()


def test_environment_secret_is_used_in_production(monkeypatch):
    _clear_config_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "configured-secret")

    assert _secret_key_from_environment() == "configured-secret"


def test_run_config_defaults_are_production_safe(monkeypatch):
    _clear_config_env(monkeypatch)

    assert _run_config() == {"debug": False, "host": "127.0.0.1", "port": 5000}


def test_debug_and_binding_require_explicit_environment(monkeypatch):
    _clear_config_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("FLASK_DEBUG", "1")
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "8000")

    assert _run_config() == {"debug": True, "host": "0.0.0.0", "port": 8000}


def test_debug_is_disabled_in_production_even_when_requested(monkeypatch):
    _clear_config_env(monkeypatch)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("FLASK_DEBUG", "1")

    assert _run_config()["debug"] is False
