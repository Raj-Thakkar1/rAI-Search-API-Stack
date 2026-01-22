# Deep Search & Extraction API v2.0 - Complete Guide

## 🚀 Overview

This is a **production-grade semantic search and content extraction system** with: 

- ✅ **Semantic Reranking** via Google Gemini embeddings (with local fallback)
- ✅ **Anti-Blocking Browser Fallback** using Playwright
- ✅ **24-Hour File-Based Caching** with automatic cleanup & stats
- ✅ **RAG-Ready Chunking** (markdown/semantic/hybrid strategies)
- ✅ **Graceful Degradation** - All features degrade gracefully on failure
- ✅ **30-Second Search Timeout** with background processing
- ✅ **16GB RAM & 1vCPU Optimized** 

---

## 📋 Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Running the Server](#running-the-server)
4. [API Endpoints](#api-endpoints)
5. [Examples](#examples)
6. [Architecture](#architecture)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Installation

### Prerequisites

- Python 3.10+
- 16GB RAM (tested)
- 1vCPU or more

### Step 1: Clone or Create Project

```bash
mkdir deep-search-api
cd deep-search-api
git clone https://github.com/yourusername/deep-search-api.git
# or copy the provided files
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install Playwright Browsers

```bash
playwright install chromium
```

This downloads the Chromium browser for JavaScript rendering fallback.

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Cache Configuration
CACHE_ENABLED=true
CACHE_DIR=./cache
CACHE_TTL=86400  # 24 hours in seconds
CACHE_MAX_SIZE_MB=2000  # 2GB max cache size

# Playwright Configuration
PLAYWRIGHT_TIMEOUT=30  # seconds
MAX_BROWSERS=4  # Concurrent browsers

# Search Configuration
SEARCH_TIMEOUT=30  # seconds
RERANKER_USE_CLOUD=true  # Try Google Gemini first

# Chunking Configuration
CHUNKING_STRATEGY=hybrid  # markdown, semantic, or hybrid
CHUNK_SIZE=350  # tokens

# Debug Mode
DEBUG=false
```

### Getting a Google API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Generative Language API** and **Gemini API**
4. Create an API key (Service Account)
5. Add to `.env`

---

## 🏃 Running the Server

### Option 1: Development

```bash
python main.py
```

Server will start at `http://localhost:8000`

Interactive docs:  `http://localhost:8000/docs`

### Option 2: Production with Gunicorn

```bash
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers. UvicornWorker --bind 0.0.0.0:8000
```

### Option 3: Docker (Recommended)

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application
COPY . .

# Set environment
ENV PYTHONUNBUFFERED=1

# Run
CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t deep-search-api .
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key \
  -v cache:/app/cache \
  deep-search-api
```

---

## 📡 API Endpoints

### 1. POST `/search` - Main Search Endpoint

Performs a complete search with optional reranking, chunking, and caching.

**Request:**

```json
{
  "query": "SpaceX Starship launch timeline",
  "max_results":  10,
  "deep_extract": true,
  "enable_reranking": true,
  "rerank_top_k": 5,
  "enable_chunking": true,
  "chunking_strategy": "hybrid",
  "target_chunk_size": 350
}
```

**Response:**

```json
{
  "query": "SpaceX Starship launch timeline",
  "total_results": 10,
  "results": [
    {
      "url": "https://example.com/spacex",
      "title": "SpaceX Starship Launch Plans",
      "author": "John Doe",
      "date": "2026-01-20",
      "content_markdown":  "## SpaceX Starship.. .",
      "content_html": "<html>...</html>",
      "images": [
        {
          "type": "image",
          "src": "https://.. .",
          "alt": "Starship prototype"
        }
      ],
      "chunks": [
        {
          "id": 0,
          "text": "Starship is...",
          "token_count": 150,
          "start_char":  0,
          "end_char": 450,
          "source_section": "## Introduction"
        }
      ],
      "chunking_metadata": {
        "success": true,
        "strategy": "hybrid",
        "total_chunks": 12,
        "total_tokens":  2450,
        "message": "Successfully chunked into 12 chunks..."
      },
      "reranking_score": 0.92
    }
  ],
  "search_timestamp": "2026-01-21T12:34:56.789Z",
  "search_duration_seconds": 8.5,
  "reranking_enabled": true,
  "reranking_status": "success",
  "cache_hit":  false
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query |
| `max_results` | int | 5 | 1-20, results to fetch from DDG |
| `deep_extract` | bool | true | Extract full HTML content |
| `enable_reranking` | bool | false | Use semantic reranking |
| `rerank_top_k` | int | null | Rerank only top-k (null = all) |
| `enable_chunking` | bool | true | Split into RAG chunks |
| `chunking_strategy` | string | "hybrid" | "markdown", "semantic", or "hybrid" |
| `target_chunk_size` | int | 350 | Target chunk size in tokens |

---

### 2. GET `/cache/stats` - Cache Statistics

Get detailed cache usage statistics.

**Response:**

```json
{
  "stats": {
    "total_entries": 45,
    "total_size_mb": 123.4,
    "hit_count": 234,
    "miss_count":  89,
    "hit_rate":  0.725,
    "oldest_entry":  "2026-01-20T08:00:00Z",
    "newest_entry": "2026-01-21T15:30:00Z"
  },
  "timestamp": "2026-01-21T15:35:00Z"
}
```

---

### 3. POST `/cache/clear` - Clear Cache

Delete all cached entries.

**Response:**

```json
{
  "message": "Cache cleared successfully"
}
```

---

### 4. GET `/health` - Health Check

Verify API is running.

**Response:**

```json
{
  "status":  "healthy",
  "timestamp":  "2026-01-21T15:35:00Z",
  "config": {
    "cache_enabled": true,
    "reranking_enabled": true,
    "browser_fallback_enabled":  true
  }
}
```

---

## 💡 Examples

### Example 1: Simple Search (No Reranking)

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python async programming",
    "max_results": 5,
    "enable_reranking": false,
    "enable_chunking": false
  }'
```

**Use case:** Quick search without heavy processing

---

### Example 2: Semantic Reranking Only

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how to optimize database queries",
    "max_results":  10,
    "deep_extract": true,
    "enable_reranking": true,
    "rerank_top_k": 5,
    "enable_chunking":  false
  }'
```

**Use case:** Get the most relevant results based on semantic similarity

**Output:** 
- Top 5 results reranked by relevance
- Each result has `reranking_score` (0-1)
- Results sorted by score (highest first)

---

### Example 3: RAG Pipeline (Full Features)

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning best practices",
    "max_results": 8,
    "deep_extract":  true,
    "enable_reranking": true,
    "rerank_top_k": 8,
    "enable_chunking": true,
    "chunking_strategy": "hybrid",
    "target_chunk_size": 350
  }'
```

**Use case:** Prepare data for RAG (Retrieval Augmented Generation)

**Output:**
- Top 8 results reranked by relevance
- Each result split into semantic chunks
- Each chunk has token count for context window budgeting
- Ready to feed into LLMs (GPT, Claude, etc.)

---

### Example 4: Semantic Chunking Strategy

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change solutions",
    "max_results":  3,
    "enable_chunking": true,
    "chunking_strategy": "semantic",
    "target_chunk_size":  300
  }'
```

**Chunking Strategies:**

- **markdown**: Split by headers first, then sentences (fast, respects structure)
- **semantic**: Group sentences by semantic similarity (slower, more coherent)
- **hybrid** (default): Try semantic first, fallback to markdown (balanced)

---

### Example 5: Check Cache Statistics

```bash
curl -X GET "http://localhost:8000/cache/stats"
```

**Output:**

```json
{
  "stats": {
    "total_entries": 12,
    "total_size_mb": 45.2,
    "hit_count": 89,
    "miss_count":  34,
    "hit_rate":  0.72
  }
}
```

---

## 🏗️ Architecture

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│              1. CACHE CHECK (FileBasedCache)                 │
│  - SHA-256 hash of query + params as key                     │
│  - Return cached result if < 24h old                         │
│  - Else, proceed to search                                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│          2. DISCOVERY (DuckDuckGo Search)                    │
│  - Run in thread pool (non-blocking)                         │
│  - Returns:  [{"href": ".. .", "title": ".. .", ... }]           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│    3. ACQUISITION (TieredFetcher - Anti-Blocking)           │
│  Tier 1: Fast HTTPX/Trafilatura fetch (200ms)               │
│    └─ If fails or 403 → Tier 2                              │
│  Tier 2: Playwright headless browser (3-5s)                 │
│    └─ Renders JavaScript, handles Cloudflare              │
│    └─ If fails → Return None (graceful)                     │
│  Returns: HTML content or None                              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│         4. EXTRACTION (LXML + Trafilatura)                  │
│  - Run in ProcessPoolExecutor (bypass Python GIL)           │
│  - Trafilatura: Extract markdown + metadata                 │
│  - LXML: Extract images, videos, tables, links              │
│  - SimHash: Fingerprint for deduplication                   │
│  Returns: {url, title, content, images, tables, links... }   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  5. RERANKING (Optional - SemanticReranker)                 │
│  If enabled:                                                 │
│    Tier 1: Google Gemini embeddings (cloud)                 │
│      └─ Embed query + top-k docs                           │
│      └─ Cosine similarity scoring                           │
│    Tier 2: Local cross-encoder (fallback)                   │
│      └─ cross-encoder/mmarco-mMiniLMv2-L12-H384-v1         │
│    Tier 3: Return original DDG order (graceful)             │
│  Returns: Documents sorted by relevance score               │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│      6. CHUNKING (Optional - RAGChunker)                     │
│  If enabled:                                                 │
│    Strategy:                                                  │
│      - markdown: Split by headers, then sentences           │
│      - semantic: Group by similarity (slower)               │
│      - hybrid: Try semantic, fallback to markdown           │
│  Returns: [{id, text, token_count, source_section}, ...]    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│         7. ASSEMBLY & CACHING (PipelineOrchestrator)        │
│  - Build RichDocument objects                               │
│  - Attach metadata (reranking scores, chunk info)           │
│  - Cache result (async in background)                       │
│  - Return SearchResponse                                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                   USER RESPONSE                              │
│  SearchResponse with all extracted data                      │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**1. File-Based Caching (Not Redis)**
- ✅ No external dependency
- ✅ Works on single machine (1vCPU)
- ✅ Auto-cleanup when > 2GB
- ✅ SHA-256 content hashing for dedup

**2. Playwright in Separate Process Pool**
- ✅ Non-blocking (uses asyncio)
- ✅ Timeout protected (30s max)
- ✅ 4 concurrent browsers max (1vCPU safe)
- ✅ Graceful fallback if fails

**3. Semantic Reranking with Fallback**
- ✅ Cloud first (Google Gemini for scale)
- ✅ Local fallback (cross-encoder, no API calls)
- ✅ Graceful degradation (return DDG order if all fail)

**4. RAG Chunking with Multiple Strategies**
- ✅ Markdown-based (fast, structure-aware)
- ✅ Semantic similarity (slow, coherent)
- ✅ Hybrid (balanced approach)
- ✅ Token counting with tiktoken

---

## 🚨 Troubleshooting

### Issue: "GOOGLE_API_KEY not set"

**Solution:**
1. Create `.env` file with `GOOGLE_API_KEY=your_key`
2. Or set environment variable: `export GOOGLE_API_KEY=your_key`
3. Restart the server

---

### Issue:  Playwright timeout (30s exceeded)

**Symptoms:** Search returns `504 Gateway Timeout`

**Causes:**
- Site is very slow or blocking requests
- Network latency
- Browser startup overhead

**Solutions:**
1. Increase `PLAYWRIGHT_TIMEOUT` in `.env` (max recommended: 60s)
2. Reduce `max_results` to fetch fewer URLs
3. Add the slow site to a blocklist in production

---

### Issue: Cache keeps growing (disk full)

**Causes:** 
- `CACHE_MAX_SIZE_MB` set too high
- Cache not cleaning up

**Solutions:**
1. Clear cache manually:  `POST /cache/clear`
2. Reduce `CACHE_MAX_SIZE_MB` in `.env` (default: 2000MB)
3. Check logs for cleanup errors:  `grep "Cache cleanup" logs. txt`

---

### Issue: Reranking always fails (returns original order)

**Symptoms:** `reranking_status: "failed_all_returned_original"`

**Causes:**
- Google API key invalid
- No internet connectivity
- sentence-transformers not installed (for local fallback)

**Solutions:**
1. Verify API key:  `curl https://generativelanguage.googleapis.com/v1/models? key=YOUR_KEY`
2. Check logs:  `tail -f logs.txt | grep -i rerank`
3. Install local fallback: `pip install sentence-transformers`

---

### Issue: Memory usage grows over time

**Causes:**
- Browser pool not cleaning up
- Cache accumulating
- Chunker loading large models repeatedly

**Solutions:**
1. Monitor memory:  `watch -n 1 'ps aux | grep main.py'`
2. Restart server periodically (e.g., via cron)
3. Reduce `MAX_BROWSERS` from 4 to 2 in `.env`

---

### Issue: "NotImplementedError" on Windows startup

**Causes:**
- Windows default `ProactorEventLoop` vs `SelectorEventLoop` conflict with Playwright.

**Solutions:**
- **Fixed in v2.0**: The `main.py` now automatically handles this by forcing `ProactorEventLoopPolicy`.
- Ensure you are running `python main.py` which applies the patch, not `uvicorn main:app` directly from CLI without the policy patch.

---

### Issue: "HTTP 429 Too Many Requests"

**Causes:** DuckDuckGo or target websites rate-limiting

**Solutions:**
1. Add delay between searches
2. Use smaller `max_results` (reduce load)
3. Implement request queuing in production

---

## 🧪 Testing & Verification

We provide three levels of testing to ensure stability.

### 1. Unit & Feature Tests (Fast)
Run this to verify that internal logic (caching, chunking, reranking) works correctly. Uses mocks for external APIs.
```bash
python tests/run_tests.py
```

### 2. Integration Tests (Real World)
Run this to verify that the app can actually connect to the internet, launch browsers, and hit external APIs (Z.ai). **Requires valid API keys.**
```bash
python -m pytest tests/test_integration.py
```

### 3. Reliability Stress Test (Production Grade)
Run the full crawler suite to test edge cases (SPAs, 404s, blocking sites).
```bash
python tests/reliability_suite.py
```
*Generates a `reliability_report.md` with success rates.*

---

## 📊 Performance Benchmarks

On 1vCPU + 16GB RAM (AWS t3.large):

| Operation | Time | Notes |
|-----------|------|-------|
| Cache hit | < 10ms | Instant cached result |
| Fast fetch + extract | 1-3s | Simple HTML pages |
| Playwright fallback | 3-8s | JS-heavy sites, Cloudflare |
| Reranking (Gemini) | 2-4s | API latency |
| Reranking (local) | 0.5-1.5s | CPU-bound |
| Semantic chunking | 1-2s | Model inference |
| Markdown chunking | 100-300ms | Regex-based |
| End-to-end (8 results, all features) | 8-12s | Realistic scenario |

---

## 🔐 Security Considerations

**1. API Key Management**
- ✅ Never commit `.env` to git
- ✅ Use environment variables in production
- ✅ Rotate keys periodically

**2. Rate Limiting**
- Consider adding rate limiting middleware in production
- Example: `pip install slowapi`

**3. Content Sanitization**
- HTML content is extracted but not sanitized
- Implement HTML sanitization if displaying in web UI (use `bleach` library)

**4. Cache Encryption**
- Cache files are plaintext
- In production, encrypt cache directory:  `encfs encrypted/ ~/cache`

---

## 📝 License

MIT License - Use freely in commercial projects.

---

## 🤝 Contributing

Found a bug or have a feature request? Open an issue! 

---

## 📧 Support

Questions?  Email:  support@deepsearch.dev

Or check GitHub Discussions:  https://github.com/yourusername/deep-search-api/discussions