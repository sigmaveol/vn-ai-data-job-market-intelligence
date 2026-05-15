"""Data loading, caching, filtering for the VN Job Market dashboard."""
import re
from pathlib import Path
from collections import Counter
from itertools import combinations
import pandas as pd
import numpy as np
import streamlit as st

DATA_PATH = Path(__file__).parent.parent / 'data' / 'processed' / 'jobs_processed.parquet'
CSV_DATA_PATH = Path(__file__).parent.parent / 'data' / 'processed' / 'jobs_processed.csv'

# ── Role taxonomy ──────────────────────────────────────────────────────────────
ROLE_MAP = {
    'Data Analyst':     ['data analyst','business intelligence','bi analyst','reporting analyst','phân tích dữ liệu'],
    'Business Analyst': ['business analyst','system analyst','systems analyst','product analyst'],
    'Data Engineer':    ['data engineer','etl engineer','data pipeline','data platform','kỹ sư dữ liệu'],
    'AI/ML Engineer':   ['ai engineer','ml engineer','machine learning engineer','deep learning','nlp engineer','computer vision engineer','artificial intelligence'],
    'Data Scientist':   ['data scientist','research scientist','applied scientist','khoa học dữ liệu'],
    'MLOps/DevOps':     ['mlops','devops engineer','platform engineer','cloud engineer','site reliability','sre'],
    'Software Engineer':['software engineer','backend engineer','frontend engineer','fullstack','full stack','lập trình viên','developer'],
    'Manager/Lead':     ['manager','head of data','head of ai','director','chief data','tech lead','data lead','trưởng nhóm'],
    'Database/DBA':     ['dba','database administrator','database engineer','sql developer'],
    'Intern/Fresher':   ['intern','thực tập','fresher','trainee','graduate'],
}

SOFT_SKILLS = {
    'communication','teamwork','leadership','problem solving','critical thinking',
    'time management','agile','scrum','english','presentation','analytical',
    'microsoft office','word','excel','powerpoint','work','ability','experience',
    'knowledge','skill','team','project','management','customer','service',
}

EXP_ORDER = ['intern','fresher','junior','middle','senior','lead','manager']

# ── Core loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_parquet(DATA_PATH)
    except Exception:
        df = pd.read_csv(CSV_DATA_PATH)

    df['job_title'] = _col(df, 'job_title', '').astype(str)
    df['company_name'] = _col(df, 'company_name', 'Không rõ').astype(str)
    df['skills_str'] = _col(df, 'skills_str', '').astype(str)
    df['source_website'] = _col(df, 'source_website', 'Không rõ').astype(str)
    df['experience_level_inferred'] = _col(df, 'experience_level_inferred', 'unknown').astype(str)
    df['salary_midpoint_usd'] = pd.to_numeric(_col(df, 'salary_midpoint_usd', np.nan), errors='coerce')
    df['is_remote'] = _bool_col(df, 'is_remote')

    df['role_category'] = df['job_title'].apply(_categorize_role)
    df['_skills_list'] = df['skills_str'].apply(_parse_skills)
    date_source = _col(df, 'posted_date_dt', pd.NaT)
    df['_date'] = pd.to_datetime(date_source, errors='coerce')
    df['_month'] = df['_date'].dt.to_period('M').astype(str)
    df['_month'] = df['_month'].where(df['_month'] != 'NaT', None)
    # Normalize location
    location = df.get('location_normalized', df.get('location'))
    df['city'] = location.fillna('Khác') if location is not None else 'Khác'
    return df


def _col(df: pd.DataFrame, name: str, default):
    if name in df.columns:
        return df[name].fillna(default)
    return pd.Series([default] * len(df), index=df.index)


def _bool_col(df: pd.DataFrame, name: str) -> pd.Series:
    if name not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    s = df[name].fillna(False)
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().isin(['true', '1', 'yes', 'remote'])


def infer_role_category(title: str) -> str:
    t = str(title).lower()
    for role, kws in ROLE_MAP.items():
        if any(k in t for k in kws):
            return role
    return 'Khác'


