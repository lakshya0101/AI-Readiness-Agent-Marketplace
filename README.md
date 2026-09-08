# Brand AI Readiness Audit

> Adobe University Hackathon 2026 — Round 3

An Agent Skill Marketplace for auditing websites across two dimensions:

- AI Discoverability
- On-Site Engagement

The system accepts a website URL, analyzes the site using specialized
agent skills, collects evidence-backed findings, assigns severity,
and generates prioritized recommendations for improvement.

---

## Problem

AI assistants increasingly discover, interpret, and recommend information
from websites.

However, a website may be difficult for AI systems to discover, read,
understand, identify, trust, or cite. Even when a user reaches the website,
poor orientation, unclear information architecture, or weak next actions
can prevent meaningful engagement.

This project addresses both sides of that problem through an automated,
read-only website audit.

---

## Solution

The project implements an Agent Skill Marketplace composed of specialized
skills.

Given a website URL, the marketplace:

1. Crawls and inspects the website.
2. Audits AI discoverability.
3. Audits content extractability and structured information.
4. Evaluates entity clarity and information consistency.
5. Evaluates on-site visitor engagement.
6. Aggregates findings from specialized skills.
7. Assigns severity and priority.
8. Produces a structured audit report with evidence and recommended fixes.

---

## Architecture

```text
                     Website URL
                          |
                          v
                +--------------------+
                | Audit Orchestrator |
                +---------+----------+
                          |
             +------------+------------+
             |                         |
             v                         v
    +------------------+      +------------------+
    | AI Discoverability|      | Engagement Audit |
    |      Skills       |      |      Skills      |
    +---------+--------+      +---------+--------+
              |                         |
              +------------+------------+
                           |
                           v
                 +----------------------+
                 | Finding Aggregation  |
                 | Severity & Priority  |
                 +----------+-----------+
                            |
                            v
                    Final Audit Report
