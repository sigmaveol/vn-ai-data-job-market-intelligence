"""
Enrich 990 TopCV records missing job_description by retrying detail page fetch.

Strategy:
  - Use curl-cffi with safari15_5 impersonation
  - Rotate between multiple impersonation profiles to avoid 403
  - Add longer delays between requests
  - Extract JSON-LD: description, benefits, skills, salary, expiry_date

Usage:
    python enrich_topcv_details.py
"""
import json
import logging
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
import sys
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_RAW = ROOT / "data" / "raw"
IMPERSONATE_PROFILES = ["safari15_5", "chrome120", "chrome110", "safari17_0"]
DELAY_BASE = 1.0       # seconds between requests
MAX_403_IN_ROW = 5     # stop trying after N consecutive 403s
MIN_DESC_LEN = 50      # minimum chars to count as "has description"


def _needs_enrichment(record: dict) -> bool:
    desc = record.get("job_description") or ""
    return len(str(desc).strip()) < MIN_DESC_LEN


def _extract_json_ld(html: str) -> dict:
    """Extract JobPosting JSON-LD from TopCV detail page."""
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


def _parse_detail(html: str) -> dict:
    """Parse TopCV detail page and extract all available fields."""
    result = {}
    jld = _extract_json_ld(html)
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
        result["benefits"] = BeautifulSoup(str(ben), "lxml").get_text(" ", strip=True)[:1500]

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


def enrich_topcv():
    """Main enrichment function."""
    from curl_cffi import requests as curl_requests

    # Find TopCV JSONL file
    files = sorted(DATA_RAW.glob("topcv_jobs_*.jsonl"), reverse=True)
    if not files:
        logger.error("No TopCV JSONL file found")
        return

    jsonl_path = files[0]
    records = []
    with open(jsonl_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    # Find records needing enrichment
    need_enrichment = [(i, r) for i, r in enumerate(records) if _needs_enrichment(r)]
    logger.info(f"TopCV enrichment: {len(need_enrichment)}/{len(records)} records need detail pages")

    if not need_enrichment:
        logger.info("All records already have job_description — nothing to do")
        return

    # Create session with first profile
    profile_idx = 0
    session = curl_requests.Session(impersonate=IMPERSONATE_PROFILES[profile_idx])
    session.headers.update({
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
        "Referer": "https://www.topcv.vn/",
    })

    enriched = 0
    failed = 0
    consecutive_403 = 0

    for count, (idx, record) in enumerate(need_enrichment, 1):
        url = record.get("url", "")
        if not url:
            continue

        # Rotate impersonation profile after consecutive 403s
        if consecutive_403 >= 3:
            profile_idx = (profile_idx + 1) % len(IMPERSONATE_PROFILES)
            try:
                session.close()
            except Exception:
                pass
            session = curl_requests.Session(impersonate=IMPERSONATE_PROFILES[profile_idx])
            session.headers.update({
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
                "Referer": "https://www.topcv.vn/",
            })
            logger.info(f"  Switched to profile: {IMPERSONATE_PROFILES[profile_idx]}")
            consecutive_403 = 0
            time.sleep(10)  # longer pause after switching profile

        if consecutive_403 >= MAX_403_IN_ROW:
            logger.warning(f"  Too many 403s — stopping enrichment")
            break

        # Try to fetch detail page
        success = False
        for attempt in range(3):
            try:
                time.sleep(DELAY_BASE + attempt * 1.5)
                resp = session.get(url, timeout=20)

                if resp.status_code == 200:
                    detail = _parse_detail(resp.text)
                    if detail.get("job_description"):
                        records[idx].update(detail)
                        records[idx]["data_completeness"] = "full"
                        enriched += 1
                        consecutive_403 = 0
                        success = True
                        logger.info(
                            f"  [{count}/{len(need_enrichment)}] OK: "
                            f"{record.get('job_title','?')[:45]}"
                        )
                    else:
                        logger.debug(f"  [{count}] No JSON-LD found: {url[:60]}")
                        consecutive_403 = 0
                        success = True  # got 200 but no description
                    break

                elif resp.status_code == 403:
                    consecutive_403 += 1
                    logger.debug(f"  [{count}] 403 attempt {attempt+1}")
                    if attempt < 2:
                        time.sleep(3 + attempt * 5)

                elif resp.status_code == 404:
                    logger.debug(f"  [{count}] 404 (expired): {url[:60]}")
                    success = True
                    break

                else:
                    logger.debug(f"  [{count}] HTTP {resp.status_code}")
                    break

            except Exception as e:
                logger.debug(f"  [{count}] Error: {e}")
                break

        if not success:
            failed += 1

        # Progress checkpoint every 100 records
        if count % 100 == 0:
            logger.info(f"Progress: {count}/{len(need_enrichment)} | enriched={enriched} failed={failed}")
            # Save checkpoint
            temp = jsonl_path.with_suffix(".temp.jsonl")
            with open(temp, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    try:
        session.close()
    except Exception:
        pass

    # Save final result
    temp = jsonl_path.with_suffix(".temp.jsonl")
    with open(temp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Replace original
    jsonl_path.unlink()
    temp.rename(jsonl_path)

    # Final stats
    after_enrichment = sum(1 for r in records if not _needs_enrichment(r))
    logger.info(f"\n{'='*55}")
    logger.info(f"TopCV enrichment COMPLETE")
    logger.info(f"  Processed  : {len(need_enrichment)} records")
    logger.info(f"  Enriched   : {enriched}")
    logger.info(f"  Failed/403 : {failed}")
    logger.info(f"  Has description (after): {after_enrichment}/{len(records)} "
                f"({after_enrichment/len(records)*100:.1f}%)")
    logger.info(f"{'='*55}")


if __name__ == "__main__":
    enrich_topcv()
