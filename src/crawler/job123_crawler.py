"""
123job.vn crawler — IT jobs.

Architecture:
  - 123job.vn is server-rendered HTML, no Selenium needed
  - IT job listings at /viec-lam-it (1400+ jobs) and keyword-specific URLs
  - Each listing page shows 30-31 job cards
  - Pagination: /viec-lam-{keyword}?q={keyword}&sort=top_related&page=N
  - Card selector: div[class*='item-job']  (div.job__list-item.js-item-job)

Card fields (verified 2026-05-14):
  - Title:      h2.job__list-item-title a (text + href)
  - Company:    .job__list-item-company span
  - Salary:     .job__list-item-info .salary label
  - Location:   .job__list-item-info .address label
  - Posted:     data-time attribute (ISO-like: "2026-05-14 14:55:03")
  - Description:.job__list-item-teaser (snippet)
  - Job URL:    href of title a (full URL)
  - Hash slug:  data-hash-slug attribute
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


class Job123Crawler(BaseCrawler):
    source_name = "123job"
    base_url    = "https://123job.vn"

    # URL pattern: /viec-lam-{keyword} for page 1
    # Pagination: ?q={keyword}&sort=top_related&page=N
    SEARCH_CONFIGS = [
        # (page1_url, keyword_for_pagination)
        # IT general (1400+ jobs)
        ("/viec-lam-it",                         "it"),
        # AI / Data
        ("/viec-lam-data-scientist",              "data-scientist"),
        ("/viec-lam-data-analyst",                "data-analyst"),
        ("/viec-lam-data-engineer",               "data-engineer"),
        ("/viec-lam-machine-learning",            "machine-learning"),
        ("/viec-lam-ai-engineer",                 "ai-engineer"),
        ("/viec-lam-business-intelligence",       "business-intelligence"),
        # Backend
        ("/viec-lam-software-engineer",           "software-engineer"),
        ("/viec-lam-backend-developer",           "backend-developer"),
        ("/viec-lam-java-developer",              "java-developer"),
        ("/viec-lam-python-developer",            "python-developer"),
        ("/viec-lam-php-developer",               "php-developer"),
        ("/viec-lam-nodejs",                      "nodejs"),
        ("/viec-lam-net-developer",               "net-developer"),
        # Frontend / Mobile
        ("/viec-lam-frontend-developer",          "frontend-developer"),
        ("/viec-lam-react-developer",             "react-developer"),
        ("/viec-lam-android-developer",           "android-developer"),
        ("/viec-lam-ios-developer",               "ios-developer"),
        ("/viec-lam-flutter",                     "flutter"),
        ("/viec-lam-fullstack-developer",         "fullstack-developer"),
        # DevOps / Cloud / QA / Other
        ("/viec-lam-devops",                      "devops"),
        ("/viec-lam-cloud-engineer",              "cloud-engineer"),
        ("/viec-lam-qa-engineer",                 "qa-engineer"),
        ("/viec-lam-business-analyst",            "business-analyst"),
        ("/viec-lam-product-manager",             "product-manager"),
        ("/viec-lam-security-engineer",           "security-engineer"),
        # Additional tech keywords
        ("/viec-lam-angular-developer",           "angular-developer"),
        ("/viec-lam-react-native",                "react-native"),
        ("/viec-lam-golang",                      "golang"),
        ("/viec-lam-kubernetes",                  "kubernetes"),
        ("/viec-lam-blockchain-developer",        "blockchain-developer"),
        ("/viec-lam-embedded-developer",          "embedded-developer"),
        ("/viec-lam-game-developer",              "game-developer"),
        ("/viec-lam-nlp-engineer",                "nlp-engineer"),
        ("/viec-lam-technical-lead",              "technical-lead"),
        ("/viec-lam-erp",                         "erp"),
        # Vietnamese-language keywords
        ("/viec-lam-lap-trinh-vien",              "lap-trinh-vien"),
        ("/viec-lam-ky-su-phan-mem",              "ky-su-phan-mem"),
        ("/viec-lam-chuyen-vien-cong-nghe",       "chuyen-vien-cong-nghe"),
        ("/viec-lam-scrum-master",                "scrum-master"),
        ("/viec-lam-database-administrator",      "database-administrator"),
        # More specific IT roles
        ("/viec-lam-salesforce",                  "salesforce"),
        ("/viec-lam-sap-developer",               "sap-developer"),
        ("/viec-lam-magento",                     "magento"),
        ("/viec-lam-wordpress-developer",         "wordpress-developer"),
        ("/viec-lam-network-engineer",            "network-engineer"),
        ("/viec-lam-system-administrator",        "system-administrator"),
        ("/viec-lam-automation-engineer",         "automation-engineer"),
        ("/viec-lam-cloud-architect",             "cloud-architect"),
        ("/viec-lam-data-architecture",           "data-architecture"),
        ("/viec-lam-iot-engineer",                "iot-engineer"),
        ("/viec-lam-robotic-process-automation",  "robotic-process-automation"),
        ("/viec-lam-unity-developer",             "unity-developer"),
        ("/viec-lam-ui-ux-designer",              "ui-ux-designer"),
        ("/viec-lam-api-developer",               "api-developer"),
        # Data / Analytics tools
        ("/viec-lam-power-bi",                    "power-bi"),
        ("/viec-lam-tableau",                     "tableau"),
        ("/viec-lam-sql-developer",               "sql-developer"),
        ("/viec-lam-oracle-developer",            "oracle-developer"),
        ("/viec-lam-etl-developer",               "etl-developer"),
        ("/viec-lam-big-data",                    "big-data"),
        # Cloud / Infrastructure
        ("/viec-lam-aws-engineer",                "aws-engineer"),
        ("/viec-lam-azure-developer",             "azure-developer"),
        ("/viec-lam-gcp-engineer",                "gcp-engineer"),
        ("/viec-lam-linux-administrator",         "linux-administrator"),
        ("/viec-lam-network-administrator",       "network-administrator"),
        ("/viec-lam-infrastructure-engineer",     "infrastructure-engineer"),
        # Security
        ("/viec-lam-penetration-testing",         "penetration-testing"),
        ("/viec-lam-soc-analyst",                 "soc-analyst"),
        # More specific IT roles
        ("/viec-lam-technical-architect",         "technical-architect"),
        ("/viec-lam-solution-architect",          "solution-architect"),
        ("/viec-lam-product-owner",               "product-owner"),
        ("/viec-lam-it-manager",                  "it-manager"),
        ("/viec-lam-crm-developer",               "crm-developer"),
        ("/viec-lam-ruby-on-rails",               "ruby-on-rails"),
        ("/viec-lam-spring-boot",                 "spring-boot"),
        ("/viec-lam-microservices",               "microservices"),
        ("/viec-lam-graphql",                     "graphql"),
        # Vietnamese-language IT roles
        ("/viec-lam-nhan-vien-it",                "nhan-vien-it"),
        ("/viec-lam-giam-sat-cntt",               "giam-sat-cntt"),
        ("/viec-lam-quan-tri-mang",               "quan-tri-mang"),
        ("/viec-lam-chuyen-vien-phan-tich-he-thong", "chuyen-vien-phan-tich-he-thong"),
    ]
    MAX_PAGES = 100

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

        logger.info(f"[123job] Starting HTML crawl — max_jobs={max_jobs}")
        jobs: list[dict] = []

        from config import USER_AGENT
        self._session = get_session(USER_AGENT)
        self._session.headers.update({
            "Referer": "https://123job.vn/",
        })

        try:
            for page1_path, kw in self.SEARCH_CONFIGS:
                if len(jobs) >= max_jobs:
                    break

                logger.info(f"[123job] Keyword: {kw}")

                for page in range(1, self.MAX_PAGES + 1):
                    if len(jobs) >= max_jobs:
                        break

                    if page == 1:
                        page_url = self.base_url + page1_path
                    else:
                        page_url = (
                            f"{self.base_url}{page1_path}"
                            f"?q={kw}&sort=top_related&page={page}"
                        )

                    try:
                        resp = self._session.get(page_url, timeout=20)
                        if resp.status_code not in (200, 301, 302):
                            logger.warning(f"[123job] HTTP {resp.status_code} on {page_url}")
                            break
                    except Exception as e:
                        logger.warning(f"[123job] Request error: {e}")
                        break

                    soup = parse_html(resp.text)
                    cards = soup.select("div.js-item-job") or soup.select("div[class*='item-job']")

                    if not cards:
                        logger.info(f"[123job] No cards on page {page} of {kw}")
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

                        # Fetch detail page for complete fields
                        if job.get("url"):
                            detail = self._fetch_detail_page(job["url"])
                            job.update(detail)

                        job["source_website"] = self.source_name
                        job["crawled_at"] = datetime.utcnow().isoformat()
                        job["data_completeness"] = (
                            "full" if job.get("job_description") else "partial"
                        )

                        annotate_time_fields(job, ANALYSIS_START_DATE, ANALYSIS_END_DATE)

                        jobs.append(job)
                        self._append_to_file(job)
                        self.stats.total_saved += 1
                        new_count += 1

                        logger.info(
                            f"[123job] [{len(jobs):03d}] "
                            f"{job['job_title'][:45]} @ {job['company_name'][:20]}"
                        )

                    if new_count == 0:
                        break

                    time.sleep(self.delay)

        finally:
            if self._session:
                self._session.close()

        logger.info(f"[123job] Done. {len(jobs)} jobs.\n{self.stats.report()}")
        return jobs

    # ── Card parser ───────────────────────────────────────────────────────────

    def _parse_card(self, card) -> dict:
        # Title + URL
        title_el = card.select_one("h2.job__list-item-title a") or card.select_one("h2 a")
        if not title_el:
            title_el = card.select_one("a[href*='/viec-lam/']")
        if not title_el:
            return {}

        title = title_el.get_text(strip=True)
        if not title:
            return {}

        href = title_el.get("href", "")
        url = re.sub(r"\?.*$", "", href)  # strip ?codePosition=C1
        if url and not url.startswith("http"):
            url = self.base_url + url

        # Company
        comp_el = (
            card.select_one(".job__list-item-company span")
            or card.select_one(".job__list-item-company")
            or card.select_one("[class*='company']")
        )
        company = comp_el.get_text(strip=True) if comp_el else ""

        # Salary
        sal_el = (
            card.select_one(".job__list-item-info .salary label")
            or card.select_one("[class*='salary'] label")
            or card.select_one(".salary")
        )
        # Remove icon text (e.g. "$" from <i> tag)
        if sal_el:
            for i in sal_el.select("i"):
                i.extract()
            salary = sal_el.get_text(strip=True)
        else:
            salary = ""
        sal_min, sal_max, currency = extract_salary_numbers(salary)

        # Location
        loc_el = (
            card.select_one(".address label")
            or card.select_one("[class*='address'] label")
            or card.select_one(".location")
        )
        if loc_el:
            for i in loc_el.select("i"):
                i.extract()
            location = loc_el.get_text(strip=True)
        else:
            location = ""

        # Posted date — data-time attribute (ISO-like "2026-05-14 14:55:03")
        posted_date = card.get("data-time") or ""
        if not posted_date:
            # Fallback to .timing text
            timing_el = card.select_one(".timing") or card.select_one("[class*='timing']")
            if timing_el:
                posted_date = timing_el.get_text(strip=True)

        # Description snippet
        desc_el = card.select_one(".job__list-item-teaser") or card.select_one("[class*='teaser']")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        # Skills from title + description
        skills = self._extract_skills(title, desc)

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
            "job_description": desc,
            "benefits":        "",
            "posted_date":     posted_date,
            "expiry_date":     "",
            "industry":        "IT / Technology",
            "job_type":        "Full-time",
        }

    def _extract_skills(self, title: str, desc: str) -> list[str]:
        from config import ALL_SKILLS
        found: list[str] = []
        text = (title + " " + desc).lower()
        for skill in ALL_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", text):
                found.append(skill)
        # Parenthetical from title
        for group in re.findall(r"\(([^)]{3,60})\)", title):
            for part in re.split(r"[/,;]", group):
                s = part.strip()
                if s and len(s) <= 40:
                    found.append(s)
        return list(dict.fromkeys(s for s in found if len(s) >= 2))[:20]

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

    # ── Detail page fetcher ───────────────────────────────────────────────────

    def _fetch_detail_page(self, url: str) -> dict:
        """Fetch 123job detail page and extract full job data."""
        try:
            resp = self._session.get(url, timeout=15)
            if resp.status_code != 200:
                return {}
            return self._parse_detail_page(resp.text)
        except Exception as e:
            logger.debug(f"[123job] Detail page error {url}: {e}")
            return {}

    def _parse_detail_page(self, html: str) -> dict:
        """
        Extract complete job fields from 123job detail page HTML.

        Section structure on 123job detail page:
          - "Mô tả công việc" → job_description
          - "Yêu cầu công việc" → requirements (for experience, skills)
          - "Quyền lợi" → benefits
          - Salary, experience, education shown as badge pills
        """
        from src.crawler.itviec_crawler import (
            _extract_experience_from_text, _parse_experience_years
        )
        from config import ALL_SKILLS

        soup = parse_html(html)

        # Extract section text using heading boundary approach
        # 1. Collect all text in page, find sections by heading keywords
        full_text = soup.get_text(" ", strip=True)

        desc      = self._extract_section(full_text, "mô tả công việc",
                                          ["yêu cầu công việc", "quyền lợi"])
        req_text  = self._extract_section(full_text, "yêu cầu công việc",
                                          ["quyền lợi", "thông tin chung"])
        benefits  = self._extract_section(full_text, "quyền lợi",
                                          ["thông tin chung", "việc làm tương tự"])

        # Also try DOM-based extraction for robustness
        if not desc:
            desc = self._dom_section(soup, ["mô tả", "description", "job-description"])
        if not req_text:
            req_text = self._dom_section(soup, ["yêu cầu", "requirement", "job-requirement"])
        if not benefits:
            benefits = self._dom_section(soup, ["quyền lợi", "benefit", "phúc lợi"])

        # Experience from requirements text
        exp_phrase = _extract_experience_from_text(req_text or desc or "")
        experience_years = _parse_experience_years(exp_phrase) if exp_phrase else None

        # Skills from all text
        combined_text = (desc + " " + req_text).lower()
        found_skills: list[str] = []
        for skill in ALL_SKILLS:
            if re.search(rf"\b{re.escape(skill.lower())}\b", combined_text):
                found_skills.append(skill)

        # Salary from detail page (often more specific)
        sal_el = soup.select_one(".box-salary .salary-value, [class*='salary-value'], [class*='box-salary']")
        salary_detail = sal_el.get_text(strip=True) if sal_el else ""

        # Expiry date
        expiry_el = soup.select_one("[class*='deadline'], [class*='expire'], [class*='hethan']")
        expiry_date = ""
        if expiry_el:
            expiry_text = expiry_el.get_text(strip=True)
            m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})", expiry_text)
            if m:
                expiry_date = m.group(1)

        # Extract expiry date from full page text ("Hạn nộp hồ sơ DD/MM/YYYY")
        if not expiry_date:
            m = re.search(
                r"hạn\s+nộp\s+(?:hồ\s+sơ\s+)?(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})",
                full_text, re.IGNORECASE
            )
            if m:
                expiry_date = m.group(1)

        # Clean benefits: remove navigation noise after "Cập nhật gần nhất"
        if benefits:
            noise_idx = benefits.lower().find("cập nhật gần nhất")
            if noise_idx > 0:
                benefits = benefits[:noise_idx].strip()
            # Also remove "Xem thêm Nộp hồ sơ" suffixes
            for noise in ["xem thêm nộp hồ sơ", "xem thêm", "nộp hồ sơ online"]:
                idx = benefits.lower().rfind(noise)
                if idx > len(benefits) - 100:
                    benefits = benefits[:idx].strip()

        result: dict = {}
        if desc:
            result["job_description"] = desc[:3000]
        if benefits:
            result["benefits"] = benefits[:1500]
        if req_text:
            result["requirements"] = req_text[:2000]
        if experience_years is not None:
            result["experience_years"] = experience_years
        if found_skills:
            result["skills_required"] = list(dict.fromkeys(found_skills))[:20]
        if salary_detail:
            from src.crawler.utils import extract_salary_numbers
            sal_min, sal_max, currency = extract_salary_numbers(salary_detail)
            if sal_min:
                result["salary"] = salary_detail
                result["salary_min"] = sal_min
                result["salary_max"] = sal_max
                result["salary_currency"] = currency
        if expiry_date:
            result["expiry_date"] = expiry_date

        return result

    def _extract_section(self, text: str, start_kw: str, end_kws: list[str]) -> str:
        """Extract text between two section headings (case-insensitive)."""
        text_lower = text.lower()
        start_idx = text_lower.find(start_kw)
        if start_idx < 0:
            return ""
        # Skip past the heading itself
        content_start = start_idx + len(start_kw)

        # Find earliest end keyword
        end_idx = len(text)
        for ekw in end_kws:
            idx = text_lower.find(ekw, content_start)
            if 0 < idx < end_idx:
                end_idx = idx

        return text[content_start:end_idx].strip()

    def _dom_section(self, soup, keywords: list[str]) -> str:
        """Find section content via DOM keyword match on heading elements."""
        for el in soup.select("h1, h2, h3, h4, strong, label, dt"):
            t = el.get_text(strip=True).lower()
            if any(kw in t for kw in keywords):
                # Get parent container text
                parent = el.parent
                if parent:
                    return parent.get_text(" ", strip=True)[:2000]
        return ""
