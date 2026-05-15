# PLANNING.md

# Job Market Intelligence & Resume Matching System

> Operational planning document.
> Tracks project phases, execution roadmap, and development priorities.

---

# Current Status

The project has completed Phase 1 to Phase 7 and is now in:

```text
Phase 8 - Final Deliverables & Packaging
```

Primary deliverable remains a Data Analysis and Visualization project:
- EDA
- dashboard
- business insights
- presentation-ready reporting

NLP and Resume Analyzer are supporting enhancements only.

---

# Phase 1 - Project Setup

## Status
- [x] Completed

## Objectives
- Setup repository structure
- Setup virtual environment
- Setup dependencies
- Create project documentation

## Tasks
- [x] Create folder structure
- [x] Create README.md
- [x] Create PROJECT_CONTEXT.md
- [x] Create requirements.txt
- [x] Configure .gitignore

---

# Phase 2 - Data Collection

## Status
- [x] Completed

## Objectives
- Collect Vietnamese AI/Data job postings
- Build raw datasets

## Sources
- ITviec
- TopCV
- TopDev
- VietnamWorks
- 123job
- CareerViet

## Tasks
- [x] Build crawler modules
- [x] Crawl job descriptions
- [x] Save raw datasets
- [x] Validate collected data

---

# Phase 3 - Data Preprocessing

## Status
- [x] Completed

## Objectives
- Clean and normalize datasets

## Tasks
- [x] Remove duplicates
- [x] Normalize salary
- [x] Normalize locations
- [x] Normalize skills
- [x] Remove invalid records
- [x] Export cleaned dataset

---

# Phase 4 - Exploratory Data Analysis

## Status
- [x] Completed

## Objectives
- Generate insights from datasets
- Build reusable visual analysis outputs
- Support business storytelling

## Tasks
- [x] Salary analysis
- [x] Skill analysis
- [x] Company analysis
- [x] Hiring trend analysis
- [x] Geographic analysis
- [x] Export EDA charts

---

# Phase 5 - Dashboard Development

## Status
- [x] Completed

## Objectives
- Build a professional analytics dashboard
- Present EDA findings clearly
- Create Power BI/Tableau-style dashboard UX

## Tasks
- [x] Build Streamlit UI
- [x] Add sidebar filters
- [x] Add KPI overview
- [x] Add interactive charts
- [x] Add salary analytics page
- [x] Add skill analytics page
- [x] Add company analytics page
- [x] Add geographic analytics page
- [x] Add hiring trend page
- [x] Add export functionality
- [x] Add static HTML dashboard

---

# Phase 6 - Resume Analyzer & NLP Enhancements

## Status
- [x] Completed

## Objectives
- Add lightweight NLP features
- Build a practical Resume Analyzer
- Enrich dashboard analytics

Resume Analyzer is a supporting feature, NOT the core of the project.

The implementation MUST remain:
- lightweight
- explainable
- analytics-oriented

Avoid:
- deep learning pipelines
- transformer fine-tuning
- RAG systems
- vector databases
- production ATS complexity

## Tasks
- [x] Resume parser (PDF/DOCX/TXT)
- [x] Skill extraction
- [x] ATS keyword extraction
- [x] Similarity scoring
- [x] Missing skill detection
- [x] Resume to JD matching
- [x] Resume scoring visualization
- [x] Resume Analyzer dashboard page

---

# Phase 7 - Dashboard Development & Final Packaging Preparation

## Status
- [x] Completed

## Objectives
- Build a professional analytics dashboard
- Finalize presentation-ready UI
- Prepare final deliverables

The dashboard MUST resemble:
- Power BI
- Tableau
- modern analytics dashboards

The dashboard SHOULD focus on:
- EDA
- business insights
- visualization
- storytelling

NOT:
- complex backend systems
- SaaS infrastructure
- authentication systems
- enterprise deployment

## Tasks
- [x] Build Streamlit UI
- [x] Add sidebar filters
- [x] Add interactive charts
- [x] Add KPI overview
- [x] Add salary analytics page
- [x] Add skill analytics page
- [x] Add geographic/company analytics
- [x] Integrate Resume Analyzer
- [x] Optimize dashboard UI/UX
- [x] Export charts & tables
- [x] Final dashboard polish
- [x] Prepare screenshots for report/slides
- [x] Final deployment preparation

---

# Phase 8 - Final Deliverables & Packaging

## Status
- [ ] In progress

## Objectives
- Prepare final course submission
- Package dashboard, report, slides, data, and source code
- Make the project easy to evaluate and present

## Tasks
- [ ] Final report DOCX/PDF
- [ ] Final presentation slides PPTX/PDF
- [ ] Dashboard screenshots
- [ ] Source code cleanup
- [ ] Final README check
- [ ] Final dataset/output check
- [ ] Package ZIP submission

---

# Final Submission Structure

```text
HoangSinhHung52300106_TranThienHung52300109.zip
```

Suggested contents:
- docs/report.pdf
- docs/report.docx
- slides/final_presentation.pptx
- Project/source_code
- Project/data/processed
- Project/outputs/charts
- Project/outputs/dashboard
- README.md
