"""
Full preprocessing pipeline for the Vietnamese IT job market dataset.

Pipeline steps:
    1. Load raw JSONL
    2. Drop invalid / missing records
    3. Clean text fields (HTML removal, whitespace)
    4. Remove duplicates
    5. Normalize salary (→ USD)
    6. Normalize location (→ canonical city)
    7. Normalize skills
    8. Extract/infer experience
    9. Normalize dates
    10. Feature engineering (salary_midpoint, skill_count, is_remote)
    11. Dataset validation
    12. Export CSV + Parquet
"""
import json
import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


def load_raw_dataset(jsonl_path: Path) -> pd.DataFrame:
    """Load raw JSONL into a DataFrame."""
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"  Skipping line {line_no}: {e}")
    if not records:
        raise ValueError(f"No valid records found in {jsonl_path}")
    df = pd.DataFrame(records)
    logger.info(f"  Loaded {len(df):,} records from {jsonl_path.name}")
    return df


def validate_dataset(df: pd.DataFrame) -> dict:
    """Compute dataset quality metrics."""
    n = len(df)
    if n == 0:
        return {"total": 0}

    key_fields = [
        "job_title", "company_name", "salary_min_usd", "location_normalized",
        "skills_normalized", "experience_years_parsed", "experience_level_inferred",
        "job_description", "benefits", "posted_date", "expiry_date",
    ]
    null_pct = {}
    for col in key_fields:
        if col in df.columns:
            not_null = df[col].apply(
                lambda x: bool(x) if isinstance(x, list)
                else (pd.notna(x) and str(x).strip() not in ("", "[]", "nan"))
            ).sum()
            null_pct[col] = round((1 - not_null / n) * 100, 1)

    sources = df["source_website"].value_counts().to_dict() if "source_website" in df.columns else {}
    locations = (df["location_normalized"].value_counts().head(10).to_dict()
                 if "location_normalized" in df.columns else {})
    levels = (df["experience_level_inferred"].value_counts().to_dict()
              if "experience_level_inferred" in df.columns else {})

    has_salary = df.get("has_salary", pd.Series([False] * n)).sum()
    is_remote = df.get("is_remote", pd.Series([False] * n)).sum()

    return {
        "total_records": n,
        "null_percentages": null_pct,
        "by_source": sources,
        "salary_coverage_pct": round(has_salary / n * 100, 1),
        "skill_coverage_pct": round(
            (df["skill_count"] > 0).sum() / n * 100, 1
        ) if "skill_count" in df.columns else 0,
        "remote_count": int(is_remote),
        "top_locations": locations,
        "experience_level_distribution": levels,
    }


