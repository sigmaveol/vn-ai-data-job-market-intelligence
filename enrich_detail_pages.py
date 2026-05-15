"""
Enrich existing records with detail page data.

Usage:
    python enrich_detail_pages.py --source 123job
    python enrich_detail_pages.py --source careerviet
    python enrich_detail_pages.py --source all

Reads existing JSONL, fetches detail pages for records missing key fields,
writes enriched records to a new JSONL file.
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import DATA_RAW, USER_AGENT
from src.crawler.utils import get_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

NEEDS_ENRICHMENT_SOURCES = ["123job", "careerviet"]


def _needs_enrichment(record: dict) -> bool:
    """Check if a record is missing key fields from detail pages."""
    return (
        not record.get("job_description") or len(record["job_description"]) < 200
        or not record.get("benefits")
        or not record.get("expiry_date")
    )


def enrich_123job_records(jsonl_path: Path, delay: float = 1.5) -> int:
    """Enrich 123job records with detail page data."""
    from src.crawler.job123_crawler import Job123Crawler

    session = get_session(USER_AGENT)
    session.headers.update({"Referer": "https://123job.vn/"})

    # Create a dummy crawler to use its methods
    crawler = Job123Crawler.__new__(Job123Crawler)
    crawler._session = session

    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except:
                    pass

    total = len(records)
    enriched = 0
    skipped = 0

    # Write enriched records to a temp file, then replace
    temp_path = jsonl_path.with_suffix(".enriched.jsonl")

    with open(temp_path, "w", encoding="utf-8") as out:
        for i, record in enumerate(records):
            if not _needs_enrichment(record):
                skipped += 1
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                continue

            url = record.get("url", "")
            if not url:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                continue

            try:
                detail = crawler._fetch_detail_page(url)
                if detail:
                    record.update(detail)
                    record["data_completeness"] = "full"
                    enriched += 1
            except Exception as e:
                logger.debug(f"Error enriching {url}: {e}")

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

            if (i + 1) % 50 == 0:
                logger.info(f"[123job enrich] {i+1}/{total} processed, {enriched} enriched")

            time.sleep(delay)

    # Replace original with enriched
    jsonl_path.unlink()
    temp_path.rename(jsonl_path)

    session.close()
    logger.info(f"[123job enrich] Done. {enriched} enriched, {skipped} already complete.")
    return enriched


def enrich_careerviet_records(jsonl_path: Path, delay: float = 1.5) -> int:
    """Enrich CareerViet records with detail page data."""
    from src.crawler.careerviet_crawler import CareerVietCrawler

    session = get_session(USER_AGENT)
    session.headers.update({"Referer": "https://careerviet.vn/"})

    crawler = CareerVietCrawler.__new__(CareerVietCrawler)
    crawler._session = session

    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except:
                    pass

    total = len(records)
    enriched = 0
    skipped = 0

    temp_path = jsonl_path.with_suffix(".enriched.jsonl")

    with open(temp_path, "w", encoding="utf-8") as out:
        for i, record in enumerate(records):
            if not _needs_enrichment(record):
                skipped += 1
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                continue

            url = record.get("url", "")
            if not url:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                continue

            try:
                detail = crawler._fetch_detail_page(url)
                if detail:
                    record.update(detail)
                    record["data_completeness"] = "full"
                    enriched += 1
            except Exception as e:
                logger.debug(f"Error enriching {url}: {e}")

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

            if (i + 1) % 50 == 0:
                logger.info(f"[careerviet enrich] {i+1}/{total} processed, {enriched} enriched")

            time.sleep(delay)

    jsonl_path.unlink()
    temp_path.rename(jsonl_path)

    session.close()
    logger.info(f"[careerviet enrich] Done. {enriched} enriched, {skipped} already complete.")
    return enriched


def main():
    parser = argparse.ArgumentParser(description="Enrich existing records with detail page data")
    parser.add_argument("--source", default="all", choices=["123job", "careerviet", "all"])
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between requests")
    args = parser.parse_args()

    sources = ["123job", "careerviet"] if args.source == "all" else [args.source]

    for source in sources:
        # Find the JSONL file for this source
        files = sorted(DATA_RAW.glob(f"{source}_jobs_*.jsonl"), reverse=True)
        if not files:
            logger.warning(f"No {source} JSONL file found in {DATA_RAW}")
            continue

        jsonl_path = files[0]
        record_count = sum(1 for _ in open(jsonl_path, encoding="utf-8"))
        logger.info(f"\nEnriching {source}: {jsonl_path.name} ({record_count} records)")
        logger.info(f"Estimated time: {record_count * args.delay / 60:.1f} minutes")

        if source == "123job":
            enrich_123job_records(jsonl_path, args.delay)
        elif source == "careerviet":
            enrich_careerviet_records(jsonl_path, args.delay)


if __name__ == "__main__":
    main()
