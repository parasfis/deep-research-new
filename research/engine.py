"""Research engine for Deep Research Assistant.

This module provides the core research functionality, coordinating between
the Ollama client and web search components.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

from research.ollama_client import OllamaClient
from research.web_search import WebSearcher
import config

logger = logging.getLogger(__name__)


class ResearchEngine:
    """Core research engine that coordinates the research process."""

    def __init__(self):
        """Initialize the research engine."""
        self.ollama_client = OllamaClient()
        self.web_searcher = WebSearcher()
        self.current_research = None

    def start_research(self, topic: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Start a new research project.

        Args:
            topic: The research topic.
            context: Additional context for the research.

        Returns:
            Dictionary containing the research plan.
        """
        logger.info(f"Starting research on topic: {topic}")
        
        # Generate research queries using Ollama
        research_plan = self.ollama_client.research_query(topic, context)
        
        # Store the current research
        self.current_research = {
            "topic": topic,
            "context": context,
            "plan": research_plan,
            "start_time": time.time(),
            "status": "in_progress",
            "results": None
        }
        
        return research_plan

    def execute_research(self, topic: str, context: Optional[str] = None, 
                        max_sources: int = None) -> Dict[str, Any]:
        """Execute a complete research process.

        Args:
            topic: The research topic.
            context: Additional context for the research.
            max_sources: Maximum number of sources to include.

        Returns:
            Dictionary containing the research results.
        """
        # Start the research and get the plan
        research_plan = self.start_research(topic, context)
        
        # Extract search queries from the plan
        search_queries = research_plan.get("search_queries", [topic])
        
        # Perform parallel web searches
        logger.info(f"Executing {len(search_queries)} parallel searches")
        research_data = self.web_searcher.parallel_research(
            search_queries, 
            max_results_per_query=5,
            max_content_sources=max_sources or config.MAX_SOURCES_PER_TOPIC
        )
        
        # Analyze content with Ollama
        analyzed_sources = self._analyze_sources(research_data["content_sources"], topic)
        
        # Generate the final report
        report = self.ollama_client.generate_report(
            topic, 
            analyzed_sources, 
            context
        )
        
        # Update the current research
        self.current_research["results"] = {
            "raw_data": research_data,
            "analyzed_sources": analyzed_sources,
            "report": report
        }
        self.current_research["status"] = "completed"
        self.current_research["end_time"] = time.time()
        
        return self.current_research

    def _analyze_sources(self, sources: List[Dict[str, Any]], topic: str) -> List[Dict[str, Any]]:
        """Analyze sources using Ollama.

        Args:
            sources: List of content sources.
            topic: The research topic.

        Returns:
            List of analyzed sources with key facts and metadata.
        """
        analyzed_sources = []
        
        with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_SEARCHES) as executor:
            future_to_source = {}
            
            for i, source in enumerate(sources):
                # Skip sources with no content
                if not source.get("content"):
                    continue
                    
                future = executor.submit(
                    self.ollama_client.analyze_content,
                    source["content"],
                    topic
                )
                future_to_source[future] = source
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    analysis = future.result()
                    
                    # Only include sources with sufficient relevance
                    relevance = analysis.get("relevance_score", 0)
                    if relevance >= 0.3:  # Threshold for inclusion
                        analyzed_source = {
                            "url": source["url"],
                            "title": source["title"],
                            "relevance": relevance,
                            "key_facts": analysis.get("key_facts", []),
                            "biases": analysis.get("biases", []),
                            "limitations": analysis.get("limitations", [])
                        }
                        analyzed_sources.append(analyzed_source)
                        logger.info(f"Analyzed source: {source['url']} (relevance: {relevance})")
                    else:
                        logger.info(f"Skipping low-relevance source: {source['url']} (relevance: {relevance})")
                except Exception as e:
                    logger.error(f"Error analyzing source {source['url']}: {e}")
        
        # Sort by relevance
        analyzed_sources.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        return analyzed_sources

    def get_current_research(self) -> Optional[Dict[str, Any]]:
        """Get the current research project.

        Returns:
            Dictionary containing the current research project, or None if no research is in progress.
        """
        return self.current_research

    def get_research_status(self) -> Dict[str, Any]:
        """Get the status of the current research project.

        Returns:
            Dictionary containing the status of the current research project.
        """
        if not self.current_research:
            return {"status": "no_research"}
            
        return {
            "topic": self.current_research["topic"],
            "status": self.current_research["status"],
            "start_time": self.current_research["start_time"],
            "end_time": self.current_research.get("end_time"),
            "duration": time.time() - self.current_research["start_time"]
        }