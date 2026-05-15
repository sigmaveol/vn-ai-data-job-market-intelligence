"""AI Agent automation workflow page."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Agent Automation", page_icon="🤖", layout="wide")

from src.agent import AnalyticsAgentOrchestrator
from src.auth import require_role
from utils.export import dated_file_name, render_csv_download
from utils.sidebar import render_sidebar
from utils.style import empty_state, inject_css, page_header

inject_css()
render_sidebar()
require_role("analyst")

page_header(
    "🤖 AI Agent Automation",
    "Upload dataset → schema detection → EDA → chart plan → insights → report/slide outline",
)

st.markdown(
    """
    <div class="insight-panel">
      <h4>Workflow</h4>
      <ul>
        <li>User Prompt → Data Understanding → Cleaning → EDA → Insight Generation</li>
        <li>Chart Selection → Dashboard Layout → Report Outline → Slide Outline</li>
        <li>Phiên bản hiện tại deterministic, explainable, không phụ thuộc LLM.</li>
      </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded = st.file_uploader("Upload CSV dataset", type=["csv"])
prompt = st.text_area(
    "Business prompt",
    placeholder="Ví dụ: Hãy phân tích dataset tuyển dụng và đề xuất KPI, biểu đồ, insight cho dashboard quản trị.",
    height=90,
)

if uploaded is None:
    empty_state("Chưa có dataset", "Upload CSV để chạy workflow tự động.")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as exc:
    st.error(f"Không đọc được CSV: {exc}")
    st.stop()

agent = AnalyticsAgentOrchestrator()
result = agent.run(df, prompt)
profile = result["profile"]
cleaned_df = result["cleaned_df"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Domain", result["domain"])
k2.metric("Rows", f"{profile.rows:,}")
k3.metric("Columns", f"{profile.columns:,}")
k4.metric("Missing max", f"{max(profile.missing_rate.values()) if profile.missing_rate else 0:.1f}%")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Schema", "KPI & Charts", "Insights", "Report/Slides", "Export"])

with tab1:
    st.markdown("### Schema profile")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Numeric columns**")
        st.write(profile.numeric_columns or "Không có")
        st.write("**Datetime columns**")
        st.write(profile.datetime_columns or "Không có")
    with c2:
        st.write("**Categorical columns**")
        st.write(profile.categorical_columns or "Không có")
        st.write("**Text columns**")
        st.write(profile.text_columns or "Không có")
    missing_df = pd.DataFrame(
        [{"column": col, "missing_pct": val} for col, val in profile.missing_rate.items()]
    ).sort_values("missing_pct", ascending=False)
    st.dataframe(missing_df, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("### Suggested KPIs")
    st.dataframe(pd.DataFrame(result["kpis"]), use_container_width=True, hide_index=True)
    st.markdown("### Suggested charts")
    st.dataframe(pd.DataFrame(result["charts"]), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Generated insights")
    for insight in result["insights"]:
        st.write(f"- {insight}")
    st.markdown("### Executive summary")
    st.info(result["executive_summary"])

with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Report outline")
        for item in result["report_outline"]:
            st.write(f"- {item}")
    with c2:
        st.markdown("### Slide outline")
        for item in result["slide_outline"]:
            st.write(f"- {item}")
    st.markdown("### Dashboard layout plan")
    st.dataframe(pd.DataFrame(result["dashboard_layout"]), use_container_width=True, hide_index=True)

with tab5:
    st.markdown("### Export workflow outputs")
    e1, e2, e3 = st.columns(3)
    with e1:
        render_csv_download(
            cleaned_df,
            "Download cleaned CSV",
            dated_file_name("agent_cleaned_dataset"),
            key="agent_cleaned_csv",
        )
    with e2:
        render_csv_download(
            pd.DataFrame(result["charts"]),
            "Download chart plan",
            dated_file_name("agent_chart_plan"),
            key="agent_chart_plan_csv",
        )
    with e3:
        render_csv_download(
            pd.DataFrame({"insight": result["insights"]}),
            "Download insights",
            dated_file_name("agent_insights"),
            key="agent_insights_csv",
        )
