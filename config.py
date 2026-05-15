"""
Project-level configuration.
All paths, constants, and taxonomy definitions live here.
Never hardcode these values in individual modules.
"""
from datetime import date
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
DATA_RAW       = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_CLEANED   = ROOT / "data" / "cleaned"
OUTPUTS        = ROOT / "outputs"
CHARTS_DIR     = OUTPUTS / "charts"
REPORTS_DIR    = OUTPUTS / "reports"
EXPORTS_DIR    = OUTPUTS / "exports"
NOTEBOOKS_DIR  = ROOT / "notebooks"

# Canonical dataset filenames
RAW_JOBS_FILE       = DATA_RAW / "jobs_raw.jsonl"


def raw_jobs_path(source: str) -> Path:
    """Return timestamped output path: data/raw/itviec_jobs_2026_05_14.jsonl"""
    from datetime import datetime
    date = datetime.now().strftime("%Y_%m_%d")
    return DATA_RAW / f"{source}_jobs_{date}.jsonl"
CLEANED_JOBS_FILE   = DATA_CLEANED / "jobs_cleaned.csv"
PROCESSED_JOBS_FILE = DATA_PROCESSED / "jobs_processed.parquet"

# ─── Analysis Time Window ─────────────────────────────────────────────────────
# Jobs outside this range are flagged out_of_range but NOT deleted from raw data.
# The preprocessing pipeline filters to in_analysis_period == True for the main dataset.
ANALYSIS_START_DATE = date(2025, 1, 1)
ANALYSIS_END_DATE   = date(2026, 5, 14)

# A job with unknown expiry is assumed active for this many days after posting.
ASSUMED_ACTIVE_DAYS = 90

# ─── Crawl Settings ───────────────────────────────────────────────────────────
CRAWL_DELAY_SECONDS = 2          # polite delay between requests
REQUEST_TIMEOUT     = 15
MAX_PAGES_PER_SOURCE = 20    # per search category (increased for 10K target)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ─── Dataset Schema ───────────────────────────────────────────────────────────
JOB_SCHEMA_FIELDS = [
    "job_title",
    "company_name",
    "salary",
    "salary_min",
    "salary_max",
    "salary_currency",
    "location",
    "employment_type",
    "job_level",
    "skills_required",
    "experience_years",
    "experience_level",
    "job_description",
    "benefits",
    "posted_date",
    "expiry_date",
    "url",
    "source_website",
    "industry",
    "job_type",
]

# ─── Job Title Whitelist ──────────────────────────────────────────────────────
# Expanded to all IT roles for 10K dataset target.
# AI/Data roles are still the primary focus for EDA insights.
VALID_JOB_TITLES = [
    # AI / Data / ML (primary focus)
    "AI Engineer", "Machine Learning Engineer", "ML Engineer",
    "Data Scientist", "Data Analyst", "Data Engineer",
    "NLP Engineer", "Computer Vision Engineer", "CV Engineer",
    "MLOps Engineer", "LLM Engineer", "Generative AI Engineer",
    "GenAI Engineer", "Deep Learning Engineer",
    "Business Intelligence", "BI Developer", "Analytics Engineer",
    "Data Architect", "Big Data", "AI Developer", "AI Researcher",
    # Backend / Server-side
    "Backend Developer", "Backend Engineer",
    "Software Engineer", "Software Developer",
    "Java Developer", "Python Developer", "Node.js Developer",
    "Go Developer", "C++ Developer", "Golang Developer",
    "PHP Developer", "Ruby Developer", ".NET Developer",
    "API Developer", "Microservices",
    # Frontend / Mobile
    "Frontend Developer", "Frontend Engineer",
    "React Developer", "Vue Developer", "Angular Developer",
    "iOS Developer", "Android Developer", "Mobile Developer",
    "React Native", "Flutter Developer",
    # Full-stack
    "Full-stack Developer", "Fullstack Developer",
    "Full Stack Engineer",
    # DevOps / Infrastructure / Cloud
    "DevOps Engineer", "SRE", "Site Reliability",
    "Cloud Engineer", "AWS Engineer", "GCP Engineer",
    "Kubernetes", "Docker", "Platform Engineer",
    "Infrastructure Engineer",
    # Security / QA / Other
    "Security Engineer", "Cybersecurity",
    "QA Engineer", "Test Engineer", "Automation Tester",
    "Blockchain Developer", "Embedded Engineer",
    "Solution Architect", "Technical Lead",
    "Product Manager", "Technical Project Manager",
    "Database Administrator", "DBA",
    "System Administrator", "Network Engineer",
    "Scrum Master", "Agile Coach",
    "Business Analyst", "System Analyst",
    "ERP", "SAP", "Salesforce",
]

