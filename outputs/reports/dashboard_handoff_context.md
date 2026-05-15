# Dashboard Handoff Context

Use this file as the full context for another AI/chat session to continue or rebuild the dashboard without losing project direction.

## Project Identity

Project name: **Job Market Intelligence & Resume Matching System**

Topic: **AI/Data Careers in Vietnam 2025-2026**

Course: **Data Analysis and Visualization (505067)**

Team:
- Hoang Sinh Hung - 52300106
- Tran Thien Hung - 52300109

Primary goal: build a professional analytics dashboard for the Vietnamese AI/Data labor market.

This is a **data analysis, visualization, and business intelligence** project. It is not primarily a deep learning or NLP research project.

## Priority

The dashboard should emphasize:
- EDA
- Visualization
- Business insights
- Dashboard UX
- Presentation-ready storytelling

Secondary features:
- NLP skill extraction
- Resume Analyzer
- ML experiments

Do not over-focus on advanced ML/NLP before the dashboard is presentation-ready.

## Current Repository Root

Main project folder:

```text
Project/
```

Important files:

```text
Project/app.py
Project/pages/1_Salary.py
Project/pages/2_Skills.py
Project/pages/3_Company.py
Project/pages/4_Geographic.py
Project/pages/5_Timeseries.py
Project/pages/6_Resume.py
Project/pages/7_About.py
Project/utils/data_loader.py
Project/utils/charts.py
Project/utils/sidebar.py
Project/utils/style.py
Project/utils/export.py
Project/utils/insights.py
Project/data/processed/jobs_processed.csv
Project/data/processed/jobs_processed.parquet
Project/outputs/dashboard/index.html
Project/outputs/charts/
```

## Data

Primary processed dataset:

```text
Project/data/processed/jobs_processed.csv
Project/data/processed/jobs_processed.parquet
```

Approximate dataset size: around **7,051 job postings**.

Sources:
- 123job
- VietnamWorks
- ITviec
- TopDev
- TopCV
- CareerViet

Analysis period: **January-May 2026**.

Canonical important columns:

```text
job_id
job_hash
job_title
company_name
company_name_normalized
salary
salary_min_usd
salary_max_usd
salary_midpoint_usd
salary_currency_norm
has_salary
is_negotiable
location
location_normalized
is_remote
employment_type
job_level
skills_str
skill_count
experience_years_parsed
experience_level_inferred
job_description
benefits
posted_date
posted_date_dt
expiry_date
expiry_date_dt
days_since_posted
url
source_website
industry
job_type
data_completeness
crawled_at
is_active
in_analysis_period
```

Useful derived fields already handled in `utils/data_loader.py`:
- `role_category`
- `_skills_list`
- `_date`
- `_month`
- `city`

## Existing Phase Status

Completed before dashboard work:
- Phase 1: Repository setup and skeleton architecture
- Phase 2: Data collection pipeline
- Phase 3: Preprocessing and validation
- Phase 4: EDA and chart export

Current focus:
- Phase 5: Dashboard development and visualization system

Phase 6:
- Lightweight NLP and Resume Analyzer have been implemented.
- Resume Analyzer is deterministic and explainable, not a production ATS platform.

## Dashboard Requirements

The dashboard should look like:
- Power BI
- Tableau
- Modern analytics SaaS dashboard
- Professional portfolio BI project

It should not look like:
- Raw notebook in a browser
- Developer-only Streamlit demo
- Cluttered classroom project

Required pages/sections:
- Overview
- Salary Analytics
- Skill Analytics
- Company Analytics
- Geographic Analytics
- Hiring Trends / Timeseries
- Resume Analyzer

Required features:
- Sidebar/global filters
- KPI cards
- Interactive charts
- Responsive layout
- Insight panels
- Download/export datasets
- Optional chart/image export

Preferred UI language:
- Vietnamese labels and explanations
- English variable names and technical implementation

## Recommended Dashboard Layout

For a single-page HTML dashboard, prefer one unified BI canvas:

```text
Header
Filters row
KPI row
Main dashboard grid:
  - Role demand chart
  - City demand chart
  - Skill demand chart
  - Source share chart
  - Salary distribution
  - Experience level chart
Insight strip
```

Do not split every chart into visually unrelated cards if the page becomes fragmented. A unified panel with internal chart regions is preferred.

For Streamlit, multipage layout is acceptable:
- `app.py` as Overview
- `pages/*.py` for deep-dive pages

## Visual Direction

Current requested style:
- Light theme
- Clean BI layout
- White cards/panels
- Soft gray background
- Blue primary accent
- restrained multi-color chart palette

Suggested palette:

```text
background: #f6f8fc
surface: #ffffff
border: #dbe3ef
text: #0f172a
muted: #64748b
primary blue: #2563eb
cyan: #0284c7
green: #059669
orange: #ea580c
rose: #e11d48
purple: #7c3aed
```

