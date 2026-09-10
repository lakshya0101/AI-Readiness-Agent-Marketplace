import unittest
from skills.ai_discoverability.scripts.identify_inspector import IdentifyInspector
from skills.ai_discoverability.scripts.extract_inspector import ExtractInspector
from skills.ai_discoverability.scripts.html_reader import PageTextExtractor
from skills.ai_discoverability.scripts.finding_factory import FindingFactory

class TestIdentifyStage(unittest.TestCase):
    def setUp(self):
        self.factory = FindingFactory()
        self.inspector = IdentifyInspector(self.factory)
        self.extract_inspector = ExtractInspector(self.factory)

    def _run_identify(self, html: str, url: str = "https://example.com/test"):
        read_obs = PageTextExtractor.analyze(html, url)
        _, extract_obs = self.extract_inspector.inspect_page(url, html, read_obs)
        return self.inspector.inspect_page(url, read_obs, extract_obs)

    # -------------------------------------------------------------
    # FALSE-POSITIVE TESTS
    # -------------------------------------------------------------
    
    def test_fp_1_acme_inc_vs_acme(self):
        html = """<html>
        <head><title>Acme Inc.</title></head>
        <body><h1>Acme</h1>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme Inc."}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_2_acme_cloud_case_diff(self):
        html = """<html>
        <head><title>ACME CLOUD</title></head>
        <body><h1>Acme Cloud</h1>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme Cloud"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_3_pricing_acme_vs_acme(self):
        html = """<html>
        <head><title>Pricing | Acme</title></head>
        <body><h1>Acme</h1>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_4_product_brand_acme_under_org_acme_corp(self):
        html = """<html>
        <head><title>Acme SuperWidget</title></head>
        <body><h1>Acme SuperWidget</h1>
        <script type="application/ld+json">[
            {"@type": "Organization", "name": "Acme Corporation"},
            {"@type": "Product", "brand": {"@type": "Brand", "name": "Acme"}}
        ]</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_5_legitimate_sub_brand(self):
        html = """<html>
        <head><title>Acme AWS Services</title></head>
        <body><h1>Acme AWS Services</h1>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_6_http_vs_https_canonical_normalization(self):
        html = '<html><head><link rel="canonical" href="http://example.com/test"></head><body><h1>A</h1></body></html>'
        findings, _ = self._run_identify(html, "https://example.com/test")
        self.assertEqual(len(findings), 0)

    def test_fp_7_trailing_slash_differences(self):
        html = '<html><head><link rel="canonical" href="https://example.com/test/"></head><body><h1>A</h1></body></html>'
        findings, _ = self._run_identify(html, "https://example.com/test")
        self.assertEqual(len(findings), 0)

    def test_fp_8_duplicate_url_normalization(self):
        html = '<html><head><link rel="canonical" href="https://www.example.com/test"></head><body><h1>A</h1></body></html>'
        findings, _ = self._run_identify(html, "https://example.com/test")
        self.assertEqual(len(findings), 0)

    def test_fp_9_missing_sameas(self):
        html = """<html>
        <body><h1>Acme</h1>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_10_missing_organization_schema(self):
        html = "<html><head><title>Acme</title></head><body><h1>Acme</h1></body></html>"
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_11_missing_canonical(self):
        html = "<html><head><title>Acme</title></head><body><h1>Acme</h1></body></html>"
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_12_multiple_legitimate_product_entities(self):
        html = """<html>
        <body><h1>MultiProduct</h1>
        <script type="application/ld+json">[
            {"@type": "Product", "name": "Prod A"},
            {"@type": "Product", "name": "Prod B"}
        ]</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_13_org_and_product_different_names_valid(self):
        html = """<html><head><title>SuperWidget</title></head>
        <body><h1>SuperWidget</h1>
        <script type="application/ld+json">[
            {"@type": "Organization", "name": "Acme Corp"},
            {"@type": "Product", "name": "SuperWidget"}
        ]</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    def test_fp_14_multiple_schema_distinct_entities(self):
        html = """<html>
        <script type="application/ld+json">[
            {"@type": "Organization", "name": "Acme Corp"},
            {"@type": "WebSite", "name": "Acme Corp Blog"}
        ]</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        self.assertEqual(len(findings), 0)

    # -------------------------------------------------------------
    # POSITIVE TESTS
    # -------------------------------------------------------------

    def test_tp_1_org_contradicts_h1_and_title(self):
        html = """<html><head><title>Globex CRM</title></head>
        <body><h1>Globex CRM</h1>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Identity Signals Are Inconsistent", titles)

    def test_tp_2_org_contradicts_website_and_h1(self):
        html = """<html><head><title>Acme</title></head>
        <body><h1>Globex</h1>
        <script type="application/ld+json">[
            {"@type": "Organization", "name": "Acme"},
            {"@type": "WebSite", "name": "Globex"}
        ]</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Structured Entity Name Conflicts With Page Identity", titles)

    def test_tp_3_canonical_different_origin(self):
        html = '<html><head><link rel="canonical" href="https://different.com/test"></head><body><h1>A</h1></body></html>'
        findings, _ = self._run_identify(html, "https://example.com/test")
        titles = [f["title"] for f in findings]
        self.assertIn("Canonical URL Conflicts With Page Identity", titles)

    def test_tp_4_jsonld_url_contradicts_canonical(self):
        html = """<html><head><link rel="canonical" href="https://example.com/test"></head>
        <body><h1>A</h1>
        <script type="application/ld+json">{"@type": "Organization", "url": "https://different.com"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html, "https://example.com/test")
        titles = [f["title"] for f in findings]
        self.assertIn("Structured Entity Name Conflicts With Page Identity", titles)

    def test_tp_5_malformed_sameas_url(self):
        html = """<html>
        <body><h1>A</h1>
        <script type="application/ld+json">{"@type": "Organization", "sameAs": "Not a URL"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Malformed sameAs Relationship", titles)

    def test_tp_6_invalid_non_url_value_sameas(self):
        html = """<html>
        <body><h1>A</h1>
        <script type="application/ld+json">{"@type": "Organization", "sameAs": "Acme Corporation"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Malformed sameAs Relationship", titles)

    def test_tp_7_org_publisher_conflicts(self):
        html = """<html><head><title>Globex</title></head>
        <body><h1>Globex</h1>
        <script type="application/ld+json">{"@type": "Organization", "name": "Acme"}</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Identity Signals Are Inconsistent", titles)

    def test_tp_8_conflicting_product_identity(self):
        # Even with product schema, if the names strongly conflict in website vs org it fires
        html = """<html><head><title>Test</title></head>
        <body><h1>Globex</h1>
        <script type="application/ld+json">[
            {"@type": "Organization", "name": "Acme"},
            {"@type": "WebSite", "name": "Globex"}
        ]</script>
        </body></html>"""
        findings, _ = self._run_identify(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Structured Entity Name Conflicts With Page Identity", titles)

if __name__ == '__main__':
    unittest.main()
