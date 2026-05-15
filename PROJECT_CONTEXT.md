# PROJECT_CONTEXT.md

# Job Market Intelligence & Resume Matching System
## AI/Data Careers in Vietnam 2025–2026

> AI-first operational context document.
> This file is designed for engineers and AI agents working inside this repository.
> The purpose is to ensure deterministic development, reproducible analysis, and consistent project architecture.

---

# 1. Project Overview

This project analyzes the AI/Data recruitment market in Vietnam during 2025–2026 and builds an intelligent resume matching system.

The project combines:
1. Job Market Intelligence
2. NLP-based Job Description Mining
3. AI Resume Analyzer

The system collects Vietnamese job postings, extracts structured insights, analyzes hiring trends, and evaluates resume compatibility against job descriptions.

The project is developed for the university course:
Data Analysis and Visualization.

---

# 2. Core Objectives

The system MUST answer the following questions:

## Market Intelligence
- Which AI/Data roles are most in demand?
- Which cities recruit AI talent the most?
- Which technical skills are trending?
- Which tech stacks are growing rapidly?
- Which companies hire aggressively?

## NLP Job Mining
- Which skills are associated with which companies?
- How do Junior and Senior requirements differ?
- Which skill clusters frequently appear together?
- How do salary and skills correlate?

## Resume Analysis
- How compatible is a CV with a job description?
- Which skills are missing?
- Which ATS keywords are absent?
- How strong is the resume-job match?

# Project Priority

The PRIMARY objective of this project is:
- Exploratory Data Analysis (EDA)
- Data Visualization
- Business Insight Generation

The project is fundamentally a Data Analysis and Visualization project, NOT a production NLP system.

---

# Priority Order

The AI agent MUST prioritize work in the following order:

1. Data Collection
2. Data Cleaning
3. Exploratory Data Analysis (MOST IMPORTANT)
4. Visualization & Insight Generation
5. Dashboard Development
6. NLP Enhancements
7. Resume Analyzer
8. Machine Learning Experiments

---

# Critical Requirement

The project MUST emphasize:
- meaningful visualizations
- business insights
- hiring trend analysis
- skill demand analysis
- salary analysis
- storytelling through charts and dashboards

The following are considered secondary:
- advanced NLP modeling
- deep learning experimentation
- production-grade resume scoring
- state-of-the-art ML performance

---

# Visualization Importance

Charts, dashboards, and business insights are considered the core deliverables of this project.

The project SHOULD resemble:
- a professional analytics dashboard
- a business intelligence platform
- a labor market analytics system

The project SHOULD NOT resemble:
- a pure NLP research project
- a machine learning benchmark project
- a resume parser-only application
- a deep learning engineering project

---

# 3. High-Level System Architecture

```text
┌────────────────────────────────────────────┐
│ Vietnamese Recruitment Websites:ITviec /   │
│  TopCV / TopDev / VietnamWorks / LinkedIn  │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
          ┌────────────────────────┐
          │ Data Collection Layer  │
          │ Crawlers / APIs        │
          └──────────┬─────────────┘
                     │ raw jobs
                     ▼
          ┌────────────────────────┐
          │ Data Cleaning Pipeline │
          │ normalization/filter   │
          └──────────┬─────────────┘
                     │ cleaned jobs
                     ▼
     ┌──────────────────────────────────────┐
     │ NLP Extraction & Feature Engineering │
     │ skills / salary / level / keywords   │
     └───────────────┬──────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌─────────────────┐     ┌──────────────────┐
│ Market Analytics│     │ JD Mining Module │
│ EDA + charts    │     │ NLP clustering   │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └──────────┬────────────┘
                    ▼
         ┌────────────────────────┐
         │ Resume Analyzer Module │
         │ CV ↔ JD matching       │
         └──────────┬─────────────┘
                    ▼
         ┌────────────────────────┐
         │ Dashboard + Reports    │
         └────────────────────────┘
```

# 4. Project Scope

The project ONLY focuses on:
- AI jobs
- Data jobs
- Machine Learning jobs
- NLP jobs
- Computer Vision jobs
- MLOps jobs

