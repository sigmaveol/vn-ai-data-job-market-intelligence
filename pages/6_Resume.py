"""Resume Analyzer dashboard page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Resume Analyzer", page_icon="📄", layout="wide")

from src.resume_analyzer import ResumeMatcher, ResumeParser
from src.nlp import SkillExtractor
from src.auth import require_role
from utils.data_loader import get_filtered_df
from utils.export import dated_file_name, render_csv_download
from utils.sidebar import render_sidebar
from utils.style import C, PLOTLY_CONFIG, PLOTLY_LAYOUT, empty_state, inject_css, page_header

inject_css()
render_sidebar()
require_role("analyst")

df = get_filtered_df()
parser = ResumeParser()
matcher = ResumeMatcher()
skill_extractor = SkillExtractor()

page_header(
    "📄 Resume Analyzer",
    "Chấm điểm CV với JD theo kỹ năng, keyword và kinh nghiệm - deterministic, explainable",
)

if df.empty:
    empty_state()
    st.stop()

st.markdown(
    """
    <div class="insight-panel">
      <h4>Nguyên tắc chấm điểm</h4>
      <ul>
        <li><span class="highlight">60%</span> skill overlap: kỹ năng CV khớp với JD.</li>
        <li><span class="highlight">20%</span> keyword overlap: từ khóa ATS/JD xuất hiện trong CV.</li>
        <li><span class="highlight">20%</span> experience alignment: số năm kinh nghiệm so với yêu cầu.</li>
      </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.25])

with left:
    st.markdown("### 1. Upload CV")
    uploaded = st.file_uploader("Upload PDF, DOCX hoặc TXT", type=["pdf", "docx", "txt"])
    manual_resume = st.text_area(
        "Hoặc dán nội dung CV",
        height=180,
        placeholder="Dán nội dung CV nếu chưa có file...",
    )
    candidate_years = st.number_input(
        "Số năm kinh nghiệm của ứng viên",
        min_value=0.0,
        max_value=30.0,
        value=0.0,
        step=0.5,
    )

with right:
    st.markdown("### 2. Chọn JD để đối chiếu")
    role_options = ["Tất cả"] + sorted(df["role_category"].dropna().unique().tolist())
    selected_role = st.selectbox("Lọc vai trò", role_options)
    jd_pool = df if selected_role == "Tất cả" else df[df["role_category"] == selected_role]
    jd_pool = jd_pool.head(500).copy()
    jd_pool["display"] = (
        jd_pool["job_title"].fillna("Không rõ")
        + " · "
        + jd_pool["company_name"].fillna("Không rõ")
        + " · "
        + jd_pool["city"].fillna("Khác")
    )
    selected_display = st.selectbox("Job Description", jd_pool["display"].tolist())
    selected_job = jd_pool[jd_pool["display"] == selected_display].iloc[0]
    jd_text = "\n".join([
        str(selected_job.get("job_title", "") or ""),
        str(selected_job.get("skills_str", "") or ""),
        str(selected_job.get("job_description", "") or ""),
    ]).strip()

    with st.expander("Xem nhanh JD"):
        st.write({
            "job_title": selected_job.get("job_title"),
            "company_name": selected_job.get("company_name"),
            "city": selected_job.get("city"),
            "experience_level": selected_job.get("experience_level_inferred"),
            "salary_midpoint_usd": selected_job.get("salary_midpoint_usd"),
        })
        st.caption(jd_text[:1200] + ("..." if len(jd_text) > 1200 else ""))

resume_text = ""
parse_error = None
if uploaded is not None:
    try:
        resume_text = parser.parse_uploaded_file(uploaded)
    except Exception as exc:
        parse_error = str(exc)
elif manual_resume.strip():
    resume_text = manual_resume.strip()

if parse_error:
    st.error(f"Không thể parse CV: {parse_error}")

if not resume_text:
    st.info("Upload CV hoặc dán nội dung CV để bắt đầu phân tích.")
    st.stop()

sections = parser.extract_sections(resume_text)
resume_skills = skill_extractor.extract_from_text(resume_text)
jd_skills = skill_extractor.extract_from_text(jd_text)
required_years = matcher.extract_required_experience(jd_text)

result = matcher.analyze(
    resume_text,
    jd_text,
    resume_skills=resume_skills,
    jd_skills=jd_skills,
    candidate_experience=candidate_years,
    required_experience=required_years,
)
frames = matcher.result_to_frames(result)

st.divider()

