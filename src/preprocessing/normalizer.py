"""Normalization functions: salary, location, skills, experience, dates."""
import logging
import re
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

# ── Salary normalization ───────────────────────────────────────────────────────

# Exchange rate used for VND→USD conversion (fixed rate for consistency)
VND_TO_USD = 1 / 25_500   # 1 USD ≈ 25,500 VND (May 2026)

# Salary sanity bounds (USD/month)
SALARY_MIN_USD = 50
SALARY_MAX_USD = 50_000

# "Negotiable" keywords (salary is not disclosed)
_NEGOTIABLE = {
    "thỏa thuận", "thoả thuận", "thoa thuan", "negotiable", "competitive",
    "đang cập nhật", "dang cap nhat", "cạnh tranh", "canh tranh",
    "attractive", "hấp dẫn", "hap dan", "you'll love it",
    "sign in to view", "login to view", "theo kinh nghiệm",
}


def _is_negotiable(salary_str: str) -> bool:
    s = str(salary_str).lower().strip()
    return not s or any(kw in s for kw in _NEGOTIABLE)


def _parse_salary_string(salary_str: str) -> tuple[Optional[float], Optional[float], str]:
    """
    Parse a raw salary string into (min_usd, max_usd, currency).
    Returns (None, None, '') for negotiable/unspecified salaries.
    """
    if _is_negotiable(salary_str):
        return None, None, ""

    s = str(salary_str).lower().strip()
    currency = "USD"

    # Detect currency
    is_vnd = any(k in s for k in ["triệu", "trieu", "vnd", "vnđ", "đồng", "tr/th"])
    if is_vnd:
        currency = "VND"
    elif "$" in s or "usd" in s:
        currency = "USD"

    # Extract numbers (handles "8 - 15 triệu", "1,500 - 2,000 USD", "Upto 2000")
    # Remove commas used as thousands separator
    s_clean = re.sub(r",", "", s)
    numbers = re.findall(r"\d+(?:\.\d+)?", s_clean)
    values = [float(n) for n in numbers if float(n) > 0]

    if not values:
        return None, None, ""

    # VND millions: "8 - 15 triệu" → 8,000,000 - 15,000,000 VND
    if is_vnd:
        # If values < 1000, treat as "triệu" (millions)
        if max(values) < 1000:
            values = [v * 1_000_000 for v in values]
        # Convert to USD
        values = [v * VND_TO_USD for v in values]
        currency = "USD"

    if len(values) == 1:
        # Single value — could be "upto X" or "from X"
        val = values[0]
        if "upto" in s or "up to" in s or "tối đa" in s:
            sal_min, sal_max = val * 0.7, val
        elif "from" in s or "từ" in s or "tối thiểu" in s:
            sal_min, sal_max = val, val * 1.4
        else:
            sal_min = sal_max = val
    elif len(values) >= 2:
        sal_min, sal_max = min(values[:2]), max(values[:2])
    else:
        return None, None, ""

    # Sanity bounds
    if sal_min > SALARY_MAX_USD or sal_max < SALARY_MIN_USD:
        return None, None, ""
    sal_min = max(sal_min, SALARY_MIN_USD)
    sal_max = min(sal_max, SALARY_MAX_USD)

    return round(sal_min, 2), round(sal_max, 2), "USD"


