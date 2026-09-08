"""Audit Orchestrator: Central coordinator for the Brand AI Readiness Agent Marketplace."""

from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Callable, Dict, List, Optional

try:
    from .contracts import (
        AuditFinding,
        AuditReport,
    )
    from .deduplication import deduplicate_findings
    from .mock_modules import (
        get_mock_discoverability_success,
        get_mock_engagement_success,
    )
    from .normalization import normalize_finding_ratings
    from .report_generator import generate_audit_report
    from .validation import (
        validate_input_url,
        validate_module_payload,
    )
except ImportError:
    from contracts import (  # type: ignore
        AuditFinding,
        AuditReport,
    )
    from deduplication import deduplicate_findings  # type: ignore
    from mock_modules import (  # type: ignore
        get_mock_discoverability_success,
        get_mock_engagement_success,
    )
    from normalization import normalize_finding_ratings  # type: ignore
    from report_generator import generate_audit_report  # type: ignore
    from validation import (  # type: ignore
        validate_input_url,
        validate_module_payload,
    )


class AuditOrchestrator:
    """
    Coordinates specialized agent skills, validates findings, deduplicates,
    normalizes severities/priorities, and generates the final audit report.
    """

    def __init__(
        self,
        discoverability_runner: Optional[Callable[[str], Dict[str, Any]]] = None,
        engagement_runner: Optional[Callable[[str], Dict[str, Any]]] = None,
    ):
        # Default to mock runners if actual skills are still under branch development
        self.discoverability_runner = discoverability_runner or get_mock_discoverability_success
        self.engagement_runner = engagement_runner or get_mock_engagement_success

    def run_audit(self, site_input: str) -> AuditReport:
        """
        Executes the complete audit orchestration workflow for a given site.
        """
        # 1. Validate Target Website Input
        is_valid, clean_url_or_err = validate_input_url(site_input)
        if not is_valid:
            raise ValueError(f"Invalid audit target input: {clean_url_or_err}")

        target_url = clean_url_or_err
        all_raw_findings: List[AuditFinding] = []
        module_statuses: Dict[str, Dict[str, Any]] = {}
        limitations: List[str] = []

        # 2. Execute AI Discoverability Module
        try:
            disc_payload = self.discoverability_runner(target_url)
            disc_findings, disc_rejections, disc_err = validate_module_payload(
                disc_payload, expected_skill="ai-discoverability"
            )

            if disc_err:
                module_statuses["ai_discoverability"] = {
                    "status": "failure",
                    "findings_count": 0,
                    "error": disc_err,
                }
                limitations.append(f"AI Discoverability module failed: {disc_err}")
            else:
                all_raw_findings.extend(disc_findings)
                module_statuses["ai_discoverability"] = {
                    "status": "success",
                    "findings_count": len(disc_findings),
                }
                if disc_rejections:
                    limitations.extend([f"AI Discoverability: {r}" for r in disc_rejections])
        except Exception as ex:
            module_statuses["ai_discoverability"] = {
                "status": "failure",
                "findings_count": 0,
                "error": str(ex),
            }
            limitations.append(f"AI Discoverability execution crashed: {str(ex)}")

        # 3. Execute On-Site Engagement Module
        try:
            eng_payload = self.engagement_runner(target_url)
            eng_findings, eng_rejections, eng_err = validate_module_payload(
                eng_payload, expected_skill="engagement-audit"
            )

            if eng_err:
                module_statuses["on_site_engagement"] = {
                    "status": "failure",
                    "findings_count": 0,
                    "error": eng_err,
                }
                limitations.append(f"On-Site Engagement module failed: {eng_err}")
            else:
                all_raw_findings.extend(eng_findings)
                module_statuses["on_site_engagement"] = {
                    "status": "success",
                    "findings_count": len(eng_findings),
                }
                if eng_rejections:
                    limitations.extend([f"On-Site Engagement: {r}" for r in eng_rejections])
        except Exception as ex:
            module_statuses["on_site_engagement"] = {
                "status": "failure",
                "findings_count": 0,
                "error": str(ex),
            }
            limitations.append(f"On-Site Engagement execution crashed: {str(ex)}")

        # 4. Normalize Ratings
        normalized_findings = [normalize_finding_ratings(f) for f in all_raw_findings]

        # 5. Deduplicate Findings Conservatively
        deduped_findings, merged_count = deduplicate_findings(normalized_findings)
        if merged_count > 0:
            limitations.append(f"Deduplication consolidated {merged_count} overlapping finding(s).")

        # 6. Generate Final Audit Report
        report = generate_audit_report(
            site=target_url,
            findings=deduped_findings,
            module_statuses=module_statuses,
            limitations=limitations,
        )

        return report


def main():
    parser = argparse.ArgumentParser(description="Brand AI Readiness Audit Orchestrator")
    parser.add_argument("site", help="Target website URL to audit (e.g. https://example.com)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON report")
    parser.add_argument("--out", type=str, default=None, help="Save report to destination file")

    args = parser.parse_args()

    orchestrator = AuditOrchestrator()
    try:
        report = orchestrator.run_audit(args.site)
        report_dict = report.to_dict()

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2)
            print(f"Report written to {args.out}")
        elif args.json:
            print(json.dumps(report_dict, indent=2))
        else:
            print(f"\n=======================================================")
            print(f" BRAND AI READINESS AUDIT REPORT")
            print(f" Target: {report.site}")
            print(f" Audited At: {report.audited_at}")
            print(f"=======================================================")
            print(f" Summary: {report.summary.total_findings} total findings")
            print(f"   Critical: {report.summary.critical} | High: {report.summary.high} | Medium: {report.summary.medium} | Low: {report.summary.low}")
            print(f"=======================================================")
            for idx, f in enumerate(report.findings, start=1):
                print(f" [{idx}] [{f.severity.upper()}] {f.id}: {f.title}")
                print(f"     Category: {f.category} / {f.subcategory}")
                print(f"     Evidence: {f.evidence}")
                print(f"     Why It Matters: {f.why_it_matters}")
                print(f"     Action: {f.suggested_action.summary} (Priority: {f.suggested_action.priority.upper()})")
                print()
            if report.limitations:
                print(" Limitations / Notes:")
                for lim in report.limitations:
                    print(f"   - {lim}")
                print()
    except Exception as ex:
        print(f"Error executing audit: {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
