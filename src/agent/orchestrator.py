"""Prompt-driven AI-agent style analytics orchestration.

This module is deterministic by default. It structures the agent workflow used
for demos and can later be connected to an LLM provider if API keys are present.
"""
from __future__ import annotations

import pandas as pd

from .analytics_pipeline import AutomatedAnalyticsPipeline


WORKFLOW_STEPS = [
    "Data Understanding",
    "Data Cleaning",
    "EDA",
    "Insight Generation",
    "Chart Selection",
    "Dashboard Layout",
    "Report Generation",
    "Slide Generation",
    "Dashboard Publishing",
]


class AnalyticsAgentOrchestrator:
    def __init__(self):
        self.pipeline = AutomatedAnalyticsPipeline()

    def run(self, df: pd.DataFrame, user_prompt: str = "") -> dict:
        result = self.pipeline.run(df, user_prompt)
        return {
            "workflow_steps": WORKFLOW_STEPS,
            "domain": result["domain"],
            "profile": result["profile"],
            "kpis": result["kpis"],
            "charts": result["charts"],
            "insights": result["insights"],
            "dashboard_layout": self.dashboard_layout(result),
            "executive_summary": self.executive_summary(result),
            "report_outline": self.report_outline(result),
            "slide_outline": self.slide_outline(result),
            "cleaned_df": result["cleaned_df"],
        }

    @staticmethod
    def dashboard_layout(result: dict) -> list[dict]:
        return [
            {"section": "Header", "content": "Dataset title, domain, last refresh, filters"},
            {"section": "KPI Row", "content": [kpi["label"] for kpi in result["kpis"]]},
            {"section": "Main Charts", "content": [chart["title"] for chart in result["charts"][:4]]},
            {"section": "Deep Dive", "content": [chart["title"] for chart in result["charts"][4:]]},
            {"section": "Insight Panel", "content": result["insights"][:4]},
        ]

    @staticmethod
    def executive_summary(result: dict) -> str:
        profile = result["profile"]
        domain = result["domain"].replace("_", " ")
        first_insight = result["insights"][0] if result["insights"] else "Dataset đã được phân tích."
        return (
            f"Dataset được nhận diện là nhóm {domain}, gồm {profile.rows:,} dòng và "
            f"{profile.columns:,} cột. {first_insight} Dashboard nên ưu tiên KPI tổng quan, "
            "biểu đồ phân nhóm chính và insight panel để hỗ trợ quyết định nhanh."
        )

    @staticmethod
    def report_outline(result: dict) -> list[str]:
        return [
            "1. Executive summary",
            "2. Dataset overview and schema quality",
            "3. KPI interpretation",
            "4. Key chart findings",
            "5. Business insights and recommendations",
            "6. Data limitations",
        ]

    @staticmethod
    def slide_outline(result: dict) -> list[str]:
        return [
            "Slide 1 - Project objective and dataset",
            "Slide 2 - KPI overview",
            "Slide 3 - Main dashboard findings",
            "Slide 4 - Deep-dive analytics",
            "Slide 5 - Recommendations and next steps",
        ]
