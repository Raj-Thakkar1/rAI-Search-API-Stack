# QUICKSTART.md — Get rAI Search Running in 5 Minutes

This guide assumes you have **Python 3.11+** and **git** installed.

---

## Step 1: Clone and Enter Directory (30 seconds)

```bash
git clone https://github.com/Raj-Thakkar1/rAI-Search-API-Stack.git
cd rAI-Search-API-Stack
```

---

## Step 2: Set Up Environment Variables (1 minute)

### Option A: Create a `.env` file (Recommended for local development)

```bash
cat > .env << 'EOF'
GOOGLE_API_KEY="your-google-api-key-here"
CACHE_ENABLED="true"
CACHE_DIR="./cache"
CACHE_TTL="86400"
CACHE_MAX_SIZE_MB="2000"
PLAYWRIGHT_TIMEOUT="30"
MAX_BROWSERS="4"
SEARCH_TIMEOUT="30"
RERANKER_USE_CLOUD="true"
CHUNKING_STRATEGY="hybrid"
CHUNK_SIZE="350"
DEBUG="false"
EOF
```

Then edit `.env` and replace `your-google-api-key-here` with your actual Google API key.

### Option B: Export directly (Quick test)

```bash
export GOOGLE_API_KEY="your-google-api-key"
export CACHE_ENABLED="true"
export DEBUG="false"
```

### Getting a Google API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Click "Create API Key"
3. Copy the key and paste into `.env` or terminal

**⚠️ Keep your API key secret!** Never commit it to version control.

---

## Step 3: Install Dependencies (2 minutes)

### Python Virtual Environment (Recommended)

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Or, Install Globally (Less recommended)

```bash
pip install -r requirements.txt
```

### Playwright Setup

Playwright needs browser binaries. Install them:

```bash
playwright install chromium
```

(This downloads ~300MB of Chromium; may take 1-2 minutes on first run)

---

## Step 4: Start the API (30 seconds)

```bash
python main.py
```
*Do not use `uvicorn main:app` directly from the CLI on Windows. `python main.py` ensures the correct AsyncIO event loop is loaded for Playwright.*

---

## ✅ Verification

Expected output:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

The API is now running at `http://localhost:8000`

---

## Step 5: Test with a Simple Query (1 minute)

Open a **new terminal** (keep the first one running) and test:

### Basic Search (No reranking or chunking)

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what is Python async/await",
    "max_results": 3,
    "enable_reranking": false,
    "enable_chunking": false,
    "enable_synthesis": false
  }'
```

Expected response structure (JSON):

```json
{
  "query": "what is Python async/await",
  "subqueries": ["what is Python async/await"],
  "answer": null,
  "sources": [
    {
      "id": 1,
      "url": "https://...",
      "title": "...",
      "score": null
    }
  ],
  "total_results": 3,
  "results": [
    {
      "url": "...",
      "title": "...",
      "content_markdown": "...",
      "chunks": null,
      "images": [],
      "videos": [],
      "reranking_score": null
    }
  ],
  "search_timestamp": "2026-01-22T...",
  "search_duration_seconds": 2.45,
  "reranking_enabled": false,
  "cache_hit": false
}
```

### Full-Featured Search (All features enabled)

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compare React vs Vue for web development",
    "max_results": 5,
    "enable_reranking": true,
    "rerank_top_k": 5,
    "enable_chunking": true,
    "chunking_strategy": "hybrid",
    "enable_synthesis": false
  }' | python -m json.tool
```

This will:
1. Search for both "React" and "Vue" (auto-deconstructed)
2. Rerank results by semantic relevance
3. Chunk each result into RAG-ready segments
4. Return sources with reranking scores

### Check Cache Stats

```bash
curl http://localhost:8000/cache/stats | python -m json.tool
```

Response:

```json
{
  "stats": {
    "total_entries": 2,
    "total_size_mb": 0.5,
    "hit_count": 0,
    "miss_count": 2,
    "hit_rate": 0.0,
    "oldest_entry": "2026-01-22T...",
    "newest_entry": "2026-01-22T..."
  },
  "timestamp": "2026-01-22T..."
}
```

### Health Check

