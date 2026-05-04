"""
Retrieval module with hybrid search (FAISS + BM25).
Implements semantic and lexical search with fusion.
"""

import os
import pickle
import logging
import numpy as np
from typing import List, Tuple
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

MODEL_NAME = 'all-MiniLM-L6-v2'
INDEX_DIR = Path(__file__).parent / 'indexes'
FAISS_INDEX_PATH = INDEX_DIR / 'faiss_index.pkl'

INDEX_DIR.mkdir(exist_ok=True)


class HybridRetriever:
    """Hybrid retriever combining FAISS (semantic) and BM25 (lexical) search."""
    
    def __init__(self):
        self.model = None
        self.faiss_index = None
        self.chunks = None
        self.bm25 = None
        self.tokenized_chunks = None
        
    def build_index(self, chunks: List[Tuple[str, str, int]]):
        """Build FAISS index and BM25 model."""
        logger.info("Building retrieval indexes...")
        
        # Initialize embedding model
        self.model = SentenceTransformer(MODEL_NAME)
        
        # Extract chunk texts
        chunk_texts = [chunk[1] for chunk in chunks]
        self.chunks = chunks
        
        # Build FAISS index (semantic search)
        logger.info("Creating embeddings...")
        embeddings = self.model.encode(chunk_texts, show_progress_bar=True)
        embeddings = embeddings.astype(np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create index
        dimension = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dimension)
        self.faiss_index.add(embeddings)
        
        logger.info(f"FAISS index created with {len(chunk_texts)} vectors")
        
        # Build BM25 index (lexical search)
        logger.info("Building BM25 index...")
        self.tokenized_chunks = [chunk.lower().split() for chunk in chunk_texts]
        self.bm25 = BM25Okapi(self.tokenized_chunks)
        
        logger.info("Indexes built successfully")
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Tuple[float, Tuple]]:
        """Semantic search using FAISS."""
        if self.faiss_index is None:
            raise RuntimeError("Index not built. Call build_index() first.")
        
        query_embedding = self.model.encode([query])
        query_embedding = query_embedding.astype(np.float32)
        faiss.normalize_L2(query_embedding)
        
        scores, indices = self.faiss_index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                results.append((float(score), self.chunks[idx]))
        
        return results
    
    def bm25_search(self, query: str, top_k: int = 5) -> List[Tuple[float, Tuple]]:
        """Lexical search using BM25."""
        if self.bm25 is None:
            raise RuntimeError("BM25 index not built. Call build_index() first.")
        
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((float(scores[idx]), self.chunks[idx]))
        
        return results
    
    def hybrid_search(self, query: str, top_k: int = 5, 
                     semantic_weight: float = 0.7, 
                     lexical_weight: float = 0.3) -> List[Tuple[float, Tuple]]:
        """
        Hybrid search combining semantic and lexical search.
        Uses weighted fusion.
        """
        # Get results from both retrievers
        semantic_results = self.semantic_search(query, top_k=top_k*2)
        bm25_results = self.bm25_search(query, top_k=top_k*2)
        
        # Normalize scores and combine
        scores_dict = {}
        
        # Add semantic scores
        for score, chunk in semantic_results:
            chunk_id = id(chunk)
            scores_dict[chunk_id] = semantic_weight * score
        
        # Add BM25 scores (normalize to 0-1 range)
        max_bm25_score = max([score for score, _ in bm25_results], default=1.0)
        if max_bm25_score > 0:
            for score, chunk in bm25_results:
                chunk_id = id(chunk)
                normalized_score = score / max_bm25_score if max_bm25_score > 0 else 0
                scores_dict[chunk_id] = scores_dict.get(chunk_id, 0) + lexical_weight * normalized_score
        
        # Sort by combined score
        combined_results = []
        for chunk in self.chunks:
            chunk_id = id(chunk)
            if chunk_id in scores_dict:
                combined_results.append((scores_dict[chunk_id], chunk))
        
        combined_results.sort(key=lambda x: x[0], reverse=True)
        return combined_results[:top_k]
    
    def save(self, path: Path = FAISS_INDEX_PATH):
        """Save indexes to disk."""
        logger.info(f"Saving indexes to {path}")
        with open(path, 'wb') as f:
            pickle.dump({
                'faiss_index': self.faiss_index,
                'chunks': self.chunks,
                'model': self.model,
                'bm25': self.bm25,
                'tokenized_chunks': self.tokenized_chunks
            }, f)
        logger.info("Indexes saved")
    
    def load(self, path: Path = FAISS_INDEX_PATH):
        """Load indexes from disk."""
        logger.info(f"Loading indexes from {path}")
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.faiss_index = data['faiss_index']
            self.chunks = data['chunks']
            self.model = data['model']
            self.bm25 = data['bm25']
            self.tokenized_chunks = data['tokenized_chunks']
        logger.info("Indexes loaded")


def get_retriever() -> HybridRetriever:
    """Get or create retriever instance."""
    retriever = HybridRetriever()
    
    if FAISS_INDEX_PATH.exists():
        try:
            retriever.load()
            return retriever
        except Exception as e:
            logger.warning(f"Failed to load index: {e}")
    
    # Build from scratch if not found
    from ingestion import load_documents, chunk_documents
    documents = load_documents()
    chunks = chunk_documents(documents)
    retriever.build_index(chunks)
    retriever.save()
    
    return retriever


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("Testing retrieval...")
    retriever = get_retriever()
    
    query = "cement for construction"
    print(f"\nQuery: {query}")
    
    print("\n=== Semantic Search ===")
    semantic_results = retriever.semantic_search(query, top_k=3)
    for score, chunk in semantic_results:
        print(f"Score: {score:.4f}, Doc: {chunk[0]}, Text: {chunk[1][:80]}...")
    
    print("\n=== BM25 Search ===")
    bm25_results = retriever.bm25_search(query, top_k=3)
    for score, chunk in bm25_results:
        print(f"Score: {score:.4f}, Doc: {chunk[0]}, Text: {chunk[1][:80]}...")
    
    print("\n=== Hybrid Search ===")
    hybrid_results = retriever.hybrid_search(query, top_k=3)
    for score, chunk in hybrid_results:
        print(f"Score: {score:.4f}, Doc: {chunk[0]}, Text: {chunk[1][:80]}...")
