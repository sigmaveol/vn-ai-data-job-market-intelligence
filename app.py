"""VN Job Market Intelligence Dashboard — Overview page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(
    page_title="VN Job Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.style import inject_css, insight_panel, page_header, empty_state, C
from utils.data_loader import dataset_summary, load_data, get_filtered_df, get_salary_df, EXP_ORDER
from utils.charts import hbar, histogram_chart, pie_donut, vbar, PLOTLY_CONFIG
from utils.export import filtered_jobs_export, render_chart_download, render_csv_download, dated_file_name
from utils.sidebar import render_sidebar
from utils import insights

inject_css()
render_sidebar()

df     = get_filtered_df()
df_sal = get_salary_df(df)
n_total = len(load_data())
total_summary = dataset_summary(load_data())

# ── Header ─────────────────────────────────────────────────────────────────────
page_header(
    "📊 Tổng Quan Thị Trường AI/Data Việt Nam",
    f"{n_total:,} tin tuyển dụng · {total_summary['sources']} nền tảng · Tháng 1–5/2026 · Đang hiển thị {len(df):,}/{n_total:,} tin"
)

if df.empty:
    empty_state()
    st.stop()

# ── KPI Cards ──────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k5, k6, k7, k8 = st.columns(4)

k1.metric("Tin tuyển dụng", f"{len(df):,}")
k2.metric("Doanh nghiệp", f"{df['company_name'].nunique():,}")
k3.metric("Tỉnh/Thành phố", f"{df['city'].nunique()}")
k4.metric("Nguồn tuyển dụng", f"{df['source_website'].nunique()}")

med_sal = df_sal['salary_midpoint_usd'].median() if len(df_sal) else 0
sal_pct = 100 * len(df_sal) / len(df) if len(df) else 0

sc = Counter()
for lst in df['_skills_list']:
    sc.update(lst)
top_skill = sc.most_common(1)[0][0].title() if sc else '—'
top_co = df['company_name'].value_counts().index[0] if len(df) else '—'
top_role = df['role_category'].value_counts().index[0] if len(df) else '—'
top_city = df['city'].value_counts().index[0] if len(df) else '—'

k5.metric("Lương trung vị", f"${med_sal:,.0f}" if med_sal else "N/A")
k6.metric("Công bố lương", f"{sal_pct:.1f}%")
k7.metric("Top vai trò", str(top_role)[:22] + ('…' if len(str(top_role)) > 22 else ''))
k8.metric("Top thành phố", str(top_city)[:22] + ('…' if len(str(top_city)) > 22 else ''))

st.divider()

# ── Charts row 1 ───────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Phân Bổ Theo Vai Trò**")
    rc = df['role_category'].value_counts().head(10).reset_index()
    rc.columns = ['Vai trò', 'Số tin']
    fig = hbar(rc, 'Số tin', 'Vai trò', height=360)
    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig, "overview_roles.png", key="overview_roles_png")

with col2:
    st.markdown("**Nguồn Tuyển Dụng**")
    src = df['source_website'].value_counts()
    fig2 = pie_donut(src.index.tolist(), src.values.tolist(), height=360)
    st.plotly_chart(fig2, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig2, "overview_sources.png", key="overview_sources_png")

# ── Charts row 2 ───────────────────────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.markdown("**Cấp Độ Kinh Nghiệm**")
    exp_vc = df['experience_level_inferred'].value_counts()
    ordered = [(e, int(exp_vc.get(e, 0))) for e in EXP_ORDER if e in exp_vc.index]
    others  = [(e, int(v)) for e, v in exp_vc.items() if e not in EXP_ORDER]
    exp_df  = pd.DataFrame(ordered + others, columns=['Cấp độ', 'Số tin'])
    fig3 = vbar(exp_df, 'Cấp độ', 'Số tin', height=300)
    st.plotly_chart(fig3, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig3, "overview_experience.png", key="overview_experience_png")

with col4:
    st.markdown("**Top 10 Thành Phố**")
    city_vc = df['city'].value_counts().head(10).reset_index()
    city_vc.columns = ['Thành phố', 'Số tin']
    fig4 = hbar(city_vc, 'Số tin', 'Thành phố', height=300, color=C['blue'])
    st.plotly_chart(fig4, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig4, "overview_cities.png", key="overview_cities_png")

# ── Charts row 3 ───────────────────────────────────────────────────────────────
col5, col6 = st.columns(2)

with col5:
    st.markdown("**Phân Bố Lương (USD/tháng)**")
    if len(df_sal):
        fig5 = histogram_chart(df_sal['salary_midpoint_usd'], height=320, color=C['accent'])
        fig5.update_layout(xaxis_title="USD/tháng", yaxis_title="Số tin")
        st.plotly_chart(fig5, width='stretch', config=PLOTLY_CONFIG)
        render_chart_download(fig5, "overview_salary_distribution.png", key="overview_salary_png")
    else:
        st.info("Bộ lọc hiện tại không có tin công bố lương.")

with col6:
    st.markdown("**Top 10 Kỹ Năng**")
    skill_df = pd.DataFrame(sc.most_common(10), columns=['Kỹ năng', 'Số lần'])
    if not skill_df.empty:
        fig6 = hbar(skill_df, 'Số lần', 'Kỹ năng', height=320, color=C['green'])
        fig6.update_layout(xaxis_title="Số lần xuất hiện")
        st.plotly_chart(fig6, width='stretch', config=PLOTLY_CONFIG)
        render_chart_download(fig6, "overview_top_skills.png", key="overview_skills_png")
    else:
        st.info("Bộ lọc hiện tại không có dữ liệu kỹ năng.")

with st.expander("📥 Export dữ liệu tổng quan"):
    c1, c2 = st.columns(2)
    with c1:
        render_csv_download(
            filtered_jobs_export(df),
            "Download CSV (tin đang lọc)",
            dated_file_name("overview_filtered_jobs"),
            key="overview_jobs_csv",
        )
    with c2:
        summary = pd.concat(
            [
                rc.assign(nhom="Vai trò").rename(columns={"Vai trò": "label", "Số tin": "value"}),
                city_vc.assign(nhom="Thành phố").rename(columns={"Thành phố": "label", "Số tin": "value"}),
                skill_df.assign(nhom="Kỹ năng").rename(columns={"Kỹ năng": "label", "Số lần": "value"}),
            ],
            ignore_index=True,
        )[["nhom", "label", "value"]]
        render_csv_download(
            summary,
            "Download CSV (bảng tổng hợp)",
            dated_file_name("overview_summary"),
            key="overview_summary_csv",
        )

# ── Insight panel ──────────────────────────────────────────────────────────────
insight_panel(insights.OVERVIEW)
