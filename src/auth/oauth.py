"""OAuth login helpers for Streamlit.

Auth is disabled by default for local demos. In production set
`AUTH_ENABLED=true` and provide OAuth client credentials via environment
variables or Streamlit secrets.
"""
from __future__ import annotations

import secrets
import urllib.parse

import requests
import streamlit as st

from src.platform import get_settings
from .rbac import normalize_role


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _query_params() -> dict:
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()


def _clear_query_params() -> None:
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()


def _role_for_email(email: str) -> str:
    settings = get_settings()
    return normalize_role(settings.user_role_map.get(email, settings.default_auth_role))


def _dev_user() -> dict:
    return {
        "email": "local-demo@example.com",
        "name": "Local Demo User",
        "provider": "local",
        "role": "admin",
    }


def get_current_user() -> dict | None:
    settings = get_settings()
    if not settings.auth_enabled:
        st.session_state.setdefault("auth_user", _dev_user())
        return st.session_state["auth_user"]
    return st.session_state.get("auth_user")


def require_login() -> dict:
    settings = get_settings()
    if not settings.auth_enabled:
        return get_current_user()

    if st.session_state.get("auth_user"):
        return st.session_state["auth_user"]

    params = _query_params()
    code = params.get("code")
    state = params.get("state")
    provider = params.get("provider", st.session_state.get("oauth_provider", "google"))
    if isinstance(code, list):
        code = code[0]
    if isinstance(state, list):
        state = state[0]
    if isinstance(provider, list):
        provider = provider[0]

    if code:
        _handle_callback(provider, code, state)
        _clear_query_params()
        st.rerun()

    _render_login(settings)
    st.stop()


def logout_button() -> None:
    settings = get_settings()
    user = get_current_user()
    if not user:
        return
    with st.sidebar:
        st.caption(f"Đăng nhập: {user.get('email')} · {user.get('role')}")
        if settings.auth_enabled and st.button("Đăng xuất", use_container_width=True):
            st.session_state.pop("auth_user", None)
            st.session_state.pop("oauth_state", None)
            st.rerun()


def _render_login(settings) -> None:
    st.title("Đăng nhập dashboard")
    st.caption("Dashboard đang bật chế độ OAuth. Vui lòng đăng nhập để tiếp tục.")

    if settings.google_oauth_ready:
        st.link_button("Đăng nhập bằng Google", _auth_url("google"), use_container_width=True)
    else:
        st.warning("Google OAuth chưa được cấu hình. Thiết lập GOOGLE_OAUTH_CLIENT_ID và GOOGLE_OAUTH_CLIENT_SECRET.")

    if settings.github_oauth_ready:
        st.link_button("Đăng nhập bằng GitHub", _auth_url("github"), use_container_width=True)


def _auth_url(provider: str) -> str:
    settings = get_settings()
    state = secrets.token_urlsafe(24)
    st.session_state["oauth_state"] = state
    st.session_state["oauth_provider"] = provider

    if provider == "github":
        query = {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"{GITHUB_AUTH_URL}?{urllib.parse.urlencode(query)}"

    query = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(query)}"


def _handle_callback(provider: str, code: str, state: str | None) -> None:
    expected_state = st.session_state.get("oauth_state")
    if expected_state and state != expected_state:
        st.error("OAuth state không hợp lệ. Vui lòng đăng nhập lại.")
        st.stop()

    if provider == "github":
        user = _exchange_github(code)
    else:
        user = _exchange_google(code)

    user["role"] = _role_for_email(user.get("email", ""))
    st.session_state["auth_user"] = user


def _exchange_google(code: str) -> dict:
    settings = get_settings()
    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    token_response.raise_for_status()
    access_token = token_response.json()["access_token"]
    user_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    user_response.raise_for_status()
    data = user_response.json()
    return {
        "email": data.get("email", ""),
        "name": data.get("name", data.get("email", "")),
        "provider": "google",
    }


def _exchange_github(code: str) -> dict:
    settings = get_settings()
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "redirect_uri": settings.github_redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    token_response.raise_for_status()
    access_token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    user_response = requests.get(GITHUB_USERINFO_URL, headers=headers, timeout=15)
    user_response.raise_for_status()
    user_data = user_response.json()
    email = user_data.get("email") or _primary_github_email(headers)
    return {
        "email": email or "",
        "name": user_data.get("name") or user_data.get("login") or email or "",
        "provider": "github",
    }


def _primary_github_email(headers: dict) -> str | None:
    response = requests.get(GITHUB_EMAILS_URL, headers=headers, timeout=15)
    if not response.ok:
        return None
    for item in response.json():
        if item.get("primary") and item.get("verified"):
            return item.get("email")
    return None
