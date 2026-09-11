"""Unit and contract tests for input, finding, and report schemas."""

import json
from pathlib import Path
import pytest
from skills.audit_orchestrator.scripts import (
    AuditFinding,
    AuditReport,
    AuditSummary,
    SuggestedAction,
    validate_input_url,
    validate_finding,
)


class TestContractsAndSchemas:

    def test_input_url_validation(self):
        # Valid URLs
        valid, url = validate_input_url("https://example.com")
        assert valid and url == "https://example.com"

        valid, url = validate_input_url("http://sub.domain.org/path")
        assert valid and url == "http://sub.domain.org/path"

        valid, url = validate_input_url("example.com")
        assert valid and url == "https://example.com"

        # Invalid URLs
        valid, err = validate_input_url("")
        assert not valid

        valid, err = validate_input_url("ftp://invalid-scheme.com")
        assert not valid

        valid, err = validate_input_url("not a url at all")
        assert not valid

    def test_json_schemas_exist_and_are_valid_json(self):
        ref_dir = Path(__file__).parents[2] / "skills" / "audit-orchestrator" / "references"
        schemas = ["input_schema.json", "finding_schema.json", "report_schema.json"]

        for schema_file in schemas:
            path = ref_dir / schema_file
            assert path.exists(), f"Missing schema file {schema_file}"
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert "$schema" in data
                assert "title" in data
                assert data.get("type") == "object"

    def test_marketplace_manifest_validity(self):
        manifest_path = Path(__file__).parents[2] / "marketplace.json"
        assert manifest_path.exists(), "marketplace.json must exist at root"

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["entrypoint"] == "audit-orchestrator"
        assert isinstance(manifest["skills"], list)
        assert len(manifest["skills"]) == 3

        skill_names = [s["name"] for s in manifest["skills"]]
        assert "audit-orchestrator" in skill_names
        assert "ai-discoverability" in skill_names
        assert "engagement-audit" in skill_names

        # Verify only one entrypoint skill
        entrypoints = [s for s in manifest["skills"] if s.get("entrypoint") is True]
        assert len(entrypoints) == 1
        assert entrypoints[0]["name"] == "audit-orchestrator"
