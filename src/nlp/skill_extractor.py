"""Deterministic skill extraction for jobs and resumes.

The implementation is intentionally lightweight: taxonomy lookup, alias
normalization, and regex matching. It is suitable for analytics enrichment and
resume matching without introducing black-box NLP models.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import ALL_SKILLS, SKILL_TAXONOMY  # noqa: E402


SKILL_ALIASES = {
    "js": "JavaScript",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "reactjs": "React",
    "react.js": "React",
    "vuejs": "Vue",
    "vue.js": "Vue",
    "angularjs": "Angular",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mssql": "SQL Server",
    "ms sql": "SQL Server",
    "sql server": "SQL Server",
    "scikit learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "pyspark": "PySpark",
    "spark": "Apache Spark",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "gcp": "GCP",
    "google cloud": "GCP",
    "amazon web services": "AWS",
    "k8s": "Kubernetes",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "llm": "LLM",
    "llms": "LLM",
    "gen ai": "Generative AI",
    "genai": "Generative AI",
    "generative ai": "Generative AI",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "computer vision": "Computer Vision",
    "natural language processing": "NLP",
    "nlp": "NLP",
    "etl": "ETL",
    "elt": "ELT",
    "excel": "Excel",
    "looker": "Looker",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "git": "Git",
    "linux": "Linux",
}


EXTRA_SKILLS = [
    "Node.js", "React", "Vue", "Angular", "SQL Server", "Machine Learning",
    "Deep Learning", "Computer Vision", "Generative AI", "NLP", "ETL", "ELT",
    "Excel", "Looker", "FastAPI", "Flask", "Django", "Git", "Linux",
    "NoSQL", "REST API", "Microservices", "Statistics", "A/B Testing",
    "Data Modeling", "Data Warehouse", "Data Lake", "Business Intelligence",
]


@dataclass(frozen=True)
class ExtractedSkill:
    skill: str
    category: str


class SkillExtractor:
    """Rule-based skill extractor with canonical normalization."""

    def __init__(self, extra_skills: list[str] | None = None):
        skills = list(dict.fromkeys([*ALL_SKILLS, *EXTRA_SKILLS, *(extra_skills or [])]))
        self.skill_lookup = {self.normalize_skill(skill): skill for skill in skills}
        for alias, canonical in SKILL_ALIASES.items():
            self.skill_lookup[self.normalize_skill(alias)] = canonical

        self.category_lookup = self._build_category_lookup()
        self.patterns: dict[str, list[re.Pattern]] = {}
        for raw, canonical in self.skill_lookup.items():
            self.patterns.setdefault(canonical, []).append(self._compile_pattern(raw))

    @staticmethod
    def normalize_skill(skill: str) -> str:
        text = str(skill).strip().lower()
        text = text.replace(".", " ").replace("-", " ")
        text = re.sub(r"[^a-z0-9+#/ ]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def normalize_text(text: str) -> str:
        text = str(text or "").lower()
        text = text.replace(".", " ")
        text = re.sub(r"[^a-z0-9+#/À-ỹ ]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return f" {text} "

    @staticmethod
    def _compile_pattern(normalized_skill: str):
        escaped = re.escape(normalized_skill)
        return re.compile(rf"(?<![a-z0-9+#/]){escaped}(?![a-z0-9+#/])", re.IGNORECASE)

    def _build_category_lookup(self) -> dict[str, str]:
        lookup = {}
        for category, skills in SKILL_TAXONOMY.items():
            for skill in skills:
                lookup[self.normalize_skill(skill)] = category
        for alias, canonical in SKILL_ALIASES.items():
            lookup[self.normalize_skill(alias)] = lookup.get(self.normalize_skill(canonical), "technical")
        for skill in EXTRA_SKILLS:
            lookup.setdefault(self.normalize_skill(skill), "technical")
        return lookup

    def extract_from_text(self, text: str) -> list[str]:
        """Return deduplicated canonical skills found in text."""
        if not text:
            return []
        normalized_text = self.normalize_text(text)
        found = []
        for skill, patterns in self.patterns.items():
            if any(pattern.search(normalized_text) for pattern in patterns):
                found.append(skill)
        return sorted(set(found), key=lambda s: s.lower())

    def extract_batch(self, df: pd.DataFrame, col: str = "job_description") -> pd.Series:
        if col not in df.columns:
            return pd.Series([[] for _ in range(len(df))], index=df.index)
        return df[col].fillna("").apply(self.extract_from_text)

    def skill_category(self, skill: str) -> str:
        normalized = self.normalize_skill(skill)
        canonical = self.skill_lookup.get(normalized, skill)
        return self.category_lookup.get(self.normalize_skill(canonical), "other")

    def extract_with_categories(self, text: str) -> list[ExtractedSkill]:
        return [ExtractedSkill(skill=s, category=self.skill_category(s)) for s in self.extract_from_text(text)]

    def frequency(self, texts: list[str] | pd.Series, top_n: int = 50) -> pd.DataFrame:
        counter = Counter()
        for text in texts:
            counter.update(self.extract_from_text(text))
        rows = [
            {"skill": skill, "category": self.skill_category(skill), "count": count}
            for skill, count in counter.most_common(top_n)
        ]
        return pd.DataFrame(rows)

    def cooccurrence_pairs(self, skill_lists: list[list[str]] | pd.Series, top_n: int = 50) -> pd.DataFrame:
        counter = Counter()
        for skills in skill_lists:
            unique = sorted(set(skills))
            for i, left in enumerate(unique):
                for right in unique[i + 1:]:
                    counter[(left, right)] += 1
        rows = [
            {"skill_a": a, "skill_b": b, "count": count}
            for (a, b), count in counter.most_common(top_n)
        ]
        return pd.DataFrame(rows)
