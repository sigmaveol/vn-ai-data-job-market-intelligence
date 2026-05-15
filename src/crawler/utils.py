"""Shared crawler utilities: HTTP, HTML parsing, salary parsing, deduplication."""
import hashlib
import logging
import re
import time
import unicodedata
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def get_session(user_agent: str) -> requests.Session:
    """Return a requests.Session with browser-like headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return session


def safe_get(
    session: requests.Session,
    url: str,
    timeout: int = 15,
    retries: int = 3,
    delay: float = 2.0,
) -> Optional[requests.Response]:
    """GET with exponential back-off retry. Returns None after all retries fail."""
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response
        except requests.exceptions.HTTPError as e:
            # 404/410 → stop retrying immediately
            if e.response is not None and e.response.status_code in (404, 410):
                logger.debug(f"Skip {url}: HTTP {e.response.status_code}")
                return None
            logger.warning(f"HTTP error on {url} (attempt {attempt+1}/{retries}): {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error on {url} (attempt {attempt+1}/{retries}): {e}")

        if attempt < retries - 1:
            wait = delay * (2 ** attempt)   # exponential back-off
            logger.debug(f"Retrying in {wait}s …")
            time.sleep(wait)

    logger.error(f"All retries exhausted for {url}")
    return None


# ── HTML helpers ──────────────────────────────────────────────────────────────

def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def strip_html(html: str) -> str:
    """Remove HTML tags, collapse whitespace, return plain text."""
    if not html:
        return ""
    text = BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)
    return re.sub(r"\s{2,}", " ", text).strip()


def normalize_url(base: str, href: str) -> str:
    """Resolve a relative href against a base URL."""
    return urljoin(base, href)


def is_valid_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


# ── Deduplication ─────────────────────────────────────────────────────────────

def compute_job_id(url: str, title: str, company: str) -> str:
    """
    Deterministic MD5 ID for deduplication.
    Uses URL + normalized title + normalized company name.
    """
    raw = "|".join([
        url.strip().lower(),
        title.strip().lower(),
        company.strip().lower(),
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ── Salary parsing ────────────────────────────────────────────────────────────

def _strip_diacritics(text: str) -> str:
    """'thỏa thuận' → 'thoa thuan' for robust keyword matching."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


_NEGOTIABLE_KEYWORDS = (
    # Vietnamese negotiable phrases
    "thỏa thuận", "thoả thuận", "thoa thuan",
    "cạnh tranh", "canh tranh",
    "hấp dẫn", "hap dan",
    # English negotiable phrases
    "negotiate", "negotiable",
    "competitive", "attractive",
    "market rate", "based on", "according to",
    # ITviec-specific vague salary strings
    "you'll love it", "you will love it",
    "sign in to view", "login to view",
    "see details", "to be discussed",
    "upon interview", "upto",
)

def extract_salary_numbers(
    text: str,
) -> tuple[Optional[float], Optional[float], str]:
    """
    Parse salary strings into (salary_min, salary_max, currency).

    Handled patterns:
        '$1,000 - $2,000'     → (1000.0, 2000.0, 'USD')
        '1000 - 2000 USD'     → (1000.0, 2000.0, 'USD')
        'Up to $3,000'        → (0.0,    3000.0, 'USD')
        '20 - 30 triệu'       → (20_000_000.0, 30_000_000.0, 'VND')
        '500 - 700 nghìn đồng'→ (500_000.0, 700_000.0, 'VND')
        'Thỏa thuận'          → (None, None, 'negotiable')
        ''                    → (None, None, '')
    """
    if not text:
        return None, None, ""

    text_lower = _strip_diacritics(text.lower().strip())

    if any(kw in text_lower for kw in _NEGOTIABLE_KEYWORDS):
        return None, None, "negotiable"

    # Detect currency
    if "$" in text or "usd" in text_lower:
        currency = "USD"
        multiplier = 1.0
    elif any(kw in text_lower for kw in ("triệu", "million", " tr ")):
        currency = "VND"
        multiplier = 1_000_000.0
    elif any(kw in text_lower for kw in ("nghìn", "thousand", "k vnd")):
        currency = "VND"
        multiplier = 1_000.0
    else:
        currency = "VND"
        multiplier = 1_000_000.0   # default assume millions for VND job boards

    # Extract all numbers (handles commas as thousands separators)
    raw_numbers = re.findall(r"\d[\d,\.]*", text)
    numbers: list[float] = []
    for n in raw_numbers:
        cleaned = n.replace(",", "")
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue

    if not numbers:
        return None, None, currency

    sal_min = numbers[0] * multiplier
    sal_max = numbers[-1] * multiplier if len(numbers) > 1 else sal_min

    # Sanity: ensure min <= max
    if sal_min > sal_max:
        sal_min, sal_max = sal_max, sal_min

    return round(sal_min, 2), round(sal_max, 2), currency


# ── File naming ───────────────────────────────────────────────────────────────

def timestamped_filename(source: str, ext: str = "jsonl") -> str:
    """Return filename like 'itviec_jobs_2026_05_14.jsonl'."""
    from datetime import datetime
    date = datetime.now().strftime("%Y_%m_%d")
    return f"{source}_jobs_{date}.{ext}"
