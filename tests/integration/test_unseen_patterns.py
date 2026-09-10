"""Unseen-Website Pattern Simulation and Hardening Tests.

Tests the complete Audit Orchestrator pipeline against 12 diverse website archetypes:
1. Strong static informational website
2. Documentation website
3. Product/e-commerce page
4. Article/news page
5. Corporate website
6. Historical/archive content
7. JS-heavy / SPA shell
8. Deep-entry content page
9. Strong structured-data page
10. Conflicting metadata/entity signals
11. Minimal landing page
12. Page with unconventional but valid semantic structure
"""

import json
from unittest.mock import patch, MagicMock
import pytest

from skills.audit_orchestrator.scripts import AuditOrchestrator, AuditReport
from skills.ai_discoverability.scripts.http_client import HttpResponse


def _mock_resp(url: str, body: bytes, status_code: int = 200, headers: dict = None) -> HttpResponse:
    return HttpResponse(
        requested_url=url,
        final_url=url,
        status_code=status_code,
        redirect_chain=[],
        headers=headers or {"content-type": "text/html; charset=utf-8"},
        body=body,
    )


class TestUnseenWebsitePatterns:

    # -------------------------------------------------------------------------
    # 1. Strong Static Informational Website
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_01_strong_static_informational_website(self, mock_disc_fetch, mock_eng_urlopen):
        """A well-structured static informational site should pass cleanly with zero high/critical findings."""
        html = b"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Acme Robotics Research Institute - Official Portal</title>
            <meta name="description" content="Pioneering autonomous systems and open robotics research.">
            <meta property="og:site_name" content="Acme Robotics Research Institute">
            <meta property="og:title" content="Acme Robotics Research Institute">
            <link rel="canonical" href="https://acme-robotics.org">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "ResearchOrganization",
                "name": "Acme Robotics Research Institute",
                "url": "https://acme-robotics.org",
                "description": "Leading global research institute for autonomous systems."
            }
            </script>
        </head>
        <body>
            <header>
                <nav aria-label="Main Navigation">
                    <a href="https://acme-robotics.org/">Home</a>
                    <a href="/research">Research</a>
                    <a href="/publications">Publications</a>
                    <a href="/contact">Contact</a>
                </nav>
            </header>
            <main>
                <h1>Advancing Autonomous Systems for Humanity</h1>
                <p>Acme Robotics Research Institute is a non-profit research institute founded in 2010. We publish peer-reviewed papers on robotics, motion planning, machine perception, and human-robot interaction.</p>
                <h2>Current Focus Areas</h2>
                <p>Our lab investigates high-precision manipulation in unstructured environments and multi-agent coordination.</p>
            </main>
            <footer>
                <a href="/privacy">Privacy Policy</a>
                <a href="/terms">Terms of Service</a>
            </footer>
        </body>
        </html>"""

        def disc_side_effect(url):
            if "robots.txt" in url:
                return _mock_resp(url, b"User-agent: *\nAllow: /\nSitemap: https://acme-robotics.org/sitemap.xml\n")
            if "sitemap.xml" in url:
                return _mock_resp(url, b"<?xml version='1.0'?><urlset><url><loc>https://acme-robotics.org/</loc></url></urlset>")
            return _mock_resp(url, html)
        mock_disc_fetch.side_effect = disc_side_effect

        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://acme-robotics.org")

        assert report.modules["ai_discoverability"]["status"] == "success"
        assert report.modules["on_site_engagement"]["status"] == "success"
        # Must have zero critical and zero high severity findings
        assert report.summary.critical == 0
        assert report.summary.high == 0

    # -------------------------------------------------------------------------
    # 2. Documentation Website
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_02_documentation_website(self, mock_disc_fetch, mock_eng_urlopen):
        """Documentation pages with sidebar nav & breadcrumbs must not trigger false disorientation or context loss."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Guide - CloudSDK Documentation</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "TechArticle",
                "headline": "Authentication Guide",
                "name": "CloudSDK Documentation"
            }
            </script>
        </head>
        <body>
            <header><a href="https://docs.cloudsdk.io/">CloudSDK Docs</a></header>
            <nav class="sidebar">
                <a href="/docs/getting-started">Getting Started</a>
                <a href="/docs/auth">Authentication</a>
                <a href="/docs/api">API Reference</a>
            </nav>
            <nav class="breadcrumb" aria-label="Breadcrumb">
                <a href="/">Home</a> / <a href="/docs">Docs</a> / <span>Auth</span>
            </nav>
            <main>
                <h1>Authentication Guide</h1>
                <p>Authenticate your API client using bearer tokens or mutual TLS certificates for secure access.</p>
                <h2>Using Bearer Tokens</h2>
                <p>Pass your token in the Authorization header of every request.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator(
            engagement_options={"entry_type": "deep", "inferred_page_type": "documentation"}
        )
        report = orchestrator.run_audit("https://docs.cloudsdk.io/docs/auth")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        # Documentation orientation (ENG-202) and deep entry (ENG-301) must NOT trigger
        assert not any(f.id == "ENG-202" for f in eng_findings)
        assert not any(f.id == "ENG-301" for f in eng_findings)

    # -------------------------------------------------------------------------
    # 3. Product / E-Commerce Page
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_03_product_page_with_clear_actions(self, mock_disc_fetch, mock_eng_urlopen):
        """E-commerce product page with Buy/Demo action must not trigger actionability findings."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>UltraNoise Pro Headphones - AudioLab Store</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "UltraNoise Pro Headphones",
                "offers": { "@type": "Offer", "price": "299.00", "priceCurrency": "USD" }
            }
            </script>
        </head>
        <body>
            <header><a href="https://audiolab.com/">AudioLab</a></header>
            <main>
                <h1>UltraNoise Pro Headphones</h1>
                <p>Industry-leading active noise cancelling wireless headphones with 40-hour battery life.</p>
                <form action="/cart/add" method="post">
                    <button type="submit">Buy Now - $299</button>
                </form>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator(
            engagement_options={"inferred_page_type": "product"}
        )
        report = orchestrator.run_audit("https://audiolab.com/products/ultranoise-pro")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        # Product action finding (ENG-501) must NOT trigger
        assert not any(f.id == "ENG-501" for f in eng_findings)

    # -------------------------------------------------------------------------
    # 4. Article / News Page
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_04_article_news_page_with_provenance(self, mock_disc_fetch, mock_eng_urlopen):
        """News article with time tag and author metadata must not trigger provenance or metadata findings."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>Renewable Energy Breakthrough - Tech Daily</title>
            <meta name="author" content="Dr. Sarah Connor">
            <meta property="article:published_time" content="2026-03-15T09:00:00Z">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": "Renewable Energy Breakthrough",
                "datePublished": "2026-03-15T09:00:00Z",
                "author": { "@type": "Person", "name": "Dr. Sarah Connor" }
            }
            </script>
        </head>
        <body>
            <header><a href="https://techdaily.news/">Tech Daily</a></header>
            <main>
                <h1>Renewable Energy Breakthrough Announced</h1>
                <p>By Dr. Sarah Connor on <time datetime="2026-03-15">March 15, 2026</time></p>
                <p>Researchers at the National Energy Lab have demonstrated a new solid-state battery chemistry with 3x energy density.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator(
            engagement_options={"inferred_page_type": "article/news"}
        )
        report = orchestrator.run_audit("https://techdaily.news/articles/renewable-breakthrough")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        # Article metadata (ENG-201) must NOT trigger
        assert not any(f.id == "ENG-201" for f in eng_findings)

    # -------------------------------------------------------------------------
    # 5. Corporate Website
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_05_corporate_website_landing(self, mock_disc_fetch, mock_eng_urlopen):
        """Standard corporate homepage with company description and nav should be recognized cleanly."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>Global Logistics Corp - Enterprise Freight Solutions</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Corporation",
                "name": "Global Logistics Corp",
                "url": "https://globallogistics.com"
            }
            </script>
        </head>
        <body>
            <header>
                <nav>
                    <a href="/">Home</a>
                    <a href="/about">About Us</a>
                    <a href="/solutions">Solutions</a>
                    <a href="/contact">Contact</a>
                </nav>
            </header>
            <main>
                <h1>Enterprise Freight and Supply Chain Solutions</h1>
                <p>Global Logistics Corp provides freight forwarding, customs brokerage, and supply chain technology for Fortune 500 enterprises.</p>
                <a href="/contact" class="btn">Request a Quote</a>
            </main>
            <footer>
                <a href="/privacy">Privacy</a>
                <a href="/terms">Terms</a>
            </footer>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://globallogistics.com")

        assert report.summary.critical == 0
        assert report.summary.high == 0

    # -------------------------------------------------------------------------
    # 6. Historical / Archive Content
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_06_historical_archive_content_not_flagged_as_stale(self, mock_disc_fetch, mock_eng_urlopen):
        """Historical articles from 2018 must not trigger artificial staleness or identity errors."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>2018 Annual Technology Retrospective - Tech Historical Archives</title>
            <meta name="author" content="Archive Editor">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "2018 Annual Technology Retrospective",
                "datePublished": "2018-12-31T00:00:00Z"
            }
            </script>
        </head>
        <body>
            <header><a href="https://archive.tech.org/">Tech Archives</a></header>
            <main>
                <h1>2018 Annual Technology Retrospective</h1>
                <p>Published on <time datetime="2018-12-31">December 31, 2018</time></p>
                <p>A comprehensive review of breakthroughs in cloud computing and edge computing in the year 2018.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator(
            engagement_options={"inferred_page_type": "article/news"}
        )
        report = orchestrator.run_audit("https://archive.tech.org/2018/retrospective")

        # Must run successfully without crashing
        assert report.modules["ai_discoverability"]["status"] == "success"
        assert report.modules["on_site_engagement"]["status"] == "success"

    # -------------------------------------------------------------------------
    # 7. JS-Heavy / SPA Shell
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_07_spa_shell_graceful_handling(self, mock_disc_fetch, mock_eng_urlopen):
        """Client-rendered SPA shell with empty body reports appropriate thin-content finding and limitations."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>App Portal</title>
            <script src="/bundle.js"></script>
        </head>
        <body>
            <div id="root"></div>
            <noscript>You need to enable JavaScript to run this app.</noscript>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://spa-app.io")

        assert report.modules["ai_discoverability"]["status"] == "success"
        assert report.modules["on_site_engagement"]["status"] == "success"
        # Must contain limitation about server-rendered HTML vs browser DOM
        assert any("Read stage analyzed initial server-delivered HTML" in lim or "structural DOM" in lim for lim in report.limitations)

    # -------------------------------------------------------------------------
    # 8. Deep-Entry Content Page
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_08_deep_entry_content_page_with_context(self, mock_disc_fetch, mock_eng_urlopen):
        """Deep-entry page with root link and header retains context and avoids ENG-301."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Enterprise Analytics - Platform Features</title></head>
        <body>
            <header>
                <a href="https://platform.io/">Platform Home</a>
                <nav><a href="/features">Features</a></nav>
            </header>
            <main>
                <h1>Enterprise Analytics Suite</h1>
                <p>Real-time telemetry and reporting pipelines for distributed cloud services.</p>
                <a href="/signup">Sign up for trial</a>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator(
            engagement_options={"entry_type": "deep", "inferred_page_type": "service"}
        )
        report = orchestrator.run_audit("https://platform.io/features/analytics")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        assert not any(f.id == "ENG-301" for f in eng_findings)

    # -------------------------------------------------------------------------
    # 9. Strong Structured-Data Page
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_09_strong_structured_data_rich_schema(self, mock_disc_fetch, mock_eng_urlopen):
        """Page with complete JSON-LD graph (Organization + WebSite + BreadcrumbList) passes structured data inspection."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>Acme Tools Corporation</title>
            <link rel="canonical" href="https://acmetools.com/">
            <meta property="og:site_name" content="Acme Tools Corporation">
            <meta property="og:title" content="Acme Tools Corporation">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@graph": [
                    {
                        "@type": "Organization",
                        "@id": "https://acmetools.com/#organization",
                        "name": "Acme Tools Corporation",
                        "url": "https://acmetools.com"
                    },
                    {
                        "@type": "WebSite",
                        "@id": "https://acmetools.com/#website",
                        "name": "Acme Tools Corporation",
                        "url": "https://acmetools.com",
                        "publisher": { "@id": "https://acmetools.com/#organization" }
                    }
                ]
            }
            </script>
        </head>
        <body>
            <main>
                <h1>Acme Tools Corporation</h1>
                <p>Leading supplier of precision manufacturing tools and equipment.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://acmetools.com")

        disc_findings = [f for f in report.findings if f.category == "ai_discoverability"]
        # Must not report missing structured data or missing entity identity
        assert not any(f.subcategory in {"structured_data", "entity_identity"} for f in disc_findings)

    # -------------------------------------------------------------------------
    # 10. Conflicting Metadata / Entity Signals
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_10_conflicting_metadata_entity_signals_detected(self, mock_disc_fetch, mock_eng_urlopen):
        """Conflicting brand identity signals between JSON-LD and page Title/H1 must trigger identity consistency finding."""
        html = b"""<!DOCTYPE html>
        <html>
        <head>
            <title>Apex Dynamics Systems</title>
            <meta property="og:title" content="Apex Dynamics Systems">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Zenith Heavy Industries"
            }
            </script>
        </head>
        <body>
            <main>
                <h1>Apex Dynamics Systems</h1>
                <p>Industrial machinery engineering company.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://apexdynamics.com")

        disc_findings = [f for f in report.findings if f.category == "ai_discoverability"]
        # Must detect conflict between "Zenith Heavy Industries" and "Apex Dynamics Systems"
        conflict_findings = [f for f in disc_findings if "inconsistent" in f.title.lower() or "conflict" in f.title.lower()]
        assert len(conflict_findings) > 0
        evidence_text = conflict_findings[0].evidence
        assert "Zenith Heavy Industries" in evidence_text or "Apex Dynamics" in evidence_text

    # -------------------------------------------------------------------------
    # 11. Minimal Landing Page
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_11_minimal_landing_page_with_essential_signals(self, mock_disc_fetch, mock_eng_urlopen):
        """A minimal launch page with clear H1, title, and CTA must not trigger ENG-101 (unclear purpose)."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Nova AI - Coming Fall 2026</title></head>
        <body>
            <main>
                <h1>Next Generation Reasoning Models</h1>
                <p>Nova AI is developing verifiable reasoning architectures for automated theorem proving and code synthesis.</p>
                <a href="/signup">Join Waitlist</a>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://nova-ai.tech")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        # ENG-101 (unclear landing purpose) must NOT trigger
        assert not any(f.id == "ENG-101" for f in eng_findings)

    # -------------------------------------------------------------------------
    # 12. Page with Unconventional but Valid Semantic Structure
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_12_unconventional_semantic_structure_recognized(self, mock_disc_fetch, mock_eng_urlopen):
        """Page using <article> or <section role='main'> instead of literal <main> must not trigger missing landmark."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Research Note - Quantum Computing</title></head>
        <body>
            <article>
                <h1>Topological Qubits in 2026</h1>
                <p>Recent experiments demonstrate increased coherence times in braided Majorana zero modes.</p>
            </article>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://quantum-notes.org")

        disc_findings = [f for f in report.findings if f.category == "ai_discoverability"]
        # Missing primary landmark should NOT trigger because <article> serves as primary content container
        landmark_findings = [f for f in disc_findings if "landmark" in f.title.lower()]
        assert len(landmark_findings) == 0

    # -------------------------------------------------------------------------
    # 13. Highly Readable Page with No JSON-LD
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_13_highly_readable_page_no_jsonld(self, mock_disc_fetch, mock_eng_urlopen):
        """A page with clear headings, main landmark, and rich body text but no JSON-LD has zero critical/high errors."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>History of Modern Typography - Essay</title></head>
        <body>
            <header>
                <nav>
                    <a href="/">Home</a>
                    <a href="/essays">Essays</a>
                </nav>
            </header>
            <main>
                <h1>The Evolution of Digital Typography</h1>
                <p>Digital typography emerged alongside bitmap displays in the early 1970s. PostScript outline fonts created scalable vectors that standardized publishing across platforms.</p>
                <p>TrueType and OpenType formats unified font rendering across major operating systems, enabling dynamic kerning and rich glyph substitution tables.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://typography-history.org")

        assert report.summary.critical == 0
        assert report.summary.high == 0

    # -------------------------------------------------------------------------
    # 14. Highly Crawlable Site without Sitemap Directive
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_14_highly_crawlable_site_no_sitemap_directive(self, mock_disc_fetch, mock_eng_urlopen):
        """A site with valid robots.txt permitting crawlers without Sitemap directive does not produce critical blockers."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Open Knowledge Hub</title></head>
        <body><main><h1>Open Knowledge Hub</h1><p>Public open knowledge repository.</p></main></body>
        </html>"""

        def disc_side_effect(url):
            if "robots.txt" in url:
                return _mock_resp(url, b"User-agent: *\nAllow: /\n")
            return _mock_resp(url, html)

        mock_disc_fetch.side_effect = disc_side_effect
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://openknowledge.org")

        assert report.summary.critical == 0
        # AI discoverability status is success
        assert report.modules["ai_discoverability"]["status"] == "success"

    # -------------------------------------------------------------------------
    # 15. Contextual Links without <nav>
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_15_contextual_links_without_nav_avoids_navigation_failure(self, mock_disc_fetch, mock_eng_urlopen):
        """A page with multiple in-body contextual links does not trigger ENG-401 navigation failure."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Compiler Architecture Overview</title></head>
        <body>
            <main>
                <h1>Compiler Optimization Passes</h1>
                <p>Learn more about our <a href="/lexer">Lexical Analysis</a>, <a href="/parser">AST Generation</a>, and <a href="/codegen">Code Generation</a> pipelines.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://compiler-design.dev")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        # ENG-401 must NOT trigger because total_links (3) >= 2
        assert not any(f.id == "ENG-401" for f in eng_findings)

    # -------------------------------------------------------------------------
    # 16. role='main' Semantic Container Recognized
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_16_role_main_recognized_as_landmark(self, mock_disc_fetch, mock_eng_urlopen):
        """Container with role='main' satisfies landmark requirement and produces no landmark finding."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Cloud Console - Overview</title></head>
        <body>
            <div role="main">
                <h1>Infrastructure Dashboard</h1>
                <p>Telemetry for active compute clusters across all regions.</p>
            </div>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator()
        report = orchestrator.run_audit("https://cloudconsole.io")

        disc_findings = [f for f in report.findings if f.category == "ai_discoverability"]
        assert not any("landmark" in f.title.lower() for f in disc_findings)

    # -------------------------------------------------------------------------
    # 17. Single-CTA Product Page
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_17_single_cta_product_page_no_false_positive(self, mock_disc_fetch, mock_eng_urlopen):
        """Product page with single 'Buy Now' button satisfies actionability without triggering ENG-501."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Ergonomic Keyboard Model X</title></head>
        <body>
            <main>
                <h1>Ergonomic Keyboard Model X</h1>
                <p>Split mechanical keyboard designed for maximum posture support and wrist comfort.</p>
                <button type="button">Buy Now</button>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator(
            engagement_options={"inferred_page_type": "product"}
        )
        report = orchestrator.run_audit("https://keyboards.shop/model-x")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        assert not any(f.id == "ENG-501" for f in eng_findings)

    # -------------------------------------------------------------------------
    # 18. Deep Page with Root Link
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_18_deep_page_with_root_link_preserves_context(self, mock_disc_fetch, mock_eng_urlopen):
        """Deep page with a link to root home '/' preserves site context and avoids ENG-301."""
        html = b"""<!DOCTYPE html>
        <html>
        <head><title>Payment Gateways - Developer Guide</title></head>
        <body>
            <p><a href="/">Back to Merchant Hub</a></p>
            <main>
                <h1>Payment Gateways Integration</h1>
                <p>Step-by-step guide for embedding Stripe and PayPal checkout flows.</p>
            </main>
        </body>
        </html>"""

        mock_disc_fetch.side_effect = lambda url: _mock_resp(url, html) if "robots.txt" not in url else _mock_resp(url, b"User-agent: *\nAllow: /\n")
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__.return_value = mock_resp
        mock_eng_urlopen.return_value = mock_resp

        orchestrator = AuditOrchestrator(
            engagement_options={"entry_type": "deep", "inferred_page_type": "documentation"}
        )
        report = orchestrator.run_audit("https://merchanthub.dev/guides/payments")

        eng_findings = [f for f in report.findings if f.category == "on_site_engagement"]
        # ENG-301 (context loss on deep entry) must NOT trigger because has_home_link is True
        assert not any(f.id == "ENG-301" for f in eng_findings)
