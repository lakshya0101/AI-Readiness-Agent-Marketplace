<div align="center">

# AI-Readiness Agent Marketplace

### Make every website discoverable, understandable, and actionable for AI agents.

**Adobe University Hackathon 2026 · Round 3: Development Round**

[![Agent Skills Specification](https://img.shields.io/badge/Agent_Skills-Compliant-blue.svg)](#marketplace-architecture)
[![Designated Entrypoint: audit-orchestrator](https://img.shields.io/badge/Entrypoint-audit--orchestrator-orange.svg)](#the-three-skills)
[![Automated Tests: 200 Passing](https://img.shields.io/badge/Tests-200_Passing-brightgreen.svg)](#engineering-rigor--verification)
[![Runtime: Pure Python StdLib](https://img.shields.io/badge/Runtime-Pure_Python_3.10+_StdLib-informational.svg)](#operational-safety--guardrails)
[![Package Size: ~141 KB](https://img.shields.io/badge/Package_Size-~141_KB_%28%3C50MB%29-success.svg)](#repository--package-structure)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

</div>

---

## 1. Product Overview

The **AI-Readiness Agent Marketplace** is an Agent Skill Marketplace that enables autonomous AI agents to audit any public website across machine discoverability and on-site user engagement. Operating through a single designated entrypoint (`audit-orchestrator`), it coordinates specialized evaluation skills to convert observable DOM and network evidence into normalized findings and prioritized remediation plans.

---

## 2. The Problem

The web is increasingly navigated by autonomous AI assistants, retrieval-augmented generation (RAG) engines, and LLM-driven search systems rather than traditional desktop browsers alone.

Traditional website audits optimize for legacy search engine rankings and cosmetic desktop layouts. For a website to succeed in an agent-mediated ecosystem, two complementary challenges must be resolved:

```text
                           Target Website Under Audit
                                       |
                  +--------------------+--------------------+
                  |                                         |
                  v                                         v
     [ 1. AI Discoverability Gap ]             [ 2. On-Site Engagement Gap ]
     Can AI crawlers and RAG systems           When an AI links directly to a deep
     reach, parse, and cite the site?          page, can visitors orient and act?
     - Crawler access & robots blocks          - Lost brand and parent identity
     - Client-side rendering dependencies      - Missing primary purpose & headings
     - Missing or malformed Schema.org         - Isolated pages lacking navigation
     - Contradictory identity metadata         - Absent call-to-action pathways
```

---

## 3. Marketplace Architecture & Flow

The system follows the **Agent Skills Specification**, exposing one primary orchestrator that delegates to decoupled, domain-specific audit skills:

```text
                               Target Website URL
                                       |
                                       v
                    +-------------------------------------+
                    |          audit-orchestrator         |
                    |    (Designated Market Entrypoint)   |
                    +------------------+------------------+
                                       |
                  +--------------------+--------------------+
                  |                                         |
                  v                                         v
     +--------------------------+              +--------------------------+
     |    ai-discoverability    |              |     engagement-audit     |
     |   (6-Stage Machine Pass) |              |   (5-Dimension DOM Pass) |
     +------------+-------------+              +------------+-------------+
                  |                                         |
                  +--------------------+--------------------+
                                       |
                                       v
                    +-------------------------------------+
                    |      Evidence Validation Guard      |
                    |  (Strict schema, zero hallucinations)|
                    +------------------+------------------+
                                       |
                                       v
                    +-------------------------------------+
                    |   Normalization & Deduplication     |
                    | (Fingerprinting & priority mapping) |
                    +------------------+------------------+
                                       |
                                       v
                    +-------------------------------------+
                    |       Consolidated Audit Report     |
                    | (JSON envelope + CLI summary table) |
                    +-------------------------------------+
```

---

## 4. The Three Skills

| Skill | Role | Scope & Capabilities |
| :--- | :--- | :--- |
| **`audit-orchestrator`** | **Designated Entrypoint** | Validates target URLs, executes audit skills in parallel or sequence, validates finding schemas, normalizes severities, eliminates cross-skill duplicates, and builds the prioritized action plan. |
| **`ai-discoverability`** | Specialized Audit Skill | Evaluates technical machine readability across six progressive stages: crawler permissions, SSR text density, structured JSON-LD data, semantic HTML hierarchies, entity consistency, and trust signals. |
| **`engagement-audit`** | Specialized Audit Skill | Evaluates visitor experience on deep landing pages across five structural dimensions: orientation, heading progression, parent context retention, exploratory navigation, and conversion next actions. |

---

## 5. Architectural Principles

| Principle | Implementation in This Marketplace | Why It Matters |
| :--- | :--- | :--- |
| **Single Entrypoint** | Exactly one marketplace entrypoint (`audit-orchestrator`) declared in `marketplace.json`. | Simplifies autonomous tool discovery for host LLM agents. |
| **Composable Skills** | Specialized skills run independently or as part of the orchestration pipeline. | Enables modular maintenance and targeted single-domain audits. |
| **Shared Finding Contract** | All findings adhere to a uniform JSON schema (`id`, `severity`, `evidence`, `suggested_action`). | Guarantees deterministic processing and clean report aggregation. |
| **Evidence-First Findings** | Every finding requires concrete, observable proof (DOM selectors, HTTP status, robots lines). | Rejects speculative statements and eliminates hallucinations. |
| **Conservative Deduplication**| Fingerprints findings by category and root cause while preserving distinct issues. | Prevents repetitive noise without dropping unique architectural flaws. |
| **Read-Only Execution** | Passive HTTP `GET`/`HEAD` requests; zero site modifications, state changes, or form submissions. | Safe for automated scanning against any public web property. |
| **Pure Python Runtime** | Zero third-party dependencies; executes entirely within the Python 3.10+ standard library. | Zero installation friction, instant startup, and dependable execution. |

---

## 6. AI Discoverability: 6-Stage Pipeline

```text
REACH  ──▶  READ  ──▶  EXTRACT  ──▶  UNDERSTAND  ──▶  IDENTIFY  ──▶  TRUST
```

1. **Reach**: Verifies hostname resolution, HTTP availability, redirect chains, and AI crawler permissions (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Bingbot`).
2. **Read**: Evaluates client-side rendering dependencies, initial server-delivered HTML payload density, and text-to-code ratio for non-JavaScript parsers.
3. **Extract**: Validates presence, syntax, and schema conformance of Schema.org JSON-LD blocks and OpenGraph metadata.
4. **Understand**: Inspects semantic document hierarchy (`<main>`, `<article>`, `<nav>`, `<footer>`), heading progression (`h1`–`h6`), and content landmark distribution.
5. **Identify**: Assesses brand and organization identity consistency across titles, OpenGraph metadata, and structured data declarations.
6. **Trust**: Evaluates transport security (HTTPS), attribution (authors, publishers), canonical URL declarations, and content freshness indicators.

---

## 7. On-Site Engagement: 5 Core Dimensions

1. **Landing Experience**: Checks immediate brand context, viewport semantic stability, and primary value proposition upon entry.
2. **Information Orientation**: Evaluates heading hierarchy, section outlining, and primary content landmarks without assuming prior site familiarity.
3. **Deep-Page Context Retention**: Detects isolated nested pages lacking parent identity, site title, or overarching organizational context.
4. **Navigation Pathways**: Verifies breadcrumb trails, utility navigation, parent-directory links, and homepage return routes.
5. **Meaningful Next Actions**: Inspects primary and secondary call-to-action (CTA) affordances, conversion links, documentation pointers, and contact mechanisms.

---

## 8. Structured Audit Output & Findings

Every audit finding is evidence-grounded, categorized, severity-ranked, and paired with actionable remediation guidance.

### Finding Schema Example

```json
{
  "id": "ENG-401",
  "category": "on_site_engagement",
  "subcategory": "navigation",
  "title": "Severe lack of exploratory navigation",
  "severity": "high",
  "evidence": "The landing page contains 0 <nav> elements, 0 headers/footers, and fewer than 2 total links.",
  "why_it_matters": "Users are effectively trapped on this page with no structural pathways to explore the broader website.",
  "suggested_action": {
    "summary": "Add site navigation structure",
    "details": "Provide header navigation, footer links, or contextual related links to allow users to explore the site.",
    "priority": "high"
  }
}
```

### Consolidated Report Structure

```json
{
  "site": "https://example.com",
  "audited_at": "2026-09-12T01:00:00Z",
  "summary": {
    "total_findings": 2,
    "critical": 0,
    "high": 1,
    "medium": 0,
    "low": 1
  },
  "findings": [ ... ],
  "modules": {
    "ai_discoverability": { "status": "success", "findings_count": 1 },
    "on_site_engagement": { "status": "success", "findings_count": 1 }
  },
  "limitations": [ ... ],
  "prioritized_action_plan": [
    {
      "finding_id": "ENG-401",
      "category": "on_site_engagement",
      "title": "Severe lack of exploratory navigation",
      "severity": "high",
      "priority": "high",
      "action_summary": "Add site navigation structure",
      "action_details": "Provide header navigation, footer links, or contextual related links to allow users to explore the site."
    }
  ]
}
```

---

## 9. Operational Safety & Guardrails

- **Read-Only by Design**: Issues passive `GET` and `HEAD` requests only. Never submits forms, creates state, or alters target domains.
- **Bounded Crawl Budget**: Enforces a strict default crawl limit (5 pages) and per-request timeout (10 seconds) to prevent server overload.
- **Robots-Aware Crawling**: Respects `robots.txt` disallow directives and crawl boundaries.
- **Provider-Neutral Rules**: Evaluates standard web specifications (HTML5, W3C WAI-ARIA, Schema.org) rather than proprietary platform heuristics.
- **Zero Pretrained Model Dependencies**: Operates deterministically via pure algorithmic inspection without requiring model weights.
- **Graceful Fault Tolerance**: Individual skill timeouts or network exceptions never crash the orchestrator; healthy module outputs are preserved with explicit limitation notes.

---

## 10. Engineering Rigor & Verification

The marketplace implementation is hardened through extensive unit, stage, contract, and live-site regression test suites:

- **200 Automated Tests Passing**:
  - `ai-discoverability` Unit & Stage Tests (133 tests)
  - `engagement-audit` Unit Tests (22 tests)
  - `audit-orchestrator` Contract & Validation Tests (13 tests)
  - Multi-Skill Integration & Deduplication Tests (14 tests)
  - 18-Pattern Unseen Website Matrix (18 tests)
- **Live Public Website Hardening**: Tested and verified against diverse real-world architectures (`react.dev`, `stripe.com`, `adobe.com`, `vercel.com`, `pypi.org`, `docs.python.org`, `example.com`).
- **Cross-Stage Contract Verification**: Fixed and regression-tested `ReadObservation` data model consistency across all downstream evaluation inspectors.

---

## 11. Quick Start

### Prerequisites
- Python 3.10 or higher (Pure Python standard library; no `pip install` required).

### Run an Audit via CLI

```bash
# Human-readable CLI summary
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com

# Machine-readable JSON output to stdout
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com --json

# Save JSON report to file
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com --out report.json
```

### Run Programmatically via Python API

```python
import sys
from pathlib import Path

# Add orchestrator script path
sys.path.insert(0, str(Path("skills/audit-orchestrator/scripts")))
from orchestrator import AuditOrchestrator

orchestrator = AuditOrchestrator()
report = orchestrator.run_audit("https://example.com")
print(report.to_dict())
```

### Run the Test Suite

```bash
python -m pytest tests/ -v
```

---

## 12. Repository & Package Structure

```text
AI-Readiness-Agent-Marketplace/
├── marketplace.json                    # Marketplace catalog and single entrypoint definition
├── README.md                           # Marketplace overview and technical specifications
├── LICENSE                             # MIT License
├── docs/                               # Deep technical architecture and methodology
│   ├── architecture.md                 # System architecture and data flow
│   ├── methodology.md                  # Scoring model and evidence criteria
│   └── integration-checklist.md        # Pre-merge verification standards
├── skills/                             # Agent Skills
│   ├── audit-orchestrator/             # Designated marketplace entrypoint
│   │   ├── SKILL.md                    # Orchestrator skill specification
│   │   ├── references/                 # Input, finding, and report JSON schemas
│   │   └── scripts/                    # Orchestrator, validation, normalization
│   ├── ai-discoverability/             # Specialized AI discoverability skill
│   │   ├── SKILL.md                    # Discoverability skill specification
│   │   ├── references/                 # Stage criteria documentation
│   │   └── scripts/                    # 6-stage audit engine
│   └── engagement-audit/               # Specialized on-site engagement skill
│       ├── SKILL.md                    # Engagement skill specification
│       ├── references/                 # Engagement criteria documentation
│       └── scripts/                    # 5-dimension evaluator and DOM parser
└── tests/                              # Automated test suite (200 tests)
    ├── conftest.py                     # Module resolution and test fixtures
    ├── discoverability/                # Discoverability stage test suites
    ├── integration/                    # Orchestration and 18-pattern test matrix
    └── test_engagement_audit.py        # Engagement unit test suite
```

---

## 13. Submission Context & References

This project is packaged as a self-contained Agent Skill Marketplace compliant with the **Adobe University Hackathon 2026 Round 3** requirements. The root delivery contains `marketplace.json`, all three skill directories, and this reference `README.md`.

- [Architecture & Technical Design](docs/architecture.md)
- [Audit Methodology & Scoring Framework](docs/methodology.md)
- [Integration Checklist & Verification Standards](docs/integration-checklist.md)
- [Marketplace Catalog Manifest](marketplace.json)

---

## 14. License

This project is licensed under the [MIT License](LICENSE).
