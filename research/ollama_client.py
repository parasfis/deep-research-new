\"""Ollama API client for Deep Research Assistant.

This module provides integration with Ollama API for LLM capabilities.
"""

import json
import logging
import requests
from typing import Dict, Any, Optional, List, Union

import config

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, host: str = None, model: str = None):
        """Initialize the Ollama client.

        Args:
            host: Ollama API host URL. Defaults to config.OLLAMA_HOST.
            model: Ollama model to use. Defaults to config.OLLAMA_MODEL.
        """
        self.host = host or config.OLLAMA_HOST
        self.model = model or config.OLLAMA_MODEL
        self.api_base = f"{self.host}/api"
        
    def is_available(self) -> bool:
        """Check if Ollama API is available.

        Returns:
            bool: True if Ollama API is available, False otherwise.
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Ollama API: {e}")
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                 temperature: float = 0.7, max_tokens: int = 2000) -> Dict[str, Any]:
        """Generate a response from Ollama.

        Args:
            prompt: The user prompt to send to Ollama.
            system_prompt: Optional system prompt to set context.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum number of tokens to generate.

        Returns:
            Dict containing the response from Ollama.
        """
        url = f"{self.api_base}/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error generating response from Ollama: {e}")
            return {"error": str(e)}

    def research_query(self, topic: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate a research query for a given topic.

        Args:
            topic: The research topic.
            context: Additional context for the research.

        Returns:
            Dict containing research queries and subtopics.
        """
        system_prompt = (
            "You are a research assistant helping to formulate effective search queries. "
            "Break down the topic into 3-5 specific search queries that would yield "
            "comprehensive information. Also identify 2-4 subtopics for deeper research."
        )
        
        prompt = f"Research Topic: {topic}\n"
        if context:
            prompt += f"Additional Context: {context}\n"
        prompt += "\nPlease provide search queries and subtopics in JSON format."
        
        response = self.generate(prompt, system_prompt=system_prompt, temperature=0.3)
        
        try:
            # Extract JSON from the response
            content = response.get("response", "{}")
            # Find JSON content (might be embedded in text)
            json_start = content.find('{')
            json_end = content.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end+1]
                result = json.loads(json_str)
            else:
                # If no JSON found, create a basic structure
                result = {
                    "search_queries": [topic],
                    "subtopics": ["General information"]
                }
                
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse research query response: {e}")
            # Fallback to basic structure
            return {
                "search_queries": [topic],
                "subtopics": ["General information"]
            }

    def analyze_content(self, content: str, topic: str) -> Dict[str, Any]:
        """Analyze content for relevance and extract key information.

        Args:
            content: The content to analyze.
            topic: The research topic.

        Returns:
            Dict containing analysis results.
        """
        system_prompt = (
            "You are a research assistant analyzing web content. "
            "Evaluate the relevance of the content to the topic, extract key facts, "
            "and identify any biases or limitations in the source."
        )
        
        prompt = f"Research Topic: {topic}\n\nContent to Analyze:\n{content[:5000]}...\n\n"
        prompt += "Please provide analysis in JSON format with keys: relevance_score, key_facts, biases, limitations."
        
        response = self.generate(prompt, system_prompt=system_prompt, temperature=0.2)
        
        try:
            # Extract JSON from the response
            content = response.get("response", "{}")
            # Find JSON content (might be embedded in text)
            json_start = content.find('{')
            json_end = content.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end+1]
                return json.loads(json_str)
            else:
                # If no JSON found, create a basic structure
                return {
                    "relevance_score": 0.5,
                    "key_facts": ["Content could not be properly analyzed"],
                    "biases": [],
                    "limitations": ["Analysis failed"]
                }
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse content analysis response: {e}")
            return {
                "relevance_score": 0,
                "key_facts": [],
                "biases": [],
                "limitations": ["Analysis failed due to error"]
            }

    def generate_report(self, research_data: Dict[str, Any], topic: str, 
                        context: Optional[str] = None) -> str:
        """Generate a comprehensive research report.

        Args:
            research_data: Collected research data.
            topic: The research topic.
            context: Additional context for the research.

        Returns:
            String containing the formatted research report.
        """
        system_prompt = (
            "You are a research assistant generating a comprehensive report. "
            "Synthesize the provided research data into a well-structured report "
            "with an executive summary, methodology, findings, analysis, and conclusion. "
            "Use markdown formatting for headings and structure."
        )
        
        # Prepare research data summary
        sources_summary = ""
        for i, source in enumerate(research_data.get("sources", [])):
            facts = "\n- ".join(source.get("key_facts", ["No key facts extracted"]))
            sources_summary += f"\nSource {i+1}: {source.get('url', 'Unknown')}\nKey Facts:\n- {facts}\n"
        
        prompt = f"Research Topic: {topic}\n"
        if context:
            prompt += f"Additional Context: {context}\n"
        prompt += f"\nResearch Data Summary:\n{sources_summary}\n\n"
        prompt += "Please generate a comprehensive research report in markdown format."
        
        response = self.generate(
            prompt, 
            system_prompt=system_prompt, 
            temperature=0.4,
            max_tokens=4000
        )
        
        return response.get("response", "Error generating report")