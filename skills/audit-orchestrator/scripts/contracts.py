"""Shared data contracts and type definitions for the Brand AI Readiness Audit."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional

SeverityLevel = Literal["critical", "high", "medium", "low"]
PriorityLevel = Literal["critical", "high", "medium", "low"]
CategoryType = Literal["ai_discoverability", "on_site_engagement"]
ModuleStatus = Literal["success", "partial", "failure", "skipped"]

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_CATEGORIES = {"ai_discoverability", "on_site_engagement"}


@dataclass
class SuggestedAction:
    summary: str
    details: str
    priority: PriorityLevel = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SuggestedAction:
        return cls(
            summary=str(data.get("summary", "")).strip(),
            details=str(data.get("details", "")).strip(),
            priority=str(data.get("priority", "medium")).lower(),  # type: ignore
        )


@dataclass
class AuditFinding:
    id: str
    category: CategoryType
    subcategory: str
    title: str
    severity: SeverityLevel
    evidence: str
    why_it_matters: str
    suggested_action: SuggestedAction
    confidence: Optional[str] = None
    affected_pages: List[str] = field(default_factory=list)
    evidence_type: Optional[str] = None
    methodology: Optional[str] = None
    remediation_complexity: Optional[str] = None
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "category": self.category,
            "subcategory": self.subcategory,
            "title": self.title,
            "severity": self.severity,
            "evidence": self.evidence,
            "why_it_matters": self.why_it_matters,
            "suggested_action": self.suggested_action.to_dict(),
        }
        if self.confidence:
            data["confidence"] = self.confidence
        if self.affected_pages:
            data["affected_pages"] = self.affected_pages
        if self.evidence_type:
            data["evidence_type"] = self.evidence_type
        if self.methodology:
            data["methodology"] = self.methodology
        if self.remediation_complexity:
            data["remediation_complexity"] = self.remediation_complexity
        if self.references:
            data["references"] = self.references
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditFinding:
        raw_action = data.get("suggested_action", {})
        action = SuggestedAction.from_dict(raw_action) if isinstance(raw_action, dict) else SuggestedAction(summary="", details="")
        return cls(
            id=str(data.get("id", "")).strip(),
            category=str(data.get("category", "")).strip(),  # type: ignore
            subcategory=str(data.get("subcategory", "")).strip(),
            title=str(data.get("title", "")).strip(),
            severity=str(data.get("severity", "medium")).strip().lower(),  # type: ignore
            evidence=str(data.get("evidence", "")).strip(),
            why_it_matters=str(data.get("why_it_matters", "")).strip(),
            suggested_action=action,
            confidence=data.get("confidence"),
            affected_pages=list(data.get("affected_pages", [])),
            evidence_type=data.get("evidence_type"),
            methodology=data.get("methodology"),
            remediation_complexity=data.get("remediation_complexity"),
            references=list(data.get("references", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ModuleResult:
    skill: str
    status: ModuleStatus
    findings: List[AuditFinding] = field(default_factory=list)
    error: Optional[str] = None
    limitations: List[str] = field(default_factory=list)
    execution_time_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "status": self.status,
            "findings_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "error": self.error,
            "limitations": self.limitations,
            "execution_time_seconds": self.execution_time_seconds,
        }


@dataclass
class AuditSummary:
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "total_findings": self.total_findings,
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
        }


@dataclass
class AuditReport:
    site: str
    audited_at: str
    summary: AuditSummary
    findings: List[AuditFinding]
    modules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    prioritized_action_plan: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site": self.site,
            "audited_at": self.audited_at,
            "summary": self.summary.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "modules": self.modules,
            "limitations": self.limitations,
            "prioritized_action_plan": self.prioritized_action_plan,
        }
