"""
TopCV.vn crawler — IT jobs via Selenium + curl-cffi hybrid.

Strategy (hybrid approach):
  - Selenium: listing pages (anti-bot friendly, proven to work)
    → /tim-viec-lam-{keyword} → 25-50 cards per page
  - curl-cffi: detail pages (JSON-LD with complete data)
    → /viec-lam/{slug}/{id}.html → skills, benefits, salary, dates

Why hybrid:
  - curl-cffi for listing pages → blocked after ~130 requests (rate limited)
  - Selenium for listing → slower but much harder to detect
  - curl-cffi for detail pages → faster than Selenium, gets JSON-LD data

Data quality with this approach:
  - job_title, company, salary, location, experience, posted_date (from card)
  - job_description, benefits, skills, expiry_date (from detail page JSON-LD)
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.crawler.base_crawler import BaseCrawler
from src.crawler.utils import compute_job_id, extract_salary_numbers, parse_html

logger = logging.getLogger(__name__)

_SEARCH_URLS = [
    # AI / Data (primary)
    "https://www.topcv.vn/tim-viec-lam-ai-engineer",
    "https://www.topcv.vn/tim-viec-lam-data-scientist",
    "https://www.topcv.vn/tim-viec-lam-data-analyst",
    "https://www.topcv.vn/tim-viec-lam-data-engineer",
    "https://www.topcv.vn/tim-viec-lam-machine-learning",
    "https://www.topcv.vn/tim-viec-lam-mlops",
    "https://www.topcv.vn/tim-viec-lam-nlp",
    "https://www.topcv.vn/tim-viec-lam-business-intelligence",
    "https://www.topcv.vn/tim-viec-lam-llm",
    "https://www.topcv.vn/tim-viec-lam-deep-learning",
    "https://www.topcv.vn/tim-viec-lam-computer-vision",
    "https://www.topcv.vn/tim-viec-lam-data-warehouse",
    # Backend
    "https://www.topcv.vn/tim-viec-lam-software-engineer",
    "https://www.topcv.vn/tim-viec-lam-backend-developer",
    "https://www.topcv.vn/tim-viec-lam-java-developer",
    "https://www.topcv.vn/tim-viec-lam-python-developer",
    "https://www.topcv.vn/tim-viec-lam-php-developer",
    "https://www.topcv.vn/tim-viec-lam-nodejs-developer",
    "https://www.topcv.vn/tim-viec-lam-golang-developer",
    "https://www.topcv.vn/tim-viec-lam-net-developer",
    "https://www.topcv.vn/tim-viec-lam-ruby-developer",
    # Frontend / Mobile
    "https://www.topcv.vn/tim-viec-lam-frontend-developer",
    "https://www.topcv.vn/tim-viec-lam-react-developer",
    "https://www.topcv.vn/tim-viec-lam-angular-developer",
    "https://www.topcv.vn/tim-viec-lam-android-developer",
    "https://www.topcv.vn/tim-viec-lam-ios-developer",
    "https://www.topcv.vn/tim-viec-lam-mobile-developer",
    "https://www.topcv.vn/tim-viec-lam-flutter-developer",
    "https://www.topcv.vn/tim-viec-lam-react-native",
    "https://www.topcv.vn/tim-viec-lam-fullstack-developer",
    # DevOps / Cloud
    "https://www.topcv.vn/tim-viec-lam-devops-engineer",
    "https://www.topcv.vn/tim-viec-lam-cloud-engineer",
    "https://www.topcv.vn/tim-viec-lam-aws",
    "https://www.topcv.vn/tim-viec-lam-kubernetes",
    # QA / Other
    "https://www.topcv.vn/tim-viec-lam-qa-engineer",
    "https://www.topcv.vn/tim-viec-lam-tester",
    "https://www.topcv.vn/tim-viec-lam-automation-tester",
    "https://www.topcv.vn/tim-viec-lam-business-analyst",
    "https://www.topcv.vn/tim-viec-lam-product-manager",
    "https://www.topcv.vn/tim-viec-lam-technical-lead",
    "https://www.topcv.vn/tim-viec-lam-solution-architect",
    "https://www.topcv.vn/tim-viec-lam-security-engineer",
    "https://www.topcv.vn/tim-viec-lam-blockchain-developer",
    "https://www.topcv.vn/tim-viec-lam-embedded-engineer",
    "https://www.topcv.vn/tim-viec-lam-database-administrator",
    "https://www.topcv.vn/tim-viec-lam-project-manager",
    "https://www.topcv.vn/tim-viec-lam-scrum-master",
    "https://www.topcv.vn/tim-viec-lam-erp",
]
MAX_PAGES      = 20
PAGE_WAIT      = 6    # Selenium wait for JS render
BETWEEN_PAGES  = 3    # wait between Selenium requests


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


class TopCVCrawler(BaseCrawler):
    source_name = "topcv"
    base_url    = "https://www.topcv.vn"

    def __init__(self, output_path: Path, delay: float = 2.0):
        super().__init__(output_path, delay)
        self._driver = None
        self._cffi_session = None

    def iter_job_urls(self) -> Iterator[str]:
        return iter([])

    def parse_job_page(self, url: str, html: str) -> dict:
        return {}

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self, max_jobs: int = 500) -> list[dict]:
        from config import ANALYSIS_START_DATE, ANALYSIS_END_DATE
        from src.crawler.date_utils import annotate_time_fields

        logger.info(f"[topcv] Starting Selenium+cffi hybrid crawl — max_jobs={max_jobs}")
        jobs: list[dict] = []

        # Init curl-cffi session for detail pages
        try:
            from curl_cffi import requests as curl_requests
            self._cffi_session = curl_requests.Session(impersonate="safari15_5")
            self._cffi_session.headers.update({
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
                "Referer": self.base_url + "/",
            })
        except ImportError:
            logger.warning("[topcv] curl-cffi not available — detail pages will be skipped")

        try:
            for search_url in _SEARCH_URLS:
                if len(jobs) >= max_jobs:
                    break

                # Fresh Selenium session per search URL (prevents Cloudflare detection)
                self._quit_driver()
                time.sleep(2)
                try:
                    self._driver = _make_driver()
                except Exception as e:
                    logger.error(f"[topcv] Driver startup failed: {e}")
                    break

                logger.info(f"[topcv] Scanning: {search_url}")

                for page in range(1, MAX_PAGES + 1):
                    if len(jobs) >= max_jobs:
                        break

                    page_url = search_url if page == 1 else f"{search_url}?page={page}"

                    try:
                        self._driver.get(page_url)
                        time.sleep(PAGE_WAIT)
                    except Exception as e:
                        logger.warning(f"[topcv] Selenium error: {e}")
                        break

                    html = self._driver.page_source
                    if "cloudflare" in html.lower()[:2000]:
                        logger.warning(f"[topcv] Cloudflare block at page {page}")
                        break

                    soup = parse_html(html)
                    cards = soup.select("div[class*='job-item']")

                    if not cards:
                        logger.info(f"[topcv] No cards on page {page}")
                        break

                    # Extract card data + URLs
                    new_count = 0
                    for card in cards:
                        if len(jobs) >= max_jobs:
                            break

                        card_job = self._parse_card(card)
                        if not card_job or not card_job.get("job_title"):
                            continue
                        if not card_job.get("url"):
                            continue

                        # Dedup check
                        jid = compute_job_id(
                            card_job.get("url", ""),
                            card_job.get("job_title", ""),
                            card_job.get("company_name", ""),
                        )
                        if jid in self._seen_ids:
                            self.stats.total_duplicates += 1
                            continue
                        self._seen_ids.add(jid)
                        card_job["job_id"] = jid

                        # Relevance check (on card data first)
                        if not self._is_relevant(card_job):
                            self.stats.total_irrelevant += 1
                            continue

                        # Enrich with detail page (curl-cffi, much faster than Selenium)
                        if self._cffi_session and card_job.get("url"):
                            detail = self._fetch_detail_cffi(card_job["url"])
                            card_job.update(detail)

                        card_job["source_website"] = self.source_name
                        card_job["crawled_at"] = datetime.utcnow().isoformat()
                        card_job["data_completeness"] = (
                            "full" if card_job.get("job_description") else "partial"
                        )

                        annotate_time_fields(card_job, ANALYSIS_START_DATE, ANALYSIS_END_DATE)

                        jobs.append(card_job)
                        self._append_to_file(card_job)
                        self.stats.total_saved += 1
                        new_count += 1

                        logger.info(
                            f"[topcv] [{len(jobs):03d}] "
                            f"{card_job['job_title'][:45]} @ {card_job['company_name'][:20]}"
                        )

                    if new_count == 0:
                        break

                    time.sleep(BETWEEN_PAGES)

        finally:
            self._quit_driver()
            if self._cffi_session:
                try:
                    self._cffi_session.close()
                except Exception:
                    pass

        logger.info(f"[topcv] Done. {len(jobs)} jobs.\n{self.stats.report()}")
        return jobs

    # ── Card parser (Selenium listing page) ───────────────────────────────────

    def _parse_card(self, card) -> dict:
        # Title + URL
        title_el = card.select_one("h3.title a") or card.select_one("h3 a")
        if not title_el:
            return {}
        title = title_el.get_text(strip=True)
        if not title:
            return {}

        href = title_el.get("href", "")
        url = re.sub(r"\?.*$", "", href)
        if url and not url.startswith("http"):
            url = self.base_url + url

        # Company
        comp_el = card.select_one("span.company-name") or card.select_one("[class*='company']")
        company = comp_el.get_text(strip=True) if comp_el else ""

        # Salary
        sal_el = card.select_one("label.salary") or card.select_one("[class*='salary']")
        salary = sal_el.get_text(strip=True) if sal_el else ""
        sal_min, sal_max, currency = extract_salary_numbers(salary)

        # Location
        loc_el = card.select_one("span[class*='city']") or card.select_one("[class*='location']")
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Experience from card
        from src.crawler.itviec_crawler import (
            _extract_experience_from_text, _parse_experience_years
        )
        card_text = card.get_text(" ", strip=True)
        exp_phrase = _extract_experience_from_text(card_text)
        experience_years = _parse_experience_years(exp_phrase) if exp_phrase else None

        # Posted date
        date_el = (card.select_one(".time") or card.select_one("[class*='date']")
                   or card.select_one("time"))
        posted_date = date_el.get_text(strip=True) if date_el else ""

        # Basic skills from title
        from config import ALL_SKILLS
        found_skills = [s for s in ALL_SKILLS
                        if re.search(rf"\b{re.escape(s.lower())}\b", title.lower())]
        skills = list(dict.fromkeys(found_skills))[:10]

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
            "job_level":       self._infer_level(title),
            "skills_required": skills,
            "experience_years": experience_years,
            "experience_level": "",
            "job_description": "",
            "benefits":        "",
            "posted_date":     posted_date,
            "expiry_date":     "",
            "industry":        "IT / Technology",
            "job_type":        "Full-time",
        }

    # ── Detail page fetcher (curl-cffi, faster than Selenium) ─────────────────

    def _fetch_detail_cffi(self, url: str) -> dict:
        """Fetch detail page with curl-cffi to get JSON-LD (description, benefits, etc.)."""
        for attempt in range(2):
            try:
                time.sleep(0.3 + attempt * 1.5)
                resp = self._cffi_session.get(url, timeout=15)
                if resp.status_code == 200:
                    return self._parse_jsonld(resp.text)
                elif resp.status_code == 403:
                    time.sleep(2)
            except Exception as e:
                logger.debug(f"[topcv] cffi detail error: {e}")
        return {}

    def _parse_jsonld(self, html: str) -> dict:
        """Extract complete job data from TopCV detail page JSON-LD."""
        result = {}
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        jld = self._extract_json_ld(html)

        if not jld:
            return result

        # Description
        desc_html = jld.get("description", "") or ""
        if desc_html:
            result["job_description"] = BeautifulSoup(desc_html, "lxml").get_text(" ", strip=True)[:3000]

        # Dates
        dp = jld.get("datePosted", "")
        if dp:
            result["posted_date"] = str(dp)[:10]
        valid = jld.get("validThrough", "")
        if valid:
            result["expiry_date"] = str(valid)[:10]

        # Skills
        skills_raw = jld.get("skills", "")
        if isinstance(skills_raw, str) and skills_raw:
            result["skills_required"] = [s.strip() for s in skills_raw.split(",") if s.strip()][:20]
        elif isinstance(skills_raw, list):
            result["skills_required"] = [str(s).strip() for s in skills_raw if str(s).strip()][:20]

        # Benefits
        ben = jld.get("jobBenefits", "")
        if ben:
            ben_text = BeautifulSoup(str(ben), "lxml").get_text(" ", strip=True)
            result["benefits"] = ben_text[:1500]

        # Salary
        sal = jld.get("baseSalary", {})
        if isinstance(sal, dict):
            v = sal.get("value", {})
            if isinstance(v, dict):
                try:
                    sal_min = float(v.get("minValue") or 0)
                    sal_max = float(v.get("maxValue") or 0)
                    cur = sal.get("currency", "USD")
                    if sal_min > 0:
                        result["salary_min"] = sal_min
                        result["salary_max"] = sal_max
                        result["salary"] = f"{sal_min}-{sal_max} {cur}"
                        result["salary_currency"] = cur
                except Exception:
                    pass

        # Employment type
        emp = jld.get("employmentType", "")
        if isinstance(emp, list):
            emp = emp[0] if emp else ""
        emp_map = {"FULL_TIME": "Full-time", "PART_TIME": "Part-time",
                   "CONTRACT": "Contract", "INTERN": "Internship"}
        if emp:
            result["employment_type"] = emp_map.get(str(emp).strip('"\'').upper(), "Full-time")

        # Experience
        exp_req = jld.get("experienceRequirements", {})
        if isinstance(exp_req, dict):
            months = exp_req.get("monthsOfExperience")
            if months is not None:
                try:
                    result["experience_years"] = round(float(months) / 12, 1)
                except Exception:
                    pass

        return result

    @staticmethod
    def _extract_json_ld(html: str) -> dict:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                text = script.string
                if not text:
                    continue
                data = json.loads(text)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            return item
                elif isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        return data
                    for item in data.get("@graph", []):
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            return item
            except Exception:
                continue
        return {}

    def _infer_level(self, title: str) -> str:
        t = title.lower()
        for level, kws in [
            ("Lead",   ["lead", "head", "manager", "director", "trưởng phòng"]),
            ("Senior", ["senior", "sr.", "principal"]),
            ("Junior", ["junior", "fresher", "jr.", "entry"]),
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