def run_pipeline(
    raw_jsonl: Path,
    processed_dir: Path,
    cleaned_dir: Path,
) -> dict:
    """Run the full preprocessing pipeline. Returns a stats/validation dict."""
    from src.preprocessing.cleaner import (
        clean_text_columns, compute_job_hash,
        drop_invalid_urls, drop_missing_titles, remove_duplicates,
    )
    from src.preprocessing.normalizer import (
        normalize_dates, normalize_experience_columns,
        normalize_location_column, normalize_salary, normalize_skills_column,
    )

    logger.info("=" * 60)
    logger.info("Phase 3: Preprocessing Pipeline")
    logger.info("=" * 60)
    stats: dict = {"input": 0, "output": 0, "steps": {}}

    logger.info("\n[1] Loading raw dataset...")
    df = load_raw_dataset(raw_jsonl)
    stats["input"] = len(df)

    logger.info("\n[2] Filtering invalid records...")
    before = len(df)
    df = drop_missing_titles(df)
    df = drop_invalid_urls(df)
    stats["steps"]["drop_invalid"] = before - len(df)
    logger.info(f"  Remaining: {len(df):,}")

    logger.info("\n[3] Cleaning text fields...")
    df = clean_text_columns(df)
    df = compute_job_hash(df)

    logger.info("\n[4] Removing duplicates...")
    before = len(df)
    df = remove_duplicates(df)
    stats["steps"]["dedup"] = before - len(df)
    logger.info(f"  Remaining: {len(df):,}")

    logger.info("\n[5] Normalizing salaries...")
    df = normalize_salary(df)

    logger.info("\n[6] Normalizing locations...")
    df = normalize_location_column(df)

    logger.info("\n[7] Normalizing skills...")
    df = normalize_skills_column(df)

    logger.info("\n[8] Normalizing experience...")
    df = normalize_experience_columns(df)

    logger.info("\n[9] Normalizing dates...")
    df = normalize_dates(df)

    stats["output"] = len(df)

    logger.info("\n[10] Validating dataset...")
    validation = validate_dataset(df)
    logger.info(f"\n  Total records       : {validation['total_records']:,}")
    logger.info(f"  Salary coverage     : {validation['salary_coverage_pct']}%")
    logger.info(f"  Skill coverage      : {validation['skill_coverage_pct']}%")
    logger.info(f"  Remote jobs         : {validation['remote_count']}")
    logger.info(f"\n  By source:")
    for src, cnt in sorted(validation["by_source"].items(), key=lambda x: -x[1]):
        logger.info(f"    {src:<20}: {cnt:>5}")
    logger.info(f"\n  Null percentages (key fields):")
    for col, pct in validation["null_percentages"].items():
        icon = "" if pct < 30 else ("~" if pct < 60 else "!")
        logger.info(f"    {icon} {col:<30}: {pct}%")
    logger.info(f"\n  Top locations:")
    for loc, cnt in list(validation["top_locations"].items())[:8]:
        logger.info(f"    {loc:<30}: {cnt}")
    logger.info(f"\n  Experience levels:")
    for lvl, cnt in sorted(validation["experience_level_distribution"].items(),
                           key=lambda x: -x[1]):
        logger.info(f"    {lvl:<15}: {cnt}")

    logger.info("\n[11] Exporting datasets...")
    processed_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    _EXPORT_COLS = [
        "job_id", "job_hash", "job_title", "company_name", "company_name_normalized",
        "salary", "salary_min_usd", "salary_max_usd", "salary_midpoint_usd",
        "salary_currency_norm", "has_salary", "is_negotiable",
        "location", "location_normalized", "is_remote",
        "employment_type", "job_level",
        "skills_str", "skill_count",
        "experience_years_parsed", "experience_level_inferred",
        "job_description", "benefits",
        "posted_date", "posted_date_dt", "expiry_date", "expiry_date_dt",
        "days_since_posted",
        "url", "source_website", "industry", "job_type",
        "data_completeness", "crawled_at",
        "is_active", "in_analysis_period",
    ]
    export_cols = [c for c in _EXPORT_COLS if c in df.columns]
    df_export = df[export_cols].copy()

    # CSV needs string-ified datetimes
    df_csv = df_export.copy()
    for col in df_csv.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        df_csv[col] = df_csv[col].astype(str)

    # Processed (full normalized)
    proc_csv = processed_dir / "jobs_processed.csv"
    proc_parquet = processed_dir / "jobs_processed.parquet"
    df_csv.to_csv(proc_csv, index=False, encoding="utf-8-sig")
    df_export.to_parquet(proc_parquet, index=False)
    logger.info(f"  Processed: {proc_csv.name} + {proc_parquet.name} ({len(df_export):,} rows)")

    # Cleaned (only records with title+company+url present)
    mask_clean = (
        df["job_title"].notna() & (df["job_title"].str.strip() != "")
        & df["company_name"].notna() & (df["company_name"].str.strip() != "")
        & df["url"].notna()
    )
    df_clean = df_export[mask_clean].copy()
    df_csv_clean = df_csv[mask_clean].copy()
    clean_csv = cleaned_dir / "jobs_cleaned.csv"
    clean_parquet = cleaned_dir / "jobs_cleaned.parquet"
    df_csv_clean.to_csv(clean_csv, index=False, encoding="utf-8-sig")
    df_clean.to_parquet(clean_parquet, index=False)
    logger.info(f"  Cleaned : {clean_csv.name} + {clean_parquet.name} ({len(df_clean):,} rows)")

    stats["validation"] = validation
    stats["output_files"] = {
        "processed_csv": str(proc_csv),
        "processed_parquet": str(proc_parquet),
        "cleaned_csv": str(clean_csv),
        "cleaned_parquet": str(clean_parquet),
    }

    logger.info("\n" + "=" * 60)
    logger.info(f"Phase 3 COMPLETE — {stats['output']:,} records processed")
    logger.info("=" * 60)
    return stats
