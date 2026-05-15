"""Download helpers for dashboard datasets and Plotly charts."""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
import streamlit as st


DEFAULT_EXPORT_COLUMNS = [
    "job_title",
    "company_name",
    "city",
    "role_category",
    "experience_level_inferred",
    "salary_midpoint_usd",
    "skills_str",
    "source_website",
    "posted_date_dt",
    "url",
]


def slugify(value: str) -> str:
    """Create stable ASCII file names for dashboard exports."""
    value = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).lower()).strip("_")
    return value or "export"


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def filtered_jobs_export(df: pd.DataFrame) -> pd.DataFrame:
    cols = [col for col in DEFAULT_EXPORT_COLUMNS if col in df.columns]
    return df[cols].copy()


def render_csv_download(
    df: pd.DataFrame,
    label: str,
    file_name: str,
    *,
    key: str,
    disabled: bool = False,
) -> None:
    st.download_button(
        label,
        data=csv_bytes(df),
        file_name=file_name,
        mime="text/csv",
        use_container_width=True,
        key=key,
        disabled=disabled or df.empty,
    )


def render_chart_download(fig, file_name: str, *, key: str, label: str = "PNG") -> None:
    """Render a PNG download button when static Plotly export is available."""
    if not st.session_state.get('enable_png_exports', False):
        return

    try:
        data = fig.to_image(format="png", scale=2)
    except Exception:
        return

    st.download_button(
        label,
        data=data,
        file_name=file_name,
        mime="image/png",
        use_container_width=False,
        key=key,
    )


def dated_file_name(prefix: str, extension: str = "csv") -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    return f"{slugify(prefix)}_{stamp}.{extension}"
