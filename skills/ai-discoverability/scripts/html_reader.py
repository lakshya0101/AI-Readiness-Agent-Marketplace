"""HTML Text and Structural Content Extractor for the Read Audit Stage.

Extracts visible text, structural elements (headings, paragraphs, titles),
application root containers, script counts, and computes text-to-code signals.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from html.parser import HTMLParser
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Tags whose inner content is invisible or non-textual
IGNORE_TAGS = {"script", "style", "noscript", "template", "svg", "canvas", "video", "audio", "iframe"}

# Common SPA container IDs and attributes
SPA_CONTAINER_IDS = {"root", "app", "__next", "main-app", "app-root"}

LOADING_PATTERNS = [
    re.compile(r"\bloading\b(?:\s*\.{3})?", re.IGNORECASE),
    re.compile(r"\bplease wait\b", re.IGNORECASE),
    re.compile(r"\binitializing\b", re.IGNORECASE),
    re.compile(r"\benable javascript\b", re.IGNORECASE),
    re.compile(r"\byou need to enable javascript\b", re.IGNORECASE),
]


@dataclass
class ReadObservation:
    """Structured deterministic observations extracted from initial HTML."""

    url: str
    html_bytes: int
    visible_text_chars: int
    text_to_html_ratio: float
    title: str = ""
    heading_count: int = 0
    h1_count: int = 0
    headings: List[Tuple[str, str]] = field(default_factory=list)
    paragraph_count: int = 0
    paragraphs: List[str] = field(default_factory=list)
    script_count: int = 0
    external_script_count: int = 0
    inline_script_bytes: int = 0
    spa_container_id: Optional[str] = None
    spa_container_text_chars: int = 0
    has_loading_indicator: bool = False
    loading_indicator_text: Optional[str] = None
    has_noscript_warning: bool = False
    initial_content_signal: str = "moderate"  # minimal, low, moderate, substantial
    rendered_dom_comparison: Optional[Dict[str, Any]] = None  # Hook for future rendering stage

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["headings_summary"] = [f"{tag.upper()}: {txt[:40]}" for tag, txt in self.headings[:5]]
        return d


class _HTMLReadParser(HTMLParser):
    """Parses visible text and structural elements while excluding non-textual nodes."""

    def __init__(self):
        super().__init__()
        self.title_parts: List[str] = []
        self.in_title = False

        self.visible_text_parts: List[str] = []
        self.ignore_tag_stack: List[str] = []

        self.current_heading_tag: Optional[str] = None
        self.current_heading_parts: List[str] = []
        self.headings: List[Tuple[str, str]] = []

        self.current_p_parts: List[str] = []
        self.in_paragraph = False
        self.paragraphs: List[str] = []

        self.scripts: List[Dict[str, Any]] = []
        self.in_script = False
        self.current_script_parts: List[str] = []

        self.in_noscript = False
        self.noscript_parts: List[str] = []

        # SPA container tracking
        self.spa_container_id: Optional[str] = None
        self.spa_container_depth = 0
        self.spa_text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        tag_lower = tag.lower()
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}

        # Check for hidden elements via style or attribute
        style = attrs_dict.get("style", "").lower()
        is_hidden = (
            "display:none" in style
            or "display: none" in style
            or "visibility:hidden" in style
            or "visibility: hidden" in style
            or "hidden" in attrs_dict
        )

        if tag_lower in IGNORE_TAGS or is_hidden:
            self.ignore_tag_stack.append(tag_lower)

        if tag_lower == "title":
            self.in_title = True

        elif tag_lower == "script":
            self.in_script = True
            src = attrs_dict.get("src", "").strip()
            script_type = attrs_dict.get("type", "").strip()
            self.scripts.append({"src": src, "type": script_type})

        elif tag_lower == "noscript":
            self.in_noscript = True

        elif tag_lower in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.current_heading_tag = tag_lower
            self.current_heading_parts = []

        elif tag_lower == "p":
            self.in_paragraph = True
            self.current_p_parts = []

        # Detect SPA container
        elem_id = attrs_dict.get("id", "").strip().lower()
        if self.spa_container_id is None and elem_id in SPA_CONTAINER_IDS:
            self.spa_container_id = attrs_dict.get("id", "").strip()
            self.spa_container_depth = 1
        elif self.spa_container_id is not None:
            self.spa_container_depth += 1

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()

        if tag_lower == "title":
            self.in_title = False

        elif tag_lower == "script":
            self.in_script = False

        elif tag_lower == "noscript":
            self.in_noscript = False

        elif tag_lower in {"h1", "h2", "h3", "h4", "h5", "h6"} and self.current_heading_tag == tag_lower:
            h_text = " ".join("".join(self.current_heading_parts).split())
            if h_text:
                self.headings.append((self.current_heading_tag, h_text))
            self.current_heading_tag = None
            self.current_heading_parts = []

        elif tag_lower == "p" and self.in_paragraph:
            self.in_paragraph = False
            p_text = " ".join("".join(self.current_p_parts).split())
            if p_text:
                self.paragraphs.append(p_text)
            self.current_p_parts = []

        # End SPA container tracking
        if self.spa_container_id is not None:
            self.spa_container_depth -= 1

        # Pop from ignore tag stack
        if self.ignore_tag_stack and self.ignore_tag_stack[-1] == tag_lower:
            self.ignore_tag_stack.pop()

    def handle_data(self, data: str):
        if self.in_title:
            self.title_parts.append(data)

        if self.in_script:
            self.current_script_parts.append(data)

        if self.in_noscript:
            self.noscript_parts.append(data)

        if not self.ignore_tag_stack:
            clean_data = data.strip()
            if clean_data:
                self.visible_text_parts.append(clean_data)

            if self.current_heading_tag is not None:
                self.current_heading_parts.append(data)

            if self.in_paragraph:
                self.current_p_parts.append(data)

            if self.spa_container_id is not None and self.spa_container_depth > 0:
                if clean_data:
                    self.spa_text_parts.append(clean_data)


class PageTextExtractor:
    """Extracts structured text observations and signals from raw HTML."""

    @classmethod
    def analyze(cls, html: str, page_url: str) -> ReadObservation:
        """Parses HTML and computes deterministic read observations."""
        if not html:
            return ReadObservation(
                url=page_url,
                html_bytes=0,
                visible_text_chars=0,
                text_to_html_ratio=0.0,
                initial_content_signal="minimal",
            )

        html_bytes = len(html.encode("utf-8", errors="replace"))

        parser = _HTMLReadParser()
        try:
            parser.feed(html)
        except Exception:
            pass

        title = " ".join("".join(parser.title_parts).split())
        visible_text = " ".join(parser.visible_text_parts)
        visible_chars = len(visible_text)

        ratio = (visible_chars / html_bytes) if html_bytes > 0 else 0.0

        h1_count = sum(1 for tag, _ in parser.headings if tag == "h1")
        heading_count = len(parser.headings)
        paragraph_count = len(parser.paragraphs)

        script_count = len(parser.scripts)
        ext_script_count = sum(1 for s in parser.scripts if s.get("src"))
        inline_script_bytes = sum(len(s.encode("utf-8")) for s in parser.current_script_parts)

        spa_container_id = parser.spa_container_id
        spa_text = " ".join(parser.spa_text_parts)
        spa_text_chars = len(spa_text)

        # Loading indicator check
        has_loading = False
        loading_text = None
        for pattern in LOADING_PATTERNS:
            match = pattern.search(visible_text)
            if match:
                has_loading = True
                loading_text = match.group(0)
                break

        # Noscript warning check
        noscript_text = " ".join(parser.noscript_parts).lower()
        has_noscript_warning = "enable javascript" in noscript_text or "javascript is required" in noscript_text

        # Classify content signal
        if visible_chars >= 1000 and (heading_count >= 1 or paragraph_count >= 2):
            signal = "substantial"
        elif visible_chars >= 350 and (heading_count >= 1 or paragraph_count >= 1):
            signal = "moderate"
        elif visible_chars >= 150:
            signal = "low"
        else:
            signal = "minimal"

        return ReadObservation(
            url=page_url,
            html_bytes=html_bytes,
            visible_text_chars=visible_chars,
            text_to_html_ratio=round(ratio, 4),
            title=title,
            heading_count=heading_count,
            h1_count=h1_count,
            headings=parser.headings,
            paragraph_count=paragraph_count,
            paragraphs=parser.paragraphs,
            script_count=script_count,
            external_script_count=ext_script_count,
            inline_script_bytes=inline_script_bytes,
            spa_container_id=spa_container_id,
            spa_container_text_chars=spa_text_chars,
            has_loading_indicator=has_loading,
            loading_indicator_text=loading_text,
            has_noscript_warning=has_noscript_warning,
            initial_content_signal=signal,
            rendered_dom_comparison=None,
        )