Valid job titles include:
- AI Engineer
- Machine Learning Engineer
- Data Scientist
- Data Analyst
- Data Engineer
- NLP Engineer
- Computer Vision Engineer
- MLOps Engineer
- LLM Engineer
- Generative AI Engineer

The project MUST NOT include:
- unrelated software jobs
- business-only jobs
- marketing positions
- non-technical roles

---

# 5. Data Sources

Primary sources:

- https://itviec.com
- https://topcv.vn
- https://topdev.vn
- https://vietnamworks.com
- LinkedIn

Optional:
- LinkedIn datasets
- Kaggle datasets
- public GitHub datasets

The system MUST only use publicly accessible information.

---

# 6. Dataset Schema

Canonical dataset schema:

```json
{
  "job_title": "string",
  "company_name": "string",
  "salary": "string",
  "salary_min": "float | null",
  "salary_max": "float | null",
  "salary_currency": "string",
  "location": "string",
  "employment_type": "string",
  "job_level": "string",
  "skills_required": ["string"],
  "experience_years": "float | null",
  "experience_level": "string",
  "job_description": "string",
  "benefits": "string",
  "posted_date": "datetime",
  "expiry_date": "datetime",
  "url": "string",
  "source_website": "string",
  "industry": "string",
  "job_type": "string"
}
```

---

# 7. Data Cleaning Rules

The preprocessing pipeline MUST:

1. Remove duplicate jobs
2. Normalize salary formats
3. Normalize locations
4. Normalize skill names
5. Handle missing values
6. Remove HTML tags
7. Remove invalid URLs
8. Standardize dates

Examples:

```text
"TP.HCM" → "Ho Chi Minh City"
"HCM" → "Ho Chi Minh City"
```

```text
"$1000-$2000" →
salary_min = 1000
salary_max = 2000
```

---

# 8. NLP Pipeline

The NLP system extracts information from job descriptions and resumes.

## Tasks

### Skill Extraction
Extract:
- programming languages
- frameworks
- cloud technologies
- AI libraries

### Keyword Extraction
Detect:
- ATS keywords
- important phrases
- trending technologies

### Topic Modeling
Discover:
- hidden job categories
- recruitment themes
- company preferences

### Clustering
Group:
- similar jobs
- similar skills
- similar companies

---

# 9. Resume Analyzer Pipeline

```text
CV Upload
    │
    ▼
Resume Parsing
    │
    ▼
Skill Extraction
    │
    ▼
Job Description Selection
    │
    ▼
Similarity & Keyword Matching
    │
    ▼
Resume Score Generation
    │
    ▼
Missing Skill Recommendations
```

---

# 10. Resume Analyzer Features

The Resume Analyzer SHOULD provide:

- Resume-job matching score
- Skill overlap percentage
- Missing skill detection
- ATS keyword analysis
- Resume recommendations

The scoring MUST remain deterministic and reproducible.

---

# 11. Exploratory Data Analysis (EDA)

The analysis pipeline MUST generate:

## Job Market Analysis
- Top job titles
- Job count by city
- Remote vs onsite jobs
- Hiring trends over time

## Salary Analysis
- Salary distribution
- Salary by role
- Salary by location
- Salary by experience

## Skill Analysis
- Most required skills
- Skill frequency
- Skill co-occurrence
- Trending technologies

## Company Analysis
- Top hiring companies
- Company-skill relationships

## Resume Analytics
- Match score distributions
- Missing skill frequency
- ATS keyword frequency

---

# 12. Visualization Requirements

The project MUST generate professional visualizations.

Recommended libraries:
- Plotly
- Matplotlib
- Seaborn

Required charts:
- Bar chart
- Histogram
- Heatmap
- Boxplot
- Treemap
- WordCloud
- Line chart
- Correlation matrix

All charts MUST:
- have titles
- have labels
- use readable styling
- be presentation-ready

---

# 13. Machine Learning & NLP Methods

Possible methods:

## NLP
- TF-IDF
- BERTopic
- Embedding clustering
- NER skill extraction

