import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

try:
    import streamlit as st
    STREAMLIT_ENV = st.secrets
except (ImportError, AttributeError, RuntimeError):
    STREAMLIT_ENV = None


BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")


def _get_env(key: str, default: str = None) -> str:
    """Lê variáveis de ambiente do Streamlit Secrets (nuvem) ou .env (local)"""
    if STREAMLIT_ENV:
        try:
            return STREAMLIT_ENV[key]
        except (KeyError, AttributeError):
            pass
    return os.getenv(key, default)


def get_connection():
    driver = _get_env("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = _get_env("SQL_SERVER", "localhost")
    database = _get_env("SQL_DATABASE")

    trusted_connection = _get_env("SQL_TRUSTED_CONNECTION", "yes").lower()
    username = _get_env("SQL_USERNAME")
    password = _get_env("SQL_PASSWORD")

    encrypt = _get_env("SQL_ENCRYPT", "yes")
    trust_server_certificate = _get_env("SQL_TRUST_SERVER_CERTIFICATE", "yes")

    if not database:
        raise ValueError(
            "SQL_DATABASE não foi configurado. "
            "Configure no arquivo .env (local) ou em 'Secrets' (Streamlit Cloud)"
        )

    connection_parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust_server_certificate}",
    ]

    # Em ambiente local, prioriza autenticacao integrada do Windows.
    if trusted_connection == "yes":
        connection_parts.append("Trusted_Connection=yes")
    else:
        if not username or not password:
            raise ValueError(
                "SQL_USERNAME e SQL_PASSWORD precisam ser informados quando SQL_TRUSTED_CONNECTION=no"
            )

        connection_parts.append(f"UID={username}")
        connection_parts.append(f"PWD={password}")

    return pyodbc.connect(";".join(connection_parts))
