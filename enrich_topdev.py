"""
Enrich TopDev records with detail page data using Selenium.

TopDev detail page findings (2026-05-15):
- JSON-LD in plain <script> tag (NOT type=application/ld+json)
  → @type=JobPosting, title, datePosted, validThrough, skills, description
- DOM class prefix: td-* (TopDev design system)
  → Requirements: div[class*='td-mt-3'][class*='td-flex-col']
  → Description: div.td-block.td-mx-3 (About Us section)
- Salary: HIDDEN behind login (cannot extract)
- expiry_date in page text: "Application deadline: DD-MM-YYYY"
- experience_years in page text: "N+ years" or "N nam"

Usage:
    python enrich_topdev.py
"""
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _make_driver():
    from src.crawler.topdev_crawler import _make_driver as td_make_driver
    return td_make_driver()


def _extract_topdev_job_data(html: str, page_text: str) -> dict:
    """Extract job data from TopDev rendered detail page."""
    from src.crawler.utils import parse_html

    soup = parse_html(html)
    result = {}

    # 1. JSON-LD in plain <script> tag (TopDev-specific)
    for script in soup.find_all("script"):
        txt = script.string or ""
        if '"@type":"JobPosting"' in txt or '"@type": "JobPosting"' in txt:
            try:
                # Find JSON object
                m = re.search(r'\{[^{}]*"@type"\s*:\s*"JobPosting".*\}', txt, re.DOTALL)
                if m:
                    jld = json.loads(m.group(0))
                else:
                    jld = json.loads(txt)
                result["jsonld_found"] = True
                result["posted_date"] = str(jld.get("datePosted", ""))[:10]
                result["expiry_date"] = str(jld.get("validThrough", ""))[:10]
                skills_raw = jld.get("skills", "")
                if skills_raw:
                    result["skills_required"] = [s.strip() for s in skills_raw.split(",") if s.strip()]
                # Description from JSON-LD
                desc_html = jld.get("description", "")
                if desc_html:
                    from bs4 import BeautifulSoup
                    result["job_description"] = BeautifulSoup(desc_html, "lxml").get_text(" ").strip()[:3000]
                # Benefits from JSON-LD
                ben_html = jld.get("jobBenefits", "")
                if ben_html:
                    from bs4 import BeautifulSoup as BS
                    ben_text = BS(str(ben_html), "lxml").get_text(" ", strip=True)
                    if len(ben_text.strip()) > 10:
                        result["benefits"] = ben_text[:1500]
                # Salary from JSON-LD
                sal = jld.get("baseSalary", {})
                if isinstance(sal, dict):
                    v = sal.get("value", {})
                    if isinstance(v, dict):
                        sal_val = v.get("value", "")
                        if isinstance(sal_val, str) and sal_val.strip():
                            if sal_val.lower() in ("negotiable", "thoa thuan", "thoả thuận"):
                                result["salary"] = "Negotiable"
                                result["is_negotiable"] = True
                            else:
                                try:
                                    n = float(sal_val.replace(",", ""))
                                    cur = sal.get("currency", "VND")
                                    result["salary_min"] = n
                                    result["salary_max"] = n
                                    result["salary"] = f"{n} {cur}"
                                    result["salary_currency"] = cur
                                except Exception:
                                    result["salary"] = sal_val
                        elif isinstance(v.get("minValue"), (int, float)):
                            try:
                                sal_min = float(v.get("minValue") or 0)
                                sal_max = float(v.get("maxValue") or 0)
                                cur = sal.get("currency", "VND")
                                if sal_min > 0:
                                    result["salary_min"] = sal_min
                                    result["salary_max"] = sal_max
                                    result["salary"] = f"{sal_min}-{sal_max} {cur}"
                                    result["salary_currency"] = cur
                            except Exception:
                                pass
                # Experience from experienceRequirements
                exp_req = jld.get("experienceRequirements", {})
                if isinstance(exp_req, dict):
                    months = exp_req.get("monthsOfExperience")
                    if months is not None:
                        try:
                            result["experience_years"] = round(float(months) / 12, 1)
                        except Exception:
                            pass
                break
            except Exception as e:
                logger.debug(f"JSON-LD parse error: {e}")

    # 2. DOM-based extraction using td-* class selectors
    if not result.get("job_description"):
        # TopDev uses td-* prefix classes
        # Description sections are in large td-mt-3 or td-flex-col divs
        desc_parts = []
        for div in soup.select("div[class*='td-mt-3'], div[class*='td-flex-col']"):
            txt = div.get_text(" ", strip=True)
            if 200 < len(txt) < 4000:
                desc_parts.append(txt)
        if desc_parts:
            result["job_description"] = "\n\n".join(desc_parts[:3])[:3000]

    # 3. Extract from page_text using patterns
    # Expiry date
    if not result.get("expiry_date"):
        m = re.search(r"application deadline\s*[:：]\s*(\d{1,2}-\d{1,2}-\d{4}|\d{4}-\d{2}-\d{2})",
                      page_text, re.IGNORECASE)
        if m:
            result["expiry_date"] = m.group(1)

    # Experience years
    from src.crawler.itviec_crawler import (
        _extract_experience_from_text, _parse_experience_years
    )
    if result.get("job_description"):
        phrase = _extract_experience_from_text(result["job_description"])
        if phrase:
            result["experience_years"] = _parse_experience_years(phrase)
    if not result.get("experience_years"):
        phrase = _extract_experience_from_text(page_text[:2000])
        if phrase:
            result["experience_years"] = _parse_experience_years(phrase)

    # Location (often in page text as "Ho Chi Minh" or "Hà Nội")
    if not result.get("location"):
        for loc in ["Ho Chi Minh", "Ha Noi", "Da Nang", "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Remote"]:
            if loc.lower() in page_text.lower():
                result["location"] = loc
                break

    # Employment type
    if "Fulltime" in page_text or "Full-time" in page_text or "FULL_TIME" in page_text:
        result["employment_type"] = "Full-time"
    elif "Remote" in page_text:
        result["employment_type"] = "Remote"
    elif "Parttime" in page_text or "Part-time" in page_text:
        result["employment_type"] = "Part-time"

    return result