## ML
- salary prediction
- clustering
- trend forecasting

Recommended libraries:
- scikit-learn
- sentence-transformers
- spaCy
- BERTopic
- XGBoost

---

# 14. Dashboard Requirements

Preferred framework:
- Streamlit

Dashboard modules:

## A. Market Overview
- total jobs
- top companies
- top locations
- salary overview

## B. Skill Analytics
- top skills
- trending skills
- skill clusters

## C. Salary Analytics
- salary by location
- salary by role
- salary by experience

## D. NLP Job Mining
- topic clusters
- keyword extraction
- company preference analysis

## E. Resume Analyzer
- CV upload
- JD selection
- match score
- recommendations

The UI MUST:
- remain modern
- avoid excessive colors
- support filtering
- remain responsive

---

# 15. Folder Structure

```text
Project/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── cleaned/
│
├── notebooks/
│
├── src/
│   ├── crawler/
│   ├── preprocessing/
│   ├── analysis/
│   ├── nlp/
│   ├── ml/
│   ├── resume_analyzer/
│   ├── visualization/
│   └── dashboard/
│
├── outputs/
│   ├── charts/
│   ├── reports/
│   ├── slides/
│   └── exports/
│
├── app/
│
├── README.md
├── PROJECT_CONTEXT.md
├── requirements.txt
└── .gitignore
```

---

# 16. Module Responsibilities

| Module | Responsibility |
|---|---|
| `crawler/` | Data collection |
| `preprocessing/` | Cleaning & normalization |
| `analysis/` | EDA & statistics |
| `nlp/` | NLP pipelines |
| `ml/` | ML experiments |
| `resume_analyzer/` | Resume matching |
| `visualization/` | Charts |
| `dashboard/` | Streamlit dashboard |

---

# 17. Final Deliverables

The final submission MUST include:

## A. Report
Formats:
- DOCX
- PDF

## B. Slides
Formats:
- PPTX

## C. Source Code
Including:
- crawlers
- preprocessing
- NLP modules
- dashboard
- notebooks
- requirements.txt
- README.md

---

# Language Policy

## Technical Documentation
The following files MUST use English:
- PROJECT_CONTEXT.md
- README.md
- PLANNING.md
- ARCHITECTURE.md
- SPEC.md
- source code comments (optional)

Reason:
The repository is optimized for AI agents and modern software engineering workflows.

---

## Academic Deliverables
The following deliverables MUST use Vietnamese:
- final report (.docx/.pdf)
- presentation slides (.pptx)
- dashboard explanations
- chart insights
- business analysis

Reason:
The project is submitted to a Vietnamese university course.

---

## UI Language

The dashboard SHOULD:
- use Vietnamese labels
- use Vietnamese chart titles
- use Vietnamese explanations

Technical/internal variable names SHOULD remain in English.

---

## NLP Processing Language

The system processes:
- Vietnamese job descriptions
- Vietnamese resumes
- Vietnamese recruitment content

The NLP pipeline MUST support Vietnamese text normalization and tokenization.

---

# 18. Coding Standards

The agent MUST:
- write modular code
- avoid duplicated logic
- use meaningful variable names
- separate preprocessing and visualization logic
- keep notebooks clean

The agent SHOULD:
- use configuration files
- minimize hardcoded paths
- write reusable functions

---

# 19. Constraints

The system MUST NOT:
- fabricate data
- invent statistics
- generate fake insights
- use copyrighted/private datasets illegally
- scrape restricted/private systems

All insights MUST come from actual analysis.

---

# 20. Invariants (DO NOT VIOLATE)

- The project ONLY focuses on AI/Data-related jobs.
- Dataset schema consistency MUST be preserved.
- Salary normalization MUST remain deterministic.
- Charts MUST remain reproducible.
- Raw data MUST NOT be overwritten.
- NLP extraction MUST remain traceable.
- Resume scoring MUST remain deterministic.
- Folder structure MUST remain stable.
- Final outputs MUST be presentation-ready.
- The project should resemble a real-world analytics platform rather than a simple classroom notebook.