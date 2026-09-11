"""Mock module outputs and simulated runners for AI Discoverability and Engagement skills.

These mocks decouple orchestrator testing and validation from the parallel development
occurring on feature/aditya-discoverability and feature/vishesh-engagement.
"""

from __future__ import annotations
from typing import Any, Dict, List


def get_mock_discoverability_success(site: str) -> Dict[str, Any]:
    """Simulates a successful AI Discoverability audit output."""
    return {
        "skill": "ai-discoverability",
        "status": "success",
        "findings": [
            {
                "id": "DISC-001",
                "category": "ai_discoverability",
                "subcategory": "structured_data",
                "title": "Missing Schema.org Organization JSON-LD markup",
                "severity": "high",
                "evidence": f"Audited {site}/ - No <script type='application/ld+json'> tags containing Schema.org/Organization were found in HTML head or body.",
                "why_it_matters": "LLMs and search crawlers cannot unambiguously resolve corporate identity, official name, or social profiles without structured entity markup.",
                "suggested_action": {
                    "summary": "Implement Schema.org Organization markup in JSON-LD format",
                    "details": "Embed a JSON-LD script on the homepage defining '@type': 'Organization', 'name', 'url', and 'sameAs' social links.",
                    "priority": "high",
                },
                "confidence": "high",
                "affected_pages": [f"{site}/"],
                "evidence_type": "HTML_DOM",
                "methodology": "Identify",
                "remediation_complexity": "low",
            },
            {
                "id": "DISC-002",
                "category": "ai_discoverability",
                "subcategory": "crawlability",
                "title": "Robots.txt restricts AI crawler user-agents unnecessarily",
                "severity": "medium",
                "evidence": f"Found 'Disallow: /docs/' applied generally in {site}/robots.txt without explicit allow-rules for GPTBot or ClaudeBot.",
                "why_it_matters": "AI assistant indexing pipelines respect robots.txt restrictions and will fail to cite documentation.",
                "suggested_action": {
                    "summary": "Add selective crawler rules for verified AI agents",
                    "details": "Update robots.txt to explicitly permit documentation endpoints for GPTBot, ClaudeBot, and PerplexityBot.",
                    "priority": "medium",
                },
                "confidence": "high",
                "affected_pages": [f"{site}/robots.txt"],
                "evidence_type": "ROBOTS_TXT",
                "methodology": "Reach",
                "remediation_complexity": "low",
            },
        ],
    }


def get_mock_engagement_success(site: str) -> Dict[str, Any]:
    """Simulates a successful On-Site Engagement audit output."""
    return {
        "skill": "engagement-audit",
        "status": "success",
        "findings": [
            {
                "id": "ENG-001",
                "category": "on_site_engagement",
                "subcategory": "orientation",
                "title": "Hero section lacks immediate value proposition in viewport",
                "severity": "high",
                "evidence": f"Above-the-fold content on {site}/ contains a large decorative canvas (620px height) before primary H1 value headline appears at scroll offset 740px.",
                "why_it_matters": "First-time visitors arriving from AI search decide whether to stay within 3 seconds; obscured value propositions lead to immediate bounces.",
                "suggested_action": {
                    "summary": "Restructure above-the-fold hero layout",
                    "details": "Elevate primary H1 headline and secondary sub-headline into the initial 500px viewport above decorative visual assets.",
                    "priority": "high",
                },
                "confidence": "high",
                "affected_pages": [f"{site}/"],
                "evidence_type": "RENDERED_DOM",
                "methodology": "Landing",
                "remediation_complexity": "medium",
            },
            {
                "id": "ENG-002",
                "category": "on_site_engagement",
                "subcategory": "next_action",
                "title": "Primary Call to Action button blends into background",
                "severity": "medium",
                "evidence": f"Computed contrast ratio between CTA button (#64748b) and background (#475569) on {site}/ is 1.8:1, failing WCAG AA (4.5:1).",
                "why_it_matters": "Low contrast CTAs reduce conversion rate by impairing visual affordance for visitors ready to take the next step.",
                "suggested_action": {
                    "summary": "Increase primary action button contrast ratio",
                    "details": "Update CTA button background to high-contrast theme color (#2563eb on #f8fafc) providing at least 4.5:1 contrast ratio.",
                    "priority": "medium",
                },
                "confidence": "high",
                "affected_pages": [f"{site}/"],
                "evidence_type": "CSS_COMPUTED",
                "methodology": "Next Action",
                "remediation_complexity": "low",
            },
        ],
    }


def get_mock_module_failure(skill_name: str, error_msg: str) -> Dict[str, Any]:
    """Simulates a failed audit module output."""
    return {
        "skill": skill_name,
        "status": "failure",
        "error": error_msg,
        "findings": [],
    }
