"""Integration tests for the Audit Orchestrator pipeline."""

import pytest
from skills.audit_orchestrator.scripts import (
    AuditOrchestrator,
    AuditFinding,
    SuggestedAction,
    validate_finding,
    deduplicate_findings,
    normalize_severity,
    calculate_priority,
)
from skills.audit_orchestrator.scripts.mock_modules import (
    get_mock_discoverability_success,
    get_mock_engagement_success,
    get_mock_module_failure,
)


class TestOrchestrationPipeline:

    def test_01_empty_findings(self):
        """Orchestrator runs successfully when both modules report zero findings."""
        def empty_disc(site: str):
            return {"skill": "ai-discoverability", "status": "success", "findings": []}

        def empty_eng(site: str):
            return {"skill": "engagement-audit", "status": "success", "findings": []}

        orchestrator = AuditOrchestrator(
            discoverability_runner=empty_disc,
            engagement_runner=empty_eng,
        )
        report = orchestrator.run_audit("https://clean-site.org")

        assert report.site == "https://clean-site.org"
        assert report.summary.total_findings == 0
        assert report.summary.critical == 0
        assert report.summary.high == 0
        assert report.summary.medium == 0
        assert report.summary.low == 0
        assert len(report.findings) == 0
        assert report.modules["ai_discoverability"]["status"] == "success"
        assert report.modules["on_site_engagement"]["status"] == "success"

    def test_02_one_discoverability_finding(self):
        """Orchestrator correctly processes a single discoverability finding."""
        def single_disc(site: str):
            return {
                "skill": "ai-discoverability",
                "status": "success",
                "findings": [
                    {
                        "id": "DISC-001",
                        "category": "ai_discoverability",
                        "subcategory": "structured_data",
                        "title": "Missing Schema.org JSON-LD",
                        "severity": "high",
                        "evidence": "No JSON-LD tags observed in page body.",
                        "why_it_matters": "Impedes entity disambiguation.",
                        "suggested_action": {
                            "summary": "Add Schema.org JSON-LD",
                            "details": "Embed Organization markup.",
                            "priority": "high",
                        },
                    }
                ],
            }

        def empty_eng(site: str):
            return {"skill": "engagement-audit", "status": "success", "findings": []}

        orchestrator = AuditOrchestrator(
            discoverability_runner=single_disc,
            engagement_runner=empty_eng,
        )
        report = orchestrator.run_audit("https://example.com")

        assert report.summary.total_findings == 1
        assert report.summary.high == 1
        assert report.findings[0].id == "DISC-001"
        assert report.findings[0].category == "ai_discoverability"

    def test_03_one_engagement_finding(self):
        """Orchestrator correctly processes a single engagement finding."""
        def empty_disc(site: str):
            return {"skill": "ai-discoverability", "status": "success", "findings": []}

        def single_eng(site: str):
            return {
                "skill": "engagement-audit",
                "status": "success",
                "findings": [
                    {
                        "id": "ENG-001",
                        "category": "on_site_engagement",
                        "subcategory": "orientation",
                        "title": "Hero section missing H1 headline",
                        "severity": "medium",
                        "evidence": "Computed DOM has no H1 element in hero viewport.",
                        "why_it_matters": "Visitors bounce without immediate context.",
                        "suggested_action": {
                            "summary": "Add hero H1 headline",
                            "details": "Place descriptive value proposition H1 in hero.",
                            "priority": "medium",
                        },
                    }
                ],
            }

        orchestrator = AuditOrchestrator(
            discoverability_runner=empty_disc,
            engagement_runner=single_eng,
        )
        report = orchestrator.run_audit("https://example.com")

        assert report.summary.total_findings == 1
        assert report.summary.medium == 1
        assert report.findings[0].id == "ENG-001"
        assert report.findings[0].category == "on_site_engagement"

    def test_04_findings_from_both_modules(self):
        """Orchestrator successfully aggregates findings from both modules."""
        orchestrator = AuditOrchestrator(
            discoverability_runner=get_mock_discoverability_success,
            engagement_runner=get_mock_engagement_success,
        )
        report = orchestrator.run_audit("https://example.com")

        assert report.summary.total_findings == 4
        assert report.summary.high == 2
        assert report.summary.medium == 2
        assert len(report.findings) == 4
        categories = {f.category for f in report.findings}
        assert "ai_discoverability" in categories
        assert "on_site_engagement" in categories
        assert len(report.prioritized_action_plan) == 4

    def test_05_duplicate_findings_deduplication(self):
        """Orchestrator deduplicates overlapping findings and merges evidence conservatively."""
        def disc_with_dupes(site: str):
            return {
                "skill": "ai-discoverability",
                "status": "success",
                "findings": [
                    {
                        "id": "DISC-001",
                        "category": "ai_discoverability",
                        "subcategory": "structured_data",
                        "title": "Missing Schema.org Organization JSON-LD markup",
                        "severity": "medium",
                        "evidence": "Observed on homepage /",
                        "why_it_matters": "Entity resolution failure.",
                        "suggested_action": {
                            "summary": "Add Schema.org JSON-LD",
                            "details": "Embed JSON-LD on homepage.",
                            "priority": "medium",
                        },
                        "affected_pages": ["https://example.com/"],
                    },
                    {
                        "id": "DISC-001",  # Same ID, higher severity
                        "category": "ai_discoverability",
                        "subcategory": "structured_data",
                        "title": "Missing Schema.org Organization JSON-LD markup",
                        "severity": "high",
                        "evidence": "Observed on about page /about",
                        "why_it_matters": "Entity resolution failure.",
                        "suggested_action": {
                            "summary": "Add Schema.org JSON-LD",
                            "details": "Embed JSON-LD on about page.",
                            "priority": "high",
                        },
                        "affected_pages": ["https://example.com/about"],
                    },
                ],
            }

        def empty_eng(site: str):
            return {"skill": "engagement-audit", "status": "success", "findings": []}

        orchestrator = AuditOrchestrator(
            discoverability_runner=disc_with_dupes,
            engagement_runner=empty_eng,
        )
        report = orchestrator.run_audit("https://example.com")

        assert report.summary.total_findings == 1
        assert report.summary.high == 1  # Retained higher severity
        finding = report.findings[0]
        assert "https://example.com/" in finding.affected_pages
        assert "https://example.com/about" in finding.affected_pages
        assert "homepage" in finding.evidence
        assert "about page" in finding.evidence

    def test_06_invalid_severity_normalization(self):
        """Orchestrator normalizes unconventional or uppercase severity values."""
        raw = {
            "id": "DISC-010",
            "category": "ai_discoverability",
            "subcategory": "crawlability",
            "title": "Robots.txt blocks all crawlers",
            "severity": "BLOCKER",  # Non-standard severity alias
            "evidence": "Disallow: / on User-agent: *",
            "why_it_matters": "No search engine or AI crawler can access the site.",
            "suggested_action": {
                "summary": "Fix robots.txt",
                "details": "Remove universal disallow.",
                "priority": "URGENT",
            },
        }
        finding, err = validate_finding(raw, allow_normalization=True)
        assert err is None
        assert finding is not None
        assert finding.severity == "critical"
        assert finding.suggested_action.priority == "critical"

    def test_07_missing_evidence_is_rejected_never_hallucinated(self):
        """Orchestrator strictly rejects findings with missing or empty evidence."""
        raw = {
            "id": "DISC-011",
            "category": "ai_discoverability",
            "subcategory": "crawlability",
            "title": "Suspected missing sitemap",
            "severity": "low",
            "evidence": "",  # Missing evidence
            "why_it_matters": "Sitemaps help indexing.",
            "suggested_action": {
                "summary": "Add sitemap",
                "details": "Generate sitemap.xml",
                "priority": "low",
            },
        }
        finding, err = validate_finding(raw)
        assert finding is None
        assert "evidence" in err.lower()
        assert "never be fabricated" in err.lower()

    def test_08_graceful_module_failure_handling(self):
        """Orchestrator handles single-module failure without crashing or dropping other findings."""
        def failing_disc(site: str):
            return get_mock_module_failure("ai-discoverability", "Connection timeout during crawler fetch.")

        orchestrator = AuditOrchestrator(
            discoverability_runner=failing_disc,
            engagement_runner=get_mock_engagement_success,
        )
        report = orchestrator.run_audit("https://example.com")

        # Discoverability failed, but engagement succeeded
        assert report.modules["ai_discoverability"]["status"] == "failure"
        assert "timeout" in report.modules["ai_discoverability"]["error"]
        assert report.modules["on_site_engagement"]["status"] == "success"

        # Report contains engagement findings and notes the limitation
        assert report.summary.total_findings == 2
        assert any("Discoverability module failed" in lim for lim in report.limitations)

    def test_09_multiple_severity_levels_and_ranking(self):
        """Orchestrator handles all 4 severity levels and sorts findings by severity rank."""
        def mixed_disc(site: str):
            return {
                "skill": "ai-discoverability",
                "status": "success",
                "findings": [
                    {
                        "id": "DISC-001",
                        "category": "ai_discoverability",
                        "subcategory": "sitemap",
                        "title": "Minor sitemap formatting notice",
                        "severity": "low",
                        "evidence": "Trailing slash discrepancy in sitemap URL entry.",
                        "why_it_matters": "Minor canonical redirect.",
                        "suggested_action": {"summary": "Fix trailing slash", "details": "Sync sitemap URLs.", "priority": "low"},
                    },
                    {
                        "id": "DISC-002",
                        "category": "ai_discoverability",
                        "subcategory": "crawlability",
                        "title": "Site-wide crawler block in HTTP 403",
                        "severity": "critical",
                        "evidence": "Origin server returns 403 Forbidden to all automated user agents.",
                        "why_it_matters": "Complete indexing blackout.",
                        "suggested_action": {"summary": "Remove WAF block", "details": "Configure bot access list.", "priority": "critical"},
                    },
                    {
                        "id": "DISC-003",
                        "category": "ai_discoverability",
                        "subcategory": "schema",
                        "title": "Missing Organization Schema",
                        "severity": "high",
                        "evidence": "No Organization schema found.",
                        "why_it_matters": "Entity resolution fails.",
                        "suggested_action": {"summary": "Add Schema", "details": "Add JSON-LD.", "priority": "high"},
                    },
                    {
                        "id": "DISC-004",
                        "category": "ai_discoverability",
                        "subcategory": "meta",
                        "title": "Missing OpenGraph description tag",
                        "severity": "medium",
                        "evidence": "og:description missing on 2 subpages.",
                        "why_it_matters": "Social and AI snippet generator falls back to raw text.",
                        "suggested_action": {"summary": "Add og:description", "details": "Set meta description.", "priority": "medium"},
                    },
                ],
            }

        def empty_eng(site: str):
            return {"skill": "engagement-audit", "status": "success", "findings": []}

        orchestrator = AuditOrchestrator(
            discoverability_runner=mixed_disc,
            engagement_runner=empty_eng,
        )
        report = orchestrator.run_audit("https://example.com")

        assert report.summary.total_findings == 4
        assert report.summary.critical == 1
        assert report.summary.high == 1
        assert report.summary.medium == 1
        assert report.summary.low == 1

        # Sorted by severity rank: critical, high, medium, low
        severities = [f.severity for f in report.findings]
        assert severities == ["critical", "high", "medium", "low"]

    def test_10_final_summary_counts_and_action_plan(self):
        """Orchestrator generates consistent summary counts and a correctly sorted action plan."""
        orchestrator = AuditOrchestrator(
            discoverability_runner=get_mock_discoverability_success,
            engagement_runner=get_mock_engagement_success,
        )
        report = orchestrator.run_audit("https://test-brand.com")
        summary = report.summary

        assert summary.total_findings == summary.critical + summary.high + summary.medium + summary.low
        assert len(report.prioritized_action_plan) == summary.total_findings

        # Verify action plan structure
        for item in report.prioritized_action_plan:
            assert "finding_id" in item
            assert "priority" in item
            assert "action_summary" in item
            assert "action_details" in item
