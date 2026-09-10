# AI Discoverability Reference & Heuristic Guide

> **Module**: `ai-discoverability`  
> **Lead**: Aditya (`feature/aditya-discoverability`)  
> **Current Implemented Stages**: **Reach, Read, Extract, Understand, Identify, & Trust**  
> **Standard**: Brand AI Readiness Agent Marketplace

---

## 1. Module Purpose

The `ai-discoverability` module audits how effectively AI search assistants, autonomous agents, and LLM indexing pipelines can discover, reach, parse, extract, understand, identify, and trust web content.

---

## 2. Six-Stage Methodology Overview

1. **Reach** (*Implemented*): Evaluates whether important publicly accessible information on the website can be reached by automated readers under normal crawl conditions (URL normalization, HTTP response/redirects, robots.txt RFC 9309 parsing, sitemap discovery, internal link extraction, and broken page detection).
2. **Read** (*Implemented*): Evaluates whether an automated reader can obtain meaningful page information from the initial HTTP response, or if important content is materially dependent on client-side rendering (CSR / SPA shells, text-to-code ratios, visible textual content, loading placeholders, noscript warnings).
3. **Extract** (*Implemented*): Deterministic extraction of Schema.org JSON-LD, OpenGraph tags, social metadata, and semantic HTML landmarks. Analyzes structured data quality and identifies meaningful schema gaps.
4. **Understand** (*Implemented*): Topic coherence, heading hierarchy (`H1` $\rightarrow$ `H2` $\rightarrow$ `H3`), subject consistency, and contextual sufficiency.
5. **Identify** (*Implemented*): Entity disambiguation, brand naming consistency, canonical URLs, and `sameAs` linkage validation.
6. **Trust** (*Implemented*): Attribution signals, publication timestamps, date consistency, HTTPS transport security, transparency disclosures, and internal factual corroboration.

---

## 3. Reach Stage Heuristics & Audit Criteria

### 3.1 Target URL Validation & Normalization
- **Normalization**: Automatically prepends `https://` if no scheme is specified; removes URL fragments (`#...`); normalizes default path to `/`.
- **Validation**: Enforces supported schemes (`http`, `https`). Validates host/domain structure. Rejects unsupported protocols (e.g. `ftp://`, `file://`).
- **Failure Handling**: Produces structured failure envelope (`status: "failure"`) on invalid targets without unhandled exceptions.

### 3.2 HTTP Response & Redirect Inspection
- **Captured Data**: Final destination URL, HTTP status code, full redirect chain (hops with status codes), content type, response size, and HTTPS status.
- **Normal Redirect Invariant (Zero False-Positive Rule)**: Standard single-hop redirects (e.g. `http://` $\rightarrow$ `https://` or `example.com` $\rightarrow$ `www.example.com` returning 200) are considered healthy and **never produce a defect finding**.
- **Excessive Redirects**: If redirect chain length exceeds threshold (default: > 3 hops), emits `DISC-###` (`redirects` subcategory, `medium` severity).
- **Insecure Protocol**: If destination remains unencrypted HTTP without HTTPS upgrade, emits `DISC-###` (`http_accessibility` subcategory, `medium` severity).
- **Access Barriers**: Status 403 Forbidden, 404 Not Found, or 5xx Server Error on target root generates `critical` severity finding (`http_accessibility` subcategory).

### 3.3 Robots.txt Inspection & AI Crawler Permission Matrix
- **RFC 9309 Compliant Parsing**:
  - Groups: Respects multi-line `User-agent:` declarations per directive block.
  - Directives: Parses `Disallow`, `Allow`, and `Sitemap`.
  - Specificity Matching: Evaluates paths by longest-matching prefix. In case of equal-length `Allow` and `Disallow` matches, `Allow` takes precedence.
  - Wildcard Fallback: If no specific user-agent group matches a bot, rules from `User-agent: *` apply.
  - Empty Disallow: Interprets `Disallow:` with no path as "allow all".
- **Targeted AI Crawlers**:
  - `GPTBot` (OpenAI indexer)
  - `ChatGPT-User` (ChatGPT web browsing)
  - `ClaudeBot` (Anthropic web crawler)
  - `anthropic-ai` (Anthropic crawler)
  - `PerplexityBot` (Perplexity search indexer)
  - `CCBot` (Common Crawl)
  - `Google-Extended` (Google Gemini training indexer)
  - `Bytespider` (ByteDance web crawler)
  - `Applebot-Extended` (Apple AI crawler)
  - `Amazonbot` (Amazon AI crawler)