VALID_JOB_KEYWORDS = [
    # AI/Data keywords
    "machine learning", "deep learning", "artificial intelligence",
    "data science", "data analysis", "data engineering",
    "nlp", "natural language processing", "computer vision",
    "mlops", "llm", "generative ai", "transformer",
    "pytorch", "tensorflow", "scikit-learn",
    # General IT keywords — all IT roles accepted
    "software", "developer", "engineer", "programmer",
    "backend", "frontend", "fullstack", "full-stack",
    "devops", "cloud", "aws", "azure", "gcp",
    "mobile", "android", "ios", "react", "vue", "angular",
    "java", "python", "nodejs", "golang", "php", "swift",
    "database", "sql", "nosql", "mongodb", "postgresql",
    "qa", "testing", "automation", "selenium",
    "security", "cybersecurity", "penetration",
    "blockchain", "embedded", "iot",
    "solution architect", "technical lead",
    "product manager", "project manager",
]

# ─── Location Normalization Map ───────────────────────────────────────────────
LOCATION_MAP = {
    "hcm": "Ho Chi Minh City",
    "hồ chí minh": "Ho Chi Minh City",
    "tp.hcm": "Ho Chi Minh City",
    "tp hcm": "Ho Chi Minh City",
    "tphcm": "Ho Chi Minh City",
    "sài gòn": "Ho Chi Minh City",
    "saigon": "Ho Chi Minh City",
    "hn": "Hanoi",
    "hà nội": "Hanoi",
    "ha noi": "Hanoi",
    "hanoi": "Hanoi",
    "đà nẵng": "Da Nang",
    "da nang": "Da Nang",
    "cần thơ": "Can Tho",
    "can tho": "Can Tho",
    "remote": "Remote",
    "toàn quốc": "Nationwide",
}

# ─── Skill Taxonomy ───────────────────────────────────────────────────────────
SKILL_TAXONOMY = {
    "programming_languages": [
        "Python", "R", "SQL", "Scala", "Java", "C++", "Julia",
        "Go", "Rust", "JavaScript", "TypeScript",
    ],
    "ml_frameworks": [
        "PyTorch", "TensorFlow", "Keras", "JAX", "MXNet",
        "Scikit-learn", "XGBoost", "LightGBM", "CatBoost",
        "Hugging Face", "Transformers", "ONNX",
    ],
    "data_tools": [
        "Pandas", "NumPy", "Dask", "PySpark", "Apache Spark",
        "Airflow", "dbt", "Great Expectations",
        "SQL", "PostgreSQL", "MySQL", "SQLite",
    ],
    "cloud_platforms": [
        "AWS", "GCP", "Azure", "S3", "EC2", "GCS",
        "BigQuery", "Redshift", "Databricks", "Snowflake",
    ],
    "mlops_tools": [
        "MLflow", "Kubeflow", "BentoML", "Seldon", "Ray",
        "Docker", "Kubernetes", "Terraform", "CI/CD",
        "GitHub Actions", "Jenkins",
    ],
    "visualization_tools": [
        "Matplotlib", "Seaborn", "Plotly", "Tableau",
        "Power BI", "Grafana", "Superset",
    ],
    "nlp_tools": [
        "spaCy", "NLTK", "Gensim", "BERTopic", "LangChain",
        "OpenAI", "GPT", "BERT", "LLaMA", "Llama",
    ],
    "computer_vision": [
        "OpenCV", "YOLO", "detectron2", "MMDetection",
        "PIL", "Albumentations", "torchvision",
    ],
    "databases": [
        "MongoDB", "Redis", "Elasticsearch", "Cassandra",
        "Neo4j", "Pinecone", "Weaviate", "ChromaDB",
    ],
    "soft_skills": [
        "English", "Communication", "Teamwork",
        "Problem Solving", "Agile", "Scrum",
    ],
}

# Flat skill list derived from taxonomy
ALL_SKILLS = [
    skill
    for skills in SKILL_TAXONOMY.values()
    for skill in skills
]

# ─── Salary Settings ──────────────────────────────────────────────────────────
SALARY_CURRENCIES = ["USD", "VND"]
USD_TO_VND = 25_000          # approximate exchange rate for normalization
SALARY_OUTLIER_THRESHOLD_USD = 50_000   # monthly salary cap for outlier filter

# ─── Experience Level Labels ──────────────────────────────────────────────────
EXPERIENCE_LEVELS = {
    "intern": (0, 0.5),
    "junior": (0.5, 2),
    "mid": (2, 5),
    "senior": (5, 10),
    "lead": (10, float("inf")),
}

# ─── Visualization Style ──────────────────────────────────────────────────────
CHART_THEME = "plotly_white"
COLOR_PRIMARY   = "#2563EB"   # blue
COLOR_SECONDARY = "#16A34A"   # green
COLOR_ACCENT    = "#DC2626"   # red
COLOR_PALETTE = [
    "#2563EB", "#16A34A", "#DC2626", "#9333EA",
    "#EA580C", "#0891B2", "#CA8A04", "#BE185D",
]
CHART_WIDTH  = 900
CHART_HEIGHT = 500