```bash
curl http://localhost:8000/health | python -m json.tool
```

Response:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-22T...",
  "config": {
    "cache_enabled": true,
    "reranking_enabled": true,
    "browser_fallback_enabled": true
  }
}
```

---

## Step 6: Verify System Health

### ✅ Expected Behavior

- **First query**: Takes 5-15 seconds (network + Playwright fallback if needed)
- **Second identical query**: <100ms (cache hit)
- **Reranking**: Adds 2-4 seconds for cloud embeddings
- **Chunking**: Adds <1 second for hybrid strategy
- **Log output**: Should show `INFO` and `DEBUG` messages, no errors

### ❌ Common Setup Mistakes

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install -r requirements.txt` in the correct virtualenv |
| `GOOGLE_API_KEY missing` | Check `.env` file exists and has your key (no spaces around `=`) |
| `Playwright timeout for {url}` | Normal for heavy JS sites; increase `PLAYWRIGHT_TIMEOUT` to 60 if needed |
| `ModuleNotFoundError: No module named 'playwright'` | Run `pip install playwright && playwright install chromium` |
| `Connection refused` on port 8000 | Check if another service is using port 8000: `lsof -i :8000` |
| Cache growing too large | Run `curl -X POST http://localhost:8000/cache/clear` |

---

## Next Steps

### Ready to Deploy?

- See **[DEPLOYMENT.md](DEPLOYMENT.md)** for Docker, production tuning, and scaling

### Want to Understand the Architecture?

- See **[FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md)** for how each component works

### Explore the Full API?

- See **[USAGE_GUIDE.md](USAGE_GUIDE.md)** for all endpoints and parameters
- Interactive API docs at `http://localhost:8000/docs` (Swagger UI)

### Run Tests?

- See **[TESTING.md](TESTING.md)** for how to run integration tests

---

## Docker Quick Start (Alternative)

If you prefer Docker:

**Linux/Mac (Curl):**
```bash
# Build image
docker build -t rai-search-api:latest .

# Run container
docker run -e GOOGLE_API_KEY="your-key" \
  -p 8000:8000 \
  -v rai-cache:/app/cache \
  rai-search-api:latest

# Or use docker-compose
docker-compose up --build
```

API will be at `http://localhost:8000`

---

## Rate Limiting

Default: **30 requests per minute** (configurable).

If you hit the limit, you'll get:

```json
{
  "detail": "Rate limit exceeded: 30 per 1 minute"
}
```

Adjust in `.env` or via reverse proxy (nginx, CloudFlare).

---

## Troubleshooting

### "Connection refused" on first request

**Cause**: API is still starting  
**Fix**: Wait 10 seconds, API initialization includes Playwright browser pool setup

### "GOOGLE_API_KEY is invalid"

**Cause**: Typo or expired key  
**Fix**: Double-check your key at [Google AI Studio](https://aistudio.google.com/app/apikeys)

### Searches are very slow (>30 seconds)

**Cause**: Playwright fallback kicking in; network latency; slow target sites  
**Fix**: Increase `SEARCH_TIMEOUT` to 60 seconds in `.env` or check your internet speed

### Memory usage growing unbounded

**Cause**: Cache filling up; browser pool not cleaned  
**Fix**: Set `CACHE_MAX_SIZE_MB` to a lower value, or run `curl -X POST http://localhost:8000/cache/clear`

### Reranking returns original order

**Cause**: Fallback mode (local embedding failed or API key invalid)  
**Fix**: Check `GOOGLE_API_KEY`, or run locally without cloud: set `RERANKER_USE_CLOUD="false"`

---

## Success Criteria

✅ You're ready when:

1. `python main.py` starts without errors
2. `curl http://localhost:8000/health` returns `"status": "healthy"`
3. A search query returns results in <20 seconds
4. Second identical query returns in <100ms (cache hit)

---

## Next Documentation

- **[README.md](README.md)** — Project overview and vision
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** — Full API reference
- **[FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md)** — Architecture and design
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production deployment

---

**Questions?** Open an issue on [GitHub](https://github.com/Raj-Thakkar1/rAI-Search-API-Stack/issues)

**Last Updated**: January 2026