- **Conservative Finding Rules**:
  - Universal root block (`User-agent: *` with `Disallow: /`) generates `critical` finding (`robots` subcategory).
  - Explicit blocks on `/` targeting major AI crawlers generate `high` finding (`robots` subcategory).
  - Permitted bots or routine administrative path disallows (`/admin`, `/api`) produce **no finding**.

### 3.4 Sitemap Discovery & Validation
- **Discovery Sources**:
  1. `Sitemap:` directives advertised in `robots.txt`.
  2. Default probe: `https://<netloc>/sitemap.xml`.
- **Validation**: Confirms HTTP 200 and validates XML syntax using `xml.etree.ElementTree`. Identifies `<urlset>` or `<sitemapindex>` and extracts URL counts.
- **Conservative Finding Rules**:
  - Advertised sitemap in robots.txt returning 4xx or 5xx generates `medium` finding (`sitemap` subcategory).
  - Sitemap returning 200 but containing invalid/malformed XML syntax generates `medium` finding (`sitemap` subcategory).
  - **Absence of default `/sitemap.xml` when not advertised in robots.txt produces NO finding** (preventing unwarranted SEO penalties).

### 3.5 Internal Link Extraction & Representative Page Reachability
- **Link Extraction**: Parses anchor `<a>` tags, normalizes relative URLs to absolute same-origin URLs, filters out fragment links, javascript, mailto, and external domains.
- **Bounded Representative Selection**: Prioritizes high-value informative paths (`about`, `product`, `docs`, `pricing`, `blog`) up to a configurable limit (default: 5 pages total).
- **Broken Page Detection**: Probes selected representative pages. If an internal link consistently returns 404, 410, or 5xx, emits `medium` finding (`crawlability` subcategory).
- **Transient Failures**: A single connection timeout on a secondary page is logged as a limitation and does not fail the audit.

---

## 4. Read Stage Heuristics & Audit Criteria

### 4.1 Visible Text Extraction & Sanitization
- **Node Filtering**: Strips `<script>`, `<style>`, `<noscript>`, `<template>`, and XML/HTML comments.
- **CSS Visibility Filtering**: Excludes markup wrapped in `display:none`, `visibility:hidden`, or having the HTML5 `hidden` attribute.
- **Normalization**: Collapses contiguous whitespace into single spaces and cleans entity escapes.

### 4.2 Deterministic Payload Metrics
- **`html_bytes`**: Raw size of the HTTP response body in bytes.
- **`visible_text_chars`**: Total characters of sanitized visible human-readable text.
- **`text_to_html_ratio`**: Percentage calculated as `(visible_text_chars / html_bytes) * 100`.
- **Structural Tags**: Counts `<h1>`-`<h6>`, `<p>`, `<li>`, `<a>`, and `<script>` elements.
- **Content Density Levels**:
  - `substantial`: $\ge 1200$ visible characters.
  - `moderate`: $450 - 1199$ visible characters.
  - `low`: $150 - 449$ visible characters.
  - `minimal`: $< 150$ visible characters.

### 4.3 CSR & SPA Shell Detection
- **Mount Point Identification**: Matches conventional SPA root elements:
  - IDs: `#root`, `#app`, `#__next`, `#app-root`, `#main-content`
  - Attributes: `[data-reactroot]`
  - Elements: `<app-root>` (Angular)
- **Inner Content Measurement**: Evaluates the character count inside the mount container. An empty or whitespace-only container indicates client-side rendering is required to render UI content.
- **Loading & Noscript Indicators**: Identifies loading skeletons ("loading...", "please wait...", spinner classes) and warnings requiring JavaScript execution ("Please enable JavaScript to run this app").

### 4.4 Multi-Factor Finding Rules (Conservative / Zero False-Positive)
- **Rule 1: JavaScript Alone Is Never Flagged**:
  Modern sites frequently bundle analytics, hydration scripts, and tracking tags. Even 50+ script tags produce **no finding** if the server-rendered HTML contains readable textual content ($\ge 450$ chars or clear headings/copy).
- **Rule 2: Low Ratio Alone Is Never Flagged**:
  Sites with substantial inline SVGs, CSS variables, or styling will naturally have low text-to-code ratios. If the text itself is substantive, **no finding** is generated.