def parse_skills(s) -> list[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    items = re.split(r'[;,\n|]', s)
    out = []
    for item in items:
        sk = item.strip().lower().strip('"\'')
        if sk and 2 < len(sk) < 40 and sk not in SOFT_SKILLS:
            out.append(sk)
    return out


def infer_city(row_or_location) -> str:
    """Infer display city from a row or raw location string."""
    if isinstance(row_or_location, pd.Series):
        value = row_or_location.get('location_normalized') or row_or_location.get('location')
    else:
        value = row_or_location
    if pd.isna(value) or not str(value).strip():
        return 'Khác'
    return str(value)


def _categorize_role(title: str) -> str:
    return infer_role_category(title)


def _parse_skills(s) -> list[str]:
    return parse_skills(s)


# ── Filter helpers ─────────────────────────────────────────────────────────────
def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    cities = f.get('cities', [])
    roles  = f.get('roles', [])
    exps   = f.get('exps', [])
    srcs   = f.get('sources', [])
    remote = f.get('remote', 'Tất cả')
    sal_rng = f.get('salary_range', (0, 10000))

    if cities:
        df = df[df['city'].isin(cities)]
    if roles:
        df = df[df['role_category'].isin(roles)]
    if exps:
        df = df[df['experience_level_inferred'].isin(exps)]
    if srcs:
        df = df[df['source_website'].isin(srcs)]
    if remote == 'Remote':
        df = df[df['is_remote'] == True]
    elif remote == 'Onsite':
        df = df[df['is_remote'] == False]
    # Salary filter only on rows with salary
    df_sal_mask = df['salary_midpoint_usd'].notna()
    df_no_sal = df[~df_sal_mask]
    df_with_sal = df[df_sal_mask]
    df_with_sal = df_with_sal[
        (df_with_sal['salary_midpoint_usd'] >= sal_rng[0]) &
        (df_with_sal['salary_midpoint_usd'] <= sal_rng[1])
    ]
    df = pd.concat([df_with_sal, df_no_sal], ignore_index=True)
    return df


def get_filtered_df() -> pd.DataFrame:
    return apply_filters(load_data(), st.session_state.get('filters', {}))


def filter_data(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Compatibility wrapper for dashboard builders."""
    return apply_filters(df, filters)


def get_salary_df(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = get_filtered_df()
    return df[df['salary_midpoint_usd'].notna() & (df['salary_midpoint_usd'] > 0) & (df['salary_midpoint_usd'] < 10000)].copy()


# ── Skill aggregates ───────────────────────────────────────────────────────────
def get_skill_counts(df: pd.DataFrame) -> Counter:
    c = Counter()
    for lst in df['_skills_list']:
        c.update(lst)
    return c


def skill_by_role_matrix(df: pd.DataFrame, top_skills: int = 12, top_roles: int = 6) -> pd.DataFrame:
    roles = df['role_category'].value_counts().head(top_roles).index.tolist()
    all_counts = get_skill_counts(df)
    top_sk = [s for s, _ in all_counts.most_common(top_skills)]
    rows = {}
    for role in roles:
        sub = df[df['role_category'] == role]
        sc = get_skill_counts(sub)
        rows[role] = {sk: sc.get(sk, 0) for sk in top_sk}
    return pd.DataFrame(rows, index=top_sk)


def skill_pair_rankings(df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    counter = Counter()
    for skills in df['_skills_list']:
        unique = sorted(set(skills))
        for left, right in combinations(unique, 2):
            counter[(left, right)] += 1
    rows = [
        {'skill_a': left, 'skill_b': right, 'count': count}
        for (left, right), count in counter.most_common(top_n)
    ]
    return pd.DataFrame(rows)


def high_paying_skills(df_sal: pd.DataFrame, min_count: int = 15) -> pd.DataFrame:
    skill_sal: dict[str, list] = {}
    for _, row in df_sal.iterrows():
        for sk in row['_skills_list']:
            skill_sal.setdefault(sk, []).append(row['salary_midpoint_usd'])
    rows = [{'skill': sk, 'median_salary': np.median(vals), 'count': len(vals)}
            for sk, vals in skill_sal.items() if len(vals) >= min_count]
    if not rows:
        return pd.DataFrame(columns=['skill', 'median_salary', 'count'])
    return pd.DataFrame(rows).sort_values('median_salary', ascending=False).head(15)


def dataset_summary(df: pd.DataFrame) -> dict:
    df_sal = get_salary_df(df)
    return {
        'jobs': len(df),
        'companies': df['company_name'].nunique() if 'company_name' in df else 0,
        'cities': df['city'].nunique() if 'city' in df else 0,
        'sources': df['source_website'].nunique() if 'source_website' in df else 0,
        'salary_coverage': 100 * len(df_sal) / len(df) if len(df) else 0,
    }
