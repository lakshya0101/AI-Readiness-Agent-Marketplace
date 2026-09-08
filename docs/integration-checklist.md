# Integration Checklist & Pre-Merge Verification

> **Brand AI Readiness Audit — Agent Skill Marketplace**  
> **Lead Orchestrator**: Lakshya

This checklist defines the criteria that each specialized skill module (`ai-discoverability` and `engagement-audit`) must fulfill before being integrated into `feature/lakshya-orchestrator` and `main`.

---

## 1. AI Discoverability Integration (`feature/aditya-discoverability`)

- [ ] **Skill Path**: Code resides under `skills/ai-discoverability/` with `scripts/` and `references/`.
- [ ] **SKILL.md Compliance**: Valid YAML frontmatter with exact `name: ai-discoverability` and descriptive `description`.
- [ ] **Interface / Runner**: Module exposes a callable entrypoint (e.g. `audit_discoverability(site: str, options: dict) -> dict`).
- [ ] **Input Compatibility**: Accepts sanitized URL and handles optional crawl configuration gracefully.
- [ ] **Finding Schema Compatibility**: Findings strictly match [finding_schema.json](../skills/audit-orchestrator/references/finding_schema.json).
- [ ] **ID Format**: Finding IDs conform to `DISC-001`, `DISC-002`, etc.
- [ ] **Concrete Observable Evidence**: Every finding must include verifiable evidence (DOM selector, HTTP status, robots.txt snippet). No speculative assertions.
- [ ] **Severity Normalization**: Severities use standard canonical levels (`critical`, `high`, `medium`, `low`).
- [ ] **Actionable Recommendations**: `suggested_action` includes clear `summary`, `details`, and `priority`.
- [ ] **Failure Handling**: Returns structured failure payload (`{"skill": "ai-discoverability", "status": "failure", "error": "..."}`) on timeout or crawl errors instead of unhandled crashes.

---

## 2. On-Site Engagement Integration (`feature/vishesh-engagement`)

- [ ] **Skill Path**: Code resides under `skills/engagement-audit/` with `scripts/` and `references/`.
- [ ] **SKILL.md Compliance**: Valid YAML frontmatter with exact `name: engagement-audit` and descriptive `description`.
- [ ] **Interface / Runner**: Module exposes a callable entrypoint (e.g. `audit_engagement(site: str, options: dict) -> dict`).
- [ ] **Input Compatibility**: Accepts sanitized URL and handles optional crawl configuration gracefully.
- [ ] **Finding Schema Compatibility**: Findings strictly match [finding_schema.json](../skills/audit-orchestrator/references/finding_schema.json).
- [ ] **ID Format**: Finding IDs conform to `ENG-001`, `ENG-002`, etc.
- [ ] **Concrete Observable Evidence**: Every finding must cite observable UI proof (computed style contrast, viewport element offset, DOM hierarchy).
- [ ] **Severity Normalization**: Severities use standard canonical levels (`critical`, `high`, `medium`, `low`).
- [ ] **Actionable Recommendations**: `suggested_action` includes clear `summary`, `details`, and `priority`.
- [ ] **Failure Handling**: Returns structured failure payload (`{"skill": "engagement-audit", "status": "failure", "error": "..."}`) on timeout or layout render errors.

---

## 3. Orchestrator Integration & Aggregation

- [ ] **Module Dispatch**: Orchestrator dynamically imports or hooks both specialized skill runners.
- [ ] **Shared Acquisition Evaluation**: Inspect if common crawl data (DOM snapshot, headers) can be shared without duplicate network fetches.
- [ ] **Payload Guard**: Strict validation validates every incoming finding; rejects findings lacking concrete evidence.
- [ ] **Conservative Deduplication**: Merges overlapping issues on identical resources while preserving distinct findings.
- [ ] **Rating Normalization**: Canonical severity normalization and dynamic evidence-backed priority calculation.
- [ ] **Graceful Failure**: If either module fails, the orchestrator preserves the healthy module's findings and records explicit limitations.
- [ ] **Final Report**: Generates compliant JSON report matching [report_schema.json](../skills/audit-orchestrator/references/report_schema.json) with prioritized action plan.

---

## 4. End-to-End Verification Scenarios

Before final submission readiness, test the integrated system against:
- [ ] **Static Website**: Plain HTML/CSS site with minimal client JS.
- [ ] **JS-Heavy / SPA Website**: React/Vue/Angular client-rendered application.
- [ ] **E-commerce Website**: Product catalogs, pricing schemas, shopping cart engagement flows.
- [ ] **SaaS Landing Page**: Value proposition hero sections, feature grids, CTA buttons.
- [ ] **Corporate Website**: Organization metadata, investor relations, multi-tier navigation.
- [ ] **Documentation / Knowledge Site**: Technical docs with deep heading hierarchies and code blocks.
- [ ] **Content / News Site**: Articles with author attributions, dates, Schema.org Article markup.
- [ ] **Deep Pages & Subdirectories**: Multi-page audits checking affected pages lists.
- [ ] **Empty Findings (Clean Site)**: Verifies zero-finding handling and empty summary counts.
- [ ] **Single Module Failure**: Verifies graceful degradation and limitation recording.
- [ ] **Duplicate / Overlapping Findings**: Verifies conservative deduplication.
- [ ] **Malformed / Invalid Findings**: Verifies validation guard rejection of bad payloads.
- [ ] **Unseen Websites**: Tests generalization on previously untested public domains.
