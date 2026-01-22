# FEATURES_IN_DEPTH.md — System Architecture and Design

---

## Table of Contents

1. [System Pipeline Flow](#system-pipeline-flow)
2. [Search & Discovery](#search--discovery)
3. [Fetching Strategy](#fetching-strategy)
4. [Content Extraction](#content-extraction)
5. [Semantic Reranking](#semantic-reranking)
6. [RAG Chunking](#rag-chunking)
7. [Caching System](#caching-system)
8. [Generative Synthesis](#generative-synthesis)
9. [Failure Modes & Recovery](#failure-modes--recovery)
10. [Design Decisions & Tradeoffs](#design-decisions--tradeoffs)
11. [Limitations & Non-Goals](#limitations--non-goals)

---

## System Pipeline Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. CACHE CHECK (24h TTL)                                      │
│    └─ If hit: return cached results immediately (~10ms)      │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. QUERY DECONSTRUCTION (Optional)                           │
│    └─ "compare X vs Y" → ["X benefits", "Y benefits", ...]   │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. DISCOVERY: DuckDuckGo Search                               │
│    └─ Get 20 URLs (merge if multiple subqueries)             │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. DEDUPLICATION                                              │
│    └─ Remove duplicate URLs                                   │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. TIERED FETCHING (Parallel)                                 │
│    ├─ Tier 1: HTTPX + Trafilatura (~200ms per URL)           │
│    └─ Tier 2: Playwright (3-8s, if Tier 1 times out)        │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. CONTENT EXTRACTION                                         │
│    └─ Markdown, metadata, images, videos, tables, links      │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 7. RERANKING (Optional)                                       │
│    ├─ Cloud: Google Gemini embeddings                         │
│    └─ Fallback: Local cross-encoder                           │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 8. RAG CHUNKING (Optional)                                    │
│    ├─ Markdown strategy (header-based)                        │
│    ├─ Semantic strategy (similarity-grouped)                  │
│    └─ Hybrid (semantic with fallback)                         │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 9. SYNTHESIS (Optional)                                       │
│    └─ Generate answer with inline citations                  │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 10. CACHE WRITE                                               │
│     └─ Store for future identical queries                     │
└───────────────────┬──────────────────────────────────────────┘
                    ↓
              RETURN RESPONSE
```

**Key Design Principle**: Every stage can fail independently. API gracefully degrades by skipping failed steps.

---

## Search & Discovery

### DuckDuckGo Integration

**Why DuckDuckGo?**
- Free, no API key required
- Anonymity-focused (privacy)
- Privacy-friendly (doesn't track)
- Diverse results (less algorithmic bias)
- Fast and reliable

**How it works**:
1. User query → DuckDuckGo API
2. Return top 20 URLs
3. If query deconstructed: merge results from all sub-queries
4. Remove duplicates by URL

**Query Deconstruction** (Heuristic):

```python
"compare React vs Vue for web" →
  - "React for web specs"
  - "Vue for web specs"
  - "React vs Vue for web comparison"

"machine learning with Python" →
  - "machine learning with Python" (no deconstruction)
```

**Limitations**:
- Limited by DuckDuckGo's index
- May miss very new or niche content
- Blocked in some jurisdictions

---

## Fetching Strategy

### Tiered Fetching Architecture

Why three tiers? **Speed vs. compatibility tradeoff**.

#### Tier 1: Fast HTTP Fetch (200ms)

**Tool**: Trafilatura + HTTPX  
**Speed**: ~200ms per URL  
**Success Rate**: ~95%  
**What it handles**: Static HTML, most blogs, documentation sites

```python
async def fetch_url(url: str) -> Optional[str]:
    try:
        html = await asyncio.wait_for(
            asyncio.to_thread(trafilatura.fetch_url, url),
            timeout=5.0
        )
        return html
    except asyncio.TimeoutError:
        return None  # Fall through to Tier 2
```

**Advantages**:
- Fast (200-500ms)
- Low resource usage
- No browser overhead

**Disadvantages**:
- Can't execute JavaScript
- Fails on Cloudflare-protected sites
- Misses dynamic content

#### Tier 2: Playwright Browser Rendering (3-8s)

**Tool**: Playwright (headless Chromium)  
**Speed**: 3-8s per URL  
**Success Rate**: ~98%  
**What it handles**: React/Vue/Angular SPAs, Cloudflare-protected sites, JavaScript-heavy sites

```python
async def fetch_with_js(self, url: str) -> Optional[str]:
    try:
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        html = await page.content()
        return html
    except PlaywrightTimeoutError:
        return None  # Tier 3
```

**Advantages**:
- Renders JavaScript
- Handles Cloudflare
- Gets fully rendered DOM

**Disadvantages**:
- 3-8 seconds per URL (20-40x slower than Tier 1)
- Higher memory usage
- May hang on poorly-written JS

**Concurrency**: Limited to `MAX_BROWSERS=4` concurrent instances to control memory.

#### Tier 3: Graceful Failure

If both Tier 1 and Tier 2 fail:
- Log warning
- Return `None` for that URL
- Continue with other results
- API **never crashes**

---

## Content Extraction

### Trafilatura Extraction

**What we extract**:

| Component | Tool | Purpose |
|-----------|------|---------|
| Main text | Trafilatura | Markdown-formatted content |
| Metadata | Trafilatura | Title, author, date, sitename |
| Images | LXML | `<img>` tags with src, alt |
| Videos | LXML | `<video>`, `<iframe>`, `<embed>` |
| Tables | LXML | `<table>` HTML strings |
| Links | LXML | Internal nav tree + external links |
| Files | LXML | `.pdf`, `.csv`, `.xlsx`, etc. |

### SimHash Fingerprinting

**Purpose**: Detect duplicate/similar content.

```python
fingerprint = trafilatura.utils.sha1(content)
# Store in cache with fingerprint for deduplication
```

**Use Case**: Avoid storing near-duplicate pages in cache.

---

## Semantic Reranking

### Why Reranking?

DuckDuckGo's ranking is keyword-based. Semantic reranking ensures:
- Conceptually relevant results rank higher
- Synonyms considered (e.g., "autonomous" ≈ "self-driving")
- Context matters (e.g., "python snake vs python programming")

### Multi-Tier Reranking System

```
┌─────────────────────────────────────┐
│ 1. Try Google Gemini Embeddings     │
│    (cloud, accurate, costs $$)      │
└────────────┬────────────────────────┘
             ↓ (if fails)
┌─────────────────────────────────────┐
│ 2. Try Local Cross-Encoder          │
│    (local, free, slower)            │
└────────────┬────────────────────────┘
             ↓ (if fails)
┌─────────────────────────────────────┐
│ 3. Use DuckDuckGo Order             │
│    (always works)                   │
└─────────────────────────────────────┘
```

### Google Gemini Embeddings (Primary)

**Model**: `models/embedding-001`  
**API**: `batchEmbedContents`  
**Speed**: 2-4 seconds for 10 documents  
**Cost**: ~$0.02 per 1M tokens  

**How it works**:
1. Generate embedding for user query
2. Generate embeddings for each result's title + snippet
3. Cosine similarity between query and results
4. Sort by similarity score (0-1)

**Advantages**:
- State-of-the-art accuracy
- Multi-lingual support
- Fast batch API

**Disadvantages**:
- Requires API key
- Costs money (but cheap)
- Network latency (API call)

### Local Cross-Encoder Fallback

**Model**: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`  
**Speed**: 0.5-1.5 seconds for 10 documents  
**Cost**: Free (runs locally)

**How it works**:
1. Pass (query, document) pairs to model
2. Model outputs relevance score (0-1)
3. Sort by score

**Advantages**:
- Free (no API calls)
- No latency (local)
- Always available

**Disadvantages**:
- Requires 2GB RAM
- Download ~1.3GB on first run
- Slightly lower accuracy than Gemini

### Graceful Degradation

If both fail (API key invalid, local model download fails):
- **Status**: `reranking_status = "failed_all_used_original"`
- **Result**: Return original DuckDuckGo order
- **API**: Still returns 200 OK (never fails)

---

## RAG Chunking

### Why Chunking?

LLMs have context windows (e.g., Claude 100K tokens). Need to split documents into:
- Semantically coherent units
- Token-budgeted for context windows
- With source section references

### Three Strategies

#### 1. Markdown Strategy (Fast)

**How**:
1. Split by markdown headers (# ## ###)
2. Within each section, split by sentences
3. Group sentences until hitting `target_chunk_size` tokens

**Speed**: Fast (<100ms per document)  
**Quality**: Good for structured docs  
**Best for**: Technical documentation, blog posts, structured content

**Example**:
```
Input: "# Introduction\n\nAsync programming is... ## Benefits\n\n..."
Output:
  Chunk 0: "# Introduction\n\nAsync programming is..."
  Chunk 1: "## Benefits\n\n..."
```

#### 2. Semantic Strategy (Slow)

**How**:
1. Split text into sentences
2. Generate embeddings for each sentence
3. Group consecutive sentences with high similarity
4. Merge/split groups to hit `target_chunk_size`

**Speed**: Slow (1-5s per document)  
**Quality**: Excellent for coherence  
**Best for**: Unstructured prose, news articles, synthesis

**Trade-off**: Quality vs. speed

#### 3. Hybrid Strategy (Balanced, Default)

**How**:
1. Try semantic strategy
2. If it takes >3 seconds, fall back to markdown
3. If markdown fails, use simple sentence splitting

**Speed**: 0.5-2s per document  
**Quality**: Balanced  
**Best for**: Production (recommended default)

### Token Counting

**Tool**: `tiktoken` (OpenAI's tokenizer)  
**Encoding**: GPT-2 compatible  
**Accuracy**: Within 1-2% of actual model

```python
import tiktoken
enc = tiktoken.get_encoding("gpt2")
tokens = enc.encode("hello world")  # [31373, 1504]
```

---

## Caching System

### Why File-Based Cache?

- **No external dependencies**: No Redis/PostgreSQL needed
- **Persistent**: Survives API restarts
- **Content-addressable**: SHA-256 hashing for deduplication
- **Observable**: Easy to inspect cache directory
- **Tuneable**: Per-instance cache size limits

### Cache Storage Structure

```
./cache/
├── .cache_stats.json          (persistent hit/miss stats)
├── abc123def456789...json     (cached search 1)
├── xyz789abc123456...json     (cached search 2)
└── ...
```

**Cache Key**: SHA-256(query + params)

**Entry Structure**:
```json
{
  "key": "search:abc123...",
  "data": {...full response...},
  "timestamp": "2026-01-22T14:30:00Z",
  "ttl_seconds": 86400,
  "size_bytes": 125000,
  "content_hash": "def456..."
}
```

### TTL & Expiration

**Default TTL**: 24 hours (86400 seconds)  
**Cleanup**: On-demand via `/cache/clear` or automatic on disk full

**Rationale**: 24 hours is a good balance:
- Content freshness (websites update daily)
- Cost savings (reduced API calls)
- Storage efficiency

### Deduplication

**Problem**: Multiple users searching same query → store data twice

**Solution**: SHA-256 content hashing
```python
content_hash = hashlib.sha256(response_json.encode()).hexdigest()
# Only store if hash not in cache already
```

### Cache Statistics

**Tracked Metrics**:
- `hit_count`: Successful cache hits
- `miss_count`: Cache misses
- `hit_rate`: hit_count / (hit_count + miss_count)
- `total_size_mb`: Total cache size
- `oldest_entry`: First cache entry timestamp

**Use**: Monitoring cache efficiency; deciding when to clear

---

## Generative Synthesis

### Why Synthesis?

Users want **answers**, not just links. Synthesis:
- Reads top chunks from results
- Generates coherent answer
- Includes inline citations [1], [2], etc.
- Prevents hallucination with strict prompts

### Multi-Provider Architecture

```
┌─────────────────────────┐
│ 1. Gemini (Primary)     │ Fastest, free tier available
└──────────┬──────────────┘
           ↓ (if fails)
┌─────────────────────────┐
│ 2. OpenAI (Fallback)    │ Reliable, costs $
└──────────┬──────────────┘
           ↓ (if fails)
┌─────────────────────────┐
│ 3. Zai (Fallback)       │ Self-hosted, free tier
└─────────────────────────┘
```

### System Prompt Engineering

```python
SYNTHESIS_SYSTEM_PROMPT = """You are a factual answer synthesis engine.

Rules:
1) Use ONLY the provided context snippets. Do not use prior knowledge.
2) If the context is insufficient, say: "I don't know based on the provided sources."
3) Every factual claim must include an inline citation like [1], [2], etc.
4) Citations must refer to source IDs. Do not invent citations.
5) Keep the answer concise, neutral, and directly responsive.
6) If comparing items, use compact structure and cite each point.
"""
```

**Why these rules?**
- Rule 1: Prevents hallucination
- Rule 2: Honest about limitations
- Rule 3-4: Traceable facts
- Rule 5: User-friendly
- Rule 6: Comparison-specific optimization

### Citation Injection

**Input**:
```json
[
  {"source_id": 1, "url": "https://example.com", "text": "Python async is..."},
  {"source_id": 2, "url": "https://docs.org", "text": "asyncio module..."}
]
```

**Generated Output**:
```
Python async programming allows concurrent execution [1]. 
The asyncio module provides tools for writing async code [2].
```

**Citation Format**: `[source_id]` references the source URL in final response.

---

## Failure Modes & Recovery

### Graceful Degradation Philosophy

> **Never crash the API. Always return partial results.**

| Failure Point | Impact | Fallback |
|---------------|--------|----------|
| Cache read fails | Fetch fresh | Continue to search |
| DuckDuckGo API fails | No results from DDG | Return empty results |
| Fetch Tier 1 fails | URL not accessible | Try Tier 2 (Playwright) |
| Fetch Tier 2 fails | URL not accessible | Skip that URL |
| All fetches fail | All URLs inaccessible | Return empty results |
| Reranking fails | Can't semantically rank | Return DDG order |
| Chunking fails | Can't split content | Return unchunked content |
| Synthesis fails | Can't generate answer | Return null `answer` |
| Cache write fails | Can't persist | Continue without caching |

**Principle**: Feature failures are non-fatal; document failures are handled gracefully.

### Error Logging

All errors logged at `ERROR` or `WARNING` level with:
- Timestamp
- Component name
- Error message
- Context (URL, query, etc.)

Example:
```
2026-01-22 14:30:45 - Reranker - WARNING - Failed to initialize Google Gemini embedder: GOOGLE_API_KEY not found
2026-01-22 14:30:50 - BrowserFallback - WARNING - Playwright timeout for https://example.com after 30s
```

---

## Design Decisions & Tradeoffs

### 1. Why DuckDuckGo + Reranking vs. Full Index?

| Approach | Pros | Cons |
|----------|------|------|
| **DuckDuckGo + Reranking** | Fast, simple, fresh | Limited to DDG index; no deep context |
| **Full Index** (Elasticsearch) | Unlimited coverage | Massive infrastructure; 24h crawl lag |

**Decision**: DuckDuckGo + Reranking  
**Rationale**: Simpler architecture, fresh results, sufficient for most uses

### 2. Why File-Based Cache vs. Redis?

| Approach | Pros | Cons |
|----------|------|------|
| **File-based** | Zero dependencies; observable | Not shareable across instances |
| **Redis** | Shared; fast | External dependency; DevOps overhead |

**Decision**: File-based (with migration path to Redis)  
**Rationale**: Simpler deployment; works for single-instance; add Redis later if needed

### 3. Why Trafilatura + LXML vs. Beautiful Soup?

| Tool | Speed | Quality | Maintenance |
|------|-------|---------|---|
| **Trafilatura** | Fast | Excellent (ML-based) | Active |
| **Beautiful Soup** | Slow | Good | Very active |

**Decision**: Trafilatura  
**Rationale**: ML-based content detection; good balance of speed & quality

### 4. Why Playwright vs. Selenium/Puppeteer?

| Tool | Maturity | Speed | Multiprocess |
|------|----------|-------|---|
| **Playwright** | Modern | Fast | Excellent |
| **Selenium** | Mature | Slow | Good |
| **Puppeteer** | Mature | Fast | Node.js only |

**Decision**: Playwright  
**Rationale**: Modern, multiprocess support, Python native

---

## Limitations & Non-Goals

### Known Limitations

1. **JavaScript-only sites**: Some SPAs don't expose content in DOM until after async JS. Playwright may timeout.

2. **Authentication-required sites**: Can't scrape behind login walls.

3. **Anti-scraping measures**: Some sites (LinkedIn, Twitter with login) explicitly block automated access. Respect `robots.txt`.

4. **Paywalled content**: Can't bypass paywalls (ethical + legal boundary).

5. **Real-time updates**: Cache TTL means searches miss < 1 hour old news. Adjust `CACHE_TTL` if needed.

6. **Semantic accuracy**: Reranking is not perfect; sometimes irrelevant results rank high.

7. **Synthesis hallucination**: Even with strict prompts, LLMs can invent facts. Always verify citations.

8. **Language support**: Primarily tested on English. Other languages may have degraded quality.

### Non-Goals (Out of Scope)

- **Full-text indexing**: Not a replacement for Elasticsearch/Solr
- **Real-time index**: Not suitable for live stock tickers, sports scores
- **Legal/medical accuracy**: Use specialized tools for those domains
- **Privacy compliance**: Doesn't auto-GDPR-scrub data; your responsibility
- **Multi-tenant SaaS**: Built for single deployment; add your own auth layer

---

## Performance Characteristics

### Asymptotic Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Search (cache hit) | O(1) | Direct lookup |
| Search (cache miss) | O(n log n) | n = results; sorting by rank |
| Reranking | O(n) | n = results |
| Chunking | O(m log m) | m = document size |
| Synthesis | O(k) | k = top chunks |

### Scaling Characteristics

- **Vertical** (more CPU/RAM): Linear improvement up to 16GB + 4 vCPU
- **Horizontal** (multiple instances): Limited by shared cache; needs Redis
- **Network**: Bottleneck is fetching URLs (Tier 2 Playwright is slowest)

---

**Next**: See [FILE_STRUCTURE.md](FILE_STRUCTURE.md) for code organization, or [DEPLOYMENT.md](DEPLOYMENT.md) for production setup.

**Last Updated**: January 2026
