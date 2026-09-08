"""Severity and priority normalization and calculation logic."""

from __future__ import annotations
from typing import Optional, Tuple
try:
    from .contracts import (
        AuditFinding,
        PriorityLevel,
        SeverityLevel,
        VALID_PRIORITIES,
        VALID_SEVERITIES,
    )
except ImportError:
    from contracts import (  # type: ignore
        AuditFinding,
        PriorityLevel,
        SeverityLevel,
        VALID_PRIORITIES,
        VALID_SEVERITIES,
    )

# Mapping aliases to canonical severities
SEVERITY_ALIAS_MAP = {
    "critical": "critical",
    "blocker": "critical",
    "fatal": "critical",
    "p0": "critical",
    "high": "high",
    "major": "high",
    "severe": "high",
    "p1": "high",
    "medium": "medium",
    "moderate": "medium",
    "warning": "medium",
    "warn": "medium",
    "p2": "medium",
    "low": "low",
    "minor": "low",
    "info": "low",
    "informational": "low",
    "trivial": "low",
    "p3": "low",
}

PRIORITY_ALIAS_MAP = {
    "critical": "critical",
    "urgent": "critical",
    "immediate": "critical",
    "p0": "critical",
    "high": "high",
    "p1": "high",
    "medium": "medium",
    "moderate": "medium",
    "p2": "medium",
    "low": "low",
    "p3": "low",
}


def normalize_severity(raw_severity: Optional[str]) -> Tuple[SeverityLevel, bool]:
    """
    Normalizes arbitrary severity strings to valid levels ('critical', 'high', 'medium', 'low').
    Returns (normalized_severity, was_modified_or_fallback).
    """
    if not raw_severity or not isinstance(raw_severity, str):
        return "medium", True

    cleaned = raw_severity.strip().lower()
    if cleaned in VALID_SEVERITIES:
        return cleaned, False  # type: ignore

    if cleaned in SEVERITY_ALIAS_MAP:
        return SEVERITY_ALIAS_MAP[cleaned], True  # type: ignore

    # Fallback conservative default
    return "medium", True


def normalize_priority(raw_priority: Optional[str]) -> Tuple[PriorityLevel, bool]:
    """
    Normalizes priority strings to valid levels ('critical', 'high', 'medium', 'low').
    Returns (normalized_priority, was_modified_or_fallback).
    """
    if not raw_priority or not isinstance(raw_priority, str):
        return "medium", True

    cleaned = raw_priority.strip().lower()
    if cleaned in VALID_PRIORITIES:
        return cleaned, False  # type: ignore

    if cleaned in PRIORITY_ALIAS_MAP:
        return PRIORITY_ALIAS_MAP[cleaned], True  # type: ignore

    return "medium", True


def calculate_priority(
    severity: SeverityLevel,
    confidence: Optional[str] = None,
    affected_pages_count: int = 1,
    remediation_complexity: Optional[str] = None,
) -> PriorityLevel:
    """
    Calculates an evidence-backed priority level for a recommendation without fake numerical scores.
    Considers:
    - Base severity
    - Evidence confidence (low confidence downweights urgency)
    - Breadth of impact (many pages vs isolated)
    - Remediation complexity (low-effort high-impact quick wins)
    """
    norm_sev, _ = normalize_severity(severity)

    # Base priority mirrors severity
    base_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}[norm_sev]

    # Adjust based on confidence
    conf_clean = str(confidence).strip().lower() if confidence else "medium"
    if conf_clean == "low" and base_rank > 1:
        base_rank -= 1  # Don't create urgent fire drills on weak/unconfirmed evidence

    # Adjust for widespread breadth (e.g. site-wide impact on 5+ pages)
    if affected_pages_count >= 5 and base_rank < 4:
        base_rank += 1

    # Quick win adjustment: low complexity on high/medium issue
    comp_clean = str(remediation_complexity).strip().lower() if remediation_complexity else "medium"
    if comp_clean == "low" and base_rank == 2:
        base_rank = 3  # promote easy fixes

    rank_to_priority: dict[int, PriorityLevel] = {
        4: "critical",
        3: "high",
        2: "medium",
        1: "low",
    }
    # Clamp to [1, 4]
    clamped_rank = max(1, min(4, base_rank))
    return rank_to_priority[clamped_rank]


def normalize_finding_ratings(finding: AuditFinding) -> AuditFinding:
    """Normalizes both severity and suggested action priority for a given finding in-place."""
    norm_sev, _ = normalize_severity(finding.severity)
    finding.severity = norm_sev

    raw_prio = finding.suggested_action.priority if finding.suggested_action else None
    if raw_prio and str(raw_prio).strip().lower() in VALID_PRIORITIES:
        norm_prio, _ = normalize_priority(raw_prio)
    else:
        norm_prio = calculate_priority(
            severity=norm_sev,
            confidence=finding.confidence,
            affected_pages_count=len(finding.affected_pages) if finding.affected_pages else 1,
            remediation_complexity=finding.remediation_complexity,
        )

    if finding.suggested_action:
        finding.suggested_action.priority = norm_prio

    return finding
