"""
Enrich TopCV records missing job_description via Selenium.

Selenium bypasses IP-level Cloudflare blocking (different fingerprint from curl-cffi).
Estimated time: ~990 records × 10s each ≈ 2.75 hours.
Expected success rate: 20-40% (many jobs may have expired).

Usage:
    python enrich_topcv_selenium.py
"""
import json
import logging
import time
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

DATA_RAW = ROOT / "data" / "raw"
MIN_DESC_LEN = 50
CHECKPOINT_EVERY = 50   # save progress every N records
PAGE_WAIT = 7           # seconds for JS to render


def _needs_enrichment(record: dict) -> bool:
    desc = record.get("job_description") or ""
    return len(str(desc).strip()) < MIN_DESC_LEN


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
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
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


def _parse_detail_from_html(html: str) -> dict:
    """Parse TopCV detail page JSON-LD."""
    import json as json_module
    from bs4 import BeautifulSoup
    result = {}

    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            text = script.string
            if not text:
                continue
            data = json_module.loads(text)
            if isinstance(data, list):
                data = next((x for x in data if isinstance(x, dict)
                             and x.get("@type") == "JobPosting"), None)
            if not isinstance(data, dict) or data.get("@type") != "JobPosting":
                continue

            # Description
            desc_html = data.get("description", "") or ""
            if desc_html:
                result["job_description"] = BeautifulSoup(
                    desc_html, "lxml"
                ).get_text(" ", strip=True)[:3000]

            # Dates
            dp = data.get("datePosted", "")
            if dp:
                result["posted_date"] = str(dp)[:10]
            valid = data.get("validThrough", "")
            if valid:
                result["expiry_date"] = str(valid)[:10]

            # Skills
            skills_raw = data.get("skills", "")
            if isinstance(skills_raw, str) and skills_raw:
                result["skills_required"] = [
                    s.strip() for s in skills_raw.split(",") if s.strip()
                ][:20]

            # Benefits
            ben = data.get("jobBenefits", "")
            if ben:
                result["benefits"] = BeautifulSoup(
                    str(ben), "lxml"
                ).get_text(" ", strip=True)[:1500]

            # Salary
            sal = data.get("baseSalary", {})
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

            # Experience
            exp_req = data.get("experienceRequirements", {})
            if isinstance(exp_req, dict):
                months = exp_req.get("monthsOfExperience")
                if months is not None:
                    try:
                        result["experience_years"] = round(float(months) / 12, 1)
                    except Exception:
                        pass

            break
        except Exception:
            continue

    return result


def enrich_topcv_selenium():
    """Main Selenium-based enrichment."""
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

    need = [(i, r) for i, r in enumerate(records) if _needs_enrichment(r)]
    logger.info(f"TopCV Selenium enrichment: {len(need)}/{len(records)} records need detail pages")

    if not need:
        logger.info("All TopCV records already have job_description")
        return

    driver = None
    enriched = 0
    skipped_expired = 0
    skipped_blocked = 0

    try:
        driver = _make_driver()
        logger.info("Selenium driver started")

        for count, (idx, record) in enumerate(need, 1):
            url = record.get("url", "")
            if not url:
                continue

            # Restart driver every 200 records to avoid memory/session issues
            if count > 1 and count % 200 == 1:
                logger.info(f"Restarting Selenium driver at record {count}...")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(5)
                driver = _make_driver()

            try:
                driver.get(url)
                time.sleep(PAGE_WAIT)

                # Check page status
                title = driver.title
                html = driver.page_source

                # Detect cloudflare or expired
                is_cloudflare = "cloudflare" in html.lower()[:1000] or "attention required" in title.lower()
                is_404 = "404" in title or "not found" in title.lower() or "trang không tồn tại" in title.lower()

                if is_cloudflare:
                    skipped_blocked += 1
                    logger.debug(f"  [{count}] Cloudflare block: {url[:60]}")
                    time.sleep(10)  # extra wait after block
                    continue

                if is_404:
                    skipped_expired += 1
                    logger.debug(f"  [{count}] Expired/404: {url[:60]}")
                    continue

                detail = _parse_detail_from_html(html)

                if detail.get("job_description"):
                    records[idx].update(detail)
                    records[idx]["data_completeness"] = "full"
                    enriched += 1
                    logger.info(
                        f"  [{count}/{len(need)}] OK "
                        f"desc={len(detail['job_description'])}chars "
                        f"expiry={detail.get('expiry_date','?')}"
                    )
                else:
                    logger.debug(f"  [{count}] No JSON-LD found on page")

            except Exception as e:
                logger.warning(f"  [{count}] Error on {url[:60]}: {e}")
                # Try to restart driver if connection issue
                if "ERR_CONNECTION" in str(e) or "WebDriverException" in str(e):
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(10)
                    try:
                        driver = _make_driver()
                    except Exception as e2:
                        logger.error(f"Driver restart failed: {e2}")
                        break

            # Checkpoint save
            if count % CHECKPOINT_EVERY == 0:
                logger.info(
                    f"Checkpoint {count}/{len(need)} | "
                    f"enriched={enriched} | expired={skipped_expired} | blocked={skipped_blocked}"
                )
                _save_records(records, jsonl_path)

            time.sleep(1.0)  # polite delay

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # Final save
    _save_records(records, jsonl_path)

    after = sum(1 for r in records if not _needs_enrichment(r))
    logger.info(f"\n{'='*55}")
    logger.info("TopCV Selenium Enrichment COMPLETE")
    logger.info(f"  Processed     : {len(need)}")
    logger.info(f"  Enriched      : {enriched}")
    logger.info(f"  Expired/404   : {skipped_expired}")
    logger.info(f"  Blocked       : {skipped_blocked}")
    logger.info(f"  Has desc after: {after}/{len(records)} ({after/len(records)*100:.1f}%)")
    logger.info(f"{'='*55}")


def _save_records(records: list, path: Path):
    """Atomic save: write to temp then rename."""
    temp = path.with_suffix(".temp.jsonl")
    with open(temp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if path.exists():
        path.unlink()
    temp.rename(path)


if __name__ == "__main__":
    enrich_topcv_selenium()
