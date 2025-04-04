"""Research package for Deep Research Assistant.

This package contains the core research functionality, including:
- Research engine: Coordinates the research process
- Ollama client: Interfaces with the Ollama API for AI-powered analysis
- Web search: Performs web searches to gather research data
"""

from research.engine import ResearchEngine

__all__ = ['ResearchEngine']