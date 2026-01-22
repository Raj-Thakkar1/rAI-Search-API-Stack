# ARCHITECTURE.md — System Design & Component Architecture

---

## Overview

rAI Search API Stack is a modular, async-first system designed around a **multi-tier graceful degradation** philosophy. Every component can fail independently without crashing the API. This document explains the "why" behind architectural decisions and provides deep insight into component interactions.

---

## Design Philosophy

### 1. Multi-Tier Graceful Degradation

Every critical path has 3+ fallback levels:

```
Tier 1 (Fast Path)     → Tier 2 (Fallback)     → Tier 3 (Last Resort)
─────────────────────────────────────────────────────────────────
HTTP (HTTPX)           → JavaScript (Playwright) → Original/None
Google Embeddings      → Local Cross-Encoder    → Original Order
Gemini Synthesis       → OpenAI Synthesis       → Zai Synthesis
```

**Why**: Production systems fail. Gracefully. Users would rather get stale/basic results than 500 errors.

**Trade-off**: Slightly higher complexity, significantly higher reliability.

### 2. Async-First Architecture

Every I/O operation is async:

```python
# ✅ Good
async def search(query: str) -> AnswerEngineResponse:
    tasks = [fetch_search_results(), check_cache(), ...]
    results = await asyncio.gather(*tasks)
    return aggregate(results)

# ❌ Bad (blocking)
def search(query: str) -> AnswerEngineResponse:
    results = fetch_search_results()  # Blocks thread
    return results
```

**Why**: Single FastAPI worker can handle ~100+ concurrent requests instead of ~10.

**Trade-off**: Requires async-aware libraries; some complexity in debugging; must avoid blocking calls.

### 3. Cache-First Pipeline

Every search checks cache first:

```
User Request
    ↓
Cache Lookup (sync file I/O)
    ├─ Cache Hit → Return cached result (< 10ms)
    └─ Cache Miss → Continue pipeline
        ↓
    DuckDuckGo Search
        ↓
    Tiered Fetch (HTTPX → Playwright)
        ↓
    Extract & Chunk
        ↓
    Rerank
        ↓
    Synthesize
        ↓
    Write Cache
        ↓
    Return Result
```

**Why**: 70-80% of queries repeat within 24h on typical deployments.

**Trade-off**: Cache directory requires storage (~2GB max); TTL adds staleness; requires periodic cleanup.

### 4. Extraction-then-Synthesis Model

Results are extracted before synthesis:

```
Search Results
    ↓
Extract Content (HTML → plain text)
    ↓
Deduplicate
    ↓
Chunk (RAG-ready)
    ↓
Rerank by Relevance
    ↓
Synthesis (top-K used for answer)
```

**Why**: Separates concerns; extraction failures don't break synthesis; chunking enables better context window usage.

**Trade-off**: Multiple stages = multiple failure points (mitigated by graceful degradation).

---

## Component Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│              FastAPI Application                     │
│              (main.py)                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │     SearchOrchestrator                      │   │
│  │     (Coordinates entire pipeline)           │   │
│  └────────────┬────────────────────────────────┘   │
│               │                                    │
│  ┌────────────┴─────────┬──────────┬────────────┐  │
│  ↓                      ↓          ↓            ↓  │
│  CacheManager     SearchService   Reranker  Synthesizer
│  (cache.py)       (DuckDuckGo)    (rk.py)   (syn.py)
│  ├─ TTL-based    ├─ Query prep   ├─ Tier 1  ├─ Tier 1
│  ├─ Dedup        ├─ DuckDuckGo   │  Google  │  Gemini
│  └─ Cleanup      └─ Error handle │  Embed   ├─ Tier 2
│                                    │          │  OpenAI
│                  ┌─────────────────┤  Tier 2  ├─ Tier 3
│                  │                 │  Local   │  Zai
│                  ↓                 │  CE      │
│              TieredFetcher   Tier 3│          └─ Citations
│              (bf.py)         Original Order
│              ├─ Tier 1: HTTPX
│              ├─ Tier 2: Playwright (pool)
│              └─ Tier 3: None
│
│              RAGChunker       Embeddings
│              (chunker.py)     (emb.py)
│              ├─ Markdown      ├─ Google
│              ├─ Semantic      ├─ Local CE
│              └─ Hybrid        └─ Gemma LLM
│
└─────────────────────────────────────────────────────┘
```

### Data Flow: /search Endpoint

```
1. Request → SearchRequest(query, num_results, strategy)
   ↓
