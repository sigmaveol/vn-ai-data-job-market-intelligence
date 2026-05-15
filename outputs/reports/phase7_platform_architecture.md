# Phase 7 Platform Architecture

## Goal

Phase 7 turns the local analytics dashboard into a lightweight production-style analytics platform:

```text
EDA Dashboard -> Production Analytics Platform
```

The implementation remains demo-friendly and avoids enterprise over-engineering.

## Implemented Components

### Production Configuration

```text
.env.example
.streamlit/secrets.example.toml
src/platform/settings.py
src/platform/logging_config.py
render.yaml
DEPLOYMENT.md
```

Configuration is environment-driven. Secrets are not hardcoded.

### OAuth Authentication

```text
src/auth/oauth.py
```

Supported:

- Google OAuth
- Optional GitHub OAuth
- Login/logout flow
- OAuth disabled mode for local demos

### RBAC

```text
src/auth/rbac.py
```

Roles:

- `viewer`
- `analyst`
- `admin`

Current route protection:

- All dashboard pages pass through auth via sidebar.
- Resume Analyzer requires `analyst`.
- AI Agent Automation requires `analyst`.

### AI Agent Automation

```text
src/agent/analytics_pipeline.py
src/agent/orchestrator.py
pages/8_AI_Agent.py
```

Workflow:

```text
Dataset Upload
  -> Schema Detection
  -> Cleaning Pipeline
  -> EDA Summary
  -> KPI Suggestions
  -> Chart Suggestions
  -> Insight Generation
  -> Dashboard Layout Plan
  -> Report Outline
  -> Slide Outline
```

The current agent is deterministic and explainable. It can later be connected to an LLM provider.

### Export & Sharing

Existing:

- CSV exports across dashboard pages
- Optional PNG chart exports
- Resume report exports
- AI Agent cleaned data, chart plan, and insight exports

## Deployment Targets

Recommended:

- Streamlit Cloud
- Render

Render config is included in `render.yaml`.

## Important Limitation

This coding environment cannot create a public deployment URL because it requires an external hosting account and OAuth provider configuration.

To complete production validation:

1. Deploy to Streamlit Cloud or Render.
2. Configure OAuth client IDs/secrets.
3. Set callback URL to deployed app URL.
4. Test login/logout.
5. Test RBAC roles.

## Security Notes

- Do not commit `.env`.
- Store real secrets only in Streamlit Cloud/Render secrets.
- Rotate secrets if they were pasted into chats, logs, screenshots, or committed history.
