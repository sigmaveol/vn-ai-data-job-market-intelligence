# Phase 6 NLP & Resume Analyzer Summary

## Scope

Phase 6 adds lightweight, deterministic NLP enhancements and a practical Resume Analyzer. It supports dashboard storytelling and business value without turning the project into a deep learning or ATS benchmark.

## Implemented Modules

```text
src/nlp/skill_extractor.py
src/nlp/keyword_extractor.py
src/resume_analyzer/parser.py
src/resume_analyzer/matcher.py
pages/6_Resume.py
```

## NLP Enhancements

- Rule-based skill extraction from job descriptions and resumes
- Skill alias normalization
- Skill category lookup from `config.SKILL_TAXONOMY`
- TF-IDF keyword extraction with deterministic fallback
- Role/company keyword association helper methods
- Skill co-occurrence pair rankings
- Skill Analytics dashboard now includes:
  - Top JD keywords
  - Top skill pairs
  - CSV export for skill pairs

## Resume Analyzer

Supported input:

- PDF via `pdfplumber`
- DOCX via `python-docx`
- TXT via plain text decoding
- Manual resume text paste in dashboard

Extracted signals:

- Resume text
- Resume sections
- Candidate skills
- JD skills
- ATS/JD keywords
- Candidate experience input
- Required experience inferred from JD text

## Scoring Logic

The score is deterministic and explainable:

```text
60% skill overlap
20% keyword overlap
20% experience alignment
```

Outputs:

- Match score
- Skill score
- Keyword score
- Experience score
- Matched skills
- Missing skills
- Resume-only skills
- Matched keywords
- Missing keywords
- Recommendations

## Dashboard Page

Updated page:

```text
pages/6_Resume.py
```

Features:

- CV upload
- Manual CV text fallback
- JD selector from filtered dataset
- Role filter for JD list
- Match score KPI cards
- Radar chart
- Progress breakdown
- Skill overlap panels
- ATS keyword panels
- Recommendations
- Parsed resume sections
- CSV exports:
  - summary
  - skills
  - recommendations
  - full report

## Validation Notes

Python/Streamlit runtime was not available on PATH in the current shell, so validation was source-level only. Run manually:

```powershell
cd Project
streamlit run app.py
```

Then test:

- Upload `outputs/exports/sample_resume_data_analyst.txt` first
- Select a JD
- Confirm scores are stable across refreshes
- Confirm missing skills table is deterministic
- Confirm CSV exports work
- Test PDF/DOCX only if `pdfplumber` and `python-docx` are installed
