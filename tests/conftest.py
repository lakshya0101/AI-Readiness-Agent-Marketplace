"""Pytest configuration and module loader for kebab-case skill folders."""

import importlib.util
from pathlib import Path
import sys
import types

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure root 'skills' namespace package exists in sys.modules
if "skills" not in sys.modules:
    skills_pkg = types.ModuleType("skills")
    skills_pkg.__path__ = [str(REPO_ROOT / "skills")]
    sys.modules["skills"] = skills_pkg


def _register_skill_alias(skill_folder_name: str, python_alias: str):
    scripts_dir = REPO_ROOT / "skills" / skill_folder_name / "scripts"
    init_file = scripts_dir / "__init__.py"
    if not init_file.exists():
        return

    skills_pkg = sys.modules["skills"]
    pkg_mod = types.ModuleType(f"skills.{python_alias}")
    pkg_mod.__path__ = [str(REPO_ROOT / "skills" / skill_folder_name)]
    setattr(skills_pkg, python_alias, pkg_mod)
    sys.modules[f"skills.{python_alias}"] = pkg_mod

    spec = importlib.util.spec_from_file_location(
        f"skills.{python_alias}.scripts",
        str(init_file),
        submodule_search_locations=[str(scripts_dir)],
    )
    if spec and spec.loader:
        scripts_mod = importlib.util.module_from_spec(spec)
        setattr(pkg_mod, "scripts", scripts_mod)
        sys.modules[f"skills_{python_alias}"] = scripts_mod
        sys.modules[f"skills.{python_alias}.scripts"] = scripts_mod
        spec.loader.exec_module(scripts_mod)

        # Expose sub-classes on shadowed module/function names for unittest.mock.patch path traversal
        if hasattr(scripts_mod, "audit_discoverability"):
            for attr_name in ("HttpClient", "DiscoverabilityAuditor", "FindingFactory"):
                if hasattr(scripts_mod, attr_name):
                    setattr(scripts_mod.audit_discoverability, attr_name, getattr(scripts_mod, attr_name))


# Register audit-orchestrator
_register_skill_alias("audit-orchestrator", "audit_orchestrator")

# Register ai-discoverability
_register_skill_alias("ai-discoverability", "ai_discoverability")

# Register engagement-audit
_register_skill_alias("engagement-audit", "engagement_audit")
