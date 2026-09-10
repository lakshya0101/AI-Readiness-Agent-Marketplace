"""AI Discoverability Audit Module - Reach & Read Stages.

Evaluates whether important publicly accessible information on a target website
can be reached and read by automated readers and AI assistants under normal crawl conditions.

Capabilities:
    REACH STAGE:
    1. Target URL validation and normalization
    2. HTTP response and redirect chain inspection
    3. Robots.txt RFC 9309 parsing and AI crawler permission matrix
    4. XML Sitemap discovery and syntax validation
    5. Internal link collection and representative page reachability
    6. Broken page detection

    READ STAGE:
    7. HTML text extraction and content-to-code signal
    8. Client-side rendering dependency and SPA application shell detection
    9. Server-rendered structural content evaluation
"""

from __future__ import annotations
import json
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from .finding_factory import FindingFactory, FindingValidationError
from .http_client import HttpClient, HttpResponse
from .robots_inspector import RobotsInspector, RobotsReport
from .sitemap_inspector import SitemapInspector, SitemapResult
from .link_extractor import LinkExtractor
from .html_reader import PageTextExtractor, ReadObservation
from .read_inspector import ReadInspector
from .extract_inspector import ExtractInspector, ExtractObservation
from .understand_inspector import UnderstandInspector, UnderstandObservation
from .identify_inspector import IdentifyInspector, IdentifyObservation
from .trust_inspector import TrustInspector, TrustObservation

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_PAGES = 5
DEFAULT_MAX_REDIRECTS_THRESHOLD = 3


