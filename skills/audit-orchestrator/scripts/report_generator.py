"""Audit report generator and summary builder."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
try:
    from .contracts import (
        AuditFinding,
        AuditReport,
        AuditSummary,
    )
except ImportError:
    from contracts import (  # type: ignore
        AuditFinding,
        AuditReport,
        AuditSummary,
    )


def _priority_rank(prio: str) -> int:
    ranks = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return ranks.get(prio.lower(), 1)


def generate_audit_report(
    site: str,
    findings: List[AuditFinding],
    module_statuses: Optional[Dict[str, Dict[str, Any]]] = None,
    limitations: Optional[List[str]] = None,
) -> AuditReport:
    """
    Constructs the final structured AuditReport from validated and deduplicated findings.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Calculate summary counts
    summary = AuditSummary(total_findings=len(findings))
    for f in findings:
        sev = f.severity.lower()
        if sev == "critical":
            summary.critical += 1
        elif sev == "high":
            summary.high += 1
        elif sev == "medium":
            summary.medium += 1
        elif sev == "low":
            summary.low += 1

    # Sort findings deterministically: by severity rank descending, then ID ascending
    sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    sorted_findings = sorted(
        findings,
        key=lambda f: (-sev_rank.get(f.severity.lower(), 1), f.id),
    )

    # Build prioritized action plan
    # Sorted by priority rank descending, then severity rank descending
    sorted_for_plan = sorted(
        findings,
        key=lambda f: (
            -_priority_rank(f.suggested_action.priority if f.suggested_action else "low"),
            -sev_rank.get(f.severity.lower(), 1),
            f.id,
        ),
    )

    action_plan: List[Dict[str, Any]] = []
    for f in sorted_for_plan:
        action_plan.append({
            "finding_id": f.id,
            "category": f.category,
            "title": f.title,
            "severity": f.severity,
            "priority": f.suggested_action.priority if f.suggested_action else "medium",
            "action_summary": f.suggested_action.summary if f.suggested_action else "",
            "action_details": f.suggested_action.details if f.suggested_action else "",
            "affected_pages": f.affected_pages,
        })

    return AuditReport(
        site=site,
        audited_at=now_iso,
        summary=summary,
        findings=sorted_findings,
        modules=module_statuses or {},
        limitations=limitations or [],
        prioritized_action_plan=action_plan,
    )
