
import os
import streamlit as st


def get_groq_api_key():
    """Read the Groq API key from environment variables or Streamlit secrets."""
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            api_key = ""

    return api_key


def get_groq_model():
    """Read the configured model name or use the default."""
    try:
        return st.secrets.get(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        )
    except Exception:
        return os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        )
