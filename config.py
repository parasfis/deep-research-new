"""Configuration settings for the Deep Research Assistant."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Ollama API settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "llama3.2"
OLLAMA_TIMEOUT = 240  # Increased from 30 to 60 seconds
OLLAMA_ENDPOINT = "http://localhost:11434"

# Search engine API keys
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SEARX_INSTANCE = os.getenv("SEARX_INSTANCE", "https://searx.thegpm.org")

# Research settings
MAX_PARALLEL_SEARCHES = int(os.getenv("MAX_PARALLEL_SEARCHES", 4))
MAX_SOURCES_PER_TOPIC = int(os.getenv("MAX_SOURCES_PER_TOPIC", 10))
SEARCH_TIMEOUT = 30

# Search engines configuration
SEARCH_ENGINES = [
    "tavily",  # Primary search engine
    "duckduckgo",  # Fallback
    "google",  # Fallback
    "searx"  # Fallback
]

# PDF generation settings
PDF_AUTHOR = "Deep Research Assistant"
PDF_TITLE_PREFIX = "Deep Research Report: "
PDF_OUTPUT_DIR = "reports"

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "deep_research.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# User interface settings
DEFAULT_PROMPT = """Please provide a research topic and any specific context or requirements:"""

# New configuration value
MAX_RESULTS_PER_ENGINE = 10