"""
LLM-based field extractor using DeepSeek API (OpenAI-compatible).

Purpose: Enrich crawled job records with fields that regex/DOM parsing misses:
  - experience_years_min / experience_years_max
  - experience_level (Intern / Junior / Mid / Senior / Lead)
  - skills_required (comprehensive list from full description text)
  - salary_text (when hidden from structured data but mentioned in description)

Cost estimate (DeepSeek-V3, ~$0.28/1M input tokens):
  500 jobs × ~800 tokens/call = 400K tokens ≈ $0.11 total

Usage:
    extractor = LLMExtractor()
    job = extractor.enrich(job)         # enriches a single record in-place
    jobs = extractor.enrich_batch(jobs) # enriches a list of records
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Load DEEPSEEK_API_KEY from environment or .env file
def _load_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    return key


_SYSTEM_PROMPT = """You are a precise job posting data extractor.
Extract structured information from the given job title and description.
Return ONLY valid JSON, no explanation or markdown.
All monetary values must be in USD/month."""

_USER_TEMPLATE = """\
Job title: {title}

Job description (up to 2000 chars):
{description}

Extract and return this exact JSON:
{{
  "experience_years_min": <float or null — minimum years of experience required>,
  "experience_years_max": <float or null — maximum years, null if open-ended>,
  "experience_level": "<one of: Intern, Junior, Mid, Senior, Lead>",
  "skills_required": [<list of technical skills: languages, frameworks, tools, platforms, libraries>],
  "salary_min_usd": <float or null — monthly USD salary if explicitly stated, else null>,
  "salary_max_usd": <float or null — monthly USD salary max, else null>
}}

Rules:
- experience_years_min: e.g. "1-3 years" → 1.0; "at least 2 years" → 2.0; "no experience needed" → 0.0
- experience_years_max: e.g. "1-3 years" → 3.0; "5+ years" → null (open-ended)
- experience_level: infer from title seniority words AND years (0 → Intern/Junior, 1-2 → Junior, 3-5 → Mid, 5-8 → Senior, 8+ → Lead)
- skills_required: extract EVERY technical tool/library/language mentioned, deduplicated
- salary_*_usd: only fill if explicitly stated in USD; VND salaries → null (leave for preprocessing)
"""


class LLMExtractor:
    """
    Enrich job records using DeepSeek LLM.

    Calls the API only when enrichment is needed (missing experience or thin skills list).
    Respects rate limits with configurable delay between calls.
    """

    MODEL = "deepseek-chat"          # DeepSeek-V3
    BASE_URL = "https://api.deepseek.com"
    MAX_DESC_CHARS = 2000             # truncate to control token cost
    CALL_DELAY = 0.5                  # seconds between API calls (rate limit safety)

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or _load_api_key()
        if not key:
            raise ValueError(
                "DEEPSEEK_API_KEY not found. "
                "Set it in .env or pass api_key= to LLMExtractor()."
            )
        from openai import OpenAI
        self._client = OpenAI(api_key=key, base_url=self.BASE_URL)
        self._call_count = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def enrich(self, job: dict) -> dict:
        """
        Enrich a single job record in-place.
        Returns the same dict with added/updated fields.
        Skips LLM call if experience and skills are already well-populated.
        """
        if not self._needs_enrichment(job):
            return job

        description = (job.get("job_description") or "")[:self.MAX_DESC_CHARS]
        title = job.get("job_title", "")

        extracted = self._call_llm(title, description)
        if not extracted:
            return job

        self._merge(job, extracted)
        return job

    def enrich_batch(self, jobs: list[dict], verbose: bool = True) -> list[dict]:
        """Enrich a list of job records. Shows progress."""
        total = len(jobs)
        for i, job in enumerate(jobs):
            if verbose:
                logger.info(
                    f"[LLM] Enriching {i+1}/{total}: "
                    f"{job.get('job_title','?')[:40]} @ {job.get('company_name','?')[:20]}"
                )
            self.enrich(job)
            time.sleep(self.CALL_DELAY)
        logger.info(f"[LLM] Done. Total API calls: {self._call_count}")
        return jobs

    # ── Internal ──────────────────────────────────────────────────────────────

    def _needs_enrichment(self, job: dict) -> bool:
        """Return True if the record is missing key extracted fields."""
        exp_missing   = job.get("experience_years") is None
        level_missing = not job.get("experience_level")
        skills_thin   = len(job.get("skills_required") or []) < 4
        return exp_missing or level_missing or skills_thin

    def _call_llm(self, title: str, description: str) -> Optional[dict]:
        """Call DeepSeek API and return parsed JSON dict."""
        prompt = _USER_TEMPLATE.format(
            title=title,
            description=description,
        )
        try:
            response = self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,       # deterministic extraction
                max_tokens=400,
            )
            self._call_count += 1
            raw = response.choices[0].message.content or ""
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"[LLM] JSON parse error: {e}")
        except Exception as e:
            logger.error(f"[LLM] API error: {e}")
        return None

    def _merge(self, job: dict, extracted: dict) -> None:
        """
        Merge LLM-extracted fields into job dict.
        LLM values only fill missing fields — never overwrite existing structured data
        (JSON-LD salary, etc.) unless the existing value is None/empty.
        """
        # experience_years: prefer existing if already set
        if job.get("experience_years") is None:
            val = extracted.get("experience_years_min")
            if isinstance(val, (int, float)) and val >= 0:
                job["experience_years"] = float(val)

        job["experience_years_max"] = extracted.get("experience_years_max")

        # experience_level: always set from LLM (regex-inferred is weak)
        level = extracted.get("experience_level", "")
        if level in ("Intern", "Junior", "Mid", "Senior", "Lead"):
            job["experience_level"] = level

        # skills_required: merge LLM list with existing tags (deduplicated)
        llm_skills = extracted.get("skills_required") or []
        existing = job.get("skills_required") or []
        merged = list(dict.fromkeys(existing + llm_skills))   # preserves order, dedupes
        job["skills_required"] = [s for s in merged if s and len(s) <= 80][:40]

        # salary: fill only if currently missing, and validate against realistic USD range
        # USD/month sanity bounds: $100 (absolute min) – $50,000 (very senior expat)
        # Anything outside this range is likely a VND value mis-extracted as USD → discard
        _USD_MIN = 100
        _USD_MAX = 50_000
        if job.get("salary_min") is None:
            sal_min = extracted.get("salary_min_usd")
            sal_max = extracted.get("salary_max_usd")
            if (isinstance(sal_min, (int, float))
                    and _USD_MIN <= sal_min <= _USD_MAX):
                job["salary_min"] = float(sal_min)
                sal_max_val = float(sal_max) if isinstance(sal_max, (int, float)) and sal_max <= _USD_MAX else float(sal_min)
                job["salary_max"] = sal_max_val
                job["salary_currency"] = "USD"
                job["salary"] = job["salary"] or f"{int(sal_min)} - {int(sal_max_val)} USD"
            elif isinstance(sal_min, (int, float)) and sal_min > _USD_MAX:
                logger.debug(f"[LLM] Rejected suspicious salary ${sal_min:,.0f} (likely VND mis-parsed as USD)")

        job["llm_enriched"] = True
