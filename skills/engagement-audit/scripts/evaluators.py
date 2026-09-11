from html.parser import HTMLParser
from typing import List, Dict, Optional
from urllib.parse import urlparse
from .models import Finding, SuggestedAction

class StructuredPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.h1s = []
        self.headings = []
        self.nav_count = 0
        self.links = []
        self.footer_count = 0
        self.header_count = 0
        self.buttons = 0
        self.forms = 0
        self.meta_tags = []
        self.time_tags = 0
        self.text_content = []
        self.breadcrumbs = False
        
        self._current_tag = []
        self._in_title = False
        self._in_h1 = False
        self._in_nav = False
        self._in_header = False
        self._ignore_text_tags = {"script", "style", "noscript"}
        self._in_ignore_text = 0
        
        # Link text extraction
        self._current_link = None

    def handle_starttag(self, tag, attrs):
        self._current_tag.append(tag)
        attr_dict = dict(attrs)
        
        if tag in self._ignore_text_tags:
            self._in_ignore_text += 1
            
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            self.headings.append(tag)
        elif tag == "nav":
            self.nav_count += 1
            self._in_nav = True
            aria_label = attr_dict.get("aria-label", "").lower()
            class_name = attr_dict.get("class", "").lower()
            if "breadcrumb" in aria_label or "breadcrumb" in class_name:
                self.breadcrumbs = True
        elif tag == "header":
            self.header_count += 1
            self._in_header = True
        elif tag == "footer":
            self.footer_count += 1
        elif tag == "a":
            href = attr_dict.get("href", "")
            class_name = attr_dict.get("class", "").lower()
            self._current_link = {"href": href, "in_nav": self._in_nav, "in_header": self._in_header, "class": class_name, "text": ""}
            if "btn" in class_name or "button" in class_name:
                self.buttons += 1
        elif tag == "button":
            self.buttons += 1
        elif tag == "form":
            self.forms += 1
        elif tag == "meta":
            self.meta_tags.append(attr_dict)
        elif tag == "time":
            self.time_tags += 1

    def handle_endtag(self, tag):
        if self._current_tag and self._current_tag[-1] == tag:
            self._current_tag.pop()
            
        if tag in self._ignore_text_tags:
            self._in_ignore_text = max(0, self._in_ignore_text - 1)
        
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "nav":
            self._in_nav = False
        elif tag == "header":
            self._in_header = False
        elif tag == "a" and self._current_link is not None:
            self.links.append(self._current_link)
            self._current_link = None

    def handle_data(self, data):
        if self._in_ignore_text > 0:
            return
            
        text = data.strip()
        if not text:
            return
            
        if self._in_title:
            self.title += text
        elif self._in_h1:
            self.h1s.append(text)
        else:
            if self._current_link is not None:
                self._current_link["text"] += text + " "
                
            if len(" ".join(self.text_content)) < 500 and not self._in_nav and not self._in_header:
                self.text_content.append(text)

