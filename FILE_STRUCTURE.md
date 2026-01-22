# FILE_STRUCTURE.md — Project Directory Map

---

## Directory Tree

```
rAI-Search-API-Stack/
│
├── 📄 main.py                      # FastAPI application & orchestration
├── 📄 config.py                    # Configuration management (env vars)
├── 📄 browser_fallback.py          # Playwright tiered fetching
├── 📄 cache_manager.py             # File-based caching system
├── 📄 embeddings.py                # Reranking & embedding services
├── 📄 rag_chunker.py              # RAG-ready document chunking
├── 📄 reranker.py                 # Reranking orchestration
├── 📄 synthesis.py                # LLM-based answer generation
│
├── 📄 requirements.txt             # Python dependencies
├── 📄 Dockerfile                   # Multi-stage Docker build
├── 📄 docker-compose.yml           # Docker Compose for local dev
│
├── 📄 README.md                    # Project overview
├── 📄 QUICKSTART.md                # 5-minute setup guide
├── 📄 USAGE_GUIDE.md               # Full API reference
├── 📄 FEATURES_IN_DEPTH.md         # Architecture & design
├── 📄 FILE_STRUCTURE.md            # This file
├── 📄 DEPLOYMENT.md                # Production deployment
├── 📄 TESTING.md                   # Test suite guide
├── 📄 ARCHITECTURE.md              # System design details
├── 📄 PERFORMANCE.md               # Benchmarks & optimization
├── 📄 LIMITATIONS.md               # Known issues & edge cases
├── 📄 CONTRIBUTING.md              # Developer guidelines
│
├── 📁 schemas/                     # JSON schemas
│   └── answer-engine-response.schema.json
│
├── 📁 tests/                       # Test suite
│   ├── run_tests.py                # Test runner
│   ├── test_features.py            # Unit tests
│   ├── test_integration.py         # Integration tests
│   └── test_server.py              # API endpoint tests
│
└── 📁 cache/                       # Cache directory (created at runtime)
    ├── .cache_stats.json           # Cache statistics
    └── *.json                      # Cached search results
```

---

## Core Modules

### `main.py` — FastAPI Application (1129 lines)

**Responsibilities**:
- FastAPI app initialization & configuration
- HTTP endpoints (`/search`, `/cache/stats`, `/health`, etc.)
- Request/response validation & serialization
- Orchestration of all components
- Error handling & logging
- Rate limiting via SlowAPI

**Key Classes**:
- `SearchService`: DuckDuckGo search wrapper
- `ExtractionWorker`: Multiprocess HTML parsing
- `SearchOrchestrator`: Coordinates all components
- `AnswerEngine`: Main pipeline orchestrator

**Key Functions**:
- `search()`: POST endpoint for searches
- `get_cache_stats()`: GET cache statistics
- `clear_cache()`: POST to clear cache
- `health_check()`: GET health status

**Dependencies**: FastAPI, uvicorn, slowapi, all other modules

---

### `config.py` — Configuration Management (104 lines)

**Responsibilities**:
- Load configuration from environment variables
- Define configuration schema with validation
- Provide defaults for all settings

**Key Classes**:
- `GoogleEmbeddingConfig`: Gemini embedding settings
- `GoogleFallbackConfig`: Gemma fallback LLM
- `PlaywrightConfig`: Browser automation settings
- `CacheConfig`: Cache behavior
- `ChunkingConfig`: RAG chunking strategy
- `RerankerConfig`: Reranking settings
- `SearchConfig`: Search behavior
- `Config`: Master configuration (union of all above)

**Key Functions**:
- `load_config()`: Load from environment, return Config object

**Design**: Pydantic models for validation; environment variables from `.env`

---

### `browser_fallback.py` — Tiered Fetching (167 lines)

**Responsibilities**:
- Manage Playwright browser pool
- Implement tiered fetching (HTTPX → Playwright → Fail)
- Handle timeouts and errors gracefully

**Key Classes**:
- `BrowserPool`: Manages 4 concurrent browser instances
- `TieredFetcher`: Orchestrates tiered fetching

**Key Functions**:
- `fetch_url()`: Main entry point (Tier 1 + Tier 2)
- `fetch_with_js()`: Playwright-based fetch
- `initialize()`: Set up browser pool
- `shutdown()`: Clean up resources

**Design**: Async/await throughout; semaphore for concurrency control

---

### `cache_manager.py` — File-Based Caching (292 lines)

**Responsibilities**:
- Read/write cache entries to disk
- TTL-based expiration
- Content deduplication via SHA-256
- Cache statistics tracking

