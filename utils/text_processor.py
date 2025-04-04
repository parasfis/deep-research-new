\"""Text processing utilities for Deep Research Assistant.

This module provides functionality for processing and analyzing text content.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

# Try to import NLP libraries
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    nltk_available = True
except ImportError:
    nltk_available = False

try:
    import spacy
    spacy_available = True
except ImportError:
    spacy_available = False

logger = logging.getLogger(__name__)


class TextProcessor:
    """Class for processing and analyzing text content."""

    def __init__(self):
        """Initialize the text processor."""
        self.nltk_initialized = False
        self.spacy_model = None
        
        # Initialize NLP libraries if available
        if nltk_available:
            try:
                # Download required NLTK resources
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                self.nltk_initialized = True
            except Exception as e:
                logger.warning(f"Failed to initialize NLTK: {e}")
        
        if spacy_available:
            try:
                # Load a small spaCy model for efficiency
                self.spacy_model = spacy.load('en_core_web_sm')
            except Exception as e:
                logger.warning(f"Failed to load spaCy model: {e}")

    def extract_key_sentences(self, text: str, topic: str, max_sentences: int = 10) -> List[str]:
        """Extract key sentences related to the topic.

        Args:
            text: The text to extract sentences from.
            topic: The research topic.
            max_sentences: Maximum number of sentences to extract.

        Returns:
            List of key sentences.
        """
        if not text:
            return []
            
        # Split topic into keywords
        topic_keywords = set(self._extract_keywords(topic))
        
        # Tokenize text into sentences
        if self.nltk_initialized:
            sentences = sent_tokenize(text)
        else:
            # Simple sentence splitting fallback
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        
        # Score sentences based on keyword matches
        scored_sentences = []
        for sentence in sentences:
            # Skip very short sentences
            if len(sentence.split()) < 5:
                continue
                
            sentence_keywords = set(self._extract_keywords(sentence))
            # Calculate score based on keyword overlap
            score = len(sentence_keywords.intersection(topic_keywords))
            
            # Boost score for sentences with exact topic phrases
            if topic.lower() in sentence.lower():
                score += 3
                
            scored_sentences.append((sentence, score))
        
        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sentence for sentence, score in scored_sentences[:max_sentences] if score > 0]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text.

        Args:
            text: The text to extract keywords from.

        Returns:
            List of keywords.
        """
        # Convert to lowercase and tokenize
        text = text.lower()
        
        if self.nltk_initialized:
            # Use NLTK for tokenization and stopword removal
            tokens = word_tokenize(text)
            stop_words = set(stopwords.words('english'))
            keywords = [word for word in tokens if word.isalnum() and word not in stop_words]
        else:
            # Simple keyword extraction fallback
            # Remove punctuation and split by whitespace
            text = re.sub(r'[^\w\s]', '', text)
            tokens = text.split()
            # Simple stopword list
            simple_stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                               'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'of'}
            keywords = [word for word in tokens if word not in simple_stopwords]
            
        return keywords

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text.

        Args:
            text: The text to extract entities from.

        Returns:
            Dictionary mapping entity types to lists of entities.
        """
        entities = {
            "person": [],
            "organization": [],
            "location": [],
            "date": [],
            "other": []
        }
        
        if self.spacy_model:
            try:
                # Use spaCy for entity extraction
                doc = self.spacy_model(text)
                
                for ent in doc.ents:
                    if ent.label_ in ["PERSON", "PER"]:
                        entities["person"].append(ent.text)
                    elif ent.label_ in ["ORG", "ORGANIZATION"]:
                        entities["organization"].append(ent.text)
                    elif ent.label_ in ["GPE", "LOC", "LOCATION"]:
                        entities["location"].append(ent.text)
                    elif ent.label_ in ["DATE", "TIME"]:
                        entities["date"].append(ent.text)
                    else:
                        entities["other"].append(ent.text)
                        
                # Remove duplicates while preserving order
                for entity_type in entities:
                    seen = set()
                    entities[entity_type] = [x for x in entities[entity_type] 
                                           if not (x.lower() in seen or seen.add(x.lower()))]
            except Exception as e:
                logger.error(f"Error extracting entities with spaCy: {e}")
        
        return entities

    def summarize_text(self, text: str, max_length: int = 500) -> str:
        """Generate a summary of the text.

        Args:
            text: The text to summarize.
            max_length: Maximum length of the summary in characters.

        Returns:
            Summarized text.
        """
        if not text:
            return ""
            
        # Extract key sentences
        key_sentences = self.extract_key_sentences(text, "", max_sentences=5)
        
        # Join sentences into a summary
        summary = " ".join(key_sentences)
        
        # Truncate if necessary
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + "..."
            
        return summary

    def clean_text(self, text: str) -> str:
        """Clean and normalize text.

        Args:
            text: The text to clean.

        Returns:
            Cleaned text.
        """
        if not text:
            return ""
            
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove repeated punctuation
        text = re.sub(r'([.!?])\1+', r'\1', text)
        
        # Fix common issues
        text = text.replace(" .", ".")
        text = text.replace(" ,", ",")
        
        # Normalize quotes
        text = re.sub(r'["\'"'']', '"', text)
        text = re.sub(r'[''']', "'", text)
        
        return text.strip()

    def extract_citations(self, text: str) -> List[Dict[str, str]]:
        """Extract citations from text.

        Args:
            text: The text to extract citations from.

        Returns:
            List of dictionaries containing citation information.
        """
        citations = []
        
        # Match common citation patterns
        # APA style: (Author, Year)
        apa_pattern = r'\\(([A-Za-z\\s-]+),\\s*(\\d{4})\\)'
        
        # MLA style: (Author Page)
        mla_pattern = r'\\(([A-Za-z\\s-]+)\\s+(\\d+)\\)'
        
        # URL citations
        url_pattern = r'https?://[^\\s)>]+'
        
        # Extract APA citations
        for match in re.finditer(apa_pattern, text):
            citations.append({
                "type": "apa",
                "author": match.group(1).strip(),
                "year": match.group(2).strip(),
                "text": match.group(0)
            })
        
        # Extract MLA citations
        for match in re.finditer(mla_pattern, text):
            citations.append({
                "type": "mla",
                "author": match.group(1).strip(),
                "page": match.group(2).strip(),
                "text": match.group(0)
            })
        
        # Extract URL citations
        for match in re.finditer(url_pattern, text):
            citations.append({
                "type": "url",
                "url": match.group(0),
                "text": match.group(0)
            })
        
        return citations