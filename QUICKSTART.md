# BIS Standards Recommendation Engine - Quick Start Guide

## 🚀 5-Minute Setup

### 1. Install Dependencies (2 min)
```bash
pip install -r requirements.txt
```

### 2. Build Vector Index (1 min)
```bash
python -c "import sys; sys.path.insert(0, 'src'); from retrieval import get_retriever; r = get_retriever()"
```

### 3. Start Backend (1 min)
```bash
python -m src.api
```
✅ API running at: http://localhost:8000

### 4. Start Frontend (1 min, separate terminal)
```bash
cd src/frontend
python -m http.server 3000
```
✅ UI available at: http://localhost:3000/index.html

---

## 🧪 Test the System

### Option A: Web UI
1. Open http://localhost:3000/index.html
2. Enter: "cement for construction"
3. Click "Get Recommendations"
4. See results in ~0.4s

### Option B: API Endpoint
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "steel reinforcement bars"}'
```

### Option C: Batch Processing
```bash
python inference.py --input sample_input.json --output sample_output.json
```

---

## 📊 Evaluate Performance
```bash
python eval_script.py --predictions sample_output.json --ground_truth ground_truth.json
```

---

## 📁 Files Generated During Hackathon

### Modular Architecture
- `src/ingestion.py` - Document loading & chunking
- `src/retrieval.py` - FAISS + BM25 hybrid search
- `src/llm.py` - LLM integration with caching
- `src/api.py` - FastAPI backend

### Outputs
- `src/indexes/faiss_index.pkl` - Vector database
- `sample_output.json` - Batch processing results
- `metrics.json` - Evaluation metrics
- `presentation/` - Presentation materials

### Supporting Files
- `inference.py` - CLI for batch processing
- `eval_script.py` - Performance evaluation
- `presentation.py` - Generate presentation slides
- `sample_input.json` - Test queries
- `ground_truth.json` - Ground truth for evaluation

---

## 🎯 Performance Metrics (as of last run)

| Metric | Value |
|--------|-------|
| Avg Latency | 0.11s |
| Queries Processed | 5 |
| Hit@3 | 0.40 |
| Hit@5 | 0.60 |
| MRR@5 | 0.34 |
| Throughput | ~90 queries/minute |

---

## 🔧 Optional: Use Real OpenAI API

Set environment variable:
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"

# Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"
```

Then restart backend for real LLM recommendations.

---

## 📚 API Documentation

Swagger UI: http://localhost:8000/docs

### POST /recommend
```json
Request: {"query": "cement for construction"}
Response: {
  "standards": [
    {"code": "IS 269", "title": "...", "reason": "..."}
  ],
  "latency_seconds": 0.45,
  "confidence": 0.87
}
```

---

## 💡 Quick Tips

✅ System works offline (uses mock LLM)
✅ Hybrid search combines semantic + keyword matching
✅ Caching speeds up repeated queries
✅ Query expansion improves recall
✅ Batch processing for scalability

---

## 🎓 Next Steps

1. Review PRESENTATION_OUTLINE.txt in the `presentation/` folder
2. Follow DEMO_SCRIPT.txt for your 7-minute presentation
3. Use ARCHITECTURE_DIAGRAM.txt in your slides
4. Modify sample data in `data/` for more realistic scenarios
5. Add real BIS PDFs to `data/` folder and rebuild index

---

Built with ❤️ for the BIS Standards Recommendation Engine Challenge