class EngagementEvaluator:
    def __init__(self, url: str, html: str, entry_type: str, page_type: str):
        self.url = url
        self.html = html
        self.entry_type = entry_type
        self.page_type = page_type.lower() if page_type else self._infer_page_type(url, html)
        
        # Origin for home link logic
        parsed_url = urlparse(url)
        self.origin = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.netloc else ""
        
        self.parser = StructuredPageParser()
        if self.html:
            self.parser.feed(self.html)
            
    def _infer_page_type(self, url: str, html: str) -> str:
        url_lower = url.lower()
        if "/doc" in url_lower or "docs." in url_lower:
            return "documentation"
        if "/blog" in url_lower or "/news" in url_lower or "/article" in url_lower:
            return "article/news"
        if "/pricing" in url_lower:
            return "pricing"
        if "/product" in url_lower or "/item" in url_lower or "/p/" in url_lower:
            return "product"
        if "/contact" in url_lower or "/services" in url_lower:
            return "service"
        if "/about" in url_lower or "/corporate" in url_lower:
            return "corporate/about"
        if "/legal" in url_lower or "/privacy" in url_lower or "/terms" in url_lower:
            return "informational/legal"
        if url.rstrip("/").count("/") <= 2:
            return "landing"
        return "other"
        
    def _is_home_link(self, href: str) -> bool:
        if href == "/":
            return True
        if self.origin and (href == self.origin or href == self.origin + "/"):
            return True
        return False

    def evaluate(self) -> List[Finding]:
        findings = []
        
        # 1. Landing Experience
        f = self._evaluate_landing_experience()
        if f: findings.append(f)
            
        # 2. Information Orientation
        f = self._evaluate_information_orientation()
        if f: findings.append(f)
            
        # 3. Context Retention (Deep Entry)
        f = self._evaluate_deep_entry()
        if f: findings.append(f)
            
        # 4. Navigation
        f = self._evaluate_navigation()
        if f: findings.append(f)
            
        # 5. Meaningful Next Action
        f = self._evaluate_next_actions()
        if f: findings.append(f)
            
        return findings

    def _evaluate_landing_experience(self) -> Optional[Finding]:
        has_h1 = len(self.parser.h1s) > 0
        has_title = bool(self.parser.title.strip())
        intro_text = " ".join(self.parser.text_content)
        has_meaningful_intro = len(intro_text) > 30

        if not has_h1 and not has_title and not has_meaningful_intro:
            return Finding(
                id="ENG-101",
                category="engagement",
                subcategory="landing",
                title="Unclear page purpose and missing structural headings",
                severity="high",
                evidence="The page contains 0 <h1> tags, an empty <title>, and no substantive introductory text.",
                why_it_matters="Without a clear primary heading or title, users cannot determine the page's core purpose immediately upon arrival.",
                suggested_action=SuggestedAction(
                    summary="Add a descriptive <h1> and <title>",
                    details="Implement a clear <h1> tag and an informative <title> that summarize the value proposition or content of the page.",
                    priority="high"
                )
            )
        return None

    def _evaluate_information_orientation(self) -> Optional[Finding]:
        if self.page_type == "article/news":
            has_time = self.parser.time_tags > 0
            has_author = any("author" in str(m).lower() for m in self.parser.meta_tags)
            
            if not has_time and not has_author:
                return Finding(
                    id="ENG-201",
                    category="engagement",
                    subcategory="orientation",
                    title="Missing standard article metadata",
                    severity="low",
                    evidence="The article/news page lacks <time> tags and author meta tags.",
                    why_it_matters="Readers of news and articles rely on publication dates and author info to judge timeliness and credibility.",
                    suggested_action=SuggestedAction(
                        summary="Include publication date and author",
                        details="Add a <time> element for the publish date and standard meta tags for the author.",
                        priority="low"
                    )
                )
        elif self.page_type == "documentation":
            # For docs, check if there is structural orientation
            has_nav = self.parser.nav_count > 0
            has_breadcrumbs = self.parser.breadcrumbs
            has_links = len(self.parser.links) > 0
            
            if not has_nav and not has_breadcrumbs and not has_links:
                return Finding(
                    id="ENG-202",
                    category="engagement",
                    subcategory="orientation",
                    title="Missing documentation structure and hierarchy",
                    severity="medium",
                    evidence="The documentation page contains 0 navigation blocks, 0 breadcrumbs, and 0 internal links.",
                    why_it_matters="A documentation page without structural links prevents users from understanding where the topic fits within the broader guide or finding related sections.",
                    suggested_action=SuggestedAction(
                        summary="Add documentation hierarchy",
                        details="Include a side navigation menu, breadcrumbs, or 'next/previous' links to orient the user.",
                        priority="medium"
                    )
                )
        return None

    def _evaluate_deep_entry(self) -> Optional[Finding]:
        if self.entry_type != "deep":
            return None
            
        has_nav = self.parser.nav_count > 0 or self.parser.header_count > 0
        has_breadcrumbs = self.parser.breadcrumbs
        has_home_link = any(self._is_home_link(l["href"]) for l in self.parser.links)
        
        if not has_nav and not has_breadcrumbs and not has_home_link:
            return Finding(
                id="ENG-301",
                category="engagement",
                subcategory="deep-entry",
                title="Total loss of site context on deep entry",
                severity="critical",
                evidence="The deep page contains 0 global navigation links, 0 breadcrumbs, and no visible links to the site root/home.",
                why_it_matters="A first-time visitor arriving directly via an AI recommendation cannot identify the brand or navigate to the rest of the site.",
                suggested_action=SuggestedAction(
                    summary="Implement global navigation and brand context",
                    details="Add a persistent header with a link to the homepage and basic site navigation, or include breadcrumbs indicating the page's position in the site hierarchy.",
                    priority="critical"
                )
            )
        return None

    def _evaluate_navigation(self) -> Optional[Finding]:
        if self.page_type in ["informational/legal"]:
            return None
            
        total_links = len(self.parser.links)
        nav_elements = self.parser.nav_count
        header_footer = self.parser.header_count + self.parser.footer_count
        
        if total_links < 2 and nav_elements == 0 and header_footer == 0:
            return Finding(
                id="ENG-401",
                category="engagement",
                subcategory="navigation",
                title="Severe lack of exploratory navigation",
                severity="high",
                evidence=f"The {self.page_type} page contains 0 <nav> elements, 0 headers/footers, and fewer than 2 total links.",
                why_it_matters="Users are effectively trapped on this page with no structural pathways to explore the broader website.",
                suggested_action=SuggestedAction(
                    summary="Add site navigation structure",
                    details="Provide header navigation, footer links, or contextual related links to allow users to explore the site.",
                    priority="high"
                )
            )
        return None

    def _evaluate_next_actions(self) -> Optional[Finding]:
        if self.page_type in ["informational/legal", "corporate/about", "other"]:
            return None
            
        action_verbs = {"buy", "purchase", "order", "demo", "request", "contact", 
                       "sign up", "signup", "start", "trial", "get started", 
                       "subscribe", "book", "enquire", "inquire"}
                       
        has_button_element = self.parser.buttons > 0
        has_form = self.parser.forms > 0
        
        has_action_link = False
        for link in self.parser.links:
            text_lower = link.get("text", "").lower()
            if any(verb in text_lower for verb in action_verbs):
                has_action_link = True
                break
                
        has_cta = has_button_element or has_form or has_action_link
        
        if not has_cta:
            if self.page_type == "product":
                return Finding(
                    id="ENG-501",
                    category="engagement",
                    subcategory="actionability",
                    title="Missing purchase/demo action on product page",
                    severity="high",
                    evidence="The product page contains 0 buttons, 0 forms, and 0 links with purchase/demo action text.",
                    why_it_matters="Visitors learning about a product have no clear pathway to acquire it, request a demo, or take a meaningful next step.",
                    suggested_action=SuggestedAction(
                        summary="Add a clear call-to-action",
                        details="Include a prominent button or link (e.g., 'Buy Now', 'Request Demo') that guides the user to the next stage.",
                        priority="high"
                    )
                )
            elif self.page_type in ["service", "pricing"]:
                return Finding(
                    id="ENG-502",
                    category="engagement",
                    subcategory="actionability",
                    title=f"Missing action on {self.page_type} page",
                    severity="high",
                    evidence=f"The {self.page_type} page contains 0 buttons, 0 forms, and 0 links with contact/signup action text.",
                    why_it_matters="Visitors interested in the offering have no structured way to initiate a request or signup.",
                    suggested_action=SuggestedAction(
                        summary="Add a contact form or signup button",
                        details="Provide a clear CTA leading to a contact form or signup page.",
                        priority="high"
                    )
                )
        return None
