"""
Date parsing and time-window validation for crawled job records.

Responsibilities:
- Parse relative date strings ("3 days ago", "1 tuần trước")
- Parse absolute date strings (ISO, Vietnamese formats)
- Annotate each job with is_active / posted_date_status / expiry_date_status
- Determine whether a job falls within the analysis period

Analysis period: 2025-01-01 → 2026-05-14 (configurable via config.py)
"""
import re
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ── Relative date patterns ────────────────────────────────────────────────────

_RELATIVE_PATTERNS: list[tuple[re.Pattern, str, int]] = [
    # (pattern, unit, multiplier)
    (re.compile(r"(\d+)\s*(?:day|ngày|days)\s*ago",             re.I), "day",   1),
    (re.compile(r"(\d+)\s*(?:week|tuần|weeks)\s*ago",           re.I), "week",  7),
    (re.compile(r"(\d+)\s*(?:month|tháng|months)\s*ago",        re.I), "month", 30),
    (re.compile(r"(\d+)\s*(?:hour|giờ|hours)\s*ago",            re.I), "hour",  0),
    (re.compile(r"(\d+)\s*(?:minute|phút|minutes)\s*ago",       re.I), "min",   0),
    # Vietnamese variants
    (re.compile(r"(\d+)\s*ngày\s*trước",                        re.I), "day",   1),
    (re.compile(r"(\d+)\s*tuần\s*trước",                        re.I), "week",  7),
    (re.compile(r"(\d+)\s*tháng\s*trước",                       re.I), "month", 30),
]

_TODAY_PATTERNS = re.compile(
    r"\b(today|hôm nay|just now|vừa đăng|vừa xong)\b", re.I
)
_YESTERDAY_PATTERNS = re.compile(
    r"\b(yesterday|hôm qua|1\s*day\s*ago|1\s*ngày\s*trước)\b", re.I
)

# ── Absolute date formats ─────────────────────────────────────────────────────

_ABSOLUTE_FORMATS = [
    "%Y-%m-%d",         # ISO: 2026-01-15
    "%d/%m/%Y",         # Vietnamese: 15/01/2026
    "%d-%m-%Y",         # 15-01-2026
    "%Y/%m/%d",         # 2026/01/15
    "%d %b %Y",         # 15 Jan 2026
    "%d %B %Y",         # 15 January 2026
    "%b %d, %Y",        # Jan 15, 2026
    "%B %d, %Y",        # January 15, 2026
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
]


# ── Core parsing functions ────────────────────────────────────────────────────

def parse_absolute_date(text: str) -> Optional[date]:
    """Try each known format; return the first successful parse, else None."""
    text = text.strip()
    for fmt in _ABSOLUTE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_relative_date(text: str, reference: date) -> Optional[date]:
    """
    Convert relative strings like '3 days ago' to an absolute date.
    Uses `reference` as the anchor (typically crawled_at date).
    Returns None if text does not match any relative pattern.
    """
    if not text:
        return None

    if _TODAY_PATTERNS.search(text):
        return reference

    if _YESTERDAY_PATTERNS.search(text):
        return reference - timedelta(days=1)

    for pattern, unit, multiplier in _RELATIVE_PATTERNS:
        m = pattern.search(text)
        if m:
            n = int(m.group(1))
            if unit in ("hour", "min"):
                return reference   # same day
            delta_days = n * multiplier
            return reference - timedelta(days=delta_days)

    return None


def parse_posted_date(
    raw_text: str, crawled_at_iso: str
) -> tuple[Optional[date], str]:
    """
    Parse posted_date from raw text.

    Returns:
        (parsed_date, status) where status is one of:
            'exact'     — from unambiguous absolute date string
            'estimated' — computed from relative string ("3 days ago")
            'unknown'   — could not parse
    """
    if not raw_text:
        return None, "unknown"

    # Try absolute first
    d = parse_absolute_date(raw_text)
    if d:
        return d, "exact"

    # Try relative
    try:
        reference = datetime.fromisoformat(crawled_at_iso.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        reference = date.today()

    d = parse_relative_date(raw_text, reference)
    if d:
        return d, "estimated"

    return None, "unknown"


def parse_expiry_date(raw_text: str) -> tuple[Optional[date], str]:
    """
    Parse expiry_date field.

    Returns:
        (parsed_date, status) where status is 'known' | 'unknown'
    """
    if not raw_text:
        return None, "unknown"

    d = parse_absolute_date(raw_text)
    if d:
        return d, "known"

    return None, "unknown"


# ── Main annotation function ──────────────────────────────────────────────────

def annotate_time_fields(job: dict, analysis_start: date, analysis_end: date) -> dict:
    """
    Add time-validation fields to a job dict in-place.

    Fields added:
        posted_date_parsed    — ISO date string or None
        posted_date_status    — 'exact' | 'estimated' | 'unknown' | 'out_of_range'
        expiry_date_status    — 'known' | 'unknown' | 'expired'
        is_active             — True | False | None (None = uncertain)
        in_analysis_period    — True | False | None
    """
    today = date.today()
    crawled_at = job.get("crawled_at", today.isoformat())

    # ── posted_date ───────────────────────────────────────────────────────────
    posted_raw = job.get("posted_date") or ""
    posted_date, p_status = parse_posted_date(str(posted_raw), str(crawled_at))

    if posted_date and p_status != "unknown":
        if not (analysis_start <= posted_date <= analysis_end):
            p_status = "out_of_range"

    job["posted_date_parsed"] = posted_date.isoformat() if posted_date else None
    job["posted_date_status"] = p_status

    # ── expiry_date ───────────────────────────────────────────────────────────
    expiry_raw = job.get("expiry_date") or ""
    expiry_date, e_status = parse_expiry_date(str(expiry_raw))

    if expiry_date and expiry_date < today:
        e_status = "expired"

    job["expiry_date_status"] = e_status

    # ── is_active ─────────────────────────────────────────────────────────────
    if e_status == "expired":
        is_active = False
    elif e_status == "known" and expiry_date and expiry_date >= today:
        is_active = True
    else:
        # No expiry info: assume active if posted recently enough
        if posted_date and p_status in ("exact", "estimated"):
            try:
                from config import ASSUMED_ACTIVE_DAYS
            except ImportError:
                ASSUMED_ACTIVE_DAYS = 90
            days_since_post = (today - posted_date).days
            is_active = days_since_post <= ASSUMED_ACTIVE_DAYS
        else:
            is_active = None                     # genuinely unknown

    job["is_active"] = is_active

    # ── in_analysis_period ────────────────────────────────────────────────────
    if posted_date and p_status in ("exact", "estimated"):
        job["in_analysis_period"] = analysis_start <= posted_date <= analysis_end
    else:
        job["in_analysis_period"] = None

    return job
