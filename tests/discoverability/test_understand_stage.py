import unittest
from skills.ai_discoverability.scripts.understand_inspector import UnderstandInspector
from skills.ai_discoverability.scripts.extract_inspector import ExtractInspector
from skills.ai_discoverability.scripts.html_reader import PageTextExtractor
from skills.ai_discoverability.scripts.finding_factory import FindingFactory

class TestUnderstandStage(unittest.TestCase):
    def setUp(self):
        self.factory = FindingFactory()
        self.inspector = UnderstandInspector(self.factory)
        self.extract_inspector = ExtractInspector(self.factory)

    def _run_understand(self, html: str, url: str = "https://example.com/test"):
        read_obs = PageTextExtractor.analyze(html, url)
        _, extract_obs = self.extract_inspector.inspect_page(url, html, read_obs)
        return self.inspector.inspect_page(url, html, read_obs, extract_obs)

    # -------------------------------------------------------------
    # FALSE-POSITIVE TESTS
    # -------------------------------------------------------------
    
    def test_normal_hierarchy_no_finding(self):
        # 1. H1 -> H2 -> H3 normal hierarchy
        html = "<html><body><h1>Title</h1><p>" + "a "*300 + "</p><h2>Sub</h2><h3>Sub sub</h3></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_h1_h2_h2_h3_hierarchy(self):
        # 2. H1 -> H2 -> H2 -> H3
        html = "<html><body><h1>Title</h1><p>" + "a "*300 + "</p><h2>S1</h2><h2>S2</h2><h3>S2.1</h3></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_multiple_h1s_with_coherent_content(self):
        # 3. Multiple H1s with coherent content
        html = "<html><head><title>Test Page</title></head><body><h1>Title 1</h1><h1>Title 2</h1><p>Substantive content here.</p></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_short_legitimate_headings(self):
        # 4. Short legitimate headings like "Overview", "Pricing"
        html = "<html><body><h1>Acme</h1><p>" + "a "*300 + "</p><h2>Pricing</h2><h2>Overview</h2></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_concise_landing_page(self):
        # 5. Concise but clear landing page content
        html = "<html><head><title>Acme App</title></head><body><h1>Acme App</h1><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_capitalization_diffs(self):
        # 6. Different capitalization between title/H1
        html = "<html><head><title>ACME cloud Backup</title></head><body><h1>Acme Cloud Backup</h1><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_punctuation_diffs(self):
        # 7. Punctuation differences between title and H1
        html = "<html><head><title>Acme: Cloud Backup!</title></head><body><h1>Acme - Cloud Backup</h1><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_harmless_wording_variation(self):
        # 9. Multiple valid subject signals that use harmless wording variation
        html = """
        <html><head>
        <title>Acme Software Services for Business</title>
        <meta property="og:title" content="Acme Business Software">
        </head><body><h1>Acme Software Services</h1><p>" + "a "*300 + "</p></body></html>
        """
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_page_without_schema_but_clear_subject(self):
        # 10. A page without Article/Product schema where the actual page subject is still clear
        html = "<html><head><title>Some clear subject</title></head><body><h1>Some clear subject</h1><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        # It shouldn't trigger an Understand finding (Extract might trigger schema gap, but we are checking Understand)
        self.assertEqual(len(findings), 0)


    # -------------------------------------------------------------
    # POSITIVE TESTS
    # -------------------------------------------------------------

    def test_no_h1_no_meaningful_subject(self):
        # 1. No H1 + no meaningful primary subject.
        html = "<html><body><div><p>Welcome to our page.</p></div></body></html>"
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Primary Page Subject Is Not Clearly Exposed", titles)

    def test_h1_skipped_to_h4_no_other_structure(self):
        # 2. H1 followed immediately by H4/H5 with weak surrounding structure.
        # Wait, the heuristic says "if len(skipped_levels) > 1 and h_counts['h1'] == 0" for Hierarchy finding.
        # Or no H1 and substantive text. Let's trigger missing primary heading.
        html = "<html><body><h4>Small</h4><h6>Smaller</h6><p>Substantive text " + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Heading Hierarchy Is Structurally Ambiguous", titles)

    def test_conflicting_primary_subject_signals(self):
        # 3. Multiple conflicting primary subject signals.
        html = """
        <html><head>
        <title>Acme Cloud Backup</title>
        <meta property="og:title" content="Best Software">
        </head><body><h1>Enterprise CRM Platform</h1></body></html>
        """
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Primary Page Subject Signals are Strongly Conflicting", titles)

    def test_empty_headings(self):
        # 4. Empty headings
        html = "<html><body><h1>-</h1><h2>*</h2><h2>*</h2><h3>*</h3></body></html>"
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Substantial Number of Empty Headings Detected", titles)

    def test_repetitive_substantive_headings(self):
        # 5. Repetitive substantive headings without clear H1
        html = "<html><body><h2>Product</h2><h2>Product</h2><h2>Product</h2><h2>Product</h2><h2>Product</h2></body></html>"
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Repetitive Heading Structure Creates Ambiguity", titles)

    def test_product_subject_no_explanatory_context(self):
        # 6. Product/service subject with almost no explanatory context.
        html = "<html><head><title>Buy SuperWidget</title></head><body><h1>SuperWidget</h1></body></html>"
        findings, obs = self._run_understand(html, "https://example.com/product/123")
        # To trigger, it needs either schema or h1, and visible text < 150 chars, 0 paragraphs.
        titles = [f["title"] for f in findings]
        self.assertIn("Important Subject Has Insufficient Textual Context", titles)

    def test_strongly_consistent_subject(self):
        # 8. Strongly consistent title/H1/OG subject. (This is a negative test essentially)
        html = """
        <html><head>
        <title>Consistent Name</title>
        <meta property="og:title" content="Consistent Name">
        </head><body><h1>Consistent Name</h1><p>" + "a "*300 + "</p></body></html>
        """
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

