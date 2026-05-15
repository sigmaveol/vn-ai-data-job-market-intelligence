"""
LinkedIn Vietnam IT jobs crawler — public guest API only (no login).

Architecture:
  - linkedin.com/jobs/search/ returns server-rendered HTML with job cards
  - No authentication needed for public job listings
  - Pagination via &start=N (25 jobs per page increment)
  - Card selector: div[class*='job-search-card']

Card fields (verified 2026-05-14):
  - Title:    .base-search-card__title
  - Company:  .base-search-card__subtitle a  OR  .job-search-card__company-name
  - Location: .job-search-card__location
  - Posted:   time[datetime]  OR  .job-search-card__listdate
  - URL:      a.base-card__full-link[href]
  - Job ID:   data-entity-urn attribute ("urn:li:jobPosting:{ID}")

Rate limiting: 1-2s delay between requests to respect the server.
"""
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.crawler.base_crawler import BaseCrawler
from src.crawler.utils import compute_job_id, extract_salary_numbers, get_session, parse_html

logger = logging.getLogger(__name__)

# Search keywords for Vietnam IT jobs
_KEYWORDS = [
    # AI / Data (primary)
    "data scientist", "data analyst", "data engineer", "ai engineer",
    "machine learning", "mlops engineer", "nlp engineer",
    "business intelligence", "llm engineer", "computer vision engineer",
    # Backend
    "software engineer", "backend developer", "java developer",
    "python developer", "php developer", "nodejs developer",
    "golang developer", "net developer",
    # Frontend / Mobile
    "frontend developer", "react developer", "android developer",
    "ios developer", "flutter developer", "fullstack developer",
    # DevOps / Cloud / QA / Other
    "devops engineer", "cloud engineer", "qa engineer",
    "business analyst", "product manager", "security engineer",
    "technical lead", "solution architect",
]


