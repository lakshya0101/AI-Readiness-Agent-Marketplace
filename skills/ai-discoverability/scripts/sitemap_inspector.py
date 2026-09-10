"""Sitemap discovery and XML structure validator."""

from __future__ import annotations
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .http_client import HttpClient, HttpResponse


class SitemapResult:
    """Encapsulates inspection results for a sitemap endpoint."""

    def __init__(
        self,
        url: str,
        status_code: int,
        content_type: str,
        is_advertised_in_robots: bool,
        is_valid_xml: bool = False,
        is_sitemap_index: bool = False,
        url_count: int = 0,
        sub_sitemaps_count: int = 0,
        sample_urls: Optional[List[str]] = None,
        parse_error: Optional[str] = None,
        fetch_error: Optional[str] = None,
    ):
        self.url = url
        self.status_code = status_code
        self.content_type = content_type
        self.is_advertised_in_robots = is_advertised_in_robots
        self.is_valid_xml = is_valid_xml
        self.is_sitemap_index = is_sitemap_index
        self.url_count = url_count
        self.sub_sitemaps_count = sub_sitemaps_count
        self.sample_urls = sample_urls or []
        self.parse_error = parse_error
        self.fetch_error = fetch_error


class SitemapInspector:
    """Discovers and inspects sitemap XML endpoints."""

    def __init__(self, http_client: HttpClient):
        self.http_client = http_client

    def inspect_sitemap(self, sitemap_url: str, is_advertised: bool) -> SitemapResult:
        """Fetches and parses a candidate sitemap URL."""
        resp: HttpResponse = self.http_client.fetch(sitemap_url)

        if not resp.is_success:
            return SitemapResult(
                url=sitemap_url,
                status_code=resp.status_code,
                content_type=resp.content_type,
                is_advertised_in_robots=is_advertised,
                is_valid_xml=False,
                fetch_error=resp.error or f"HTTP {resp.status_code}",
            )

        # Parse XML
        raw_xml = resp.body.strip()
        if not raw_xml:
            return SitemapResult(
                url=sitemap_url,
                status_code=resp.status_code,
                content_type=resp.content_type,
                is_advertised_in_robots=is_advertised,
                is_valid_xml=False,
                parse_error="Empty sitemap response body.",
            )

        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError as pe:
            return SitemapResult(
                url=sitemap_url,
                status_code=resp.status_code,
                content_type=resp.content_type,
                is_advertised_in_robots=is_advertised,
                is_valid_xml=False,
                parse_error=f"Malformed XML syntax: {str(pe)}",
            )
        except Exception as ex:
            return SitemapResult(
                url=sitemap_url,
                status_code=resp.status_code,
                content_type=resp.content_type,
                is_advertised_in_robots=is_advertised,
                is_valid_xml=False,
                parse_error=f"XML parsing error: {str(ex)}",
            )

        # Strip XML namespaces for tag matching
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        is_index = tag.lower() == "sitemapindex"

        urls: List[str] = []
        sub_sitemaps: List[str] = []

        for elem in root.iter():
            elem_tag = elem.tag.split("}")[-1].lower()
            if elem_tag == "loc" and elem.text and elem.text.strip():
                loc_val = elem.text.strip()
                if is_index:
                    sub_sitemaps.append(loc_val)
                else:
                    urls.append(loc_val)

        return SitemapResult(
            url=sitemap_url,
            status_code=resp.status_code,
            content_type=resp.content_type,
            is_advertised_in_robots=is_advertised,
            is_valid_xml=True,
            is_sitemap_index=is_index,
            url_count=len(urls),
            sub_sitemaps_count=len(sub_sitemaps),
            sample_urls=(sub_sitemaps[:5] if is_index else urls[:5]),
            parse_error=None,
        )

    def discover(self, base_url: str, robots_sitemaps: List[str]) -> List[SitemapResult]:
        """
        Discovers and inspects sitemaps from robots.txt directives and default sitemap.xml.
        """
        results: List[SitemapResult] = []
        candidate_urls: Dict[str, bool] = {}  # url -> is_advertised

        # 1. Add sitemaps declared in robots.txt
        for r_sitemap in robots_sitemaps:
            clean = r_sitemap.strip()
            if clean and clean.startswith(("http://", "https://")):
                candidate_urls[clean] = True

        # 2. Add default /sitemap.xml if not already listed
        default_sitemap = f"{base_url.rstrip('/')}/sitemap.xml"
        if default_sitemap not in candidate_urls:
            candidate_urls[default_sitemap] = False

        for url, is_adv in candidate_urls.items():
            results.append(self.inspect_sitemap(url, is_advertised=is_adv))

        return results
