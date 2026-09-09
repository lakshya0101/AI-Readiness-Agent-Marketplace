---
name: On-Site Engagement Audit
description: Audits a webpage's structural engagement signals to evaluate orientation, context retention, navigation, and actionability.
---

# On-Site Engagement Audit

## Description
This skill evaluates website engagement signals based purely on observable structural HTML data without subjective visual aesthetic judgments. It analyzes 5 core dimensions:
1. Landing experience
2. Information orientation
3. Deep-page context retention
4. Navigation
5. Meaningful next action

## When to Use
Use this skill when analyzing a website's readiness for AI and organic visitor engagement, especially checking deep-page entries where an AI directly links a user to a nested page.

## Inputs
Accepts JSON through stdin containing:
- `url` (string)
- `html` (string)
- `entry_type` (string: "landing" or "deep")
- `inferred_page_type` (optional string)

## Procedure
1. The orchestrator collects the target URL's HTML.
2. The orchestrator pipes a JSON payload to `scripts/audit_engagement.py`.
3. The module infers the page type if missing.
4. It evaluates the page against the 5 dimensions, using conservative false-positive controls.
5. Emits strict, evidence-backed findings to stdout.

## Output
Outputs a JSON array of Findings following the team's agreed schema. Errors/diagnostics print to stderr.

## Dependencies/Tools
- Python 3 (Standard library only; no external dependencies)

## AI-Referred Deep-Entry Test
This skill treats deep pages as first-time interactions. When `entry_type` is "deep", it evaluates if the user can understand the brand, page purpose, relationship to broader offering, and meaningful next actions, simulating a direct AI recommendation.

## Limitations
- Analyzes structural DOM only; cannot evaluate CSS aesthetics or visual layout.
- Evaluates a single supplied page, does not crawl.