- **Rule 3: Empty SPA Shell Barrier** (`high` severity, `rendering_dependency` subcategory):
  Triggered when:
  1. An empty frontend mount container (`#root`, `#app`, etc.) or loading/noscript indicator is present; AND
  2. The page loads 2 or more `<script>` bundles; AND
  3. The page contains zero headings (`H1`-`H6`) and minimal visible server-rendered text ($< 250$ chars).
- **Rule 4: Heavily Client-Dependent Payload** (`medium` severity, `rendering_dependency` subcategory):
  Triggered when:
  1. Server-rendered text is low ($< 450$ chars) and text-to-HTML ratio is very low ($< 1.5\%$); AND
  2. The page loads 5 or more `<script>` tags; AND
  3. The page lacks structural headings (`<h1>`/`<h2>`) or standard paragraph blocks.

---


---

## 5. Extract Stage Heuristics & Audit Criteria

### 5.1 JSON-LD & Schema.org Extraction
- **Parsing**: Extracts all `<script type="application/ld+json">` blocks. Supports objects, arrays, and `@graph` structures.
- **Type Identification**: Deterministically extracts Schema.org `@type` declarations (e.g. `Organization`, `Product`, `Article`).
- **Malformed Data**: Emits finding if JSON-LD block is malformed and non-empty. Severity is `medium` if no valid blocks exist, `low` if other valid blocks are present.

### 5.2 Meaningful Schema Gaps (Conservative Heuristics)
- **Product Gap**: If a page URL contains `/product/`, `/p/`, or `/item/` and title/content mentions "buy" or "price", but lacks `Product` or `Offer` schema, emits a `medium` finding.
- **Article Gap**: If a page URL contains `/blog/`, `/article/`, or `/news/`, has an `<article>` landmark, and >3 paragraphs, but lacks `Article`/`NewsArticle`/`BlogPosting` schema, emits a `medium` finding.

### 5.3 OpenGraph & Social Metadata
- **Extraction**: Records `og:*` and `twitter:*` properties without penalizing purely missing fields.
- **Conflicting Signals**: Emits a `medium` finding if `og:url` is present but points to a completely different domain than the `canonical` link, confusing crawlers.

### 5.4 Semantic HTML Landmarks
- **Extraction**: Checks for presence of `<main>`, `<article>`, `<header>`, `<footer>`, `<nav>`, `<aside>` and equivalent `role=""` attributes.
- **Primary Content Region**: If the document lacks both `<main>`/`<article>` and `role="main"`, it emits a `low` severity finding since automated readers might struggle to isolate primary content.

### 5.5 False Positive Controls (Zero Hallucination)
- **No Penalties for Cosmetic Diff**: Formatting differences between JSON-LD and visible text do not trigger findings.
- **No Generic Penalties**: Missing optional OpenGraph tags or missing `Product` schema on generic homepages do not trigger findings.


---

## 6. Understand Stage Heuristics & Audit Criteria

### 6.1 Heading Hierarchy Analysis
- **Missing or Skipped Levels**: Extracts the sequence of `h1`-`h6` tags. Checks if multiple heading levels are skipped (e.g. `h1` directly to `h4`) and flags ambiguous structure if there's no clear primary structure.
- **Missing Primary Heading**: Emits a `medium` severity finding if a page lacks an `H1` and `H2`, has no descriptive title, but contains substantive text.
- **Empty / Punctuation-Only Headings**: Flags if the majority of headings on a page contain no visible, meaningful text.
- **Repetitive Headings**: Detects when a single ambiguous heading (e.g., "Details") repeats aggressively as the primary structural element.

### 6.2 Page Subject / Topic Signals
- **Consistency**: Compares `<title>`, the first `<h1>`, and OpenGraph `<meta property="og:title">`. Normalizes text (lowercasing, removing common stop words and punctuation) to detect if signals entirely contradict each other.
- **Insufficient Signals**: If `title`, `h1`, and `og:title` are all missing, flags the page as having an ambiguous primary subject.

### 6.3 Context Sufficiency
- **Content Context**: If a page declares a strong subject (via `h1` or JSON-LD schema) but contains almost zero visible paragraph text, it flags the page for having insufficient explanatory context (`medium` severity).

