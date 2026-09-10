"""Discoverability test package."""

import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

disc_scripts_dir = REPO_ROOT / "skills" / "ai-discoverability" / "scripts"
disc_init_file = disc_scripts_dir / "__init__.py"

if disc_init_file.exists() and "skills.ai_discoverability.scripts" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "skills.ai_discoverability.scripts",
        str(disc_init_file),
        submodule_search_locations=[str(disc_scripts_dir)],
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules["skills.ai_discoverability"] = module
        sys.modules["skills.ai_discoverability.scripts"] = module
        spec.loader.exec_module(module)
