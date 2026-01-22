# 🔍 Deep Search & Extraction API v2.0

**Advanced semantic search with reranking, anti-blocking, caching, and RAG chunking**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## ✨ Features

### 1. **Semantic Reranking** 🤖
- Google Gemini embeddings for cloud-based semantic reranking
- Local cross-encoder fallback (`mmarco-mMiniLMv2-L12-H384-v1`)
- Graceful degradation to original DDG order if all fail
- Optional:  Rerank only top-k results to save compute

### 2. **Anti-Blocking Tiered Fetching** 🌐
- **Tier 1:** Fast HTTPX/Trafilatura (200ms)
- **Tier 2:** Headless Playwright (3-8s, handles JS + Cloudflare)
- **Tier 3:** Return None and skip (graceful)
- 30-second timeout per URL
- Async I/O for high concurrency

### 3. **Smart File-Based Caching** 💾
- 24-hour TTL with auto-cleanup
- SHA-256 content hashing for deduplication
- Cache statistics endpoint
- Max 2GB (configurable for 16GB RAM machines)
- Persistent hit/miss tracking

### 4. **RAG-Ready Chunking** 📚
- **Markdown Strategy:** Split by headers + sentences (fast)
- **Semantic Strategy:** Group by similarity (slower, coherent)
- **Hybrid Strategy:** Try semantic, fallback to markdown (balanced)
- Token counting with tiktoken (GPT-2 compatible)
- Each chunk has:  `id`, `text`, `token_count`, `source_section`

### 5. **Production Reliability Suite** 🛡️
- **Edge-Case Handling**: Verified against DNS failures, 404s, and blocking sites.
- **SPA Support**: Automatically renders JavaScript-heavy sites (React/Vue) via Playwright.
- **Integration Tests**: Included suite for real-world API validation.

### 6. **Production Features** 🏭
- 30-second search timeout with background processing
- Graceful error handling (all features degrade gracefully)
- Health check endpoint
- Comprehensive logging
- Docker + Docker Compose support

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone repo
git clone https://github.com/yourusername/deep-search-api.git
cd deep-search-api

# Create .env with your Google API key
cp .env.example .env
# Edit .env - add GOOGLE_API_KEY

# Start server
docker-compose up --build

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Option 2: Local Python

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Create . env
cp .env.example .env
# Edit .env

# Run
python main.py
```

---

## 📡 API Examples

### Example 1: Semantic Reranking

Get the most relevant results based on semantic matching, not just keywords.

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "best practices for async Python",
    "max_results": 10,
    "enable_reranking": true,
    "rerank_top_k": 5
  }'
```

**Response includes:**
- Each result has `reranking_score` (0-1)
- Results sorted by relevance
- `reranking_status:  "success"` or fallback status

---

### Example 2: RAG Pipeline (Full Features)

Prepare data for LLM context injection.

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning optimization techniques",
    "max_results":  5,
    "enable_reranking": true,
    "rerank_top_k": 5,
    "enable_chunking": true,
    "chunking_strategy": "hybrid",
    "target_chunk_size": 350
  }'
```

**Response includes:**
- Results reranked by relevance
- Each result split into semantic chunks
- Each chunk has token count for context budgeting
- Ready to feed into GPT-4, Claude, etc.

---

### Example 3: Cache Statistics

Monitor cache efficiency. 

```bash
curl "http://localhost:8000/cache/stats"
```

**Response:**
```json
{
  "stats": {
    "total_entries": 45,
    "total_size_mb": 123.4,
    "hit_count": 234,
    "miss_count":  89,
    "hit_rate":  0.725
  }
}
```

---

## 📋 Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=sk-... 

# Cache (24-hour TTL, auto-cleanup to 2GB)
CACHE_ENABLED=true
CACHE_DIR=./cache
CACHE_TTL=86400
CACHE_MAX_SIZE_MB=2000

# Browser (30s timeout, 4 concurrent)
PLAYWRIGHT_TIMEOUT=30
MAX_BROWSERS=4

# Search (30s total timeout)
SEARCH_TIMEOUT=30
RERANKER_USE_CLOUD=true

# Chunking (Hybrid by default)
CHUNKING_STRATEGY=hybrid
CHUNK_SIZE=350

# Debug
DEBUG=false
```

See [USAGE_GUIDE.md](./USAGE_GUIDE.md) for detailed configuration. 

---

## 🏗️ Architecture

```
Request
  ↓
┌─────────────────────────────────┐
│ 1. Cache Check (24h TTL)        │ ← Return if hit
└────────┬────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ 2. DuckDuckGo Search            │ → Get URLs
└────────┬────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ 3. Tiered Fetch (Fast + PW)     │ → HTML content
└────────┬────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ 4. Extract (Trafilatura + LXML) │ → Text + metadata
└────────┬────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ 5. Rerank (Gemini + Fallback)   │ ← Optional, score docs
└────────┬────────────────────────┘
         ↓
┌─────────────────────────────────┐
│ 6. Chunk (Markdown/Semantic)    │ ← Optional, split for RAG
└────────┬────────────────────────┘
         ↓
Response (cached for next time)
```

---

## 📊 Performance

On 1vCPU + 16GB RAM: 

| Operation | Time |
|-----------|------|
| Cache hit | <10ms |
| Fast fetch | 1-3s |
| Playwright fallback | 3-8s |
| Gemini reranking | 2-4s |
| Local reranking | 0.5-1.5s |
| End-to-end (8 results) | 8-12s |

---

## 🔐 Security

- API keys via environment variables (never hardcoded)
- Cache files are plaintext (encrypt in production)
- No authentication layer (add reverse proxy auth)
- HTML content is extracted but not sanitized (use `bleach` if displaying)

---

## 🛠️ Troubleshooting

**Issue:** Playwright timeout
- Increase `PLAYWRIGHT_TIMEOUT` in `.env`

**Issue:** Cache disk full
- `POST /cache/clear` to delete all
- Reduce `CACHE_MAX_SIZE_MB` in `.env`

**Issue:** Reranking fails
- Check `GOOGLE_API_KEY` is valid
- Verify sentence-transformers installed:  `pip install sentence-transformers`

See [USAGE_GUIDE.md § Troubleshooting](./USAGE_GUIDE.md#-troubleshooting) for more. 

---

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - 5-minute setup
- **[USAGE_GUIDE.md](./USAGE_GUIDE.md)** - Detailed API & architecture
- **[API Docs](http://localhost:8000/docs)** - Interactive Swagger UI

---

## 🤝 Contributing

Found a bug?  Have a feature request? Open an issue! 

**Development Setup:**
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8

# Run fast unit tests
python tests/run_tests.py

# Run real-world integration tests
python -m pytest tests/test_integration.py

# Format code
black . 

# Lint
flake8 .
```

---

## 📄 License

MIT License - See [LICENSE](./LICENSE) file

---

## 📧 Support

Questions? Issues? 
- Open a GitHub issue
- Check discussions

---

## 🎯 Roadmap

- [ ] Add Mistral AI fallback for reranking
- [ ] Support for PDF/Document upload
- [ ] Webhook notifications for long-running searches
- [ ] Multi-language support
- [ ] GraphQL endpoint
- [ ] Batch search endpoint

---

**Made with ❤️ for the search enthusiasts**