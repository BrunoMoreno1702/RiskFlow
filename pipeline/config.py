from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://riskflow:riskflow@localhost:5432/riskflow")
SOURCE_API_URL = os.getenv("SOURCE_API_URL", "http://localhost:8001")
SOURCE_CUSTOMERS = int(os.getenv("SOURCE_CUSTOMERS", "500"))
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", str(ROOT_DIR / "ml" / "artifacts")))
SQL_DIR = ROOT_DIR / "sql"