def normalize_salary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill salary_min / salary_max from raw salary string where missing.
    All monetary values unified to USD for cross-source comparison.
    """
    def _fill_row(row):
        sal_min = row.get("salary_min")
        sal_max = row.get("salary_max")
        currency = row.get("salary_currency", "")

        # Already parsed and reasonable
        if pd.notna(sal_min) and pd.notna(sal_max) and sal_min > 0:
            # Convert VND to USD if needed
            if str(currency).upper() == "VND":
                sal_min = sal_min * VND_TO_USD
                sal_max = sal_max * VND_TO_USD
                currency = "USD"
            # Sanity check
            if SALARY_MIN_USD <= sal_min <= SALARY_MAX_USD:
                return sal_min, sal_max, "USD"

        # Parse from salary string
        sal_str = row.get("salary", "")
        return _parse_salary_string(sal_str)

    results = df.apply(_fill_row, axis=1)
    df["salary_min_usd"] = results.apply(lambda x: x[0])
    df["salary_max_usd"] = results.apply(lambda x: x[1])
    df["salary_currency_norm"] = results.apply(lambda x: x[2])

    # Compute midpoint for analysis
    mask = df["salary_min_usd"].notna() & df["salary_max_usd"].notna()
    df.loc[mask, "salary_midpoint_usd"] = (
        (df.loc[mask, "salary_min_usd"] + df.loc[mask, "salary_max_usd"]) / 2
    ).round(2)

    # Flag
    df["has_salary"] = df["salary_min_usd"].notna()
    df["is_negotiable"] = df["salary"].fillna("").apply(_is_negotiable)

    filled = df["salary_min_usd"].notna().sum()
    logger.info(f"  normalize_salary: {filled}/{len(df)} records with parsed salary")
    return df


# ── Location normalization ─────────────────────────────────────────────────────

def normalize_location(location: str) -> str:
    """Map raw location strings to canonical city names using LOCATION_MAP."""
    from config import LOCATION_MAP

    if not location or not isinstance(location, str):
        return "Unknown"

    loc = location.strip()
    loc_lower = loc.lower()

    # Direct map lookup
    for raw, canonical in LOCATION_MAP.items():
        if raw.lower() in loc_lower:
            return canonical

    # Handle "| " separated multi-city strings (e.g. "Ho Chi Minh | Ha Noi")
    parts = re.split(r"[|,;/]", loc)
    if len(parts) > 1:
        first = normalize_location(parts[0].strip())
        if first and first != "Unknown":
            return first + " + more"

    # Return cleaned original if no match
    return loc.strip().title() if loc.strip() else "Unknown"


def normalize_location_column(df: pd.DataFrame) -> pd.DataFrame:
    """Apply location normalization and add city/region columns."""
    df["location_normalized"] = df["location"].fillna("").apply(normalize_location)

    # is_remote flag
    df["is_remote"] = df["location"].fillna("").str.lower().apply(
        lambda x: "remote" in x or "từ xa" in x or "work from home" in x.lower()
    ) | df["employment_type"].fillna("").str.lower().apply(
        lambda x: "remote" in x
    )

    return df


# ── Skills normalization ───────────────────────────────────────────────────────

# Canonical skill name mapping (raw → canonical)
_SKILL_ALIASES: dict[str, str] = {
    "pytorch": "PyTorch", "torch": "PyTorch",
    "tensorflow": "TensorFlow", "tf": "TensorFlow",
    "sklearn": "Scikit-learn", "scikit learn": "Scikit-learn",
    "scikit-learn": "Scikit-learn",
    "numpy": "NumPy", "np": "NumPy",
    "pandas": "Pandas", "pd": "Pandas",
    "js": "JavaScript", "javascript": "JavaScript", "es6": "JavaScript",
    "ts": "TypeScript", "typescript": "TypeScript",
    "nodejs": "Node.js", "node js": "Node.js", "node.js": "Node.js",
    "reactjs": "React", "react.js": "React", "react js": "React",
    "vuejs": "Vue.js", "vue js": "Vue.js", "vue.js": "Vue.js",
    "angularjs": "Angular", "angular js": "Angular",
    "mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "elasticsearch": "Elasticsearch", "elastic": "Elasticsearch",
    "k8s": "Kubernetes", "kube": "Kubernetes",
    "aws": "AWS", "amazon web services": "AWS",
    "gcp": "GCP", "google cloud": "GCP",
    "azure": "Azure", "microsoft azure": "Azure",
    "docker": "Docker", "dockerfile": "Docker",
    "git": "Git", "github": "Git", "gitlab": "Git",
    "ci/cd": "CI/CD", "cicd": "CI/CD",
    "ml": "Machine Learning", "machine learning": "Machine Learning",
    "dl": "Deep Learning", "deep learning": "Deep Learning",
    "ai": "AI", "artificial intelligence": "AI",
    "nlp": "NLP", "natural language processing": "NLP",
    "cv": "Computer Vision", "computer vision": "Computer Vision",
    "llm": "LLM", "large language model": "LLM",
    "rag": "RAG", "retrieval augmented generation": "RAG",
    "java": "Java", "spring": "Spring Boot", "spring boot": "Spring Boot",
    "python": "Python", "py": "Python",
    "golang": "Go", "go lang": "Go",
    "c#": "C#", ".net": ".NET", "dotnet": ".NET",
    "php": "PHP", "laravel": "Laravel",
    "swift": "Swift", "kotlin": "Kotlin",
    "flutter": "Flutter", "dart": "Flutter",
    "react native": "React Native",
    "sql": "SQL", "nosql": "NoSQL",
    "redis": "Redis", "kafka": "Kafka",
    "grafana": "Grafana", "kibana": "Kibana",
    "tableau": "Tableau", "power bi": "Power BI", "powerbi": "Power BI",
    "excel": "Excel", "vba": "VBA",
    "scrum": "Scrum", "agile": "Agile", "kanban": "Kanban",
}


def normalize_skill(skill: str) -> str:
    """Normalize a single skill name to its canonical form."""
    if not skill or not isinstance(skill, str):
        return ""
    s = skill.strip().lower()
    # Direct alias lookup
    if s in _SKILL_ALIASES:
        return _SKILL_ALIASES[s]
    # Partial match for known skills
    for raw, canonical in _SKILL_ALIASES.items():
        if raw == s:
            return canonical
    # Return cleaned original with Title case (but keep acronyms uppercase)
    return skill.strip()


def normalize_skills(skills: list) -> list[str]:
    """Normalize a list of skill strings."""
    if not skills:
        return []
    if isinstance(skills, str):
        # Parse comma-separated string
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    normalized = []
    seen = set()
    for sk in skills:
        norm = normalize_skill(str(sk))
        if norm and norm.lower() not in seen:
            normalized.append(norm)
            seen.add(norm.lower())
    return normalized[:25]


def normalize_skills_column(df: pd.DataFrame) -> pd.DataFrame:
    """Apply skills normalization and add skill_count column."""
    def _parse_skills(val):
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            if val.startswith("["):
                try:
                    import json
                    return json.loads(val)
                except Exception:
                    pass
            return [s.strip() for s in val.split(",") if s.strip()]
        return []

    df["skills_list"] = df["skills_required"].apply(_parse_skills)
    df["skills_normalized"] = df["skills_list"].apply(normalize_skills)
    df["skills_str"] = df["skills_normalized"].apply(lambda x: ", ".join(x))
    df["skill_count"] = df["skills_normalized"].apply(len)
    return df


# ── Experience normalization ───────────────────────────────────────────────────

_EXP_PATTERNS = [
    # "3+ years", "5 years", "2-4 years"
    (r"(\d+)\s*\+?\s*(?:to|-)\s*(\d+)\s*(?:year|yr|năm)", lambda m: float(m.group(1))),
    (r"(\d+)\s*\+\s*(?:year|yr|năm)", lambda m: float(m.group(1))),
    (r"(\d+)\s*(?:year|yr|năm)s?", lambda m: float(m.group(1))),
    # "ít nhất 2 năm", "tối thiểu 3 năm"
    (r"(?:ít nhất|tối thiểu|at least|minimum)\s*(\d+)", lambda m: float(m.group(1))),
    # "từ 2 năm", "from 2 years"
    (r"(?:từ|from)\s*(\d+)\s*(?:year|yr|năm)", lambda m: float(m.group(1))),
    # experience in months "24 months"
    (r"(\d+)\s*month", lambda m: round(float(m.group(1)) / 12, 1)),
]


def parse_experience_years(text: str) -> Optional[float]:
    """
    Extract numeric experience from strings like '3-5 years', 'ít nhất 2 năm'.
    Returns the minimum of the range (or the stated value).
    """
    if not text or not isinstance(text, str):
        return None
    text_lower = text.lower()

    # Fresher / intern = 0 years
    if any(k in text_lower for k in ["fresher", "fresh grad", "intern", "thực tập",
                                      "0 year", "no experience", "không yêu cầu"]):
        return 0.0

    for pattern, extractor in _EXP_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            try:
                val = extractor(m)
                if 0 <= val <= 20:
                    return val
            except Exception:
                continue
    return None


def infer_experience_level(
    years: Optional[float],
    title: str = "",
    job_level: str = "",
) -> str:
    """
    Map numeric years + title keywords → experience level.

    Levels: intern → fresher → junior → mid → senior → lead
    """
    title_lower = (title or "").lower()
    level_lower = (job_level or "").lower()

    # Direct level keywords (high priority)
    if any(k in title_lower or k in level_lower
           for k in ["intern", "thực tập", "trainee"]):
        return "intern"
    if any(k in title_lower for k in ["lead", "head", "manager", "director",
                                       "principal", "trưởng nhóm", "trưởng phòng"]):
        return "lead"
    if any(k in title_lower for k in ["senior", "sr.", "cao cấp"]):
        return "senior"
    if any(k in title_lower for k in ["fresher", "fresh grad"]):
        return "fresher"
    if any(k in title_lower for k in ["junior", "jr.", "entry"]):
        return "junior"

    # Years-based inference
    if years is not None:
        if years == 0:
            return "fresher"
        elif years < 1:
            return "junior"
        elif years < 3:
            return "junior"
        elif years < 5:
            return "mid"
        elif years < 8:
            return "senior"
        else:
            return "lead"

    # Job level field
    if "senior" in level_lower or "cao cấp" in level_lower:
        return "senior"
    if "junior" in level_lower or "fresher" in level_lower:
        return "junior"
    if "lead" in level_lower or "manager" in level_lower:
        return "lead"
    if "intern" in level_lower:
        return "intern"

    return "mid"   # default


def normalize_experience_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Fill experience_years from text fields and infer experience_level."""
    # Fill missing experience_years from job description text
    def _get_exp(row):
        val = row.get("experience_years")
        if pd.notna(val) and val is not None:
            try:
                return float(val)
            except Exception:
                pass
        # Try to extract from text fields
        for field in ["job_description", "requirements", "benefits"]:
            text = str(row.get(field) or "")
            if text and len(text) > 10:
                parsed = parse_experience_years(text)
                if parsed is not None:
                    return parsed
        # From job title and level
        title = str(row.get("job_title") or "")
        level = str(row.get("job_level") or "")
        if any(k in title.lower() for k in ["intern", "thực tập", "trainee"]):
            return 0.0
        if any(k in title.lower() for k in ["fresher", "fresh"]):
            return 0.0
        if any(k in title.lower() for k in ["junior", "jr.", "entry"]):
            return 0.5
        if any(k in title.lower() for k in ["senior", "sr."]):
            return 5.0
        return None

    df["experience_years_parsed"] = df.apply(_get_exp, axis=1)

    # Infer experience level
    df["experience_level_inferred"] = df.apply(
        lambda r: infer_experience_level(
            r.get("experience_years_parsed"),
            str(r.get("job_title") or ""),
            str(r.get("job_level") or ""),
        ),
        axis=1,
    )
    return df


# ── Date normalization ─────────────────────────────────────────────────────────

def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse posted_date / expiry_date into pandas datetime."""
    for col in ["posted_date", "expiry_date"]:
        if col not in df.columns:
            continue
        # Convert to datetime with error coercion
        df[f"{col}_dt"] = pd.to_datetime(
            df[col].replace(r"^\s*$", None, regex=True),
            errors="coerce",
            infer_datetime_format=True,
            utc=False,
        )
        # Days since posting (for posted_date)
        if col == "posted_date":
            reference = pd.Timestamp("2026-05-15")
            df["days_since_posted"] = (
                reference - df["posted_date_dt"]
            ).dt.days.clip(lower=0)

    return df
