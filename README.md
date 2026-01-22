# rAI Search API Stack

**Production-grade semantic search engine with anti-blocking, intelligent caching, RAG-ready chunking, and generative synthesis.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-blue)](https://www.docker.com/)

---

## Project Vision

The **rAI Search API Stack** is a comprehensive, production-hardened search and extraction engine designed to power AI-driven applications that require:

- **Semantic intelligence**: Retrieve not just keyword matches, but conceptually relevant results
- **Resilience**: Handle anti-blocking, JavaScript-heavy sites, and degraded network conditions
- **LLM integration**: Chunk and synthesize results directly into AI model context windows
- **Reliability**: Fail gracefully across all tiers, never blocking the request pipeline

This system is built for **senior engineers deploying to production**, with careful attention to performance, security, cost-control, and operational observability.

---

## What This Is

A complete REST API that:

1. **Discovers** relevant content via DuckDuckGo search
2. **Fetches** HTML with intelligent fallback (fast HTTP → Playwright browser automation)
3. **Extracts** markdown, images, videos, tables, and structured data from web pages
4. **Reranks** results using semantic embeddings (cloud: Google Gemini, fallback: local cross-encoders)
5. **Chunks** content into RAG-ready segments with token counting
6. **Synthesizes** final answers with inline citations using LLM providers (Gemini, OpenAI, Zai)
7. **Caches** aggressively to reduce compute and network latency
8. **Streams** responses as Server-Sent Events (SSE) for real-time UX

---

## What This Is NOT

- **Not a web crawler or scraper**: This is a search-focused extraction engine, not a mass indexing system
- **Not a replacement for Elasticsearch**: No persistent indexing; each search is fresh
- **Not guaranteed to work on all websites**: Some sites explicitly forbid automated access (respect robots.txt and ToS)
- **Not a legal service**: This tool does not guarantee accuracy or currency of information
- **Not a privacy-preserving service**: URLs, content, and metadata are cached and may be logged
- **Not suitable for sensitive data**: Do not use this to process confidential or personally identifiable information

---

## Who This Is For

- **AI/ML Engineers** building RAG pipelines who need fresh, structured search results
- **Research Teams** aggregating information from multiple sources with synthesis
- **Content Platforms** that need intelligent search + reranking without building from scratch
- **Backend Systems** needing semantic search with production observability
- **Developers** willing to operate infrastructure (Docker, environment tuning, monitoring)

---

## Core Capabilities

### 🔍 Tiered Fetching with Anti-Blocking

| Tier | Method | Speed | Compatibility | Use Case |
|------|--------|-------|---|---|
| **1** | HTTPX + Trafilatura | ~200ms | Static HTML | 95% of web pages |
| **2** | Playwright (Headless Chrome) | 3-8s | JavaScript-heavy (React, Vue, Angular) | Cloudflare, SPAs |
| **3** | Graceful Failure | Instant | Blocked/Unavailable | Returns empty, doesn't crash |

**Automatic fallback** if Tier 1 times out or fails. Honors `User-Agent` headers and timeouts.

### 🧠 Semantic Reranking

- **Primary**: Google Gemini Embeddings API (cloud-based, accurate)
- **Fallback**: Local cross-encoder model (`mmarco-mMiniLMv2-L12-H384-v1`, requires no API key)
- **Last Resort**: Return DuckDuckGo order if all fail
- **Control**: Optionally rerank only top-k results to balance speed vs. quality

### 💾 Intelligent Caching

- **File-based storage** with SHA-256 content deduplication
- **24-hour TTL** (configurable), automatic expiration
- **2GB limit** per instance (configurable for your machine)
- **Persistent stats** tracking (hit/miss rates, cache health)
- **Endpoints** to inspect, clear, and monitor cache state

### 📚 RAG-Ready Chunking

Three strategies for splitting documents into LLM-friendly segments:

| Strategy | Characteristics | Best For |
|----------|---|---|
| **Markdown** | Header-based + sentence splitting (fast) | Structured documents, speed-critical |
| **Semantic** | Similarity-based grouping (slower) | Coherent semantic clusters |
| **Hybrid** | Semantic with markdown fallback | Balanced quality + performance |

Each chunk includes:
- Token count (via tiktoken GPT-2 encoding)
- Byte positions for source mapping
- Source section (e.g., "## Introduction")

### 🤖 Generative Synthesis

- **Multi-provider support**: Gemini, OpenAI, Zai (or any OpenAI-compatible API)
- **Inline citations**: All facts traced back to source URLs with references [1], [2], etc.
- **System-prompted accuracy**: Engineered prompts to prevent hallucination
- **Streaming or batch**: Choose real-time streaming (SSE) or final response

### 🏭 Production Features

- **Rate limiting** (configurable, e.g., 30 requests/minute)
- **Health checks** with detailed system status
- **Comprehensive logging** at all layers
- **Error handling** that never crashes the API
- **Background cache pruning** to maintain storage bounds
- **Query deconstruction** for complex queries (e.g., "compare X vs Y")

---

## Quick Feature Map

```
User Query
    ↓
[Query Deconstruction] → Optional: break into sub-queries
    ↓
[DuckDuckGo Search] → Merge results from all sub-queries
    ↓
[Deduplication] → Remove duplicate URLs
    ↓
[Tiered Fetching] → Tier 1: HTTPX | Tier 2: Playwright | Tier 3: Skip
    ↓
[Content Extraction] → Markdown, images, videos, tables, links, metadata
    ↓
[Reranking (Optional)] → Semantic reordering of results
    ↓
[RAG Chunking (Optional)] → Split into token-aware segments
    ↓
[Synthesis (Optional)] → Generate answer with citations
    ↓
Final Response (JSON or SSE stream)
```

---

## Apache 2.0 License & Legal Disclaimer

**License**: This project is licensed under the [Apache License 2.0](LICENSE).

### Important Legal Notice

**This software is provided "AS IS" without warranties of any kind.** Users are responsible for:

1. **Compliance with website Terms of Service**: Ensure your use complies with each target website's ToS and `robots.txt`
2. **Compliance with local law**: Some jurisdictions restrict automated scraping; verify your use is legal
3. **Rate limiting and politeness**: This tool can be aggressive; use responsibly to avoid overloading target servers
4. **Data privacy**: Do not use this to collect personal data or violate privacy laws (GDPR, CCPA, etc.)
5. **Attribution**: If you republish scraped content, provide proper attribution

**The maintainers assume no liability** for misuse, legal consequences, or damages resulting from this software.

---

## Security and Responsibility

### What This Tool Can Do (Responsibly)

✅ Aggregate public research information for analysis  
✅ Power LLM-backed search features in applications  
✅ Research competitor pricing or public API documentation  
✅ Monitor public content changes for notifications  

### What NOT To Do

❌ Mass scrape for commercial resale without permission  
❌ Bypass authentication or paywalls  
❌ Violate `robots.txt` or `meta` no-index directives  
❌ Collect personally identifiable information (names, emails, addresses)  
❌ Circumvent rate limits or DDoS servers  

**Use this tool ethically. Automated scraping can impact server costs and user experience.**

---

## System Requirements

### Minimum (Development)

- Python 3.11+
- 2GB RAM
- 500MB disk space
- Stable internet connection

### Recommended (Production)

- **CPU**: 1-2 vCPU
- **RAM**: 12-16GB (for browser pool + cache)
- **Disk**: 50GB (for 2GB cache + logs + margin)
- **Network**: Low-latency, high-bandwidth connection
- **OS**: Linux (Ubuntu 20.04+, Debian 11+), macOS, or Windows

### Dependencies at a Glance

- **FastAPI** (async web framework)
- **Playwright** (headless browser automation)
- **Trafilatura** (HTML-to-text extraction)
- **DuckDuckGo Search** (search backend)
- **Sentence Transformers** (local semantic embeddings)
- **Google Generative AI** (cloud embeddings + synthesis)
- **tiktoken** (token counting)
- **SlowAPI** (rate limiting)

Full list in [requirements.txt](requirements.txt).

---

## Getting Started (5 Minutes)

### 1. Clone and Enter Directory

```bash
git clone https://github.com/Raj-Thakkar1/rAI-Search-API-Stack.git
cd rAI-Search-API-Stack
```

### 2. Set Environment Variables

```bash
export GOOGLE_API_KEY="your-google-api-key"
export CACHE_ENABLED="true"
export DEBUG="false"
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup.

### 3. Install and Run

```bash
pip install -r requirements.txt
python main.py
```

API will start at `http://localhost:8000`

### 4. Test with a Simple Query

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest Python 3.13 features",
    "max_results": 5,
    "enable_reranking": true,
    "enable_chunking": true,
    "enable_synthesis": false
  }'
