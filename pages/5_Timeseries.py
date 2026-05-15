"""Time-series Analytics page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Xu Hướng Tuyển Dụng", page_icon="📈", layout="wide")

from utils.style import inject_css, insight_panel, page_header, empty_state, C, PLOTLY_LAYOUT
from utils.data_loader import get_filtered_df
from utils.charts import vbar, PLOTLY_CONFIG
from utils.export import filtered_jobs_export, render_chart_download, render_csv_download, dated_file_name
from utils.sidebar import render_sidebar
from utils import insights

inject_css()
render_sidebar()
df = get_filtered_df()

page_header("📈 Xu Hướng Tuyển Dụng Theo Thời Gian",
            "Diễn biến số tin đăng theo tháng và tăng trưởng theo vai trò")

if df.empty:
    empty_state()
    st.stop()

# Filter dated records
df_dated = df[df['_month'].notna() & (df['_month'] != 'NaT')].copy()

if len(df_dated) < 10:
    st.warning("Không đủ dữ liệu thời gian với bộ lọc hiện tại.")
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
monthly = df_dated.groupby('_month').size().sort_index()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Tháng quan sát", f"{len(monthly)}")
k2.metric("Tháng cao nhất", f"{monthly.idxmax()} ({monthly.max():,} tin)")
k3.metric("Tháng thấp nhất", f"{monthly.idxmin()} ({monthly.min():,} tin)")
peak_change = (monthly.max() - monthly.mean()) / monthly.mean() * 100
k4.metric("Đỉnh so với TB", f"+{peak_change:.0f}%")

st.divider()

# ── Overall monthly trend ──────────────────────────────────────────────────────
st.markdown("**Xu Hướng Tổng Thể Theo Tháng**")
monthly_df = monthly.reset_index()
monthly_df.columns = ['Tháng', 'Số tin']

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=monthly_df['Tháng'], y=monthly_df['Số tin'],
    mode='lines+markers',
    line=dict(color=C['accent'], width=3),
    marker=dict(size=8, color=C['accent']),
    fill='tozeroy', fillcolor=f"rgba(108,99,255,0.12)",
    name='Số tin',
    hovertemplate='<b>%{x}</b><br>%{y:,} tin<extra></extra>',
))
# Add mean line
mean_val = monthly_df['Số tin'].mean()
fig.add_hline(y=mean_val, line_dash='dash', line_color=C['muted'],
              annotation_text=f'Trung bình: {mean_val:.0f}',
              annotation_position='right', annotation_font_color=C['muted'])
fig.update_layout(**PLOTLY_LAYOUT, height=320,
                  xaxis_title='Tháng', yaxis_title='Số tin đăng')
st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
render_chart_download(fig, "timeseries_monthly_trend.png", key="time_monthly_png")

# ── Trend by role ──────────────────────────────────────────────────────────────
st.markdown("**Xu Hướng Theo Vai Trò Chính**")
top_roles = df_dated['role_category'].value_counts().head(5).index.tolist()
pivot = (df_dated[df_dated['role_category'].isin(top_roles)]
         .groupby(['_month', 'role_category']).size()
         .unstack(fill_value=0)
         .sort_index())

if not pivot.empty:
    months = pivot.index.tolist()
    colors = [C['accent'], C['red'], C['green'], C['orange'], C['blue']]
    fig2 = go.Figure()
    for i, role in enumerate(pivot.columns):
        fig2.add_trace(go.Scatter(
            x=months, y=pivot[role].tolist(),
            mode='lines+markers', name=role,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=6),
            hovertemplate=f'<b>{role}</b><br>%{{x}}: %{{y:,}} tin<extra></extra>',
        ))
    fig2.update_layout(**PLOTLY_LAYOUT, height=360,
                       xaxis_title='Tháng', yaxis_title='Số tin đăng',
                       showlegend=True)
    st.plotly_chart(fig2, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig2, "timeseries_role_trend.png", key="time_roles_png")

# ── Day-of-week pattern ────────────────────────────────────────────────────────
df_dated['_dow'] = df_dated['_date'].dt.dayofweek
dow_map = {0:'Thứ 2',1:'Thứ 3',2:'Thứ 4',3:'Thứ 5',4:'Thứ 6',5:'Thứ 7',6:'Chủ nhật'}
if df_dated['_dow'].notna().sum() > 50:
    st.markdown("**Phân Bổ Đăng Tin Theo Ngày Trong Tuần**")
    dow_vc = df_dated['_dow'].value_counts().sort_index()
    dow_df = pd.DataFrame({'Ngày': [dow_map[i] for i in dow_vc.index], 'Số tin': dow_vc.values})
    fig3 = vbar(dow_df, 'Ngày', 'Số tin', height=280, color=C['purple'])
    st.plotly_chart(fig3, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig3, "timeseries_day_of_week.png", key="time_dow_png")

with st.expander("📥 Export dữ liệu xu hướng"):
    trend_export = monthly_df.copy()
    c1, c2 = st.columns(2)
    with c1:
        render_csv_download(
            trend_export,
            "Download CSV (xu hướng tháng)",
            dated_file_name("monthly_trend"),
            key="time_monthly_csv",
        )
    with c2:
        render_csv_download(
            filtered_jobs_export(df_dated),
            "Download CSV (tin có ngày đăng)",
            dated_file_name("dated_filtered_jobs"),
            key="time_jobs_csv",
        )

insight_panel(insights.TIMESERIES)
