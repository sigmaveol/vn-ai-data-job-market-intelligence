"""Production settings loaded from environment variables."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _secret(name: str, default: Any = "") -> Any:
    """Read config from env first, then Streamlit secrets when available."""
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = _secret(name, None)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _json_env(name: str, default):
    value = _secret(name, None)
    if not value:
        return default
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


@dataclass(frozen=True)
class AppSettings:
    app_env: str = field(default_factory=lambda: _secret("APP_ENV", "development"))
    app_base_url: str = field(default_factory=lambda: _secret("APP_BASE_URL", "http://localhost:8501"))
    auth_enabled: bool = field(default_factory=lambda: _bool_env("AUTH_ENABLED", False))
    log_level: str = field(default_factory=lambda: _secret("LOG_LEVEL", "INFO"))

    google_client_id: str = field(default_factory=lambda: _secret("GOOGLE_OAUTH_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: _secret("GOOGLE_OAUTH_CLIENT_SECRET", ""))
    google_redirect_uri: str = field(default_factory=lambda: _secret("GOOGLE_OAUTH_REDIRECT_URI", _secret("APP_BASE_URL", "http://localhost:8501")))

    github_client_id: str = field(default_factory=lambda: _secret("GITHUB_OAUTH_CLIENT_ID", ""))
    github_client_secret: str = field(default_factory=lambda: _secret("GITHUB_OAUTH_CLIENT_SECRET", ""))
    github_redirect_uri: str = field(default_factory=lambda: _secret("GITHUB_OAUTH_REDIRECT_URI", _secret("APP_BASE_URL", "http://localhost:8501")))

    user_role_map: dict = field(default_factory=lambda: _json_env("USER_ROLE_MAP", {}))
    default_auth_role: str = field(default_factory=lambda: _secret("DEFAULT_AUTH_ROLE", "viewer"))

    @property
    def google_oauth_ready(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def github_oauth_ready(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)


def get_settings() -> AppSettings:
    return AppSettings()