def enrich_topdev():
    """Main enrichment function for TopDev records."""
    data_files = sorted(Path("data/raw").glob("topdev_jobs_*.jsonl"), reverse=True)
    if not data_files:
        logger.error("No TopDev JSONL file found")
        return

    jsonl_path = data_files[0]
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    logger.info(f"Enriching {len(records)} TopDev records from {jsonl_path.name}")

    driver = None
    enriched = 0
    skipped = 0

    temp_path = jsonl_path.with_suffix(".enriched.jsonl")

    try:
        # Start Selenium with homepage warmup
        logger.info("Starting Chrome with homepage warmup...")
        driver = _make_driver()
        driver.get("https://topdev.vn")
        time.sleep(8)
        logger.info("Homepage loaded, starting enrichment...")

        with open(temp_path, "w", encoding="utf-8") as out:
            for i, record in enumerate(records):
                url = record.get("url", "")
                already_has_desc = (record.get("job_description") and
                                    len(record["job_description"]) > 100)
                already_has_benefits = len(str(record.get("benefits") or "").strip()) > 10
                already_complete = already_has_desc and record.get("posted_date") and already_has_benefits

                if already_complete:
                    skipped += 1
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    continue

                if not url:
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    continue

                try:
                    driver.get(url)
                    time.sleep(5)

                    html = driver.page_source
                    page_text = driver.execute_script("return document.body.innerText") or ""

                    detail_data = _extract_topdev_job_data(html, page_text)
                    if detail_data:
                        # Only update non-empty fields
                        for k, v in detail_data.items():
                            if k != "jsonld_found" and v:
                                record[k] = v
                        record["data_completeness"] = "full" if record.get("job_description") else "partial"
                        enriched += 1

                    out.write(json.dumps(record, ensure_ascii=False) + "\n")

                    logger.info(
                        f"[{i+1:03d}/{len(records)}] "
                        f"{record.get('job_title','?')[:40]}"
                        f" | desc={bool(record.get('job_description'))}"
                        f" | date={record.get('posted_date','')}"
                    )

                except Exception as e:
                    logger.warning(f"Error enriching {url}: {e}")
                    # Try to restart if connection closed
                    if "ERR_CONNECTION_CLOSED" in str(e) or "ERR_FAILED" in str(e):
                        logger.info("Restarting Chrome...")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        time.sleep(15)
                        try:
                            driver = _make_driver()
                            driver.get("https://topdev.vn")
                            time.sleep(10)
                        except Exception as e2:
                            logger.error(f"Restart failed: {e2}")
                            break
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")

                time.sleep(1)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    if temp_path.exists():
        jsonl_path.unlink()
        temp_path.rename(jsonl_path)
        logger.info(f"Done. {enriched} enriched, {skipped} skipped.")


if __name__ == "__main__":
    enrich_topdev()