class DiscoverabilityAuditor:
    """Audits website reachability and content readability for AI crawlers and automated agents."""

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        self.options = options or {}
        self.timeout = int(self.options.get("timeout", DEFAULT_TIMEOUT))
        self.user_agent = str(self.options.get("user_agent", ""))
        self.max_pages = int(self.options.get("max_pages", DEFAULT_MAX_PAGES))
        self.max_redirects_threshold = int(self.options.get("max_redirects_threshold", DEFAULT_MAX_REDIRECTS_THRESHOLD))

        client_kwargs: Dict[str, Any] = {"timeout": self.timeout}
        if self.user_agent:
            client_kwargs["user_agent"] = self.user_agent
        self.http_client = HttpClient(**client_kwargs)

        self.factory = FindingFactory()
        self.crawl_metadata: Dict[str, Any] = {}
        self.read_metadata: Dict[str, Any] = {}
        self.extract_metadata: Dict[str, Any] = {}
        self.understand_metadata: Dict[str, Any] = {}
        self.identify_metadata: Dict[str, Any] = {}
        self.trust_metadata: Dict[str, Any] = {}

    @classmethod
    def validate_and_normalize_url(cls, site: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validates and normalizes target site input URL.
        Returns (is_valid, normalized_url, error_message).
        """
        if not site or not isinstance(site, str) or not site.strip():
            return False, "", "Target site URL must be a non-empty string."

        trimmed = site.strip()
        # Strip fragment if provided
        trimmed = trimmed.split("#")[0].strip()

        # Prepend https:// if no scheme is specified
        if not trimmed.startswith(("http://", "https://")):
            if "://" in trimmed:
                scheme = trimmed.split("://", 1)[0]
                return False, "", f"Unsupported URL scheme '{scheme}'. Only HTTP and HTTPS are supported."
            trimmed = "https://" + trimmed

        try:
            parsed = urllib.parse.urlparse(trimmed)
            if not parsed.scheme or parsed.scheme.lower() not in {"http", "https"}:
                return False, "", f"Invalid URL scheme '{parsed.scheme}'. Must be http or https."

            if not parsed.netloc or "." not in parsed.netloc:
                if parsed.netloc.lower() != "localhost":
                    return False, "", f"Invalid domain structure in URL '{trimmed}'."

            # Normalize path
            path = parsed.path if parsed.path else "/"
            normalized = urllib.parse.urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                parsed.params,
                parsed.query,
                "",  # strip fragment
            ))
            return True, normalized, None
        except Exception as ex:
            return False, "", f"Malformed URL parsing error: {str(ex)}"

    def _serialize_extract_obs(self, obs: ExtractObservation) -> Dict[str, Any]:
        return {
            "url": obs.url,
            "jsonld": {
                "block_count": len(obs.jsonld_blocks),
                "valid_blocks": sum(1 for b in obs.jsonld_blocks if b.is_valid),
                "invalid_blocks": sum(1 for b in obs.jsonld_blocks if not b.is_valid and b.raw_content.strip()),
                "types": list(obs.types_found)
            },
            "opengraph": {
                "present": bool(obs.opengraph),
                "fields": obs.opengraph
            },
            "social": {
                "twitter_fields": obs.twitter
            },
            "semantic_landmarks": obs.landmarks,
            "canonical_url": obs.canonical_url,
            "title": obs.title
        }

    def audit(self, site: str) -> Dict[str, Any]:
        """
        Executes the REACH and READ stages of the discoverability audit.
        Returns the standard module payload envelope.
        """
        # -------------------------------------------------------------
        # 1. URL Validation and Normalization
        # -------------------------------------------------------------
        is_valid, target_url, url_error = self.validate_and_normalize_url(site)
        if not is_valid:
            return {
                "skill": "ai-discoverability",
                "status": "failure",
                "findings": [],
                "error": url_error,
                "limitations": [],
            }

        findings: List[Dict[str, Any]] = []
        limitations: List[str] = []

        parsed_target = urllib.parse.urlparse(target_url)
        base_url = f"{parsed_target.scheme}://{parsed_target.netloc}"

        # -------------------------------------------------------------
        # 2. HTTP Response & Redirect Inspection (Target Root)
        # -------------------------------------------------------------
        target_resp = self.http_client.fetch(target_url)

        # Fatal target network/connection failure
        if target_resp.status_code == 0:
            return {
                "skill": "ai-discoverability",
                "status": "failure",
                "findings": [],
                "error": f"Failed to connect to target URL {target_url}: {target_resp.error}",
                "limitations": limitations,
            }

        # Root HTTP 4xx / 5xx Handling
        if target_resp.status_code == 403:
            findings.append(self.factory.create_finding(
                subcategory="http_accessibility",
                title="Target Root URL Returns HTTP 403 Forbidden",
                severity="critical",
                evidence=f"Automated reader requested {target_url} and received HTTP 403 Forbidden. Server response headers: {dict(list(target_resp.headers.items())[:3])}.",
                why_it_matters="Automated crawlers and AI assistants are denied access to the root page, resulting in complete indexing failure.",
                suggested_action_summary="Reconfigure WAF and bot access permissions",
                suggested_action_details="Ensure legitimate web crawlers and automated discovery agents can access public landing pages without triggering 403 blocks.",
                suggested_action_priority="critical",
                affected_pages=[target_url],
                evidence_type="HTTP_HEADER",
                methodology="Reach",
                remediation_complexity="medium",
            ))
        elif target_resp.status_code == 404:
            findings.append(self.factory.create_finding(
                subcategory="http_accessibility",
                title="Target Root URL Returns HTTP 404 Not Found",
                severity="critical",
                evidence=f"Automated reader requested {target_url} and received HTTP 404 Not Found.",
                why_it_matters="The target homepage is missing, preventing automated crawlers from discovering content.",
                suggested_action_summary="Verify target URL and publish landing page",
                suggested_action_details="Ensure the root URL resolves to a live landing page and update any broken entrypoint URLs.",
                suggested_action_priority="critical",
                affected_pages=[target_url],
                evidence_type="HTTP_HEADER",
                methodology="Reach",
                remediation_complexity="low",
            ))
        elif target_resp.is_server_error:
            findings.append(self.factory.create_finding(
                subcategory="http_accessibility",
                title=f"Target Root URL Returns Server Error HTTP {target_resp.status_code}",
                severity="critical",
                evidence=f"Automated reader requested {target_url} and received server error HTTP {target_resp.status_code}.",
                why_it_matters="Origin server errors prevent automated crawlers from accessing site content.",
                suggested_action_summary="Investigate and resolve server error",
                suggested_action_details=f"Inspect server logs for 5xx errors on {target_url} and restore stable HTTP 200 responses.",
                suggested_action_priority="critical",
                affected_pages=[target_url],
                evidence_type="HTTP_HEADER",
                methodology="Reach",
                remediation_complexity="high",
            ))

        # Check for Excessive Redirects
        if target_resp.redirect_count > self.max_redirects_threshold:
            chain_desc = " -> ".join([f"{h['status_code']} to {h['to_url']}" for h in target_resp.redirect_chain])
            findings.append(self.factory.create_finding(
                subcategory="redirects",
                title=f"Excessive Redirect Hops Observed ({target_resp.redirect_count} hops)",
                severity="medium",
                evidence=f"Requested {target_url}. Traversed {target_resp.redirect_count} redirect hops exceeding threshold of {self.max_redirects_threshold}: {chain_desc}.",
                why_it_matters="Multi-hop redirect chains increase crawler latency, consume crawl budgets, and elevate the risk of crawler aborts.",
                suggested_action_summary="Consolidate redirect hops into a single direct redirect",
                suggested_action_details=f"Update server routing and internal links to redirect directly from {target_url} to {target_resp.final_url} in a single HTTP 301 hop.",
                suggested_action_priority="medium",
                affected_pages=[target_url, target_resp.final_url],
                evidence_type="HTTP_HEADER",
                methodology="Reach",
                remediation_complexity="low",
            ))

        # Check HTTPS vs HTTP
        if not target_resp.is_https:
            findings.append(self.factory.create_finding(
                subcategory="http_accessibility",
                title="Website Does Not Enforce HTTPS Protocol",
                severity="medium",
                evidence=f"Requested {target_url} resolved to unencrypted HTTP destination {target_resp.final_url} without automatic upgrade to HTTPS.",
                why_it_matters="AI assistant search pipelines and automated indexing systems prioritize secure HTTPS resources for authoritative citations.",
                suggested_action_summary="Enforce site-wide HTTPS with HTTP 301 redirects",
                suggested_action_details="Install an SSL/TLS certificate and configure the web server or CDN to redirect all unencrypted HTTP requests to HTTPS.",
                suggested_action_priority="high",
                affected_pages=[target_resp.final_url],
                evidence_type="HTTP_HEADER",
                methodology="Reach",
                remediation_complexity="low",
            ))

        # -------------------------------------------------------------
        # 3. Robots.txt Inspection
        # -------------------------------------------------------------
        robots_url = f"{base_url}/robots.txt"
        robots_resp = self.http_client.fetch(robots_url)
        robots_report = RobotsInspector.parse(
            url=robots_url,
            status_code=robots_resp.status_code,
            text=robots_resp.text if robots_resp.is_success else "",
            error=robots_resp.error,
        )

        if robots_resp.is_success:
            # Audit AI crawler restrictions
            ai_blocks = RobotsInspector.audit_ai_restrictions(robots_report, path="/")
            if ai_blocks:
                wildcard_blocks = [b for b in ai_blocks if b["is_wildcard"]]
                specific_blocks = [b for b in ai_blocks if not b["is_wildcard"]]

                if wildcard_blocks:
                    rule_sample = wildcard_blocks[0]["rule"]
                    findings.append(self.factory.create_finding(
                        subcategory="robots",
                        title="Universal Crawler Disallow in robots.txt",
                        severity="critical",
                        evidence=f"Evaluated {robots_url}: 'User-agent: *' contains directive '{rule_sample}' matching root path '/', blocking all automated crawlers and AI assistants.",
                        why_it_matters="Universal root disallow prevents all standard automated search crawlers, AI assistants, and indexing pipelines from reading any site content.",
                        suggested_action_summary="Remove universal root disallow from robots.txt",
                        suggested_action_details="Update robots.txt to restrict only sensitive internal endpoints (e.g. /admin) rather than placing a universal disallow on root '/'.",
                        suggested_action_priority="critical",
                        affected_pages=[robots_url],
                        evidence_type="ROBOTS_TXT",
                        methodology="Reach",
                        remediation_complexity="low",
                    ))
                elif specific_blocks:
                    blocked_names = [b["bot"] for b in specific_blocks]
                    rules_desc = "; ".join([f"{b['bot']} via group '{b['group']}' ({b['rule']})" for b in specific_blocks[:4]])
                    findings.append(self.factory.create_finding(
                        subcategory="robots",
                        title="Major AI Crawlers Explicitly Restricted in robots.txt",
                        severity="high",
                        evidence=f"Evaluated {robots_url}: AI crawlers {', '.join(blocked_names)} are restricted from root path '/' by rules: {rules_desc}.",
                        why_it_matters="Modern AI assistants (ChatGPT, Claude, Perplexity) adhere to robots.txt restrictions and will fail to index or cite information from restricted domains.",
                        suggested_action_summary="Permit verified AI assistant crawlers in robots.txt",
                        suggested_action_details=f"Add explicit 'Allow: /' directives or remove disallow rules for verified AI user-agents ({', '.join(blocked_names[:3])}) in {robots_url}.",
                        suggested_action_priority="high",
                        affected_pages=[robots_url],
                        evidence_type="ROBOTS_TXT",
                        methodology="Reach",
                        remediation_complexity="low",
                    ))
        else:
            limitations.append(f"robots.txt inspection notice: {robots_url} returned status {robots_resp.status_code} ({robots_resp.error or 'Not Available'}).")

        # -------------------------------------------------------------
        # 4. Sitemap Discovery and Validation
        # -------------------------------------------------------------
        sitemap_inspector = SitemapInspector(self.http_client)
        sitemap_results = sitemap_inspector.discover(base_url, robots_report.sitemaps)

        for sr in sitemap_results:
            if sr.is_advertised_in_robots and not (200 <= sr.status_code < 300):
                findings.append(self.factory.create_finding(
                    subcategory="sitemap",
                    title="Advertised Sitemap in robots.txt Is Unreachable",
                    severity="medium",
                    evidence=f"robots.txt advertised sitemap at {sr.url}, but the endpoint returned HTTP status {sr.status_code} ({sr.fetch_error or 'Endpoint unreachable'}).",
                    why_it_matters="Search engines and AI crawler discovery pipelines rely on advertised sitemaps to map site architecture; dead sitemap links impair URL discovery.",
                    suggested_action_summary="Fix or update advertised sitemap location",
                    suggested_action_details=f"Deploy a valid sitemap at {sr.url} or update the Sitemap directive in robots.txt to point to an active sitemap URL.",
                    suggested_action_priority="medium",
                    affected_pages=[sr.url, robots_url],
                    evidence_type="ROBOTS_TXT",
                    methodology="Reach",
                    remediation_complexity="low",
                ))
            elif sr.status_code == 200 and not sr.is_valid_xml:
                findings.append(self.factory.create_finding(
                    subcategory="sitemap",
                    title="Sitemap Contains Malformed or Invalid XML",
                    severity="medium",
                    evidence=f"Discovered sitemap at {sr.url} returned HTTP 200, but failed XML validation: {sr.parse_error}.",
                    why_it_matters="Automated XML ingestors in AI search pipelines cannot parse malformed sitemaps, preventing automated discovery of listed pages.",
                    suggested_action_summary="Correct XML syntax in sitemap",
                    suggested_action_details=f"Ensure {sr.url} produces well-formed XML conforming to the sitemaps.org protocol.",
                    suggested_action_priority="medium",
                    affected_pages=[sr.url],
                    evidence_type="SCHEMA_ORG",
                    methodology="Reach",
                    remediation_complexity="low",
                ))

        # -------------------------------------------------------------
        # 5. Internal Link Extraction & Representative Page Reachability
        # -------------------------------------------------------------
        link_data = LinkExtractor.extract_links(target_resp.text, target_resp.final_url)
        internal_links = link_data["internal_links"]

        representative_pages = LinkExtractor.select_representative_pages(
            internal_links=internal_links,
            root_url=target_resp.final_url,
            max_pages=self.max_pages,
        )

        broken_pages_found: List[Dict[str, Any]] = []

        for page_url in representative_pages:
            if page_url == target_resp.final_url or page_url == target_url:
                continue

            page_resp = self.http_client.fetch(page_url)
            if page_resp.status_code in {404, 410}:
                broken_pages_found.append({
                    "url": page_url,
                    "status_code": page_resp.status_code,
                    "error": f"HTTP {page_resp.status_code}",
                })
            elif page_resp.is_server_error:
                broken_pages_found.append({
                    "url": page_url,
                    "status_code": page_resp.status_code,
                    "error": f"HTTP {page_resp.status_code}",
                })
            elif page_resp.status_code == 0:
                limitations.append(f"Representative page probe failed for {page_url}: {page_resp.error}.")

        if broken_pages_found:
            broken_urls = [p["url"] for p in broken_pages_found]
            broken_desc = ", ".join([f"{p['url']} ({p['error']})" for p in broken_pages_found[:3]])
            findings.append(self.factory.create_finding(
                subcategory="crawlability",
                title=f"Broken Internal Links Detected ({len(broken_pages_found)} page(s) unreachable)",
                severity="medium",
                evidence=f"Audited representative internal pages linked from homepage. The following endpoints returned client/server errors: {broken_desc}.",
                why_it_matters="Broken internal links lead crawlers to dead ends, fragment site architecture, and prevent indexing of important subpages.",
                suggested_action_summary="Repair or remove broken internal links",
                suggested_action_details="Update anchor hrefs on the homepage or implement 301 redirects from broken URLs to active content destinations.",
                suggested_action_priority="medium",
                affected_pages=broken_urls,
                evidence_type="HTML_DOM",
                methodology="Reach",
                remediation_complexity="low",
            ))

        # -------------------------------------------------------------
        # 6. READ STAGE: Content Extractability & Rendering Dependency
        # -------------------------------------------------------------
        read_observations: List[Dict[str, Any]] = []

        # Analyze root page
        root_obs = PageTextExtractor.analyze(target_resp.text, target_resp.final_url)
        read_observations.append(root_obs.to_dict())

        root_read_findings = ReadInspector.evaluate_page(root_obs, self.factory)
        findings.extend(root_read_findings)

        # Multi-page read analysis on already-fetched representative pages
        for page_url in representative_pages:
            if page_url == target_resp.final_url or page_url == target_url:
                continue

            page_resp = self.http_client.cache.get(page_url)
            if page_resp and page_resp.is_success and page_resp.text:
                rep_obs = PageTextExtractor.analyze(page_resp.text, page_url)
                read_observations.append(rep_obs.to_dict())

                # If root page did not already flag rendering dependency, evaluate secondary pages
                if not any(f["subcategory"] == "rendering_dependency" for f in root_read_findings):
                    rep_findings = ReadInspector.evaluate_page(rep_obs, self.factory)
                    findings.extend(rep_findings)

        self.read_metadata = {
            "root_observation": root_obs.to_dict(),
            "all_observations": read_observations,
            "pages_analyzed": len(read_observations),
        }

        limitations.append(
            "Read stage analyzed initial server-delivered HTML; browser-rendered DOM comparison is not active in this non-browser pass."
        )

        # -------------------------------------------------------------
        # 7. EXTRACT STAGE: Structured Data & Semantic Landmarks
        # -------------------------------------------------------------
        extract_inspector = ExtractInspector(self.factory)
        
        # Analyze root page
        extract_findings, root_extract_obs = extract_inspector.inspect_page(
            url=target_resp.final_url,
            html_content=target_resp.text,
            read_obs=root_obs
        )
        findings.extend(extract_findings)
        
        extract_observations: List[Dict[str, Any]] = [self._serialize_extract_obs(root_extract_obs)]
        
        # Analyze representative pages
        for page_url in representative_pages:
            if page_url == target_resp.final_url or page_url == target_url:
                continue
                
            page_resp = self.http_client.cache.get(page_url)
            if page_resp and page_resp.is_success and page_resp.text:
                rep_read_obs = PageTextExtractor.analyze(page_resp.text, page_url)
                rep_extract_findings, rep_extract_obs = extract_inspector.inspect_page(
                    url=page_url,
                    html_content=page_resp.text,
                    read_obs=rep_read_obs
                )
                findings.extend(rep_extract_findings)
                extract_observations.append(self._serialize_extract_obs(rep_extract_obs))
                
        self.extract_metadata = {
            "root_observation": extract_observations[0] if extract_observations else {},
            "all_observations": extract_observations,
            "pages_analyzed": len(extract_observations),
        }

        # -------------------------------------------------------------
        # 8. UNDERSTAND STAGE: Page Structure & Subject Analysis
        # -------------------------------------------------------------
        understand_inspector = UnderstandInspector(self.factory)
        
        # Analyze root page
        understand_findings, root_understand_obs = understand_inspector.inspect_page(
            url=target_resp.final_url,
            html_content=target_resp.text,
            read_obs=root_obs,
            extract_obs=root_extract_obs
        )
        findings.extend(understand_findings)
        
        understand_observations: List[Dict[str, Any]] = [root_understand_obs.to_dict()]
        
        # We need to map rep_read_obs and rep_extract_obs for secondary pages
        # The easiest way is to re-run or cache them. We already iterate over them in EXTRACT stage.
        # Let's adjust the loop below instead of doing it here, or we can just iterate again and fetch from cache.
        # Wait, since the Extract stage loops and creates rep_extract_obs, maybe it's better to store them in a dictionary
        # or do a separate loop here.
        
        for page_url in representative_pages:
            if page_url == target_resp.final_url or page_url == target_url:
                continue
                
            page_resp = self.http_client.cache.get(page_url)
            if page_resp and page_resp.is_success and page_resp.text:
                rep_read_obs = PageTextExtractor.analyze(page_resp.text, page_url)
                # Re-run extract_inspector quickly to get the obs (or we could have stored it).
                # Since it's local HTML parsing, it's very fast.
                _, rep_extract_obs = extract_inspector.inspect_page(
                    url=page_url,
                    html_content=page_resp.text,
                    read_obs=rep_read_obs
                )
                
                rep_understand_findings, rep_understand_obs = understand_inspector.inspect_page(
                    url=page_url,
                    html_content=page_resp.text,
                    read_obs=rep_read_obs,
                    extract_obs=rep_extract_obs
                )
                findings.extend(rep_understand_findings)
                understand_observations.append(rep_understand_obs.to_dict())

        self.understand_metadata = {
            "root_observation": understand_observations[0] if understand_observations else {},
            "all_observations": understand_observations,
            "pages_analyzed": len(understand_observations),
        }

        # -------------------------------------------------------------
        # 9. IDENTIFY STAGE: Entity & Brand Consistency
        # -------------------------------------------------------------
        identify_inspector = IdentifyInspector(self.factory)
        
        identify_findings, root_identify_obs = identify_inspector.inspect_page(
            url=target_resp.final_url,
            read_obs=root_obs,
            extract_obs=root_extract_obs
        )
        findings.extend(identify_findings)
        
        identify_observations_raw: List[IdentifyObservation] = [root_identify_obs]
        identify_observations: List[Dict[str, Any]] = [root_identify_obs.to_dict()]
        
        for page_url in representative_pages:
            if page_url == target_resp.final_url or page_url == target_url:
                continue
                
            page_resp = self.http_client.cache.get(page_url)
            if page_resp and page_resp.is_success and page_resp.text:
                rep_read_obs = PageTextExtractor.analyze(page_resp.text, page_url)
                _, rep_extract_obs = extract_inspector.inspect_page(
                    url=page_url,
                    html_content=page_resp.text,
                    read_obs=rep_read_obs
                )
                
                rep_identify_findings, rep_identify_obs = identify_inspector.inspect_page(
                    url=page_url,
                    read_obs=rep_read_obs,
                    extract_obs=rep_extract_obs
                )
                findings.extend(rep_identify_findings)
                identify_observations_raw.append(rep_identify_obs)
                identify_observations.append(rep_identify_obs.to_dict())

        self.identify_metadata = {
            "root_observation": identify_observations[0] if identify_observations else {},
            "all_observations": identify_observations,
            "pages_analyzed": len(identify_observations),
        }

        # -------------------------------------------------------------
        # 10. TRUST STAGE: Security, Freshness, Transparency, Corroboration
        # -------------------------------------------------------------
        trust_inspector = TrustInspector(self.factory)
        
        trust_observations: List[TrustObservation] = []
        
        # Root page
        trust_findings, root_trust_obs = trust_inspector.inspect_page(
            url=target_resp.final_url,
            html_content=target_resp.text,
            headers=target_resp.headers,
            is_https=target_resp.is_https,
            read_obs=root_obs,
            extract_obs=root_extract_obs,
            identify_obs=root_identify_obs,
            existing_findings=findings
        )
        findings.extend(trust_findings)
        trust_observations.append(root_trust_obs)
        
        # Representative pages
        rep_idx = 1
        for page_url in representative_pages:
            if page_url == target_resp.final_url or page_url == target_url:
                continue
                
            page_resp = self.http_client.cache.get(page_url)
            if page_resp and page_resp.is_success and page_resp.text:
                rep_read_obs = PageTextExtractor.analyze(page_resp.text, page_url)
                _, rep_extract_obs = extract_inspector.inspect_page(
                    url=page_url,
                    html_content=page_resp.text,
                    read_obs=rep_read_obs
                )
                _, rep_identify_obs = identify_inspector.inspect_page(
                    url=page_url,
                    read_obs=rep_read_obs,
                    extract_obs=rep_extract_obs
                )
                
                rep_trust_findings, rep_trust_obs = trust_inspector.inspect_page(
                    url=page_url,
                    html_content=page_resp.text,
                    headers=page_resp.headers,
                    is_https=page_resp.is_https,
                    read_obs=rep_read_obs,
                    extract_obs=rep_extract_obs,
                    identify_obs=rep_identify_obs,
                    existing_findings=findings
                )
                findings.extend(rep_trust_findings)
                trust_observations.append(rep_trust_obs)
                rep_idx += 1

        # Evaluate cross-page Trust
        cross_page_trust_findings = trust_inspector.evaluate_cross_page(
            observations=trust_observations,
            identify_observations=identify_observations_raw
        )
        findings.extend(cross_page_trust_findings)

        self.trust_metadata = {
            "root_observation": trust_observations[0].to_dict() if trust_observations else {},
            "all_observations": [obs.to_dict() for obs in trust_observations],
            "pages_analyzed": len(trust_observations),
        }

        # -------------------------------------------------------------
        # 11. Capture Crawl Metadata (Separated from findings)
        # -------------------------------------------------------------
        self.crawl_metadata = {
            "requested_url": target_url,
            "final_url": target_resp.final_url,
            "status_code": target_resp.status_code,
            "redirect_count": target_resp.redirect_count,
            "redirect_chain": target_resp.redirect_chain,
            "content_type": target_resp.content_type,
            "content_length": target_resp.content_length,
            "is_https": target_resp.is_https,
            "robots_status": robots_resp.status_code,
            "robots_sitemaps_count": len(robots_report.sitemaps),
            "sitemaps_evaluated": [s.url for s in sitemap_results],
            "total_links_found": link_data["total_links_found"],
            "unique_internal_links": link_data["unique_internal_count"],
            "representative_pages_checked": len(representative_pages),
            "initial_content_signal": root_obs.initial_content_signal,
            "text_to_html_ratio": root_obs.text_to_html_ratio,
            "visible_text_chars": root_obs.visible_text_chars,
        }

        return {
            "skill": "ai-discoverability",
            "status": "success",
            "findings": findings,
            "error": None,
            "limitations": limitations,
        }


def audit_discoverability(site: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Canonical public entrypoint for the AI Discoverability module.
    Accepts target website URL and optional crawl configurations.
    Returns orchestrator-compatible module payload dictionary.
    """
    auditor = DiscoverabilityAuditor(options=options)
    return auditor.audit(site)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "skill": "ai-discoverability",
            "status": "failure",
            "findings": [],
            "error": "Usage: python audit_discoverability.py <url> [--json]",
            "limitations": [],
        }, indent=2))
        sys.exit(1)

    target_site = sys.argv[1]
    result = audit_discoverability(target_site)
    print(json.dumps(result, indent=2))
