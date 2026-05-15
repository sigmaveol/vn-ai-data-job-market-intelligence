"""Data cleaning functions: deduplication, HTML removal, invalid record filtering."""
import hashlib
import logging
import re
from typing import Optional
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ── Text cleaning ──────────────────────────────────────────────────────────────

def remove_html_tags(text: str) -> str:
    """Strip HTML markup from job description text."""
    if not text or not isinstance(text, str):
        return ""
    if "<" not in text:
        return clean_text_field(text)
    try:
        clean = BeautifulSoup(text, "lxml").get_text(separator=" ")
    except Exception:
        clean = re.sub(r"<[^>]+>", " ", text)
    return clean_text_field(clean)


def clean_text_field(text: str) -> str:
    """Normalize whitespace and strip leading/trailing spaces."""
    if not text or not isinstance(text, str):
        return ""
    # Replace multiple whitespace/newlines with single space
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def clean_company_name(name: str) -> str:
    """Normalize company name — remove common legal suffixes for grouping."""
    if not name or not isinstance(name, str):
        return ""
    text = clean_text_field(name)
    # Normalize common Vietnamese legal forms
    for pat, repl in [
        (r"\bCÔNG TY TNHH\b", ""),
        (r"\bCÔNG TY CỔ PHẦN\b", ""),
        (r"\bCÔNG TY CP\b", ""),
        (r"\bC\.P\.\b", ""),
        (r"\bJSC\b", ""),
        (r"\bLTD\b", ""),
        (r"\bLLC\b", ""),
        (r"\bINC\b", ""),
        (r"\bCO\.\s*LTD\b", ""),
        (r"\s{2,}", " "),
    ]:
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text.strip()


# ── Row-level filters ─────────────────────────────────────────────────────────

def drop_missing_titles(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with empty or null job_title."""
    before = len(df)
    mask = df["job_title"].notna() & (df["job_title"].str.strip() != "")
    df_clean = df[mask].copy()
    dropped = before - len(df_clean)
    if dropped:
        logger.info(f"  drop_missing_titles: removed {dropped} rows")
    return df_clean


def drop_invalid_urls(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where url is missing or malformed."""
    before = len(df)
    url_pattern = re.compile(r"^https?://[^\s]+", re.IGNORECASE)
    mask = df["url"].notna() & df["url"].astype(str).str.match(url_pattern)
    df_clean = df[mask].copy()
    dropped = before - len(df_clean)
    if dropped:
        logger.info(f"  drop_invalid_urls: removed {dropped} rows")
    return df_clean


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop duplicate jobs based on (job_title, company_name, url).
    URL-based dedup first (most reliable), then title+company.
    """
    before = len(df)

    # 1. URL-based dedup (exact)
    df = df.drop_duplicates(subset=["url"], keep="first")

    # 2. Title + company dedup (normalized, catches same job on different URL)
    title_norm = df["job_title"].fillna("").str.lower().str.strip()
    company_norm = df["company_name"].fillna("").str.lower().str.strip()
    composite = title_norm + "|||" + company_norm
    df = df[~composite.duplicated(keep="first")].copy()

    dropped = before - len(df)
    if dropped:
        logger.info(f"  remove_duplicates: removed {dropped} rows")
    return df


# ── Batch cleaning ────────────────────────────────────────────────────────────

def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply HTML cleaning and whitespace normalization to text columns."""
    html_cols = ["job_description", "benefits"]
    text_cols = ["job_title", "company_name", "location", "salary",
                 "employment_type", "job_level"]

    for col in html_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").apply(remove_html_tags)

    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").apply(clean_text_field)

    # Normalized company name (for grouping, keep original company_name)
    if "company_name" in df.columns:
        df["company_name_normalized"] = df["company_name"].apply(clean_company_name)

    return df


def compute_job_hash(df: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic job_hash for cross-run deduplication."""
    def _hash(row) -> str:
        key = f"{row.get('url','')}{row.get('job_title','')}{row.get('company_name','')}"
        return hashlib.md5(key.encode()).hexdigest()
    df["job_hash"] = df.apply(_hash, axis=1)
    return df