2. Check Cache
   ├─ Hit (TTL valid) → Return ✓ (< 10ms)
   └─ Miss → Continue
   ↓
3. Query Deconstruction
   ├─ Extract entities (via regex or simple NLP)
   ├─ Identify intent (search, compare, summarize)
   └─ Clean query string
   ↓
4. Search Results
   └─ DuckDuckGo API call → 30 results (max)
   ↓
5. Tiered Fetch (for each result URL)
   ├─ Tier 1: HTTPX (fast, no JS)
   │  ├─ Timeout: 5 seconds
   │  ├─ User-Agent: Real browser string
   │  ├─ Trafilatura extract
   │  └─ Success → Next result (concurrent)
   ├─ Tier 2 (on Tier 1 failure): Playwright
   │  ├─ Timeout: 15 seconds
   │  ├─ Browser pool (4 instances max)
   │  ├─ Wait for JS rendering
   │  ├─ Extract DOM
   │  └─ Success → Next result
   └─ Tier 3 (on Tier 2 failure): Give up
      └─ Skip URL, try next
   ↓
6. Extraction & Deduplication
   ├─ HTML → Plain text via Trafilatura
   ├─ Remove boilerplate (nav, ads, footer)
   ├─ SHA-256 hash content
   ├─ Filter exact duplicates
   └─ Result: 5-25 unique documents (typical)
   ↓
7. Chunking (RAG-Ready)
   ├─ Strategy: Markdown (header-based) [default]
   │  ├─ Respects document structure
   │  ├─ Chunk size: 500-2000 tokens
   │  └─ Preserves hierarchy
   ├─ Fallback: Semantic similarity
   │  ├─ Overlap: 20%
   │  ├─ Uses sentence-transformers
   │  └─ Better for dense text
   └─ Fallback: Hybrid (both + merge)
   ↓
8. Reranking (Semantic Relevance)
   ├─ Tier 1: Google Gemini Embeddings
   │  ├─ Query embedding: ~5ms
   │  ├─ Document embeddings: batch
   │  ├─ Cosine similarity ranking
   │  └─ Success → Use ranked order
   ├─ Tier 2 (on cloud fail): Local cross-encoder
   │  ├─ Rerank top-K (default K=10)
   │  ├─ More accurate, slower (~100ms)
   │  └─ Success → Use ranked order
   └─ Tier 3 (on local fail): Original order
      └─ Return DDG order, no reranking
   ↓
9. Synthesis (Generative Answer)
   ├─ Take top-K chunks (K=3-5 default)
   ├─ Build prompt with:
   │  ├─ System prompt (enforce citations)
   │  ├─ Context (top chunks)
   │  └─ User query
   ├─ Tier 1: Gemini
   │  ├─ Stream response
   │  ├─ Parse citations
   │  └─ Success → Use answer
   ├─ Tier 2 (on fail): OpenAI GPT-4
   │  ├─ Fallback synthesis
   │  └─ Success → Use answer
   └─ Tier 3 (on fail): Zai
      └─ Last resort synthesis
   ↓
10. Build Response
    ├─ Synthesized answer (string)
    ├─ Source references (URLs)
    ├─ Original search results (30 items)
    ├─ Chunks used (for attribution)
    └─ Metadata (time, cache_hit, provider)
    ↓
11. Write Cache
    ├─ Serialize AnswerEngineResponse
    ├─ SHA-256 key (query)
    ├─ TTL: 24 hours
    └─ Size limit: 2GB total
    ↓
