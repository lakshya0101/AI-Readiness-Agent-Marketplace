import unittest
import sys
import os
import json
from io import StringIO

current_dir = os.path.dirname(os.path.abspath(__file__))
audit_dir = os.path.join(current_dir, "..", "skills", "engagement-audit")
sys.path.append(audit_dir)

from scripts.evaluators import EngagementEvaluator
import scripts.audit_engagement as audit_engagement

class TestEngagementAudit(unittest.TestCase):
    # --- DOCUMENTATION TESTS ---
    def test_strong_documentation_hierarchy(self):
        html = """
        <html>
            <head><title>Docs</title></head>
            <body>
                <nav class="sidebar"><a href="/docs/intro">Intro</a></nav>
                <nav class="breadcrumb"><a href="/docs">Docs</a></nav>
                <h1>API Overview</h1>
            </body>
        </html>
        """
        evaluator = EngagementEvaluator("https://example.com/docs/api", html, "deep", "documentation")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "orientation"]), 0)

    def test_genuine_documentation_context_loss(self):
        html = """
        <html>
            <head><title>API</title></head>
            <body>
                <h1>API Overview</h1>
                <p>Use the endpoint.</p>
            </body>
        </html>
        """
        evaluator = EngagementEvaluator("https://example.com/docs/api", html, "deep", "documentation")
        findings = evaluator.evaluate()
        orient_findings = [f for f in findings if f.subcategory == "orientation"]
        self.assertEqual(len(orient_findings), 1)

    def test_doc_missing_breadcrumbs_strong_nav(self):
        html = """
        <html>
            <head><title>Docs</title></head>
            <body>
                <nav class="sidebar"><a href="/docs/intro">Intro</a></nav>
                <h1>API Overview</h1>
            </body>
        </html>
        """
        evaluator = EngagementEvaluator("https://example.com/docs/api", html, "deep", "documentation")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "orientation"]), 0)

    # --- SERVICE TESTS ---
    def test_service_contact_us_link(self):
        html = '<html><body><h1>Our Services</h1><a href="/contact">Contact Us</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/services", html, "landing", "service")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "actionability"]), 0)

    def test_service_request_quote_link(self):
        html = '<html><body><h1>Our Services</h1><a href="/quote">Request a Quote</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/services", html, "landing", "service")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "actionability"]), 0)

    def test_service_lacking_meaningful_action(self):
        html = '<html><body><h1>Our Services</h1><a href="/legal">Terms</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/services", html, "landing", "service")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "actionability"]), 1)

    # --- ARTICLE/NEWS TESTS ---
    def test_article_proper_metadata(self):
        html = '<html><body><h1>News</h1><time>2026-01-01</time><meta name="author" content="Bob"></body></html>'
        evaluator = EngagementEvaluator("https://example.com/news/1", html, "landing", "article/news")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "orientation"]), 0)

    def test_article_missing_metadata(self):
        html = '<html><body><h1>News</h1></body></html>'
        evaluator = EngagementEvaluator("https://example.com/news/1", html, "landing", "article/news")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "orientation"]), 1)

    def test_ordinary_corporate_no_metadata_finding(self):
        html = '<html><body><h1>About Us</h1><p>We are a company.</p></body></html>'
        evaluator = EngagementEvaluator("https://example.com/about", html, "landing", "corporate/about")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "orientation"]), 0)

    # --- CTA TESTS ---
    def test_cta_plain_anchor(self):
        html = '<html><body><h1>Product</h1><a href="/buy">Buy Now</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/product/1", html, "landing", "product")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "actionability"]), 0)

    def test_cta_button(self):
        html = '<html><body><h1>Product</h1><button>Acquire</button></body></html>'
        evaluator = EngagementEvaluator("https://example.com/product/1", html, "landing", "product")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "actionability"]), 0)

    def test_cta_form(self):
        html = '<html><body><h1>Product</h1><form></form></body></html>'
        evaluator = EngagementEvaluator("https://example.com/product/1", html, "landing", "product")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "actionability"]), 0)

    def test_non_cta_links(self):
        html = '<html><body><h1>Product</h1><a href="/info">Read info</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/product/1", html, "landing", "product")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "actionability"]), 1)

    # --- PARSER TESTS ---
    def test_parser_script_style_ignored(self):
        html = """
        <html>
            <head>
                <style>body { color: red; }</style>
                <script>
                    var x = 1;
                    function doThing() { return false; }
                </script>
            </head>
            <body></body>
        </html>
        """
        evaluator = EngagementEvaluator("https://example.com/", html, "landing", "landing")
        findings = evaluator.evaluate()
        landing_findings = [f for f in findings if f.subcategory == "landing"]
        # Because the script/style text is ignored, intro text is empty -> landing finding triggers
        self.assertEqual(len(landing_findings), 1)

    def test_normal_text_after_script_captured(self):
        html = """
        <html>
            <body>
                <script>var x = 1;</script>
                <p>This is a normal paragraph with enough text to be considered a meaningful introductory content piece.</p>
                <title>Clear</title>
            </body>
        </html>
        """
        evaluator = EngagementEvaluator("https://example.com/", html, "landing", "landing")
        findings = evaluator.evaluate()
        landing_findings = [f for f in findings if f.subcategory == "landing"]
        self.assertEqual(len(landing_findings), 0)

    # --- DEEP ENTRY TESTS ---
    def test_strong_deep_page(self):
        html = '<html><body><nav></nav><a href="https://example.com/">Home</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/nested/page", html, "deep", "other")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "deep-entry"]), 0)

    def test_missing_breadcrumbs_strong_context(self):
        html = '<html><body><header></header><a href="/">Logo</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/nested/page", html, "deep", "other")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "deep-entry"]), 0)

    def test_genuine_context_loss_deep(self):
        html = '<html><body><a href="https://other.com">External</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/nested/page", html, "deep", "other")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "deep-entry"]), 1)

    # --- ROBUSTNESS TESTS ---
    def test_empty_html(self):
        evaluator = EngagementEvaluator("https://example.com/", "", "landing", "landing")
        findings = evaluator.evaluate()
        self.assertTrue(len(findings) > 0)

    def test_malformed_html(self):
        html = '<html<body<p>Unclosed stuff'
        evaluator = EngagementEvaluator("https://example.com/", html, "landing", "landing")
        # Ensure it doesn't crash
        findings = evaluator.evaluate()
        self.assertTrue(isinstance(findings, list))

    def test_minimal_html(self):
        evaluator = EngagementEvaluator("https://example.com/", "<html></html>", "landing", "landing")
        findings = evaluator.evaluate()
        self.assertTrue(len(findings) > 0)

    def test_absolute_homepage_link(self):
        html = '<html><body><a href="https://example.com/">Home</a></body></html>'
        evaluator = EngagementEvaluator("https://example.com/docs", html, "deep", "other")
        findings = evaluator.evaluate()
        self.assertEqual(len([f for f in findings if f.subcategory == "deep-entry"]), 0)

if __name__ == "__main__":
    unittest.main()
