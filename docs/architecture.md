# Architecture & Technical Design

> **Brand AI Readiness Audit — Agent Skill Marketplace**  
> **Adobe University Hackathon 2026 — Round 3**  
> **Lead Architect & Orchestrator**: Lakshya

---

## 1. System Overview

The Brand AI Readiness Agent Marketplace is a modular, read-only audit platform designed to evaluate any public website across two complementary dimensions:
1. **AI Discoverability**: How effectively AI assistants, LLM indexing pipelines, and automated crawlers can discover, extract, interpret, disambiguate, and cite site information.
2. **On-Site Engagement**: How clearly the website orients first-time visitors arriving from AI search, conveys its core proposition, structures navigation, and guides visitors toward next actions.

The orchestrator serves as the **single designated entrypoint** for the marketplace, coordinating specialized agent skills, validating incoming data contracts, deduplicating issues conservatively, normalizing severity and priority ratings, and producing a structured, evidence-backed audit report.

```
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
                   |  Finding Payload Guard   |
                   |   - Strict Contract Check|
                   |   - No Fake Evidence     |
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
                   | - Aggregated Summary     |
                   | - Prioritized Action Plan|
                   | - Explicit Limitations   |
                   +--------------------------+
```

---

## 2. Skill Responsibilities & Ownership

| Skill | Directory | Lead | Branch | Primary Responsibility |
|---|---|---|---|---|
| **`audit-orchestrator`** | `skills/audit-orchestrator/` | Lakshya | `feature/lakshya-orchestrator` | Marketplace entrypoint, lifecycle management, input/finding validation, deduplication, rating normalization, graceful degradation, and final report generation. |
| **`ai-discoverability`** | `skills/ai-discoverability/` | Aditya | `feature/aditya-discoverability` | Crawlability analysis, HTTP headers, robots.txt AI rules, sitemaps, JSON-LD Schema.org entities, OpenGraph, content extractability, and brand citation readiness. |
| **`engagement-audit`** | `skills/engagement-audit/` | Vishesh | `feature/vishesh-engagement` | Landing viewport hierarchy, above-the-fold value clarity, cognitive load, navigation affordances, and Call-To-Action (CTA) contrast and friction. |

---

## 3. Data Contracts

### 3.1 Input Contract
The system accepts a minimal, provider-neutral input:
```json
{
  "site": "https://example.com"
}
```

### 3.2 Finding Baseline Contract
All specialized skills must produce findings adhering to this common JSON structure:
```json
{
  "id": "DISC-001",
  "category": "ai_discoverability",
  "subcategory": "structured_data",
  "title": "Missing Schema.org Organization JSON-LD markup",
  "severity": "high",
  "evidence": "Audited https://example.com/ - No JSON-LD Organization script tags found in HTML head or body.",
  "why_it_matters": "LLMs and AI search crawlers cannot unambiguously resolve corporate identity or verify official brand links without structured entity markup.",
  "suggested_action": {
    "summary": "Implement Schema.org Organization markup in JSON-LD",
    "details": "Embed a JSON-LD script on the homepage defining '@type': 'Organization', 'name', 'url', and 'sameAs' social links.",
    "priority": "high"
  },
  "confidence": "high",
  "affected_pages": ["https://example.com/"],
  "evidence_type": "HTML_DOM",
  "methodology": "Identify",
  "remediation_complexity": "low"
}
```

### 3.3 Output Report Contract
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
  "findings": [ ... ],
  "modules": {
    "ai_discoverability": { "status": "success", "findings_count": 2 },
    "on_site_engagement": { "status": "success", "findings_count": 2 }
  },
  "limitations": [ ... ],
  "prioritized_action_plan": [ ... ]
}
```

---

## 4. Finding Lifecycle & Pipeline

### 4.1 Input Validation & Normalization
The orchestrator inspects the target website string, normalizes missing protocols (defaults to `https://`), validates hostname structure, and rejects malformed inputs upfront.

### 4.2 Module Dispatch & Execution
The orchestrator invokes specialized skills asynchronously or synchronously. Mocks decouple orchestrator testing during parallel branch development.

### 4.3 Strict Finding Validation & Integrity Guard
Each incoming finding is validated against schema constraints:
- **Mandatory Fields**: `id`, `category`, `subcategory`, `title`, `severity`, `evidence`, `why_it_matters`, and `suggested_action`.
- **Integrity Rule (Zero Hallucination)**: The orchestrator never invents missing evidence. Findings lacking concrete observable evidence are rejected and logged in report limitations.

### 4.4 Conservative Deduplication
- Identical finding IDs or semantic fingerprint collisions (same category, subcategory, and core defect keywords) are merged.
- Distinct issues (e.g., missing Schema.org vs. ambiguous brand naming) are preserved.
- When merged, the highest severity is preserved, unique affected URLs and references are united, and evidence snippets are appended.

### 4.5 Severity Normalization
Standard severities: `critical`, `high`, `medium`, `low`.  
Inconsistent strings (e.g. `blocker`, `warning`, `minor`) are mapped deterministically to canonical levels; unresolvable entries default conservatively to `medium`.

### 4.6 Priority Calculation
Action priority reflects how urgently the fix should be implemented:
- Combines normalized severity, evidence confidence, affected page breadth, and remediation complexity.
- Quick wins (low complexity on high-impact issues) receive elevated priority.
- No artificial arbitrary numerical scores are generated.

### 4.7 Graceful Degradation & Module Failure Handling
If one specialized skill encounters a network error, timeout, or parsing crash:
1. The successful module's findings are fully preserved.
2. The orchestrator records the failing module's error state in `modules` and adds clear diagnostic entries to `limitations`.
3. The final report is generated cleanly with all available verified data.

---

## 5. Shared Crawl Data Architecture

To prevent duplicate crawling and redundant network overhead across specialized skills:
- The orchestrator architecture supports passing a shared crawl snapshot (DOM, raw HTML, HTTP headers, robots.txt, sitemap XML, rendered DOM).
- Specialized skills consume the shared snapshot or query supplementary endpoints as needed.
- This design ensures high execution speed and provider neutrality without blocking independent module development.
