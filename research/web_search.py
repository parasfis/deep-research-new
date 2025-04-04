"""Web search and scraping utilities for Deep Research Assistant.

This module provides functionality for searching the web and scraping content
from various sources in parallel.
"""

import logging
import time
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Import search engine APIs
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

import config

logger = logging.getLogger(__name__)


class WebSearcher:
    """Class for performing web searches and content extraction."""

    def __init__(self, search_engines: List[str] = None, timeout: int = None):
        """Initialize the web searcher.

        Args:
            search_engines: List of search engines to use. Defaults to config.SEARCH_ENGINES.
            timeout: Timeout for search requests in seconds. Defaults to config.SEARCH_TIMEOUT.
        """
        self.search_engines = search_engines or config.SEARCH_ENGINES
        self.timeout = timeout or config.SEARCH_TIMEOUT
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Perform a search across multiple search engines.

        Args:
            query: The search query.
            max_results: Maximum number of results to return per search engine.

        Returns:
            List of search results with metadata.
        """
        all_results = []
        
        with ThreadPoolExecutor(max_workers=len(self.search_engines)) as executor:
            future_to_engine = {
                executor.submit(self._search_with_engine, engine, query, max_results): engine
                for engine in self.search_engines
            }
            
            for future in as_completed(future_to_engine):
                engine = future_to_engine[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                    logger.info(f"Found {len(results)} results from {engine}")
                except Exception as e:
                    logger.error(f"Error searching with {engine}: {e}")
        
        # Remove duplicates based on URL
        unique_results = []
        seen_urls = set()
        
        for result in all_results:
            url = result.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results[:max_results]

    def _search_with_engine(self, engine: str, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform a search with a specific search engine.

        Args:
            engine: The search engine to use.
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        if engine == "duckduckgo":
            return self._search_duckduckgo(query, max_results)
        elif engine == "google":
            return self._search_google(query, max_results)
        elif engine == "searx":
            return self._search_searx(query, max_results)
        else:
            logger.warning(f"Unknown search engine: {engine}")
            return []

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        if not DDGS:
            logger.error("DuckDuckGo search module not available")
            return []
            
        try:
            results = []
            with DDGS() as ddgs:
                ddgs_results = list(ddgs.text(query, max_results=max_results))
                
                for result in ddgs_results:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", ""),
                        "source": "duckduckgo"
                    })
            return results
        except Exception as e:
            logger.error(f"Error in DuckDuckGo search: {e}")
            return []

    def _search_google(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using Google (via SerpAPI).

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        if not GoogleSearch:
            logger.error("Google search module (SerpAPI) not available")
            return []
            
        try:
            # Note: SerpAPI requires an API key, which should be set in environment variables
            params = {
                "q": query,
                "num": max_results,
                "api_key": os.getenv("SERPAPI_KEY", "")
            }
            
            if not params["api_key"]:
                logger.warning("No SerpAPI key found. Google search will be skipped.")
                return []
                
            search = GoogleSearch(params)
            results = []
            
            for result in search.get_dict().get("organic_results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "google"
                })
                
            return results
        except Exception as e:
            logger.error(f"Error in Google search: {e}")
            return []

    def _search_searx(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using a SearX instance.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results with metadata.
        """
        # Use a public SearX instance (or configure your own in config)
        searx_instance = os.getenv("SEARX_INSTANCE", "https://searx.be")
        
        try:
            params = {
                "q": query,
                "format": "json",
                "categories": "general",
                "language": "en-US",
                "time_range": "",  # empty for no time restriction
                "engines": "bing,brave,qwant",  # use engines that don't require API keys
            }
            
            response = self.session.get(
                f"{searx_instance}/search", 
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for result in data.get("results", [])[:max_results]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", ""),
                    "source": "searx"
                })
                
            return results
        except Exception as e:
            logger.error(f"Error in SearX search: {e}")
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