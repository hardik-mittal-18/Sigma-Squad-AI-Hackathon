"""
FastAPI backend for BIS Standards Recommendation Engine.
Orchestrates retrieval and LLM modules.
"""

import logging
import time
import sys
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from retrieval import get_retriever
from llm import LLMRecommender, query_expansion, MOCK_STANDARDS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="BIS Standards Recommendation Engine",
    description="RAG-based system for recommending BIS standards",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
retriever = None
recommender = None

# Validation constants
VALID_MATERIALS = {
    'cement', 'steel', 'concrete', 'aggregate', 'reinforcement',
    'rebar', 'coarse aggregate', 'fine aggregate', 'sand', 'gravel',
    'brick', 'block', 'mortar', 'paste', 'fiber'
}


# Pydantic models
class Standard(BaseModel):
    code: str = Field(..., description="BIS standard code (e.g., 'IS 269')")
    title: str = Field(..., description="Full title of the standard")
    reason: str = Field(..., description="Why this standard is recommended")


class RecommendRequest(BaseModel):
    query: str = Field(..., description="Product description", min_length=3, max_length=500)


class RecommendResponse(BaseModel):
    standards: List[Standard] = Field(..., description="Top 3-5 recommended standards")
    latency_seconds: float = Field(..., description="Time taken to generate recommendations")
    query: str = Field(..., description="Original query")
    confidence: float = Field(..., description="Confidence score (0-1)")


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    model_loaded: bool


# Utility functions
def validate_query(query: str) -> bool:
    """Validate if query is about building materials."""
    query_lower = query.lower()
    return any(material in query_lower for material in VALID_MATERIALS)


def calculate_confidence(num_standards: int, avg_score: float) -> float:
    """Calculate confidence of recommendations."""
    # Confidence based on number of standards and retrieval score
    confidence = min(0.95, (num_standards / 5.0) * 0.5 + avg_score * 0.5)
    return max(0.1, confidence)


@app.on_event("startup")
async def startup_event():
    """Initialize models on startup."""
    global retriever, recommender
    try:
        logger.info("Initializing retriever...")
        retriever = get_retriever()
        logger.info("Retriever initialized")
        
        logger.info("Initializing recommender...")
        recommender = LLMRecommender()
        logger.info("Recommender initialized")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if retriever and recommender else "degraded",
        timestamp=datetime.now().isoformat(),
        model_loaded=retriever is not None and recommender is not None
    )


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """
    Recommend BIS standards for a product description.
    
    Args:
        request: RecommendRequest with product description
        
    Returns:
        RecommendResponse with top standards and latency
    """
    start_time = time.time()
    
    try:
        # Validate input
        query = request.query.strip()
        
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not validate_query(query):
            raise HTTPException(
                status_code=400,
                detail="Query must be about building materials (cement, steel, concrete, aggregates, etc.)"
            )
        
        logger.info(f"Processing query: {query}")
        
        # Query expansion
        expanded_queries = query_expansion(query)
        logger.info(f"Expanded queries: {expanded_queries}")
        
        # Retrieve chunks with hybrid search
        all_chunks = []
        scores = []
        
        for q in expanded_queries:
            try:
                results = retriever.hybrid_search(q, top_k=5)
                for score, chunk in results:
                    all_chunks.append(chunk[1])
                    scores.append(score)
            except Exception as e:
                logger.warning(f"Hybrid search failed for '{q}': {e}")
        
        if not all_chunks:
            logger.warning(f"No chunks retrieved for query: {query}")
            all_chunks = [f"Query about {query}"]
            scores = [0.5]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk not in seen:
                unique_chunks.append(chunk)
                seen.add(chunk)
        
        logger.info(f"Retrieved {len(unique_chunks)} unique chunks")
        
        # Generate recommendations
        recommendations = recommender.generate_recommendations(query, unique_chunks)
        
        if not recommendations:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate recommendations"
            )
        
        # Convert to response format
        standards = [
            Standard(
                code=std['code'],
                title=std['title'],
                reason=std['reason']
            )
            for std in recommendations
        ]
        
        latency = time.time() - start_time
        avg_score = sum(scores) / len(scores) if scores else 0.5
        confidence = calculate_confidence(len(standards), avg_score)
        
        logger.info(f"Generated {len(standards)} recommendations in {latency:.2f}s")
        
        return RecommendResponse(
            standards=standards,
            latency_seconds=round(latency, 3),
            query=query,
            confidence=round(confidence, 3)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/standards", response_model=Dict[str, str])
async def list_standards():
    """Get list of all available BIS standards."""
    return MOCK_STANDARDS


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
