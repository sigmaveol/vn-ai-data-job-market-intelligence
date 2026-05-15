"""
VietnamWorks crawler — IT jobs via ms.vietnamworks.com REST API.

Architecture (learned from learning_context_crawl):
  - API: https://ms.vietnamworks.com/job-search/v1.0/search (POST)
  - Auth: curl-cffi with chrome120 impersonation bypasses Cloudflare TLS
  - Each API call returns 10 jobs with COMPLETE data (no detail page needed)
  - Fields available: title, company, salary, skills, benefits, experience, dates

API payload:
  {
    "query": keyword,
    "industryV3Ids": [25, 35, 36, 37, 44, 45],
    "page": 0,   # 0-indexed
    "size": 20,
  }

Industry IDs (IT):
  25=IT Software/SaaS, 35=Software Developer, 36=IT Mgmt,
  37=IT PM, 44=IT Support/HelpDesk, 45=Security/Network
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator

from src.crawler.base_crawler import BaseCrawler
from src.crawler.utils import compute_job_id, extract_salary_numbers

logger = logging.getLogger(__name__)

SEARCH_API = "https://ms.vietnamworks.com/job-search/v1.0/search"
VNW_IT_INDUSTRY_IDS = [25, 35, 36, 37, 44, 45]

# Employment type codes
_TYPE_WORKING = {
    1: "Full-time", 2: "Part-time", 3: "Contract",
    4: "Internship", 5: "Freelance", 6: "Remote"
}

# Keywords for IT roles — expanded for more coverage
_SEARCH_KEYWORDS = [
    # AI / Data (primary)
    "data scientist", "data analyst", "data engineer", "ai engineer",
    "machine learning", "mlops", "nlp engineer", "computer vision",
    "business intelligence", "llm engineer", "deep learning",
    "data architect", "analytics engineer", "big data",
    "data warehouse", "etl developer", "bi developer",
    # Backend
    "software engineer", "backend developer", "java developer",
    "python developer", "php developer", "nodejs developer",
    "golang developer", "net developer", "ruby developer",
    "spring boot", "microservices", "scala developer", "c++ developer",
    # Frontend / Mobile
    "frontend developer", "react developer", "angular developer",
    "android developer", "ios developer", "flutter developer",
    "fullstack developer", "react native", "vue developer",
    "ui ux designer", "mobile developer",
    # DevOps / Cloud / QA
    "devops engineer", "cloud engineer", "aws", "qa engineer",
    "tester", "business analyst", "product manager",
    "security engineer", "blockchain developer",
    "kubernetes", "docker", "sre", "platform engineer",
    "automation tester", "solution architect", "technical lead",
    # General IT
    "it", "developer", "engineer", "programmer", "software",
    "database administrator", "network engineer", "system administrator",
    "erp", "salesforce", "sap developer", "project manager",
]


class VietnamWorksCrawler(BaseCrawler):
    source_name = "vietnamworks"
    base_url    = "https://www.vietnamworks.com"

    MAX_PAGES = 50   # per keyword (API is 0-indexed)
    PAGE_SIZE = 20   # jobs per API call

    def __init__(self, output_path: Path, delay: float = 1.5):
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

        logger.info(f"[vietnamworks] Starting API crawl — max_jobs={max_jobs}")
        jobs: list[dict] = []

        try:
            from curl_cffi import requests as curl_requests
            self._session = curl_requests.Session(impersonate="chrome120")
            self._session.headers.update({
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
                "Origin": self.base_url,
                "Referer": self.base_url + "/",
            })
        except ImportError:
            logger.error("[vietnamworks] curl-cffi not installed. Run: pip install curl-cffi")
            return []

        try:
            for keyword in _SEARCH_KEYWORDS:
                if len(jobs) >= max_jobs:
                    break

                logger.info(f"[vietnamworks] Keyword: {keyword}")

                # Fetch first page to get total pages
                raw_jobs, total_pages = self._search_page(keyword, 0)
                if not raw_jobs:
                    continue

                logger.debug(f"[vietnamworks]   → {total_pages} pages available")
                all_pages = [raw_jobs]  # page 0 already fetched

                # Fetch remaining pages
                for page in range(1, min(total_pages, self.MAX_PAGES)):
                    if len(jobs) >= max_jobs:
                        break
                    page_jobs, _ = self._search_page(keyword, page)
                    if not page_jobs:
                        break
                    all_pages.append(page_jobs)
                    time.sleep(self.delay)

                # Process all collected raw jobs
                for raw_list in all_pages:
                    for raw in raw_list:
                        if len(jobs) >= max_jobs:
                            break
                        job = self._normalize_job(raw)
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
                        job["data_completeness"] = "full"

                        annotate_time_fields(job, ANALYSIS_START_DATE, ANALYSIS_END_DATE)

                        jobs.append(job)
                        self._append_to_file(job)
                        self.stats.total_saved += 1

                        logger.info(
                            f"[vietnamworks] [{len(jobs):03d}] "
                            f"{job['job_title'][:45]} @ {job['company_name'][:20]}"
                        )

        finally:
            if self._session:
                try:
                    self._session.close()
                except Exception:
                    pass

        logger.info(f"[vietnamworks] Done. {len(jobs)} jobs.\n{self.stats.report()}")
        return jobs

    # ── API call ──────────────────────────────────────────────────────────────

    def _search_page(self, keyword: str, page: int) -> tuple[list[dict], int]:
        """Call VNW search API. Returns (jobs, total_pages)."""
        # Alternate between industry-filtered and broad search for wider coverage
        use_industry = (hash(keyword) % 3 != 0)  # ~67% use industry filter
        payload = {
            "query": keyword,
            "page": page,
            "size": self.PAGE_SIZE,
        }
        if use_industry:
            payload["industryV3Ids"] = VNW_IT_INDUSTRY_IDS
        for attempt in range(3):
            try:
                resp = self._session.post(SEARCH_API, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    meta = data.get("meta", {})
                    nb_pages = min(int(meta.get("nbPages", 0)), self.MAX_PAGES)
                    return data.get("data", []), nb_pages
                elif resp.status_code == 429:
                    logger.warning("[vietnamworks] Rate limited, waiting 30s")
                    time.sleep(30)
                else:
                    logger.warning(f"[vietnamworks] HTTP {resp.status_code} on page {page}")
                    break
            except Exception as e:
                logger.warning(f"[vietnamworks] API error (attempt {attempt+1}): {e}")
                time.sleep(5 * (attempt + 1))
        return [], 0

    # ── Job normalization ─────────────────────────────────────────────────────

    def _normalize_job(self, raw: dict) -> dict:
        """Map VNW API response fields to our schema."""
        if not isinstance(raw, dict):
            return {}

        title = (raw.get("jobTitle") or raw.get("title") or "").strip()
        if not title:
            return {}

        company = (raw.get("companyName") or raw.get("company_name") or "").strip()

        # URL
        url = (raw.get("jobUrl") or raw.get("canonical") or "")
        if not url:
            alias = raw.get("alias", "")
            jid = raw.get("jobId", "")
            if alias and jid:
                url = f"{self.base_url}/{alias}-{jid}-jv"
        if url and not url.startswith("http"):
            url = self.base_url + url
        url = re.sub(r"\?.*$", "", url)

        # Salary
        salary_str = (raw.get("prettySalary") or raw.get("prettySalaryVI") or "Thỏa thuận")
        sal_min_raw = raw.get("salaryMin", 0)
        sal_max_raw = raw.get("salaryMax", 0)
        try:
            sal_min = float(sal_min_raw) if float(sal_min_raw or 0) > 0 else None
            sal_max = float(sal_max_raw) if float(sal_max_raw or 0) > 0 else None
        except Exception:
            sal_min = sal_max = None
        currency = raw.get("salaryCurrency") or "USD"
        # Fallback parse from salary string
        if sal_min is None and salary_str:
            sal_min, sal_max, currency = extract_salary_numbers(salary_str)

        # Dates
        posted_date = ""
        approved = raw.get("approvedOn") or raw.get("onlineOn") or raw.get("createdOn") or ""
        if approved:
            posted_date = str(approved)[:10]
        expiry_date = ""
        expired = raw.get("expiredOn") or ""
        if expired:
            expiry_date = str(expired)[:10]

        # Experience
        yoe = raw.get("yearsOfExperience")
        try:
            experience_years = float(yoe) if yoe is not None and float(yoe) >= 0 else None
        except Exception:
            experience_years = None

        # Job level
        job_level_raw = raw.get("jobLevel") or raw.get("jobLevelVI") or ""
        job_level = self._normalize_level(str(job_level_raw) + " " + title)

        # Employment type
        twid = raw.get("typeWorkingId")
        employment_type = "Full-time"
        if twid:
            try:
                employment_type = _TYPE_WORKING.get(int(twid), "Full-time")
            except Exception:
                pass

        # Location
        locs = raw.get("workingLocations", [])
        if isinstance(locs, list) and locs:
            city_names = []
            for loc in locs:
                if isinstance(loc, dict):
                    city = loc.get("cityName") or loc.get("cityNameVI") or loc.get("address") or ""
                    if city:
                        city_names.append(city)
            location = ", ".join(filter(None, city_names[:3]))
        else:
            location = str(raw.get("address", "")).strip()

        # Skills
        skills_raw = raw.get("skills", [])
        skills: list[str] = []
        if isinstance(skills_raw, list):
            for s in skills_raw:
                if isinstance(s, dict) and s.get("skillName"):
                    skills.append(s["skillName"])
                elif isinstance(s, str) and s:
                    skills.append(s)

        # Benefits
        ben_raw = raw.get("benefits", [])
        benefits_list: list[str] = []
        if isinstance(ben_raw, list):
            for b in ben_raw:
                if isinstance(b, dict):
                    name = b.get("benefitName") or b.get("benefitNameVI") or ""
                    val = b.get("benefitValue") or ""
                    if name and val:
                        benefits_list.append(f"{name}: {val}")
                    elif name:
                        benefits_list.append(name)
                elif isinstance(b, str) and b:
                    benefits_list.append(b)
        benefits_str = "; ".join(benefits_list[:10])

        # Description
        desc_html = raw.get("jobDescription", "") or ""
        req_html = raw.get("jobRequirement", "") or ""
        from bs4 import BeautifulSoup
        desc_text = BeautifulSoup(desc_html, "lxml").get_text(" ").strip() if desc_html else ""
        req_text = BeautifulSoup(req_html, "lxml").get_text(" ").strip() if req_html else ""
        job_description = (desc_text + "\n\n" + req_text).strip()[:3000]

        # Experience from description if not available
        if experience_years is None and job_description:
            from src.crawler.itviec_crawler import (
                _extract_experience_from_text, _parse_experience_years
            )
            exp_phrase = _extract_experience_from_text(job_description)
            if exp_phrase:
                experience_years = _parse_experience_years(exp_phrase)

        # Industry
        ind_list = raw.get("industriesV3", []) or raw.get("industries", [])
        industry = "IT / Technology"
        if isinstance(ind_list, list):
            for item in ind_list:
                if isinstance(item, dict):
                    name = (item.get("industryV3Name") or item.get("industryName")
                            or item.get("name") or "")
                    if name:
                        industry = name
                        break

        return {
            "url":             url,
            "job_title":       title,
            "company_name":    company,
            "salary":          salary_str,
            "salary_min":      sal_min,
            "salary_max":      sal_max,
            "salary_currency": currency,
            "location":        location,
            "employment_type": employment_type,
            "job_level":       job_level,
            "skills_required": skills[:20],
            "experience_years": experience_years,
            "experience_level": "",
            "job_description": job_description,
            "benefits":        benefits_str,
            "posted_date":     posted_date,
            "expiry_date":     expiry_date,
            "industry":        industry,
            "job_type":        employment_type,
        }

    def _normalize_level(self, raw: str) -> str:
        t = raw.lower()
        for level, kws in [
            ("Lead",   ["manager", "director", "head", "lead", "principal", "trưởng"]),
            ("Senior", ["senior", "experienced", "cao cấp", "sr."]),
            ("Junior", ["junior", "fresher", "entry", "jr.", "intern", "thực tập"]),
        ]:
            if any(k in t for k in kws):
                return level
        return "Mid-level"
