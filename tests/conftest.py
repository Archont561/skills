"""Make the scripts/ package importable from tests (repo root on sys.path)."""

import importlib.util
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_counter = itertools.count()


def load_skill_module(core_dir: Path, stem: str = "runtime"):
    """Import <core_dir>/<stem>.py under a UNIQUE module name.

    Several tests import runtime.py from different locations (repo copy vs
    tmp consumer installs); a plain `import runtime` would silently reuse the
    first cached module for everyone. This bypasses sys.modules collisions.
    """
    path = Path(core_dir) / f"{stem}.py"
    name = f"arch561_{stem}_{next(_counter)}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # dataclasses resolve cls.__module__ via sys.modules during exec_module
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module