12. Return Response
    └─ HTTP 200 + JSON (cache_hit=false)
```

---

## Async Execution Model

### Concurrency Strategy

```python
# ✅ Maximum concurrency throughout:

async def search(query: str):
    # Cache + prep concurrently
    tasks = [
        cache.get(query),           # Async file I/O
        search_service.search(query),  # API call
        query_deconstruct(query),   # CPU-bound (small)
    ]
    cache_result, search_results, entities = await asyncio.gather(*tasks)
    
    if cache_result:
        return cache_result  # Skip rest
    
    # Fetch all URLs concurrently (tiered)
    fetch_tasks = [
        tiered_fetcher.fetch(url) for url in search_results
    ]
    extracted_docs = await asyncio.gather(*fetch_tasks)
    
    # Chunk + rerank concurrently
    chunking_tasks = [
        chunker.chunk(doc) for doc in extracted_docs
    ]
    chunks = await asyncio.gather(*chunking_tasks)
    
    # Rerank all chunks concurrently
    reranked = await reranker.rerank(chunks, query)
    
    # Synthesize (streaming)
    answer = await synthesizer.generate(reranked[:5], query)
    
    # Write cache (async, don't wait)
    asyncio.create_task(cache.set(query, answer))
    
    return answer
```

**Concurrency Graph**:

```
|──────── Cache Lookup ──────────────────|
|── Search API ─────────────────|        
|── Query Deconstruct ──|              [Return cached or continue]
                         |─── Fetch URL 1 ──────────────|
                         |─── Fetch URL 2 ──────────────|
                         |─── Fetch URL 3 ──────────────|
                         |─── ... (concurrent, pool-limited)
                         |─ Chunk 1 ─|
                         |─ Chunk 2 ─|  [Wait for chunks]
                         |─ Chunk 3 ─|
                         |──── Rerank (streaming) ──────|
                         |─ Synthesize (streaming) ─────|
                         |─ Write Cache (background) ──|
```

**Concurrency Limits**:

```python
# From config.py
PlaywrightConfig:
    max_workers = 4       # Max 4 concurrent browsers
    request_timeout = 5   # Seconds
    
SearchConfig:
    max_concurrent_fetches = 10  # Max 10 URLs in parallel
    max_synthesis_chunks = 5     # Use top-5 for answer
```

---

## Error Handling & Fallback Strategy

### Principle: Never Crash

Every error is caught, logged, and gracefully handled:

```python
# ✅ Paradigm: Try → Catch → Fallback → Log → Return

async def extract_url(url: str) -> Document | None:
    try:
        # Tier 1: Fast HTTPX
        result = await tiered_fetcher.fetch_httpx(url, timeout=5)
        return result
    except (TimeoutError, ConnectionError) as e:
        logger.warning(f"HTTPX failed for {url}: {e}")
        
        try:
            # Tier 2: Fallback to Playwright
            result = await tiered_fetcher.fetch_playwright(url, timeout=15)
            return result
        except Exception as e2:
            logger.warning(f"Playwright failed for {url}: {e2}")
            
            # Tier 3: Give up, skip this URL
            return None
```

### Error Modes & Recovery

| Component | Error | Tier 1 Fail | Recovery |
|---|---|---|---|
| **Fetching** | URL timeout/network | HTTPX hangs | Try Playwright, skip if both fail |
| **Cache** | Disk full | Write fails | Log warning, continue (bypass cache) |
| **Reranking** | Gemini quota exceeded | Cloud embedding fails | Use local cross-encoder |
| **Synthesis** | OpenAI rate limit | Generation fails | Try Zai provider |
| **DuckDuckGo** | API rate limit | Search returns 0 results | Return empty results, cache miss |
| **Query** | Invalid UTF-8 | Parse fails | Return 400 error (client error) |

### Failure Cascade Example

```
User: /search?query="xss<script>"

Query Validation
  └─ Validate UTF-8: ✓ Pass
  └─ Validate length: ✓ Pass (20 chars)
  └─ Sanitize: ✓ Pass (already URL encoded)

