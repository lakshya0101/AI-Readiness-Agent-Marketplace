"""Robots.txt parser and evaluator for AI crawler accessibility."""

from __future__ import annotations
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

AI_USER_AGENTS = [
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "anthropic-ai",
    "PerplexityBot",
    "CCBot",
    "Google-Extended",
    "Bytespider",
    "Applebot-Extended",
    "Amazonbot",
]


class RobotsRule:
    """Represents a single Allow or Disallow rule."""

    def __init__(self, rule_type: str, path: str, line_number: int = 0):
        self.rule_type = rule_type.lower()  # 'allow' or 'disallow'
        self.path = path.strip()
        self.line_number = line_number

    def matches(self, target_path: str) -> bool:
        """Determines whether rule path prefix matches target path."""
        if not self.path:
            return False
        # Normalize trailing wildcard if present
        clean_path = self.path
        if clean_path.endswith("*"):
            clean_path = clean_path[:-1]
        return target_path.startswith(clean_path)

    @property
    def length(self) -> int:
        return len(self.path)


class RobotsGroup:
    """Represents a User-agent group containing directives."""

    def __init__(self):
        self.user_agents: List[str] = []
        self.rules: List[RobotsRule] = []

    def applies_to(self, bot_name: str) -> bool:
        bot_lower = bot_name.lower()
        for ua in self.user_agents:
            ua_lower = ua.lower()
            if ua_lower == bot_lower or (ua_lower != "*" and ua_lower in bot_lower):
                return True
        return False

    def is_wildcard(self) -> bool:
        return any(ua.strip() == "*" for ua in self.user_agents)

    def is_allowed(self, target_path: str) -> Tuple[bool, Optional[RobotsRule]]:
        """
        Evaluates path against group rules using longest-match specificity (RFC 9309).
        If matching Allow and Disallow have equal length, Allow takes precedence.
        Returns (is_allowed, matched_rule).
        """
        matching_rules: List[RobotsRule] = [r for r in self.rules if r.matches(target_path)]
        if not matching_rules:
            # Default to allowed if no rule matches
            return True, None

        # Sort by longest path length descending; for ties, allow takes precedence
        def sort_key(r: RobotsRule):
            is_allow_val = 1 if r.rule_type == "allow" else 0
            return (r.length, is_allow_val)

        best_rule = max(matching_rules, key=sort_key)
        if best_rule.rule_type == "allow":
            return True, best_rule
        else:
            return False, best_rule


class RobotsReport:
    """Structured inspection results from robots.txt."""

    def __init__(
        self,
        url: str,
        status_code: int,
        raw_text: str,
        groups: List[RobotsGroup],
        sitemaps: List[str],
        error: Optional[str] = None,
    ):
        self.url = url
        self.status_code = status_code
        self.raw_text = raw_text
        self.groups = groups
        self.sitemaps = sitemaps
        self.error = error

    def evaluate_bot(self, bot_name: str, path: str = "/") -> Tuple[bool, Optional[str], Optional[RobotsRule]]:
        """
        Evaluates whether a specific bot is allowed on path.
        Returns (is_allowed, matched_user_agent_group_name, matched_rule).
        """
        # 1. Search for specific group matching bot_name
        for group in self.groups:
            if not group.is_wildcard() and group.applies_to(bot_name):
                allowed, rule = group.is_allowed(path)
                return allowed, ", ".join(group.user_agents), rule

        # 2. Fallback to wildcard group
        for group in self.groups:
            if group.is_wildcard():
                allowed, rule = group.is_allowed(path)
                return allowed, "*", rule

        # 3. No matching group -> allowed by default
        return True, None, None


class RobotsInspector:
    """Inspects and parses robots.txt with RFC 9309 group semantics."""

    @classmethod
    def parse(cls, url: str, status_code: int, text: str, error: Optional[str] = None) -> RobotsReport:
        groups: List[RobotsGroup] = []
        sitemaps: List[str] = []

        if status_code != 200 or not text.strip():
            return RobotsReport(
                url=url,
                status_code=status_code,
                raw_text=text,
                groups=[],
                sitemaps=[],
                error=error or (f"HTTP {status_code}" if status_code != 200 else "Empty robots.txt"),
            )

        current_group: Optional[RobotsGroup] = None
        in_user_agent_declarations = False

        for idx, line in enumerate(text.splitlines(), start=1):
            # Strip comments and whitespace
            clean = line.split("#")[0].strip()
            if not clean:
                continue

            if ":" not in clean:
                continue

            directive, value = clean.split(":", 1)
            directive = directive.strip().lower()
            value = value.strip()

            if directive == "sitemap":
                if value and value not in sitemaps:
                    sitemaps.append(value)
                continue

            if directive == "user-agent":
                if not in_user_agent_declarations or current_group is None:
                    # Start a new group
                    current_group = RobotsGroup()
                    groups.append(current_group)
                    in_user_agent_declarations = True
                if value:
                    current_group.user_agents.append(value)

            elif directive in {"disallow", "allow"}:
                in_user_agent_declarations = False
                if current_group is not None:
                    if not value:
                        # Empty Disallow: indicates allow all
                        if directive == "disallow":
                            current_group.rules.append(RobotsRule("allow", "/", line_number=idx))
                    else:
                        current_group.rules.append(RobotsRule(directive, value, line_number=idx))

        return RobotsReport(
            url=url,
            status_code=status_code,
            raw_text=text,
            groups=groups,
            sitemaps=sitemaps,
            error=None,
        )

    @classmethod
    def audit_ai_restrictions(cls, report: RobotsReport, path: str = "/") -> List[Dict[str, Any]]:
        """
        Analyzes robots report for meaningful AI crawler restrictions.
        Returns diagnostic descriptions of blocked bots.
        """
        if report.status_code != 200:
            return []

        blocked_records: List[Dict[str, Any]] = []

        # Check wildcard first
        wildcard_allowed, wc_agent, wc_rule = report.evaluate_bot("*", path=path)
        is_wildcard_blocked = not wildcard_allowed

        for bot in AI_USER_AGENTS:
            allowed, agent_group, matched_rule = report.evaluate_bot(bot, path=path)
            if not allowed:
                rule_desc = f"{matched_rule.rule_type.upper()}: {matched_rule.path}" if matched_rule else "Disallow: /"
                blocked_records.append({
                    "bot": bot,
                    "group": agent_group or bot,
                    "rule": rule_desc,
                    "path": matched_rule.path if matched_rule else path,
                    "is_wildcard": agent_group == "*",
                })

        return blocked_records
