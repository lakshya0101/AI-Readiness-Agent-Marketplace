import unittest
from datetime import date, timedelta
from skills.ai_discoverability.scripts.trust_inspector import TrustInspector
from skills.ai_discoverability.scripts.html_reader import PageTextExtractor
from skills.ai_discoverability.scripts.extract_inspector import ExtractInspector
from skills.ai_discoverability.scripts.identify_inspector import IdentifyInspector
from skills.ai_discoverability.scripts.finding_factory import FindingFactory

class TestTrustStage(unittest.TestCase):
    def setUp(self):
        self.factory = FindingFactory()
        self.inspector = TrustInspector(self.factory)
        # Mock today for predictable testing (e.g. 2026-01-01)
        self.inspector.today = date(2026, 1, 1)
        self.extract_inspector = ExtractInspector(self.factory)
        self.identify_inspector = IdentifyInspector(self.factory)

    def _run_trust(self, html: str, url: str = "https://example.com/test", headers=None, is_https=True, existing_findings=None):
        if headers is None: headers = {}
        if existing_findings is None: existing_findings = []
        read_obs = PageTextExtractor.analyze(html, url)
        _, extract_obs = self.extract_inspector.inspect_page(url, html, read_obs)
        _, identify_obs = self.identify_inspector.inspect_page(url, read_obs, extract_obs)
        return self.inspector.inspect_page(url, html, headers, is_https, read_obs, extract_obs, identify_obs, existing_findings)

    # -------------------------------------------------------------
    # FALSE-POSITIVE TESTS (10 Additions)
    # -------------------------------------------------------------
    def test_fp_1_org_only_corporate_no_privacy(self):
        # 1. Organization-only corporate site without privacy links -> No finding
        html = '<html><script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script><body></body></html>'
        _, obs1 = self._run_trust(html, "https://ex.com/1")
        _, obs2 = self._run_trust(html, "https://ex.com/2")
        findings = self.inspector.evaluate_cross_page([obs1, obs2], [])
        self.assertEqual(len(findings), 0)

    def test_fp_2_nonprofit_no_privacy(self):
        # 2. Nonprofit Organization site without privacy links -> No finding
        html = '<html><script type="application/ld+json">{"@type": "NGO", "name": "Acme"}</script><body></body></html>'
        _, obs1 = self._run_trust(html, "https://ex.com/1")
        _, obs2 = self._run_trust(html, "https://ex.com/2")
        findings = self.inspector.evaluate_cross_page([obs1, obs2], [])
        self.assertEqual(len(findings), 0)

    def test_fp_3_historical_annual_report(self):
        # 3. Historical annual report older than 365 days -> No staleness
        html = '<html><head><title>2023 Annual Report</title><meta property="article:published_time" content="2024-01-01"></head><body><article></article></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertNotIn("Important Content Shows a Strong Staleness Signal", titles)

    def test_fp_4_historical_news_article(self):
        # 4. Historical news article -> No staleness
        html = '<html><head><title>News Event</title><meta property="article:published_time" content="2022-01-01"></head><body><article></article></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertNotIn("Important Content Shows a Strong Staleness Signal", titles)

    def test_fp_5_archive_page_old_date(self):
        # 5. Archive page with old date -> No staleness
        html = '<html><head><title>Archive 2021</title><meta property="article:published_time" content="2021-01-01"></head><body><article></article></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertNotIn("Important Content Shows a Strong Staleness Signal", titles)

    def test_fp_6_generic_article_layout_no_meta(self):
        # 6. Generic page containing <article> layout but no date/schema -> No attribution finding
        html = '<html><body><article><h1>Welcome to our home page</h1></article></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertNotIn("Important Content Lacks Attribution", titles)

    def test_fp_7_commercial_privacy_on_one_page(self):
        # 7. Commercial site, privacy exists on ONE page -> No transparency gap
        html1 = '<html><script type="application/ld+json">{"@type": "Product"}</script><body></body></html>'
        html2 = '<html><script type="application/ld+json">{"@type": "Product"}</script><body><a href="/privacy">Privacy</a></body></html>'
        _, obs1 = self._run_trust(html1, "https://ex.com/1")
        _, obs2 = self._run_trust(html2, "https://ex.com/2")
        findings = self.inspector.evaluate_cross_page([obs1, obs2], [])
        self.assertEqual(len(findings), 0)

    def test_fp_8_two_legitimate_sub_brands(self):
        # 8. Legitimate sub-brand organization names across pages (Acme Corp vs Acme Labs) -> No conflict
        html1 = '<html><script type="application/ld+json">{"@type": "Organization", "name": "Acme Corp"}</script><body></body></html>'
        html2 = '<html><script type="application/ld+json">{"@type": "Organization", "name": "Acme Labs"}</script><body></body></html>'
        _, id1 = self.identify_inspector.inspect_page("https://ex.com/1", PageTextExtractor.analyze(html1, ""), self.extract_inspector.inspect_page("https://ex.com/1", html1, PageTextExtractor.analyze(html1, ""))[1])
        _, id2 = self.identify_inspector.inspect_page("https://ex.com/2", PageTextExtractor.analyze(html2, ""), self.extract_inspector.inspect_page("https://ex.com/2", html2, PageTextExtractor.analyze(html2, ""))[1])
        _, obs1 = self._run_trust(html1, "https://ex.com/1")
        _, obs2 = self._run_trust(html2, "https://ex.com/2")
        findings = self.inspector.evaluate_cross_page([obs1, obs2], [id1, id2])
        self.assertEqual(len(findings), 0)

    def test_fp_9_https_missing_security_headers(self):
        # 9. Security headers absent on HTTPS -> No finding
        html = '<html><body></body></html>'
        findings, _ = self._run_trust(html, is_https=True, headers={})
        self.assertEqual(len(findings), 0)

    def test_fp_10_multiple_identical_date_contradictions(self):
        # 10. Multiple identical date contradictions -> Only one finding emitted
        html = '<html><head><meta property="article:published_time" content="2025-01-01"><meta property="article:modified_time" content="2024-01-01"></head><body></body></html>'
        findings, _ = self._run_trust(html)
        date_findings = [f for f in findings if f["title"] == "Important Content Has Inconsistent Publication Metadata"]
        self.assertEqual(len(date_findings), 1)

    # -------------------------------------------------------------
    # TRUE-POSITIVE TESTS (6 Additions)
    # -------------------------------------------------------------
    def test_tp_1_commercial_no_transparency(self):
        # 1. Commercial Product/Offer site with no transparency links across multiple pages
        html = '<html><script type="application/ld+json">{"@type": "Product"}</script><body></body></html>'
        _, obs1 = self._run_trust(html, "https://ex.com/1")
        _, obs2 = self._run_trust(html, "https://ex.com/2")
        findings = self.inspector.evaluate_cross_page([obs1, obs2], [])
        titles = [f["title"] for f in findings]
        self.assertIn("Meaningful Transparency Signal Gap", titles)

    def test_tp_2_article_no_attribution(self):
        # 2. Article with strong Article schema + no author/publisher
        html = '<html><script type="application/ld+json">{"@type": "Article"}</script><body></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Important Content Lacks Attribution", titles)

    def test_tp_3_current_looking_stale_content(self):
        # 3. Current-looking content with strong stale signal (Title implies >= 2026, date is 2024)
        html = '<html><head><title>2026 Pricing</title><meta property="article:published_time" content="2024-01-01"></head><body><article></article></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Important Content Shows a Strong Staleness Signal", titles)

    def test_tp_4_impossible_date_modified(self):
        # 4. Clearly impossible dateModified < datePublished
        html = '<html><head><meta property="article:published_time" content="2025-01-01"><meta property="article:modified_time" content="2024-01-01"></head><body></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Important Content Has Inconsistent Publication Metadata", titles)

    def test_tp_5_explicitly_conflicting_org_identities(self):
        # 5. Same organization identity explicitly conflicting (no shared substring) across pages
        html1 = '<html><script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script><body></body></html>'
        html2 = '<html><script type="application/ld+json">{"@type": "Organization", "name": "Globex"}</script><body></body></html>'
        _, id1 = self.identify_inspector.inspect_page("https://ex.com/1", PageTextExtractor.analyze(html1, ""), self.extract_inspector.inspect_page("https://ex.com/1", html1, PageTextExtractor.analyze(html1, ""))[1])
        _, id2 = self.identify_inspector.inspect_page("https://ex.com/2", PageTextExtractor.analyze(html2, ""), self.extract_inspector.inspect_page("https://ex.com/2", html2, PageTextExtractor.analyze(html2, ""))[1])
        _, obs1 = self._run_trust(html1, "https://ex.com/1")
        _, obs2 = self._run_trust(html2, "https://ex.com/2")
        findings = self.inspector.evaluate_cross_page([obs1, obs2], [id1, id2])
        titles = [f["title"] for f in findings]
        self.assertIn("Conflicting Factual Values Across Inspected Pages", titles)

    def test_tp_6_http_site_no_duplicate(self):
        # 6. HTTP site without an existing Reach HTTPS finding
        html = "<html><body></body></html>"
        findings, _ = self._run_trust(html, is_https=False, existing_findings=[])
        titles = [f["title"] for f in findings]
        self.assertIn("Page Served Over HTTP", titles)
        # Verify deduplication
        findings2, _ = self._run_trust(html, is_https=False, existing_findings=[{"title": "Website Does Not Enforce HTTPS Protocol"}])
        titles2 = [f["title"] for f in findings2]
        self.assertNotIn("Page Served Over HTTP", titles2)


    def test_fp_11_homepage_no_author(self):
        html = "<html><body><h1>Acme Home</h1></body></html>"
        findings, obs = self._run_trust(html)
        self.assertEqual(len(findings), 0)

    def test_fp_12_product_page_no_author(self):
        html = '<html><body><h1>Super Widget</h1><script type="application/ld+json">{"@type": "Product", "name": "Super Widget"}</script></body></html>'
        findings, obs = self._run_trust(html)
        self.assertEqual(len(findings), 0)

    def test_fp_13_valid_date_combo(self):
        html = '<html><head><meta property="article:published_time" content="2024-01-01"><meta property="article:modified_time" content="2024-02-01"></head><body></body></html>'
        findings, obs = self._run_trust(html)
        self.assertEqual(len(findings), 0)

    def test_fp_14_same_date_different_formats(self):
        html = '<html><head><script type="application/ld+json">{"@type": "Article", "author": "Jane", "datePublished": "2024-01-01T00:00:00Z", "dateModified": "2024-01-01"}</script></head><body></body></html>'
        findings, obs = self._run_trust(html)
        self.assertEqual(len(findings), 0)

    def test_fp_15_person_author_org_publisher(self):
        html = '<html><body><article><h1>News</h1></article><script type="application/ld+json">{"@type": "Article", "author": {"@type": "Person", "name": "Jane Doe"}, "publisher": {"@type": "Organization", "name": "News Corp"}}</script></body></html>'
        findings, obs = self._run_trust(html)
        self.assertEqual(len(findings), 0)

    def test_tp_7_article_conflicting_metadata(self):
        html = '<html><head><meta property="article:published_time" content="2025-01-01"><meta property="article:modified_time" content="2024-01-01"></head><body></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Important Content Has Inconsistent Publication Metadata", titles)

    def test_tp_8_malformed_attribution_structure(self):
        html = '<html><body><article><h1>Piece</h1></article><script type="application/ld+json">{"@type": "Article", "author": true}</script></body></html>'
        findings, _ = self._run_trust(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Important Content Lacks Attribution", titles)

if __name__ == '__main__':
    unittest.main()
