# Job Market Intelligence & Resume Matching System
## AI/Data Careers in Vietnam 2025-2026

A Data Analysis and Visualization project focused on the Vietnamese AI/Data recruitment market, business intelligence dashboards, and lightweight resume-job matching.

---

# Features

## Job Market Intelligence
- AI/Data hiring trends
- Salary analytics
- Skill demand analysis
- Company hiring analysis
- Geographic hiring distribution

## NLP Job Description Mining
- Rule-based skill extraction
- TF-IDF keyword extraction
- Skill co-occurrence analysis
- Company-skill analysis

## Resume Analyzer
- CV parsing for PDF/DOCX/TXT
- Resume to JD matching
- ATS keyword analysis
- Missing skill detection
- Explainable resume scoring

## Production Platform Enhancements
- OAuth-ready authentication
- Role-based access control
- AI Agent automation workflow
- Automated dataset profiling and dashboard planning
- Deployment configuration for Streamlit Cloud and Render

---

# Tech Stack

## Data Processing
- Pandas
- NumPy

## Visualization
- Plotly
- Matplotlib
- Seaborn

## NLP & Matching
- scikit-learn
- Rule-based skill dictionaries
- Lightweight deterministic scoring

## Dashboard
- Streamlit
- Static HTML dashboard

## Production & Automation
- python-dotenv
- Streamlit Secrets
- OAuth via Google/GitHub
- Render/Streamlit Cloud deployment configs

---

# Project Structure

```text
Project/
|-- data/
|-- notebooks/
|-- src/
|   |-- agent/
|   |-- analysis/
|   |-- auth/
|   |-- crawler/
|   |-- nlp/
|   |-- platform/
|   |-- preprocessing/
|   `-- resume_analyzer/
|-- pages/
|-- utils/
|-- outputs/
|-- app.py
|-- PROJECT_CONTEXT.md
|-- PLANNING.md
|-- TASK.md
|-- DEPLOYMENT.md
|-- README.md
`-- requirements.txt
```

---

# Setup

## Create virtual environment

```bash
python -m venv .venv
```

## Activate environment

Windows:

```bash
.venv\Scripts\activate
```

Linux/Mac:

```bash
source .venv/bin/activate
```

## Install dependencies

Production dashboard:

```bash
pip install -r requirements.txt
```

Full local development/crawling/notebook environment:

```bash
pip install -r requirements-full.txt
```

---

# Run Dashboard

```bash
streamlit run app.py
```

## Production Configuration

Copy `.env.example` to `.env` for local production-style settings:

```bash
cp .env.example .env
```

Important variables:

```text
AUTH_ENABLED=false
APP_BASE_URL=http://localhost:8501
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
USER_ROLE_MAP={"admin@example.com":"admin","analyst@example.com":"analyst"}
```

For Streamlit Cloud, use `.streamlit/secrets.example.toml` as the template and store real secrets in the platform secret manager. See `DEPLOYMENT.md` for Streamlit Cloud and Render deployment steps.

Vietnamese quickstart:

```text
DEPLOYMENT_QUICKSTART_VI.md
```

---

# Run HTML Dashboard

Static HTML dashboard:

```text
outputs/dashboard/index.html
```

Recommended local server from `Project/` so the dashboard can load CSV automatically:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/outputs/dashboard/index.html
```

---

# Final Deliverables

- Report (.docx/.pdf)
- Slides (.pptx)
- Source code
- Dashboard demo
- Optional deployed dashboard URL
- Production deployment guide

---

# Language Policy

- Technical documentation: English
- Academic report/slides: Vietnamese
- Dashboard explanations: Vietnamese

---

# Course

Data Analysis and Visualization
