"""Salary Analytics page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Phân Tích Lương", page_icon="💰", layout="wide")

from utils.style import inject_css, insight_panel, page_header, empty_state, C
from utils.data_loader import get_filtered_df, get_salary_df, high_paying_skills, EXP_ORDER
from utils.charts import histogram_chart, boxplot_chart, hbar, PLOTLY_CONFIG
from utils.export import filtered_jobs_export, render_chart_download, render_csv_download, dated_file_name
from utils.sidebar import render_sidebar
from utils import insights

inject_css()
render_sidebar()

df     = get_filtered_df()
df_sal = get_salary_df(df)

page_header("💰 Phân Tích Lương & Compensation",
            f"{len(df_sal):,} tin có công bố lương / {len(df):,} tin đang lọc")

if df.empty:
    empty_state()
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
if len(df_sal):
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Lương trung vị", f"${df_sal['salary_midpoint_usd'].median():,.0f}")
    k2.metric("Lương trung bình", f"${df_sal['salary_midpoint_usd'].mean():,.0f}")
    k3.metric("Lương cao nhất", f"${df_sal['salary_midpoint_usd'].quantile(0.95):,.0f} (P95)")
    k4.metric("Tỷ lệ công bố lương", f"{100*len(df_sal)/len(df):.1f}%")
else:
    empty_state(
        "Không có dữ liệu lương",
        "Bộ lọc hiện tại vẫn có tin tuyển dụng, nhưng không có bản ghi công bố lương để phân tích.",
    )
    render_csv_download(
        filtered_jobs_export(df),
        "Download CSV (tin đang lọc)",
        dated_file_name("salary_no_salary_filtered_jobs"),
        key="salary_no_salary_jobs_csv",
    )
    st.stop()

st.divider()

# ── Row 1: histogram + boxplot by exp ──────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Phân Bố Mức Lương (USD/tháng)**")
    fig = histogram_chart(df_sal['salary_midpoint_usd'], height=320, color=C['accent'])
    fig.update_layout(
        xaxis_title="USD/tháng",
        yaxis_title="Số tin",
        shapes=[dict(type='line', x0=df_sal['salary_midpoint_usd'].median(),
                     x1=df_sal['salary_midpoint_usd'].median(), y0=0, y1=1,
                     yref='paper', line=dict(color=C['green'], width=2, dash='dash'))],
        annotations=[dict(x=df_sal['salary_midpoint_usd'].median(), y=1, yref='paper',
                          text=f" Trung vị ${df_sal['salary_midpoint_usd'].median():,.0f}",
                          showarrow=False, font_color=C['green'], xanchor='left')]
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig, "salary_distribution.png", key="salary_distribution_png")

with col2:
    st.markdown("**Lương Theo Cấp Độ Kinh Nghiệm**")
    fig2 = boxplot_chart(df_sal, 'experience_level_inferred', 'salary_midpoint_usd',
                         height=320, order=EXP_ORDER)
    fig2.update_layout(yaxis_title="USD/tháng", xaxis_title="")
    st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig2, "salary_by_experience.png", key="salary_experience_png")

# ── Row 2: salary by role + salary by city ────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.markdown("**Lương Trung Vị Theo Vai Trò**")
    role_sal = (df_sal.groupby('role_category')['salary_midpoint_usd']
                .median().sort_values(ascending=False).head(10).reset_index())
    role_sal.columns = ['Vai trò', 'Lương trung vị (USD)']
    role_sal['Lương trung vị (USD)'] = role_sal['Lương trung vị (USD)'].round(0)
    fig3 = hbar(role_sal, 'Lương trung vị (USD)', 'Vai trò', height=340, color=C['accent'])
    fig3.update_layout(xaxis_title="USD/tháng")
    st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig3, "salary_by_role.png", key="salary_role_png")

with col4:
    st.markdown("**Lương Trung Vị Theo Thành Phố (Top 8)**")
    top_cities = df_sal['city'].value_counts().head(8).index.tolist()
    city_sal = (df_sal[df_sal['city'].isin(top_cities)]
                .groupby('city')['salary_midpoint_usd']
                .agg(['median', 'count'])
                .sort_values('median', ascending=False).reset_index())
    city_sal.columns = ['Thành phố', 'Lương trung vị (USD)', 'Số mẫu']
    fig4 = hbar(city_sal, 'Lương trung vị (USD)', 'Thành phố', height=340, color=C['orange'])
    fig4.update_layout(xaxis_title="USD/tháng")
    st.plotly_chart(fig4, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig4, "salary_by_city.png", key="salary_city_png")

# ── Row 3: top-paying skills ───────────────────────────────────────────────────
st.markdown("**Top 15 Kỹ Năng Được Trả Lương Cao Nhất** *(trung vị, min 15 tin có lương)*")
hp = high_paying_skills(df_sal)
if not hp.empty:
    hp_plot = hp[['skill', 'median_salary']].rename(columns={'skill': 'Kỹ năng', 'median_salary': 'Lương trung vị (USD)'})
    fig5 = hbar(hp_plot, 'Lương trung vị (USD)', 'Kỹ năng', height=400, color=C['green'])
    fig5.update_layout(xaxis_title="USD/tháng")
    st.plotly_chart(fig5, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig5, "salary_high_paying_skills.png", key="salary_skills_png")
else:
    st.info("Không đủ dữ liệu để tính lương theo kỹ năng.")

# ── Raw data download ──────────────────────────────────────────────────────────
with st.expander("📥 Export dữ liệu lương"):
    c1, c2 = st.columns(2)
    with c1:
        render_csv_download(
            filtered_jobs_export(df_sal),
            "Download CSV (dữ liệu lương đã lọc)",
            dated_file_name("salary_filtered_jobs"),
            key="salary_jobs_csv",
        )
    with c2:
        render_csv_download(
            hp if not hp.empty else pd.DataFrame(),
            "Download CSV (lương theo kỹ năng)",
            dated_file_name("salary_by_skill"),
            key="salary_skill_csv",
            disabled=hp.empty,
        )

insight_panel(insights.SALARY)
