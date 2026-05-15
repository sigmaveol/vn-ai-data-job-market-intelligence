"""Company Analytics page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Phân Tích Doanh Nghiệp", page_icon="🏢", layout="wide")

from utils.style import inject_css, insight_panel, page_header, empty_state, C
from utils.data_loader import get_filtered_df
from utils.charts import hbar, pie_donut, grouped_bar, PLOTLY_CONFIG
from utils.export import filtered_jobs_export, render_chart_download, render_csv_download, dated_file_name
from utils.sidebar import render_sidebar
from utils import insights

inject_css()
render_sidebar()
df = get_filtered_df()

page_header("🏢 Phân Tích Doanh Nghiệp",
            f"{df['company_name'].nunique():,} doanh nghiệp · {len(df):,} tin tuyển dụng")

if df.empty:
    empty_state()
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
top_co_name = df['company_name'].value_counts().index[0] if len(df) else '—'
avg_per_co  = len(df) / df['company_name'].nunique() if df['company_name'].nunique() else 0
remote_pct  = 100 * df['is_remote'].sum() / len(df) if len(df) else 0

k1.metric("Tổng doanh nghiệp", f"{df['company_name'].nunique():,}")
k2.metric("Top nhà tuyển dụng", str(top_co_name)[:20])
k3.metric("Tin/công ty (TB)", f"{avg_per_co:.1f}")
k4.metric("Tỷ lệ Remote", f"{remote_pct:.1f}%")

st.divider()

# ── Row 1: top companies + remote pie ─────────────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("**Top 15 Công Ty Tuyển Dụng Nhiều Nhất**")
    co_vc = df['company_name'].value_counts().head(15).reset_index()
    co_vc.columns = ['Công ty', 'Số tin']
    fig = hbar(co_vc, 'Số tin', 'Công ty', height=440, color=C['accent'])
    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig, "company_top_hiring.png", key="company_top_png")

with col2:
    st.markdown("**Remote vs Onsite**")
    r_counts = df['is_remote'].value_counts()
    labels = ['Remote' if k else 'Onsite' for k in r_counts.index]
    fig2 = pie_donut(labels, r_counts.values.tolist(), height=240)
    st.plotly_chart(fig2, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig2, "company_remote_onsite.png", key="company_remote_png")

    st.markdown("**Phân Bổ Theo Nguồn**")
    src_vc = df['source_website'].value_counts()
    fig3 = pie_donut(src_vc.index.tolist(), src_vc.values.tolist(), height=240)
    st.plotly_chart(fig3, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig3, "company_sources.png", key="company_sources_png")

# ── Role specialization by top companies ──────────────────────────────────────
st.markdown("**Chuyên Môn Hóa Theo Vai Trò — Top 8 Công Ty**")
top8_co = df['company_name'].value_counts().head(8).index.tolist()
top6_roles = df['role_category'].value_counts().head(6).index.tolist()
df_sub = df[df['company_name'].isin(top8_co)]
pivot = df_sub.groupby(['company_name', 'role_category']).size().unstack(fill_value=0)
pivot = pivot[[r for r in top6_roles if r in pivot.columns]]

if not pivot.empty:
    cats = pivot.index.tolist()
    groups = {role: pivot[role].tolist() for role in pivot.columns}
    fig4 = grouped_bar(cats, groups, height=360)
    fig4.update_layout(
        xaxis_tickangle=-30,
        legend_title='Vai trò',
        barmode='stack',
    )
    st.plotly_chart(fig4, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig4, "company_role_specialization.png", key="company_roles_png")

with st.expander("📥 Export danh sách công ty"):
    co_export = df.groupby('company_name').agg(
        so_tin=('job_title', 'count'),
        vai_tro_chinh=('role_category', lambda x: x.value_counts().index[0]),
        thanh_pho=('city', lambda x: x.value_counts().index[0] if len(x) else ''),
    ).sort_values('so_tin', ascending=False).reset_index()
    c1, c2 = st.columns(2)
    with c1:
        render_csv_download(
            co_export,
            "Download CSV (phân tích công ty)",
            dated_file_name("company_analysis"),
            key="company_analysis_csv",
        )
    with c2:
        render_csv_download(
            filtered_jobs_export(df),
            "Download CSV (tin đang lọc)",
            dated_file_name("company_filtered_jobs"),
            key="company_jobs_csv",
        )

insight_panel(insights.COMPANY)
