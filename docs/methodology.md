# Audit Methodology & Evaluation Framework

> **Brand AI Readiness Audit — Agent Skill Marketplace**  
> **Adobe University Hackathon 2026 — Round 3**

---

## 1. AI Discoverability Methodology

AI systems, autonomous agents, and search indexing pipelines discover, parse, and cite web content through a multi-stage ingestion funnel. The AI Discoverability skill audits websites along this 6-stage lifecycle:

```
+---------+     +--------+     +-----------+     +------------+     +----------+     +---------+
|  Reach  | --> |  Read  | --> |  Extract  | --> | Understand | --> | Identify | --> |  Trust  |
+---------+     +--------+     +-----------+     +------------+     +----------+     +---------+
```

### Stage 1: Reach (Crawler Access & Infrastructure)
- **Objective**: Ensure automated AI agents and crawlers can discover and fetch resources without unintended network blockers.
- **Key Vectors**: HTTP status codes, redirection hops, robots.txt directives (specifically permissions for modern AI bots like `GPTBot`, `ClaudeBot`, `PerplexityBot`), XML sitemaps, and server response latencies.

### Stage 2: Read (Content Parseability & Rendering)
- **Objective**: Ensure information is extractable without heavy client-side JavaScript execution dependencies.
- **Key Vectors**: Server-side rendered (SSR) HTML vs. client-rendered content, HTML-to-code ratio, unencumbered textual body content.

### Stage 3: Extract (Structured Data & Semantic Markup)
- **Objective**: Provide structured schema and machine-readable data anchors.
- **Key Vectors**: Schema.org JSON-LD definitions (`Organization`, `WebSite`, `FAQPage`, `Product`, `Article`), OpenGraph metadata, Dublin Core, and semantic HTML5 structural elements (`<main>`, `<article>`, `<header>`).

### Stage 4: Understand (Syntactic & Semantic Clarity)
- **Objective**: Enable LLMs to parse information hierarchies and topical relationships unambiguously.
- **Key Vectors**: Heading hierarchy (`H1` -> `H2` -> `H3`), concise topic definitions, list structures, and question-and-answer patterns suitable for direct citations.

### Stage 5: Identify (Entity Disambiguation & Brand Clarity)
- **Objective**: Ensure brand, entity names, products, and canonical relationships are unambiguous across all indexed pages.
- **Key Vectors**: Canonical URLs, consistent brand naming conventions, social profile `sameAs` references, and entity association anchors.

### Stage 6: Trust (Attribution & Verification Signals)
- **Objective**: Establish verifiable credibility signals that AI citation engines require for high-confidence source citations.
- **Key Vectors**: Explicit author/organization attribution, privacy disclosures, terms of service availability, publication timestamps, and HTTPS security.

---

## 2. On-Site Engagement Methodology

When visitors (human or agent-referred) land on a website, retention and conversion depend on cognitive ease, visual hierarchy, and action clarity. The On-Site Engagement skill audits websites along this 5-stage funnel:

```
+-----------+     +---------------+     +-----------+     +--------------+     +---------------+
|  Landing  | --> |  Orientation  | --> |  Context  | --> |  Navigation  | --> |  Next Action  |
+-----------+     +---------------+     +-----------+     +--------------+     +---------------+
```

### Stage 1: Landing (First Viewport Impression)
- **Objective**: Deliver a stable, rapid, and clutter-free above-the-fold visual experience.
- **Key Vectors**: Above-the-fold viewport utilization, visual noise, layout shifts, intrusive overlays, and initial render structure.

### Stage 2: Orientation (Immediate Value Identification)
- **Objective**: Communicate what the product/service is and who it is for within 3 seconds of arrival.
- **Key Vectors**: Prominence of the primary `H1` headline, clarity of the core value proposition, absence of vague buzzwords.

### Stage 3: Context (Comprehension & Credibility)
- **Objective**: Provide sufficient explanatory depth to build confidence and answer visitor questions.
- **Key Vectors**: Content readability, scannability (bulleted value points, feature highlights), visual proof (testimonials, trust badges), and logical narrative flow.

### Stage 4: Navigation (Frictionless Exploration)
- **Objective**: Enable visitors to find relevant details without cognitive friction.
- **Key Vectors**: Menu simplicity, accessible site navigation structure, internal link clarity, and descriptive anchor text.

### Stage 5: Next Action (Action Affordance & Conversion)
- **Objective**: Guide the visitor toward clear, actionable next steps.
- **Key Vectors**: Prominence, visual contrast (WCAG AA standard), positioning, and clarity of Call-To-Action (CTA) buttons, minimal form friction.

---

## 3. Guiding Audit Principles

1. **Read-Only**: The audit performs non-destructive, passive observation.
2. **Evidence-Driven**: Every finding must cite concrete, observable evidence (DOM selector, computed style, HTTP header, robots.txt line). No speculative or hallucinated assertions are permitted.
3. **Provider-Neutral**: Evaluation criteria apply objectively across any web stack, CMS, or hosting provider.
4. **Actionable**: Recommendations must include a concise summary and concrete implementation guidance.
