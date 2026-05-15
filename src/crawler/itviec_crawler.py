"""
ITviec.com crawler — AI/Data jobs in Vietnam.

Selectors verified against ITviec HTML structure (May 2026).
If the site redesigns, inspect the following elements:
  - Job listing card:  div.job-card  →  a[href] inside
  - Job title:         h1.job-title  or  h1[class*='job-title']
  - Company:           a.employer-name  or  div[class*='employer'] a
  - Location:          svg[class*='location'] + span  or  div.address
  - Salary:            div.salary-period  or  span[class*='salary']
  - Skills/tags:       a.tag  or  span.tag
  - Description:       div.job-description  or  div#job-description
"""
import logging
import re
import time
from typing import Iterator

from src.crawler.base_crawler import BaseCrawler
from src.crawler.utils import (
    parse_html,
    strip_html,
    extract_salary_numbers,
    normalize_url,
    safe_get,
)

logger = logging.getLogger(__name__)


class ITviecCrawler(BaseCrawler):
    source_name = "itviec"
    base_url = "https://itviec.com"

    # Expanded search categories for 10K dataset target.
    # AI/Data categories first (primary focus), then all IT roles.
    SEARCH_URLS = [
        # ── AI / Data / ML (primary) ─────────────────────────────────────────
        "https://itviec.com/it-jobs/ai-engineer",
        "https://itviec.com/it-jobs/data-scientist",
        "https://itviec.com/it-jobs/data-analyst",
        "https://itviec.com/it-jobs/data-engineer",
        "https://itviec.com/it-jobs/machine-learning-engineer",
        "https://itviec.com/it-jobs/nlp-engineer",
        "https://itviec.com/it-jobs/computer-vision",
        "https://itviec.com/it-jobs/mlops-engineer",
        "https://itviec.com/it-jobs/business-intelligence",
        "https://itviec.com/it-jobs/big-data",
        "https://itviec.com/it-jobs/llm",
        "https://itviec.com/it-jobs/deep-learning",
        "https://itviec.com/it-jobs/data-warehouse",
        "https://itviec.com/it-jobs/analytics",
        # ── Backend ──────────────────────────────────────────────────────────
        "https://itviec.com/it-jobs/backend",
        "https://itviec.com/it-jobs/java",
        "https://itviec.com/it-jobs/python",
        "https://itviec.com/it-jobs/nodejs",
        "https://itviec.com/it-jobs/php",
        "https://itviec.com/it-jobs/net",
        "https://itviec.com/it-jobs/golang",
        "https://itviec.com/it-jobs/ruby",
        "https://itviec.com/it-jobs/software-engineer",
        "https://itviec.com/it-jobs/spring",
        "https://itviec.com/it-jobs/microservices",
        "https://itviec.com/it-jobs/scala",
        "https://itviec.com/it-jobs/c-plus-plus",
        # ── Frontend / Mobile ────────────────────────────────────────────────
        "https://itviec.com/it-jobs/frontend",
        "https://itviec.com/it-jobs/react",
        "https://itviec.com/it-jobs/javascript",
        "https://itviec.com/it-jobs/html5",
        "https://itviec.com/it-jobs/android",
        "https://itviec.com/it-jobs/ios",
        "https://itviec.com/it-jobs/mobile-apps",
        "https://itviec.com/it-jobs/flutter",
        "https://itviec.com/it-jobs/react-native",
        "https://itviec.com/it-jobs/angular",
        "https://itviec.com/it-jobs/vuejs",
        # ── DevOps / Cloud ───────────────────────────────────────────────────
        "https://itviec.com/it-jobs/devops",
        "https://itviec.com/it-jobs/aws",
        "https://itviec.com/it-jobs/linux",
        "https://itviec.com/it-jobs/database",
        "https://itviec.com/it-jobs/kubernetes",
        "https://itviec.com/it-jobs/docker",
        "https://itviec.com/it-jobs/cloud",
        # ── QA / Security / Other ────────────────────────────────────────────
        "https://itviec.com/it-jobs/tester",
        "https://itviec.com/it-jobs/qa-qc",
        "https://itviec.com/it-jobs/manager",
        "https://itviec.com/it-jobs/business-analyst",
        "https://itviec.com/it-jobs/sql",
        "https://itviec.com/it-jobs/mysql",
        "https://itviec.com/it-jobs/security",
        "https://itviec.com/it-jobs/blockchain",
        "https://itviec.com/it-jobs/embedded",
        "https://itviec.com/it-jobs/solution-architect",
        "https://itviec.com/it-jobs/product-manager",
        "https://itviec.com/it-jobs/scrum",
        "https://itviec.com/it-jobs/agile",
        "https://itviec.com/it-jobs/react-native",
        "https://itviec.com/it-jobs/vuejs",
        "https://itviec.com/it-jobs/typescript",
        "https://itviec.com/it-jobs/unity",
        "https://itviec.com/it-jobs/game",
        "https://itviec.com/it-jobs/erp",
        "https://itviec.com/it-jobs/salesforce",
        "https://itviec.com/it-jobs/bi",
        "https://itviec.com/it-jobs/tableau",
        "https://itviec.com/it-jobs/power-bi",
        # ── Location-based (catches jobs not in keyword searches) ─────────────
        "https://itviec.com/it-jobs/ho-chi-minh-city",
        "https://itviec.com/it-jobs/ha-noi",
        "https://itviec.com/it-jobs/da-nang",
        "https://itviec.com/it-jobs/remote",
    ]

    # ── URL iteration ─────────────────────────────────────────────────────────

    def iter_job_urls(self) -> Iterator[str]:
        from config import MAX_PAGES_PER_SOURCE

        seen_urls: set[str] = set()

        for search_url in self.SEARCH_URLS:
            logger.info(f"[itviec] Scanning: {search_url}")

            for page in range(1, MAX_PAGES_PER_SOURCE + 1):
                page_url = f"{search_url}?page={page}" if page > 1 else search_url
                response = safe_get(self.session, page_url)

                if response is None:
                    logger.warning(f"[itviec] No response for page {page} of {search_url}")
                    break

                soup = parse_html(response.text)
                job_links = self._extract_job_links(soup)

                if not job_links:
                    logger.info(f"[itviec] No more jobs on page {page} of {search_url}")
                    break

                new_links = [lnk for lnk in job_links if lnk not in seen_urls]
                if not new_links:
                    break   # all links seen → pagination exhausted

                for lnk in new_links:
                    seen_urls.add(lnk)
                    yield lnk

                time.sleep(self.delay)

    def _extract_job_links(self, soup) -> list[str]:
        """
        Extract absolute job detail URLs from a listing page.

        ITviec uses Stimulus.js — job cards are clickable divs, NOT <a> tags.
        The job slug is embedded in the data attribute:
            data-search--job-selection-job-slug-value="senior-data-scientist-..."
        We construct: https://itviec.com/it-jobs/{slug}

        Fallback: parse slug from /sign_in?job=<slug> links inside each card.
        """
        from urllib.parse import urlparse, parse_qs

        links: list[str] = []

        # Strategy 1 (primary): slug from data attribute on div.job-card
        for card in soup.select("div.job-card"):
            slug = card.get("data-search--job-selection-job-slug-value", "")
            if slug:
                links.append(f"{self.base_url}/it-jobs/{slug}")

        # Strategy 2 (fallback): extract slug from sign_in?job= link inside each card
        if not links:
            for card in soup.select("div.job-card"):
                sign_in = card.find("a", href=re.compile(r"/sign_in\?job="))
                if sign_in:
                    parsed = urlparse(sign_in["href"])
                    params = parse_qs(parsed.query)
                    slug = params.get("job", [None])[0]
                    if slug:
                        links.append(f"{self.base_url}/it-jobs/{slug}")

        # Strategy 3 (legacy fallback): any /it-jobs/<slug> href with 2+ path parts
        if not links:
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if re.match(r"^/it-jobs/[^/?#]+-\d+$", href):
                    links.append(normalize_url(self.base_url, href))

        return links

    # ── Job page parsing ──────────────────────────────────────────────────────

    def parse_job_page(self, url: str, html: str) -> dict:
        soup = parse_html(html)

        # ── Primary: JSON-LD JobPosting structured data ───────────────────────
        ld = self._extract_jsonld(soup)
        if ld:
            return self._parse_from_jsonld(url, ld, soup)

        # ── Fallback: DOM parsing (no JSON-LD available) ──────────────────────
        return self._parse_from_dom(url, soup)

    def _extract_jsonld(self, soup) -> dict:
        """Return parsed JSON-LD JobPosting dict, or empty dict if not found."""
        import json as _json
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = _json.loads(script.string or "{}")
                if data.get("@type") == "JobPosting":
                    return data
            except (ValueError, AttributeError):
                pass
        return {}

    def _parse_from_jsonld(self, url: str, ld: dict, soup) -> dict:
        """
        Build job record primarily from JSON-LD structured data.
        Falls back to DOM for fields not covered by JSON-LD.
        """
        # ── Salary ────────────────────────────────────────────────────────────
        base_salary = ld.get("baseSalary", {})
        sal_value   = base_salary.get("value", {})
        sal_min_raw = sal_value.get("minValue")
        sal_max_raw = sal_value.get("maxValue")
        currency    = base_salary.get("currency", "")
        salary_str  = sal_value.get("value", "")

        # If salary not in JSON-LD, try DOM
        if not salary_str:
            salary_str = self._get_salary_text(soup)

        sal_min = float(sal_min_raw) if sal_min_raw is not None else None
        sal_max = float(sal_max_raw) if sal_max_raw is not None else None

        if sal_min is None and salary_str:
            sal_min, sal_max, currency = extract_salary_numbers(salary_str)

        # ── Company ───────────────────────────────────────────────────────────
        company = (
            ld.get("hiringOrganization", {}).get("name", "")
            or self._get_company(soup)
        )

        # ── Location ──────────────────────────────────────────────────────────
        locations = ld.get("jobLocation", [])
        if isinstance(locations, dict):
            locations = [locations]
        city_parts = []
        for loc in locations:
            addr = loc.get("address", {})
            region   = (addr.get("addressRegion") or "").strip()
            locality = (addr.get("addressLocality") or "").strip()
            part = region or locality
            if part and part.lower() not in ("not available", ""):
                city_parts.append(part)
        location = ", ".join(city_parts) or self._get_location(soup)

        # ── Employment type ───────────────────────────────────────────────────
        emp_raw  = _to_str(ld.get("employmentType", ""))
        emp_type = emp_raw.replace("_", " ").title() if emp_raw else self._get_employment_type(soup)

        # ── Skills ────────────────────────────────────────────────────────────
        skills_str = _to_str(ld.get("skills", ""))
        if skills_str:
            skills = [s.strip() for s in skills_str.split(",") if s.strip()]
        else:
            skills = self._get_skills(soup)

        # ── Description ───────────────────────────────────────────────────────
        desc = strip_html(_to_str(ld.get("description", ""))) or self._get_description(soup)

        # ── Dates (exact ISO strings from JSON-LD) ────────────────────────────
        date_posted   = _to_str(ld.get("datePosted", ""))    # e.g. "2026-05-04"
        valid_through = _to_str(ld.get("validThrough", ""))   # e.g. "2026-06-08"

        # ── Experience ────────────────────────────────────────────────────────
        # Source: ONLY the description text visible to users on the job page.
        #
        # ITviec's JSON-LD monthsOfExperience is an internal categorisation
        # field (e.g. 37 → "about 3 years", 10 → "fresher") that is NOT visible
        # on the page and does NOT reflect the actual employer requirement.
        # Using it produces false values (e.g. 3.1 years for a job with no stated
        # experience requirement). experience_years = None is the honest value
        # when the job description does not explicitly mention years.
        exp_yrs = _parse_experience_years(self._get_experience_text(soup))

        # ── Benefits ─────────────────────────────────────────────────────────
        benefits = strip_html(_to_str(ld.get("jobBenefits", ""))) or self._get_benefits(soup)

        # ── Job level (not in JSON-LD, infer from DOM/title) ──────────────────
        level = self._get_job_level(soup)

        raw_title = _to_str(ld.get("title", "")) or self._get_title(soup)
        return {
            "url":             url,
            "job_title":       _clean_title(raw_title),
            "company_name":    company,
            "salary":          salary_str,
            "salary_min":      sal_min,
            "salary_max":      sal_max,
            "salary_currency": currency,
            "location":        location,
            "employment_type": emp_type,
            "job_level":       level,
            "skills_required": skills,
            "experience_years": exp_yrs,
            "experience_level": "",
            "job_description": desc,
            "benefits":        benefits[:500],
            "posted_date":     date_posted,
            "expiry_date":     valid_through,
            "industry":        ld.get("industry", "IT / Technology"),
            "job_type":        emp_type or "Full-time",
        }

    def _parse_from_dom(self, url: str, soup) -> dict:
        """Pure DOM fallback when no JSON-LD is available."""
        salary   = self._get_salary_text(soup)
        emp_type = self._get_employment_type(soup)
        exp_text = self._get_experience_text(soup)
        sal_min, sal_max, currency = extract_salary_numbers(salary)

        return {
            "url":             url,
            "job_title":       self._get_title(soup),
            "company_name":    self._get_company(soup),
            "salary":          salary,
            "salary_min":      sal_min,
            "salary_max":      sal_max,
            "salary_currency": currency,
            "location":        self._get_location(soup),
            "employment_type": emp_type,
            "job_level":       self._get_job_level(soup),
            "skills_required": self._get_skills(soup),
            "experience_years": _parse_experience_years(exp_text),
            "experience_level": "",
            "job_description": self._get_description(soup),
            "benefits":        self._get_benefits(soup),
            "posted_date":     self._get_posted_date(soup),
            "expiry_date":     "",
            "industry":        "IT / Technology",
            "job_type":        emp_type or "Full-time",
        }

    # ── Field-level extractors ─────────────────────────────────────────────────

    def _get_title(self, soup) -> str:
        for sel in ["h1.job-title", "h1[class*='title']", "h1"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(strip=True)
        return ""

    def _get_company(self, soup) -> str:
        # ITviec: company name is direct text of div.employer-name (no <a> inside)
        el = soup.select_one("div.employer-name")
        if el:
            return el.get_text(strip=True)
        return ""

    def _get_location(self, soup) -> str:
        # Location is in span.normal-text inside div.job-show-info
        info = soup.select_one("div.job-show-info")
        if info:
            el = info.select_one("span.normal-text")
            if el:
                return el.get_text(strip=True)
        return ""

    def _get_salary_text(self, soup) -> str:
        # Salary is hidden behind login on many ITviec jobs
        for sel in ["div[class*='salary']", "span[class*='salary']"]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                # "Sign in to view salary" → treat as negotiable
                if "sign in" not in text.lower():
                    return text
        return ""

    def _get_description(self, soup) -> str:
        """
        Extract job_description = 'Job description' + 'Your skills and experience' sections.
        Excludes 'Why you'll love working here' (→ benefits).
        Excludes 'Top 3 Reasons to Join Us' (brief marketing copy).
        """
        content = soup.select_one("section.job-content, div.jd-main")
        if not content:
            return ""

        # Section headings to exclude from job_description
        BENEFITS_HEADINGS = {
            "why you'll love working here",
            "why you will love working here",
            "tại sao bạn sẽ yêu thích",
            "phúc lợi",
            "benefits",
            "welfare",
        }
        SKIP_HEADINGS = {
            "top 3 reasons to join us",
            "top 3 lý do",
            "3 lý do",
        }

        desc_parts: list[str] = []
        # Walk through block-level elements in the content section
        for el in content.find_all(["h2", "h3", "p", "ul", "ol", "li", "div"], recursive=False):
            heading_text = el.get_text(strip=True).lower()[:80]

            # Skip marketing / benefits headings
            if el.name in ("h2", "h3"):
                if any(kw in heading_text for kw in BENEFITS_HEADINGS | SKIP_HEADINGS):
                    continue

            desc_parts.append(el.get_text(" ", strip=True))

        text = " ".join(desc_parts).strip()
        # Fall back to full section if section-splitting produced empty result
        return text or strip_html(str(content))

    def _get_skills(self, soup) -> list[str]:
        """
        Extract THIS job's skill tags from div.job-show-info.
        ITviec puts skill tags in: div.job-show-info > ... > div.d-flex.flex-wrap > a[class*='itag']
        The first such flex-wrap div contains the primary skills.
        """
        info = soup.select_one("div.job-show-info")
        if not info:
            return []

        # Find the first flex-wrap div — contains this job's skills
        flex_wrap = info.select_one("div.d-flex.flex-wrap")
        if flex_wrap:
            tags = [
                a.get_text(strip=True)
                for a in flex_wrap.select("a[class*='itag']")
                if a.get_text(strip=True) and len(a.get_text(strip=True)) <= 60
            ]
            if tags:
                return tags[:20]

        # Fallback: all itag links in job-show-info (before related jobs)
        return [
            a.get_text(strip=True)
            for a in info.select("a[class*='itag itag-light']")
            if a.get_text(strip=True) and len(a.get_text(strip=True)) <= 60
        ][:15]

    def _get_job_level(self, soup) -> str:
        # Infer from h1 title keywords
        title_el = soup.select_one("h1")
        if title_el:
            title = title_el.get_text(strip=True).lower()
            for level, keywords in [
                ("Lead",   ["lead", "manager", "director", "head of"]),
                ("Senior", ["senior", "sr.", "principal"]),
                ("Junior", ["junior", "jr.", "fresher", "entry"]),
                ("Intern", ["intern", "internship", "thực tập"]),
            ]:
                if any(kw in title for kw in keywords):
                    return level
        return "Mid-level"

    def _get_employment_type(self, soup) -> str:
        # Parse "At office" / "Remote" / "Hybrid" from job-show-info text
        info = soup.select_one("div.job-show-info")
        if info:
            text = info.get_text(" ", strip=True).lower()
            if "remote" in text:
                return "Remote"
            if "hybrid" in text:
                return "Hybrid"
            if "at office" in text or "onsite" in text:
                return "On-site"
        for sel in ["span[class*='job-type']", "div[class*='job-type']"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(strip=True)
        return "Full-time"

    def _get_posted_date(self, soup) -> str:
        """
        Extract raw posted_date string for date_utils to parse.

        ITviec uses relative time only: '1 day ago', '3 days ago', '1 week ago'.
        No machine-readable datetime attribute is available.
        Returns the relative string as-is; date_utils.parse_relative_date() handles it.
        """
        info = soup.select_one("div.job-show-info")
        if info:
            text = info.get_text(" ", strip=True)
            # Pattern: "Posted\n1 day ago Skills:" or "Posted 3 days ago"
            match = re.search(
                r"Posted\s+(\d+\s+(?:day|days|week|weeks|month|months)\s+ago"
                r"|today|yesterday|just now|hôm nay|hôm qua|\d+\s+ngày\s+trước"
                r"|\d+\s+tuần\s+trước|\d+\s+tháng\s+trước)",
                text, re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()
            # Fallback: grab everything after "Posted" up to next keyword
            fallback = re.search(r"Posted\s+(.+?)(?:\s+Skills|\s+Job Expertise|\s+Job Domain|$)", text)
            if fallback:
                raw = fallback.group(1).strip()[:40]   # cap length
                return raw
        return ""

    def _get_experience_text(self, soup) -> str:
        """
        Extract experience requirement from 'Your skills and experience' section.
        Falls back to full description search if section not found.
        """
        SKILLS_HEADINGS = {
            "your skills and experience",
            "skills and experience",
            "your skills & experience",
            "requirements",
            "yêu cầu ứng viên",
            "yêu cầu",
            "kỹ năng và kinh nghiệm",
        }

        content = soup.select_one("section.job-content, div.jd-main")
        if not content:
            return ""

        # Strategy 1: find the "Your skills and experience" heading and grab its content
        for heading in content.find_all(["h2", "h3", "h4", "strong"]):
            heading_text = heading.get_text(strip=True).lower()
            if any(kw in heading_text for kw in SKILLS_HEADINGS):
                # Collect text until next same-level heading (up to 600 chars)
                section_text = []
                for sib in heading.next_siblings:
                    if hasattr(sib, "name") and sib.name in ("h2", "h3", "h4", "strong"):
                        break
                    t = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else ""
                    if t:
                        section_text.append(t)
                text = " ".join(section_text)
                exp = _extract_experience_from_text(text)
                if exp:
                    return exp

        # Strategy 2: scan full description for experience patterns
        full_text = content.get_text(" ")
        return _extract_experience_from_text(full_text) or ""

    def _get_benefits(self, soup) -> str:
        """
        Extract 'Why you'll love working here' section content.
        Searches for heading keywords and grabs the following sibling content.
        """
        BENEFITS_HEADINGS = {
            "why you'll love working here",
            "why you will love working here",
            "tại sao bạn sẽ yêu thích làm việc",
            "tại sao bạn sẽ yêu thích",
            "phúc lợi",
            "benefits",
            "welfare",
        }

        content = soup.select_one("section.job-content, div.jd-main")
        if content:
            for heading in content.find_all(["h2", "h3"]):
                if any(kw in heading.get_text(strip=True).lower() for kw in BENEFITS_HEADINGS):
                    # Collect sibling content until the next heading
                    parts: list[str] = []
                    for sib in heading.next_siblings:
                        if hasattr(sib, "name") and sib.name in ("h2", "h3"):
                            break
                        text = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                        if text:
                            parts.append(text)
                    return " ".join(parts)[:500]

        # Class-based fallbacks
        for sel in ["div.benefits", "div[class*='welfare']", "div[class*='benefit']"]:
            el = soup.select_one(sel)
            if el:
                return strip_html(str(el))[:500]
        return ""


# ── Standalone helpers ────────────────────────────────────────────────────────

def _to_str(value) -> str:
    """Safely convert any JSON-LD value to string. Handles str, int, float, dict, list."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        # e.g. experienceRequirements may be {"@type": "OccupationalExperienceRequirements", ...}
        return value.get("monthsOfExperience") or value.get("description") or str(value)
    if isinstance(value, list):
        return ", ".join(_to_str(v) for v in value)
    return str(value)


def _clean_title(title: str) -> str:
    """
    Remove common ITviec title noise:
      - Leading district/location prefix: "Dong Da,Title" → "Title"
      - Leading job code prefix: "JOB-42 Title" → "Title"
      - Square-bracketed location: "[HN] Title" → "Title"
    """
    import re as _re
    if not title:
        return title
    # Strip leading [HN] / [TP.HCM] etc.
    title = _re.sub(r"^\[.*?\]\s*", "", title).strip()
    # Strip leading location district before comma if it looks like a place name
    # Pattern: "District/Ward, Actual Title" where district has no digits
    m = _re.match(r"^([A-Za-zÀ-ỹ\s]{2,30}),\s*(.+)$", title)
    if m:
        prefix, rest = m.group(1).strip(), m.group(2).strip()
        # Only strip if prefix looks like a location (no typical job words)
        job_words = {"senior", "junior", "lead", "engineer", "developer", "manager",
                     "analyst", "scientist", "ai", "ml", "data", "nlp", "cv"}
        if not any(w in prefix.lower() for w in job_words):
            title = rest
    # Strip leading job code: "JOB-42 " or "REQ-123: "
    title = _re.sub(r"^(JOB|REQ|POS|ID)[-#\s]\w+[\s:]+", "", title, flags=_re.I).strip()
    return title


def _extract_experience_from_text(text: str) -> str:
    """
    Find the first phrase mentioning experience years in a block of text.
    Uses flexible whitespace to handle extra spaces from HTML-to-text conversion.
    Returns the matched phrase (up to 100 chars) or empty string.
    """
    if not text:
        return ""

    SEP = r"\s*[–\-]\s*"   # dash or en-dash with optional spaces

    patterns = [
        # English — "minimum/at least/over N[-M] year(s) [of] experience"
        rf"(?:minimum\s+|at\s+least\s+|over\s+|more\s+than\s+)?\d+{SEP}?\d*\s*\+?\s*years?\s+(?:of\s+)?experience",
        rf"\d+\s*\+?\s*years?\s+(?:of\s+)?experience",
        rf"experience[:\s]+\d+{SEP}\d+\s*years?",
        rf"experience[:\s]+\d+\s*\+?\s*years?",
        # Vietnamese — flexible spaces around dashes and between words
        rf"(?:ít\s+nhất|tối\s+thiểu|từ|trên|hơn)\s*\d+{SEP}?\d*\s*năm",
        rf"\d+{SEP}\d+\s*năm\s*kinh\s*nghiệm",
        rf"\d+\s*năm\s*kinh\s*nghiệm",
        rf"\d+\s*năm\s*(?:làm\s*việc|thực\s*tế|chuyên\s*môn)?",
        # Generic range: "N - M years"
        rf"\d+{SEP}\d+\s+years?",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:100]
    return ""


def _parse_experience_years(text: str) -> float | None:
    """
    Parse minimum years of experience from a natural-language string.
    Input must already be a human-readable phrase (not a raw month integer).
    monthsOfExperience from JSON-LD is handled in _parse_from_jsonld directly.

    Examples:
        '3-5 years experience' → 3.0
        'ít nhất 2 năm'        → 2.0
        'At least 1 year'      → 1.0
        '5+ years'             → 5.0
        'No requirements'      → None
    """
    if not text:
        return None
    text = str(text).strip()

    # Reject pure-integer strings — they have no context (years vs months vs anything)
    # monthsOfExperience is handled upstream in _parse_from_jsonld
    if re.fullmatch(r"\d+", text):
        return None

    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if not numbers:
        return None
    return float(numbers[0])
