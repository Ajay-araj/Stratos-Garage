import importlib
import runpy
from pathlib import Path


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


def test_gunicorn_config_uses_render_port_and_single_lightweight_worker(monkeypatch):
    monkeypatch.setenv('PORT', '10000')
    config = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'gunicorn.conf.py'))

    assert config['bind'] == '0.0.0.0:10000'
    assert config['workers'] == 1
    assert config['worker_class'] == 'gthread'
    assert config['threads'] == 2
    assert config['worker_tmp_dir'] == '/tmp'
    assert config['control_socket_disable'] is True


def test_gunicorn_config_uses_local_port_fallback(monkeypatch):
    monkeypatch.delenv('PORT', raising=False)
    config = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'gunicorn.conf.py'))

    assert config['bind'] == '0.0.0.0:8000'