**Key Classes**:
- `CacheEntry`: Single cache entry with metadata
- `CacheStats`: Cache statistics DTO
- `FileBasedCache`: Main caching service

**Key Methods**:
- `get()`: Retrieve from cache; check expiration
- `set()`: Store in cache; update stats
- `clear()`: Delete all cache
- `get_stats()`: Return cache statistics

**Design**: Persistent JSON files; SHA-256 keys for deduplication

---

### `embeddings.py` — Reranking Services (293 lines)

**Responsibilities**:
- Google Gemini embedding API integration
- Local cross-encoder fallback
- Gemma fallback LLM

**Key Classes**:
- `EmbeddingProvider`: Abstract base for embedding services
- `GoogleGeminiEmbedding`: Cloud embeddings (primary)
- `LocalCrossEncoderEmbedding`: Local embeddings (fallback)
- `GemmaFallbackReranker`: LLM-based fallback

**Key Methods**:
- `embed_texts()`: Generate embeddings
- `rerank()`: Return relevance scores

**Design**: Multi-tier with graceful fallback

---

### `rag_chunker.py` — Document Chunking (326 lines)

**Responsibilities**:
- Split documents into chunks for RAG
- Support markdown, semantic, and hybrid strategies
- Token counting via tiktoken
- Preserve source section metadata

**Key Classes**:
- `Chunk`: Single RAG-ready chunk
- `ChunkingResult`: Result of chunking operation
- `RAGChunker`: Main chunking orchestrator

**Key Strategies**:
- `_chunk_markdown()`: Header-based splitting
- `_chunk_semantic()`: Similarity-based grouping
- `_chunk_hybrid()`: Semantic with fallback

**Design**: Tiktoken integration; fallback if unavailable

---

### `reranker.py` — Reranking Orchestration (154 lines)

**Responsibilities**:
- Coordinate multi-tier reranking
- Handle failures gracefully
- Return ranked results with scores

**Key Classes**:
- `RerankerStatus`: Enum for status
- `RerankerResponse`: DTO for response
- `SemanticReranker`: Main orchestrator

**Key Methods**:
- `rerank()`: Entry point

**Design**: Multi-provider pattern; graceful fallback on failure

---

### `synthesis.py` — LLM Answer Generation (279 lines)

**Responsibilities**:
- Generate answers with inline citations
- Support multiple LLM providers
- Streaming and batch modes

**Key Classes**:
- `SynthesisChunk`: Chunk for synthesis input
- `SynthesisProvider`: Abstract base
- `GeminiSynthesisProvider`: Google Gemini
- `OpenAISynthesisProvider`: OpenAI
- `ZaiSynthesisProvider`: Zai (OpenAI-compatible)
- `SynthesisService`: Orchestrator

**Key Methods**:
- `stream()`: Async generator for streaming
- `generate()`: Batch generation

**Design**: Multi-provider; streaming support

---

## Configuration Files

### `requirements.txt`

Python dependencies pinned to specific versions:
- FastAPI, uvicorn (web framework)
- Playwright, trafilatura, lxml (fetching)
- Google Generative AI, sentence-transformers (embeddings)
- tiktoken (token counting)
- httpx (HTTP client)
- slowapi (rate limiting)
- python-dotenv (environment loading)
- pytest, black, flake8 (development)

### `Dockerfile`

Multi-stage build:
- **Stage 1**: Build Python venv with dependencies
- **Stage 2**: Runtime image based on Playwright image (includes browsers)
- Exposes port 8000
- Runs `uvicorn main:app`

### `docker-compose.yml`

Local development setup:
- Single service `deep-search-api`
- Volume mounts for cache persistence
- Environment variables
- Health check
- Resource limits (1 vCPU, 14GB RAM)

---

## Schemas

### `schemas/answer-engine-response.schema.json`

JSON Schema for response validation:
- Defines structure of `AnswerEngineResponse`
- Used for validation and documentation
- Can be retrieved via `GET /schemas/answer-engine-response`

---

## Test Suite

### `tests/run_tests.py`

Test runner script:
- Runs unit tests in `test_features.py`
- Can be run directly: `python tests/run_tests.py`

### `tests/test_features.py`

Unit tests for individual components:
- `test_cache_get_set()`: Cache operations
- `test_chunking()`: RAG chunking
- `test_reranking()`: Reranking logic
- `test_extraction()`: Content extraction
- etc.

### `tests/test_integration.py`

Integration tests with real APIs:
- Tests full pipeline end-to-end
- Uses DuckDuckGo, real websites
- Can be slow (30-60s)
- Run with: `pytest tests/test_integration.py`

