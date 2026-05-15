"""
CareerViet.vn crawler — IT jobs via curl-cffi + JSON-LD on detail pages.

Architecture (learned from learning_context_crawl/careerbuilder_crawler.py):
  - curl-cffi with safari15_5 impersonation bypasses Cloudflare TLS
  - Listing pages: /viec-lam/{category}-trang-{N}-vi.html
  - Detail pages: /vi/tim-viec-lam/{slug}.{HEXID}.html
  - JSON-LD on detail pages has COMPLETE data:
      title, company, salary, skills, benefits, experience, dates

CareerViet JSON-LD fields (JobPosting):
  - title, hiringOrganization.name
  - jobLocation[].address.addressLocality
  - description (HTML)
  - baseSalary.value.{minValue, maxValue}
  - datePosted, validThrough
  - employmentType
  - skills (string or list)
  - jobBenefits
  - experienceRequirements
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

# IT category slugs on CareerViet
_CATEGORIES = [
    "cntt-phan-mem",          # IT Software (main ~769 jobs)
    "cntt-phan-cung-mang",    # IT Hardware/Network
    "ky-thuat-may-tinh",      # Computer Engineering
    "bao-mat-thong-tin",      # Information Security
]

# Keyword searches - much more comprehensive for IT
_KEYWORDS = [
    # Vietnamese IT keywords
    "lap-trinh-vien", "ky-su-phan-mem", "chuyen-vien-cntt",
    "quan-tri-mang", "ky-su-du-lieu", "phan-tich-du-lieu",
    # English keywords
    "python", "java", "javascript", "backend", "frontend",
    "fullstack", "devops", "data-analyst", "data-engineer",
    "data-scientist", "mobile", "qa-tester", "aws", "ai",
    "nodejs", "react", "golang", "machine-learning",
    "software-engineer", "security-engineer", "business-analyst",
    "android-developer", "ios-developer", "flutter", "react-native",
    "cloud-engineer", "solution-architect", "technical-lead",
    "php", "net", "ruby", "scala", "kubernetes", "docker",
    "automation-tester", "product-manager", "blockchain",
    "embedded", "erp", "database-administrator",
    "bi-developer", "nlp", "computer-vision", "mlops",
]


class CareerVietCrawler(BaseCrawler):
    source_name = "careerviet"
    base_url    = "https://careerviet.vn"
    IMPERSONATE = "safari15_5"
    MAX_PAGES   = 50
    EMPTY_LIMIT = 3

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

        logger.info(f"[careerviet] Starting curl-cffi crawl — max_jobs={max_jobs}")
        jobs: list[dict] = []

        try:
            from curl_cffi import requests as curl_requests
            self._session = curl_requests.Session(impersonate=self.IMPERSONATE)
            self._session.headers.update({
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            })
        except ImportError:
            logger.error("[careerviet] curl-cffi not installed. Run: pip install curl-cffi")
            return []

        try:
            # 1. Category-based crawl (main)
            for cat in _CATEGORIES:
                if len(jobs) >= max_jobs:
                    break
                logger.info(f"[careerviet] Category: {cat}")
                self._crawl_search(cat, "category", max_jobs, jobs,
                                   ANALYSIS_START_DATE, ANALYSIS_END_DATE, annotate_time_fields)

            # 2. Keyword-based crawl (additional coverage)
            for kw in _KEYWORDS:
                if len(jobs) >= max_jobs:
                    break
                logger.info(f"[careerviet] Keyword: {kw}")
                self._crawl_search(kw, "keyword", max_jobs, jobs,
                                   ANALYSIS_START_DATE, ANALYSIS_END_DATE, annotate_time_fields)

        finally:
            if self._session:
                try:
                    self._session.close()
                except Exception:
                    pass

        logger.info(f"[careerviet] Done. {len(jobs)} jobs.\n{self.stats.report()}")
        return jobs

    def _crawl_search(self, slug: str, mode: str, max_jobs: int,
                      jobs: list, start_date, end_date, annotate_fn):
        empty_pages = 0
        for page in range(1, self.MAX_PAGES + 1):
            if len(jobs) >= max_jobs:
                break

            if mode == "category":
                url = (f"{self.base_url}/viec-lam/{slug}-vi.html" if page == 1
                       else f"{self.base_url}/viec-lam/{slug}-trang-{page}-vi.html")
            else:
                url = (f"{self.base_url}/viec-lam/{slug}-vi.html" if page == 1
                       else f"{self.base_url}/viec-lam/{slug}-trang-{page}-vi.html")

            detail_links = self._get_job_links_from_page(url)
            if not detail_links:
                empty_pages += 1
                if empty_pages >= self.EMPTY_LIMIT:
                    break
                continue
            empty_pages = 0

            new_links = [l for l in detail_links if l not in self._seen_ids]
            if not new_links:
                break

            for link in new_links:
                if len(jobs) >= max_jobs:
                    break

                job = self._parse_detail_page(link)
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
                self._seen_ids.add(link)  # also mark URL as seen
                job["job_id"] = jid

                if not self._is_relevant(job):
                    self.stats.total_irrelevant += 1
                    continue

                job["source_website"] = self.source_name
                job["crawled_at"] = datetime.utcnow().isoformat()
                job["data_completeness"] = "full"

                annotate_fn(job, start_date, end_date)

                jobs.append(job)
                self._append_to_file(job)
                self.stats.total_saved += 1

                logger.info(
                    f"[careerviet] [{len(jobs):03d}] "
                    f"{job['job_title'][:45]} @ {job['company_name'][:20]}"
                )

                time.sleep(self.delay)

            time.sleep(self.delay)

    # ── Listing page → detail URLs ────────────────────────────────────────────

    def _get_job_links_from_page(self, url: str) -> list[str]:
        html = self._cffi_get(url)
        if not html:
            return []
        soup = parse_html(html)
        links: list[str] = []

        # Primary pattern: /vi/tim-viec-lam/{slug}.{HEXID}.html
        for heading in soup.find_all(["h2", "h3", "h4"]):
            for a in heading.find_all("a", href=True):
                href = a.get("href", "")
                if "/vi/tim-viec-lam/" in href and re.search(r"\.[0-9A-Fa-f]{7,}\.html", href):
                    full = href if href.startswith("http") else self.base_url + href
                    clean = re.sub(r"\?.*$", "", full)
                    if clean not in links:
                        links.append(clean)

        # Fallback: any link matching the pattern
        if not links:
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if "/vi/tim-viec-lam/" in href and re.search(r"\.[0-9A-Fa-f]{7,}\.html", href):
                    full = href if href.startswith("http") else self.base_url + href
                    clean = re.sub(r"\?.*$", "", full)
                    if clean not in links:
                        links.append(clean)

        return list(dict.fromkeys(links))

    # ── Detail page parser ────────────────────────────────────────────────────

    def _parse_detail_page(self, url: str) -> dict:
        """Parse CareerViet detail page using JSON-LD + HTML fallbacks."""
        html = self._cffi_get(url)
        if not html:
            return {}
        soup = parse_html(html)
        job: dict = {"url": url}

        # ── 1. JSON-LD (primary, has most complete data) ──────────────────
        jld = self._extract_json_ld(html)
        if jld:
            job["job_title"] = (jld.get("title") or "").strip()

            # Company
            org = jld.get("hiringOrganization", {})
            if isinstance(org, dict):
                job["company_name"] = (org.get("name") or "").strip()

            # Location
            loc = jld.get("jobLocation", {})
            if isinstance(loc, list) and loc:
                loc = loc[0]
            if isinstance(loc, dict):
                addr = loc.get("address", {})
                if isinstance(addr, dict):
                    job["location"] = (addr.get("addressLocality")
                                       or addr.get("addressRegion") or "").strip()

            # Description (HTML → plain text)
            desc_html = jld.get("description", "") or ""
            if desc_html:
                job["job_description"] = self._html_to_text(desc_html)[:3000]

            # Salary
            sal = jld.get("baseSalary", {})
            if isinstance(sal, dict):
                v = sal.get("value", {})
                if isinstance(v, dict):
                    sal_min = v.get("minValue")
                    sal_max = v.get("maxValue")
                    cur = sal.get("currency", "VND")
                    if sal_min and sal_max:
                        job["salary_min"] = float(sal_min)
                        job["salary_max"] = float(sal_max)
                        job["salary_currency"] = cur
                        job["salary"] = f"{sal_min}-{sal_max} {cur}"

            # Dates
            dp = jld.get("datePosted", "")
            if dp:
                job["posted_date"] = str(dp)[:10]
            valid = jld.get("validThrough", "")
            if valid:
                job["expiry_date"] = str(valid)[:10]

            # Employment type
            emp = jld.get("employmentType", "")
            if isinstance(emp, list):
                emp = emp[0] if emp else ""
            emp = str(emp).strip('"\'').upper()
            emp_map = {"FULL_TIME": "Full-time", "PART_TIME": "Part-time",
                       "CONTRACT": "Contract", "INTERN": "Internship"}
            job["employment_type"] = emp_map.get(emp, "Full-time")

            # Skills
            skills_raw = jld.get("skills", "")
            if isinstance(skills_raw, list):
                job["skills_required"] = [str(s).strip() for s in skills_raw if str(s).strip()][:20]
            elif isinstance(skills_raw, str) and skills_raw:
                job["skills_required"] = [s.strip() for s in skills_raw.split(",") if s.strip()][:20]

            # Benefits
            ben = jld.get("jobBenefits", "")
            if isinstance(ben, list):
                job["benefits"] = "; ".join(str(b).strip() for b in ben if str(b).strip())
            elif isinstance(ben, str) and ben:
                job["benefits"] = ben[:1000]

            # Experience
            exp_req = jld.get("experienceRequirements", "")
            if exp_req:
                if isinstance(exp_req, dict):
                    months = exp_req.get("monthsOfExperience")
                    if months:
                        try:
                            job["experience_years"] = round(float(months) / 12, 1)
                        except Exception:
                            pass
                elif isinstance(exp_req, str):
                    from src.crawler.itviec_crawler import (
                        _extract_experience_from_text, _parse_experience_years
                    )
                    phrase = _extract_experience_from_text(exp_req)
                    if phrase:
                        job["experience_years"] = _parse_experience_years(phrase)

            # Industry
            ind = jld.get("industry", "")
            if ind:
                job["industry"] = str(ind).strip()

        # ── 2. HTML fallbacks ─────────────────────────────────────────────
        if not job.get("job_title"):
            for sel in ["h1.title", "h1.job-title", "h1"]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and len(txt) < 200:
                        job["job_title"] = txt
                        break

        if not job.get("company_name"):
            for sel in ["a.company-name", 'a[href*="/vi/nha-tuyen-dung/"]',
                        'a[href*="/company/"]']:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    job["company_name"] = el.get_text(strip=True)
                    break

        if not job.get("salary"):
            for sel in ["div.salary-range", "span.salary", 'div[class*="salary"]']:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    job["salary"] = el.get_text(strip=True)
                    sal_min, sal_max, cur = extract_salary_numbers(job["salary"])
                    if sal_min:
                        job["salary_min"] = sal_min
                        job["salary_max"] = sal_max
                        job["salary_currency"] = cur
                    break
            if not job.get("salary"):
                job["salary"] = "Thỏa thuận"

        if not job.get("location"):
            for sel in ["div.location", "span.location", 'div[class*="location"]']:
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    job["location"] = el.get_text(strip=True)
                    break

        if not job.get("job_description"):
            for sel in ["div.job-description", "div.description",
                        'div[class*="job-des"]', "div.detail-row"]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(" ", strip=True)
                    if len(txt) > 100:
                        job["job_description"] = txt[:3000]
                        break

        if not job.get("experience_years") and job.get("job_description"):
            from src.crawler.itviec_crawler import (
                _extract_experience_from_text, _parse_experience_years
            )
            phrase = _extract_experience_from_text(job["job_description"])
            if phrase:
                job["experience_years"] = _parse_experience_years(phrase)

        if not job.get("posted_date"):
            for sel in ["span.date", "div.date-post", "time[datetime]"]:
                el = soup.select_one(sel)
                if el:
                    text = el.get("datetime") or el.get_text(strip=True)
                    from src.crawler.date_utils import parse_date_str
                    parsed = parse_date_str(text)
                    if parsed:
                        job["posted_date"] = str(parsed)
                    break

        # Skills from description if not found in JSON-LD
        if not job.get("skills_required") and job.get("job_description"):
            from config import ALL_SKILLS
            desc_lower = job["job_description"].lower()
            found = [s for s in ALL_SKILLS
                     if re.search(rf"\b{re.escape(s.lower())}\b", desc_lower)]
            job["skills_required"] = list(dict.fromkeys(found))[:20]

        # Level
        job["job_level"] = self._infer_level(
            str(job.get("job_title", ""))
        )

        # Fill defaults
        job.setdefault("salary", "Thỏa thuận")
        job.setdefault("salary_min", None)
        job.setdefault("salary_max", None)
        job.setdefault("salary_currency", "VND")
        job.setdefault("employment_type", "Full-time")
        job.setdefault("job_type", job.get("employment_type", "Full-time"))
        job.setdefault("skills_required", [])
        job.setdefault("experience_years", None)
        job.setdefault("experience_level", "")
        job.setdefault("job_description", "")
        job.setdefault("benefits", "")
        job.setdefault("posted_date", "")
        job.setdefault("expiry_date", "")
        job.setdefault("industry", "IT / Technology")

        return job

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cffi_get(self, url: str) -> str:
        """GET with curl-cffi session (browser impersonation)."""
        for attempt in range(3):
            try:
                time.sleep(0.5 + attempt * 2)
                resp = self._session.get(url, timeout=20)
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code == 429:
                    logger.warning("[careerviet] Rate limited, waiting 30s")
                    time.sleep(30)
                elif resp.status_code == 403:
                    logger.warning(f"[careerviet] 403 on attempt {attempt+1}: {url[:70]}")
                    time.sleep(15 * (attempt + 1))
                else:
                    logger.debug(f"[careerviet] HTTP {resp.status_code}: {url[:70]}")
                    break
            except Exception as e:
                logger.debug(f"[careerviet] Error attempt {attempt+1}: {e}")
        return ""

    @staticmethod
    def _extract_json_ld(html: str) -> dict:
        """Extract JobPosting from JSON-LD script tags."""
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

    @staticmethod
    def _html_to_text(html: str) -> str:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "lxml").get_text(" ", strip=True)

    def _infer_level(self, title: str) -> str:
        t = title.lower()
        for level, kws in [
            ("Lead",   ["lead", "head", "manager", "director", "trưởng"]),
            ("Senior", ["senior", "sr.", "principal", "expert"]),
            ("Junior", ["junior", "fresher", "jr.", "entry"]),
            ("Intern", ["intern", "thực tập", "trainee"]),
        ]:
            if any(k in t for k in kws):
                return level
        return "Mid-level"
