"""Web search functionality for Deep Research Assistant.

This module provides functionality for performing web searches using various search engines.
"""

import os
import time
import logging
import requests
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

import config

class WebSearcher:
    """Class for performing web searches using various search engines."""

    def __init__(self):
        """Initialize the web searcher."""
        self.search_engines = config.SEARCH_ENGINES
        self.max_results_per_engine = config.MAX_RESULTS_PER_ENGINE
        self.timeout = config.SEARCH_TIMEOUT

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

        # Initialize search engine availability
        self.duckduckgo_available = False
        self.serpapi_available = False
        self.tavily_available = False

        # Try importing search engines
        try:
            from duckduckgo_search import ddg
            self.ddg = ddg
            self.duckduckgo_available = True
        except ImportError as e:
            logger.warning(f"Could not import duckduckgo_search. DuckDuckGo search will be unavailable. Error: {e}")

        try:
            from serpapi import GoogleSearch
            self.google_search = GoogleSearch
            self.serpapi_available = True
        except ImportError as e:
            logger.warning(f"Could not import serpapi. Google search will be unavailable. Error: {e}")

        try:
            from tavily import TavilyClient
            api_key = os.getenv("TAVILY_API_KEY")
            if api_key:
                self.tavily_client = TavilyClient(api_key=api_key)
                self.tavily_available = True
            else:
                logger.warning("TAVILY_API_KEY not found in environment variables. Tavily search will be unavailable.")
        except ImportError as e:
            logger.warning(f"Could not import tavily. Tavily search will be unavailable. Error: {e}")

    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """Perform a web search using multiple search engines.

        Args:
            query: Search query.
            max_results: Maximum number of results to return. If None, uses config value.

        Returns:
            List of search results with metadata.
        """
        if max_results is None:
            max_results = self.max_results_per_engine

        results = []
        successful_engines = []

        # Try each engine in order, stopping once we get results
        for engine in self.search_engines:
            try:
                engine_results = self._search_with_engine(engine, query, max_results)
                if engine_results:
                    logger.info(f"Found {len(engine_results)} results from {engine}")
                    results.extend(engine_results)
                    successful_engines.append(engine)
                    # If we have enough results, we can stop
                    if len(results) >= max_results:
                        break
                else:
                    logger.info(f"No results found from {engine}")
            except Exception as e:
                logger.error(f"Error getting search results from {engine}: {e}")
        
        # If we didn't get any results from primary engines, try parallel search as fallback
        if not results:
            logger.warning("No results from primary engine search. Trying parallel search as fallback.")
            with ThreadPoolExecutor() as executor:
                futures = []
                for engine in self.search_engines:
                    if engine not in successful_engines:  # Don't retry engines that we already tried
                        futures.append(executor.submit(self._search_with_engine, engine, query, max_results))

                for future in as_completed(futures):
                    try:
                        engine_results = future.result()
                        results.extend(engine_results)
                    except Exception as e:
                        # Already logged in _search_with_engine
                        pass

        return results[:max_results]  # Ensure we don't return more than max_results

    def _search_with_engine(self, engine: str, query: str, max_results: int) -> List[Dict]:
        """Perform a search with a specific search engine.

        Args:
            engine: The search engine to use.
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        if engine == "duckduckgo" and self.duckduckgo_available:
            return self._search_duckduckgo(query, max_results)
        elif engine == "google" and self.serpapi_available:
            return self._search_google(query, max_results)
        elif engine == "tavily" and self.tavily_available:
            return self._search_tavily(query, max_results)
        else:
            logger.warning(f"Search engine {engine} is not available")
            return []

    def _search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict]:
        """Perform a search using DuckDuckGo.

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        if not self.duckduckgo_available:
            logger.error("DuckDuckGo search module not available")
            return []

        try:
            # Use a more resilient approach - try up to 3 times
            for attempt in range(3):
                try:
                    results = self.ddg(query, max_results=max_results)
                    if results:
                        return [{
                            "title": result.get("title", ""),
                            "url": result.get("link", ""),
                            "snippet": result.get("body", ""),
                            "source": "duckduckgo"
                        } for result in results]
                    else:
                        logger.warning(f"Empty results from DuckDuckGo on attempt {attempt+1}")
                        time.sleep(1)  # Wait a bit before retrying
                except Exception as e:
                    logger.warning(f"Error in DuckDuckGo search attempt {attempt+1}: {e}")
                    time.sleep(1)  # Wait a bit before retrying
                    
            logger.error("All DuckDuckGo search attempts failed")
            return []
        except Exception as e:
            logger.error(f"Error performing DuckDuckGo search: {e}")
            return []

    def _search_google(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using Google (via SerpAPI).

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        if not self.serpapi_available:
            logger.error("Google search module (SerpAPI) not available")
            return []
            
        try:
            # Note: SerpAPI requires an API key, which should be set in environment variables
            api_key = os.getenv("SERPAPI_KEY", "")
            
            if not api_key:
                logger.warning("No SerpAPI key found. Google search will be skipped.")
                return []
                
            params = {
                "q": query,
                "num": max_results,
                "api_key": api_key,
                "gl": "us",  # Country code for search
                "hl": "en"   # Language code
            }
            
            search = self.google_search(params)
            results = []
            
            for result in search.get_dict().get("organic_results", []):
                if not result.get("link") or not result.get("title"):
                    continue  # Skip invalid results
                    
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "google"
                })
                
            if not results:
                logger.warning(f"No results found for Google query: {query}")
                
            return results
        except Exception as e:
            logger.error(f"Error in Google search: {e}")
            return []

    def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using Tavily API.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        if not self.tavily_client:
            logger.error("Tavily client not initialized. Make sure TAVILY_API_KEY is set.")
            return []
            
        try:
            results = []
            search_response = self.tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=max_results
            )
            
            for result in search_response.get("results", [])[:max_results]:
                if not result.get("url") or not result.get("title"):
                    continue  # Skip invalid results
                    
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", ""),
                    "source": "tavily"
                })
                
            if not results:
                logger.warning(f"No results found for Tavily query: {query}")
                
            return results
        except Exception as e:
            logger.error(f"Error in Tavily search: {e}")
            return []

    def fetch_content(self, urls: List[str], max_workers: int = None) -> Dict[str, Dict[str, Any]]:
        """Fetch content from multiple URLs in parallel.

        Args:
            urls: List of URLs to fetch content from.
            max_workers: Maximum number of parallel workers. Defaults to config.MAX_PARALLEL_SEARCHES.

        Returns:
            Dictionary mapping URLs to their content and metadata.
        """
        max_workers = max_workers or config.MAX_PARALLEL_SEARCHES
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self._fetch_url, url): url for url in urls}
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    content, metadata = future.result()
                    if content:
                        results[url] = {
                            "content": content,
                            "metadata": metadata
                        }
                        logger.info(f"Successfully fetched content from {url}")
                    else:
                        logger.warning(f"No content fetched from {url}")
                except Exception as e:
                    logger.error(f"Error fetching content from {url}: {e}")
        
        return results

    def _fetch_url(self, url: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Fetch content from a single URL.

        Args:
            url: URL to fetch content from.

        Returns:
            Tuple of (content, metadata) where content is the extracted text
            and metadata contains information about the source.
        """
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc,
            "timestamp": time.time(),
            "content_type": None,
            "title": None,
            "length": 0
        }
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "")
            metadata["content_type"] = content_type
            
            # Only process HTML content
            if "text/html" not in content_type.lower():
                return None, metadata
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title
            title_tag = soup.find("title")
            if title_tag:
                metadata["title"] = title_tag.get_text(strip=True)
            
            # Remove unwanted elements
            for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            
            # Extract main content
            main_content = ""
            
            # Try to find main content container
            main_tags = soup.find_all(["main", "article", "div", "section"], 
                                     class_=["content", "main", "article", "post"])
            
            if main_tags:
                # Use the largest content block
                main_tag = max(main_tags, key=lambda x: len(x.get_text()))
                main_content = main_tag.get_text(separator="\n", strip=True)
            else:
                # Fallback to body content
                body = soup.find("body")
                if body:
                    main_content = body.get_text(separator="\n", strip=True)
                else:
                    main_content = soup.get_text(separator="\n", strip=True)
            
            # Clean up content
            lines = [line.strip() for line in main_content.split("\n") if line.strip()]
            cleaned_content = "\n".join(lines)
            
            metadata["length"] = len(cleaned_content)
            
            return cleaned_content, metadata
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None, metadata

    def parallel_research(self, queries: List[str], max_results_per_query: int = 5, 
                         max_content_sources: int = None) -> Dict[str, Any]:
        """Perform parallel research on multiple queries.

        Args:
            queries: List of search queries.
            max_results_per_query: Maximum number of results per query.
            max_content_sources: Maximum number of content sources to fetch.
                Defaults to config.MAX_SOURCES_PER_TOPIC.

        Returns:
            Dictionary containing search results and fetched content.
        """
        max_content_sources = max_content_sources or config.MAX_SOURCES_PER_TOPIC
        all_search_results = []
        
        # Perform searches in parallel
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            future_to_query = {
                executor.submit(self.search, query, max_results_per_query): query
                for query in queries
            }
            
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    results = future.result()
                    for result in results:
                        result["query"] = query  # Add the original query
                    all_search_results.extend(results)
                    logger.info(f"Completed search for query: {query}")
                except Exception as e:
                    logger.error(f"Error searching for query {query}: {e}")
        
        # Deduplicate and select top results
        unique_urls = {}
        for result in all_search_results:
            url = result.get("url")
            if url and url not in unique_urls:
                unique_urls[url] = result
        
        top_urls = list(unique_urls.keys())[:max_content_sources]
        logger.info(f"Selected {len(top_urls)} unique URLs for content fetching")
        
        # Fetch content from top URLs
        content_results = self.fetch_content(top_urls)
        
        # Combine search results with content
        research_data = {
            "search_results": all_search_results,
            "content_sources": []
        }
        
        for url, content_data in content_results.items():
            search_result = unique_urls.get(url, {})
            research_data["content_sources"].append({
                "url": url,
                "title": content_data["metadata"].get("title") or search_result.get("title", ""),
                "query": search_result.get("query", ""),
                "snippet": search_result.get("snippet", ""),
                "content": content_data["content"],
                "metadata": content_data["metadata"]
            })
        
        return research_data