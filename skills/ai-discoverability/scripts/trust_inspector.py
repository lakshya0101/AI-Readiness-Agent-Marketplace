import re
from datetime import date
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from .finding_factory import FindingFactory
from .html_reader import ReadObservation
from .extract_inspector import ExtractObservation
from .identify_inspector import IdentifyObservation

@dataclass
class TrustObservation:
    url: str
    security: Dict[str, Any] = field(default_factory=dict)
    attribution: Dict[str, Any] = field(default_factory=dict)
    freshness: Dict[str, Any] = field(default_factory=dict)
    transparency: Dict[str, Any] = field(default_factory=dict)
    corroboration: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class TrustInspector:
    def __init__(self, finding_factory: FindingFactory):
        self.finding_factory = finding_factory
        self.today = date.today()

    def _parse_date(self, d_str: str) -> Optional[date]:
        if not isinstance(d_str, str):
            return None
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', d_str)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
        return None

    def _extract_meta_content(self, html: str, name_or_property: str) -> List[str]:
        # Matches <meta name="foo" content="bar"> or <meta property="foo" content="bar">
        pattern = r'<meta\b[^>]*(?:name|property)=["\']' + re.escape(name_or_property) + r'["\'][^>]*content=["\']([^"\']+)["\']'
        return re.findall(pattern, html, re.IGNORECASE)

    def _walk_jsonld_for_trust(self, data: Any, authors: List[str], publishers: List[str], dates: Dict[str, List[str]], is_article: List[bool], is_commercial: List[bool]):
        if isinstance(data, dict):
            t = str(data.get('@type', ''))
            
            # Article signals
            if 'Article' in t or 'NewsArticle' in t or 'BlogPosting' in t:
                is_article.append(True)
                
            # Commercial signals (DO NOT include Organization by itself)
            if 'Product' in t or 'Offer' in t or 'Service' in t or 'LocalBusiness' in t:
                is_commercial.append(True)

            author = data.get('author')
            if isinstance(author, dict) and author.get('name'):
                authors.append(str(author.get('name')))
            elif isinstance(author, list):
                for a in author:
                    if isinstance(a, dict) and a.get('name'):
                        authors.append(str(a.get('name')))
                    elif isinstance(a, str):
                        authors.append(a)
            elif isinstance(author, str):
                authors.append(author)

            publisher = data.get('publisher')
            if isinstance(publisher, dict) and publisher.get('name'):
                publishers.append(str(publisher.get('name')))
            elif isinstance(publisher, list):
                for p in publisher:
                    if isinstance(p, dict) and p.get('name'):
                        publishers.append(str(p.get('name')))
                    elif isinstance(p, str):
                        publishers.append(p)
            elif isinstance(publisher, str):
                publishers.append(publisher)

            dp = data.get('datePublished')
            if dp and isinstance(dp, str):
                dates['published'].append(dp)
            dm = data.get('dateModified')
            if dm and isinstance(dm, str):
                dates['modified'].append(dm)

            for k, v in data.items():
                if k not in ('author', 'publisher'):
                    self._walk_jsonld_for_trust(v, authors, publishers, dates, is_article, is_commercial)
        elif isinstance(data, list):
            for item in data:
                self._walk_jsonld_for_trust(item, authors, publishers, dates, is_article, is_commercial)

    def _match_names(self, n1: str, n2: str) -> bool:
        if not n1 or not n2:
            return False
        n1 = re.sub(r'[^\w\s]', ' ', n1.lower())
        n2 = re.sub(r'[^\w\s]', ' ', n2.lower())
        n1 = re.sub(r'\b(inc|incorporated|llc|ltd|limited|corp|corporation)\b', ' ', n1)
        n2 = re.sub(r'\b(inc|incorporated|llc|ltd|limited|corp|corporation)\b', ' ', n2)
        n1 = " ".join(n1.split())
        n2 = " ".join(n2.split())
        if not n1 or not n2:
            return False
        # Accept if one is a substring of the other, or if they share meaningful words
        tokens1 = set(n1.split())
        tokens2 = set(n2.split())
        # To avoid false positive matches on common words like "the", "and" - we assume brand names are specific enough
        return bool(tokens1.intersection(tokens2)) or (n1 in n2) or (n2 in n1)

    def inspect_page(
        self,
        url: str,
        html_content: str,
        headers: Dict[str, str],
        is_https: bool,
        read_obs: ReadObservation,
        extract_obs: ExtractObservation,
        identify_obs: IdentifyObservation,
        existing_findings: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], TrustObservation]:
        
        findings: List[Dict[str, Any]] = []
        
        # 1. SECURITY / TRANSPORT
        security = {
            "protocol": "https" if is_https else "http",
            "strict_transport_security": headers.get("Strict-Transport-Security", ""),
            "content_security_policy": headers.get("Content-Security-Policy", ""),
            "x_content_type_options": headers.get("X-Content-Type-Options", ""),
            "referrer_policy": headers.get("Referrer-Policy", "")
        }

        if not is_https:
            already_flagged = any(f.get("title") == "Website Does Not Enforce HTTPS Protocol" for f in existing_findings)
            if not already_flagged:
                findings.append(self.finding_factory.create_finding(
                    subcategory="security",
                    title="Page Served Over HTTP",
                    severity="medium",
                    evidence=f"At {url}, the page is served over unencrypted HTTP. No prior Reach HTTPS finding exists.",
                    why_it_matters="Data in transit can be intercepted or manipulated, breaking data integrity.",
                    suggested_action_summary="Enforce HTTPS",
                    suggested_action_details="Serve all pages over HTTPS with secure certificates.",
                    methodology="Trust"
                ))

        # 2. ATTRIBUTION & TYPE
        authors = self._extract_meta_content(html_content, "author")
        publishers = self._extract_meta_content(html_content, "publisher")
        
        dates_extracted = {'published': [], 'modified': []}
        is_article_flags = []
        is_commercial_flags = []
        
        for block in extract_obs.jsonld_blocks:
            if block.parsed_data:
                self._walk_jsonld_for_trust(block.parsed_data, authors, publishers, dates_extracted, is_article_flags, is_commercial_flags)

        dates_extracted['published'].extend(self._extract_meta_content(html_content, "article:published_time"))
        dates_extracted['modified'].extend(self._extract_meta_content(html_content, "article:modified_time"))

        # More robust article classification:
        has_article_schema = bool(is_article_flags)
        has_article_tag = bool(re.search(r'<article\b', html_content, re.IGNORECASE))
        has_pub_date = bool(dates_extracted['published'] or dates_extracted['modified'])
        
        is_article = has_article_schema or (has_article_tag and has_pub_date)
        
        # Robust commercial classification
        # Look for pricing/checkout keywords if no schema explicitly calls it commercial
        if not is_commercial_flags:
            title_text = (read_obs.title or "").lower()
            if any(k in title_text for k in ["pricing", "checkout", "cart", "buy", "store"]):
                is_commercial_flags.append(True)
        is_commercial = bool(is_commercial_flags)

        attribution = {
            "authors": list(set(authors)),
            "publishers": list(set(publishers)),
            "author_urls": [],
            "publisher_urls": [],
            "is_article": is_article,
            "is_commercial": is_commercial
        }

        if is_article and not authors and not publishers and not identify_obs.identity_signals.get("organization_names"):
            evidence_str = f"At {url}, the page "
            if has_article_schema:
                evidence_str += "contains Article/NewsArticle JSON-LD"
            else:
                evidence_str += "uses <article> tags alongside publication dates"
            evidence_str += " but exposes no author or publisher metadata."
            
            findings.append(self.finding_factory.create_finding(
                subcategory="attribution",
                title="Important Content Lacks Attribution",
                severity="medium",
                evidence=evidence_str,
                why_it_matters="Automated systems cannot assess the provenance or credibility of anonymous articles.",
                suggested_action_summary="Add author or publisher metadata",
                suggested_action_details="Use schema.org/Article to specify an author or publisher entity.",
                methodology="Trust"
            ))

        # 3. FRESHNESS / DATES
        pub_dates = [self._parse_date(d) for d in dates_extracted['published'] if self._parse_date(d)]
        mod_dates = [self._parse_date(d) for d in dates_extracted['modified'] if self._parse_date(d)]
        
        status = "undated"
        oldest_pub = min(pub_dates) if pub_dates else None
        oldest_mod = min(mod_dates) if mod_dates else None
        
        if oldest_pub or oldest_mod:
            status = "recent"
            ref_date = oldest_mod if oldest_mod else oldest_pub
            age_days = (self.today - ref_date).days
            if age_days > 365:
                status = "dated"
                
                # Check for staleness signal (temporal contradiction)
                # Does the title imply the content is current? E.g., it claims a year >= current year
                title = read_obs.title or ""
                year_match = re.search(r'\b(20\d{2})\b', title)
                if year_match:
                    title_year = int(year_match.group(1))
                    # Stale if title claims a year strictly >= the current year but content is > 365 days old
                    if title_year >= self.today.year:
                        status = "stale_signal"
                        findings.append(self.finding_factory.create_finding(
                            subcategory="freshness",
                            title="Important Content Shows a Strong Staleness Signal",
                            severity="medium",
                            evidence=f"At {url}, the page is over a year old ({ref_date}) yet the title explicitly claims current/future temporal context ('{title}').",
                            why_it_matters="Stale temporal claims can lead to AI systems returning confidently incorrect obsolete information.",
                            suggested_action_summary="Update or archive stale content",
                            suggested_action_details="Update the content to reflect current reality, or adjust the title.",
                            methodology="Trust"
                        ))

        if pub_dates and mod_dates:
            max_pub = max(pub_dates)
            min_mod = min(mod_dates)
            if min_mod < max_pub:
                status = "inconsistent_dates"
                findings.append(self.finding_factory.create_finding(
                    subcategory="consistency",
                    title="Important Content Has Inconsistent Publication Metadata",
                    severity="medium",
                    evidence=f"At {url}, the earliest modification date ({min_mod}) precedes the latest publication date ({max_pub}).",
                    why_it_matters="Contradictory timestamps undermine automated trust in the content lifecycle metadata.",
                    suggested_action_summary="Fix publication timestamps",
                    suggested_action_details="Ensure dateModified is chronologically after or equal to datePublished.",
                    methodology="Trust"
                ))

        freshness = {
            "published_dates": [str(d) for d in set(pub_dates)],
            "modified_dates": [str(d) for d in set(mod_dates)],
            "status": status
        }

        # 4. TRANSPARENCY (Privacy/Terms Links)
        privacy_links = []
        terms_links = []
        
        a_tags = re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_content, re.IGNORECASE)
        for href, text in a_tags:
            href_lower = href.lower()
            text_lower = text.lower()
            # Explicit anchor text or distinct URL paths
            if 'privacy' in text_lower or 'privacy-policy' in href_lower or '/privacy' in href_lower:
                privacy_links.append(href)
            if 'terms' in text_lower or 'legal' in text_lower or 'terms-of-service' in href_lower or '/terms' in href_lower or '/legal' in href_lower:
                terms_links.append(href)

        transparency = {
            "privacy_links": list(set(privacy_links)),
            "terms_links": list(set(terms_links)),
            "legal_links": []
        }

        obs = TrustObservation(
            url=url,
            security=security,
            attribution=attribution,
            freshness=freshness,
            transparency=transparency,
            corroboration={"internal_conflicts": []}
        )

        return findings, obs

    def evaluate_cross_page(
        self,
        observations: List[TrustObservation],
        identify_observations: List[IdentifyObservation]
    ) -> List[Dict[str, Any]]:
        findings = []

        # 1. Transparency Gap
        is_commercial = any(obs.attribution.get("is_commercial") for obs in observations)
        has_privacy = any(obs.transparency.get("privacy_links") for obs in observations)
        
        if is_commercial and not has_privacy and len(observations) > 1:
            findings.append(self.finding_factory.create_finding(
                subcategory="transparency",
                title="Meaningful Transparency Signal Gap",
                severity="low",
                evidence=f"Inspected the root page and {len(observations)-1} representative internal pages of a commercial site (identified via Product/Offer schemas or commercial intent); no explicit privacy/legal links were found.",
                why_it_matters="Absence of privacy and legal transparency policies lowers corroboration trust scores for commercial entities.",
                suggested_action_summary="Add explicit privacy/legal links",
                suggested_action_details="Ensure commercial properties provide explicit footer links to privacy and terms documentation.",
                methodology="Trust"
            ))

        # 2. Internal Corroboration (Conflicting Factual Values)
        # Only compare if they represent strongly divergent names on comparable domains
        org_names_map = {}
        for id_obs in identify_observations:
            orgs = id_obs.identity_signals.get("organization_names", [])
            if orgs:
                org_names_map[id_obs.url] = orgs[0]
                
        # Find material conflicts (e.g. Globex vs Acme) rather than sub-brands (Acme vs Acme Labs)
        unique_orgs = list(set(org_names_map.values()))
        material_conflict = False
        if len(unique_orgs) > 1:
            for i in range(len(unique_orgs)):
                for j in range(i+1, len(unique_orgs)):
                    if not self._match_names(unique_orgs[i], unique_orgs[j]):
                        material_conflict = True
                        break
                        
        if material_conflict:
            evidence_details = ", ".join([f"'{org}' at {url}" for url, org in org_names_map.items()])
            findings.append(self.finding_factory.create_finding(
                subcategory="corroboration",
                title="Conflicting Factual Values Across Inspected Pages",
                severity="medium",
                evidence=f"Materially conflicting primary organization identities were declared across inspected pages: {evidence_details}.",
                why_it_matters="Internal factual contradictions prevent automated systems from establishing a single source of truth.",
                suggested_action_summary="Consolidate factual claims across pages",
                suggested_action_details="Ensure organization identity and other core facts are consistent and do not explicitly contradict.",
                methodology="Trust"
            ))

        return findings