### 6.4 False Positive Controls (Zero Hallucination)
- **Legitimate Skips**: Does not strictly fail normal structure (like `H1` -> `H2` -> `H2` -> `H3`).
- **Multiple H1s**: Multiple `H1` tags are permitted and not penalized if the page has coherent text.
- **Short Generic Headings**: Common concise headers like "Overview", "Pricing", or "Contact" are explicitly allowed.
- **Harmless Differences**: Case and punctuation variations between the Title and H1 are normalized and never penalized as contradictions.


---

## 7. Identify Stage Heuristics & Audit Criteria

### 7.1 Entity & Brand Consistency
- **Schema vs Page Identity**: Extracts Organization and WebSite schema names and compares them against visible Page Title and H1 tags using a normalized substring match.
- **Product Override**: Explicitly forgives differing H1s if a valid Product or Service schema exists to explain the page's independent identity.
- **Conflict Threshold**: Only produces a finding if multiple independent structural signals (e.g., Title AND H1) contradict the declared Organization schema.

### 7.2 Canonical URL Identity
- **Cross-Domain Canonicals**: Compares the canonical `<link>` domain to the actual page domain and emits a medium severity finding if the canonical redirects search engines to an entirely different origin.
- **Schema URL Alignment**: Validates that URLs declared in Organization or WebSite schemas align with the canonical identity of the site.

### 7.3 sameAs Relationship Quality
- **Malformed sameAs Checks**: Inspects `sameAs` values for clear malformations (e.g., non-URL text, strings containing spaces, missing schemes). Does *not* automatically penalize missing `sameAs` data.

### 7.4 False Positive Controls (Zero Hallucination)
- **Legal Suffix Stripping**: Safely ignores "Inc", "LLC", "Corp" when doing identity substring matching.
- **Case & Punctuation**: Safely ignores case and punctuation variations ("ACME CLOUD" vs "Acme Cloud").
- **Canonical Normalization**: Standardizes trailing slashes, `www.`, and default ports prior to comparison.
- **No Speculative Identity**: Avoids making generic claims about brand ambiguity without explicit deterministic contradictions in the page structure itself.


## 8. Trust Stage Heuristics & Audit Criteria

### 8.1 Commercial Classification & Transparency
- **Commercial Classification**: Requires explicit `Product`, `Offer`, `Service`, `LocalBusiness` schemas, or clear commercial keywords (pricing, checkout, buy, etc.). An `Organization` schema alone does **NOT** trigger commercial intent.
- **Transparency Gap**: Only triggered when a site has strong deterministic evidence of commercial intent, multiple representative pages were inspected, and no explicit privacy/legal/terms links were found. Forgives informational/corporate pages.

### 8.2 Attribution & Content-Type
- **Article Detection**: Detects `Article`, `NewsArticle`, `BlogPosting` schemas. A generic `<article>` layout tag only qualifies if accompanied by explicit publication dates.
- **Attribution Gap**: Only flags missing attribution (author/publisher) when the content is explicitly identified as an article. The evidence string clearly states *why* it was classified as an article.

### 8.3 Freshness & Date Consistency
- **Date Extraction**: Consolidates and deduplicates `datePublished` and `dateModified`.
- **Staleness**: A page being >365 days old is NOT automatically stale (e.g. historical reports/archives are valid). A staleness finding requires the page context (e.g. title) to explicitly claim it is current or future context, conflicting with its actual old dates.
- **Date Contradictions**: Safely emits a single finding if `dateModified` precedes `datePublished`.

### 8.4 Internal Corroboration & Security
- **Factual Conflicts**: Compares metadata (like Organization names) across inspected internal pages. Emits a finding only if material contradictions exist (e.g. Acme vs Globex), explicitly forgiving sub-brands (e.g. Acme Corp vs Acme Labs).
- **Security Observations**: Records HSTS, CSP, and Referrer-Policy headers. Does not emit findings purely for absent security headers.
- **HTTPS Deduplication**: Flags unencrypted HTTP connections without duplicating findings already emitted by the Reach stage.
- **Scope Limit**: Performs **INTERNAL DETERMINISTIC CORROBORATION ONLY**. Does NOT perform external web research.
## 9. Operational Invariants

- **Read-Only**: Passive HTTP GET requests only. Never mutate data, submit forms, or access authenticated areas.
- **Zero Hallucination**: Every finding must have verifiable, concrete observable evidence citing specific HTTP status, URL, or robots.txt line.
- **In-Memory Caching**: HTTP responses are cached per URL to prevent duplicate network round-trips.

