"""Finding Factory and Validator for AI Discoverability Module.

Ensures every finding complies strictly with the project-wide contract:
- Valid DISC-### ID format
- Canonical category 'ai_discoverability'
- Allowed severity levels (critical, high, medium, low)
- Non-empty, concrete observable evidence
- Required why_it_matters explanation
- Required suggested_action with summary, details, and valid priority
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple

DISC_ID_REGEX = re.compile(r"^DISC-[0-9]{3,4}$", re.IGNORECASE)
VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
CANONICAL_CATEGORY = "ai_discoverability"


class FindingValidationError(ValueError):
    """Raised when a finding fails contract validation."""
    pass


class FindingFactory:
    """Constructs and validates AI Discoverability findings."""

    def __init__(self, id_start: int = 1):
        self._next_id = id_start

    def next_id(self) -> str:
        """Generates the next sequential finding ID (e.g. DISC-001)."""
        finding_id = f"DISC-{self._next_id:03d}"
        self._next_id += 1
        return finding_id

    @staticmethod
    def validate(finding_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates a finding dictionary against the contract.
        Returns (is_valid, error_message_or_None).
        """
        if not isinstance(finding_data, dict):
            return False, "Finding must be a dictionary."

        # 1. ID check
        fid = str(finding_data.get("id", "")).strip()
        if not fid or not DISC_ID_REGEX.match(fid):
            return False, f"Invalid finding ID '{fid}'. Must match format DISC-### (e.g. DISC-001)."

        # 2. Category check
        category = str(finding_data.get("category", "")).strip()
        if category != CANONICAL_CATEGORY:
            return False, f"Invalid category '{category}'. Must be '{CANONICAL_CATEGORY}'."

        # 3. Subcategory check
        subcategory = str(finding_data.get("subcategory", "")).strip()
        if not subcategory:
            return False, "Finding 'subcategory' is required and cannot be empty."

        # 4. Title check
        title = str(finding_data.get("title", "")).strip()
        if not title or len(title) < 3:
            return False, "Finding 'title' is required and must be at least 3 characters."

        # 5. Severity check
        severity = str(finding_data.get("severity", "")).strip().lower()
        if severity not in VALID_SEVERITIES:
            return False, f"Invalid severity '{severity}'. Must be one of {sorted(list(VALID_SEVERITIES))}."

        # 6. Evidence check (STRICT INVARIANT: No empty, generic, or fabricated evidence)
        evidence = str(finding_data.get("evidence", "")).strip()
        if not evidence or len(evidence) < 3:
            return False, "Concrete observable 'evidence' is mandatory and must be at least 3 characters."

        # 7. Why it matters check
        why_it_matters = str(finding_data.get("why_it_matters", "")).strip()
        if not why_it_matters or len(why_it_matters) < 3:
            return False, "Finding 'why_it_matters' is required and must be at least 3 characters."

        # 8. Suggested action check
        action = finding_data.get("suggested_action")
        if not isinstance(action, dict):
            return False, "Finding 'suggested_action' must be a dictionary."

        summary = str(action.get("summary", "")).strip()
        details = str(action.get("details", "")).strip()
        priority = str(action.get("priority", "")).strip().lower()

        if not summary or len(summary) < 3:
            return False, "Suggested action 'summary' is required and must be at least 3 characters."
        if not details or len(details) < 3:
            return False, "Suggested action 'details' is required and must be at least 3 characters."
        if priority not in VALID_PRIORITIES:
            return False, f"Invalid suggested action priority '{priority}'. Must be one of {sorted(list(VALID_PRIORITIES))}."

        return True, None

    def create_finding(
        self,
        subcategory: str,
        title: str,
        severity: str,
        evidence: str,
        why_it_matters: str,
        suggested_action_summary: str,
        suggested_action_details: str,
        suggested_action_priority: str = "medium",
        finding_id: Optional[str] = None,
        confidence: Optional[str] = None,
        affected_pages: Optional[List[str]] = None,
        evidence_type: Optional[str] = None,
        methodology: Optional[str] = None,
        remediation_complexity: Optional[str] = None,
        references: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Builds and validates a finding dictionary.
        Raises FindingValidationError if any constraint is violated.
        """
        fid = finding_id.upper() if finding_id else self.next_id()
        sev = severity.strip().lower()
        pri = suggested_action_priority.strip().lower()

        finding: Dict[str, Any] = {
            "id": fid,
            "category": CANONICAL_CATEGORY,
            "subcategory": subcategory.strip(),
            "title": title.strip(),
            "severity": sev,
            "evidence": evidence.strip(),
            "why_it_matters": why_it_matters.strip(),
            "suggested_action": {
                "summary": suggested_action_summary.strip(),
                "details": suggested_action_details.strip(),
                "priority": pri,
            },
        }

        # Optional metadata fields
        if confidence:
            conf = confidence.strip().lower()
            if conf in {"high", "medium", "low"}:
                finding["confidence"] = conf
        if affected_pages:
            finding["affected_pages"] = [str(p).strip() for p in affected_pages if str(p).strip()]
        if evidence_type:
            finding["evidence_type"] = evidence_type.strip()
        if methodology:
            finding["methodology"] = methodology.strip()
        if remediation_complexity:
            rem = remediation_complexity.strip().lower()
            if rem in {"low", "medium", "high"}:
                finding["remediation_complexity"] = rem
        if references:
            finding["references"] = [str(r).strip() for r in references if str(r).strip()]

        is_valid, err = self.validate(finding)
        if not is_valid:
            raise FindingValidationError(err)

        return finding
