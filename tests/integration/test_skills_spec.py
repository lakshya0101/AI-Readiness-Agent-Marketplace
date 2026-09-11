"""Tests validating compliance of all SKILL.md files against the Agent Skills specification."""

from pathlib import Path
import re
import pytest

SKILL_NAME_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_yaml_frontmatter(content: str) -> dict:
    """Parses frontmatter from a markdown string."""
    if not content.startswith("---"):
        raise ValueError("File does not start with YAML frontmatter delimiters (---)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Unterminated YAML frontmatter delimiters")

    yaml_block = parts[1].strip()
    data = {}
    for line in yaml_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            data[key.strip()] = val.strip().strip("\"'")
    return data


class TestAgentSkillsSpecification:

    @pytest.fixture
    def skills_root(self):
        return Path(__file__).parents[2] / "skills"

    def test_all_skills_have_compliant_skill_md(self, skills_root):
        skill_dirs = [d for d in skills_root.iterdir() if d.is_dir() and not d.name.startswith(".")]
        assert len(skill_dirs) == 3, f"Expected 3 skills, found: {[d.name for d in skill_dirs]}"

        for skill_dir in skill_dirs:
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists(), f"Missing SKILL.md in {skill_dir.name}"

            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()

            frontmatter = parse_yaml_frontmatter(content)

            # 1. Name validation
            assert "name" in frontmatter, f"Missing 'name' in frontmatter for {skill_dir.name}"
            skill_name = frontmatter["name"]
            assert skill_name == skill_dir.name, f"Skill name '{skill_name}' must match folder '{skill_dir.name}'"
            assert SKILL_NAME_REGEX.match(skill_name), f"Skill name '{skill_name}' violates kebab-case pattern"

            # 2. Description validation
            assert "description" in frontmatter, f"Missing 'description' in frontmatter for {skill_dir.name}"
            description = frontmatter["description"]
            assert len(description) >= 15, f"Description too short for skill {skill_name}"

            # 3. Scripts and references directories exist
            scripts_dir = skill_dir / "scripts"
            references_dir = skill_dir / "references"
            assert scripts_dir.exists() and scripts_dir.is_dir(), f"Missing scripts/ directory in {skill_name}"
            assert references_dir.exists() and references_dir.is_dir(), f"Missing references/ directory in {skill_name}"
