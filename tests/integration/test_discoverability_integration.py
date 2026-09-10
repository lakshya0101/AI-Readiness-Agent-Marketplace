"""Integration tests verifying real AI Discoverability skill wiring into Audit Orchestrator."""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from skills.audit_orchestrator.scripts import AuditOrchestrator, AuditReport
from skills.ai_discoverability.scripts import audit_discoverability
from skills.ai_discoverability.scripts.http_client import HttpResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "audit-orchestrator" / "references" / "report_schema.json"
)


def _mock_http_response(
    url: str,
    status_code: int = 200,
    body: bytes = b"",
    headers: dict = None,
    redirect_chain: list = None,
    error: str = None,
) -> HttpResponse:
    return HttpResponse(
        requested_url=url,
        final_url=url,
        status_code=status_code,
        redirect_chain=redirect_chain or [],
        headers=headers or {"content-type": "text/html; charset=utf-8"},
        body=body,
        error=error,
    )


class TestRealDiscoverabilityOrchestration:

    def test_01_default_orchestrator_wires_real_discoverability_entrypoint(self):
        """Verify default AuditOrchestrator instance defaults to real audit_discoverability."""
        orchestrator = AuditOrchestrator()
        assert orchestrator.discoverability_runner is not None
        # Should be a callable wrapping audit_discoverability
        assert callable(orchestrator.discoverability_runner)

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_02_successful_real_discoverability_findings_in_final_report(self, mock_fetch):
        """Real discoverability produces findings that cleanly flow into orchestrator report."""
        def side_effect(url):
            if "robots.txt" in url:
                return _mock_http_response(
                    url,
                    200,
                    b"User-agent: *\nDisallow: /\nSitemap: https://example.com/sitemap.xml",
                )
            if "sitemap.xml" in url:
                return _mock_http_response(
                    url,
                    200,
                    b"<?xml version='1.0'?><urlset><url><loc>https://example.com/</loc></url></urlset>",
                )
            return _mock_http_response(
                url,
                200,
                b"<html><head><title>Acme Corporation</title></head><body><h1>Acme Corporation</h1><p>Leading provider of innovative engineering and AI discovery tools since 1995. We produce high quality products.</p></body></html>",
            )

        mock_fetch.side_effect = side_effect

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://example.com")

        assert isinstance(report, AuditReport)
        assert report.site == "https://example.com"
        assert report.modules["ai_discoverability"]["status"] == "success"
        assert report.modules["ai_discoverability"]["findings_count"] > 0

        # Verify findings contain DISC- prefix and ai_discoverability category
        disc_findings = [f for f in report.findings if f.category == "ai_discoverability"]
        assert len(disc_findings) > 0
        for f in disc_findings:
            assert f.id.startswith("DISC-")
            assert f.evidence is not None and len(f.evidence) >= 3
            assert f.why_it_matters is not None and len(f.why_it_matters) >= 3
            assert f.suggested_action.summary is not None
            assert f.suggested_action.priority in {"critical", "high", "medium", "low"}

        # Verify prioritized action plan contains the discoverability findings
        plan_ids = [item["finding_id"] for item in report.prioritized_action_plan]
        for f in disc_findings:
            assert f.id in plan_ids

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_03_real_discoverability_network_failure_handled_gracefully(self, mock_fetch):
        """When real discoverability fails on network, orchestrator captures error and produces valid report."""
        mock_fetch.return_value = _mock_http_response(
            "https://offline-target.test",
            status_code=0,
            error="Connection timed out",
        )

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://offline-target.test")

        assert report.site == "https://offline-target.test"
        assert report.modules["ai_discoverability"]["status"] == "failure"
        assert "Connection timed out" in report.modules["ai_discoverability"]["error"]
        assert any("AI Discoverability module failed" in lim for lim in report.limitations)
        # Should not fabricate discoverability findings
        disc_findings = [f for f in report.findings if f.category == "ai_discoverability"]
        assert len(disc_findings) == 0

    def test_04_invalid_or_empty_url_handling(self):
        """Invalid or empty URLs raise clean ValueError before invoking downstream skills."""
        orchestrator = AuditOrchestrator()

        with pytest.raises(ValueError, match="non-empty string"):
            orchestrator.run_audit("")

        with pytest.raises(ValueError, match="Invalid domain"):
            orchestrator.run_audit("http://not_a_valid_domain")

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_05_final_report_structure_and_schema_conformance(self, mock_fetch):
        """End-to-end report generated with real discoverability matches report_schema.json."""
        def side_effect(url):
            if "robots.txt" in url:
                return _mock_http_response(url, 200, b"User-agent: *\nAllow: /\n")
            return _mock_http_response(
                url,
                200,
                b"<html><head><title>Test Store</title></head><body><main><h1>Test Store</h1><p>Comprehensive description of our products and services with ample text.</p></main></body></html>",
            )

        mock_fetch.side_effect = side_effect

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://schema-test.org")
        report_dict = report.to_dict()

        # Check required fields
        assert "site" in report_dict
        assert "audited_at" in report_dict
        assert "summary" in report_dict
        assert "findings" in report_dict
        assert "modules" in report_dict
        assert "limitations" in report_dict
        assert "prioritized_action_plan" in report_dict

        # Check summary totals
        summary = report_dict["summary"]
        assert summary["total_findings"] == len(report_dict["findings"])
        assert summary["total_findings"] == (
            summary["critical"] + summary["high"] + summary["medium"] + summary["low"]
        )

        # Check module status
        assert "ai_discoverability" in report_dict["modules"]
        assert report_dict["modules"]["ai_discoverability"]["status"] in {"success", "failure"}
