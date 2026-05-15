"""Reusable automated analytics pipeline for uploaded datasets."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class SchemaProfile:
    rows: int
    columns: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    text_columns: list[str]
    missing_rate: dict[str, float]


class AutomatedAnalyticsPipeline:
    """Schema detection, light cleaning, EDA, chart, and insight suggestions."""

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out.columns = [str(col).strip().lower().replace(" ", "_") for col in out.columns]
        out = out.drop_duplicates()

        for col in out.columns:
            if out[col].dtype == object:
                out[col] = out[col].astype(str).str.strip()
                numeric = pd.to_numeric(out[col].str.replace(",", "", regex=False), errors="coerce")
                if numeric.notna().mean() > 0.75:
                    out[col] = numeric
                    continue
                dates = pd.to_datetime(out[col], errors="coerce")
                if dates.notna().mean() > 0.75:
                    out[col] = dates
        return out

    def profile_schema(self, df: pd.DataFrame) -> SchemaProfile:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()
        object_cols = df.select_dtypes(include="object").columns.tolist()
        categorical_cols = [c for c in object_cols if df[c].nunique(dropna=True) <= max(30, len(df) * 0.2)]
        text_cols = [c for c in object_cols if c not in categorical_cols]
        missing = (df.isna().mean() * 100).round(2).to_dict()
        return SchemaProfile(
            rows=len(df),
            columns=len(df.columns),
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            datetime_columns=datetime_cols,
            text_columns=text_cols,
            missing_rate=missing,
        )

    def infer_domain(self, df: pd.DataFrame, user_prompt: str = "") -> str:
        cols = " ".join(df.columns).lower()
        prompt = user_prompt.lower()
        text = f"{cols} {prompt}"
        if any(k in text for k in ["salary", "job", "skill", "company", "resume", "candidate"]):
            return "labor_market"
        if any(k in text for k in ["sales", "revenue", "order", "customer", "profit"]):
            return "sales"
        if any(k in text for k in ["employee", "department", "attrition", "hr", "turnover"]):
            return "hr"
        if any(k in text for k in ["marketing", "campaign", "conversion", "channel"]):
            return "marketing"
        return "general"

    def recommend_kpis(self, df: pd.DataFrame, profile: SchemaProfile, domain: str) -> list[dict]:
        kpis = [{"label": "Số bản ghi", "value": len(df), "description": "Quy mô dataset sau làm sạch"}]
        if profile.categorical_columns:
            col = profile.categorical_columns[0]
            kpis.append({"label": f"Số {col}", "value": df[col].nunique(), "description": f"Số giá trị unique của {col}"})
        if profile.numeric_columns:
            col = profile.numeric_columns[0]
            kpis.append({"label": f"Trung vị {col}", "value": round(float(df[col].median()), 2), "description": f"Median của {col}"})

        if domain == "labor_market":
            for col in ["company_name", "city", "role_category", "job_title"]:
                if col in df.columns:
                    kpis.append({"label": f"Top {col}", "value": str(df[col].mode().iloc[0]), "description": f"Giá trị phổ biến nhất của {col}"})
                    break
        elif domain == "sales":
            for col in profile.numeric_columns:
                if any(k in col for k in ["revenue", "sales", "amount", "profit"]):
                    kpis.append({"label": f"Tổng {col}", "value": round(float(df[col].sum()), 2), "description": "Tổng doanh thu/giá trị"})
                    break
        return kpis[:6]

    def recommend_charts(self, df: pd.DataFrame, profile: SchemaProfile, domain: str) -> list[dict]:
        charts = []
        for col in profile.categorical_columns[:3]:
            charts.append({"type": "bar", "title": f"Top {col}", "x": col, "y": "count", "reason": "So sánh nhóm phổ biến"})
        for col in profile.numeric_columns[:2]:
            charts.append({"type": "histogram", "title": f"Phân bố {col}", "x": col, "reason": "Xem phân phối và outlier"})
        if profile.datetime_columns and profile.numeric_columns:
            charts.append({
                "type": "line",
                "title": f"Xu hướng {profile.numeric_columns[0]} theo thời gian",
                "x": profile.datetime_columns[0],
                "y": profile.numeric_columns[0],
                "reason": "Theo dõi biến động thời gian",
            })
        if len(profile.categorical_columns) >= 1 and len(profile.numeric_columns) >= 1:
            charts.append({
                "type": "box",
                "title": f"{profile.numeric_columns[0]} theo {profile.categorical_columns[0]}",
                "x": profile.categorical_columns[0],
                "y": profile.numeric_columns[0],
                "reason": "So sánh phân phối giữa các nhóm",
            })
        return charts[:8]

    def generate_insights(self, df: pd.DataFrame, profile: SchemaProfile, domain: str) -> list[str]:
        insights = [
            f"Dataset có {profile.rows:,} dòng và {profile.columns:,} cột sau bước làm sạch nhẹ.",
        ]
        if profile.missing_rate:
            highest_missing = max(profile.missing_rate.items(), key=lambda item: item[1])
            insights.append(f"Cột thiếu dữ liệu nhiều nhất là `{highest_missing[0]}` với {highest_missing[1]:.1f}% missing.")
        if profile.categorical_columns:
            col = profile.categorical_columns[0]
            top = df[col].value_counts().head(1)
            if not top.empty:
                insights.append(f"`{top.index[0]}` là nhóm nổi bật nhất trong `{col}` với {int(top.iloc[0]):,} bản ghi.")
        if profile.numeric_columns:
            col = profile.numeric_columns[0]
            insights.append(f"`{col}` có median {df[col].median():,.2f}, phù hợp để đưa vào KPI hoặc distribution chart.")
        if domain == "labor_market":
            insights.append("Dataset phù hợp với dashboard labor market: demand by role, skill, company, location, salary.")
        elif domain == "sales":
            insights.append("Dataset phù hợp với dashboard sales: revenue, customer, product, channel, time trend.")
        elif domain == "hr":
            insights.append("Dataset phù hợp với dashboard HR: headcount, department, attrition, tenure, compensation.")
        return insights

    def run(self, df: pd.DataFrame, user_prompt: str = "") -> dict:
        cleaned = self.clean_dataframe(df)
        profile = self.profile_schema(cleaned)
        domain = self.infer_domain(cleaned, user_prompt)
        return {
            "domain": domain,
            "cleaned_df": cleaned,
            "profile": profile,
            "kpis": self.recommend_kpis(cleaned, profile, domain),
            "charts": self.recommend_charts(cleaned, profile, domain),
            "insights": self.generate_insights(cleaned, profile, domain),
        }
