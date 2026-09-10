from __future__ import annotations
import sys
import json
import ssl
import urllib.request
from typing import Any, Dict, List, Optional
from .evaluators import EngagementEvaluator
from .models import FindingEncoder, Finding


def audit_engagement(
    site: str,
    options: Optional[Dict[str, Any]] = None,
    html: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Canonical public programmatic entrypoint for the On-Site Engagement Audit skill.
    Evaluates target website landing and deep-entry structural engagement signals.
    Returns orchestrator-compatible module payload dictionary.
    """
    options = options or {}
    entry_type = str(options.get("entry_type", "landing"))
    page_type = str(options.get("inferred_page_type", ""))
    timeout = int(options.get("timeout", 10))
    limitations = [
        "Analyzes structural DOM without executing browser JavaScript or rendering CSS layout.",
        "Evaluates landing experience based on initial server-delivered HTML.",
    ]

    if not site or not isinstance(site, str) or not site.strip():
        return {
            "skill": "engagement-audit",
            "status": "failure",
            "findings": [],
            "error": "Target site URL must be a non-empty string.",
            "limitations": limitations,
        }

    clean_url = site.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    html_content = html
    if html_content is None:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; BrandAIEngagementAuditor/1.0; +https://github.com/lakshya0101/AI-Readiness-Agent-Marketplace)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            req = urllib.request.Request(clean_url, headers=headers)
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                body = resp.read()
                try:
                    html_content = body.decode("utf-8", errors="replace")
                except Exception:
                    html_content = body.decode("latin-1", errors="replace")
        except Exception as e:
            return {
                "skill": "engagement-audit",
                "status": "failure",
                "findings": [],
                "error": f"Failed to fetch {clean_url}: {str(e)}",
                "limitations": limitations,
            }

    try:
        evaluator = EngagementEvaluator(
            url=clean_url,
            html=html_content,
            entry_type=entry_type,
            page_type=page_type,
        )
        raw_findings = evaluator.evaluate()
        findings: List[Dict[str, Any]] = []
        for f in raw_findings:
            f_dict = f.to_dict() if hasattr(f, "to_dict") else vars(f)
            # Ensure canonical category format expected by orchestrator
            if f_dict.get("category") in {"engagement", "on_site_engagement"}:
                f_dict["category"] = "on_site_engagement"
            findings.append(f_dict)

        return {
            "skill": "engagement-audit",
            "status": "success",
            "findings": findings,
            "error": None,
            "limitations": limitations,
        }
    except Exception as e:
        return {
            "skill": "engagement-audit",
            "status": "failure",
            "findings": [],
            "error": f"Engagement evaluation error: {str(e)}",
            "limitations": limitations,
        }


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            print("[]", end="")
            return

        payload = json.loads(input_data)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error parsing JSON input: {e}\n")
        sys.exit(1)

    url = payload.get("url", "")
    html = payload.get("html", "")
    entry_type = payload.get("entry_type", "landing")
    page_type = payload.get("inferred_page_type", "")

    evaluator = EngagementEvaluator(url, html, entry_type, page_type)
    findings = evaluator.evaluate()

    print(json.dumps(findings, cls=FindingEncoder, indent=2))


if __name__ == "__main__":
    main()
