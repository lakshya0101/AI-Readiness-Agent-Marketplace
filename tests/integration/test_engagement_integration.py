"""Integration tests verifying real On-Site Engagement skill wiring into Audit Orchestrator."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from skills.audit_orchestrator.scripts import AuditOrchestrator, AuditReport
from skills.engagement_audit.scripts import audit_engagement
from skills.ai_discoverability.scripts.http_client import HttpResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "audit-orchestrator" / "references" / "report_schema.json"
)


def _mock_disc_response(url: str, body: bytes = b"") -> HttpResponse:
    return HttpResponse(
        requested_url=url,
        final_url=url,
        status_code=200,
        redirect_chain=[],
        headers={"content-type": "text/html; charset=utf-8"},
        body=body,
    )


class TestRealEngagementOrchestration:

    def test_01_default_orchestrator_wires_real_engagement_entrypoint(self):
        """Verify default AuditOrchestrator instance defaults to real audit_engagement."""
        orchestrator = AuditOrchestrator()
        assert orchestrator.engagement_runner is not None
        assert callable(orchestrator.engagement_runner)

    def test_02_direct_real_audit_engagement_invocation(self):
        """Verify public audit_engagement entrypoint returns standard envelope and findings."""
        sample_html = "<html><head><title>Product</title></head><body><h1>Product</h1><p>Description</p></body></html>"
        result = audit_engagement("https://example.com/product/1", options={"inferred_page_type": "product"}, html=sample_html)
        assert isinstance(result, dict)
        assert result["skill"] == "engagement-audit"
        assert result["status"] == "success"
        assert isinstance(result["findings"], list)
        assert len(result["findings"]) > 0
        finding = result["findings"][0]
        assert finding["id"].startswith("ENG-")
        assert finding["category"] == "on_site_engagement"
        assert "evidence" in finding and len(finding["evidence"]) >= 3
        assert "suggested_action" in finding
        assert finding["suggested_action"]["priority"] in {"critical", "high", "medium", "low"}

    @patch("urllib.request.urlopen")
    def test_03_successful_engagement_findings_propagate_to_report(self, mock_urlopen):
        """Successful engagement evaluation produces findings in final report & action plan."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b"<html><head><title></title></head><body></body></html>"
        )
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://empty-landing.org")

        assert isinstance(report, AuditReport)
        assert report.site == "https://empty-landing.org"
        assert report.modules["on_site_engagement"]["status"] == "success"
        assert report.modules["on_site_engagement"]["findings_count"] > 0

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        assert len(eng_findings) > 0
        for f in eng_findings:
            assert f.id.startswith("ENG-")
            assert f.category == "on_site_engagement"
            assert f.subcategory in {"landing", "orientation", "deep-entry", "navigation", "actionability"}
            assert f.severity in {"critical", "high", "medium", "low"}
            assert len(f.evidence) >= 3
            assert len(f.why_it_matters) >= 3
            assert f.suggested_action.summary is not None
            assert f.suggested_action.details is not None
            assert f.suggested_action.priority in {"critical", "high", "medium", "low"}

        # Verify findings are present in prioritized_action_plan
        plan_finding_ids = [item["finding_id"] for item in report.prioritized_action_plan]
        for f in eng_findings:
            assert f.id in plan_finding_ids

    @patch("urllib.request.urlopen")
    def test_04_engagement_network_failure_handled_gracefully(self, mock_urlopen):
        """When engagement audit encounters network failure, it records failure without throwing."""
        mock_urlopen.side_effect = Exception("Connection refused by peer")

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://unreachable-host.local")

        assert report.site == "https://unreachable-host.local"
        assert report.modules["on_site_engagement"]["status"] == "failure"
        assert "Connection refused" in report.modules["on_site_engagement"]["error"]
        assert any("On-Site Engagement module failed" in lim for lim in report.limitations)
        # Ensure zero fabricated findings
        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        assert len(eng_findings) == 0

    def test_05_engagement_runner_crash_does_not_crash_orchestrator(self):
        """If engagement runner raises an unhandled exception, orchestrator catches it gracefully."""
        def crashing_eng(url: str):
            raise RuntimeError("Fatal memory allocator failure in parser")

        orchestrator = AuditOrchestrator(engagement_runner=crashing_eng)
        report = orchestrator.run_audit("https://example.com")

        assert report.modules["on_site_engagement"]["status"] == "failure"
        assert "Fatal memory allocator failure" in report.modules["on_site_engagement"]["error"]
        assert any("On-Site Engagement execution crashed" in lim for lim in report.limitations)

    def test_06_discoverability_findings_survive_when_engagement_fails(self):
        """When engagement fails, discoverability findings still populate the final report."""
        def sample_disc(site: str):
            return {
                "skill": "ai-discoverability",
                "status": "success",
                "findings": [
                    {
                        "id": "DISC-101",
                        "category": "ai_discoverability",
                        "subcategory": "crawlability",
                        "title": "Robots.txt blocks AI crawler user agents",
                        "severity": "high",
                        "evidence": "Disallow: / for GPTBot in robots.txt.",
                        "why_it_matters": "Prevents AI search engines from indexing content.",
                        "suggested_action": {
                            "summary": "Update robots.txt rules",
                            "details": "Allow AI bots.",
                            "priority": "high",
                        },
                    }
                ],
            }

        def failing_eng(site: str):
            return {
                "skill": "engagement-audit",
                "status": "failure",
                "findings": [],
                "error": "HTML parser crashed unexpectedly",
            }

        orchestrator = AuditOrchestrator(
            discoverability_runner=sample_disc,
            engagement_runner=failing_eng,
        )
        report = orchestrator.run_audit("https://partial-success.com")

        assert report.modules["ai_discoverability"]["status"] == "success"
        assert report.modules["on_site_engagement"]["status"] == "failure"
        assert len(report.findings) == 1
        assert report.findings[0].id == "DISC-101"
        assert report.summary.total_findings == 1
        assert report.summary.high == 1

    def test_07_engagement_findings_survive_when_discoverability_fails(self):
        """When discoverability fails, engagement findings still populate the final report."""
        def failing_disc(site: str):
            return {
                "skill": "ai-discoverability",
                "status": "failure",
                "findings": [],
                "error": "DNS resolution failed",
            }

        def sample_eng(site: str):
            return {
                "skill": "engagement-audit",
                "status": "success",
                "findings": [
                    {
                        "id": "ENG-301",
                        "category": "on_site_engagement",
                        "subcategory": "deep-entry",
                        "title": "Total loss of site context on deep entry",
                        "severity": "critical",
                        "evidence": "0 global navigation links and no breadcrumbs.",
                        "why_it_matters": "Direct visitors lose all brand orientation.",
                        "suggested_action": {
                            "summary": "Add global header and breadcrumbs",
                            "details": "Implement persistent top nav.",
                            "priority": "critical",
                        },
                    }
                ],
            }

        orchestrator = AuditOrchestrator(
            discoverability_runner=failing_disc,
            engagement_runner=sample_eng,
        )
        report = orchestrator.run_audit("https://partial-success.com")

        assert report.modules["ai_discoverability"]["status"] == "failure"
        assert report.modules["on_site_engagement"]["status"] == "success"
        assert len(report.findings) == 1
        assert report.findings[0].id == "ENG-301"
        assert report.summary.total_findings == 1
        assert report.summary.critical == 1

    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_08_both_real_modules_execute_successfully_together(self, mock_disc_fetch, mock_eng_urlopen):
        """Both real discoverability and real engagement skills execute and aggregate together."""
        # Mock discoverability HTTP calls
        def disc_side_effect(url):
            if "robots.txt" in url:
                return _mock_disc_response(url, b"User-agent: *\nDisallow: /\n")
            return _mock_disc_response(
                url,
                b"<html><head><title>Test Store</title></head><body><h1>Test Store</h1><p>Description text.</p></body></html>",
            )
        mock_disc_fetch.side_effect = disc_side_effect

        # Mock engagement HTTP call (returns minimal page missing actionability and headings)
        mock_eng_resp = MagicMock()
        mock_eng_resp.read.return_value = (
            b"<html><head><title></title></head><body><p>Bare text</p></body></html>"
        )
        mock_eng_resp.__enter__.return_value = mock_eng_resp
        mock_eng_urlopen.return_value = mock_eng_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://dual-audit.org")

        assert report.modules["ai_discoverability"]["status"] == "success"
        assert report.modules["on_site_engagement"]["status"] == "success"

        categories_present = {f.category for f in report.findings}
        assert "ai_discoverability" in categories_present
        assert "on_site_engagement" in categories_present

        # Verify summary sums
        assert report.summary.total_findings == len(report.findings)
        assert report.summary.total_findings == (
            report.summary.critical + report.summary.high + report.summary.medium + report.summary.low
        )

        # Ensure limitations from both modules are preserved
        assert len(report.limitations) > 0
