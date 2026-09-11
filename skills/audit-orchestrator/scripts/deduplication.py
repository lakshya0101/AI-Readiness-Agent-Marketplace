"""Conservative finding deduplication logic."""

from __future__ import annotations
import re
from typing import List, Set, Tuple
try:
    from .contracts import AuditFinding
    from .normalization import normalize_severity, calculate_priority
except ImportError:
    from contracts import AuditFinding  # type: ignore
    from normalization import normalize_severity, calculate_priority  # type: ignore


def _build_finding_fingerprint(finding: AuditFinding) -> str:
    """
    Computes a conservative semantic signature for deduplication.
    Uses:
    - category
    - subcategory
    - normalized core title keywords
    """
    # Normalize title: lowercase, strip punctuation and whitespace
    norm_title = re.sub(r"[^\w\s]", "", finding.title.lower())
    words = [w for w in norm_title.split() if len(w) > 2]
    title_sig = "-".join(sorted(set(words)))

    return f"{finding.category}:{finding.subcategory}:{title_sig}"


def _severity_rank(sev: str) -> int:
    ranks = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return ranks.get(sev.lower(), 1)


def merge_findings(primary: AuditFinding, secondary: AuditFinding) -> AuditFinding:
    """
    Merges two duplicate findings conservatively:
    - Retains higher severity
    - Combines unique affected_pages
    - Combines references
    - Appends unique observable evidence snippets if different
    - Recalculates priority
    """
    # Pick higher severity
    if _severity_rank(secondary.severity) > _severity_rank(primary.severity):
        primary.severity = secondary.severity

    # Merge affected pages
    combined_pages = list(dict.fromkeys((primary.affected_pages or []) + (secondary.affected_pages or [])))
    primary.affected_pages = combined_pages

    # Merge references
    combined_refs = list(dict.fromkeys((primary.references or []) + (secondary.references or [])))
    primary.references = combined_refs

    # Combine evidence if secondary has unique concrete proof
    if secondary.evidence and secondary.evidence.strip() not in primary.evidence:
        primary.evidence = f"{primary.evidence.rstrip('.')}. Also observed: {secondary.evidence}"

    # Recalculate suggested action priority
    primary.suggested_action.priority = calculate_priority(
        severity=primary.severity,
        confidence=primary.confidence,
        affected_pages_count=len(primary.affected_pages),
        remediation_complexity=primary.remediation_complexity,
    )

    return primary


def deduplicate_findings(findings: List[AuditFinding]) -> Tuple[List[AuditFinding], int]:
    """
    Deduplicates a list of findings using conservative matching.
    Returns: (deduplicated_findings, count_of_merged_duplicates)
    """
    if not findings:
        return [], 0

    unique_by_id: dict[str, AuditFinding] = {}
    fingerprint_to_id: dict[str, str] = {}
    duplicates_merged = 0

    for finding in findings:
        # Case 1: Exact ID collision
        if finding.id in unique_by_id:
            existing = unique_by_id[finding.id]
            unique_by_id[finding.id] = merge_findings(existing, finding)
            duplicates_merged += 1
            continue

        # Case 2: Matching semantic fingerprint (same category, subcategory, and core problem)
        fingerprint = _build_finding_fingerprint(finding)
        if fingerprint in fingerprint_to_id:
            existing_id = fingerprint_to_id[fingerprint]
            existing = unique_by_id[existing_id]
            unique_by_id[existing_id] = merge_findings(existing, finding)
            duplicates_merged += 1
            continue

        # Unique finding
        unique_by_id[finding.id] = finding
        fingerprint_to_id[fingerprint] = finding.id

    return list(unique_by_id.values()), duplicates_merged
