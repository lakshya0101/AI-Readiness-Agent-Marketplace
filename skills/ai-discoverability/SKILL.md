---
name: ai-discoverability
description: Specialized audit skill evaluating technical crawler reachability, robots.txt AI permissions, structured JSON-LD data, entity identity clarity, and brand citation extractability.
---

# AI Discoverability Skill

> **Branch**: `feature/aditya-discoverability`  
> **Lead**: Aditya  
> **Status**: In Development (Contract Defined)

## Overview

The `ai-discoverability` skill performs an evidence-backed audit of how readily AI systems (search engines, LLM assistants, autonomous agents) can discover, parse, extract, understand, and cite content from a target website.

## Audit Lifecycle (Methodology)

1. **Reach**: Server reachability, HTTP headers, robots.txt crawler access, sitemap availability.
2. **Read**: DOM extractability, content-to-code ratio, server-rendered vs client-rendered content.
3. **Extract**: Structured data syntax, Schema.org entities, OpenGraph tags, semantic HTML landmarks.
4. **Understand**: Topic coherence, heading structure, unambiguous textual definitions.
5. **Identify**: Entity disambiguation, brand names, canonical URLs, organization metadata.
6. **Trust**: Author attribution, terms of service, publisher disclosures, security headers.

## Contract Compliance

All findings produced by this skill must adhere to the standard finding contract:
- Category: `ai_discoverability`
- Finding ID format: `DISC-001`, `DISC-002`, etc.
- Concrete, non-empty observable evidence is required.

See [finding_schema.json](../audit-orchestrator/references/finding_schema.json) for contract specifications.
