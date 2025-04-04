#!/usr/bin/env python3
"""
Deep Research Assistant - Main Entry Point

This script serves as the main entry point for the Deep Research Assistant application.
It initializes the necessary components and starts either the CLI or web interface.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
import config
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Ensure the reports directory exists
reports_dir = Path(config.PDF_OUTPUT_DIR)
reports_dir.mkdir(exist_ok=True)

# Import the research engine and UI interfaces
from research.engine import ResearchEngine
from ui.cli import ResearchCLI
from ui.web.app import start_web_server
from ui.web_interface import ResearchWeb


def main():
    """Main entry point for the application."""
    try:
        # Parse command-line arguments
        parser = argparse.ArgumentParser(description="Deep Research Assistant")
        parser.add_argument(
            "--web", 
            action="store_true", 
            help="Start the web interface instead of the CLI"
        )
        parser.add_argument(
            "--port", 
            type=int, 
            default=5000, 
            help="Port for the web interface (default: 5000)"
        )
        parser.add_argument(
            "--host", 
            type=str, 
            default="127.0.0.1", 
            help="Host for the web interface (default: 127.0.0.1)"
        )
        parser.add_argument(
            "--debug", 
            action="store_true", 
            help="Run the web interface in debug mode"
        )
        args = parser.parse_args()
        
        # Initialize the research engine
        logger.info("Initializing Research Engine")
        research_engine = ResearchEngine()
        
        if args.web:
            # Start the web interface
            logger.info(f"Starting web interface on {args.host}:{args.port}")
            web = ResearchWeb(research_engine)
            web.start(host=args.host, port=args.port, debug=args.debug)
        else:
            # Start the CLI
            logger.info("Starting CLI interface")
            cli = ResearchCLI(research_engine)
            cli.start()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()