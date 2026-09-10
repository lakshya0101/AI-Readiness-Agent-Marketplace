"""Read Inspector: Analyzes HTML extractability and client-side rendering dependencies."""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from .finding_factory import FindingFactory
from .html_reader import ReadObservation


class ReadInspector:
    """Evaluates page extractability and non-rendered reader accessibility."""

    @classmethod
    def evaluate_page(
        cls,
        observation: ReadObservation,
        factory: FindingFactory,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates a ReadObservation for meaningful server-rendered content absence.
        Applies conservative multi-factor thresholds to prevent false positives.
        """
        findings: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # FALSE-POSITIVE GUARDS:
        # If page already has substantial or moderate text with structure,
        # never flag client-side rendering dependency regardless of script tags.
        # -------------------------------------------------------------
        if observation.visible_text_chars >= 600:
            return []

        if observation.visible_text_chars >= 350 and (observation.h1_count >= 1 or observation.paragraph_count >= 2):
            return []

        # -------------------------------------------------------------
        # MULTI-FACTOR SIGNAL EVALUATION
        # -------------------------------------------------------------
        url = observation.url
        html_bytes = observation.html_bytes
        text_chars = observation.visible_text_chars
        ratio_pct = round(observation.text_to_html_ratio * 100, 2)

        # Factor A: Empty or near-empty application shell container
        spa_container_empty = (
            observation.spa_container_id is not None
            and observation.spa_container_text_chars < 50
        )

        # Factor B: Prominent script footprint
        script_heavy = observation.script_count >= 3 or observation.inline_script_bytes > 5000

        # Factor C: Complete absence of content structure
        no_structure = observation.h1_count == 0 and observation.paragraph_count == 0

        # Factor D: Explicit loading / noscript placeholder
        has_placeholder = observation.has_loading_indicator or observation.has_noscript_warning

        # -------------------------------------------------------------
        # POSITIVE CASE 1: Severe Client-Side Rendering Dependency (HIGH)
        # Empty shell, minimal text (< 250 chars), and multiple corroborating signals
        # -------------------------------------------------------------
        supporting_signals = sum([
            1 if spa_container_empty else 0,
            1 if script_heavy else 0,
            1 if no_structure else 0,
            1 if has_placeholder else 0,
        ])

        if text_chars < 250 and supporting_signals >= 2:
            evidence_parts = [
                f"Initial HTML for {url} contained {html_bytes:,} bytes but only {text_chars} characters of visible text (text-to-code ratio: {ratio_pct}%).",
            ]
            if spa_container_empty:
                evidence_parts.append(
                    f"The primary application container '#{observation.spa_container_id}' contained {observation.spa_container_text_chars} text characters."
                )
            if observation.script_count > 0:
                evidence_parts.append(f"{observation.script_count} script resources were referenced.")
            if no_structure:
                evidence_parts.append("Zero H1 headings or paragraphs were identified in the initial HTML.")
            if observation.has_loading_indicator:
                evidence_parts.append(f"Found loading placeholder: '{observation.loading_indicator_text}'.")
            if observation.has_noscript_warning:
                evidence_parts.append("Found noscript message indicating JavaScript is required to view content.")

            findings.append(factory.create_finding(
                subcategory="rendering_dependency",
                title="Primary Page Content Largely Unavailable in Initial HTML (Client-Side Rendering Dependency)",
                severity="high",
                evidence=" ".join(evidence_parts),
                why_it_matters=(
                    "Non-rendering AI search indexers, automated scrapers, and LLM assistant retrieval engines parse raw "
                    "server-rendered HTML without executing client JavaScript. When primary content relies entirely on client-side "
                    "DOM rendering, machine readers observe an empty shell and cannot discover, index, or cite site information."
                ),
                suggested_action_summary="Implement Server-Side Rendering (SSR) or Static Pre-rendering",
                suggested_action_details=(
                    f"Configure your frontend framework (e.g. Next.js, Nuxt, Remix) for Server-Side Rendering (SSR) or Static Site "
                    f"Generation (SSG) so that primary headlines, descriptive copy, and semantic containers on {url} are populated "
                    f"directly in the initial HTTP response."
                ),
                suggested_action_priority="high",
                affected_pages=[url],
                evidence_type="HTML_DOM",
                methodology="Read",
                remediation_complexity="medium",
            ))
            return findings

        # -------------------------------------------------------------
        # POSITIVE CASE 2: Low Server-Rendered Text Payload (MEDIUM)
        # Moderate text deficit with heavy script ratio and lack of structure
        # -------------------------------------------------------------
        if text_chars < 450 and observation.text_to_html_ratio < 0.015 and observation.script_count >= 6 and (observation.h1_count == 0 or observation.paragraph_count <= 1):
            findings.append(factory.create_finding(
                subcategory="server_rendered_content",
                title="Low Server-Rendered Text Payload with High Script Ratio",
                severity="medium",
                evidence=(
                    f"Initial HTML for {url} contained {html_bytes:,} bytes with only {text_chars} characters of visible text "
                    f"(ratio: {ratio_pct}%). Found {observation.script_count} script resources alongside {observation.h1_count} H1 headings "
                    f"and {observation.paragraph_count} paragraph(s), indicating significant content is deferred to client-side scripts."
                ),
                why_it_matters=(
                    "AI systems extracting facts and summary passages require substantive server-rendered textual copy. "
                    "Sparse initial HTML forces AI search engines to rely on incomplete snippets or abandon extraction."
                ),
                suggested_action_summary="Pre-render primary descriptive content in initial HTML",
                suggested_action_details=(
                    f"Ensure essential value propositions, article summaries, and core product descriptions on {url} are embedded "
                    f"directly in the server-delivered HTML payload."
                ),
                suggested_action_priority="medium",
                affected_pages=[url],
                evidence_type="HTML_DOM",
                methodology="Read",
                remediation_complexity="low",
            ))

        return findings
