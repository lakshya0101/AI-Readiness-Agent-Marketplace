"""Contract and interface tests for the AI Discoverability module."""

import importlib.util
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure REPO_ROOT is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Register 'skills.ai_discoverability' alias for kebab-case directory
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

from skills.ai_discoverability.scripts import (
    audit_discoverability,
    DiscoverabilityAuditor,
    FindingFactory,
    FindingValidationError,
    HttpResponse,
)

DISC_ID_REGEX = re.compile(r"^DISC-[0-9]{3,4}$")


def _make_mock_response(url: str, status_code: int = 200, body: bytes = b"", headers: dict = None, redirect_chain: list = None, error: str = None) -> HttpResponse:
    return HttpResponse(
        requested_url=url,
        final_url=url,
        status_code=status_code,
        redirect_chain=redirect_chain or [],
        headers=headers or {"content-type": "text/html; charset=utf-8"},
        body=body,
        error=error,
    )


class TestAIDiscoverabilityContract(unittest.TestCase):

    def test_01_public_import_works(self):
        """Verify public entrypoint and core auditor are importable and callable."""
        self.assertTrue(callable(audit_discoverability))
        self.assertTrue(isinstance(DiscoverabilityAuditor, type))
        self.assertTrue(isinstance(FindingFactory, type))

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_02_audit_discoverability_returns_dict(self, mock_fetch):
        """Verify audit_discoverability returns a dictionary."""
        mock_fetch.return_value = _make_mock_response(
            "https://example.com",
            status_code=200,
            body=b"<html><head><title>Test</title></head><body>Welcome</body></html>",
        )

        result = audit_discoverability("https://example.com")
        self.assertIsInstance(result, dict)

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_03_successful_envelope_structure(self, mock_fetch):
        """Verify the exact envelope keys and values on successful audit execution."""
        mock_fetch.return_value = _make_mock_response(
            "https://example.com",
            status_code=200,
            body=b"<html><head><title>Test</title></head><body>Welcome</body></html>",
        )

        result = audit_discoverability("https://example.com")

        # Required envelope shape
        self.assertEqual(result["skill"], "ai-discoverability")
        self.assertEqual(result["status"], "success")
        self.assertIsInstance(result["findings"], list)
        self.assertIsNone(result["error"])
        self.assertIsInstance(result["limitations"], list)

    def test_04_failure_envelope_structure(self):
        """Verify the failure envelope when given an invalid target input."""
        # Empty string
        res_empty = audit_discoverability("")
        self.assertEqual(res_empty["skill"], "ai-discoverability")
        self.assertEqual(res_empty["status"], "failure")
        self.assertIsInstance(res_empty["findings"], list)
        self.assertEqual(res_empty["findings"], [])
        self.assertIsInstance(res_empty["error"], str)
        self.assertGreater(len(res_empty["error"]), 0)
        self.assertIsInstance(res_empty["limitations"], list)

        # Invalid domain
        res_invalid = audit_discoverability("http://invalid_domain")
        self.assertEqual(res_invalid["skill"], "ai-discoverability")
        self.assertEqual(res_invalid["status"], "failure")
        self.assertIn("Invalid domain structure", res_invalid["error"])

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_05_finding_id_format(self, mock_fetch):
        """Verify all generated findings strictly conform to the DISC-### pattern."""
        def side_effect_fetch(url):
            if "robots.txt" in url:
                return _make_mock_response(url, 200, b"User-agent: *\nDisallow: /")
            return _make_mock_response(url, 200, b"<html><body>Hello</body></html>")

        mock_fetch.side_effect = side_effect_fetch

        result = audit_discoverability("https://example.com")
        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["findings"]), 0)

        for f in result["findings"]:
            self.assertTrue(
                DISC_ID_REGEX.match(f["id"]),
                f"Finding ID '{f['id']}' does not match DISC-### format",
            )

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_06_category_is_ai_discoverability(self, mock_fetch):
        """Verify the category is strictly 'ai_discoverability' with underscore."""
        def side_effect_fetch(url):
            if "robots.txt" in url:
                return _make_mock_response(url, 200, b"User-agent: GPTBot\nDisallow: /")
            return _make_mock_response(url, 200, b"<html><body>Hello</body></html>")

        mock_fetch.side_effect = side_effect_fetch

        result = audit_discoverability("https://example.com")
        self.assertGreater(len(result["findings"]), 0)

        for f in result["findings"]:
            self.assertEqual(f["category"], "ai_discoverability")
            self.assertNotEqual(f["category"], "ai-discoverability")

    def test_07_invalid_finding_rejected_by_factory(self):
        """Verify FindingFactory rejects malformed findings."""
        factory = FindingFactory()

        # Missing title
        with self.assertRaises(FindingValidationError):
            factory.create_finding(
                subcategory="crawlability",
                title="",  # Invalid
                severity="high",
                evidence="Valid observable evidence snippet",
                why_it_matters="Impact explanation",
                suggested_action_summary="Action summary",
                suggested_action_details="Action details",
            )

        # Non DISC ID
        with self.assertRaises(FindingValidationError):
            factory.create_finding(
                subcategory="crawlability",
                title="Valid title",
                severity="high",
                evidence="Valid observable evidence snippet",
                why_it_matters="Impact explanation",
                suggested_action_summary="Action summary",
                suggested_action_details="Action details",
                finding_id="INVALID-001",
            )

    def test_08_empty_evidence_cannot_produce_finding(self):
        """Verify the evidence invariant: empty or generic evidence is strictly rejected."""
        factory = FindingFactory()

        # Blank evidence
        with self.assertRaises(FindingValidationError):
            factory.create_finding(
                subcategory="crawlability",
                title="Crawler issue",
                severity="high",
                evidence="",  # Empty
                why_it_matters="Impact explanation",
                suggested_action_summary="Action summary",
                suggested_action_details="Action details",
            )

        # Whitespace-only evidence
        with self.assertRaises(FindingValidationError):
            factory.create_finding(
                subcategory="crawlability",
                title="Crawler issue",
                severity="high",
                evidence="    ",  # Whitespace
                why_it_matters="Impact explanation",
                suggested_action_summary="Action summary",
                suggested_action_details="Action details",
            )

    def test_09_invalid_severity_rejected(self):
        """Verify only allowed canonical severities (critical, high, medium, low) are accepted."""
        factory = FindingFactory()

        for invalid_sev in ["fatal", "blocker", "warn", "minor", "unknown"]:
            with self.assertRaises(FindingValidationError):
                factory.create_finding(
                    subcategory="crawlability",
                    title="Issue title",
                    severity=invalid_sev,
                    evidence="Observable evidence",
                    why_it_matters="Impact explanation",
                    suggested_action_summary="Action summary",
                    suggested_action_details="Action details",
                )

    def test_10_suggested_action_structure_validated(self):
        """Verify suggested_action requires summary, details, and valid priority."""
        factory = FindingFactory()

        # Invalid priority
        with self.assertRaises(FindingValidationError):
            factory.create_finding(
                subcategory="crawlability",
                title="Issue title",
                severity="high",
                evidence="Observable evidence",
                why_it_matters="Impact explanation",
                suggested_action_summary="Action summary",
                suggested_action_details="Action details",
                suggested_action_priority="URGENT",  # Invalid
            )

        # Missing summary
        with self.assertRaises(FindingValidationError):
            factory.create_finding(
                subcategory="crawlability",
                title="Issue title",
                severity="high",
                evidence="Observable evidence",
                why_it_matters="Impact explanation",
                suggested_action_summary="",  # Empty
                suggested_action_details="Action details",
            )

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_11_entrypoint_does_not_leak_network_exceptions(self, mock_fetch):
        """Verify public entrypoint captures network failures without leaking unhandled exceptions."""
        # Fatal network connection failure on target root
        mock_fetch.return_value = _make_mock_response(
            "https://example.com",
            status_code=0,
            body=b"",
            error="Network error: [Errno -2] Name or service not known",
        )
        res = audit_discoverability("https://example.com")
        self.assertEqual(res["status"], "failure")
        self.assertIn("Failed to connect", res["error"])
        self.assertEqual(res["findings"], [])

    def test_12_finding_optional_fields_support(self):
        """Verify optional metadata fields are cleanly attached when valid."""
        factory = FindingFactory()
        finding = factory.create_finding(
            subcategory="structured_data",
            title="Missing Schema.org Organization",
            severity="high",
            evidence="No JSON-LD script found in head or body",
            why_it_matters="LLMs cannot disambiguate entity identity",
            suggested_action_summary="Add Organization JSON-LD",
            suggested_action_details="Embed script with @type Organization",
            suggested_action_priority="high",
            confidence="high",
            affected_pages=["https://example.com/"],
            evidence_type="SCHEMA_ORG",
            methodology="Extract",
            remediation_complexity="low",
            references=["https://schema.org/Organization"],
        )

        self.assertEqual(finding["confidence"], "high")
        self.assertEqual(finding["affected_pages"], ["https://example.com/"])
        self.assertEqual(finding["evidence_type"], "SCHEMA_ORG")
        self.assertEqual(finding["methodology"], "Extract")
        self.assertEqual(finding["remediation_complexity"], "low")
        self.assertEqual(finding["references"], ["https://schema.org/Organization"])

    def test_13_discoverability_auditor_custom_options(self):
        """Verify DiscoverabilityAuditor honors custom configuration options."""
        auditor = DiscoverabilityAuditor(options={"timeout": 5, "user_agent": "CustomAgent/2.0", "max_pages": 3})
        self.assertEqual(auditor.timeout, 5)
        self.assertEqual(auditor.user_agent, "CustomAgent/2.0")
        self.assertEqual(auditor.max_pages, 3)


if __name__ == "__main__":
    unittest.main()
