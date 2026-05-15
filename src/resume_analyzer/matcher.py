"""Explainable resume-to-job matching and scoring."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.nlp.keyword_extractor import KeywordExtractor  # noqa: E402
from src.nlp.skill_extractor import SkillExtractor  # noqa: E402


DEFAULT_WEIGHTS = {
    "skill_overlap": 0.60,
    "keyword_overlap": 0.20,
    "experience_alignment": 0.20,
}


LEARNING_SUGGESTIONS = {
    "Python": "Ôn Python cho data workflow: pandas, NumPy, notebook, clean code.",
    "SQL": "Luyện SQL joins, window functions, CTE, query optimization.",
    "Power BI": "Xây dashboard Power BI với data model, DAX cơ bản và storytelling.",
    "Tableau": "Luyện dashboard Tableau, calculated fields và visual analytics.",
    "Machine Learning": "Ôn supervised learning, feature engineering và model evaluation.",
    "Deep Learning": "Nắm neural networks, PyTorch/TensorFlow basics và transfer learning.",
    "PyTorch": "Thực hành tensor, training loop, dataset/dataloader và model fine-tuning.",
    "TensorFlow": "Thực hành Keras API, model training và deployment basics.",
    "Docker": "Đóng gói app bằng Dockerfile, image, container và compose.",
    "Kubernetes": "Nắm deployment, service, configmap và autoscaling ở mức cơ bản.",
    "AWS": "Ôn S3, EC2, IAM, Lambda và data services cơ bản.",
    "GCP": "Ôn BigQuery, Cloud Storage, IAM và Vertex AI basics.",
    "Azure": "Ôn Azure SQL, Blob Storage, Functions và ML basics.",
    "Apache Spark": "Luyện Spark DataFrame, PySpark transform và job optimization.",
    "Airflow": "Xây DAG ETL, schedule, retry và dependency management.",
}


@dataclass
class MatchResult:
    score: float
    skill_score: float
    keyword_score: float
    experience_score: float
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    resume_only_skills: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    required_experience: float | None = None
    candidate_experience: float | None = None


class ResumeMatcher:
    """Deterministic matcher combining skill, keyword, and experience signals."""

    def __init__(self, weights: dict | None = None):
        self.weights = dict(DEFAULT_WEIGHTS)
        if weights:
            self.weights.update(weights)
        self.skill_extractor = SkillExtractor()

    @staticmethod
    def normalize_items(items: list[str]) -> list[str]:
        cleaned = []
        for item in items or []:
            value = str(item).strip()
            if value:
                cleaned.append(value)
        return sorted(set(cleaned), key=lambda s: s.lower())

    def skill_overlap(self, resume_skills: list[str], jd_skills: list[str]) -> dict:
        resume_norm = {self.skill_extractor.normalize_skill(s): s for s in self.normalize_items(resume_skills)}
        jd_norm = {self.skill_extractor.normalize_skill(s): s for s in self.normalize_items(jd_skills)}

        matched_keys = sorted(set(resume_norm) & set(jd_norm))
        missing_keys = sorted(set(jd_norm) - set(resume_norm))
        resume_only_keys = sorted(set(resume_norm) - set(jd_norm))

        matched = [jd_norm[k] for k in matched_keys]
        missing = [jd_norm[k] for k in missing_keys]
        resume_only = [resume_norm[k] for k in resume_only_keys]
        overlap_pct = len(matched) / len(jd_norm) if jd_norm else 0.0

        return {
            "matched": matched,
            "missing": missing,
            "resume_only": resume_only,
            "overlap_pct": overlap_pct,
        }

    def keyword_overlap(self, resume_text: str, jd_text: str, n: int = 20) -> dict:
        extractor = KeywordExtractor(max_features=150, ngram_range=(1, 2))
        extractor.fit([resume_text, jd_text])
        jd_keywords = extractor.keywords_for_document(jd_text, n=n)
        resume_keywords = set(extractor.keywords_for_document(resume_text, n=n * 2))
        matched = [kw for kw in jd_keywords if kw in resume_keywords]
        missing = [kw for kw in jd_keywords if kw not in resume_keywords]
        score = len(matched) / len(jd_keywords) if jd_keywords else 0.0
        return {
            "matched": matched,
            "missing": missing,
            "jd_keywords": jd_keywords,
            "overlap_pct": score,
        }

    def ats_keywords(self, jd_text: str, n: int = 20) -> list[str]:
        extractor = KeywordExtractor(max_features=120, ngram_range=(1, 2))
        extractor.fit([jd_text])
        return extractor.keywords_for_document(jd_text, n=n)

    @staticmethod
    def extract_required_experience(text: str) -> float | None:
        text = str(text or "").lower()
        patterns = [
            r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
            r"(\d+(?:\.\d+)?)\+?\s*(?:năm|nam)\s*(?:kinh nghiệm|kinh nghiem)?",
        ]
        values = []
        for pattern in patterns:
            values.extend(float(match) for match in re.findall(pattern, text))
        return min(values) if values else None

    @staticmethod
    def experience_alignment(candidate_years: float | None, required_years: float | None) -> float:
        if required_years is None:
            return 1.0
        if candidate_years is None:
            return 0.4
        if candidate_years >= required_years:
            return 1.0
        return max(0.0, min(1.0, candidate_years / max(required_years, 0.5)))

    def match_score(self, resume_text: str, jd_text: str) -> float:
        result = self.analyze(resume_text, jd_text)
        return result.score

    def analyze(
        self,
        resume_text: str,
        jd_text: str,
        *,
        resume_skills: list[str] | None = None,
        jd_skills: list[str] | None = None,
        candidate_experience: float | None = None,
        required_experience: float | None = None,
    ) -> MatchResult:
        resume_skills = resume_skills or self.skill_extractor.extract_from_text(resume_text)
        jd_skills = jd_skills or self.skill_extractor.extract_from_text(jd_text)
        candidate_experience = candidate_experience
        required_experience = required_experience if required_experience is not None else self.extract_required_experience(jd_text)

        skill = self.skill_overlap(resume_skills, jd_skills)
        keyword = self.keyword_overlap(resume_text, jd_text)
        exp_score = self.experience_alignment(candidate_experience, required_experience)

        score = (
            self.weights["skill_overlap"] * skill["overlap_pct"]
            + self.weights["keyword_overlap"] * keyword["overlap_pct"]
            + self.weights["experience_alignment"] * exp_score
        )

        recommendations = self.recommend_improvements(skill["missing"])

        return MatchResult(
            score=round(score * 100, 1),
            skill_score=round(skill["overlap_pct"] * 100, 1),
            keyword_score=round(keyword["overlap_pct"] * 100, 1),
            experience_score=round(exp_score * 100, 1),
            matched_skills=skill["matched"],
            missing_skills=skill["missing"],
            resume_only_skills=skill["resume_only"],
            matched_keywords=keyword["matched"],
            missing_keywords=keyword["missing"],
            recommendations=recommendations,
            required_experience=required_experience,
            candidate_experience=candidate_experience,
        )

    def recommend_improvements(self, missing_skills: list[str]) -> list[str]:
        recommendations = []
        for skill in missing_skills[:12]:
            recommendations.append(LEARNING_SUGGESTIONS.get(
                skill,
                f"Bổ sung {skill} qua project nhỏ và thể hiện rõ trong phần kỹ năng/kinh nghiệm.",
            ))
        return recommendations

    @staticmethod
    def result_to_frames(result: MatchResult) -> dict[str, pd.DataFrame]:
        skills = pd.DataFrame(
            [{"type": "matched", "skill": s} for s in result.matched_skills]
            + [{"type": "missing", "skill": s} for s in result.missing_skills]
            + [{"type": "resume_only", "skill": s} for s in result.resume_only_skills]
        )
        keywords = pd.DataFrame(
            [{"type": "matched", "keyword": k} for k in result.matched_keywords]
            + [{"type": "missing", "keyword": k} for k in result.missing_keywords]
        )
        recommendations = pd.DataFrame({"recommendation": result.recommendations})
        summary = pd.DataFrame([{
            "match_score": result.score,
            "skill_score": result.skill_score,
            "keyword_score": result.keyword_score,
            "experience_score": result.experience_score,
            "candidate_experience": result.candidate_experience,
            "required_experience": result.required_experience,
        }])
        return {
            "summary": summary,
            "skills": skills,
            "keywords": keywords,
            "recommendations": recommendations,
        }