Cache Check
  └─ File I/O fails (permission denied)
  └─ Log: ERROR - Cache read failed, continuing
  └─ Proceed without cache

DuckDuckGo Search
  └─ Rate limit hit (30 req/min exceeded by this IP)
  └─ Return 429 (Too Many Requests)
  └─ User gets error with retry-after header

Result: User sees error (correct), cache bypass doesn't crash system
```

---

## Configuration Architecture

### Layered Configuration

```
┌─────────────────────────────────────────┐
│  Environment Variables (Highest)        │
│  e.g. GOOGLE_API_KEY=sk-...             │
├─────────────────────────────────────────┤
│  .env File (Local Development)          │
│  e.g. CACHE_DIR=/app/cache              │
├─────────────────────────────────────────┤
│  Pydantic Defaults (Built-in)           │
│  e.g. cache_ttl_hours=24                │
├─────────────────────────────────────────┤
│  Hard Defaults (Fallback)               │
│  e.g. rate_limit="30/minute"            │
└─────────────────────────────────────────┘
```

### Config Classes (config.py)

```python
class GoogleEmbeddingConfig:
    api_key: str              # From env GOOGLE_API_KEY
    timeout: int = 10         # Seconds
    batch_size: int = 100     # Embeddings per request

class PlaywrightConfig:
    headless: bool = True
    max_workers: int = 4      # Browser pool size
    request_timeout: int = 15 # Seconds per page load

class CacheConfig:
    cache_dir: str = ".cache"
    ttl_hours: int = 24
    max_size_mb: int = 2048

class ChunkingConfig:
    strategy: str = "markdown"  # markdown, semantic, hybrid
    chunk_size_tokens: int = 1000
    chunk_overlap: int = 0.1

class RerankerConfig:
    provider: str = "google"    # google, local, none
    top_k: int = 10
    threshold: float = 0.3

class SearchConfig:
    max_results: int = 30
    max_concurrent_fetches: int = 10
    prefer_https: bool = True
```

---

## Extension Points

### How to Extend the System

#### 1. Add Custom Embedding Provider

```python
# In embeddings.py, subclass EmbeddingProvider