if __name__ == '__main__':
    unittest.main()

    def test_adv_different_but_related_title_h1(self):
        html = "<html><head><title>Google Workspace Pricing</title></head><body><h1>Plans & Pricing</h1><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_adv_one_heading_skip(self):
        html = "<html><body><h1>Title</h1><h4>Skip to H4</h4><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        # Should be NO finding for a single skip (len(skipped_levels) = 1)
        self.assertEqual(len(findings), 0)

    def test_adv_multiple_h1s_strong_consistency(self):
        html = "<html><head><title>Consistent Title</title></head><body><h1>Consistent Title</h1><h1>Another H1</h1><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_adv_one_empty_heading_plus_normal(self):
        html = "<html><body><h1>Title</h1><h2> </h2><h2>Valid Sub</h2><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_adv_list_based_content_no_paragraphs(self):
        html = "<html><body><h1>List Content</h1><ul>" + "<li>Valid item</li>"*10 + "</ul></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_adv_table_heavy_no_paragraphs(self):
        html = "<html><body><h1>Table Content</h1><table>" + "<tr><td>Data</td></tr>"*10 + "</table></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_adv_short_but_info_rich(self):
        html = "<html><body><h1>Strong Subject</h1><ul><li>Fact 1</li><li>Fact 2</li></ul></body></html>"
        findings, _ = self._run_understand(html)
        self.assertEqual(len(findings), 0)

    def test_tp_multiple_strongly_contradictory(self):
        html = """
        <html><head>
        <title>Acme Cloud Backup</title>
        <meta property="og:title" content="Acme Cloud Backup">
        </head><body><h1>Enterprise CRM Platform</h1><p>""" + "a "*300 + """</p></body></html>
        """
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Primary Page Subject Signals are Strongly Conflicting", titles)

    def test_tp_severe_heading_confusion(self):
        html = "<html><body><h4>Start</h4><h6>Skip</h6><p>" + "a "*300 + "</p></body></html>"
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Heading Hierarchy Is Structurally Ambiguous", titles)

    def test_tp_large_number_empty_headings(self):
        html = "<html><body><h1>Title</h1><h2>-</h2><h2>-</h2><h2>-</h2><h2>-</h2></body></html>"
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Substantial Number of Empty Headings Detected", titles)

    def test_tp_repetitive_headings_dominating(self):
        html = "<html><body><h2>Product</h2><h2>Product</h2><h2>Product</h2><h2>Product</h2><h2>Product</h2><h2>Product</h2></body></html>"
        findings, _ = self._run_understand(html)
        titles = [f["title"] for f in findings]
        self.assertIn("Repetitive Heading Structure Creates Ambiguity", titles)

    def test_tp_subject_no_context(self):
        html = "<html><body><h1>Empty Product</h1></body></html>"
        findings, _ = self._run_understand(html, "https://example.com/product")
        titles = [f["title"] for f in findings]
        self.assertIn("Important Subject Has Insufficient Textual Context", titles)

