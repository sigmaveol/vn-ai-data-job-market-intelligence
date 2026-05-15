"""Market-level EDA: job counts, locations, hiring trends, remote vs onsite."""
import pandas as pd


class MarketAnalysis:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def top_job_titles(self, n: int = 15) -> pd.Series:
        """Return top-N job titles by frequency."""
        # TODO Phase 4: df['job_title'].value_counts().head(n)
        raise NotImplementedError

    def jobs_by_city(self) -> pd.Series:
        """Return job count per normalized city."""
        # TODO Phase 4: df['location'].value_counts()
        raise NotImplementedError

    def remote_vs_onsite(self) -> pd.Series:
        """Return count breakdown: Remote / Onsite / Hybrid."""
        # TODO Phase 4: classify based on location / employment_type field
        raise NotImplementedError

    def hiring_trend_by_month(self) -> pd.DataFrame:
        """Return monthly job posting counts as (month, count) DataFrame."""
        # TODO Phase 4: df.groupby(df['posted_date'].dt.to_period('M')).size()
        raise NotImplementedError

    def top_hiring_companies(self, n: int = 20) -> pd.Series:
        """Return top-N companies by number of open positions."""
        # TODO Phase 4: df['company_name'].value_counts().head(n)
        raise NotImplementedError

    def jobs_by_experience_level(self) -> pd.Series:
        """Return job count per experience_level bucket."""
        # TODO Phase 4: df['experience_level'].value_counts()
        raise NotImplementedError

    def jobs_by_source(self) -> pd.Series:
        """Return count per source_website."""
        # TODO Phase 4: df['source_website'].value_counts()
        raise NotImplementedError
