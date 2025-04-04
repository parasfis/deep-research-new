"""Ollama API client for Deep Research Assistant.

This module provides functionality for interacting with the Ollama API.
"""

import json
import logging
import requests
import time
from typing import Dict, Any, Optional

import config

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for interacting with the Ollama API."""

    def __init__(self):
        """Initialize the Ollama client."""
        self.endpoint = config.OLLAMA_ENDPOINT
        self.model = config.OLLAMA_MODEL
        self.timeout = config.OLLAMA_TIMEOUT
        self.session = requests.Session()

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate a response from Ollama.

        Args:
            prompt: The prompt to send to Ollama.
            system: Optional system message to set context.

        Returns:
            Generated response text.

        Raises:
            RuntimeError: If the API request fails.
        """
        url = f"{self.endpoint}/api/generate"
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system:
            data["system"] = system
            
        try:
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            try:
                result = response.json()
                return result.get("response", "").strip()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {e}")
                logger.debug(f"Raw response: {response.text}")
                raise RuntimeError("Invalid response from Ollama API")
                
        except requests.Timeout:
            logger.error(f"Request to Ollama API timed out after {self.timeout} seconds")
            raise RuntimeError("Ollama API request timed out")
        except requests.RequestException as e:
            logger.error(f"Error generating response from Ollama: {e}")
            raise RuntimeError(f"Failed to get response from Ollama API: {e}")

    def research_query(self, topic: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate a research query for a topic.

        Args:
            topic: The research topic.
            context: Optional context or requirements.

        Returns:
            Dictionary containing research plan and queries.
        """
        system = """You are a research assistant helping to break down a topic into a research plan.
        Generate a structured research plan with 3-4 key questions to investigate, and 3-4 subtopics to explore.
        Format the response as JSON with 'questions' and 'subtopics' lists."""

        prompt = f"Research topic: {topic}\n"
        if context:
            prompt += f"Context: {context}\n"
        prompt += "Generate a research plan."

        try:
            response = self.generate(prompt, system)
            try:
                return json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse research plan as JSON: {e}")
                logger.debug(f"Raw response: {response}")
                return {
                    "questions": [topic],
                    "subtopics": ["General information"]
                }
        except Exception as e:
            logger.error(f"Failed to generate research query: {e}")
            return {
                "questions": [topic],
                "subtopics": ["General information"]
            }

    def analyze_source(self, content: str, topic: str) -> Dict[str, Any]:
        """Analyze a source's content for relevance to the research topic.

        Args:
            content: The source content to analyze.
            topic: The research topic.

        Returns:
            Dictionary containing relevance score and analysis.
        """
        system = """You are a research assistant analyzing source content.
        Determine the relevance of the content to the research topic on a scale of 0-100.
        Provide a brief analysis of the key points.
        Format the response as JSON with 'relevance' (number) and 'analysis' (string) fields."""

        prompt = f"""Research topic: {topic}

Source content:
{content[:2000]}  # Limit content length to avoid token limits

Analyze the relevance and key points."""

        try:
            response = self.generate(prompt, system)
            try:
                return json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse source analysis as JSON: {e}")
                logger.debug(f"Raw response: {response}")
                return {
                    "relevance": 0,
                    "analysis": "Error analyzing source"
                }
        except Exception as e:
            logger.error(f"Failed to analyze source: {e}")
            return {
                "relevance": 0,
                "analysis": f"Error analyzing source: {e}"
            }

    def generate_report(self, topic: str, sources: list, context: Optional[str] = None) -> str:
        """Generate a research report from analyzed sources.

        Args:
            topic: The research topic.
            sources: List of analyzed sources.
            context: Optional context or requirements.

        Returns:
            Generated report text.
        """
        system = """You are a research assistant generating a comprehensive report.
        Use the provided sources to create a well-structured report on the topic.
        Include relevant information, insights, and cite sources appropriately.
        Format the report in markdown with clear sections and bullet points.
        IMPORTANT: You MUST include all source URLs in a 'References' section at the end of the report."""

        # Format sources to extract key facts and URLs
        sources_text = ""
        source_urls = []
        
        for i, source in enumerate(sources):
            if isinstance(source, dict):
                # Extract key facts from the source
                key_facts = source.get("key_facts", [])
                facts_text = "\n".join([f"- {fact}" for fact in key_facts])
                
                # Get the URL and add to our list
                url = source.get("url", "")
                if url:
                    source_urls.append(url)
                    sources_text += f"Source {i+1} [{url}]:\n{facts_text}\n\n"
                else:
                    sources_text += f"Source {i+1}:\n{facts_text}\n\n"
            else:
                # Handle case where source is not a dictionary
                sources_text += f"Source {i+1}: Unable to process source data\n\n"

        prompt = f"""Research topic: {topic}"""
        if context:
            prompt += f"\nContext: {context}"
        prompt += f"""

Analyzed sources:
{sources_text}

Generate a comprehensive research report in markdown format with:
1. Introduction
2. Key findings
3. Detailed analysis
4. Conclusion
5. References - IMPORTANT: Include ALL source URLs in this section

Source URLs to include in references:
{', '.join(source_urls) if source_urls else 'No sources available'}

Make sure to cite sources properly throughout the report and include ALL source URLs in the References section."""

        max_retries = 2
        retry_delay = 3  # seconds
        
        for attempt in range(max_retries):
            try:
                return self.generate(prompt, system)
            except requests.Timeout:
                logger.error(f"Request to generate report timed out on attempt {attempt+1}")
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying in {retry_delay} seconds")
                    time.sleep(retry_delay)
                else:
                    return "Error: Report generation timed out. Please try again with a narrower topic."
            except Exception as e:
                logger.error(f"Failed to generate report on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying in {retry_delay} seconds")
                    time.sleep(retry_delay)
                else:
                    return f"Error generating report: {e}"
        
        return "Error: Maximum retries exceeded for report generation."

    def analyze_content(self, content: str, topic: str) -> Dict[str, Any]:
        """Analyze content from a source and return a structured analysis.

        Args:
            content: The content to analyze.
            topic: The research topic.

        Returns:
            Dictionary containing relevance score and analysis.
        """
        # Simplify the expected structure to make it easier for the model
        system = """You are a research assistant analyzing source content.
        Analyze the provided content for relevance to the research topic.
        Return a simplified JSON object with just two fields:
        - relevance_score: number between 0 and 1
        - key_facts: list of strings containing 3-5 key facts from the content
        """

        # Shorter prompt to reduce token usage and processing time
        prompt = f"""Research topic: {topic}

Content to analyze (excerpt):
{content[:2000]}

Analyze this content for relevance to the topic and extract key facts.
Your response must be a valid JSON object with only these fields:
{{
  "relevance_score": (number between 0 and 1),
  "key_facts": ["fact 1", "fact 2", "fact 3"]
}}"""

        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.generate(prompt, system)
                try:
                    # First try to parse as-is
                    result = json.loads(response)
                    return result
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from the response
                    # Look for JSON-like patterns
                    import re
                    json_pattern = r'({[^{}]*"relevance_score"[^{}]*"key_facts"[^{}]*})'
                    match = re.search(json_pattern, response)
                    
                    if match:
                        try:
                            return json.loads(match.group(1))
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse matched JSON on attempt {attempt+1}: {e}")
                    
                    # If all parsing fails, return a default structure
                    logger.error(f"Failed to parse content analysis as JSON on attempt {attempt+1}")
                    logger.debug(f"Raw response: {response}")
                    
                    # Don't retry if the model returned something that isn't JSON
                    if "```json" in response or "```" in response:
                        # Try to extract from code blocks
                        code_pattern = r'```(?:json)?\s*({.*?})\s*```'
                        code_match = re.search(code_pattern, response, re.DOTALL)
                        
                        if code_match:
                            try:
                                return json.loads(code_match.group(1))
                            except json.JSONDecodeError:
                                pass
                    
                    # Only retry on attempt 1 and 2, use fallback on attempt 3
                    if attempt < max_retries - 1:
                        logger.warning(f"Retrying content analysis in {retry_delay} seconds")
                        time.sleep(retry_delay)
                        continue
                    
                    # Return fallback on final attempt
                    return {
                        "relevance_score": 0.5,  # Neutral relevance
                        "key_facts": ["Error parsing analysis response"]
                    }
                    
            except requests.Timeout:
                logger.error(f"Request to Ollama API timed out on attempt {attempt+1}")
                if attempt < max_retries - 1:
                    longer_delay = retry_delay * (attempt + 1)  # Exponential backoff
                    logger.warning(f"Retrying in {longer_delay} seconds")
                    time.sleep(longer_delay)
                else:
                    return {
                        "relevance_score": 0.5,  # Neutral relevance
                        "key_facts": ["Timed out while analyzing content"]
                    }
            except Exception as e:
                logger.error(f"Failed to analyze content on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying in {retry_delay} seconds")
                    time.sleep(retry_delay)
                else:
                    return {
                        "relevance_score": 0.5,
                        "key_facts": [f"Error analyzing content: {e}"]
                    }
        
        # This should be unreachable but adding as a safeguard
        return {
            "relevance_score": 0,
            "key_facts": ["Maximum retries exceeded for content analysis"]
        }