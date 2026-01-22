# USAGE_GUIDE.md — Complete API Reference

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Request & Response Schemas](#request--response-schemas)
5. [Configuration](#configuration)
6. [Error Handling](#error-handling)
7. [Performance Notes](#performance-notes)
8. [Security Considerations](#security-considerations)

---

## Overview

The rAI Search API is a RESTful service built with FastAPI that provides semantic search, intelligent fetching, reranking, RAG chunking, and generative synthesis.

**Base URL**: `http://localhost:8000`  
**API Version**: v3.0  
**Protocol**: HTTP/REST with JSON bodies  
**Rate Limit**: 30 requests/minute (configurable)  
**Timeout**: 30 seconds per search (configurable)

---

## Authentication

**Current**: No authentication layer (this is your responsibility to add).

### Recommended for Production

```nginx
# Example: nginx reverse proxy with basic auth
server {
    listen 443 ssl;
    
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

Or use JWT middleware, API keys, or OAuth2 with a reverse proxy.

---

## Endpoints

### 1. POST `/search` — Main Search Endpoint

**Purpose**: Execute a semantic search with optional reranking, chunking, and synthesis.

**URL**: `POST /search`

**Rate Limit**: 30/minute

**Timeout**: 30 seconds (configurable)

**Request Body** (JSON):

```json
{
  "query": "what are the benefits of async programming in Python",
  "max_results": 5,
  "deep_extract": true,
  "stream": false,
  "deconstruct_query": true,
  "max_subqueries": 3,
  "enable_synthesis": false,
  "synthesis_top_k_chunks": 12,
  "enable_reranking": true,
  "rerank_top_k": 5,
  "enable_chunking": true,
  "chunking_strategy": "hybrid",
  "target_chunk_size": 350
}
```

**Parameter Details**:

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|---|
| `query` | string | (required) | 1-500 chars | Search query |
| `max_results` | integer | 5 | 1-20 | Number of results to fetch |
| `deep_extract` | boolean | true | N/A | Extract images, videos, tables, links |
| `stream` | boolean | false | N/A | Return Server-Sent Events (SSE) stream |
| `deconstruct_query` | boolean | true | N/A | Break query into sub-queries |
| `max_subqueries` | integer | 3 | 1-5 | Max sub-queries if deconstructing |
| `enable_synthesis` | boolean | false | N/A | Generate final answer with citations |
| `synthesis_top_k_chunks` | integer | 12 | 1-50 | Top chunks to use for synthesis |
| `enable_reranking` | boolean | true | N/A | Rerank results by semantic relevance |
| `rerank_top_k` | integer or null | null | 1-20 or null | Only rerank top-k (null = all) |
| `enable_chunking` | boolean | true | N/A | Split content into RAG chunks |
| `chunking_strategy` | string | "hybrid" | markdown, semantic, hybrid | Strategy for chunking |
| `target_chunk_size` | integer | 350 | 100-1000 | Target tokens per chunk |

**Response** (JSON):

```json
{
  "query": "what are the benefits of async programming",
  "subqueries": [
    "async programming Python benefits",
    "asyncio event loop performance",
    "concurrent async vs threading"
  ],
  "answer": "[Synthesis answer if enabled]",
  "sources": [
    {
      "id": 1,
      "url": "https://example.com/async-guide",
      "title": "Async Programming in Python",
      "score": 0.92
    }
  ],
  "total_results": 5,
  "results": [
    {
      "url": "https://example.com/async-guide",
      "title": "Async Programming in Python",
      "author": "John Doe",
      "date": "2024-01-15",
      "sitename": "Example Blog",
      "fingerprint": "abc123...",
      "content_markdown": "# Async Programming in Python\n\nAsync programming allows...",
      "content_html": "<h1>Async Programming...</h1>",
      "images": [
        {
          "type": "image",
          "src": "https://example.com/image.jpg",
          "alt": "Async flow diagram"
        }
      ],
      "videos": [
        {
          "type": "iframe",
          "src": "https://youtube.com/embed/...",
          "alt": "Async tutorial video"
        }
      ],
      "tables": ["<table>...</table>"],
      "downloads": [
        {
          "text": "Download async-guide.pdf",
          "url": "https://example.com/async-guide.pdf",
          "extension": "pdf"
        }
      ],
      "internal_link_tree": [
        {
          "url": "/related-async",
          "text": "Related: Async Patterns"
        }
      ],
      "external_links": [
        "https://docs.python.org/3/library/asyncio.html"
      ],
      "chunks": [
        {
          "id": 0,
          "text": "Async programming is a programming paradigm...",
          "token_count": 45,
          "start_char": 0,
          "end_char": 245,
          "source_section": "## Introduction"
        }
      ],
      "chunking_metadata": {
        "success": true,
        "strategy": "hybrid",
        "total_chunks": 8,
        "total_tokens": 1247,
        "message": "Successfully chunked into 8 segments"
      },
      "reranking_score": 0.92
    }
  ],
  "graphs": null,
  "search_timestamp": "2026-01-22T14:30:00Z",
  "search_duration_seconds": 8.45,
  "reranking_enabled": true,
  "reranking_status": "success",
  "cache_hit": false
}
```

**Status Codes**:

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed |
| 400 | Bad Request | Invalid parameters (e.g., `max_results` > 20) |
| 429 | Rate Limited | Too many requests (>30/minute) |
| 504 | Timeout | Search exceeded 30-second limit |
| 500 | Internal Error | Unexpected server error |

---

### 2. GET `/cache/stats` — Cache Statistics

**Purpose**: Inspect cache performance metrics.

**URL**: `GET /cache/stats`

**Parameters**: None

**Response** (JSON):

```json
{
  "stats": {
    "total_entries": 42,
    "total_size_mb": 234.5,
    "hit_count": 156,
    "miss_count": 89,
    "hit_rate": 0.637,
    "oldest_entry": "2026-01-20T10:15:30Z",
    "newest_entry": "2026-01-22T14:30:45Z"
  },
  "timestamp": "2026-01-22T14:31:00Z"
}
```

**Notes**:
- `hit_rate` = hit_count / (hit_count + miss_count)
- `total_size_mb` includes metadata overhead
- Useful for monitoring cache efficiency and deciding when to clear

---

### 3. POST `/cache/clear` — Clear Cache

**Purpose**: Delete all cached search results.

**URL**: `POST /cache/clear`

**Parameters**: None

**Response** (JSON):

```json
{
  "message": "Cache cleared successfully"
}
```

**Status Codes**:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 500 | Failed to clear (e.g., permission issue) |

**Use Cases**:
- Before deploying a fix (invalidate stale results)
- Freeing up disk space
- Testing with fresh data
- Resetting after modifying target websites

---

### 4. GET `/health` — Health Check

**Purpose**: Verify API is running and configured correctly.

**URL**: `GET /health`

**Parameters**: None

**Response** (JSON):

```json
{
  "status": "healthy",
  "timestamp": "2026-01-22T14:31:30Z",
  "config": {
    "cache_enabled": true,
    "reranking_enabled": true,
    "browser_fallback_enabled": true
  }
}
```

**Use Cases**:
- Kubernetes liveness/readiness probes
- Docker health checks
- Load balancer monitoring
- Manual system verification

---

### 5. GET `/schemas/answer-engine-response` — Response Schema

**Purpose**: Retrieve JSON Schema for response validation.

**URL**: `GET /schemas/answer-engine-response`

**Response**: JSON Schema file (`application/schema+json`)

---

## Request & Response Schemas

### Request: `SearchRequest`

```python
{
    "query": str,                        # Required: 1-500 chars
    "max_results": int,                  # Optional: 1-20, default 5
    "deep_extract": bool,                # Optional: default True
    "stream": bool,                      # Optional: default False
    "deconstruct_query": bool,           # Optional: default True
    "max_subqueries": int,               # Optional: 1-5, default 3
    "enable_synthesis": bool,            # Optional: default False
    "synthesis_top_k_chunks": int,       # Optional: 1-50, default 12
    "enable_reranking": bool,            # Optional: default True
    "rerank_top_k": int | null,          # Optional: 1-20 or null, default null
    "enable_chunking": bool,             # Optional: default True
    "chunking_strategy": str,            # Optional: "markdown"|"semantic"|"hybrid"
    "target_chunk_size": int             # Optional: 100-1000, default 350
}
```

### Response: `AnswerEngineResponse`

```python
{
    "query": str,
    "subqueries": List[str],
    "answer": str | None,
    "sources": List[SourceItem],         # Ranked sources
    "total_results": int,
    "results": List[RichDocument],       # Full document data
    "graphs": List[GraphSpec] | None,    # Extracted tables as graphs
    "search_timestamp": str,              # ISO 8601
    "search_duration_seconds": float,
    "reranking_enabled": bool,
    "reranking_status": str | None,      # "success", "failed_cloud_fallback_local", etc.
    "cache_hit": bool
}
```

### Document: `RichDocument`

Each result includes rich metadata and content:

```python
{
    "url": str,
    "title": str | None,
    "author": str | None,
    "date": str | None,
    "sitename": str | None,
    "fingerprint": str | None,           # SimHash for deduplication
    
    "content_markdown": str | None,
    "content_html": str | None,
    
    "images": List[MediaAsset],
    "videos": List[MediaAsset],
    "tables": List[str],                 # HTML <table> strings
    "downloads": List[FileDownload],     # .pdf, .csv, etc.
    "internal_link_tree": List[SiteNode],
    "external_links": List[str],
    
    "chunks": List[Chunk] | None,        # RAG-ready segments
    "chunking_metadata": ChunkMetadata | None,
    
    "reranking_score": float | None      # 0-1, higher = more relevant
}
```

### Chunk: `Chunk`

Each chunk is LLM-ready:

```python
{
    "id": int,
    "text": str,                         # Actual content
    "token_count": int,                  # For context budgeting
    "start_char": int,                   # Position in original
    "end_char": int,
    "source_section": str | None         # e.g. "## Introduction"
}
```

---

## Configuration

All configuration via environment variables (or `.env` file):

### Cache Configuration

```bash
CACHE_ENABLED=true                      # Enable/disable caching
CACHE_DIR="./cache"                     # Directory for cache files
CACHE_TTL=86400                         # Time-to-live in seconds (24h default)
CACHE_MAX_SIZE_MB=2000                  # Max cache size in MB (2GB default)
```

### Browser/Fetching Configuration

```bash
PLAYWRIGHT_TIMEOUT=30                   # Timeout per URL fetch (seconds)
MAX_BROWSERS=4                          # Concurrent browser instances
```

### Search Configuration

```bash
SEARCH_TIMEOUT=30                       # Total search timeout (seconds)
RERANKER_USE_CLOUD=true                 # Use Google Gemini (vs. local)
```

### Chunking Configuration

```bash
CHUNKING_STRATEGY=hybrid                # "markdown", "semantic", "hybrid"
CHUNK_SIZE=350                          # Target tokens per chunk
```

### API Keys

```bash
GOOGLE_API_KEY="sk-..."                 # For Gemini embeddings + synthesis
OPENAI_API_KEY="sk-..."                 # (Optional) For OpenAI synthesis
ZAI_API_KEY="..."                       # (Optional) For Zai synthesis
```

### Debug Configuration

```bash
DEBUG=false                             # Verbose logging
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Scenarios

| Scenario | Status | Message | Fix |
|----------|--------|---------|-----|
| Invalid query parameter | 400 | `max_results ensure this value is less than or equal to 20` | Adjust `max_results` ≤ 20 |
| Rate limit exceeded | 429 | `Rate limit exceeded: 30 per 1 minute` | Wait or adjust limit |
| Search timeout | 504 | `Search exceeded 30s timeout` | Reduce `max_results` or increase timeout |
| Missing API key | 500 | `GOOGLE_API_KEY missing` | Set environment variable |
| Invalid API key | 500 | `GOOGLE_API_KEY is invalid` | Check key at [Google AI Studio](https://aistudio.google.com/app/apikeys) |
| Orchestrator not initialized | 500 | `Orchestrator not initialized` | Ensure API started successfully |

### Graceful Degradation

The API **never crashes** due to feature failures. Instead:

- **Reranking fails**: Returns results in DuckDuckGo order
- **Synthesis fails**: Returns null `answer`
- **Chunking fails**: Returns null `chunks`
- **Some URLs fail to fetch**: Returns results from successful fetches
- **Cache write fails**: Continues without caching

---

## Performance Notes

### Typical Timings (on 1vCPU + 8GB RAM)

| Operation | Time |
|-----------|------|
| Cache hit | 10-50ms |
| Search only (DDG + dedup) | 500ms-1s |
| Fetch 5 URLs (Tier 1) | 2-5s |
| Fetch 5 URLs (Tier 2 fallback) | 15-40s |
| Rerank (cloud) | 2-4s |
| Rerank (local) | 0.5-1.5s |
| Chunk 5 docs (hybrid) | 0.5-2s |
| Synthesize answer | 3-8s |
| **Total (full pipeline)** | **8-15s** |

### Optimization Strategies

1. **Use caching aggressively**: Set `CACHE_TTL=604800` (1 week) for evergreen content
2. **Rerank fewer results**: Set `rerank_top_k=3` instead of reranking all results
3. **Disable synthesis** if not needed: `enable_synthesis=false`
4. **Use markdown chunking** if speed matters: `chunking_strategy="markdown"`
5. **Reduce max_results**: Fewer URLs = faster pipeline
6. **Use CDN** to cache compiled results: nginx, CloudFront, etc.

### Scaling Considerations

- **Vertical**: Increase RAM (for browser pool) and CPU
- **Horizontal**: Deploy multiple instances behind nginx load balancer with shared Redis cache
- **Database Cache**: Replace file-based cache with Redis or PostgreSQL for multi-instance setups

---

## Security Considerations

### API Security

1. **Add Authentication**: Use nginx auth, JWT, or API keys
2. **Rate Limiting**: Default 30/min; adjust via environment
3. **Input Validation**: Query length capped at 500 chars; use reverse proxy WAF
4. **Output Sanitization**: HTML content is extracted but NOT sanitized; sanitize before rendering

### Data Security

1. **Cache Storage**: Unencrypted by default; use encrypted volumes in production
2. **Credentials**: Never log API keys; use `.env` and `.gitignore`
3. **URL Logging**: URLs are logged at DEBUG level; be careful with sensitive URLs
4. **Third-party APIs**: Requests sent to Google Gemini, OpenAI, Zai; review their privacy policies

### Network Security

1. **Use HTTPS**: Always use TLS in production (nginx reverse proxy)
2. **Firewall**: Restrict API access to trusted networks only
3. **DDoS Protection**: Use CloudFlare or AWS WAF in front
4. **Rate Limiting**: Implement at reverse proxy level as well

### Operational Security

1. **Monitoring**: Enable CloudWatch / Prometheus alerts for errors
2. **Backup**: Cache can be rebuilt; logs should be retained
3. **Updates**: Pin dependency versions in `requirements.txt`; review updates before deploying
4. **Secrets Management**: Use AWS Secrets Manager, HashiCorp Vault, or similar in production

---

## Examples

### Example 1: Simple Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "best Python testing frameworks"}'
```

### Example 2: Full-Featured Search with All Options

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compare PostgreSQL vs MongoDB",
    "max_results": 8,
    "enable_reranking": true,
    "rerank_top_k": 5,
    "enable_chunking": true,
    "chunking_strategy": "semantic",
    "target_chunk_size": 250,
    "enable_synthesis": true,
    "synthesis_top_k_chunks": 20
  }'
```

### Example 3: Streaming (Server-Sent Events)

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what is machine learning", "stream": true}'
```

Output (line-by-line):

```
event: status
data: "Searching for: what is machine learning"

event: status
data: "Fetching 5 URLs..."

event: status
data: "Reranking results..."

event: final
data: {"query": "...", "results": [...], ...}
```

### Example 4: Monitoring Cache

```bash
curl http://localhost:8000/cache/stats | jq '.stats | {hit_rate: .hit_rate, size_mb: .total_size_mb}'
```

Output:

```json
{
  "hit_rate": 0.6823,
  "size_mb": 456.2
}
```

---

## Deprecated / Future

- **GraphQL API**: Planned for v3.5
- **WebSocket streaming**: Planned for v3.4
- **Batch endpoint**: Planned for v3.3
- **Custom models**: Planned for v4.0

---

**Questions?** Check [FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md) for architecture or [DEPLOYMENT.md](DEPLOYMENT.md) for production setup.

**Last Updated**: January 2026
