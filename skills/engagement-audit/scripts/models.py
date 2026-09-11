import json
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

@dataclass
class SuggestedAction:
    summary: str
    details: str
    priority: str

@dataclass
class Finding:
    id: str
    category: str
    subcategory: str
    title: str
    severity: str
    evidence: str
    why_it_matters: str
    suggested_action: SuggestedAction

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class FindingEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Finding):
            return obj.to_dict()
        if isinstance(obj, SuggestedAction):
            return asdict(obj)
        return super().default(obj)
