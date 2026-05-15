# Deployment Guide

## Local Run

```powershell
cd Project
pip install -r requirements.txt
streamlit run app.py
```

`requirements.txt` is optimized for the production dashboard. Use `requirements-full.txt` only for local crawler, notebook, and optional ML/NLP research work.

## Environment Variables

Use `.env.example` as the source of truth. Never commit real secrets.

Minimum local demo:

```text
AUTH_ENABLED=false
APP_BASE_URL=http://localhost:8501
```

Production OAuth:

```text
AUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=https://your-app-url
USER_ROLE_MAP={"admin@example.com":"admin","analyst@example.com":"analyst"}
DEFAULT_AUTH_ROLE=viewer
```

## Streamlit Cloud

1. Push `Project/` to GitHub.
2. Create Streamlit Cloud app.
3. App entrypoint: `app.py`.
4. Python version is pinned in `runtime.txt`.
5. Dependencies are installed from lightweight `requirements.txt`.
6. Add secrets from `.streamlit/secrets.example.toml`.
7. Set Google OAuth redirect URI to the deployed app URL.
8. Redeploy.

Vietnamese quickstart:

```text
DEPLOYMENT_QUICKSTART_VI.md
```

## Render

This repository includes:

```text
render.yaml
```

Steps:

1. Create a Render Blueprint from the GitHub repository.
2. Set environment variables in Render dashboard.
3. Keep `AUTH_ENABLED=false` for public demo or configure OAuth variables for protected access.
4. Render will run:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

## OAuth Notes

- The app uses Google OAuth by default when enabled.
- GitHub OAuth is optional.
- Roles are mapped by `USER_ROLE_MAP`.
- Unknown authenticated users receive `DEFAULT_AUTH_ROLE`.

Roles:

- `viewer`: view dashboard and public exports.
- `analyst`: upload CV/datasets, run automated analytics, export reports.
- `admin`: future management functions.

## Production Checklist

- [ ] Rotate any secrets previously exposed outside secure secret storage.
- [ ] Configure OAuth redirect URI.
- [ ] Set `AUTH_ENABLED=true` for protected app.
- [ ] Add `USER_ROLE_MAP`.
- [ ] Test login/logout.
- [ ] Test viewer cannot access upload pages.
- [ ] Test analyst can use Resume Analyzer and AI Agent.
- [ ] Test CSV exports.
- [ ] Confirm app URL is shareable.
