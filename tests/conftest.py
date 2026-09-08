"""Pytest configuration and module loader for kebab-case skill folders."""

import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Register 'skills.audit_orchestrator' alias pointing to 'skills/audit-orchestrator'
scripts_dir = REPO_ROOT / "skills" / "audit-orchestrator" / "scripts"
init_file = scripts_dir / "__init__.py"

if init_file.exists():
    spec = importlib.util.spec_from_file_location(
        "skills_audit_orchestrator",
        str(init_file),
        submodule_search_locations=[str(scripts_dir)],
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules["skills_audit_orchestrator"] = module
        sys.modules["skills.audit_orchestrator"] = module
        sys.modules["skills.audit_orchestrator.scripts"] = module
        spec.loader.exec_module(module)