### `tests/test_server.py`

HTTP endpoint tests:
- Tests `/search`, `/health`, `/cache/stats` endpoints
- Uses test client
- Can be run with: `pytest tests/test_server.py`

---

## Cache Directory

Generated at runtime if `CACHE_ENABLED=true`:

```
cache/
├── .cache_stats.json
│   └── {"hit_count": 45, "miss_count": 12, "last_updated": "..."}
│
└── [SHA256 hashes].json
    └── {
          "key": "search:abc123...",
          "data": {...full response...},
          "timestamp": "2026-01-22T14:30:00Z",
          "ttl_seconds": 86400,
          "size_bytes": 125000,
          "content_hash": "def456..."
        }
```

---

## Data Flow Between Modules

```
┌──────────────────────────────────┐
│ main.py (FastAPI Entry Point)    │
│ ├─ POST /search                  │
│ └─ Instantiate SearchOrchestrator│
└──────────────┬───────────────────┘
               ↓
        [Check cache]
          ↙         ↘
      HIT         MISS
       ↓            ↓
    Return    ┌──────────────────┐
              │ SearchService    │
              │ (DuckDuckGo)     │
              └────────┬─────────┘
                       ↓
            ┌──────────────────────┐
            │ TieredFetcher        │
            │ (browser_fallback)   │
            └────────┬─────────────┘
                     ↓
        ┌─────────────────────────┐
        │ ExtractionWorker (LXML) │
        └────────┬────────────────┘
                 ↓
      ┌────────────────────────┐
      │ SemanticReranker       │ (optional)
      │ (reranker.py)          │
      └──────┬─────────────────┘
             ↓
  ┌──────────────────────────┐
  │ RAGChunker               │ (optional)
  │ (rag_chunker.py)         │
  └──────┬───────────────────┘
         ↓
┌─────────────────────────┐
│ SynthesisService        │ (optional)
│ (synthesis.py)          │
└──────┬──────────────────┘
       ↓
   [Cache Write]
   (cache_manager.py)
       ↓
   Return Response
```

---

## Where to Add New Features

| Feature | File(s) | Notes |
|---------|---------|-------|
| New search backend (not DDG) | `main.py`, new `SearchService` | Implement same interface |
| New fetching strategy | `browser_fallback.py` | Add tier, update `TieredFetcher` |
| New cache backend (Redis) | `cache_manager.py` | Implement `FileBasedCache` interface |
| New reranker | `reranker.py`, `embeddings.py` | Add provider class |
| New LLM provider for synthesis | `synthesis.py` | Implement `SynthesisProvider` |
| New endpoint | `main.py` | Add route with FastAPI decorator |
| New configuration option | `config.py` | Add to Config class, load in `load_config()` |

---

## Where to Configure Behavior

| Setting | File | Default | How to Change |
|---------|------|---------|---|
| Max results | `config.py` → `SearchConfig` | 20 | `SEARCH_TIMEOUT` env var |
| Cache TTL | `config.py` → `CacheConfig` | 86400s | `CACHE_TTL` env var |
| Chunking strategy | `config.py` → `ChunkingConfig` | "hybrid" | `CHUNKING_STRATEGY` env var |
| Browser timeout | `config.py` → `PlaywrightConfig` | 30s | `PLAYWRIGHT_TIMEOUT` env var |
| Rate limit | `main.py` line ~50 | 30/min | `RATE_LIMIT` env var or code |
| Google API key | `config.py` | from env | `GOOGLE_API_KEY` env var |
| Debug logging | `config.py` → `Config` | False | `DEBUG=true` env var |

---

## Code Style & Conventions

- **Python**: PEP 8 (black formatter)
- **Async**: Use `async/await` consistently
- **Error Handling**: Log and gracefully degrade
- **Type Hints**: Annotate function signatures
- **Docstrings**: Module and class level
- **Logging**: Use `logger.info()`, `logger.error()`, etc.

---

## Development Workflow

1. **Understand Architecture**: Read [FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md)
2. **Understand Endpoints**: Read [USAGE_GUIDE.md](USAGE_GUIDE.md)
3. **Make Changes**: Edit relevant file(s)
4. **Test Locally**: `python main.py` and test with curl
5. **Run Tests**: `pytest tests/`
6. **Format Code**: `black .`
7. **Lint**: `flake8 .`
8. **Commit**: Push to branch, create PR

---

**Next**: See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup, or [TESTING.md](TESTING.md) for testing guidelines.

**Last Updated**: January 2026
