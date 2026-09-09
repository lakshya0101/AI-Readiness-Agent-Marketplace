import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .finding_factory import FindingFactory
from .html_reader import ReadObservation
from .extract_inspector import ExtractObservation

@dataclass
class IdentifyObservation:
    url: str
    identity_signals: Dict[str, Any] = field(default_factory=dict)
    identity_assessment: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class IdentifyInspector:
    def __init__(self, finding_factory: FindingFactory):
        self.finding_factory = finding_factory
        # Legal suffixes
        self.suffix_re = re.compile(r'\b(inc|incorporated|llc|ltd|limited|corp|corporation)\b', re.IGNORECASE)

    def _normalize_name(self, name: Any) -> str:
        if not name or not isinstance(name, str):
            return ""
        n = name.lower()
        n = re.sub(r'[^\w\s]', ' ', n)
        n = self.suffix_re.sub(' ', n)
        return " ".join(n.split())

    def _match_names(self, n1: str, n2: str) -> bool:
        if not n1 or not n2:
            return False
        # Conservative substring match
        return n1 in n2 or n2 in n1

    def _normalize_domain(self, url: str) -> str:
        if not url or not isinstance(url, str):
            return ""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if not netloc:
                # Might be missing scheme, e.g. example.com/foo
                if "/" in url and not url.startswith("/"):
                    netloc = url.split("/")[0].lower()
                elif not url.startswith("/"):
                    netloc = url.lower()
                    
            if ":" in netloc:
                netloc = netloc.split(":")[0]
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    def _walk_jsonld(self, data: Any, entities: List[Dict[str, Any]], same_as_list: List[str]):
        if isinstance(data, dict):
            t = data.get('@type', '')
            if t:
                # Handle array of types
                if isinstance(t, list):
                    t = t[0] if t else ''
                entities.append(data)
            
            # Extract sameAs anywhere
            same_as = data.get('sameAs')
            if same_as:
                if isinstance(same_as, list):
                    for s in same_as:
                        if isinstance(s, str):
                            same_as_list.append(s)
                elif isinstance(same_as, str):
                    same_as_list.append(same_as)

            for k, v in data.items():
                self._walk_jsonld(v, entities, same_as_list)
        elif isinstance(data, list):
            for item in data:
                self._walk_jsonld(item, entities, same_as_list)

    def inspect_page(
        self,
        url: str,
        read_obs: ReadObservation,
        extract_obs: ExtractObservation
    ) -> Tuple[List[Dict[str, Any]], IdentifyObservation]:
        
        findings: List[Dict[str, Any]] = []
        
        # 1. Collect Signals
        title = read_obs.title or ""
        h1s = [text for tag, text in read_obs.headings if tag == "h1"]
        first_h1 = h1s[0] if h1s else ""
        og_title = extract_obs.opengraph.get("og:title", [""])[0] if "og:title" in extract_obs.opengraph else ""
        
        entities: List[Dict[str, Any]] = []
        same_as_list: List[str] = []
        
        for block in extract_obs.jsonld_blocks:
            if block.parsed_data:
                self._walk_jsonld(block.parsed_data, entities, same_as_list)
                
        org_names = []
        website_names = []
        product_names = []
        brand_names = []
        declared_urls = []
        
        for e in entities:
            t = str(e.get('@type', ''))
            name = str(e.get('name', '')) if e.get('name') else ''
            e_url = str(e.get('url', '')) if e.get('url') else ''
            
            if 'Organization' in t or 'LocalBusiness' in t or 'Corporation' in t:
                if name: org_names.append(name)
                if e_url: declared_urls.append(e_url)
                
                # Check publisher of something else maybe?
                # Publisher is usually nested, handled if it has @type Organization
                
            if 'WebSite' in t or 'WebPage' in t:
                if name: website_names.append(name)
                if e_url: declared_urls.append(e_url)
                
            if 'Product' in t or 'Service' in t:
                if name: product_names.append(name)
                if e_url: declared_urls.append(e_url)
                brand = e.get('brand')
                if isinstance(brand, dict) and brand.get('name'):
                    brand_names.append(str(brand.get('name')))
                elif isinstance(brand, str):
                    brand_names.append(brand)

        norm_title = self._normalize_name(title)
        norm_h1 = self._normalize_name(first_h1)
        norm_og = self._normalize_name(og_title)
        norm_orgs = [self._normalize_name(n) for n in org_names]
        norm_websites = [self._normalize_name(n) for n in website_names]
        norm_products = [self._normalize_name(n) for n in product_names]
        norm_brands = [self._normalize_name(n) for n in brand_names]

        identity_signals = {
            "page_title": title,
            "h1": first_h1,
            "og_title": og_title,
            "organization_names": org_names,
            "website_names": website_names,
            "product_names": product_names,
            "brand_names": brand_names,
            "declared_urls": declared_urls,
            "canonical_url": extract_obs.canonical_url,
            "same_as": same_as_list
        }

        strong_conflicts = []
        status = "insufficient"
        
        if norm_title or norm_h1 or norm_orgs or norm_websites:
            status = "consistent"
            
        # 2. BRAND NAME / ENTITY CONSISTENCY
        # Conflict A: Org name contradicts WebSite name AND Page H1
        if norm_orgs and norm_websites and norm_h1:
            org_n = norm_orgs[0]
            site_n = norm_websites[0]
            if not self._match_names(org_n, site_n) and not self._match_names(org_n, norm_h1):
                strong_conflicts.append("Organization name contradicts WebSite name and H1")
                findings.append(self.finding_factory.create_finding(
                    subcategory="entity_identity",
                    title="Structured Entity Name Conflicts With Page Identity",
                    severity="medium",
                    evidence=f"At {url}, Organization name '{org_names[0]}' strongly contradicts WebSite name '{website_names[0]}' and Page H1 '{first_h1}'.",
                    why_it_matters="Conflicting structured identities prevent automated agents from disambiguating the entity.",
                    suggested_action_summary="Align structured data names",
                    suggested_action_details="Ensure Organization and WebSite schema names correctly reflect the same entity.",
                    methodology="Identify"
                ))

        # Conflict B: Org name contradicts page H1 AND title (and no product schema justifies it)
        elif norm_orgs and norm_h1 and norm_title:
            org_n = norm_orgs[0]
            if not self._match_names(org_n, norm_h1) and not self._match_names(org_n, norm_title):
                # Only flag if H1 and Title align with each other (multiple independent signals)
                if self._match_names(norm_title, norm_h1) or norm_title == norm_h1:
                    # And there's no product schema explaining the H1
                    product_explains = False
                    for p in norm_products:
                        if self._match_names(p, norm_h1) or self._match_names(p, norm_title):
                            product_explains = True
                            break
                    if not product_explains:
                        strong_conflicts.append("Organization name contradicts page Title and H1")
                        findings.append(self.finding_factory.create_finding(
                            subcategory="brand_consistency",
                            title="Identity Signals Are Inconsistent",
                            severity="medium",
                            evidence=f"At {url}, Organization name '{org_names[0]}' shares no identity with Title '{title}' or H1 '{first_h1}', with no Product schema to explain the difference.",
                            why_it_matters="A declared structured organization that entirely conflicts with the page's visible primary identity causes entity confusion.",
                            suggested_action_summary="Align Organization schema with page identity",
                            suggested_action_details="Update the Organization schema to reflect the actual entity, or ensure the page title reflects the organization.",
                            methodology="Identify"
                        ))
                        
        # 3. CANONICAL URL ANALYSIS
        page_domain = self._normalize_domain(url)
        canon_domain = self._normalize_domain(extract_obs.canonical_url) if extract_obs.canonical_url else ""
        
        if canon_domain and page_domain and canon_domain != page_domain:
            strong_conflicts.append("Canonical URL points to different origin")
            findings.append(self.finding_factory.create_finding(
                subcategory="canonical_identity",
                title="Canonical URL Conflicts With Page Identity",
                severity="medium",
                evidence=f"At {url}, the canonical URL '{extract_obs.canonical_url}' points to a completely different domain ({canon_domain} vs {page_domain}).",
                why_it_matters="A cross-domain canonical tag tells bots that the true identity of this page belongs to another website.",
                suggested_action_summary="Fix canonical URL domain",
                suggested_action_details="Ensure the canonical URL points to the correct authoritative domain for this entity.",
                methodology="Identify"
            ))
            
        # JSON-LD URL vs Canonical Origin
        if canon_domain and declared_urls:
            for d_url in declared_urls:
                d_domain = self._normalize_domain(d_url)
                if d_domain and d_domain != canon_domain and d_domain != page_domain:
                    # JSON-LD points to different origin than canonical AND page
                    strong_conflicts.append("Structured data URL conflicts with canonical origin")
                    findings.append(self.finding_factory.create_finding(
                        subcategory="structured_identity",
                        title="Structured Entity Name Conflicts With Page Identity",
                        severity="low",
                        evidence=f"At {url}, structured data declares URL '{d_url}' which contradicts the canonical/page domain '{canon_domain or page_domain}'.",
                        why_it_matters="Mismatched domain declarations in schema create ambiguity about the entity's primary web property.",
                        suggested_action_summary="Align structured data URLs",
                        suggested_action_details="Ensure Organization/WebSite 'url' properties match the canonical domain.",
                        methodology="Identify"
                    ))
                    break # only flag once
                    
        # 4. SAMEAS QUALITY
        malformed_count = 0
        invalid_examples = []
        for s in same_as_list:
            # Check for non-URL strings or obvious malformations
            if " " in s or not ("." in s or "/" in s):
                malformed_count += 1
                if len(invalid_examples) < 2:
                    invalid_examples.append(s)
                    
        if malformed_count > 0:
            strong_conflicts.append(f"Malformed sameAs values ({malformed_count})")
            findings.append(self.finding_factory.create_finding(
                subcategory="same_as",
                title="Malformed sameAs Relationship",
                severity="low",
                evidence=f"At {url}, found {malformed_count} clearly invalid non-URL values in sameAs (e.g., '{invalid_examples[0]}').",
                why_it_matters="Invalid sameAs entries (like plain text names instead of URLs) break knowledge graph linkages.",
                suggested_action_summary="Use valid URLs in sameAs",
                suggested_action_details="Ensure all sameAs properties contain fully qualified absolute URLs.",
                methodology="Identify"
            ))

        if strong_conflicts:
            status = "inconsistent"

        identity_assessment = {
            "status": status,
            "strong_conflicts": strong_conflicts,
            "supporting_signals": []
        }

        obs = IdentifyObservation(
            url=url,
            identity_signals=identity_signals,
            identity_assessment=identity_assessment
        )
        
        return findings, obs

