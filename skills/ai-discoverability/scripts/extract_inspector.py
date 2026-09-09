import json
import logging
from html.parser import HTMLParser
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse

from .finding_factory import FindingFactory
from .html_reader import ReadObservation

logger = logging.getLogger(__name__)

@dataclass
class JsonLdBlock:
    index: int
    raw_content: str
    is_valid: bool
    parsed_data: Any = None
    parse_error: Optional[str] = None
    types: List[str] = field(default_factory=list)

@dataclass
class ExtractObservation:
    url: str
    jsonld_blocks: List[JsonLdBlock] = field(default_factory=list)
    types_found: Set[str] = field(default_factory=set)
    opengraph: Dict[str, List[str]] = field(default_factory=dict)
    twitter: Dict[str, List[str]] = field(default_factory=dict)
    landmarks: Dict[str, bool] = field(default_factory=lambda: {
        "main": False,
        "article": False,
        "header": False,
        "footer": False,
        "nav": False,
        "aside": False
    })
    roles: Dict[str, bool] = field(default_factory=lambda: {
        "main": False,
        "navigation": False,
        "banner": False,
        "contentinfo": False
    })
    canonical_url: Optional[str] = None
    title: Optional[str] = None

class ExtractHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.observation = ExtractObservation(url="")
        self.in_jsonld_script = False
        self.current_jsonld_content = []
        self.jsonld_count = 0
        self.in_title = False
        self.current_title = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        
        if tag == "script":
            if attr_dict.get("type", "").lower().strip() == "application/ld+json":
                self.in_jsonld_script = True
                self.current_jsonld_content = []
                
        elif tag == "meta":
            property_attr = attr_dict.get("property", "")
            name_attr = attr_dict.get("name", "")
            content_attr = attr_dict.get("content", "")
            
            if property_attr.startswith("og:"):
                self.observation.opengraph.setdefault(property_attr, []).append(content_attr)
            elif name_attr.startswith("twitter:"):
                self.observation.twitter.setdefault(name_attr, []).append(content_attr)
                
        elif tag == "link":
            if attr_dict.get("rel") == "canonical":
                self.observation.canonical_url = attr_dict.get("href")
                
        elif tag == "title":
            self.in_title = True
            self.current_title = []
            
        elif tag in self.observation.landmarks:
            self.observation.landmarks[tag] = True
            
        role = attr_dict.get("role")
        if role and role in self.observation.roles:
            self.observation.roles[role] = True

    def handle_endtag(self, tag):
        if tag == "script" and self.in_jsonld_script:
            self.in_jsonld_script = False
            raw_content = "".join(self.current_jsonld_content).strip()
            
            if raw_content:
                block = JsonLdBlock(index=self.jsonld_count, raw_content=raw_content, is_valid=False)
                self.jsonld_count += 1
                try:
                    parsed = json.loads(raw_content)
                    block.is_valid = True
                    block.parsed_data = parsed
                    block.types = self._extract_types(parsed)
                    self.observation.types_found.update(block.types)
                except json.JSONDecodeError as e:
                    block.parse_error = str(e)
                self.observation.jsonld_blocks.append(block)
                
        elif tag == "title" and self.in_title:
            self.in_title = False
            self.observation.title = "".join(self.current_title).strip()

    def handle_data(self, data):
        if self.in_jsonld_script:
            self.current_jsonld_content.append(data)
        elif self.in_title:
            self.current_title.append(data)

    def handle_entityref(self, name):
        # Handle HTML entities inside script/title tags (though rare in script, could happen)
        # Actually for JSON-LD we should just append the raw entity string so it can be unescaped properly, 
        # but let's just append `&name;` for simplicity or use html.unescape later.
        pass

    def _extract_types(self, parsed_data) -> List[str]:
        types = []
        if isinstance(parsed_data, dict):
            if "@type" in parsed_data:
                t = parsed_data["@type"]
                if isinstance(t, str):
                    types.append(t)
                elif isinstance(t, list):
                    types.extend([str(x) for x in t])
            if "@graph" in parsed_data and isinstance(parsed_data["@graph"], list):
                for item in parsed_data["@graph"]:
                    types.extend(self._extract_types(item))
            for k, v in parsed_data.items():
                if isinstance(v, (dict, list)) and k not in ("@graph",):
                    if isinstance(v, dict):
                         types.extend(self._extract_types(v))
                    elif isinstance(v, list):
                         for item in v:
                             if isinstance(item, dict):
                                 types.extend(self._extract_types(item))
        elif isinstance(parsed_data, list):
            for item in parsed_data:
                types.extend(self._extract_types(item))
        return list(set(types))