score_cols = st.columns(4)
score_cols[0].metric("Match score", f"{result.score:.1f}%")
score_cols[1].metric("Skill overlap", f"{result.skill_score:.1f}%")
score_cols[2].metric("Keyword overlap", f"{result.keyword_score:.1f}%")
score_cols[3].metric("Experience fit", f"{result.experience_score:.1f}%")

viz_col, detail_col = st.columns([0.9, 1.1])

with viz_col:
    st.markdown("### Match Radar")
    radar = go.Figure()
    radar.add_trace(go.Scatterpolar(
        r=[result.skill_score, result.keyword_score, result.experience_score, result.score],
        theta=["Kỹ năng", "Keyword", "Kinh nghiệm", "Tổng điểm"],
        fill="toself",
        marker_color=C["accent"],
        line_color=C["accent"],
        name="CV match",
    ))
    radar_layout = dict(**PLOTLY_LAYOUT)
    radar_layout.update(
        height=360,
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        margin=dict(t=30, b=30, l=30, r=30),
    )
    radar.update_layout(**radar_layout)
    st.plotly_chart(radar, use_container_width=True, config=PLOTLY_CONFIG)

    st.markdown("### Breakdown")
    for label, value in [
        ("Skill overlap", result.skill_score),
        ("Keyword overlap", result.keyword_score),
        ("Experience alignment", result.experience_score),
    ]:
        st.caption(label)
        st.progress(int(round(value)))

with detail_col:
    st.markdown("### Kỹ năng khớp / còn thiếu")
    c1, c2 = st.columns(2)
    with c1:
        st.success("Matched skills")
        st.write(", ".join(result.matched_skills) if result.matched_skills else "Chưa tìm thấy kỹ năng khớp.")
    with c2:
        st.warning("Missing skills")
        st.write(", ".join(result.missing_skills) if result.missing_skills else "Không có kỹ năng thiếu rõ ràng.")

    st.markdown("### ATS keywords")
    kw1, kw2 = st.columns(2)
    with kw1:
        st.info("Keyword khớp")
        st.write(", ".join(result.matched_keywords[:20]) if result.matched_keywords else "Chưa có keyword khớp.")
    with kw2:
        st.info("Keyword nên bổ sung")
        st.write(", ".join(result.missing_keywords[:20]) if result.missing_keywords else "Không có keyword thiếu nổi bật.")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Khuyến nghị", "Bảng kỹ năng", "Resume sections", "Export"])

with tab1:
    st.markdown("### Khuyến nghị cải thiện CV")
    if result.recommendations:
        for item in result.recommendations:
            st.write(f"- {item}")
    else:
        st.success("CV đã bao phủ tốt các kỹ năng chính trong JD.")

    if result.required_experience is not None:
        st.caption(
            f"JD yêu cầu khoảng {result.required_experience:g}+ năm kinh nghiệm; "
            f"ứng viên nhập {candidate_years:g} năm."
        )

with tab2:
    skills_df = frames["skills"]
    if skills_df.empty:
        st.info("Không có kỹ năng để hiển thị.")
    else:
        st.dataframe(skills_df, use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Sections parser")
    for section, text in sections.items():
        with st.expander(section.title(), expanded=section in ["skills", "experience"]):
            st.write(text[:2000] if text else "Không phát hiện rõ section này.")

with tab4:
    st.markdown("### Export kết quả phân tích")
    e1, e2, e3 = st.columns(3)
    with e1:
        render_csv_download(
            frames["summary"],
            "Download summary CSV",
            dated_file_name("resume_match_summary"),
            key="resume_summary_csv",
        )
    with e2:
        render_csv_download(
            frames["skills"],
            "Download skills CSV",
            dated_file_name("resume_match_skills"),
            key="resume_skills_csv",
            disabled=frames["skills"].empty,
        )
    with e3:
        render_csv_download(
            frames["recommendations"],
            "Download recommendations CSV",
            dated_file_name("resume_recommendations"),
            key="resume_recommendations_csv",
            disabled=frames["recommendations"].empty,
        )

    report_df = pd.concat(
        [
            frames["summary"].assign(section="summary"),
            frames["skills"].assign(section="skills"),
            frames["keywords"].assign(section="keywords"),
            frames["recommendations"].assign(section="recommendations"),
        ],
        ignore_index=True,
        sort=False,
    )
    render_csv_download(
        report_df,
        "Download full report CSV",
        dated_file_name("resume_full_report"),
        key="resume_full_report_csv",
    )