class LinkedInCrawler(BaseCrawler):
    source_name = "linkedin"
    base_url    = "https://www.linkedin.com"

    PAGE_SIZE = 25   # LinkedIn increments in steps of 25
    MAX_START = 975  # LinkedIn caps at 1000 results per search (40 pages × 25)

    def __init__(self, output_path: Path, delay: float = 2.0):
        super().__init__(output_path, delay)
        self._session = None

    def iter_job_urls(self) -> Iterator[str]:
        return iter([])

    def parse_job_page(self, url: str, html: str) -> dict:
        return {}

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self, max_jobs: int = 500) -> list[dict]:
        from config import ANALYSIS_START_DATE, ANALYSIS_END_DATE
        from src.crawler.date_utils import annotate_time_fields

        logger.info(f"[linkedin] Starting Vietnam IT job search — max_jobs={max_jobs}")
        jobs: list[dict] = []

        from config import USER_AGENT
        self._session = get_session(USER_AGENT)
        self._session.headers.update({
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Referer": "https://www.linkedin.com/jobs/",
        })

        try:
            for keyword in _KEYWORDS:
                if len(jobs) >= max_jobs:
                    break

                logger.info(f"[linkedin] Keyword: {keyword}")

                start = 0
                while start <= self.MAX_START and len(jobs) < max_jobs:
                    kw_encoded = keyword.replace(" ", "+")
                    page_url = (
                        f"{self.base_url}/jobs/search/"
                        f"?keywords={kw_encoded}&location=Vietnam&start={start}"
                    )

                    try:
                        resp = self._session.get(page_url, timeout=20)
                        if resp.status_code == 429:
                            logger.warning("[linkedin] Rate limited — sleeping 30s")
                            time.sleep(30)
                            continue
                        if resp.status_code != 200:
                            logger.warning(f"[linkedin] HTTP {resp.status_code}")
                            break
                    except Exception as e:
                        logger.warning(f"[linkedin] Request error: {e}")
                        break

                    soup = parse_html(resp.text)
                    cards = soup.select("div[class*='job-search-card']")

                    if not cards:
                        logger.info(f"[linkedin] No cards at start={start} for {keyword}")
                        break

                    new_count = 0
                    for card in cards:
                        if len(jobs) >= max_jobs:
                            break

                        job = self._parse_card(card)
                        if not job or not job.get("job_title"):
                            continue

                        jid = compute_job_id(
                            job.get("url", ""),
                            job.get("job_title", ""),
                            job.get("company_name", ""),
                        )
                        if jid in self._seen_ids:
                            self.stats.total_duplicates += 1
                            continue
                        self._seen_ids.add(jid)
                        job["job_id"] = jid

                        if not self._is_relevant(job):
                            self.stats.total_irrelevant += 1
                            continue

                        job["source_website"] = self.source_name
                        job["crawled_at"] = datetime.utcnow().isoformat()
                        job["data_completeness"] = "partial"

                        annotate_time_fields(job, ANALYSIS_START_DATE, ANALYSIS_END_DATE)

                        jobs.append(job)
                        self._append_to_file(job)
                        self.stats.total_saved += 1
                        new_count += 1

                        logger.info(
                            f"[linkedin] [{len(jobs):03d}] "
                            f"{job['job_title'][:45]} @ {job['company_name'][:20]}"
                        )

                    if new_count == 0:
                        break

                    start += self.PAGE_SIZE
                    time.sleep(self.delay)

        finally:
            if self._session:
                self._session.close()

        logger.info(f"[linkedin] Done. {len(jobs)} jobs.\n{self.stats.report()}")
        return jobs

    # ── Card parser ───────────────────────────────────────────────────────────

    def _parse_card(self, card) -> dict:
        # URL
        link_el = card.select_one("a.base-card__full-link") or card.select_one("a[href*='linkedin.com/jobs']")
        if not link_el:
            return {}
        href = link_el.get("href", "")
        url = re.sub(r"\?.*$", "", href)

        # Job ID from data-entity-urn
        urn = card.get("data-entity-urn", "")
        job_id_raw = re.search(r":(\d+)$", urn)
        job_id_raw = job_id_raw.group(1) if job_id_raw else ""

        # Title
        title_el = (
            card.select_one(".base-search-card__title")
            or card.select_one("h3.job-search-card__title")
            or card.select_one("[class*='title']")
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return {}

        # Company
        comp_el = (
            card.select_one(".base-search-card__subtitle a")
            or card.select_one(".job-search-card__company-name")
            or card.select_one("[class*='company']")
        )
        company = comp_el.get_text(strip=True) if comp_el else ""

        # Location
        loc_el = (
            card.select_one(".job-search-card__location")
            or card.select_one("[class*='location']")
        )
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Posted date
        time_el = card.select_one("time[datetime]")
        posted_date = time_el.get("datetime", "") if time_el else ""
        if not posted_date:
            date_el = card.select_one(".job-search-card__listdate")
            if date_el:
                posted_date = date_el.get_text(strip=True)

        # Benefits/salary snippet (if visible)
        benefits_el = card.select_one(".job-search-card__salary-info") or card.select_one("[class*='salary']")
        salary = benefits_el.get_text(strip=True) if benefits_el else ""
        sal_min, sal_max, currency = extract_salary_numbers(salary) if salary else (None, None, "")

        # Skills from title
        skills = self._extract_skills(title)

        # Level
        level = self._infer_level(title)

        return {
            "url":             url,
            "job_title":       title,
            "company_name":    company,
            "salary":          salary,
            "salary_min":      sal_min,
            "salary_max":      sal_max,
            "salary_currency": currency,
            "location":        location,
            "employment_type": "Full-time",
            "job_level":       level,
            "skills_required": skills,
            "experience_years": None,
            "experience_level": "",
            "job_description": "",
            "benefits":        "",
            "posted_date":     posted_date,
            "expiry_date":     "",
            "industry":        "IT / Technology",
            "job_type":        "Full-time",
        }

    def _extract_skills(self, title: str) -> list[str]:
        from config import ALL_SKILLS
        found: list[str] = []
        title_lower = title.lower()
        for skill in ALL_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", title_lower):
                found.append(skill)
        for group in re.findall(r"\(([^)]{3,60})\)", title):
            for part in re.split(r"[/,;]", group):
                s = part.strip()
                if s and len(s) <= 40:
                    found.append(s)
        return list(dict.fromkeys(s for s in found if len(s) >= 2))[:20]

    def _infer_level(self, title: str) -> str:
        t = title.lower()
        for level, kws in [
            ("Lead",   ["lead", "head", "manager", "director", "principal", "staff"]),
            ("Senior", ["senior", "sr.", "expert"]),
            ("Junior", ["junior", "fresher", "jr.", "entry", "associate", "intern"]),
        ]:
            if any(k in t for k in kws):
                return level
        return "Mid-level"
