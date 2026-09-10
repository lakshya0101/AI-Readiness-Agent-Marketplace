import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Set

from .finding_factory import FindingFactory
from .html_reader import ReadObservation
from .extract_inspector import ExtractObservation

@dataclass
class UnderstandObservation:
    url: str
    headings: Dict[str, Any] = field(default_factory=dict)
    subject_signals: Dict[str, Any] = field(default_factory=dict)
    content_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class UnderstandInspector:
    def __init__(self, finding_factory: FindingFactory):
        self.finding_factory = finding_factory
        # Pre-compile common separators and punctuation for normalization
        self.norm_re = re.compile(r"[^a-z0-9\s]")
        
    def _normalize_text(self, text: str) -> Set[str]:
        if not text:
            return set()
        clean = self.norm_re.sub(" ", text.lower())
        words = set(w for w in clean.split() if len(w) > 2 and w not in {"the", "and", "for", "with", "from", "that", "this", "page", "home"})
        return words

    def inspect_page(
        self,
        url: str,
        html_content: str,
        read_obs: ReadObservation,
        extract_obs: ExtractObservation
    ) -> Tuple[List[Dict[str, Any]], UnderstandObservation]:
        
        findings: List[Dict[str, Any]] = []
        
        # 1. Heading Analysis
        headings = read_obs.headings
        h1_values = [text for tag, text in headings if tag == "h1"]
        h_counts = {f"h{i}": 0 for i in range(1, 7)}
        empty_heading_count = 0
        skipped_levels = []
        
        last_level = 0
        duplicate_counts: Dict[str, int] = {}
        
        for tag, text in headings:
            h_counts[tag] += 1
            
            clean_text = text.strip()
            # empty or punctuation only
            if not clean_text or not re.search(r'[a-zA-Z0-9]', clean_text):
                empty_heading_count += 1
            else:
                duplicate_counts[clean_text] = duplicate_counts.get(clean_text, 0) + 1
                
            level = int(tag[1])
            if (last_level > 0 and level > last_level + 1) or (last_level == 0 and level > 1):
                skipped_levels.append(f"h{last_level}->h{level}" if last_level > 0 else f"root->h{level}")
            last_level = level
            
        headings_obs = {
            "sequence": [tag for tag, text in headings],
            "counts": {k: v for k, v in h_counts.items() if v > 0},
            "h1_values": h1_values,
            "empty_heading_count": empty_heading_count,
            "skipped_levels": skipped_levels
        }

        # 2. Subject Signals
        title = read_obs.title or ""
        first_h1 = h1_values[0] if h1_values else ""
        og_title = extract_obs.opengraph.get("og:title", [""])[0] if "og:title" in extract_obs.opengraph else ""
        schema_names = list(extract_obs.types_found)
        
        title_words = self._normalize_text(title)
        h1_words = self._normalize_text(first_h1)
        og_words = self._normalize_text(og_title)
        
        signals_present = sum(1 for w in [title_words, h1_words, og_words] if w)
        
        consistency = "consistent"
        if signals_present == 0:
            consistency = "insufficient"
        elif signals_present == 3:
            t_h1 = bool(title_words.intersection(h1_words))
            t_og = bool(title_words.intersection(og_words))
            h1_og = bool(h1_words.intersection(og_words))
            
            # If two match but the third contradicts completely
            if (t_og and not t_h1 and not h1_og):
                consistency = "strongly_conflicting"
            elif (t_h1 and not t_og and not h1_og):
                consistency = "strongly_conflicting"
            elif (h1_og and not t_h1 and not t_og):
                consistency = "strongly_conflicting"
            # If none of them match
            elif not t_h1 and not t_og and not h1_og:
                consistency = "strongly_conflicting"
            else:
                consistency = "potentially_mixed"
        elif signals_present == 2:
            t_h1 = bool(title_words.intersection(h1_words)) if title_words and h1_words else False
            t_og = bool(title_words.intersection(og_words)) if title_words and og_words else False
            h1_og = bool(h1_words.intersection(og_words)) if h1_words and og_words else False
            if not t_h1 and not t_og and not h1_og:
                consistency = "potentially_mixed"
        
        subject_signals = {
            "title": title,
            "h1": first_h1,
            "og_title": og_title,
            "schema_names": schema_names,
            "consistency": consistency
        }

        # 3. Content Context
        list_item_count = len(re.findall(r'<li', html_content, re.IGNORECASE))
        table_count = len(re.findall(r'<table', html_content, re.IGNORECASE))
        link_count = len(re.findall(r'<a', html_content, re.IGNORECASE))
        
        visible_text_chars = read_obs.visible_text_chars
        paragraph_count = read_obs.paragraph_count
        
        primary_subject_context = "substantial"
        if visible_text_chars < 150:
            if paragraph_count == 0 and list_item_count == 0 and table_count == 0:
                primary_subject_context = "insufficient"
            else:
                primary_subject_context = "limited"
        elif visible_text_chars < 400 and paragraph_count == 0 and list_item_count == 0 and table_count == 0:
            primary_subject_context = "limited"
            
        content_context = {
            "visible_text_chars": visible_text_chars,
            "paragraph_count": paragraph_count,
            "list_item_count": list_item_count,
            "table_count": table_count,
            "link_count": link_count,
            "primary_subject_context": primary_subject_context
        }

        obs = UnderstandObservation(
            url=url,
            headings=headings_obs,
            subject_signals=subject_signals,
            content_context=content_context
        )

