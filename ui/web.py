\"""Web interface for Deep Research Assistant.

This module provides a web interface for interacting with the research engine.
"""

import os
import logging
from pathlib import Path

from research.engine import ResearchEngine
from ui.web.app import start_web_server
import config

logger = logging.getLogger(__name__)


class ResearchWeb:
    """Web interface for the Deep Research Assistant."""

    def __init__(self, research_engine: ResearchEngine):
        """Initialize the web interface.

        Args:
            research_engine: The research engine to use.
        """
        self.research_engine = research_engine
        
        # Ensure the reports directory exists
        reports_dir = Path(config.PDF_OUTPUT_DIR)
        reports_dir.mkdir(exist_ok=True)
        
        # Ensure the uploads directory exists
        uploads_dir = Path(os.path.join(os.path.dirname(__file__), 'web/uploads'))
        uploads_dir.mkdir(exist_ok=True)

    def start(self, host='0.0.0.0', port=5000, debug=False):
        """Start the web interface.
        
        Args:
            host: Host to bind the server to.
            port: Port to bind the server to.
            debug: Whether to run the server in debug mode.
        """
        logger.info(f"Starting web interface on {host}:{port}")
        start_web_server(host=host, port=port, debug=debug)