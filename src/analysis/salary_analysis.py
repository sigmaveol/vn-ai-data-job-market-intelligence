"""Salary EDA: distributions, role vs salary, location vs salary, experience vs salary."""
import pandas as pd


class SalaryAnalysis:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def salary_distribution(self) -> pd.DataFrame:
        """Return descriptive stats (mean, median, std, min, max) of salary_min."""
        # TODO Phase 4: df['salary_min'].describe()
        raise NotImplementedError

    def salary_by_role(self) -> pd.DataFrame:
        """Return median salary_min grouped by job_title."""
        # TODO Phase 4: df.groupby('job_title')['salary_min'].median().sort_values(ascending=False)
        raise NotImplementedError

    def salary_by_location(self) -> pd.DataFrame:
        """Return median salary grouped by location."""
        # TODO Phase 4: df.groupby('location')['salary_min'].median()
        raise NotImplementedError

    def salary_by_experience(self) -> pd.DataFrame:
        """Return median salary grouped by experience_level."""
        # TODO Phase 4: df.groupby('experience_level')['salary_min'].median()
        raise NotImplementedError

    def salary_currency_split(self) -> pd.Series:
        """Return proportion of USD vs VND postings."""
        # TODO Phase 4: df['salary_currency'].value_counts(normalize=True)
        raise NotImplementedError

    def negotiable_salary_rate(self) -> float:
        """Return fraction of jobs with no disclosed salary."""
        # TODO Phase 4: (df['salary_min'].isna().sum()) / len(df)
        raise NotImplementedError