# FINDINGS GENERATION (Strictly Conservative)
        
        # A. Primary Page Subject Is Not Clearly Exposed
        if consistency == "insufficient" and not schema_names and h_counts["h2"] == 0:
            findings.append(self.finding_factory.create_finding(
                subcategory="page_subject",
                title="Primary Page Subject Is Not Clearly Exposed",
                severity="medium",
                evidence=f"At {url}, Title, H1, and OpenGraph tags are all absent or empty. No strong fallback schema or H2 exists.",
                why_it_matters="Automated systems cannot identify what this page is about without clear subject signals.",
                suggested_action_summary="Add a descriptive title and H1",
                suggested_action_details="Provide a clear <title> and <h1> that describe the page subject.",
                methodology="Understand"
            ))
        elif consistency == "strongly_conflicting":
             findings.append(self.finding_factory.create_finding(
                subcategory="page_subject",
                title="Primary Page Subject Signals are Strongly Conflicting",
                severity="medium",
                evidence=f"At {url}, multiple primary signals contradict. Title: '{title}', H1: '{first_h1}', OG Title: '{og_title}'.",
                why_it_matters="Conflicting signals can cause search engines and AI to misunderstand the page's primary topic.",
                suggested_action_summary="Align Title, H1, and OG Title",
                suggested_action_details="Ensure the <title>, <h1>, and OpenGraph title express a consistent primary subject.",
                methodology="Understand"
            ))
            
        # B. Heading Hierarchy Is Structurally Ambiguous
        # Only flag if there are multiple skips AND no H1 AND the content isn't clearly just a small component
        if len(skipped_levels) > 1 and h_counts["h1"] == 0 and visible_text_chars > 300:
            findings.append(self.finding_factory.create_finding(
                subcategory="heading_structure",
                title="Heading Hierarchy Is Structurally Ambiguous",
                severity="low",
                evidence=f"At {url}, multiple skipped heading levels ({', '.join(skipped_levels)}) and no H1 present.",
                why_it_matters="A chaotic heading structure breaks content outlining for screen readers and AI parsers.",
                suggested_action_summary="Fix heading hierarchy",
                suggested_action_details="Ensure headings increment by one level at a time.",
                methodology="Understand"
            ))
            
        # C. Primary Heading Is Missing or Uninformative
        if h_counts["h1"] == 0 and not title_words and visible_text_chars > 300 and h_counts["h2"] == 0 and not schema_names:
            findings.append(self.finding_factory.create_finding(
                subcategory="heading_structure",
                title="Primary Heading Is Missing or Uninformative",
                severity="medium",
                evidence=f"At {url}, no H1 or H2 headings found on a page with substantive text, and no title or schema.",
                why_it_matters="Without primary headings, the document lacks a structural entry point.",
                suggested_action_summary="Add a primary heading",
                suggested_action_details="Include a descriptive <h1> summarizing the page.",
                methodology="Understand"
            ))
            
        # D. Important Subject Has Insufficient Textual Context
        if primary_subject_context == "insufficient" and (schema_names or first_h1):
            findings.append(self.finding_factory.create_finding(
                subcategory="content_context",
                title="Important Subject Has Insufficient Textual Context",
                severity="low",
                evidence=f"At {url}, page declares subject ('{first_h1 or schema_names[0]}') but provides almost no visible paragraphs, lists, or tables ({visible_text_chars} chars).",
                why_it_matters="AI systems cannot extract definitions or relationships if the page has insufficient explanatory text.",
                suggested_action_summary="Add descriptive content",
                suggested_action_details="Provide substantive paragraph text explaining the product, service, or concept.",
                methodology="Understand"
            ))
            
        # E. Repetitive Heading Structure Creates Ambiguity
        repetitive = [k for k, v in duplicate_counts.items() if v >= 5 and len(k) > 3]
        if repetitive and len(headings) > 0:
            # Only flag if a single repetitive heading dominates >50% of the page structure without a clear H1
            if h_counts["h1"] == 0 and duplicate_counts[repetitive[0]] > len(headings) * 0.5:
                findings.append(self.finding_factory.create_finding(
                    subcategory="semantic_coherence",
                    title="Repetitive Heading Structure Creates Ambiguity",
                    severity="low",
                    evidence=f"At {url}, heading '{repetitive[0]}' repeats {duplicate_counts[repetitive[0]]} times without a clear primary H1.",
                    why_it_matters="Excessively repetitive identical headings provide no differentiation for machine reading.",
                    suggested_action_summary="Differentiate heading titles",
                    suggested_action_details="Make section headings unique and descriptive.",
                    methodology="Understand"
                ))
                
        # Empty headings Check
        if empty_heading_count > 0 and empty_heading_count > len(headings) * 0.5 and len(headings) > 2:
             findings.append(self.finding_factory.create_finding(
                subcategory="heading_structure",
                title="Substantial Number of Empty Headings Detected",
                severity="low",
                evidence=f"At {url}, {empty_heading_count} out of {len(headings)} headings are empty or punctuation-only.",
                why_it_matters="Empty headings break the structural outline.",
                suggested_action_summary="Remove empty headings",
                suggested_action_details="Remove heading tags that contain no text.",
                methodology="Understand"
            ))

        return findings, obs
        return findings, obs
