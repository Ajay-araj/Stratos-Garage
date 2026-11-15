import importlib


def test_settings_package_selects_production_when_requested(monkeypatch):
    monkeypatch.setenv('DJANGO_ENV', 'production')
    import Stratosgarage.settings as settings_module
    importlib.reload(settings_module)

    assert settings_module.DEBUG is False
    assert hasattr(settings_module, 'SECURE_SSL_REDIRECT')


def test_settings_package_selects_development_by_default(monkeypatch):
    monkeypatch.delenv('DJANGO_ENV', raising=False)
    import Stratosgarage.settings as settings_module
    importlib.reload(settings_module)

    assert settings_module.DEBUG is True
