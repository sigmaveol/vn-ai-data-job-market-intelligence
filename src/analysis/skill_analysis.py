"""Skill demand EDA: frequency, co-occurrence, trending skills, company-skill mapping."""
import pandas as pd


class SkillAnalysis:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def top_skills(self, n: int = 30) -> pd.Series:
        """Return top-N skills by frequency across all job postings."""
        # TODO Phase 4:
        #   - explode df['skills_required']
        #   - value_counts().head(n)
        raise NotImplementedError

    def skills_by_category(self) -> pd.DataFrame:
        """Return skill frequency grouped by SKILL_TAXONOMY category."""
        # TODO Phase 4: map skills to categories from config.SKILL_TAXONOMY, then count
        raise NotImplementedError

    def skill_cooccurrence_matrix(self, top_n: int = 20) -> pd.DataFrame:
        """
        Return NxN co-occurrence matrix for the top-N skills.
        Used to build heatmap and cluster similar roles.
        """
        # TODO Phase 4: itertools.combinations per row → count pairs → pivot to matrix
        raise NotImplementedError

    def skills_by_experience_level(self) -> pd.DataFrame:
        """Return skill frequency split by Junior vs Senior."""
        # TODO Phase 4: filter df on experience_level, compute top skills per group
        raise NotImplementedError

    def skills_by_role(self, role: str) -> pd.Series:
        """Return top skills for a specific job title."""
        # TODO Phase 4: filter df['job_title'] == role, explode skills, value_counts
        raise NotImplementedError

    def trending_skills(self, window_months: int = 3) -> pd.DataFrame:
        """Return skills whose frequency increased most in the last N months."""
        # TODO Phase 4: compare skill counts in recent window vs prior window
        raise NotImplementedError
