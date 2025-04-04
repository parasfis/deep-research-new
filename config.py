"""Configuration settings for the Deep Research Assistant."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Ollama API settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# Research settings
MAX_PARALLEL_SEARCHES = int(os.getenv("MAX_PARALLEL_SEARCHES", 5))
MAX_SOURCES_PER_TOPIC = int(os.getenv("MAX_SOURCES_PER_TOPIC", 10))
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", 30))  # seconds

# Search engines configuration
SEARCH_ENGINES = [
    "duckduckgo",
    "google",
    "searx"
]

# PDF generation settings
PDF_AUTHOR = os.getenv("PDF_AUTHOR", "Deep Research Assistant")
PDF_TITLE_PREFIX = os.getenv("PDF_TITLE_PREFIX", "Research Report: ")
PDF_OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "reports")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "deep_research.log")

# User interface settings
DEFAULT_PROMPT = """Please provide a research topic and any specific context or requirements:"""