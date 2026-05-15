"""
Fast TopCV detail page enrichment using optimized Selenium.

Optimizations vs 7-hour version:
1. Detect expired/404 pages after 2s (skip instead of full 7s wait)
2. Only wait 3s for valid pages (JSON-LD is server-side, no JS needed)
3. Batch driver restarts every 100 records
4. Expected time: ~1 hour for 1023 records

Success estimate: ~20-40% get description (expired jobs = fast 404 skip)

Usage:
    python enrich_topcv_fast.py
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
FAST_WAIT   = 2    # seconds before checking if page is expired
FULL_WAIT   = 3    # extra seconds for valid pages to load JSON-LD
DELAY       = 0.5  # between requests


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
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    # Speed: disable images and CSS
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(15)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def _parse_json_ld(html: str) -> dict:
    """Extract JobPosting JSON-LD from rendered HTML."""
    import json as json_mod
    from bs4 import BeautifulSoup
    result = {}

    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            text = script.string
            if not text:
                continue
            data = json_mod.loads(text)
            if isinstance(data, list):
                data = next((x for x in data if isinstance(x, dict)
                             and x.get("@type") == "JobPosting"), None)
            if not isinstance(data, dict) or data.get("@type") != "JobPosting":
                continue

            desc_html = data.get("description", "") or ""
            if desc_html:
                result["job_description"] = BeautifulSoup(
                    desc_html, "lxml"
                ).get_text(" ", strip=True)[:3000]

            dp = data.get("datePosted", "")
            if dp:
                result["posted_date"] = str(dp)[:10]
            valid = data.get("validThrough", "")
            if valid:
                result["expiry_date"] = str(valid)[:10]

            skills_raw = data.get("skills", "")
            if isinstance(skills_raw, str) and skills_raw:
                result["skills_required"] = [
                    s.strip() for s in skills_raw.split(",") if s.strip()
                ][:20]

            ben = data.get("jobBenefits", "")
            if ben:
                from bs4 import BeautifulSoup as BS
                result["benefits"] = BS(str(ben), "lxml").get_text(" ", strip=True)[:1500]

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


def _is_page_dead(title: str, html_snippet: str) -> str:
    """Check if page is expired/blocked/404. Returns reason or ''."""
    title_lower = title.lower()
    if "cloudflare" in title_lower or "attention required" in title_lower:
        return "cloudflare"
    if "404" in title_lower or "not found" in title_lower:
        return "404"
    if "trang không tồn tại" in title_lower or "không tìm thấy" in title_lower:
        return "expired"
    if not title or len(title) < 5:
        return "no_title"
    return ""


def _save(records: list, path: Path):
    temp = path.with_suffix(".temp.jsonl")
    with open(temp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if path.exists():
        path.unlink()
    temp.rename(path)


def enrich_fast():
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
    total = len(need)
    logger.info(f"TopCV fast enrichment: {total}/{len(records)} records need detail pages")
    logger.info(f"Estimated time: {total * 4 / 60:.0f} minutes (optimistic)")

    driver = None
    enriched = 0
    fast_skip = 0   # expired/404
    cloudflare = 0  # blocked

    try:
        driver = _make_driver()

        for count, (idx, record) in enumerate(need, 1):
            url = record.get("url", "")
            if not url:
                continue

            # Restart driver every 150 records
            if count > 1 and count % 150 == 1:
                logger.info(f"Restarting driver at {count}/{total}...")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(3)
                driver = _make_driver()

            try:
                driver.get(url)
                time.sleep(FAST_WAIT)   # short initial wait

                title = driver.title
                html_snippet = driver.page_source[:2000]

                dead_reason = _is_page_dead(title, html_snippet)
                if dead_reason == "cloudflare":
                    cloudflare += 1
                    time.sleep(8)  # pause after cloudflare
                    continue
                elif dead_reason in ("404", "expired", "no_title"):
                    fast_skip += 1
                    continue

                # Page looks valid — wait a bit more for JSON-LD
                time.sleep(FULL_WAIT)
                full_html = driver.page_source

                detail = _parse_json_ld(full_html)

                if detail.get("job_description"):
                    records[idx].update(detail)
                    records[idx]["data_completeness"] = "full"
                    enriched += 1
                    logger.info(
                        f"  [{count}/{total}] OK desc={len(detail['job_description'])}c "
                        f"expiry={detail.get('expiry_date','?')}"
                    )
                else:
                    fast_skip += 1

            except Exception as e:
                err = str(e)
                if "Timeout" in err or "timed out" in err.lower():
                    fast_skip += 1
                elif "ERR_CONNECTION" in err or "WebDriverException" in err:
                    logger.warning(f"  [{count}] Connection error, restarting...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(5)
                    try:
                        driver = _make_driver()
                    except Exception as e2:
                        logger.error(f"Restart failed: {e2}")
                        break
                else:
                    logger.debug(f"  [{count}] Error: {err[:60]}")

            # Checkpoint every 100 records
            if count % 100 == 0:
                logger.info(
                    f"Checkpoint {count}/{total} | "
                    f"enriched={enriched} | skipped={fast_skip} | blocked={cloudflare}"
                )
                _save(records, jsonl_path)

            time.sleep(DELAY)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    _save(records, jsonl_path)

    after = sum(1 for r in records if not _needs_enrichment(r))
    logger.info(f"\n{'='*55}")
    logger.info("TopCV Fast Enrichment COMPLETE")
    logger.info(f"  Processed : {total}")
    logger.info(f"  Enriched  : {enriched} ({enriched/total*100:.1f}%)")
    logger.info(f"  Expired   : {fast_skip}")
    logger.info(f"  Blocked   : {cloudflare}")
    logger.info(f"  Has desc  : {after}/{len(records)} ({after/len(records)*100:.1f}%)")
    logger.info(f"{'='*55}")


if __name__ == "__main__":
    enrich_fast()
