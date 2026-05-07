# auth.py — minimal Streamlit login, no external deps
from __future__ import annotations
import os, hashlib
from pathlib import Path
import streamlit as st

def _load_local_env() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()

_load_local_env()

# Configure these via env vars when packaging or deploying.
# We fail closed if credentials are not explicitly provided.
DEFAULT_USER = os.getenv("HELIX_USER", "")
DEFAULT_PASS = os.getenv("HELIX_PASS", "")
SALT        = os.getenv("HELIX_SALT", "pepper")

def _hash(pw: str) -> str:
    return hashlib.sha256((SALT + pw).encode("utf-8")).hexdigest()

_STORED_HASH = _hash(DEFAULT_PASS)

def login() -> tuple[bool, str]:
    """Simple sidebar login. Returns (is_authenticated, username)."""
    st.sidebar.markdown("### Sign in")
    if not DEFAULT_USER or not DEFAULT_PASS:
        st.sidebar.error("Authentication is not configured. Set HELIX_USER and HELIX_PASS.")
        return False, ""
    # Already authed?
    if st.session_state.get("auth_ok"):
        user = st.session_state.get("auth_user", DEFAULT_USER)
        if st.sidebar.button("Sign out", use_container_width=True, key="auth_logout"):
            for k in ("auth_ok", "auth_user"):
                st.session_state.pop(k, None)
            st.rerun()
        st.sidebar.success(f"Signed in as {user}")
        return True, user

    user = st.sidebar.text_input("Username", key="auth_user_input")
    pw   = st.sidebar.text_input("Password", type="password", key="auth_pw_input")
    if st.sidebar.button("Sign in", use_container_width=True, key="auth_login"):
        if user == DEFAULT_USER and _hash(pw) == _STORED_HASH:
            st.session_state["auth_ok"] = True
            st.session_state["auth_user"] = user
            st.sidebar.success(f"Welcome, {user}!")
            return True, user
        st.sidebar.error("Invalid credentials.")
    return False, ""
