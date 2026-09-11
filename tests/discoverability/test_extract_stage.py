import unittest
from skills.ai_discoverability.scripts.extract_inspector import ExtractHTMLParser, ExtractInspector
from skills.ai_discoverability.scripts.html_reader import PageTextExtractor
from skills.ai_discoverability.scripts.finding_factory import FindingFactory

class TestExtractStage(unittest.TestCase):
    def setUp(self):
        self.factory = FindingFactory()
        self.inspector = ExtractInspector(self.factory)

    def _run_extract(self, html: str, url: str = "https://example.com/test"):
        read_obs = PageTextExtractor.analyze(html, url)
        return self.inspector.inspect_page(url, html, read_obs)

    def test_valid_organization_jsonld(self):
        # 1. Valid Organization JSON-LD
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Acme Corp",
            "url": "https://acme.example.com"
        }
        </script>
        </head><body><main>Content</main></body></html>
        """
        findings, obs = self._run_extract(html)
        self.assertEqual(len(findings), 0, "Valid org jsonld should not produce findings")
        self.assertIn("Organization", obs.types_found)

    def test_valid_website_jsonld(self):
        # 2. Valid WebSite JSON-LD
        html = """
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"WebSite","name":"Test Site"}
        </script>
        <main>Content</main>
        """
        findings, obs = self._run_extract(html)
        self.assertEqual(len(findings), 0)
        self.assertIn("WebSite", obs.types_found)

    def test_multiple_valid_jsonld_blocks(self):
        # 3. Multiple valid JSON-LD blocks
        html = """
        <script type="application/ld+json">{"@type":"Organization","name":"Acme"}</script>
        <script type="application/ld+json">{"@type":"WebSite","name":"Acme Site"}</script>
        <main>Content</main>
        """
        findings, obs = self._run_extract(html)
        self.assertEqual(len(findings), 0)
        self.assertIn("Organization", obs.types_found)
        self.assertIn("WebSite", obs.types_found)
        self.assertEqual(len(obs.jsonld_blocks), 2)

    def test_valid_graph_structure(self):
        # 4. Valid @graph structure
        html = """
        <script type="application/ld+json">
        {
            "@graph": [
                {"@type": "Organization", "name": "Acme"},
                {"@type": "WebSite", "name": "Site"}
            ]
        }
        </script>
        <main>Content</main>
        """
        findings, obs = self._run_extract(html)
        self.assertEqual(len(findings), 0)
        self.assertIn("Organization", obs.types_found)
        self.assertIn("WebSite", obs.types_found)

    def test_not_a_product_page_no_finding(self):
        # 5. A page without Product schema when it is clearly not a product page
        html = "<main><h1>Welcome to Acme Corp</h1><p>We are a business.</p></main>"
        findings, obs = self._run_extract(html, "https://example.com/about")
        product_findings = [f for f in findings if "Product" in f["title"]]
        self.assertEqual(len(product_findings), 0)

    def test_not_an_article_page_no_finding(self):
        # 6. A page without Article schema when it is clearly not an article
        html = "<main><h1>Contact Us</h1><p>Reach out.</p></main>"
        findings, obs = self._run_extract(html, "https://example.com/contact")
        article_findings = [f for f in findings if "Article" in f["title"]]
        self.assertEqual(len(article_findings), 0)

    def test_missing_optional_opengraph(self):
        # 7. Missing optional OpenGraph image on an otherwise valid page
        html = """
        <head>
            <meta property="og:title" content="Hello">
            <meta property="og:description" content="Desc">
        </head>
        <body><main>Content</main></body>
        """
        findings, obs = self._run_extract(html)
        self.assertEqual(len(findings), 0)

    def test_role_main_landmark(self):
        # 8. A page using role="main" instead of <main>
        html = """<body><div role="main"><h1>Content</h1></div></body>"""
        findings, obs = self._run_extract(html)
        landmark_findings = [f for f in findings if f["subcategory"] == "semantic_structure"]
        self.assertEqual(len(landmark_findings), 0)

    def test_semantic_article_landmark(self):
        # 9. A page using semantic <article> correctly
        html = """<body><article><h1>Article</h1></article></body>"""
        findings, obs = self._run_extract(html)
        landmark_findings = [f for f in findings if f["subcategory"] == "semantic_structure"]
        self.assertEqual(len(landmark_findings), 0)

    def test_jsonld_cosmetic_formatting(self):
        # 10. JSON-LD whose formatting differs from visible text only cosmetically
        html = """
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "SuperWidget \u2122",
            "offers": {"@type": "Offer", "price": "19.99"}
        }
        </script>
        <main><h1>SuperWidget TM</h1><p>Price: $19.99</p></main>
        """
        findings, obs = self._run_extract(html)
        # Should be NO finding for cosmetic contradiction
        contradiction_findings = [f for f in findings if "Contradict" in f["title"]]
        self.assertEqual(len(contradiction_findings), 0)

    def test_multiple_legitimate_entities(self):
        # 11. Multiple schemas representing legitimate distinct entities
        html = """
        <script type="application/ld+json">{"@type": "Product", "name": "P1"}</script>
        <script type="application/ld+json">{"@type": "Product", "name": "P2"}</script>
        <main>Products</main>
        """
        findings, obs = self._run_extract(html)
        self.assertEqual(len(findings), 0)
        self.assertIn("Product", obs.types_found)

    def test_malformed_jsonld(self):
        # 12. Malformed JSON-LD
        html = """
        <script type="application/ld+json">
        { "@type": "Organization", "name": "Acme", } 
        </script>
        <main>Content</main>
        """
        findings, obs = self._run_extract(html)
        jsonld_findings = [f for f in findings if f["subcategory"] == "json_ld"]
        self.assertEqual(len(jsonld_findings), 1)
        self.assertEqual(jsonld_findings[0]["severity"], "medium")

    def test_empty_jsonld(self):
        # 13. Empty JSON-LD block
        html = """
        <script type="application/ld+json">   </script>
        <main>Content</main>
        """
        findings, obs = self._run_extract(html)
        # Empty should not cause findings
        self.assertEqual(len(findings), 0)

    def test_visible_product_page_with_no_schema(self):
        # 14. Visible product page with no Product schema
        html = """
        <head><title>Buy SuperWidget - Best Price</title></head>
        <body><main><h1>Buy SuperWidget</h1><p>Price: $19.99</p></main></body>
        """
        findings, obs = self._run_extract(html, "https://example.com/product/super-widget")
        product_findings = [f for f in findings if "Missing Product" in f["title"]]
        self.assertEqual(len(product_findings), 1)
        self.assertEqual(product_findings[0]["severity"], "medium")

    def test_meaningful_opengraph(self):
        # 15. Meaningful OpenGraph metadata
        html = """
        <head>
            <meta property="og:title" content="Test">
            <meta property="og:url" content="https://example.com/test">
        </head>
        <body><main>Content</main></body>
        """
        findings, obs = self._run_extract(html, "https://example.com/test")
        og_findings = [f for f in findings if f["subcategory"] == "opengraph"]
        self.assertEqual(len(og_findings), 0)

    def test_conflicting_opengraph(self):
        # 16. Conflicting OpenGraph url vs canonical
        html = """
        <head>
            <link rel="canonical" href="https://example.com/test">
            <meta property="og:url" content="https://wrongdomain.com/test">
        </head>
        <body><main>Content</main></body>
        """
        findings, obs = self._run_extract(html, "https://example.com/test")
        og_findings = [f for f in findings if f["subcategory"] == "opengraph"]
        self.assertEqual(len(og_findings), 1)
        self.assertIn("Conflicting", og_findings[0]["title"])

    def test_missing_semantic_landmark(self):
        # 17. Missing Semantic Landmarks
        html = """
        <body><div><h1>Flat Page</h1><p>No main or article or role=main.</p></div></body>
        """
        findings, obs = self._run_extract(html)
        landmark_findings = [f for f in findings if f["subcategory"] == "semantic_structure"]
        self.assertEqual(len(landmark_findings), 1)

    # -------------------------------------------------------------
    # REGRESSION TESTS: ReadObservation -> Extract Stage Contract
    # -------------------------------------------------------------

    def test_regression_product_page_with_product_jsonld(self):
        """Regression 1: Product page with valid Product JSON-LD produces no missing schema findings."""
        html = """
        <html><head>
        <title>Premium Headphones - SoundPro</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "SoundPro Wireless Headphones",
            "offers": {
                "@type": "Offer",
                "price": "199.99",
                "priceCurrency": "USD"
            }
        }
        </script>
        </head>
        <body>
        <main>
            <h1>SoundPro Wireless Headphones</h1>
            <p>High-fidelity audio with active noise cancellation.</p>
            <p>Price: $199.99</p>
        </main>
        </body></html>
        """
        findings, obs = self._run_extract(html, "https://example.com/product/soundpro-headphones")
        product_findings = [f for f in findings if "Missing Product" in f["title"]]
        self.assertEqual(len(product_findings), 0)
        self.assertIn("Product", obs.types_found)

    def test_regression_product_content_without_buy_in_title(self):
        """Regression 2: Product page where title lacks 'buy'/'price' but content has '$' evaluates without AttributeError."""
        html = """
        <html><head>
        <title>SoundPro Wireless - Audio Equipment</title>
        </head>
        <body>
        <main>
            <h1>SoundPro Wireless</h1>
            <p>Studio-quality listening experience.</p>
            <p>Special discounted rate: $149.00 available today.</p>
        </main>
        </body></html>
        """
        findings, obs = self._run_extract(html, "https://example.com/product/soundpro-wireless")
        product_findings = [f for f in findings if "Missing Product" in f["title"]]
        self.assertEqual(len(product_findings), 1)
        self.assertEqual(product_findings[0]["severity"], "medium")

    def test_regression_product_price_in_heading(self):
        """Regression 3: Product page where price '$' is inside a heading evaluates cleanly."""
        html = """
        <html><head>
        <title>SoundPro Deluxe</title>
        </head>
        <body>
        <main>
            <h1>SoundPro Deluxe</h1>
            <h2>Starting at $299</h2>
            <p>Premium wireless noise canceling headphones.</p>
        </main>
        </body></html>
        """
        findings, obs = self._run_extract(html, "https://example.com/item/soundpro-deluxe")
        product_findings = [f for f in findings if "Missing Product" in f["title"]]
        self.assertEqual(len(product_findings), 1)

    def test_regression_spa_blog_article_structure_react_dev(self):
        """Regression 4: Blog/article URL with multiple paragraphs evaluates paragraph_count without structural_tags AttributeError."""
        html = """
        <html><head>
        <title>React 19 Release Notes - React Blog</title>
        </head>
        <body>
        <article>
            <h1>React 19 is Here</h1>
            <p>React 19 brings powerful new capabilities to component architecture.</p>
            <p>Actions allow asynchronous transitions natively.</p>
            <p>Server components offer seamless data fetching.</p>
            <p>Asset loading is now deeply integrated into the render lifecycle.</p>
        </article>
        </body></html>
        """
        findings, obs = self._run_extract(html, "https://react.dev/blog/2024/12/05/react-19")
        article_findings = [f for f in findings if "Missing Article" in f["title"]]
        self.assertEqual(len(article_findings), 1)
        self.assertEqual(article_findings[0]["severity"], "medium")
        self.assertIn("react.dev", article_findings[0]["evidence"])

    def test_regression_read_observation_field_compatibility(self):
        """Regression 5: ExtractInspector consumes canonical ReadObservation instance without accessing non-existent attributes."""
        from skills.ai_discoverability.scripts.html_reader import ReadObservation
        canonical_obs = ReadObservation(
            url="https://example.com/blog/sample-post",
            html_bytes=2048,
            visible_text_chars=500,
            text_to_html_ratio=0.244,
            title="Sample Blog Post",
            heading_count=2,
            h1_count=1,
            headings=[("h1", "Sample Blog Post"), ("h2", "Section One")],
            paragraph_count=4,
            paragraphs=["P1 text", "P2 text", "P3 text", "P4 with $50 mention"],
            script_count=2,
        )
        # Verify canonical instance does not have structural_tags or visible_text
        self.assertFalse(hasattr(canonical_obs, "structural_tags"))
        self.assertFalse(hasattr(canonical_obs, "visible_text"))

        html = "<article><h1>Sample Blog Post</h1><h2>Section One</h2><p>P1 text</p><p>P2 text</p><p>P3 text</p><p>P4 with $50 mention</p></article>"
        findings, obs = self.inspector.inspect_page("https://example.com/blog/sample-post", html, canonical_obs)
        self.assertIsInstance(findings, list)
        self.assertIsInstance(obs, type(obs))


if __name__ == '__main__':
    unittest.main()

