import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "dataops.db"

# This project uses Gemini 2.5 Flash only (per pSIDDHI proposal)
GEMINI_MODEL = "gemini-2.5-flash"


def _load_api_keys() -> list[str]:
    keys: list[str] = []

    google_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if google_key:
        keys.append(google_key)

    keys_raw = os.environ.get("GEMINI_API_KEYS", "")
    if keys_raw:
        for key in keys_raw.split(","):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key and gemini_key not in keys:
        keys.append(gemini_key)

    return keys


GEMINI_API_KEYS = _load_api_keys()
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
USE_MOCK_AI = os.environ.get("USE_MOCK_AI", "true").lower() == "true" or not GEMINI_API_KEYS

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "").strip()
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "").strip()
DATABRICKS_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
DATABRICKS_CATALOG = os.environ.get("DATABRICKS_CATALOG", "workspace").strip()
DATABRICKS_SCHEMA = os.environ.get("DATABRICKS_SCHEMA", "dataops_copilot").strip()
USE_DATABRICKS = os.environ.get("USE_DATABRICKS", "false").lower() == "true"
