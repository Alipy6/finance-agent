import os
from pathlib import Path
from dotenv import load_dotenv

# Find root directory of finance-agent project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from local.env or .env in BASE_DIR
env_file = BASE_DIR / "local.env"
if not env_file.exists():
    env_file = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_file)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BRSAPI_KEY = os.getenv("BRSAPI_KEY", "")
OMNIROUTE_BASE_URL = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1").rstrip("/")
OMNIROUTE_MODEL = os.getenv("OMNIROUTE_MODEL", "auto")
HISTORY_FILE_PATH = str(BASE_DIR / os.getenv("HISTORY_FILE_PATH", "price_history.json"))