Avoid:
- dark-only dashboard
- excessive purple gradients
- decorative blobs/orbs
- marketing hero page
- overly rounded cards

## Existing Streamlit Dashboard

Run from `Project/`:

```bash
streamlit run app.py
```

Theme config:

```text
Project/.streamlit/config.toml
```

Shared modules:

```text
utils/style.py      # palette, CSS, Plotly layout
utils/charts.py     # reusable Plotly chart components
utils/sidebar.py    # sidebar filters and data status
utils/data_loader.py # load, normalize, filter, aggregate
utils/export.py     # CSV and optional PNG export helpers
utils/insights.py   # Vietnamese business insight text
```

Known Streamlit implementation notes:
- `utils/data_loader.py` loads Parquet first and falls back to CSV.
- `role_category` is inferred from job titles.
- `_skills_list` parses `skills_str`.
- Salary analysis uses `salary_midpoint_usd`.
- Current Plotly layout has been changed to light theme.
- PNG export is optional and controlled by sidebar toggle `Bật nút tải PNG`.

Important bug already fixed:
- `pie_donut()` previously caused Plotly duplicate `legend` keyword error. It now merges layout dict before `fig.update_layout()`.

If the old error still appears, restart Streamlit and delete cache:

```powershell
Remove-Item -Recurse -Force .\utils\__pycache__
streamlit run app.py
```

## Existing HTML Dashboard

Static dashboard file:

```text
Project/outputs/dashboard/index.html
```

Recommended run from `Project/`:

```bash
python -m http.server 8000
```

Open:

```text
http://localhost:8000/outputs/dashboard/index.html
```

Open it through the local server so the browser can load the CSV file.

HTML dashboard behavior:
- Loads CSV from `../../data/processed/jobs_processed.csv`
- Has filters for city, role, source, and experience level
- Computes KPIs in browser
- Draws charts with inline SVG, no external libraries
- Uses one unified dashboard frame

## Business Questions To Answer

Overview:
- How large is the AI/Data job market in the dataset?
- Which roles are most in demand?
- Which locations dominate?
- Which sources contribute most data?

Salary:
- What is median/average salary?
- How does salary vary by role?
- How does salary vary by city?
- Which skills correlate with higher salaries?
- What share of postings disclose salary?

Skills:
- Which skills are most required?
- Which skills appear across multiple roles?
- Which technical stack is strongest?
- What skill gaps should candidates prioritize?

Company:
- Which companies hire most aggressively?
- Are top companies specialized by role?
- What is remote vs onsite distribution?

Geographic:
- Which cities dominate hiring?
- How do Hanoi and Ho Chi Minh City differ?
- Which locations offer higher median salaries?

Trends:
- How does hiring change month by month?
- Which roles are growing?
- Are there day-of-week posting patterns?

Resume Analyzer:
- Use it as a lightweight, explainable demo feature.
- It supports PDF/DOCX/TXT/manual text input, JD selection, scoring, missing skills, recommendations, and CSV export.

## Current Completion State

Phase 5 is mostly complete in code:
- Streamlit multipage dashboard exists
- HTML dashboard exists
- Filters exist
- KPI cards exist
- Interactive Plotly charts exist in Streamlit
- CSV export exists
- Optional PNG export exists
- Light theme has been applied

Phase 6 is implemented in code:
- Skill extraction
- TF-IDF keyword extraction
- Skill co-occurrence ranking
- Resume parser
- Resume/JD matcher
- Explainable scoring
- Missing skill recommendations
- Resume Analyzer dashboard page

Still needs:
- Manual visual QA in browser
- Check all filters after running
- Check downloads
- Polish final copy/labels if needed
- Decide whether final presentation uses Streamlit, HTML dashboard, or both

## Guardrails For Next AI

Do:
- Preserve existing architecture unless there is a clear reason.
- Reuse processed dataset.
- Keep dashboard analytics-focused.
- Keep labels and explanations in Vietnamese.
- Keep implementation understandable for a university project.
- Prefer robust, simple BI visuals.
- Add comments only where useful.

Do not:
- Rebuild crawlers.
- Rewrite preprocessing pipeline.
- Replace the whole repo structure.
- Add heavy frontend frameworks unless explicitly requested.
- Invent fake data or fake insights.
- Over-engineer ML/NLP.

## Suggested Next Prompt

You can paste this to another chat:

```text
You are continuing a Vietnamese Data Analysis and Visualization project.
Read the provided handoff context carefully.
The goal is to improve or rebuild the dashboard only, using the processed dataset at Project/data/processed/jobs_processed.csv.
Keep the project analytics-focused and presentation-ready.
Use a light BI theme similar to Power BI/Tableau.
Do not modify crawler or preprocessing architecture.
Build a clean dashboard with filters, KPI cards, role/city/skill/salary/company/geographic/trend charts, insight panels, and export options.
Use Vietnamese UI labels.
```
