"""Skill Analytics page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Phân Tích Kỹ Năng", page_icon="🛠", layout="wide")

from utils.style import inject_css, insight_panel, page_header, empty_state, C
from src.nlp import KeywordExtractor
from utils.data_loader import get_filtered_df, get_salary_df, get_skill_counts, skill_by_role_matrix, skill_pair_rankings, high_paying_skills
from utils.charts import hbar, heatmap_chart, skill_tag_cloud_html, PLOTLY_CONFIG
from utils.export import filtered_jobs_export, render_chart_download, render_csv_download, dated_file_name
from utils.sidebar import render_sidebar
from utils import insights

inject_css()
render_sidebar()

df     = get_filtered_df()
df_sal = get_salary_df(df)

page_header("🛠 Phân Tích Kỹ Năng Kỹ Thuật",
            f"Phân tích từ {len(df):,} tin tuyển dụng")

if df.empty:
    empty_state()
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
skill_counts = get_skill_counts(df)
top5 = skill_counts.most_common(5)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Kỹ năng unique", f"{len(skill_counts):,}")
k2.metric("Top kỹ năng", top5[0][0].title() if top5 else '—')
k3.metric("Kỹ năng #2", top5[1][0].title() if len(top5) > 1 else '—')
k4.metric("Avg kỹ năng/tin", f"{df['skill_count'].mean():.1f}")

st.divider()

# ── Row 1: Top 20 skills + high-paying skills ──────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Top 20 Kỹ Năng Được Yêu Cầu Nhiều Nhất**")
    top20 = skill_counts.most_common(20)
    sk_df = pd.DataFrame(top20, columns=['Kỹ năng', 'Tần suất'])
    fig = hbar(sk_df, 'Tần suất', 'Kỹ năng', height=480, color=C['green'])
    fig.update_layout(xaxis_title="Số tin xuất hiện")
    st.plotly_chart(fig, width='stretch', config=PLOTLY_CONFIG)
    render_chart_download(fig, "skills_frequency.png", key="skills_frequency_png")

with col2:
    st.markdown("**Top 15 Kỹ Năng Được Trả Lương Cao Nhất**")
    hp = high_paying_skills(df_sal)
    if not hp.empty:
        hp_plot = hp[['skill', 'median_salary']].rename(
            columns={'skill': 'Kỹ năng', 'median_salary': 'Lương trung vị (USD)'})
        fig2 = hbar(hp_plot, 'Lương trung vị (USD)', 'Kỹ năng', height=480, color=C['orange'])
        fig2.update_layout(xaxis_title="USD/tháng (trung vị)")
        st.plotly_chart(fig2, width='stretch', config=PLOTLY_CONFIG)
        render_chart_download(fig2, "skills_salary.png", key="skills_salary_png")
    else:
        st.info("Không đủ dữ liệu lương.")

# ── Skill-Role heatmap ─────────────────────────────────────────────────────────
st.markdown("**Ma Trận Kỹ Năng × Vai Trò** *(top 12 kỹ năng × top 6 vai trò)*")
try:
    mat = skill_by_role_matrix(df, top_skills=12, top_roles=6)
    if not mat.empty:
        fig3 = heatmap_chart(mat, height=400)
        fig3.update_layout(
            xaxis_title="Vai trò",
            yaxis_title="Kỹ năng",
        )
        st.plotly_chart(fig3, width='stretch', config=PLOTLY_CONFIG)
        render_chart_download(fig3, "skills_role_heatmap.png", key="skills_heatmap_png")
except Exception as e:
    st.warning(f"Không thể render heatmap: {e}")

# ── Skill tag cloud ────────────────────────────────────────────────────────────
st.markdown("**Bản Đồ Kỹ Năng — Top 50** *(kích thước thể hiện tần suất)*")
top50 = skill_counts.most_common(50)
if top50:
    html = skill_tag_cloud_html(top50)
    st.markdown(html, unsafe_allow_html=True)

# ── NLP enhancement: keywords + co-occurrence ─────────────────────────────────
st.markdown("**NLP Enhancement — Keyword & Skill Co-occurrence**")
nlp_col1, nlp_col2 = st.columns(2)

with nlp_col1:
    st.markdown("*Top JD keywords (TF-IDF)*")
    text_col = 'job_description' if 'job_description' in df.columns else 'skills_str'
    extractor = KeywordExtractor(max_features=200, ngram_range=(1, 2), min_df=2)
    extractor.fit(df[text_col].fillna('').head(1200).tolist())
    keyword_df = extractor.top_keywords(20)
    if not keyword_df.empty:
        keyword_plot = keyword_df.copy()
        keyword_plot['score'] = keyword_plot['score'].astype(float).round(4)
        fig4 = hbar(
            keyword_plot.rename(columns={'keyword': 'Keyword', 'score': 'TF-IDF'}),
            'TF-IDF',
            'Keyword',
            height=380,
            color=C['blue'],
            text_fmt='.3f',
        )
        st.plotly_chart(fig4, width='stretch', config=PLOTLY_CONFIG)
    else:
        st.info("Không đủ dữ liệu để trích xuất keyword.")

with nlp_col2:
    st.markdown("*Top cặp kỹ năng thường đi cùng nhau*")
    pairs_df = skill_pair_rankings(df, top_n=15)
    if not pairs_df.empty:
        pair_plot = pairs_df.copy()
        pair_plot['Cặp kỹ năng'] = pair_plot['skill_a'] + ' + ' + pair_plot['skill_b']
        fig5 = hbar(
            pair_plot[['Cặp kỹ năng', 'count']].rename(columns={'count': 'Số lần'}),
            'Số lần',
            'Cặp kỹ năng',
            height=380,
            color=C['purple'],
        )
        st.plotly_chart(fig5, width='stretch', config=PLOTLY_CONFIG)
    else:
        st.info("Không đủ dữ liệu để tính co-occurrence.")

# ── Export ─────────────────────────────────────────────────────────────────────
with st.expander("📥 Export dữ liệu kỹ năng"):
    sk_export = pd.DataFrame(skill_counts.most_common(200), columns=['Kỹ năng', 'Tần suất'])
    c1, c2, c3 = st.columns(3)
    with c1:
        render_csv_download(
            sk_export,
            "Download CSV (top 200 kỹ năng)",
            dated_file_name("skill_frequency"),
            key="skills_frequency_csv",
        )
    with c2:
        render_csv_download(
            filtered_jobs_export(df),
            "Download CSV (tin đang lọc)",
            dated_file_name("skills_filtered_jobs"),
            key="skills_jobs_csv",
        )
    with c3:
        render_csv_download(
            pairs_df if 'pairs_df' in locals() else pd.DataFrame(),
            "Download CSV (skill pairs)",
            dated_file_name("skill_pairs"),
            key="skills_pairs_csv",
            disabled=('pairs_df' not in locals()) or pairs_df.empty,
        )

insight_panel(insights.SKILLS)
