"""Geographic Analytics page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Phân Tích Địa Lý", page_icon="🗺", layout="wide")

from utils.style import inject_css, insight_panel, page_header, empty_state, C
from utils.data_loader import get_filtered_df, get_salary_df
from utils.charts import hbar, pie_donut, grouped_bar, PLOTLY_CONFIG
from utils.export import filtered_jobs_export, render_chart_download, render_csv_download, dated_file_name
from utils.sidebar import render_sidebar
from utils import insights

inject_css()
render_sidebar()
df     = get_filtered_df()
df_sal = get_salary_df(df)

page_header("🗺 Phân Tích Địa Lý",
            f"{df['city'].nunique()} tỉnh/thành phố · {len(df):,} tin tuyển dụng")

if df.empty:
    empty_state()
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
city_vc = df['city'].value_counts()
top1_city = city_vc.index[0] if len(city_vc) else '—'
top1_pct  = 100 * city_vc.iloc[0] / len(df) if len(df) else 0
hn_cnt  = int(city_vc.get('Hanoi', 0))
hcm_cnt = int(city_vc.get('Ho Chi Minh City', city_vc.get('Ho Chi Minh', 0)))

k1.metric("Tổng tỉnh/thành", f"{df['city'].nunique()}")
k2.metric("Top thành phố", f"{top1_city} ({top1_pct:.0f}%)")
k3.metric("Hà Nội", f"{hn_cnt:,} tin")
k4.metric("TP.HCM", f"{hcm_cnt:,} tin")

st.divider()

# ── Row 1: city distribution + pie ────────────────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("**Phân Bổ Tin Tuyển Dụng Theo Thành Phố (Top 12)**")
    top12 = df['city'].value_counts().head(12).reset_index()
    top12.columns = ['Thành phố', 'Số tin']
    fig = hbar(top12, 'Số tin', 'Thành phố', height=380, color=C['blue'])
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig, "geographic_city_distribution.png", key="geo_city_png")

with col2:
    st.markdown("**Tỷ Trọng Theo Vùng**")
    top5 = df['city'].value_counts().head(5)
    other_sum = df['city'].value_counts().iloc[5:].sum()
    labels = top5.index.tolist() + ['Khác']
    values = top5.values.tolist() + [int(other_sum)]
    fig2 = pie_donut(labels, values, height=380)
    st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig2, "geographic_region_share.png", key="geo_region_png")

# ── HCM vs Hanoi comparison ───────────────────────────────────────────────────
st.markdown("**So Sánh TP.HCM vs Hà Nội**")

hcm_keys = ['Ho Chi Minh City', 'Ho Chi Minh', 'Hồ Chí Minh', 'HCM', 'HCMC']
hn_keys  = ['Hanoi', 'Hà Nội', 'Ha Noi', 'HN']

df_hcm = df[df['city'].isin(hcm_keys)]
df_hn  = df[df['city'].isin(hn_keys)]

if len(df_hcm) > 10 and len(df_hn) > 10:
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("*Phân bổ vai trò*")
        top_roles = df['role_category'].value_counts().head(7).index.tolist()
        hcm_roles = df_hcm['role_category'].value_counts().reindex(top_roles, fill_value=0)
        hn_roles  = df_hn['role_category'].value_counts().reindex(top_roles, fill_value=0)
        fig3 = grouped_bar(
            top_roles,
            {'TP.HCM': hcm_roles.values.tolist(), 'Hà Nội': hn_roles.values.tolist()},
            height=320
        )
        fig3.update_layout(xaxis_tickangle=-30, legend_title='')
        st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CONFIG)
        render_chart_download(fig3, "geographic_hcm_hanoi_roles.png", key="geo_roles_png")

    with col4:
        st.markdown("*Lương trung vị theo vai trò*")
        sal_hcm = get_salary_df(df_hcm)
        sal_hn  = get_salary_df(df_hn)
        if len(sal_hcm) > 5 and len(sal_hn) > 5:
            hcm_sal = sal_hcm.groupby('role_category')['salary_midpoint_usd'].median().reindex(top_roles)
            hn_sal  = sal_hn.groupby('role_category')['salary_midpoint_usd'].median().reindex(top_roles)
            fig4 = grouped_bar(
                top_roles,
                {'TP.HCM': [round(v, 0) if pd.notna(v) else 0 for v in hcm_sal],
                 'Hà Nội':  [round(v, 0) if pd.notna(v) else 0 for v in hn_sal]},
                height=320
            )
            fig4.update_layout(xaxis_tickangle=-30, legend_title='', yaxis_title='USD/tháng')
            st.plotly_chart(fig4, use_container_width=True, config=PLOTLY_CONFIG)
            render_chart_download(fig4, "geographic_hcm_hanoi_salary.png", key="geo_salary_compare_png")
        else:
            st.info("Không đủ dữ liệu lương để so sánh.")
else:
    st.info("Lọc bỏ dữ liệu HCM/Hà Nội, không thể so sánh. Hãy xóa bộ lọc thành phố.")

# ── Salary by city ─────────────────────────────────────────────────────────────
if len(df_sal) > 10:
    st.markdown("**Lương Trung Vị Theo Thành Phố (Top 8)**")
    top8_sal = df_sal['city'].value_counts().head(8).index.tolist()
    city_sal = (df_sal[df_sal['city'].isin(top8_sal)]
                .groupby('city')['salary_midpoint_usd']
                .median().sort_values(ascending=False).reset_index())
    city_sal.columns = ['Thành phố', 'Lương trung vị (USD)']
    fig5 = hbar(city_sal, 'Lương trung vị (USD)', 'Thành phố', height=320, color=C['orange'])
    st.plotly_chart(fig5, use_container_width=True, config=PLOTLY_CONFIG)
    render_chart_download(fig5, "geographic_salary_by_city.png", key="geo_salary_city_png")

with st.expander("📥 Export dữ liệu địa lý"):
    city_export = df.groupby('city').agg(
        so_tin=('job_title', 'count'),
        so_cong_ty=('company_name', 'nunique'),
        vai_tro_chinh=('role_category', lambda x: x.value_counts().index[0] if len(x) else ''),
    ).sort_values('so_tin', ascending=False).reset_index()
    if len(df_sal):
        city_salary = df_sal.groupby('city')['salary_midpoint_usd'].median().round(0).rename('luong_trung_vi_usd')
        city_export = city_export.merge(city_salary, on='city', how='left')

    c1, c2 = st.columns(2)
    with c1:
        render_csv_download(
            city_export,
            "Download CSV (phân tích thành phố)",
            dated_file_name("geographic_city_analysis"),
            key="geo_city_csv",
        )
    with c2:
        render_csv_download(
            filtered_jobs_export(df),
            "Download CSV (tin đang lọc)",
            dated_file_name("geographic_filtered_jobs"),
            key="geo_jobs_csv",
        )

insight_panel(insights.GEOGRAPHIC)
