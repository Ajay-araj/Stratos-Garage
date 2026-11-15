import importlib


def test_fix_pending_payments_exports_safe_default_settings():
    module = importlib.import_module('fix_pending_payments')
    assert module.get_default_settings_module() == 'Stratosgarage.settings.production'


def test_fix_pending_payments_parser_supports_safe_modes():
    module = importlib.import_module('fix_pending_payments')
    parser = module.build_parser()
    args = parser.parse_args(['--dry-run'])
    assert args.dry_run is True
    assert args.apply is False
