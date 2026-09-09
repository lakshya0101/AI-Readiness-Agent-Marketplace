"""HTML Link extractor and representative page selector."""

from __future__ import annotations
from html.parser import HTMLParser
import re
import urllib.parse
from typing import Dict, List, Set, Tuple

# Path segment keywords to prioritize for representative crawl
PRIORITY_KEYWORDS = [
    "about",
    "company",
    "product",
    "service",
    "solution",
    "feature",
    "pricing",
    "doc",
    "guide",
    "blog",
    "overview",
    "team",
    "contact",
]

# Extensions/patterns to exclude from page reachability crawl
EXCLUDE_EXTENSIONS = {
    ".pdf", ".zip", ".tar", ".gz", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".mp4", ".mp3", ".wav", ".avi",
    ".css", ".js", ".json", ".xml",
}

EXCLUDE_PATTERNS = [
    r"/login",
    r"/signin",
    r"/signup",
    r"/register",
    r"/logout",
    r"/cart",
    r"/checkout",
    r"/account",
    r"/admin",
    r"/wp-admin",
]


class _AnchorParser(HTMLParser):
    """Parses <a> anchor tags from HTML."""

    def __init__(self):
        super().__init__()
        self.raw_hrefs: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        if tag.lower() == "a":
            attrs_dict = {k.lower(): (v or "") for k, v in attrs}
            href = attrs_dict.get("href", "").strip()
            if href:
                self.raw_hrefs.append(href)


class LinkExtractor:
    """Extracts, normalizes, and categorizes internal links from HTML."""

    @classmethod
    def extract_links(cls, html: str, page_url: str) -> Dict[str, Any]:
        """
        Extracts all anchor hrefs, normalizing relative links to page_url.
        Categorizes into internal same-origin links and external links.
        """
        parser = _AnchorParser()
        try:
            parser.feed(html)
        except Exception:
            pass

        parsed_base = urllib.parse.urlparse(page_url)
        base_origin = f"{parsed_base.scheme.lower()}://{parsed_base.netloc.lower()}"

        all_links_count = len(parser.raw_hrefs)
        internal_links_set: Set[str] = set()
        external_links_set: Set[str] = set()

        for href in parser.raw_hrefs:
            # Skip non-navigational links
            if href.startswith(("#", "javascript:", "mailto:", "tel:", "data:", "sms:")):
                continue

            # Resolve relative URLs
            try:
                resolved = urllib.parse.urljoin(page_url, href)
                parsed_res = urllib.parse.urlparse(resolved)
            except Exception:
                continue

            if parsed_res.scheme.lower() not in {"http", "https"}:
                continue

            # Clean URL: strip fragment and trailing slash normalization
            clean_path = parsed_res.path.rstrip("/") if parsed_res.path != "/" else "/"
            clean_url = urllib.parse.urlunparse((
                parsed_res.scheme.lower(),
                parsed_res.netloc.lower(),
                clean_path,
                "",  # params
                parsed_res.query,
                "",  # fragment
            ))

            target_origin = f"{parsed_res.scheme.lower()}://{parsed_res.netloc.lower()}"
            if target_origin == base_origin:
                internal_links_set.add(clean_url)
            else:
                external_links_set.add(clean_url)

        return {
            "total_links_found": all_links_count,
            "unique_internal_count": len(internal_links_set),
            "unique_external_count": len(external_links_set),
            "internal_links": sorted(list(internal_links_set)),
            "external_links": sorted(list(external_links_set)),
        }

    @classmethod
    def select_representative_pages(
        cls,
        internal_links: List[str],
        root_url: str,
        max_pages: int = 5,
    ) -> List[str]:
        """
        Selects a bounded set of representative internal URLs for reachability testing.
        Prioritizes high-value informative content over deep/utility links.
        """
        parsed_root = urllib.parse.urlparse(root_url)
        clean_root_path = parsed_root.path.rstrip("/") if parsed_root.path != "/" else "/"
        clean_root = urllib.parse.urlunparse((
            parsed_root.scheme.lower(),
            parsed_root.netloc.lower(),
            clean_root_path,
            "", "", "",
        ))

        # Always include root as first page
        selected: List[str] = [clean_root]
        if max_pages <= 1:
            return selected

        candidates: List[Tuple[int, str]] = []

        for link in internal_links:
            if link == clean_root:
                continue

            parsed = urllib.parse.urlparse(link)
            path_lower = parsed.path.lower()

            # Skip excluded extensions
            if any(path_lower.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                continue

            # Skip excluded paths
            if any(re.search(pat, path_lower) for pat in EXCLUDE_PATTERNS):
                continue

            # Score candidates based on informative value
            score = 10
            # Path depth penalty (shallow pages preferred for representative sampling)
            segments = [s for s in parsed.path.split("/") if s]
            score -= len(segments)

            # Keyword bonus
            for kw in PRIORITY_KEYWORDS:
                if kw in path_lower:
                    score += 15
                    break

            candidates.append((score, link))

        # Sort by score descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        for _, link in candidates:
            if link not in selected:
                selected.append(link)
                if len(selected) >= max_pages:
                    break

        return selected
