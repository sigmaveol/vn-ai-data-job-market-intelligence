# PLANNING.md

# Job Market Intelligence & Resume Matching System

> Operational planning document.
> Tracks project phases, execution roadmap, and development priorities.

---

# Phase 1 — Project Setup

## Objectives
- Setup repository structure
- Setup virtual environment
- Setup dependencies
- Create project documentation

## Tasks
- [ ] Create folder structure
- [ ] Create README.md
- [ ] Create PROJECT_CONTEXT.md
- [ ] Create requirements.txt
- [ ] Configure .gitignore

---

# Phase 2 — Data Collection

## Objectives
- Collect Vietnamese AI/Data job postings
- Build raw datasets

## Sources
- ITviec
- TopCV
- TopDev
- VietnamWorks

## Tasks
- [ ] Build crawler module
- [ ] Crawl job descriptions
- [ ] Save raw datasets
- [ ] Validate collected data

---

# Phase 3 — Data Preprocessing

## Objectives
- Clean and normalize datasets

## Tasks
- [ ] Remove duplicates
- [ ] Normalize salary
- [ ] Normalize locations
- [ ] Normalize skills
- [ ] Remove invalid records
- [ ] Export cleaned dataset

---

# Phase 4 — Exploratory Data Analysis

## Objectives
- Generate insights from datasets

## Tasks
- [ ] Salary analysis
- [ ] Skill analysis
- [ ] Company analysis
- [ ] Hiring trend analysis
- [ ] Geographic analysis

---

# Phase 5 — NLP Pipeline

## Objectives
- Extract meaningful information from job descriptions

## Tasks
- [ ] Skill extraction
- [ ] Keyword extraction
- [ ] Topic modeling
- [ ] Clustering
- [ ] Embedding analysis

---

# Phase 6 — Resume Analyzer

## Objectives
- Match resumes against job descriptions

## Tasks
- [ ] Resume parser
- [ ] Skill extraction
- [ ] Similarity scoring
- [ ] Missing skill detection
- [ ] ATS keyword analysis

---

# Phase 7 — Dashboard Development

## Objectives
- Build interactive dashboard

## Tasks
- [ ] Build Streamlit UI
- [ ] Add filters
- [ ] Add charts
- [ ] Add resume analyzer
- [ ] Optimize UI

---

# Phase 8 — Final Deliverables

## Objectives
- Prepare final submission

## Tasks
- [ ] Export charts
- [ ] Complete report
- [ ] Complete slides
- [ ] Clean source code
- [ ] Package ZIP submission

---

# Final Submission Structure

```text
Ten1MaSV_Ten2MaSV.zip
```

---

# Current Implementation Notes

The repository has advanced beyond the original phase labels above:

- Phase 4 EDA: implemented through analysis modules, notebooks, exported charts, and business insight outputs.
- Phase 5 Dashboard: implemented as Streamlit multipage dashboard plus static HTML dashboard.
- Phase 6 NLP/Resume Analyzer: implemented with lightweight skill extraction, keyword extraction, resume parser, matcher, scoring, and dashboard page.
- Phase 7 Production Platform: implemented as deployment-ready enhancements, not an enterprise backend.

## Phase 7 Scope

Completed in code:
- production settings with `.env` and Streamlit Secrets support
- OAuth-ready login flow for Google and optional GitHub
- Viewer/Analyst/Admin RBAC
- protected analyst pages
- AI Agent automation page
- reusable automated analytics pipeline
- deterministic KPI/chart/insight recommendations
- Render deployment config
- deployment documentation

External actions still required:
- create hosting project on Streamlit Cloud/Render
- add real OAuth credentials in the hosting secret manager
- set `AUTH_ENABLED=true`
- test login callback URL on the deployed domain
- copy the public URL into the final report/slides
