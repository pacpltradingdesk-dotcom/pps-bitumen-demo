"""
Cloud-resilient secrets helper.

Streamlit Cloud's filesystem resets on every push / cold start, so any
credentials saved to local JSON files are wiped. This module provides a
single read priority chain so that engines/UI can be cloud-safe with
minimal code change:

  1. st.secrets[section]      — Cloud-persistent, set via app dashboard
  2. os.environ[<UPPER_KEY>]  — for self-hosted deployments using env vars
  3. st.session_state[_secrets:section] — survives within current session
  4. local file fallback (caller-provided)

Plus a small Streamlit UI helper that renders a uniform "how to make
this permanent on Cloud" expander on any setup page.
"""
from __future__ import annotations

import os
from typing import Any, Mapping


def _from_secrets(section: str) -> Mapping[str, Any] | None:
    """Try st.secrets[section]. Returns None on any failure."""
    try:
        import streamlit as st
        if not hasattr(st, "secrets"):
            return None
        sec = st.secrets.get(section)
        if sec and isinstance(sec, Mapping):
            # Convert Streamlit's AttrDict to plain dict for JSON-friendliness
            return dict(sec)
    except Exception:
        pass
    return None


def _from_env(env_keys: Mapping[str, str]) -> dict:
    """env_keys = {field_name: ENV_VAR_NAME}. Returns dict of fields whose env is set."""
    out: dict = {}
    for field, env in env_keys.items():
        val = os.environ.get(env, "").strip()
        if val:
            out[field] = val
    return out


def _from_session(section: str) -> dict | None:
    try:
        import streamlit as st
        return st.session_state.get(f"_secrets:{section}")
    except Exception:
        return None


def get_secret_block(section: str,
                     env_keys: Mapping[str, str] | None = None) -> dict:
    """Return the merged secret block for `section`.

    Order (later keys override earlier):
      file/session < env vars < st.secrets

    Returns {} if nothing found anywhere; caller should treat as "not configured".
    """
    out: dict = {}
    sess = _from_session(section)
    if sess:
        out.update({k: v for k, v in sess.items() if not k.startswith("_")})
    if env_keys:
        out.update(_from_env(env_keys))
    secrets = _from_secrets(section)
    if secrets:
        out.update({k: v for k, v in secrets.items() if not k.startswith("_")})
    return out


def remember_in_session(section: str, data: Mapping[str, Any]) -> None:
    """Cache a credential dict in st.session_state so it survives reruns
    within the current session even if the disk file is wiped."""
    try:
        import streamlit as st
        st.session_state[f"_secrets:{section}"] = dict(data)
    except Exception:
        pass


def secret_source_label(section: str,
                        env_keys: Mapping[str, str] | None = None,
                        file_present: bool = False) -> str:
    """Return a one-line user-facing label of where the current creds came from.

    Highest source wins:
      st.secrets   → "loaded from Streamlit Cloud secrets ✅"
      env          → "loaded from environment variables"
      session      → "in session memory only — will reset on cold start"
      file         → "loaded from local file — may reset on cloud push"
      none         → "not configured"
    """
    if _from_secrets(section):
        return "✅ loaded from Streamlit Cloud secrets — survives every restart"
    if env_keys and _from_env(env_keys):
        return "✅ loaded from environment variables"
    if _from_session(section):
        return "ℹ️ in session memory only — will reset on next cold start"
    if file_present:
        return "ℹ️ loaded from local file — **resets on every cloud push**"
    return "⚠️ not configured"


def render_cloud_secrets_hint(section: str,
                              fields: list[str],
                              title: str | None = None) -> None:
    """Render a uniform expander explaining how to persist credentials on
    Streamlit Cloud. Drop this on every setup/credentials page so users
    don't have to re-enter creds after every push.

    fields = list of field names that should appear in the TOML block.
    """
    try:
        import streamlit as st
    except Exception:
        return

    title = title or f"⚠️ Why credentials disappear on Cloud (and how to fix permanently — {section})"
    with st.expander(title):
        toml_lines = [f"[{section}]"]
        for f in fields:
            toml_lines.append(f'{f} = "YOUR_{f.upper()}"')
        toml = "\n".join(toml_lines)
        st.markdown(
            "**Problem:** Streamlit Cloud's filesystem resets on every code push or "
            "container restart, so any credentials saved to disk vanish. You then "
            "have to re-enter them every time.\n\n"
            "**Permanent fix — paste into Cloud Secrets (one-time, survives forever):**\n\n"
            "1. Open your Streamlit Cloud app dashboard\n"
            "2. Click **Settings → Secrets**\n"
            "3. Paste this TOML block (replace placeholders with your real values):\n"
        )
        st.code(toml, language="toml")
        st.markdown(
            "4. Save. Reload the app. The form below will then say "
            "*\"loaded from Streamlit Cloud secrets\"* and the values will "
            "survive every restart.\n\n"
            "You can still keep using the form below — it works for the current "
            "session either way."
        )