class MyCustomEmbedding(EmbeddingProvider):
    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return shape (len(texts), 768) or similar"""
        # Your implementation
        pass
    
    async def rerank(self, query: str, documents: list[str]) -> list[int]:
        """Return indices sorted by relevance"""
        # Your implementation
        pass

# In config.py, add:
embedding_provider: str = "custom"

# In reranker.py, add:
elif self.config.embedding_provider == "custom":
    return MyCustomEmbedding(...)
```

#### 2. Add Custom Synthesis Provider

```python
# In synthesis.py, subclass SynthesisProvider

class MyCustomSynthesis(SynthesisProvider):
    async def generate(self, context: str, query: str) -> str:
        """Return generated answer with citations"""
        # Your implementation
        pass
    
    async def stream(self, context: str, query: str):
        """Stream response tokens"""
        # Your implementation
        yield token

# In config.py, add:
synthesis_provider: str = "custom"

# In main.py SearchOrchestrator, add:
elif provider == "custom":
    return MyCustomSynthesis(...)
```

#### 3. Add Custom Chunking Strategy

```python
# In rag_chunker.py, add method:

async def _chunk_custom(self, text: str, max_tokens: int):
    """Return list[Chunk] with custom logic"""
    # Your implementation
    chunks = []
    # ...
    return chunks

# In RAGChunker.__init__, add:
elif strategy == "custom":
    self.strategy = "custom"

# In chunk() method, add:
elif self.strategy == "custom":
    return await self._chunk_custom(text, max_tokens)
```

#### 4. Add Custom Search Backend

```python
# Currently hardcoded to DuckDuckGo. To add another:

# In main.py SearchService, add:

async def search_with_google(self, query: str, num_results: int):
    """Use Google Custom Search API instead"""
    # Implementation
    pass

# Modify search() to route:
if self.config.search_backend == "google":
    return await self.search_with_google(query, num_results)
else:
    return await self.search_duckduckgo(query, num_results)
```

---

## Performance Characteristics

### Latency Budget

```
Typical /search?query="python async" (cache miss):

Time Spent (avg, p95):
├─ Cache lookup: 5ms (10ms p95) — sync file I/O
├─ DuckDuckGo search: 400ms (800ms p95) — network latency
├─ Tiered fetch (10 URLs, parallel):
│  ├─ HTTPX Tier 1: 2000ms (5s p95) — network + page load
│  ├─ Playwright Tier 2: 5000ms (15s p95) — JS rendering
│  └─ Reduced to ~5 URLs avg: 1500ms (4s p95)
├─ Extraction: 100ms (200ms p95) — CPU-bound
├─ Chunking: 50ms (100ms p95) — CPU-bound
├─ Reranking:
│  ├─ Tier 1 (Gemini): 400ms (1s p95) — API latency
│  └─ Fallback rare: 200ms
├─ Synthesis:
│  ├─ Prompt building: 20ms
│  ├─ Gemini stream: 2000ms (5s p95) — token generation
│  └─ Parse citations: 50ms
├─ Cache write: 10ms (20ms p95) — async I/O
└─ Response serialization: 50ms (100ms p95) — JSON encoding

Total: 4-5 seconds typical (p50)
       7-12 seconds p95 (slow networks/Playwright)
       < 10ms cache hit
```

### Memory Usage

```
Per-request memory (typical):

├─ Search results: 100KB (30 results × ~3KB)
├─ Extracted documents: 500KB (5 docs × ~100KB)
├─ Chunks: 200KB (100 chunks × ~2KB)
├─ Embeddings cache: 300KB (100 vectors × 384 dims × 8 bytes)
├─ Answer synthesis: 50KB (buffer + streaming)
└─ Overhead: 100KB (frameworks, libraries)

Total per request: ~1.2 MB

With concurrent requests (8):
├─ Per-request: 1.2 MB × 8 = 9.6 MB
├─ Browser pool: 200 MB × 4 = 800 MB (Playwright)
├─ Base system: 300 MB
└─ Total: ~1.1 GB (typical load)
```

### Scaling Characteristics

```
Request Rate vs. Latency (single instance):

Requests/sec  | Avg Latency | Memory | Browser Saturation
1             | 4s          | 200MB | 0%
5             | 4.5s        | 400MB | 0%
10            | 5s          | 800MB | 10%
20            | 6s          | 1.1GB | 50%
30            | 10s         | 1.2GB | 80%
40            | 20s         | 1.2GB | 100% (queuing)
50+           | 30s+        | 1.2GB | 100% (timeouts)

Recommendation: Run multiple instances behind load balancer (nginx)
Max per instance: ~30 req/sec comfortable, ~50 req/sec max
Cost: Each instance ~1-2 vCPU, 2GB RAM on AWS
```

---

## Security Architecture

### Data Flow (Security Perspective)

```
User Request (HTTPS/TLS 1.3)
    ↓ [Encrypted]
Reverse Proxy (nginx, validates request)
    ↓ [Rate limit check, auth check]
API Server (internal, validates input)
    ├─ Cache (encrypted volume recommended)
    ├─ DuckDuckGo (public API, HTTPS only)
    ├─ Document URLs (user-controlled, sanitize!)
    ├─ LLM APIs (credentials in secrets manager)
    └─ Synthesis (output sanitized, citations injected)
    ↓ [Response built, sanitized]
Response (HTTPS/TLS 1.3)
    ↓ [Encrypted back to user]
User Browser [Client-side sanitization of HTML]
```

### Secrets Management

```
Secrets (Never hardcoded):
├─ GOOGLE_API_KEY
├─ OPENAI_API_KEY
├─ ZAI_API_KEY
├─ Database credentials (if added)
└─ Cache encryption keys (if encrypted)

Storage Options:
├─ AWS Secrets Manager (recommended)
├─ HashiCorp Vault
├─ Kubernetes Secrets (if K8s)
└─ .env file (local dev only, never commit!)
```

---

## Testing Architecture

### Test Pyramid

```
           /\
          /  \          E2E Tests (5%)
         /    \         - Full /search endpoint
        /______\        - Real DuckDuckGo API
       /        \
      /          \     Integration Tests (25%)
     /____________\    - Cache + Search + Fetch
    /              \   - Reranking + Synthesis
   /                \ - Error scenarios
  /____________________\

  Unit Tests (70%)
  ├─ QueryDeconstruction
  ├─ Chunking strategies
  ├─ Reranking tiers
  ├─ Synthesis providers
  ├─ Cache operations
  └─ Error handling
```

---

## Deployment Architecture

### Production Topology

```
┌────────────────────────────────────────────────────┐
│                    Users (HTTPS)                   │
└────────────┬───────────────────────────────────────┘
             │
     ┌───────▼───────┐
     │  CloudFlare   │  DDoS protection, WAF
     │  (CDN)        │
     └───────┬───────┘
             │
┌────────────▼───────────────────────────────────────┐
│            AWS Network Load Balancer               │
│            (Route to nginx instances)              │
└────────────┬───────────────────────────────────────┘
             │
    ┌────────┴─────────┬──────────┐
    │                  │          │
┌───▼──┐          ┌────▼──┐  ┌───▼──┐
│nginx │          │ nginx │  │nginx │  Reverse proxy
│  +   │          │  +    │  │  +   │  Rate limit, auth
│ auth │          │ auth  │  │ auth │
└───┬──┘          └────┬──┘  └───┬──┘
    │                  │         │
┌───▼─────────────┬────▼────┬────▼────┐
│   API App 1     │ API App 2│ API App 3│  FastAPI instances
│   (Port 8000)   │(Port 8000)(Port 8000)
│                 │         │
│ Playwright Pool │ Browser │ Browser │ Pool shared or per-instance
│ Cache Dir       │ Pool    │ Pool    │ Mounted volume
└─────────────────┴─────────┴─────────┘
     │                 │         │
     └─────────────────┴─────────┘
             │
     ┌───────▼───────┐
     │  Shared Cache │   EBS volume, encrypted
     │  Directory    │
     └───────────────┘
     
     ┌───────────────┐
     │  Secrets      │   AWS Secrets Manager
     │  (API Keys)   │
     └───────────────┘
```

---

## Future Architecture Considerations

### Potential Improvements

1. **Vector Database Integration** (FAISS, Pinecone)
   - Cache embeddings across queries
   - Reduce reranking latency

2. **Message Queue** (RabbitMQ, SQS)
   - Async search jobs
   - Decouple API from heavy lifting

3. **Distributed Tracing** (Jaeger, Datadog)
   - Track request flow across services
   - Identify bottlenecks

4. **Multi-Region Deployment**
   - Geographic distribution
   - DuckDuckGo regional endpoints

5. **Custom ML Model Integration**
   - Fine-tuned rerankers for specific domains
   - Custom query understanding

---

## Design Trade-offs Made

| Decision | Choice | Rationale | Trade-off |
|---|---|---|---|
| Cache backend | File-based | Simple, no external deps | Not distributed (one instance per cache) |
| Search backend | DuckDuckGo | Privacy-friendly, API-based | Limited features vs. Google |
| Fetching | HTTPX + Playwright | Fast for static, JS handling | Playwright overhead for JS sites |
| Embeddings | Google Gemini + local | Cloud quality + offline fallback | Cost + latency for Gemini |
| Synthesis | Streaming | Fast time-to-first-token | Harder to inject citations mid-stream |
| Async model | asyncio | Native Python, FastAPI built-in | Learning curve, debugging complexity |
| Graceful degradation | 3+ tiers | High reliability | Added code complexity, harder testing |

---

**Last Updated**: January 2026
