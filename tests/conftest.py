"""Force offline mock mode during pytest (avoids Databricks/Gemini network calls)."""

import os

os.environ["USE_DATABRICKS"] = "false"
os.environ["USE_MOCK_AI"] = "true"
