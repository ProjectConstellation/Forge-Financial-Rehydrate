"""Every module the service loads must import (guards against overwritten/renamed modules breaking startup)."""
import importlib
import pkgutil

import forge


def test_all_forge_modules_import():
    failed = []
    for m in pkgutil.walk_packages(forge.__path__, "forge."):
        try:
            importlib.import_module(m.name)
        except Exception as e:  # noqa: BLE001
            failed.append(f"{m.name}: {e}")
    assert not failed, failed


def test_runtime_symbols():
    from forge.treasury.profit_velocity import VelocityEngine  # noqa: F401
    from forge.treasury.velocity import OpportunityCostEngine, assess, utilization_pressure  # noqa: F401
    import forge.runtime  # noqa: F401
