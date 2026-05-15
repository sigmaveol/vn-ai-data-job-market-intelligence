"""
Data collection entry point.

Usage:
    python run_crawl.py --source itviec       --max-jobs 50
    python run_crawl.py --source topcv        --max-jobs 100
    python run_crawl.py --source topdev       --max-jobs 100
    python run_crawl.py --source vietnamworks --max-jobs 500
    python run_crawl.py --source careerviet   --max-jobs 500
    python run_crawl.py --source all          --max-jobs 200

Output:
    data/raw/<source>_jobs_YYYY_MM_DD.jsonl
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Make sure project root is on sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import DATA_RAW
from src.crawler.utils import timestamped_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


SOURCES = ("itviec", "topcv", "topdev", "vietnamworks", "careerviet", "123job", "linkedin")


def build_crawler(source: str, output_path: Path):
    if source == "itviec":
        from src.crawler.itviec_crawler import ITviecCrawler
        return ITviecCrawler(output_path=output_path)
    elif source == "topcv":
        from src.crawler.topcv_crawler import TopCVCrawler
        return TopCVCrawler(output_path=output_path)
    elif source == "topdev":
        from src.crawler.topdev_crawler import TopDevCrawler
        return TopDevCrawler(output_path=output_path)
    elif source == "vietnamworks":
        from src.crawler.vietnamworks_crawler import VietnamWorksCrawler
        return VietnamWorksCrawler(output_path=output_path)
    elif source == "careerviet":
        from src.crawler.careerviet_crawler import CareerVietCrawler
        return CareerVietCrawler(output_path=output_path)
    elif source == "123job":
        from src.crawler.job123_crawler import Job123Crawler
        return Job123Crawler(output_path=output_path)
    elif source == "linkedin":
        from src.crawler.linkedin_crawler import LinkedInCrawler
        return LinkedInCrawler(output_path=output_path)
    else:
        raise ValueError(f"Unknown source: {source}")


def run_single(source: str, max_jobs: int) -> dict:
    output_path = DATA_RAW / timestamped_filename(source)
    logger.info(f"Output: {output_path}")

    crawler = build_crawler(source, output_path)
    try:
        jobs = crawler.run(max_jobs=max_jobs)
    except NotImplementedError as e:
        logger.warning(f"[{source}] Skipped: {e}")
        print(f"\n  [{source}] SKIPPED — {e}")
        return {"source": source, "jobs_saved": 0, "skipped": True, "reason": str(e)}

    # Validate and print report
    validation = crawler.validate_output()

    print("\n" + "=" * 50)
    print(f"  Source   : {source}")
    print(f"  Output   : {output_path.name}")
    print(crawler.stats.report())
    print("\n  Validation:")
    for k, v in validation.items():
        print(f"    {k}: {v}")
    print("=" * 50 + "\n")

    return {"source": source, "output": str(output_path), "jobs_saved": len(jobs)}


def main():
    parser = argparse.ArgumentParser(description="Job Market Intelligence — Data Collector")
    parser.add_argument(
        "--source",
        default="itviec",
        choices=list(SOURCES) + ["all"],
        help="Which website to crawl (default: itviec)",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=50,
        help="Max jobs per source (default: 50 for testing)",
    )
    args = parser.parse_args()

    sources = list(SOURCES) if args.source == "all" else [args.source]
    results = []

    for src in sources:
        logger.info(f"\n{'='*50}\nStarting: {src}\n{'='*50}")
        try:
            result = run_single(src, args.max_jobs)
            results.append(result)
        except Exception as e:
            logger.error(f"Crawler {src} failed: {e}", exc_info=True)
            results.append({"source": src, "error": str(e)})

    # Summary
    print("\n=== CRAWL SUMMARY ===")
    total = 0
    for r in results:
        if "error" in r:
            print(f"  {r['source']}: ERROR - {r['error']}")
        else:
            print(f"  {r['source']}: {r['jobs_saved']} jobs -> {Path(r['output']).name}")
            total += r["jobs_saved"]
    print(f"\n  Total collected: {total} jobs")

    # Save manifest
    manifest_path = DATA_RAW / "crawl_manifest.json"
    manifest: list = []
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            try:
                manifest = json.load(f)
            except json.JSONDecodeError:
                manifest = []
    manifest.append({"results": results, "total": total})
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.info(f"Manifest updated: {manifest_path}")


if __name__ == "__main__":
    main()
