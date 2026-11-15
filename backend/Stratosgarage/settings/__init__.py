import importlib
import os


def _resolve_settings_module():
    env_name = os.getenv('DJANGO_ENV', '').strip().lower()
    module_name = '.production' if env_name == 'production' else '.development'
    module = importlib.import_module(module_name, __name__)

    for key, value in module.__dict__.items():
        if key.startswith('__') and key.endswith('__'):
            continue
        globals()[key] = value


_resolve_settings_module()
