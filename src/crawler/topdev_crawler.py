"""
TopDev.vn crawler — AI/Data jobs in Vietnam.

Architecture:
  - topdev.vn frontend: Next.js App Router (RSC) — jobs rendered client-side
  - api.topdev.vn: REST API — returns HTML content only (no metadata)
  - Solution: Selenium waits for React hydration, then extracts job cards from DOM

Selectors verified 2026-05-14:
  - Search URL:  /jobs/search?keyword={term}
  - Job detail:  /detail-jobs/{slug}-{id}
  - Card root:   span.w-full  (parent of the flex layout)
  - Title:       a[href*='/detail-jobs/']
  - Company:     span.text-text-500  (first one in card)
  - Salary:      span.text-brand-500 span
  - Location:    extracted from card text via position analysis
  - Skills/tags: extracted from card text

Cloudflare:
  - topdev.vn DOES load via Selenium (unlike topdev.vn/viec-lam/*)
  - Fresh Chrome session per keyword (same anti-bot strategy as TopCV)
  - Page needs 12s wait for React to render job listings

SSL Note:
  - requests to topdev.vn → SSLError (Python ssl library incompatibility)
  - requests to api.topdev.vn → works but returns partial data only
  - Selenium (Chrome's BoringSSL) → works fine
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.crawler.base_crawler import BaseCrawler, CrawlStats
from src.crawler.utils import compute_job_id, extract_salary_numbers, parse_html, strip_html

logger = logging.getLogger(__name__)


def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


class TopDevCrawler(BaseCrawler):
    source_name    = "topdev"
    base_url       = "https://topdev.vn"

    # /jobs/search?keyword=X — expanded for 10K dataset target
    SEARCH_KEYWORDS = [
        # AI / Data (primary)
        "ai engineer", "data scientist", "data analyst", "data engineer",
        "machine learning engineer", "mlops engineer", "nlp engineer",
        "business intelligence", "computer vision engineer", "llm engineer",
        # Backend
        "backend developer", "java developer", "python developer",
        "php developer", "nodejs developer", "golang developer",
        "net developer", "software engineer",
        # Frontend / Mobile
        "frontend developer", "react developer", "android developer",
        "ios developer", "flutter developer", "fullstack developer",
        # DevOps / Cloud
        "devops engineer", "cloud engineer",
        # QA / Other
        "qa engineer", "business analyst", "product manager",
        "security engineer", "blockchain developer",
    ]
    PAGE_WAIT        = 12   # seconds for React to render job cards
    BETWEEN_SEARCHES = 5    # seconds between keywords

    def __init__(self, output_path: Path, delay: float = 2.0):
        super().__init__(output_path, delay)
        self._driver = None

    def iter_job_urls(self) -> Iterator[str]:
        return iter([])

    def parse_job_page(self, url: str, html: str) -> dict:
        return {}

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self, max_jobs: int = 500) -> list[dict]:
        from config import ANALYSIS_START_DATE, ANALYSIS_END_DATE
        from src.crawler.date_utils import annotate_time_fields

        logger.info(f"[topdev] Starting card-based crawl — max_jobs={max_jobs}")
        jobs: list[dict] = []

        try:
            for keyword in self.SEARCH_KEYWORDS:
                if len(jobs) >= max_jobs:
                    break

                # Reuse or create Chrome session (avoid repeated driver restarts)
                if self._driver is None:
                    logger.info("[topdev] Starting Chrome session...")
                    try:
                        self._driver = _make_driver()
                        self._driver.get(self.base_url)   # homepage warm-up
                        time.sleep(5)
                    except Exception as e:
                        logger.error(f"[topdev] Driver startup failed: {e}")
                        break

                search_url = f"{self.base_url}/jobs/search?keyword={keyword.replace(' ', '+')}"
                logger.info(f"[topdev] Scanning: {search_url}")

                for page in range(1, 20):
                    page_url = search_url if page == 1 else f"{search_url}&page={page}"
                    try:
                        self._driver.get(page_url)
                        time.sleep(self.PAGE_WAIT)
                    except Exception as e:
                        logger.warning(f"[topdev] Selenium error on {page_url}: {e}")
                        # Try to recover by restarting driver
                        self._quit_driver()
                        time.sleep(5)
                        try:
                            self._driver = _make_driver()
                            self._driver.get(page_url)
                            time.sleep(self.PAGE_WAIT)
                        except Exception as e2:
                            logger.error(f"[topdev] Recovery failed: {e2}")
                            break

                    html  = self._driver.page_source
                    title = self._driver.title

                    # Use page title for accurate block detection
                    # Working page: "Recruiting N positions with high salary [Update ...]"
                    # 404 page:     "Page Not Found" or empty title
                    # Cloudflare:   "Attention Required! | Cloudflare"
                    is_blocked = (
                        "cloudflare" in title.lower()
                        or "attention required" in title.lower()
                        or ("recruiting" not in title.lower()
                            and "job" not in title.lower()
                            and "viec lam" not in title.lower()
                            and page == 1)   # only strict check on first page
                    )
                    if is_blocked:
                        logger.warning(f"[topdev] Blocked (title={title!r}) on {page_url}")
                        break

                    logger.debug(f"[topdev] Page {page} title: {title!r}")

                    soup = parse_html(html)
                    cards = self._extract_cards(soup)

                    if not cards:
                        logger.info(f"[topdev] No cards on page {page}")
                        break

                    new_count = 0
                    for card_data in cards:
                        if len(jobs) >= max_jobs:
                            break
                        if not card_data.get("job_title"):
                            continue

                        jid = compute_job_id(
                            card_data.get("url", ""),
                            card_data.get("job_title", ""),
                            card_data.get("company_name", ""),
                        )
                        if jid in self._seen_ids:
                            self.stats.total_duplicates += 1
                            continue
                        self._seen_ids.add(jid)
                        card_data["job_id"] = jid

                        if not self._is_relevant(card_data):
                            self.stats.total_irrelevant += 1
                            continue

                        card_data["source_website"]    = self.source_name
                        card_data["crawled_at"]        = datetime.utcnow().isoformat()
                        card_data["data_completeness"] = "partial"

                        annotate_time_fields(card_data, ANALYSIS_START_DATE, ANALYSIS_END_DATE)

                        jobs.append(card_data)
                        self._append_to_file(card_data)
                        self.stats.total_saved += 1
                        new_count += 1

                        logger.info(
                            f"[topdev] [{len(jobs):03d}] "
                            f"{card_data['job_title'][:45]} @ {card_data['company_name'][:20]}"
                        )

                    if new_count == 0:
                        break

                    time.sleep(self.delay)

                time.sleep(self.BETWEEN_SEARCHES)

        finally:
            self._quit_driver()

        logger.info(f"[topdev] Done. {len(jobs)} jobs saved.\n{self.stats.report()}")
        return jobs

    # ── Card extraction ───────────────────────────────────────────────────────

    def _extract_cards(self, soup) -> list[dict]:
        """Extract all job cards from rendered listing page."""
        results: list[dict] = []

        # Find all /detail-jobs/ links (each = one job)
        job_links = soup.select("a[href*='/detail-jobs/']")

        for a in job_links:
            href  = a.get("href", "")
            title = a.get_text(strip=True)

            if not title or not href:
                continue

            # Clean URL
            url = re.sub(r"\?.*$", "", href)
            if not url.startswith("http"):
                url = self.base_url + url

            # Walk up to span.w-full (card container)
            card = self._find_card_container(a)
            if not card:
                continue

            job = self._parse_card(url, title, card)
            if job:
                results.append(job)

        return results

    def _find_card_container(self, link_el):
        """Walk up from the job link to find the full card container."""
        node = link_el
        for _ in range(10):
            if node is None:
                return None
            cls = " ".join(node.get("class") or [])
            # span.w-full is the card root
            if node.name == "span" and "w-full" in cls:
                return node
            node = node.parent
        return None

    def _parse_card(self, url: str, title: str, card) -> dict:
        """Extract all available fields from a job card element."""
        # Company
        company = ""
        for span in card.select("span"):
            cls = " ".join(span.get("class") or [])
            if "text-text-500" in cls and "line-clamp" in cls:
                company = span.get_text(strip=True)
                break

        # Salary — span.text-brand-500 cursor-pointer or actual value
        salary = ""
        for span in card.select("span"):
            cls = " ".join(span.get("class") or [])
            if "text-brand-500" in cls:
                t = span.get_text(strip=True)
                if t and "login" not in t.lower() and len(t) < 60:
                    salary = t
                    break

        # Parse full card text to extract metadata
        card_text = card.get_text(" ", strip=True)
        metadata  = self._parse_card_text(card_text, title, company, salary)

        sal_min, sal_max, currency = extract_salary_numbers(salary)

        # Validate USD salary
        _USD_MAX = 50_000
        if sal_min and sal_min > _USD_MAX:
            sal_min = sal_max = None
            currency = ""

        from src.crawler.itviec_crawler import (
            _extract_experience_from_text, _parse_experience_years
        )
        exp_yrs = _parse_experience_years(
            _extract_experience_from_text(card_text)
        )

        return {
            "url":             url,
            "job_title":       title,
            "company_name":    company,
            "salary":          salary,
            "salary_min":      sal_min,
            "salary_max":      sal_max,
            "salary_currency": currency,
            "location":        metadata.get("location", ""),
            "employment_type": metadata.get("employment_type", "Full-time"),
            "job_level":       self._infer_level(title),
            "skills_required": metadata.get("skills", []),
            "experience_years": exp_yrs,
            "experience_level": "",
            "job_description": "",    # card only, no detail page
            "benefits":        "",
            "posted_date":     metadata.get("posted_date", ""),
            "expiry_date":     "",
            "industry":        "IT / Technology",
            "job_type":        metadata.get("employment_type", "Full-time"),
        }

    def _parse_card_text(self, text: str, title: str, company: str, salary: str) -> dict:
        """
        Parse location, employment_type, skills, posted_date from card text.

        TopDev card text pattern (after title + company + salary):
            [Location]
            [Level] (Junior/Middle/Senior)
            [Type] (Fulltime/Parttime)
            [Experience] (X năm)
            [Skill1] [Skill2] ...
            [Description snippet]
            [N days/hours ago]
        """
        from config import ALL_SKILLS

        # Remove known prefix text
        remaining = text
        for prefix in [title, company, salary, "Login to view salary"]:
            if prefix and prefix in remaining:
                remaining = remaining[remaining.index(prefix) + len(prefix):].strip()

        # Posted date — TopDev shows "N days ago", "N hours ago" etc.
        # Also handle "Just now", "Today"
        posted_match = re.search(
            r"(\d+\s*(?:day|hour|minute|week|month|ngày|giờ|phút|tuần|tháng)s?\s*ago"
            r"|\bjust\s+now\b|\btoday\b|\byesterday\b"
            r"|\bhôm\s+nay\b|\bhôm\s+qua\b|\bvừa\s+đăng\b)",
            text,   # search full card text, not just remaining
            re.IGNORECASE,
        )
        posted_date = posted_match.group(0).strip() if posted_match else ""

        # Location — first word/phrase before known level keywords
        LOCATIONS = ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Cần Thơ", "Remote",
                     "Ha Noi", "Ho Chi Minh", "Da Nang", "Can Tho",
                     "Hanoi", "HCMC", "HCM"]
        location = ""
        for loc in LOCATIONS:
            if loc.lower() in remaining.lower():
                location = loc
                break

        # Employment type
        emp_type = "Full-time"
        if re.search(r"fulltime|full.time", remaining, re.I):
            emp_type = "Full-time"
        elif re.search(r"parttime|part.time", remaining, re.I):
            emp_type = "Part-time"
        elif re.search(r"remote", remaining, re.I):
            emp_type = "Remote"

        # Skills — match against taxonomy
        found_skills: list[str] = []
        text_lower = remaining.lower()
        for skill in ALL_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", text_lower):
                found_skills.append(skill)
        # Also extract parenthetical skills from title
        paren = re.findall(r"\(([^)]{3,60})\)", title)
        for group in paren:
            for part in re.split(r"[/,;]", group):
                s = part.strip()
                if s and len(s) <= 40 and not re.search(r"\d{4}|triệu|upto|năm", s, re.I):
                    found_skills.append(s)

        skills = list(dict.fromkeys(s for s in found_skills if len(s) >= 2))[:20]

        return {
            "location":        location,
            "employment_type": emp_type,
            "skills":          skills,
            "posted_date":     posted_date,
        }

    def _infer_level(self, title: str) -> str:
        t = title.lower()
        for level, kws in [
            ("Lead",   ["lead", "head", "manager", "director", "trưởng"]),
            ("Senior", ["senior", "sr.", "principal", "expert"]),
            ("Junior", ["junior", "fresher", "jr.", "entry", "intern", "trainee"]),
            ("Intern", ["intern", "thực tập", "trainee"]),
        ]:
            if any(k in t for k in kws):
                return level
        return "Mid-level"

    def _quit_driver(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
