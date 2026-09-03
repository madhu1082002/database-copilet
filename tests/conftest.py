"""Force offline mock mode during pytest (avoids Databricks/Gemini network calls)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

os.environ["USE_DATABRICKS"] = "false"
os.environ["USE_MOCK_AI"] = "true"
os.environ["GEMINI_TIMEOUT_SECONDS"] = "8"
os.environ["CACHE_TTL_SECONDS"] = "300"
