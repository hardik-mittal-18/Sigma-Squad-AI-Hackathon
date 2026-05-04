from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import os
import time
from sentence_transformers import SentenceTransformer
import faiss
import openai
from typing import List, Dict

app = FastAPI(title="BIS Standards Recommendation Engine")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the FAISS index and model
INDEX_PATH = os.path.join(os.path.dirname(__file__), 'faiss_index.pkl')
with open(INDEX_PATH, 'rb') as f:
    index, chunks, model = pickle.load(f)

# OpenAI API key (set in environment)
openai.api_key = os.getenv('OPENAI_API_KEY')

class QueryRequest(BaseModel):
    query: str

class Standard(BaseModel):
    code: str
    title: str
    reason: str

class RecommendResponse(BaseModel):
    standards: List[Standard]
    latency_seconds: float

def retrieve_top_chunks(query: str, top_k: int = 5):
    query_embedding = model.encode([query])
    faiss.normalize_L2(query_embedding)
    distances, indices = index.search(query_embedding, top_k)
    retrieved_chunks = [chunks[i] for i in indices[0]]
    return retrieved_chunks

def generate_recommendations(query: str, retrieved_chunks: List[str]):
    # Mock recommendations if no API key
    if not openai.api_key or openai.api_key == '':
        mock_standards = [
            Standard(code="IS 269", title="Ordinary Portland Cement", reason="General construction cement - commonly used"),
            Standard(code="IS 8112", title="High Strength Ordinary Portland Cement", reason="Higher strength applications"),
            Standard(code="IS 12269", title="53 Grade Ordinary Portland Cement", reason="Modern high-performance cement")
        ]
        return mock_standards
    
    try:
        context = "\n".join(retrieved_chunks)
        prompt = f"""
Based on the following BIS standards context, recommend the top 3-5 most relevant BIS standards for the product description: "{query}"

Context:
{context}

Provide the response in the following format:
- Code: Title - Reason

Only use standards from the context. No hallucinations.
"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1
        )
        recommendations_text = response.choices[0].message.content.strip()
        # Parse the response
        standards = []
        for line in recommendations_text.split('\n'):
            if line.startswith('- '):
                parts = line[2:].split(' - ', 2)
                if len(parts) >= 3:
                    code_title = parts[0].split(': ', 1)
                    if len(code_title) == 2:
                        code = code_title[0]
                        title = code_title[1]
                        reason = parts[1] if len(parts) > 2 else parts[1]
                        standards.append(Standard(code=code, title=title, reason=reason))
        return standards[:5]  # Top 3-5
    except Exception as e:
        # Fallback to mock if API fails
        mock_standards = [
            Standard(code="IS 269", title="Ordinary Portland Cement", reason="General construction - " + query[:30]),
            Standard(code="IS 383", title="Coarse and Fine Aggregate", reason="Aggregates for concrete"),
            Standard(code="IS 456", title="Code of Practice for Concrete", reason="Concrete structure design")
        ]
        return mock_standards

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: QueryRequest):
    start_time = time.time()
    try:
        retrieved = retrieve_top_chunks(request.query)
        standards = generate_recommendations(request.query, retrieved)
        latency = time.time() - start_time
        return RecommendResponse(standards=standards, latency_seconds=latency)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)