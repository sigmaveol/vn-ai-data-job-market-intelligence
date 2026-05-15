"""Abstract base class shared by all crawlers."""
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    total_fetched: int = 0
    total_saved: int = 0
    total_duplicates: int = 0
    total_irrelevant: int = 0
    total_errors: int = 0
    total_expired: int = 0
    total_out_of_period: int = 0
    failed_urls: list[str] = field(default_factory=list)

    def report(self) -> str:
        return (
            f"  Fetched        : {self.total_fetched}\n"
            f"  Saved          : {self.total_saved}\n"
            f"  Duplicates     : {self.total_duplicates}\n"
            f"  Irrelevant     : {self.total_irrelevant}\n"
            f"  Expired        : {self.total_expired}\n"
            f"  Out-of-period  : {self.total_out_of_period}\n"
            f"  Errors         : {self.total_errors}\n"
            f"  Failed URLs    : {len(self.failed_urls)}"
        )


class BaseCrawler(ABC):
    """
    All crawlers inherit from this class.
    Subclasses implement `iter_job_urls` and `parse_job_page`.
    """

    source_name: str = ""
    base_url: str = ""

    def __init__(self, output_path: Path, delay: float = 2.0):
        from src.crawler.utils import get_session
        from config import USER_AGENT

        self.output_path = Path(output_path)
        self.delay = delay
        self.session = get_session(USER_AGENT)
        self._seen_ids: set[str] = set()
        self.stats = CrawlStats()

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing job_ids so cross-run duplicates are skipped automatically
        self._load_existing_ids()

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def iter_job_urls(self) -> Iterator[str]:
        """Yield absolute URLs of individual job listing pages."""
        ...

    @abstractmethod
    def parse_job_page(self, url: str, html: str) -> dict:
        """
        Parse a single job page and return a dict matching JOB_SCHEMA_FIELDS.
        Return an empty dict if the page cannot be parsed.
        """
        ...

    # ── Crawl orchestration ───────────────────────────────────────────────────

    def run(self, max_jobs: int = 500) -> list[dict]:
        """
        Main crawl loop:
          1. iterate URLs from iter_job_urls()
          2. fetch each page with retry
          3. parse via parse_job_page()
          4. deduplicate
          5. filter relevance
          6. enrich metadata
          7. append to JSONL output
        """
        from src.crawler.utils import safe_get, compute_job_id
        from src.crawler.date_utils import annotate_time_fields
        from config import REQUEST_TIMEOUT, ANALYSIS_START_DATE, ANALYSIS_END_DATE

        logger.info(f"[{self.source_name}] Starting crawl — max_jobs={max_jobs}")
        jobs: list[dict] = []

        for url in self.iter_job_urls():
            if len(jobs) >= max_jobs:
                logger.info(f"[{self.source_name}] Reached max_jobs={max_jobs}, stopping.")
                break

            self.stats.total_fetched += 1

            try:
                response = safe_get(self.session, url, timeout=REQUEST_TIMEOUT)
                if response is None:
                    self.stats.total_errors += 1
                    self.stats.failed_urls.append(url)
                    continue

                job = self.parse_job_page(url, response.text)
                if not job:
                    self.stats.total_errors += 1
                    continue

                # ── Enrich with crawl metadata ────────────────────────────────
                job.setdefault("url", url)
                job.setdefault("source_website", self.source_name)
                job["crawled_at"] = datetime.now(timezone.utc).isoformat()

                # ── Deduplication ─────────────────────────────────────────────
                job_id = compute_job_id(
                    job.get("url", url),
                    job.get("job_title", ""),
                    job.get("company_name", ""),
                )
                if job_id in self._seen_ids:
                    logger.debug(f"[{self.source_name}] Duplicate: {url}")
                    self.stats.total_duplicates += 1
                    continue
                self._seen_ids.add(job_id)
                job["job_id"] = job_id

                # ── Relevance filter ──────────────────────────────────────────
                if not self._is_relevant(job):
                    logger.debug(f"[{self.source_name}] Irrelevant: {job.get('job_title')}")
                    self.stats.total_irrelevant += 1
                    continue

                # ── Ensure list type for skills ───────────────────────────────
                if isinstance(job.get("skills_required"), str):
                    job["skills_required"] = [
                        s.strip() for s in job["skills_required"].split(",") if s.strip()
                    ]

                # ── Time validation flags ─────────────────────────────────────
                annotate_time_fields(job, ANALYSIS_START_DATE, ANALYSIS_END_DATE)

                # Hard-skip confirmed expired jobs (known expiry date < today)
                if job.get("expiry_date_status") == "expired":
                    logger.debug(
                        f"[{self.source_name}] Expired: {job.get('job_title')}"
                    )
                    self.stats.total_expired += 1
                    continue

                # Warn (but keep) out-of-period jobs — preprocessing decides final filter
                if job.get("in_analysis_period") is False:
                    self.stats.total_out_of_period += 1

                jobs.append(job)
                self._append_to_file(job)
                self.stats.total_saved += 1

                active_tag = {True: "active", False: "inactive", None: "unknown"}[job.get("is_active")]
                period_tag = "in-period" if job.get("in_analysis_period") else (
                    "out-of-range" if job.get("in_analysis_period") is False else "date-unknown"
                )
                logger.info(
                    f"[{self.source_name}] [{len(jobs):03d}] "
                    f"[{active_tag}|{period_tag}] "
                    f"{job.get('job_title', 'N/A')} @ {job.get('company_name', 'N/A')}"
                )

            except Exception as e:
                logger.error(f"[{self.source_name}] Unexpected error on {url}: {e}", exc_info=True)
                self.stats.total_errors += 1

            time.sleep(self.delay)

        logger.info(
            f"[{self.source_name}] Crawl complete.\n{self.stats.report()}"
        )
        return jobs

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_relevant(self, job: dict) -> bool:
        """Return True if the job is within AI/Data scope."""
        from config import VALID_JOB_TITLES, VALID_JOB_KEYWORDS

        title = (job.get("job_title") or "").lower()
        desc  = (job.get("job_description") or "").lower()[:500]  # check only first 500 chars

        title_match   = any(t.lower() in title for t in VALID_JOB_TITLES)
        keyword_match = any(kw in title or kw in desc for kw in VALID_JOB_KEYWORDS)
        return title_match or keyword_match

    def _load_existing_ids(self) -> None:
        """
        Read job_ids already in the output file into _seen_ids.
        Prevents cross-run duplicates when appending to an existing JSONL file.
        """
        if not self.output_path.exists():
            return
        count = 0
        with open(self.output_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    job = json.loads(line)
                    job_id = job.get("job_id")
                    if job_id:
                        self._seen_ids.add(job_id)
                        count += 1
                except json.JSONDecodeError:
                    pass
        if count:
            logger.info(f"[{self.source_name}] Resuming: loaded {count} existing IDs from {self.output_path.name}")

    def _append_to_file(self, job: dict) -> None:
        """Append one job record as a JSONL line (never overwrites existing data)."""
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(job, ensure_ascii=False) + "\n")

    def validate_output(self) -> dict:
        """
        Read output JSONL and return basic quality metrics.
        Call after run() to check dataset health.
        """
        import pandas as pd
        from config import JOB_SCHEMA_FIELDS

        if not self.output_path.exists():
            return {"error": "Output file not found"}

        df = pd.read_json(self.output_path, lines=True)
        missing_cols = [c for c in JOB_SCHEMA_FIELDS if c not in df.columns]

        # Time field summaries (only if flags present)
        time_summary: dict = {}
        if "posted_date_status" in df.columns:
            time_summary["posted_date_status"] = df["posted_date_status"].value_counts().to_dict()
        if "expiry_date_status" in df.columns:
            time_summary["expiry_date_status"] = df["expiry_date_status"].value_counts().to_dict()
        if "is_active" in df.columns:
            time_summary["is_active"] = df["is_active"].value_counts(dropna=False).to_dict()
        if "in_analysis_period" in df.columns:
            time_summary["in_analysis_period"] = df["in_analysis_period"].value_counts(dropna=False).to_dict()

        return {
            "total_records": len(df),
            "columns_present": list(df.columns),
            "missing_schema_fields": missing_cols,
            "null_title_pct": round(df["job_title"].isna().mean() * 100, 1) if "job_title" in df else None,
            "null_salary_pct": round(df["salary_min"].isna().mean() * 100, 1) if "salary_min" in df else None,
            "sources": df["source_website"].value_counts().to_dict() if "source_website" in df else {},
            **time_summary,
        }
