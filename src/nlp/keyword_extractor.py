"""Lightweight TF-IDF keyword extraction for analytics and ATS matching."""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd


VIETNAMESE_STOPWORDS = {
    "và", "hoặc", "của", "cho", "các", "với", "trong", "theo", "tại", "là",
    "có", "được", "một", "những", "này", "để", "khi", "về", "từ", "trên",
    "dưới", "ứng", "viên", "công", "việc", "kinh", "nghiệm", "yêu", "cầu",
    "mô", "tả", "phúc", "lợi", "quyền", "lợi", "làm", "việc", "nhân", "sự",
}

ENGLISH_STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "for", "of", "in", "on", "with",
    "by", "from", "as", "is", "are", "be", "this", "that", "your", "you",
    "we", "our", "will", "can", "have", "has", "job", "work", "team",
}

DOMAIN_KEEPWORDS = {
    "python", "sql", "machine", "learning", "data", "engineer", "analyst",
    "scientist", "cloud", "aws", "azure", "gcp", "spark", "pytorch",
    "tensorflow", "tableau", "power", "bi", "docker", "kubernetes", "etl",
}


class KeywordExtractor:
    """TF-IDF keyword extractor with a deterministic frequency fallback."""

    def __init__(self, max_features: int = 300, ngram_range: tuple = (1, 2), min_df: int = 1):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.vectorizer = None
        self.matrix = None
        self.feature_names = []
        self._fallback_scores: Counter[str] = Counter()

    @staticmethod
    def clean_text(text: str) -> str:
        text = str(text or "").lower()
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"[^a-z0-9+#À-ỹ ]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @property
    def stopwords(self) -> set[str]:
        return VIETNAMESE_STOPWORDS | ENGLISH_STOPWORDS

    def fit(self, corpus: list[str]) -> "KeywordExtractor":
        cleaned = [self.clean_text(text) for text in corpus if str(text or "").strip()]
        if not cleaned:
            self._fallback_scores = Counter()
            return self

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self.vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=self.ngram_range,
                min_df=self.min_df,
                stop_words=list(self.stopwords),
                token_pattern=r"(?u)\b[a-zA-ZÀ-ỹ][a-zA-ZÀ-ỹ0-9+#]{1,}\b",
            )
            self.matrix = self.vectorizer.fit_transform(cleaned)
            self.feature_names = self.vectorizer.get_feature_names_out().tolist()
        except Exception:
            self.vectorizer = None
            self.matrix = None
            self.feature_names = []
            self._fallback_scores = self._frequency_scores(cleaned)
        return self

    def _frequency_scores(self, corpus: list[str]) -> Counter[str]:
        counter = Counter()
        for text in corpus:
            tokens = [t for t in text.split() if len(t) > 2 and (t not in self.stopwords or t in DOMAIN_KEEPWORDS)]
            counter.update(tokens)
            for i in range(len(tokens) - 1):
                phrase = f"{tokens[i]} {tokens[i + 1]}"
                counter[phrase] += 1
        return counter

    def top_keywords(self, n: int = 30) -> pd.DataFrame:
        if self.matrix is not None and self.feature_names:
            means = self.matrix.mean(axis=0).A1
            rows = sorted(zip(self.feature_names, means), key=lambda item: item[1], reverse=True)[:n]
            return pd.DataFrame(rows, columns=["keyword", "score"])

        rows = self._fallback_scores.most_common(n)
        return pd.DataFrame(rows, columns=["keyword", "score"])

    def keywords_for_document(self, text: str, n: int = 10) -> list[str]:
        cleaned = self.clean_text(text)
        if not cleaned:
            return []

        if self.vectorizer is not None and self.feature_names:
            vector = self.vectorizer.transform([cleaned])
            scores = vector.toarray()[0]
            ranked = scores.argsort()[::-1]
            return [self.feature_names[i] for i in ranked if scores[i] > 0][:n]

        scores = self._frequency_scores([cleaned])
        return [kw for kw, _ in scores.most_common(n)]

    def role_keyword_associations(
        self,
        df: pd.DataFrame,
        text_col: str = "job_description",
        role_col: str = "role_category",
        top_n: int = 8,
    ) -> pd.DataFrame:
        rows = []
        if text_col not in df or role_col not in df:
            return pd.DataFrame(columns=["role", "keyword", "score"])
        for role, sub in df.groupby(role_col):
            extractor = KeywordExtractor(self.max_features, self.ngram_range, self.min_df)
            extractor.fit(sub[text_col].fillna("").tolist())
            top = extractor.top_keywords(top_n)
            for _, row in top.iterrows():
                rows.append({"role": role, "keyword": row["keyword"], "score": row["score"]})
        return pd.DataFrame(rows)

    def company_keyword_analysis(
        self,
        df: pd.DataFrame,
        text_col: str = "job_description",
        company_col: str = "company_name",
        top_companies: int = 10,
        top_n: int = 5,
    ) -> pd.DataFrame:
        rows = []
        if text_col not in df or company_col not in df:
            return pd.DataFrame(columns=["company", "keyword", "score"])
        companies = df[company_col].value_counts().head(top_companies).index
        for company in companies:
            sub = df[df[company_col] == company]
            extractor = KeywordExtractor(self.max_features, self.ngram_range, self.min_df)
            extractor.fit(sub[text_col].fillna("").tolist())
            for _, row in extractor.top_keywords(top_n).iterrows():
                rows.append({"company": company, "keyword": row["keyword"], "score": row["score"]})
        return pd.DataFrame(rows)

    def topic_model(self, corpus: list[str], n_topics: int = 8):
        """Return lightweight keyword groups instead of BERTopic."""
        self.fit(corpus)
        keywords = self.top_keywords(n_topics * 5)
        groups = []
        for i in range(n_topics):
            chunk = keywords.iloc[i * 5:(i + 1) * 5]
            groups.append({"topic": i + 1, "keywords": chunk["keyword"].tolist()})
        return pd.DataFrame(groups)
