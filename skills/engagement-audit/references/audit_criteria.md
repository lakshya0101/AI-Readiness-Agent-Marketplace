# Engagement Audit Criteria

This document defines the strict, evidence-backed criteria used to generate findings.

## Page Type Rules
- **article/news**: Expects metadata (author, date). Missing CTAs are acceptable.
- **documentation**: Focuses on hierarchy (breadcrumbs, nav). Missing CTAs are acceptable.
- **product**: Expects a clear action (buy, demo) and product identity.
- **service**: Expects a contact or request action.
- **pricing**: Expects signup/contact actions.
- **landing**: Expects strong purpose (h1/title) and navigation.
- **corporate/about**: General context.
- **informational/legal**: No CTAs required. Minimal navigation acceptable.

## Dimension Criteria

### 1. Landing Experience
- **Evidence Required**: Complete lack of `<h1>`, empty `<title>`, and zero substantive introductory text.
- **False-Positive Control**: Missing `<h1>` alone is NOT a finding if the title and intro paragraph clearly state the purpose.

### 2. Information Orientation
- **Evidence Required**: Missing `<time>` or author meta tags on `article/news` pages.
- **False-Positive Control**: Irrelevant metadata is not required for standard product/landing pages.

### 3. Deep-Page Context Retention (Deep-Entry Test)
- **Evidence Required**: Complete lack of global navigation (`<nav>`, `<header>`), breadcrumbs, and parent links (e.g. logo linking to home).
- **False-Positive Control**: Missing breadcrumbs is NOT an automatic finding. If strong global nav exists, context is retained.

### 4. Navigation
- **Evidence Required**: Zero `<nav>` elements, zero headers/footers, and fewer than 2 internal links.
- **False-Positive Control**: Do not flag "few links" if structural pathways exist. Do not flag legal/informational pages for poor navigation.

### 5. Meaningful Next Action
- **Evidence Required**: Zero `<button>`, `<form>`, or CTA-styled links on interactive pages.
- **False-Positive Control**: Only flag missing CTAs on product, service, pricing, or similar pages where action is definitively expected. Legal pages receive NO finding.

## Severity Guidance
- **Critical**: Severe trapping (e.g., deep page with zero navigation and brand context).
- **High**: Significant failures (e.g., product page with zero way to buy/contact).
- **Medium**: Friction with workarounds.
- **Low**: Minor structural omissions (e.g., missing author on an article).
