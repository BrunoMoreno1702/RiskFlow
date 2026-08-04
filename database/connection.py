import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")


def get_connection():
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("SQL_SERVER", "localhost")
    database = os.getenv("SQL_DATABASE")

    trusted_connection = os.getenv("SQL_TRUSTED_CONNECTION", "yes").lower()
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")

    encrypt = os.getenv("SQL_ENCRYPT", "yes")
    trust_server_certificate = os.getenv("SQL_TRUST_SERVER_CERTIFICATE", "yes")

    if not database:
        raise ValueError("A variavel SQL_DATABASE nao foi configurada no arquivo .env")

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
