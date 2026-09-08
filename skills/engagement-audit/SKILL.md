---
name: engagement-audit
description: Specialized audit skill evaluating visitor landing orientation, viewport value clarity, context comprehension, navigation hierarchy, and conversion action affordance.
---

# On-Site Engagement Audit Skill

> **Branch**: `feature/vishesh-engagement`  
> **Lead**: Vishesh  
> **Status**: In Development (Contract Defined)

## Overview

The `engagement-audit` skill performs an evidence-backed audit of the human and agent-directed on-site experience, evaluating how effectively a website orients visitors, communicates its core value proposition, facilitates navigation, and prompts meaningful next actions.

## Audit Lifecycle (Methodology)

1. **Landing**: First visual impression, above-the-fold viewport clarity, layout stability.
2. **Orientation**: Immediate identification of site purpose, target audience, and primary offering.
3. **Context**: Explanatory content depth, readability, visual hierarchy, credibility signals.
4. **Navigation**: Menu clarity, search accessibility, internal link logical hierarchy.
5. **Next Action**: Visual contrast and affordance of primary Call-to-Action (CTA) elements, friction reduction.

## Contract Compliance

All findings produced by this skill must adhere to the standard finding contract:
- Category: `on_site_engagement`
- Finding ID format: `ENG-001`, `ENG-002`, etc.
- Concrete, non-empty observable evidence is required.

See [finding_schema.json](../audit-orchestrator/references/finding_schema.json) for contract specifications.
