"""Role-based access control for dashboard pages and actions."""
from __future__ import annotations

import streamlit as st


ROLE_LEVELS = {
    "viewer": 1,
    "analyst": 2,
    "admin": 3,
}

ROLE_PERMISSIONS = {
    "viewer": {
        "view_dashboard",
        "download_public_exports",
    },
    "analyst": {
        "view_dashboard",
        "download_public_exports",
        "upload_resume",
        "upload_dataset",
        "run_analytics",
        "export_reports",
    },
    "admin": {
        "view_dashboard",
        "download_public_exports",
        "upload_resume",
        "upload_dataset",
        "run_analytics",
        "export_reports",
        "manage_users",
        "manage_settings",
    },
}


def normalize_role(role: str | None) -> str:
    role = str(role or "viewer").lower()
    return role if role in ROLE_LEVELS else "viewer"


def has_role(user_role: str, required_role: str) -> bool:
    return ROLE_LEVELS[normalize_role(user_role)] >= ROLE_LEVELS[normalize_role(required_role)]


def has_permission(user_role: str, permission: str) -> bool:
    role = normalize_role(user_role)
    permissions = set()
    for candidate, level in ROLE_LEVELS.items():
        if level <= ROLE_LEVELS[role]:
            permissions.update(ROLE_PERMISSIONS.get(candidate, set()))
    return permission in permissions


def require_role(required_role: str):
    user = st.session_state.get("auth_user", {})
    role = normalize_role(user.get("role"))
    if has_role(role, required_role):
        return user

    st.error(f"Bạn cần quyền `{required_role}` để sử dụng chức năng này. Quyền hiện tại: `{role}`.")
    st.stop()