```

See [QUICKSTART.md](QUICKSTART.md) for more examples and troubleshooting.

---

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** — 5-minute setup guide with working examples
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** — Complete API reference (all endpoints, parameters, response formats)
- **[FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md)** — Architecture, pipeline flow, design decisions, limitations
- **[FILE_STRUCTURE.md](FILE_STRUCTURE.md)** — Directory layout, module responsibilities, data flow
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production hardening, Docker, scaling, observability, security
- **[TESTING.md](TESTING.md)** — Test suite overview and how to run/extend tests
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Detailed system design, component interactions, future roadmap
- **[PERFORMANCE.md](PERFORMANCE.md)** — Benchmarks, tuning, optimization strategies
- **[LIMITATIONS.md](LIMITATIONS.md)** — Known issues, edge cases, site compatibility notes
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Development guidelines for contributors

---

## High-Level Roadmap

### Near-Term (v3.1 - 3.2)

- [ ] Parallel sub-query execution for faster multi-part searches
- [ ] Advanced query understanding (NLP-based intent detection)
- [ ] Database-backed cache option (PostgreSQL, Redis) for multi-instance deployments
- [ ] Real-time crawl scheduling for fresh content indexing

### Medium-Term (v3.3 - 3.5)

- [ ] Multi-modal search (images, videos in results)
- [ ] Fine-tuned reranking models for domain-specific search
- [ ] GraphQL API option alongside REST
- [ ] Webhook-based async search completion notifications

### Long-Term (v4.0+)

- [ ] Distributed architecture for horizontal scaling
- [ ] Built-in LLM fine-tuning on search+synthesis patterns
- [ ] Integration with knowledge graphs for entity disambiguation
- [ ] Privacy-mode option (no caching, local-only processing)

---

## Community & Support

- **Issues & Bugs**: [GitHub Issues](https://github.com/Raj-Thakkar1/rAI-Search-API-Stack/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Raj-Thakkar1/rAI-Search-API-Stack/discussions)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## License & Attribution

Licensed under Apache 2.0. See [LICENSE](LICENSE) for full details.

**Built with**:
- FastAPI by Sebastián Ramírez
- Playwright by Microsoft
- Trafilatura by Adrien Barbaresi
- DuckDuckGo Search by @deedy
- Google Generative AI SDK
- Sentence Transformers by UKP Lab

---

## Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Trafilatura Documentation](https://trafilatura.readthedocs.io/)
- [Google Generative AI Documentation](https://ai.google.dev/)
- [Sentence Transformers Documentation](https://www.sbert.net/)

---

**Last Updated**: January 2026  
**Status**: Production-Ready (v3.0)
