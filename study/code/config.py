# config.py
import os

# API Configuration
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"  # or "deepseek-reasoner" if available

# Analysis Parameters
USE_LLM_THRESHOLD = 0.3  # Use LLM for 30% of quotes
CONTEXT_WINDOW_SIZE = 2  # Quotes before/after to consider as context
BATCH_SIZE = 5  # Number of quotes to process in batch
RATE_LIMIT_DELAY = 1  # Seconds between API calls

# File Paths - Will be set dynamically
JSON_FILES_PATH = None
OUTPUT_DIR = None
RESULTS_DIR = None
BACKUP_DIR = None
