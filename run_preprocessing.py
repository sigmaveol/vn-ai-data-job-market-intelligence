"""
Phase 3 entry point: Run full preprocessing pipeline.

Usage:
    python run_preprocessing.py
    python run_preprocessing.py --input data/raw/jobs_raw.jsonl
"""
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import DATA_RAW, DATA_PROCESSED, DATA_CLEANED

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Data Preprocessing")
    parser.add_argument(
        "--input",
        default=str(DATA_RAW / "jobs_raw.jsonl"),
        help="Path to raw JSONL input (default: data/raw/jobs_raw.jsonl)",
    )
    args = parser.parse_args()

    raw_path = Path(args.input)
    if not raw_path.exists():
        logger.error(f"Input file not found: {raw_path}")
        logger.error("Run merge_dataset.py first to create jobs_raw.jsonl")
        sys.exit(1)

    from src.preprocessing.pipeline import run_pipeline
    stats = run_pipeline(raw_path, DATA_PROCESSED, DATA_CLEANED)

    # Print summary
    v = stats.get("validation", {})
    print("\n" + "=" * 55)
    print("PHASE 3 PREPROCESSING SUMMARY")
    print("=" * 55)
    print(f"  Records in    : {stats['input']:>6,}")
    print(f"  Records out   : {stats['output']:>6,}")
    print(f"  Dropped       : {stats['input'] - stats['output']:>6,}")
    print(f"  Salary filled : {v.get('salary_coverage_pct', 0):>5.1f}%")
    print(f"  Skill filled  : {v.get('skill_coverage_pct', 0):>5.1f}%")
    print(f"  Remote jobs   : {v.get('remote_count', 0):>6,}")
    print(f"\n  Output files:")
    for k, p in stats.get("output_files", {}).items():
        print(f"    {Path(p).name}")
    print("=" * 55)


if __name__ == "__main__":
    main()
