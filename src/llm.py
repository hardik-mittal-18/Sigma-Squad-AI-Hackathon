"""
LLM integration module with caching and query expansion.
Handles recommendation generation from retrieved context.
"""

import logging
import json
from typing import List, Dict, Optional
from functools import lru_cache
import os

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)

# Configuration
CACHE_SIZE = 128
TEMPERATURE = 0.1
MAX_TOKENS = 300

# Mock BIS standards for fallback
MOCK_STANDARDS = {
    "IS 269": "Ordinary Portland Cement",
    "IS 8112": "High Strength Ordinary Portland Cement",
    "IS 12269": "53 Grade Ordinary Portland Cement",
    "IS 383": "Coarse and Fine Aggregate for Concrete",
    "IS 456": "Plain and Reinforced Concrete - Code of Practice",
    "IS 800": "General Construction in Steel - Code of Practice",
    "IS 875": "Code of Practice for Design Loads",
    "IS 13920": "Ductile Detailing of Reinforced Concrete Structures"
}


def query_expansion(query: str) -> List[str]:
    """
    Expand query to improve retrieval.
    Generates alternative formulations of the query.
    """
    expansions = [query]
    
    # Simple keyword-based expansion
    query_lower = query.lower()
    
    if "cement" in query_lower:
        expansions.append("Portland cement specifications standards")
        expansions.append("cement composition and properties")
    
    if "steel" in query_lower:
        expansions.append("steel reinforcement construction standards")
        expansions.append("structural steel specifications")
    
    if "concrete" in query_lower:
        expansions.append("reinforced concrete design code practice")
        expansions.append("concrete mix design specifications")
    
    if "aggregate" in query_lower:
        expansions.append("coarse fine aggregate specifications")
        expansions.append("aggregate concrete properties")
    
    return expansions[:3]  # Return top 3 expansions


class StandardExtractor:
    """Extract BIS standards from text."""
    
    # Pattern of standard codes (e.g., "IS 269", "IS 800")
    STANDARD_PATTERN = r'IS\s+\d+'
    
    @staticmethod
    def extract_codes(text: str) -> List[str]:
        """Extract BIS standard codes from text."""
        import re
        codes = re.findall(StandardExtractor.STANDARD_PATTERN, text)
        return list(set(codes))  # Remove duplicates
    
    @staticmethod
    def get_title(code: str) -> str:
        """Get standard title."""
        return MOCK_STANDARDS.get(code, f"Standard {code}")


class LLMRecommender:
    """LLM-based recommendation generator."""
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock or not HAS_OPENAI or not os.getenv('OPENAI_API_KEY')
        if HAS_OPENAI and os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"Using {'MOCK' if self.use_mock else 'REAL'} LLM mode")
    
    @lru_cache(maxsize=CACHE_SIZE)
    def _call_llm(self, query: str, context: str) -> str:
        """
        Call LLM with caching.
        Cache key is created from query + context hash.
        """
        if self.use_mock:
            return self._mock_response(query, context)
        
        try:
            prompt = f"""Based on the following BIS standards context, recommend the top 3-5 most relevant BIS standards for: "{query}"

Context:
{context}

Provide response as JSON with this exact format:
{{
  "standards": [
    {{"code": "IS 269", "title": "Ordinary Portland Cement", "reason": "explanation"}},
    {{"code": "IS 8112", "title": "High Strength OPC", "reason": "explanation"}}
  ]
}}

Use ONLY standards mentioned in the context. No hallucinations."""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._mock_response(query, context)
    
    def _mock_response(self, query: str, context: str) -> str:
        """Generate mock response without API."""
        extracted_codes = StandardExtractor.extract_codes(context)
        
        if not extracted_codes:
            # Fallback to generic standards for the query
            if "cement" in query.lower():
                extracted_codes = ["IS 269", "IS 8112", "IS 12269"]
            elif "steel" in query.lower():
                extracted_codes = ["IS 800", "IS 875"]
            elif "concrete" in query.lower():
                extracted_codes = ["IS 456", "IS 383", "IS 13920"]
            else:
                extracted_codes = ["IS 269", "IS 456"]
        
        standards = []
        for code in extracted_codes[:5]:
            standards.append({
                "code": code,
                "title": StandardExtractor.get_title(code),
                "reason": f"Relevant for {query[:30]}"
            })
        
        return json.dumps({"standards": standards})
    
    def generate_recommendations(self, query: str, retrieved_chunks: List[str]) -> List[Dict]:
        """Generate recommendations from retrieved chunks."""
        context = "\n".join(retrieved_chunks[:3])  # Use top 3 chunks
        
        try:
            response_text = self._call_llm(query, context)
            response_json = json.loads(response_text)
            return response_json.get("standards", [])
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response, using mock")
            return self._mock_response(query, context)
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return []


# Global cache decorator for LLM calls
@lru_cache(maxsize=CACHE_SIZE)
def cached_recommend(query: str, context_hash: str) -> str:
    """Cached recommendation lookup."""
    return query  # Placeholder


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("Testing LLM module...")
    
    recommender = LLMRecommender(use_mock=True)
    
    query = "cement for construction"
    context = """IS 269: Ordinary Portland Cement
This standard specifies requirements for ordinary Portland cement.

IS 8112: High Strength OPC
For high strength applications.

IS 456: Concrete Code
Code of practice for concrete structures."""
    
    recommendations = recommender.generate_recommendations(query, [context])
    
    print(f"\nQuery: {query}")
    print("\nRecommendations:")
    for std in recommendations:
        print(f"  {std['code']}: {std['title']}")
        print(f"    Reason: {std['reason']}")
