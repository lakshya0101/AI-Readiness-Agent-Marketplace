"""Comprehensive unit, integration, and false-positive tests for the READ audit stage."""

import importlib.util
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure REPO_ROOT is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skills.ai_discoverability.scripts import (
    audit_discoverability,
    DiscoverabilityAuditor,
    FindingFactory,
    HttpResponse,
    PageTextExtractor,
    ReadObservation,
    ReadInspector,
)

DISC_ID_REGEX = re.compile(r"^DISC-[0-9]{3,4}$")


def _mock_http_response(
    url: str,
    status_code: int = 200,
    body: bytes = b"",
    headers: dict = None,
    redirect_chain: list = None,
    error: str = None,
) -> HttpResponse:
    return HttpResponse(
        requested_url=url,
        final_url=url,
        status_code=status_code,
        redirect_chain=redirect_chain or [],
        headers=headers or {"content-type": "text/html; charset=utf-8"},
        body=body,
        error=error,
    )


class TestReadAuditStage(unittest.TestCase):

    # -------------------------------------------------------------
    # 1. HTML Text & Structural Extraction
    # -------------------------------------------------------------
    def test_visible_text_extraction(self):
        """Verify visible text is extracted, normalized, and comments/whitespace are cleaned."""
        html = """
        <html>
            <head><title> Acme AI Platform </title></head>
            <body>
                <!-- Header comment -->
                <header><h1>Welcome to Acme</h1></header>
                <main>
                    <p>Acme delivers high performance autonomous systems for enterprises.</p>
                </main>
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        self.assertEqual(obs.title, "Acme AI Platform")
        self.assertEqual(obs.h1_count, 1)
        self.assertEqual(obs.heading_count, 1)
        self.assertEqual(obs.paragraph_count, 1)
        self.assertIn("Welcome to Acme", obs.headings[0][1])
        self.assertIn("Acme delivers high performance", obs.paragraphs[0])
        self.assertNotIn("Header comment", obs.headings[0][1])

    def test_script_style_template_exclusion(self):
        """Verify content inside <script>, <style>, <noscript>, <template>, and hidden elements is excluded."""
        html = """
        <html>
            <head>
                <style>body { color: red; } .hidden { display: none; }</style>
                <script>const secret = "window.analytics = true";</script>
            </head>
            <body>
                <noscript>JavaScript is required to view this app.</noscript>
                <template><p>Template content that should not be visible</p></template>
                <div style="display: none">Hidden secret banner</div>
                <div hidden>Attribute hidden content</div>
                <p>This is the only visible body paragraph on the page.</p>
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        self.assertNotIn("window.analytics", obs.to_dict()["headings_summary"])
        self.assertNotIn("color: red", obs.to_dict()["headings_summary"])
        self.assertEqual(obs.paragraph_count, 1)
        self.assertEqual(obs.paragraphs[0], "This is the only visible body paragraph on the page.")
        self.assertTrue(obs.has_noscript_warning)

    def test_html_and_text_size_and_ratio_calculation(self):
        """Verify html_bytes, visible_text_chars, and text_to_html_ratio are computed deterministically."""
        html = "<html><body><h1>Hello World</h1><p>Testing the ratio calculation accurately.</p></body></html>"
        obs = PageTextExtractor.analyze(html, "https://example.com/")

        expected_bytes = len(html.encode("utf-8"))
        self.assertEqual(obs.html_bytes, expected_bytes)
        self.assertGreater(obs.visible_text_chars, 30)
        expected_ratio = round(obs.visible_text_chars / expected_bytes, 4)
        self.assertEqual(obs.text_to_html_ratio, expected_ratio)

    def test_spa_root_container_detection(self):
        """Verify SPA root containers (#root, #app, #__next) are detected and measured."""
        html_empty_root = """
        <html><body>
            <div id="root"></div>
            <script src="/bundle.js"></script>
        </body></html>
        """
        obs_empty = PageTextExtractor.analyze(html_empty_root, "https://example.com/")
        self.assertEqual(obs_empty.spa_container_id, "root")
        self.assertEqual(obs_empty.spa_container_text_chars, 0)

        html_populated_root = """
        <html><body>
            <div id="__next">
                <h1>Next.js SSR Title</h1>
                <p>Rendered server-side content with substantial text inside the container.</p>
            </div>
            <script src="/_next/static/bundle.js"></script>
        </body></html>
        """
        obs_pop = PageTextExtractor.analyze(html_populated_root, "https://example.com/")
        self.assertEqual(obs_pop.spa_container_id, "__next")
        self.assertGreater(obs_pop.spa_container_text_chars, 50)

    def test_loading_and_noscript_indicators(self):
        """Verify loading placeholders and noscript warnings are identified."""
        html = "<html><body><div id='app'><p>Loading...</p></div></body></html>"
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        self.assertTrue(obs.has_loading_indicator)
        self.assertEqual(obs.loading_indicator_text, "Loading...")

    def test_meaningful_text_classification(self):
        """Verify content signal classification levels (substantial, moderate, low, minimal)."""
        html_minimal = "<html><body></body></html>"
        self.assertEqual(PageTextExtractor.analyze(html_minimal, "https://ex.com").initial_content_signal, "minimal")

        html_low = f"<html><body><p>{'a' * 180}</p></body></html>"
        self.assertEqual(PageTextExtractor.analyze(html_low, "https://ex.com").initial_content_signal, "low")

        html_moderate = f"<html><body><h1>Title</h1><p>{'b' * 400}</p></body></html>"
        self.assertEqual(PageTextExtractor.analyze(html_moderate, "https://ex.com").initial_content_signal, "moderate")

        html_substantial = f"<html><body><h1>Title</h1><h2>Sub</h2><p>{'c' * 1100}</p></body></html>"
        self.assertEqual(PageTextExtractor.analyze(html_substantial, "https://ex.com").initial_content_signal, "substantial")

    def test_malformed_html_and_empty_response(self):
        """Verify robustness on malformed or empty HTML."""
        obs_empty = PageTextExtractor.analyze("", "https://example.com/")
        self.assertEqual(obs_empty.html_bytes, 0)
        self.assertEqual(obs_empty.visible_text_chars, 0)

        malformed = "<html><body><div><p>Unclosed paragraph<h1>Mixed up tags</div></body>"
        obs_malformed = PageTextExtractor.analyze(malformed, "https://example.com/")
        self.assertGreater(obs_malformed.visible_text_chars, 10)

    # -------------------------------------------------------------
    # 2. False-Positive Protection
    # -------------------------------------------------------------
    def test_fp_normal_ssr_page_produces_no_finding(self):
        """FALSE-POSITIVE TEST: Standard SSR page with healthy copy must NOT produce a rendering finding."""
        html = """
        <!DOCTYPE html>
        <html>
            <head><title>Enterprise Cloud Analytics</title></head>
            <body>
                <header><h1>Real-time Cloud Observability Platform</h1></header>
                <main>
                    <p>Our autonomous monitoring agents continuously inspect telemetry data across hybrid cloud environments.</p>
                    <h2>Key Features</h2>
                    <p>Distributed tracing, automated anomaly detection, and instant incident response workflows.</p>
                    <h2>Customer Testimonials</h2>
                    <p>Over 500 enterprise customers trust our platform for mission-critical infrastructure reliability.</p>
                </main>
                <footer><p>&copy; 2026 Enterprise Cloud Inc.</p></footer>
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        factory = FindingFactory()
        findings = ReadInspector.evaluate_page(obs, factory)
        self.assertEqual(len(findings), 0, "Normal SSR page must NOT trigger any Read stage findings")

    def test_fp_js_heavy_page_with_readable_content_no_finding(self):
        """FALSE-POSITIVE TEST: Page with 25 script tags but rich server-rendered HTML must NOT produce a finding."""
        scripts_block = "\n".join([f'<script src="/static/js/chunk_{i}.js"></script>' for i in range(25)])
        html = f"""
        <html>
            <head><title>Rich Media Portal</title>{scripts_block}</head>
            <body>
                <h1>Daily Industry Insights</h1>
                <p>Comprehensive market analysis covering artificial intelligence, cloud architectures, and machine learning models.</p>
                <h2>Quarterly Benchmark Report</h2>
                <p>Detailed performance benchmarks comparing agent orchestration frameworks across latency, accuracy, and cost efficiency metrics.</p>
                <p>Additional comprehensive documentation explaining evaluation methodologies, scoring rubrics, and reproducible test configurations.</p>
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        factory = FindingFactory()
        findings = ReadInspector.evaluate_page(obs, factory)
        self.assertEqual(len(findings), 0, "Script-heavy page with readable content must NOT trigger a finding")

    def test_fp_react_next_ssr_with_populated_root_no_finding(self):
        """FALSE-POSITIVE TEST: Next.js or React page where #__next or #root has server-rendered copy must NOT be flagged."""
        html = """
        <html>
            <head><title>SaaS Product</title></head>
            <body>
                <div id="__next">
                    <h1>Enterprise Agent Platform</h1>
                    <p>Accelerate your developer workflows with autonomous coding assistants integrated into your existing CI/CD pipelines.</p>
                    <h2>Seamless Integration</h2>
                    <p>Connects natively with GitHub, GitLab, and enterprise repositories with zero configuration overhead.</p>
                </div>
                <script id="__NEXT_DATA__" type="application/json">{"props":{}}</script>
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        factory = FindingFactory()
        findings = ReadInspector.evaluate_page(obs, factory)
        self.assertEqual(len(findings), 0, "Pre-rendered React/Next container must NOT trigger an SPA shell finding")

    def test_fp_low_text_to_code_ratio_with_substantive_text_no_finding(self):
        """FALSE-POSITIVE TEST: Very large HTML with inline SVGs/styling but 800 chars of good text must NOT be flagged."""
        # 40,000 bytes of boilerplate plus 800 chars of text
        boilerplate = "<!-- SVG icon boilerplate -->\n<svg viewBox='0 0 100 100'><path d='M10 10'/></svg>\n" * 200
        content = "<h1>Platform Overview</h1>" + "<p>Substantive text describing core features and architectural principles in detail.</p>" * 10
        html = f"<html><body>{boilerplate}{content}</body></html>"

        obs = PageTextExtractor.analyze(html, "https://example.com/")
        self.assertLess(obs.text_to_html_ratio, 0.05)  # low ratio
        self.assertGreater(obs.visible_text_chars, 600)  # but substantial text

        factory = FindingFactory()
        findings = ReadInspector.evaluate_page(obs, factory)
        self.assertEqual(len(findings), 0, "Low ratio alone with substantial text must NOT produce a finding")

    # -------------------------------------------------------------
    # 3. Positive Detection Cases (True Issues)
    # -------------------------------------------------------------
    def test_positive_empty_spa_shell_triggers_high_severity(self):
        """POSITIVE TEST: Empty #root container with bundle scripts triggers high severity rendering dependency finding."""
        html = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>Single Page Application</title>
                <script defer src="/static/js/main.1a2b3c.js"></script>
                <script defer src="/static/js/vendor.4d5e6f.js"></script>
                <script defer src="/static/js/runtime.7g8h9i.js"></script>
            </head>
            <body>
                <noscript>You need to enable JavaScript to run this app.</noscript>
                <div id="root"></div>
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        self.assertEqual(obs.spa_container_id, "root")
        self.assertEqual(obs.spa_container_text_chars, 0)
        self.assertTrue(obs.has_noscript_warning)

        factory = FindingFactory()
        findings = ReadInspector.evaluate_page(obs, factory)
        self.assertEqual(len(findings), 1)

        f = findings[0]
        self.assertEqual(f["category"], "ai_discoverability")
        self.assertEqual(f["subcategory"], "rendering_dependency")
        self.assertEqual(f["severity"], "high")
        self.assertEqual(f["methodology"], "Read")
        self.assertTrue(DISC_ID_REGEX.match(f["id"]))
        self.assertIn("#root", f["evidence"])
        self.assertIn("0 text characters", f["evidence"])
        self.assertIn("Server-Side Rendering", f["suggested_action"]["summary"])

    def test_positive_loading_placeholder_shell_triggers_high_severity(self):
        """POSITIVE TEST: SPA with only a loading placeholder and no headings/paragraphs triggers high severity finding."""
        html = """
        <html>
            <head>
                <script src="/app.js"></script>
                <script src="/chunk1.js"></script>
                <script src="/chunk2.js"></script>
            </head>
            <body>
                <div id="app">
                    <div class="spinner">Loading... Please wait</div>
                </div>
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        factory = FindingFactory()
        findings = ReadInspector.evaluate_page(obs, factory)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertIn("loading placeholder", findings[0]["evidence"].lower())

    def test_positive_low_ssr_text_with_high_script_ratio_triggers_medium(self):
        """POSITIVE TEST: Large HTML with ~300 chars of text, 8 scripts, and no headings triggers medium severity."""
        scripts = "\n".join([f'<script src="/bundle_{i}.js"></script>' for i in range(8)])
        content_text = "Welcome to the corporate portal. Our services provide access to various online resources, tools, and developer platforms. Please authenticate using your enterprise identity credentials or browse public category listings for additional documentation and reference material."
        html = f"""
        <html>
            <head>{scripts}</head>
            <body>
                <div class="header">Navigation Banner</div>
                <div class="content">{content_text}</div>
                {'<!-- padding to simulate large bundle -->' * 600}
            </body>
        </html>
        """
        obs = PageTextExtractor.analyze(html, "https://example.com/")
        factory = FindingFactory()
        findings = ReadInspector.evaluate_page(obs, factory)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "medium")
        self.assertEqual(findings[0]["subcategory"], "server_rendered_content")


    # -------------------------------------------------------------
    # 4. End-to-End Integration & Multi-Page Read Analysis
    # -------------------------------------------------------------
    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_e2e_read_stage_on_spa_target(self, mock_fetch):
        """Verify audit_discoverability generates Read findings for an empty SPA shell."""
        spa_html = b"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>SPA Dashboard</title>
                <script src="/main.js"></script>
                <script src="/vendor.js"></script>
                <script src="/chunk.js"></script>
            </head>
            <body>
                <div id="root"></div>
            </body>
        </html>
        """
        def side_effect(url):
            if "robots.txt" in url:
                return _mock_http_response(url, 200, b"User-agent: *\nAllow: /\n")
            if "sitemap.xml" in url:
                return _mock_http_response(url, 404, b"Not Found")
            return _mock_http_response(url, 200, spa_html)

        mock_fetch.side_effect = side_effect
        res = audit_discoverability("https://spa-example.com/")

        self.assertEqual(res["status"], "success")
        read_findings = [f for f in res["findings"] if f["methodology"] == "Read"]
        self.assertEqual(len(read_findings), 1)
        self.assertEqual(read_findings[0]["subcategory"], "rendering_dependency")
        self.assertEqual(read_findings[0]["severity"], "high")

        # Verify limitation notes non-browser inspection
        self.assertTrue(any("browser-rendered DOM comparison" in lim for lim in res["limitations"]))

    @patch("skills.ai_discoverability.scripts.audit_discoverability.HttpClient.fetch")
    def test_e2e_read_stage_on_healthy_ssr_target(self, mock_fetch):
        """Verify audit_discoverability generates zero Read findings for a healthy SSR site."""
        ssr_html = b"""
        <!DOCTYPE html>
        <html>
            <head><title>Enterprise Software Solutions</title></head>
            <body>
                <header><h1>Autonomous Cloud Management</h1></header>
                <main>
                    <p>Enterprise grade intelligent automation powering cloud operations across global data centers.</p>
                    <h2>Key Architecture Highlights</h2>
                    <p>Multi-cloud orchestration with zero downtime deployments and automated disaster recovery capabilities.</p>
                    <p>Extensive developer API documentation with complete code samples in Python, Go, and TypeScript.</p>
                </main>
                <footer><a href="/about">About Us</a></footer>
            </body>
        </html>
        """
        def side_effect(url):
            if "robots.txt" in url:
                return _mock_http_response(url, 200, b"User-agent: *\nAllow: /\n")
            if "sitemap.xml" in url:
                return _mock_http_response(url, 404, b"Not Found")
            return _mock_http_response(url, 200, ssr_html)

        mock_fetch.side_effect = side_effect
        res = audit_discoverability("https://ssr-example.com/")

        self.assertEqual(res["status"], "success")
        read_findings = [f for f in res["findings"] if f["methodology"] == "Read"]
        self.assertEqual(len(read_findings), 0, "Healthy SSR site must have zero Read findings")


if __name__ == "__main__":
    unittest.main()
