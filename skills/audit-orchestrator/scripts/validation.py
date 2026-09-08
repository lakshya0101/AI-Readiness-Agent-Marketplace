"""Validation routines for audit inputs, module payloads, and audit findings."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
try:
    from .contracts import (
        AuditFinding,
        SuggestedAction,
        VALID_CATEGORIES,
        VALID_SEVERITIES,
    )
    from .normalization import normalize_finding_ratings
except ImportError:
    from contracts import (  # type: ignore
        AuditFinding,
        SuggestedAction,
        VALID_CATEGORIES,
        VALID_SEVERITIES,
    )
    from normalization import normalize_finding_ratings  # type: ignore

ID_REGEX = re.compile(r"^[A-Z]{3,4}-[0-9]{3,4}$", re.IGNORECASE)


class ValidationError(Exception):
    """Raised when validation fails critically."""
    pass


def validate_input_url(site: Any) -> Tuple[bool, str]:
    """
    Validates the target site input URL.
    Returns (is_valid, sanitized_url_or_error_message).
    """
    if not site or not isinstance(site, str):
        return False, "Target site URL must be a non-empty string."

    trimmed = site.strip()
    if not trimmed:
        return False, "Target site URL cannot be blank."

    # Prepend https:// if user provided plain domain (e.g. example.com)
    if not re.match(r"^https?://", trimmed, re.IGNORECASE):
        trimmed = f"https://{trimmed}"

    parsed = urlparse(trimmed)
    if not parsed.scheme or parsed.scheme.lower() not in {"http", "https"}:
        return False, f"Invalid URL scheme '{parsed.scheme}'. Must be http or https."

    if not parsed.netloc or "." not in parsed.netloc:
        return False, f"Invalid domain name in URL '{trimmed}'."

    # Return normalized clean URL
    path = parsed.path.rstrip("/") if parsed.path else ""
    clean_url = f"{parsed.scheme.lower()}://{parsed.netloc}{path}"
    return True, clean_url


def validate_finding(
    raw_finding: Any,
    allow_normalization: bool = True,
) -> Tuple[Optional[AuditFinding], Optional[str]]:
    """
    Validates a single finding against the common contract.
    Returns (validated_finding_or_None, rejection_reason_or_None).

    CRITICAL RULE:
    NEVER hallucinate or invent missing evidence.
    If evidence is missing or blank, reject the finding with clear justification.
    """
    if not isinstance(raw_finding, dict):
        return None, "Finding must be a JSON object / dictionary."

    # 1. ID validation
    finding_id = str(raw_finding.get("id", "")).strip()
    if not finding_id:
        return None, "Finding 'id' is required and cannot be empty."

    # 2. Category validation
    category = str(raw_finding.get("category", "")).strip().lower()
    if category not in VALID_CATEGORIES:
        return None, f"Invalid category '{category}'. Must be one of {sorted(list(VALID_CATEGORIES))}."

    # 3. Subcategory validation
    subcategory = str(raw_finding.get("subcategory", "")).strip()
    if not subcategory:
        return None, "Finding 'subcategory' is required and cannot be empty."

    # 4. Title validation
    title = str(raw_finding.get("title", "")).strip()
    if not title or len(title) < 3:
        return None, "Finding 'title' is required and must be at least 3 characters long."

    # 5. Evidence validation (STRICT: DO NOT INVENT EVIDENCE)
    evidence = str(raw_finding.get("evidence", "")).strip()
    if not evidence or len(evidence) < 3:
        return None, "Concrete observable 'evidence' is mandatory and cannot be empty. Evidence must never be fabricated."

    # 6. Why it matters validation
    why_it_matters = str(raw_finding.get("why_it_matters", "")).strip()
    if not why_it_matters or len(why_it_matters) < 3:
        return None, "Finding 'why_it_matters' explanation is required."

    # 7. Suggested action validation
    raw_action = raw_finding.get("suggested_action")
    if not isinstance(raw_action, dict):
        return None, "Finding 'suggested_action' must be an object with 'summary' and 'details'."

    action_summary = str(raw_action.get("summary", "")).strip()
    action_details = str(raw_action.get("details", "")).strip()
    if not action_summary:
        return None, "Suggested action 'summary' is required."
    if not action_details:
        return None, "Suggested action 'details' is required."

    # Construct finding
    finding = AuditFinding.from_dict(raw_finding)

    # Normalize ratings
    if allow_normalization:
        finding = normalize_finding_ratings(finding)
    else:
        if finding.severity not in VALID_SEVERITIES:
            return None, f"Invalid severity '{finding.severity}'."

    return finding, None


def validate_module_payload(
    payload: Dict[str, Any],
    expected_skill: str,
) -> Tuple[List[AuditFinding], List[str], Optional[str]]:
    """
    Validates a raw payload returned by a skill module.
    Returns: (valid_findings, rejected_reasons, fatal_error_if_any)
    """
    if not isinstance(payload, dict):
        return [], ["Payload is not a valid JSON dictionary."], f"Module '{expected_skill}' returned non-dictionary payload."

    status = payload.get("status", "unknown")
    if status != "success":
        error_msg = payload.get("error") or f"Module '{expected_skill}' reported status '{status}'."
        return [], [], error_msg

    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        return [], ["'findings' field must be an array/list."], f"Module '{expected_skill}' findings field is not a list."

    valid_findings: List[AuditFinding] = []
    rejections: List[str] = []

    for idx, item in enumerate(raw_findings):
        finding, rejection = validate_finding(item)
        if finding:
            valid_findings.append(finding)
        else:
            rejections.append(f"Finding at index {idx} rejected: {rejection}")

    return valid_findings, rejections, None