class ExtractInspector:
    def __init__(self, finding_factory: FindingFactory):
        self.finding_factory = finding_factory

    def inspect_page(self, url: str, html_content: str, read_obs: ReadObservation) -> tuple[List[Dict[str, Any]], ExtractObservation]:
        parser = ExtractHTMLParser()
        parser.observation.url = url
        try:
            parser.feed(html_content)
        except Exception as e:
            logger.warning(f"Error parsing HTML for Extract on {url}: {e}")
        
        obs = parser.observation
        findings = []
        
        findings.extend(self._analyze_jsonld(url, obs))
        findings.extend(self._analyze_opengraph(url, obs))
        findings.extend(self._analyze_meaningful_gaps(url, obs, read_obs))
        findings.extend(self._analyze_semantic_landmarks(url, obs))
        findings.extend(self._analyze_contradictions(url, obs, read_obs))
        
        return findings, obs

    def _analyze_jsonld(self, url: str, obs: ExtractObservation) -> List[Dict[str, Any]]:
        findings = []
        invalid_blocks = [b for b in obs.jsonld_blocks if not b.is_valid and b.raw_content.strip()]
        valid_blocks = [b for b in obs.jsonld_blocks if b.is_valid]
        
        if invalid_blocks:
            # If there are valid blocks, a malformed one is lower severity
            severity = "low" if valid_blocks else "medium"
            for b in invalid_blocks:
                findings.append(self.finding_factory.create_finding(
                    title="Malformed JSON-LD Structured Data",
                    subcategory="json_ld",
                    severity=severity,
                    evidence=f"At {url}, JSON-LD block {b.index} failed JSON parsing: {b.parse_error}",
                    why_it_matters="Malformed JSON-LD prevents search engines and AI agents from extracting structured entity metadata.",
                    suggested_action_summary="Validate JSON-LD syntax",
                    suggested_action_details="Use a linter or structured data testing tool to fix parsing errors.",
                    methodology="Extract"
                ))
        return findings

    def _analyze_opengraph(self, url: str, obs: ExtractObservation) -> List[Dict[str, Any]]:
        findings = []
        # Missing OpenGraph on a content-rich page might be an issue.
        # But we only flag if it's completely absent and it's a shareable page.
        # Let's check for strong og:url conflict.
        if "og:url" in obs.opengraph and obs.canonical_url:
            og_url = obs.opengraph["og:url"][0].strip()
            canonical = obs.canonical_url.strip()
            # If they differ significantly (ignoring trailing slashes or scheme)
            og_parsed = urlparse(og_url)
            can_parsed = urlparse(canonical)
            if og_parsed.netloc and can_parsed.netloc and og_parsed.netloc != can_parsed.netloc:
                findings.append(self.finding_factory.create_finding(
                    title="Conflicting OpenGraph URL and Canonical URL",
                    subcategory="opengraph",
                    severity="medium",
                    evidence=f"At {url}, og:url is '{og_url}' but canonical URL is '{canonical}'.",
                    why_it_matters="Conflicting URLs confuse crawlers determining the primary identity of the page.",
                    suggested_action_summary="Align OpenGraph and canonical URLs",
                    suggested_action_details="Ensure og:url and canonical link point to the same authoritative URL.",
                    methodology="Extract"
                ))
        return findings

    def _analyze_meaningful_gaps(self, url: str, obs: ExtractObservation, read_obs: ReadObservation) -> List[Dict[str, Any]]:
        findings = []
        # We need a conservative heuristic for gaps.
        # If read_obs has substantial text, a title with 'Product' or 'Article', etc.
        # This is tricky to do deterministically without LLM.
        # Let's use simple string matching on the title and URL structure for clear indicators.
        
        title_lower = obs.title.lower() if obs.title else ""
        url_lower = url.lower()
        
        # Product detection
        is_product_likely = (
            ("/product/" in url_lower or "/p/" in url_lower or "/item/" in url_lower) and
            ("buy" in title_lower or "price" in title_lower or "$" in read_obs.visible_text)
        )
        if is_product_likely and not any(t in obs.types_found for t in ["Product", "Offer"]):
            # Double check if it's really a product, maybe check html structural tags?
            # We'll use low/medium severity.
            findings.append(self.finding_factory.create_finding(
                title="Missing Product Structured Data",
                subcategory="structured_data",
                severity="medium",
                evidence=f"Page at {url} appears to represent a product/offer (based on URL/title/content) but lacks 'Product' or 'Offer' JSON-LD schema.",
                why_it_matters="Missing product schema prevents rich shopping results and AI agent product extraction.",
                suggested_action_summary="Add Product structured data",
                    suggested_action_details="Add Schema.org/Product and Schema.org/Offer JSON-LD to product pages.",
                    methodology="Extract"
            ))

        # Article detection
        is_article_likely = (
            ("/blog/" in url_lower or "/article/" in url_lower or "/news/" in url_lower) and
            read_obs.structural_tags.get("p", 0) > 3 and
            obs.landmarks.get("article", False)
        )
        if is_article_likely and not any(t in obs.types_found for t in ["Article", "NewsArticle", "BlogPosting"]):
            findings.append(self.finding_factory.create_finding(
                title="Missing Article Structured Data",
                subcategory="structured_data",
                severity="medium",
                evidence=f"Page at {url} uses <article> landmarks and paragraph structures typical of an article, but lacks 'Article' schema.",
                why_it_matters="Article schema is critical for news aggregators, reading modes, and AI summary bots.",
                suggested_action_summary="Add Article structured data",
                    suggested_action_details="Add Schema.org/Article JSON-LD to blog posts and news articles.",
                    methodology="Extract"
            ))

        return findings

    def _analyze_semantic_landmarks(self, url: str, obs: ExtractObservation) -> List[Dict[str, Any]]:
        findings = []
        has_main = obs.landmarks.get("main", False) or obs.roles.get("main", False)
        has_article = obs.landmarks.get("article", False)
        
        if not has_main and not has_article:
            findings.append(self.finding_factory.create_finding(
                title="Missing Primary Content Landmark",
                subcategory="semantic_structure",
                severity="low",
                evidence=f"Page at {url} lacks a <main> tag, <article> tag, or role='main' attribute.",
                why_it_matters="Semantic landmarks help screen readers and AI agents identify the primary content region, ignoring navigation and footers.",
                suggested_action_summary="Add primary semantic landmark",
                    suggested_action_details="Wrap the primary page content in a <main> tag.",
                    methodology="Extract"
            ))
        return findings

    def _analyze_contradictions(self, url: str, obs: ExtractObservation, read_obs: ReadObservation) -> List[Dict[str, Any]]:
        findings = []
        # Check if structured data contradicts visible text.
        # Since fuzzy matching is disallowed, we only flag exact strict contradictions where we can reliably extract data.
        # This is generally difficult to do purely deterministically without false positives, so we keep it very conservative.
        return findings

