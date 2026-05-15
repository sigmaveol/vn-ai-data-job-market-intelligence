"""Export & Sharing page — Centralized export hub."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Export & Sharing",
    page_icon="📤",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.style import inject_css, insight_panel, page_header, empty_state
from utils.data_loader import get_filtered_df
from utils.export import filtered_jobs_export, render_chart_download, render_csv_download, dated_file_name

inject_css()

df = get_filtered_df()

# ── Header ─────────────────────────────────────────────────────────────────────
page_header(
    "📤 Xuất Dữ Liệu & Chia Sẻ",
    f"Xuất dữ liệu đã lọc ({len(df):,} tin tuyển dụng) · Chia sẻ insights · Tạo báo cáo"
)

if df.empty:
    empty_state()
    st.stop()

# ── Export Options ─────────────────────────────────────────────────────────────
st.markdown("### 📊 Xuất Dữ Liệu")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Dữ liệu tuyển dụng đã lọc**")
    st.markdown("Xuất toàn bộ dataset đã áp dụng bộ lọc sidebar.")
    render_csv_download(
        filtered_jobs_export(df),
        dated_file_name("filtered_jobs"),
        key="export_filtered_jobs"
    )

with col2:
    st.markdown("**Tóm tắt thống kê**")
    st.markdown("Xuất các chỉ số KPI và thống kê tổng quan.")
    summary_data = {
        "Metric": ["Total Jobs", "Companies", "Cities", "Sources", "Avg Salary (USD)"],
        "Value": [
            len(df),
            df['company_name'].nunique(),
            df['city'].nunique(),
            df['source_website'].nunique(),
            f"{df['salary_midpoint_usd'].mean():.0f}" if len(df) > 0 else "N/A"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    render_csv_download(
        summary_df,
        dated_file_name("summary_stats"),
        key="export_summary"
    )

# ── Sharing & Documentation ────────────────────────────────────────────────────
st.markdown("### 📋 Chia Sẻ & Tài Liệu")

st.markdown("**Screenshots cho báo cáo**")
st.markdown("Mở các trang khác trong sidebar để chụp ảnh màn hình cho báo cáo/slides.")

st.markdown("**Tài liệu dự án**")
st.info("📄 Xem README.md và DEPLOYMENT.md trong thư mục gốc cho hướng dẫn triển khai và tài liệu kỹ thuật.")

st.markdown("**Phiên bản production**")
st.markdown("Dashboard này đã sẵn sàng deploy lên Streamlit Cloud hoặc Render. Xem DEPLOYMENT.md để biết chi tiết.")