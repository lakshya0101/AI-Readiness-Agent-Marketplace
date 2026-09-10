"""Build and validate final release ZIP for Adobe Agent Marketplace."""

import os
import zipfile
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = "AI-Readiness-Agent-Marketplace.zip"
ZIP_PATH = REPO_ROOT / ZIP_NAME
TOP_DIR = "AI-Readiness-Agent-Marketplace"

# Exclusion patterns
EXCLUDE_DIRS = {
    ".git",
    ".github",
    ".pytest_cache",
    "__pycache__",
    ".vscode",
    ".idea",
    "tmp",
    "scratch",
    "venv",
    ".venv",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".swp",
    ".swo",
    ".DS_Store",
}

EXCLUDE_FILES = {
    ZIP_NAME,
    "package_release.py",
}


def build_zip():
    print(f"Building {ZIP_NAME} from {REPO_ROOT}...")
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    included_files = []
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(REPO_ROOT):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.endswith(".egg-info")]

            rel_root = Path(root).relative_to(REPO_ROOT)
            for file in files:
                if file in EXCLUDE_FILES or any(file.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                    continue

                abs_file = Path(root) / file
                arcname = str(Path(TOP_DIR) / rel_root / file).replace("\\", "/")
                zf.write(abs_file, arcname)
                included_files.append((arcname, abs_file.stat().st_size))

    size_bytes = ZIP_PATH.stat().st_size
    size_kb = size_bytes / 1024
    size_mb = size_kb / 1024
    print(f"Created {ZIP_NAME}: {size_bytes:,} bytes ({size_kb:.1f} KB / {size_mb:.2f} MB)")
    print(f"Total files packaged: {len(included_files)}")
    return included_files, size_bytes


def validate_extracted():
    temp_dir = REPO_ROOT / "tmp_validation_extract"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        print(f"Extracting {ZIP_NAME} to {temp_dir} for independent verification...")
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            zf.extractall(temp_dir)

        extracted_root = temp_dir / TOP_DIR
        assert extracted_root.exists(), "Extracted top-level directory missing!"
        assert (extracted_root / "marketplace.json").exists(), "marketplace.json missing in extracted package!"
        assert (extracted_root / "README.md").exists(), "README.md missing in extracted package!"
        assert (extracted_root / "LICENSE").exists(), "LICENSE missing in extracted package!"
        assert (extracted_root / "skills" / "audit-orchestrator" / "SKILL.md").exists()
        assert (extracted_root / "skills" / "ai-discoverability" / "SKILL.md").exists()
        assert (extracted_root / "skills" / "engagement-audit" / "SKILL.md").exists()

        # Run orchestrator help on extracted package
        orch_script = extracted_root / "skills" / "audit-orchestrator" / "scripts" / "orchestrator.py"
        res = subprocess.run(
            [sys.executable, str(orch_script), "--help"],
            cwd=str(extracted_root),
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Extracted orchestrator --help failed: {res.stderr}"

        # Run full pytest in extracted package
        res_test = subprocess.run(
            [sys.executable, "-m", "pytest", "-v"],
            cwd=str(extracted_root),
            capture_output=True,
            text=True,
        )
        assert res_test.returncode == 0, f"Extracted pytest suite failed: {res_test.stderr}\n{res_test.stdout}"
        print(f"Extracted package test suite passed completely!")

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    build_zip()
    validate_extracted()
