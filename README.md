# Brand AI Readiness Audit

> **Adobe University Hackathon 2026 — Round 3**  
> An Agent Skill Marketplace for evidence-backed website audits across AI Discoverability and On-Site Engagement.

---

## 1. Project Purpose & Overview

As AI assistants (such as ChatGPT, Claude, and Perplexity) increasingly discover, interpret, and cite web resources, websites face a dual-sided challenge:
1. **AI Discoverability**: Can automated AI crawlers reach, parse, disambiguate, understand, and trust the site's brand and content?
2. **On-Site Engagement**: When visitors (human or agent-directed) arrive at the website, does the landing viewport orient them immediately, convey clear value, facilitate navigation, and provide frictionless next actions?

This project implements an **Agent Skill Marketplace** that accepts any public website URL and produces a comprehensive, read-only, evidence-backed audit report with prioritized recommendations.

---

## 2. Core Architecture

The marketplace operates through a single designated entrypoint: the **`audit-orchestrator`**.

```text
                         Website Input URL
                                |
                                v
                   +--------------------------+
                   |    Audit Orchestrator    |
                   |   (marketplace.json)     |
                   +-------------+------------+
                                 |
                 +---------------+---------------+
                 |                               |
                 v                               v
    +-------------------------+     +-------------------------+
    |    ai-discoverability   |     |    engagement-audit     |
    | (Aditya - DISC-xxx)     |     | (Vishesh - ENG-xxx)     |
    +------------+------------+     +------------+------------+
                 |                               |
                 +---------------+---------------+
                                 |
                                 v
                   +--------------------------+
                   | Finding Validation Guard |
                   | - Zero Hallucination     |
                   | - Concrete Evidence Check|
                   +-------------+------------+
                                 |
                                 v
                   +--------------------------+
                   | Conservative Dedup Engine|
                   | Severity Normalization   |
                   | Priority Calculation     |
                   +-------------+------------+
                                 |
                                 v
                   +--------------------------+
                   |   Final Audit Report     |
                   | - Summary Counts         |
                   | - Evidence-Backed Issues |
                   | - Actionable Next Steps  |
                   | - Diagnostic Limitations |
                   +--------------------------+
```

---

## 3. Marketplace Skills & Team Responsibilities

| Skill | Directory | Owner | Branch | Status | Description |
|---|---|---|---|---|---|
| **`audit-orchestrator`** *(Entrypoint)* | `skills/audit-orchestrator/` | **Lakshya** | `feature/lakshya-orchestrator` | **Complete / Ready** | Coordinates specialized skills, enforces finding contracts, deduplicates issues, normalizes severities/priorities, handles failures gracefully, and compiles final audit reports. |
| **`ai-discoverability`** | `skills/ai-discoverability/` | **Aditya** | `feature/aditya-discoverability` | *In Progress* | Audits technical crawlability, robots.txt AI rules, structured data (Schema.org JSON-LD), extractability, entity clarity, and brand trust signals. |
| **`engagement-audit`** | `skills/engagement-audit/` | **Vishesh** | `feature/vishesh-engagement` | *In Progress* | Audits landing viewport hierarchy, above-the-fold value clarity, cognitive load, navigation affordances, and Call-to-Action (CTA) contrast/friction. |

---

## 4. Input & Output Contracts

### Input
The system accepts a clean, provider-neutral website URL:
```json
{
  "site": "https://example.com"
}
```

### Common Finding Contract
All specialized skills submit findings adhering to the standard schema:
```json
{
  "id": "DISC-001",
  "category": "ai_discoverability",
  "subcategory": "structured_data",
  "title": "Missing Schema.org Organization JSON-LD markup",
  "severity": "high",
  "evidence": "Audited https://example.com - No JSON-LD Organization script tags found in HTML head or body.",
  "why_it_matters": "LLMs and search crawlers cannot unambiguously resolve corporate identity or verify official brand links without structured entity markup.",
  "suggested_action": {
    "summary": "Implement Schema.org Organization markup in JSON-LD",
    "details": "Embed a JSON-LD script on the homepage defining '@type': 'Organization', 'name', 'url', and 'sameAs' social links.",
    "priority": "high"
  }
}
```

### Final Output Report
```json
{
  "site": "https://example.com",
  "audited_at": "2026-09-08T23:50:00Z",
  "summary": {
    "total_findings": 4,
    "critical": 0,
    "high": 2,
    "medium": 2,
    "low": 0
  },
  "findings": [...],
  "modules": {
    "ai_discoverability": { "status": "success", "findings_count": 2 },
    "on_site_engagement": { "status": "success", "findings_count": 2 }
  },
  "limitations": [],
  "prioritized_action_plan": [...]
}
```

---

## 5. Key System Guarantees

- **100% Read-Only & Non-Destructive**: Audits execute passively without modifying target websites.
- **Zero Evidence Hallucination**: Findings must cite concrete, observable evidence; findings with missing evidence are strictly rejected.
- **Graceful Failure**: If one audit skill fails (e.g. network timeout), findings from the healthy skill are preserved, and limitations are recorded transparently.
- **Deterministic & Dependency-Free**: Pure Python standard library implementation with zero heavy external dependencies.

---

## 6. Getting Started & Running Tests

### Running the Orchestrator
```bash
# Direct CLI execution
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com

# Formatted JSON output
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com --json

# Save report to file
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com --out report.json
```

### Running the Test Suite
```bash
python -m pytest tests/ -v
```

---

## 7. Documentation

- [Architecture & Technical Design](docs/architecture.md)
- [Audit Methodology & Framework](docs/methodology.md)
- [Audit Orchestrator Skill](skills/audit-orchestrator/SKILL.md)
- [Input Schema](skills/audit-orchestrator/references/input_schema.json)
- [Finding Schema](skills/audit-orchestrator/references/finding_schema.json)
- [Report Schema](skills/audit-orchestrator/references/report_schema.json)
