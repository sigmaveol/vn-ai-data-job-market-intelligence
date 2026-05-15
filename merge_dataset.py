"""
Phase 2 Final Step: Merge all raw JSONL files into one dataset.

Usage:
    python merge_dataset.py

Output:
    data/raw/jobs_raw.jsonl   - All records (JSONL)
    data/raw/jobs_raw.csv     - All records (CSV for quick inspection)
"""
import json
import csv
import logging
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

DATA_RAW = ROOT / "data" / "raw"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "job_id", "job_title", "company_name", "salary", "salary_min", "salary_max",
    "salary_currency", "location", "employment_type", "job_level",
    "skills_required", "experience_years", "experience_level",
    "job_description", "benefits", "posted_date", "expiry_date",
    "url", "source_website", "industry", "job_type",
    "data_completeness", "crawled_at",
    "posted_date_parsed", "posted_date_status", "expiry_date_status",
    "is_active", "in_analysis_period",
]

# Source files to include (skip .enriched.jsonl — they're temp files)
SOURCE_PRIORITY = [
    "itviec",
    "vietnamworks",
    "topcv",
    "careerviet",
    "topdev",
    "123job",
]


def load_source_files() -> list[Path]:
    """Get ALL JSONL files per source (combine multiple date files)."""
    files = []
    seen_files = set()
    used_sources = set()

    for source in SOURCE_PRIORITY:
        # Get ALL files for this source (all dates, not enriched temp files)
        candidates = sorted(
            [f for f in DATA_RAW.glob(f"{source}_jobs_*.jsonl")
             if ".enriched." not in f.name and f.name != "jobs_raw.jsonl"],
        )
        for f in candidates:
            if f not in seen_files:
                files.append(f)
                seen_files.add(f)
                used_sources.add(source)
                logger.info(f"  {source}: {f.name}")

    # Also check for any other source files not in priority list
    for f in DATA_RAW.glob("*_jobs_*.jsonl"):
        source = f.name.split("_jobs_")[0]
        if f not in seen_files and ".enriched." not in f.name and "jobs_raw" not in f.name:
            files.append(f)
            seen_files.add(f)
            logger.info(f"  {source} (extra): {f.name}")

    return files


def merge_all():
    """Merge all source JSONL files into jobs_raw.jsonl."""
    logger.info("=== Phase 2 Final Merge ===")

    files = load_source_files()
    logger.info(f"\nSource files found: {len(files)}")

    all_records = []
    seen_ids = set()
    stats = {}

    for f in files:
        source = f.name.split("_jobs_")[0]
        count = 0
        dups = 0

        with open(f, encoding="utf-8", errors="replace") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                jid = record.get("job_id", "")
                if not jid:
                    # Compute from URL+title+company
                    url = record.get("url", "")
                    title = record.get("job_title", "")
                    company = record.get("company_name", "")
                    import hashlib
                    jid = hashlib.md5(f"{url}{title}{company}".encode()).hexdigest()
                    record["job_id"] = jid

                if jid in seen_ids:
                    dups += 1
                    continue
                seen_ids.add(jid)

                # Normalize skills_required to list
                skills = record.get("skills_required", [])
                if isinstance(skills, str):
                    skills = [s.strip() for s in skills.split(",") if s.strip()]
                    record["skills_required"] = skills

                # Normalize benefits to string
                benefits = record.get("benefits", "")
                if isinstance(benefits, list):
                    record["benefits"] = "; ".join(str(b) for b in benefits)

                all_records.append(record)
                count += 1

        key = f"{source}_{f.stem[-8:]}"  # unique key per file
        stats[key] = {"source": source, "file": f.name, "count": count, "dups": dups}
        logger.info(f"  {source}: {count} unique (+{dups} dups skipped)")

    # Sort by source (as defined in priority) then by posted_date
    source_order = {s: i for i, s in enumerate(SOURCE_PRIORITY)}
    all_records.sort(
        key=lambda r: (
            source_order.get(r.get("source_website", ""), 99),
            str(r.get("posted_date") or ""),
        ),
        reverse=True
    )

    # Write JSONL
    out_jsonl = DATA_RAW / "jobs_raw.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Write CSV
    out_csv = DATA_RAW / "jobs_raw.csv"
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in all_records:
            row = dict(rec)
            # Convert list fields to strings for CSV
            if isinstance(row.get("skills_required"), list):
                row["skills_required"] = ", ".join(row["skills_required"])
            writer.writerow(row)

    # Summary
    total = len(all_records)
    logger.info(f"\n{'='*50}")
    logger.info(f"MERGE COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Total unique records: {total:,}")
    # Aggregate by source
    by_source: dict[str, int] = {}
    for s in stats.values():
        src = s["source"]
        by_source[src] = by_source.get(src, 0) + s["count"]
    logger.info(f"\nBy source:")
    for src in SOURCE_PRIORITY:
        cnt = by_source.get(src, 0)
        if cnt > 0:
            logger.info(f"  {src:<20}: {cnt:>5} records")

    # Field completeness
    logger.info(f"\nField completeness (top fields):")
    key_fields = ["salary", "job_description", "benefits", "skills_required",
                  "experience_years", "posted_date", "expiry_date"]
    for field in key_fields:
        filled = sum(1 for r in all_records
                     if r.get(field) not in (None, "", [], "N/A", "Thỏa thuận"))
        pct = filled / total * 100 if total else 0
        logger.info(f"  {field:<25}: {pct:5.1f}% ({filled:,}/{total:,})")

    logger.info(f"\nOutput files:")
    logger.info(f"  JSONL: {out_jsonl}")
    logger.info(f"  CSV : {out_csv}")
    logger.info(f"\nPhase 2 COMPLETE - {total:,} records ready for Phase 3")

    return total


if __name__ == "__main__":
    total = merge_all()
    print(f"\nPhase 2 done: {total:,} records in data/raw/jobs_raw.jsonl + jobs_raw.csv")
