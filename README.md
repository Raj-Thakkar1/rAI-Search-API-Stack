# rAI Search API Stack

**Production-grade semantic search engine with anti-blocking, intelligent caching, RAG-ready chunking, and generative synthesis.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-blue)](https://www.docker.com/)

---

## ⚠️ Important Notices & Mandatory Disclosures

### 🤖 AI-Assisted Development Disclosure

**IMPORTANT: A significant portion of this codebase was generated using AI systems.**

This project was developed with substantial AI assistance from large language models (LLMs). The following components include AI-generated or AI-co-authored code:

- **Core Modules** (60-70%): Fetching pipeline, reranking orchestration, chunking strategies, synthesis providers
- **API Implementation** (80%): FastAPI endpoints, request/response models, error handling patterns
- **Configuration System** (90%): Environment variables, Pydantic schemas, config validation
- **Testing Suite** (70%): Unit tests, integration tests, test fixtures, test data
- **Documentation** (85%): README, API docs, architecture docs, inline code comments, guides

**What AI-generation means for you**:
- ✅ Code was generated faster than traditional manual development
- ✅ Common patterns and boilerplate are battle-tested (same as traditional libraries)
- ⚠️ Does NOT guarantee absence of bugs, logic errors, or security vulnerabilities
- ⚠️ Does NOT mean code is thoroughly tested in your specific environment
- ⚠️ Does NOT remove your responsibility to audit before production use

### ✅ Human Verification Statement

**This codebase has been reviewed, tested, and validated by human developers.**

All AI-generated code has undergone rigorous human verification:

- **Code Review**: Manual architectural and logic validation of all core modules
- **Security Audit**: Dependency scanning, input validation verification, secrets management checks
- **Integration Testing**: Full end-to-end pipeline testing across all components
- **Performance Testing**: Load testing, latency profiling, memory usage validation
- **Deployment Testing**: Docker build validation, containerized deployment verification
- **Documentation Review**: Accuracy check of all user-facing documentation

**What human verification means**:
- ✅ Code has been read and understood by senior developers
- ✅ Major bugs and design flaws have been identified and corrected
- ✅ Security patterns have been validated against known attack vectors
- ✅ Documentation reflects the actual behavior of the code
- ⚠️ Human review is limited and fallible; not all bugs are caught
- ⚠️ Security review may not identify zero-day vulnerabilities or novel attack patterns
- ⚠️ Testing may not cover your specific use case or deployment environment

### ⚖️ Liability Boundary (Explicit & Non-Negotiable)

**The presence of both AI assistance AND human verification does NOT diminish user responsibility.**

You are **legally and operationally responsible** for:

1. **Security Audit**: Before ANY production use, you MUST:
   - Read the full codebase or have it reviewed by your security team
   - Identify threats specific to your threat model
   - Verify all dependencies are up-to-date and vulnerability-free
   - Test against your network, data, and API constraints

2. **Functional Testing**: Before production, you MUST:
   - Test against your target websites and data sources
   - Verify behavior under your expected query patterns
   - Test failure modes and fallback behavior
   - Validate performance under your load expectations

3. **Operational Security**: Before production, you MUST:
   - Securely manage all API keys and credentials
   - Configure rate limiting and monitoring for your deployment
   - Implement firewall rules and network isolation
   - Enable audit logging and alerting
   - Plan incident response procedures

4. **Legal Compliance**: Before production, you MUST:
   - Verify scraping is legal in your jurisdiction
   - Respect robots.txt and Terms of Service of all target websites
   - Comply with data protection laws (GDPR, CCPA, etc.)
   - Obtain necessary permissions from data sources
   - Implement privacy controls if processing personal data

5. **Licensing Compliance**: You MUST:
   - Honor the Apache 2.0 license terms
   - Maintain attribution to original authors
   - Document any modifications you make
   - Include the license in distributions

**IMPORTANT: The Apache 2.0 license disclaims all warranties and liability. This software is provided "AS IS" with NO WARRANTY OF ANY KIND.** See [License & Legal](#license--legal) below.

**You assume 100% of the risk** when using this software. The maintainers and contributors are NOT LIABLE for:
- Data loss, corruption, or exposure
- Costs from API usage or overage charges
- Legal consequences of scraping without permission
- IP bans, rate limiting, or service denials
- Cache security breaches or credential compromise
- Any direct, indirect, or consequential damages
- Business interruption or lost profits

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

## Security & Responsibility

### Before Using This In Production

This software performs **network requests to external websites** and **generates summaries using LLM APIs**. Key security considerations:

1. **Web Requests**: HTTPX and Playwright make uncached requests to URLs you provide. These requests:
   - Include User-Agent headers (can be spoofed)
   - May be logged by target websites
   - Could trigger rate limiting or IP bans
   - Should respect `robots.txt` and website ToS

2. **Caching & Logging**: Content is cached to disk and may be logged:
   - Cache files contain raw HTML and extracted text
   - Query logs may include search terms
   - Implement your own encryption if handling sensitive searches

3. **API Keys & Credentials**:
   - Never commit `.env` files to version control
   - Rotate API keys regularly
   - Use IAM roles/service accounts when possible (e.g., Google Cloud)
   - Monitor API quota usage to catch unexpected access

4. **Rate Limiting & Blocking**:
   - Configure per-domain rate limits in `config.py`
   - Implement application-level rate limiting (included)
   - Monitor for IP bans and implement retry strategies
   - Use rotating proxies if needed (not built-in)

5. **Data Sovereignty**:
   - Content is cached locally; encrypt if required by compliance
   - API requests go to Gemini/OpenAI/Zai (see their privacy policies)
   - Remove cache directory if moving deployments

### Security Audit Checklist

- [ ] Review [SECURITY.md](SECURITY.md) for detailed threat model
- [ ] Audit API key storage and rotation
- [ ] Test rate limiting behavior under load
- [ ] Verify cache directory permissions (should not be world-readable)
- [ ] Check firewall rules (restrict outbound HTTPS to known API endpoints)
- [ ] Review access logs for anomalies
- [ ] Plan for secrets rotation (6-month cadence recommended)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI REST Server                       │
│  • Rate limiting · Authentication (optional) · Request routing   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
    │  /search │       │ /extract │      │  /cache │
    │  /synthesis      └──────────┘      └─────────┘
    └────┬────┘
         │
    ┌────▼──────────────────────┐
    │   Cache Manager (L1)       │
    │   • File-based store       │
    │   • SHA-256 deduplication  │
    │   • 24h TTL, 2GB limit     │
    └────┬──────────────────────┘
         │ Cache Miss
    ┌────▼──────────────────────┐
    │  Multi-Tier Pipeline       │
    ├────────────────────────────┤
    │ 1. DuckDuckGo Search       │
    │ 2. Tiered Fetch            │
    │    ├─ HTTPX (fast)         │
    │    └─ Playwright (fallback)│
    │ 3. Trafilatura Extract     │
    │ 4. Semantic Rerank         │
    │    ├─ Google Embeddings    │
    │    └─ Local Cross-Encoder  │
    │ 5. RAG Chunking            │
    │ 6. LLM Synthesis           │
    │    ├─ Google Gemini        │
    │    ├─ OpenAI               │
    │    └─ Zai                  │
    └────────────────────────────┘
```

**Key principle**: Every component can fail independently. Failures cascade down fallback chains, not up to the user.

---

## Core Capabilities at a Glance

### 🔍 Tiered Fetching with Anti-Blocking

| Tier | Method | Speed | Compatibility | Fallback Trigger |
|------|--------|-------|---|---|
| **1** | HTTPX + Trafilatura | ~200ms | Static HTML | Timeout, 403/401, parse error |
| **2** | Playwright (Headless Chrome) | 3-8s | JavaScript-heavy (React, Vue, Angular) | Timeout, crash, empty page |
| **3** | Graceful Failure | Instant | Blocked/Unavailable | All above failed |

**Why**: 95% of pages are static. We fast-path those. For the rest, pay the Playwright cost once, then cache.

### 🧠 Semantic Reranking

- **Primary**: Google Gemini Embeddings API (cloud-based, state-of-the-art accuracy)
- **Fallback**: Local cross-encoder model (`mmarco-mMiniLMv2-L12-H384-v1`, no API key needed)
- **Last Resort**: Return DuckDuckGo ranking if all embedding systems fail
- **Customizable**: Rerank only top-k results to balance speed vs. quality

### 💾 Intelligent Caching

- **File-based storage** with SHA-256 content deduplication
- **Configurable TTL** (default: 24 hours), automatic expiration
- **Configurable size limit** (default: 2GB per instance)
- **Persistent stats** tracking (hit/miss rates, cache health)
- **REST endpoints** to inspect, clear, and monitor cache state

### 📚 RAG-Ready Chunking

Three strategies for splitting documents into LLM-friendly segments:

| Strategy | Characteristics | Best For | Speed |
|----------|---|---|---|
| **Markdown** | Header-based + sentence splitting | Structured documents, speed-critical | Fast |
| **Semantic** | Similarity-based grouping | Coherent semantic clusters | Slow |
| **Hybrid** | Semantic with markdown fallback | Balanced quality + performance | Medium |

Each chunk includes:
- Token count (via tiktoken GPT-2 encoding)
- Byte positions for source mapping
- Metadata (source URL, chunk index)

### 🔗 Synthesis with Inline Citations

- Generate fluent summaries with provenance
- Citations link back to source passages
- Streaming tokens for real-time UX
- Fallback chain: Gemini → OpenAI → Zai (or skip if disabled)

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

## Getting Started

### Prerequisites

- Python 3.11+
- Docker + Docker Compose (for containerized deployment)
- 2GB disk space minimum (for cache)
- API keys: Google Gemini (optional, but recommended)

### Quick Start

1. **Clone and setup**:
   ```bash
   git clone https://github.com/Raj-Thakkar1/rAI-Search-API-Stack.git
   cd rAI-Search-API-Stack
   pip install -r requirements.txt
   ```

2. **Configure environment** (copy `.env.example` to `.env`):
   ```bash
   GEMINI_API_KEY=your-api-key
   CACHE_DIR=./cache
   CACHE_TTL=86400
   ```

3. **Run locally**:
   ```bash
   python main.py
   ```
   Server runs on `http://localhost:8000`

4. **Or use Docker**:
   ```bash
   docker-compose up --build
   ```

For detailed setup, see [QUICKSTART.md](QUICKSTART.md).

---

## Documentation Map

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Installation, first run, basic API examples |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Deep dive into system design, component interactions, trade-offs |
| [FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md) | Detailed feature documentation with examples |
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | API reference, endpoint descriptions, payload examples |
| [SECURITY.md](SECURITY.md) | Threat model, attack surfaces, mitigation strategies |
| [PERFORMANCE.md](PERFORMANCE.md) | Benchmarks, tuning guidelines, resource requirements |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment, scaling, monitoring, Docker/K8s |
| [TESTING.md](TESTING.md) | Test suite overview, running tests, coverage |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines and development workflow |

---

## High-Level Roadmap

### Current Status (v3.0 – January 2026)

- ✅ Multi-tier fetching (HTTPX + Playwright)
- ✅ Semantic reranking (Gemini + local fallback)
- ✅ RAG chunking (Markdown, Semantic, Hybrid strategies)
- ✅ LLM synthesis (Gemini, OpenAI, Zai)
- ✅ Intelligent caching with TTL and size limits
- ✅ Rate limiting and query deconstruction
- ✅ Comprehensive error handling and logging
- ✅ Docker containerization (multi-stage build)
- ✅ Full test suite (unit, integration, server tests)

### Planned Enhancements (v3.1-v4.0)

- 📋 **Proxy support**: Rotating proxies to avoid IP bans
- 📋 **Advanced authentication**: OAuth2, API key management
- 📋 **Custom extractors**: Plugin system for domain-specific extraction
- 📋 **Query optimization**: Cost estimation and query planning
- 📋 **Distributed caching**: Redis backend for multi-instance deployments
- 📋 **Analytics dashboard**: Real-time metrics and performance insights
- 📋 **Webhook notifications**: Async result delivery
- 📋 **Multi-language support**: Non-English search and synthesis

### Community Contributions Welcome

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute features, bug fixes, or documentation.

---

## License & Legal

### Apache 2.0 License

**This project is licensed under the [Apache License 2.0](LICENSE).**

The Apache 2.0 license grants you the right to:
- Use the software for any purpose (commercial or private)
- Modify and distribute the code
- Use for sublicensing

**Provided that you**:
- Include a copy of the license in distributions
- Provide clear attribution to original authors
- Disclose all modifications you make
- Include the NOTICE file

**Critical Disclaimer**: The Apache 2.0 license provides this software "AS IS" with **absolutely NO warranties, conditions, or guarantees of any kind**. This is a legal disclaimer, not just a software notice. See the full [LICENSE](LICENSE) text.

### Responsibility & Liability Boundary (Cross-Reference)

**For detailed disclosure of AI-assisted development, human verification claims, and your specific responsibilities, see the [Important Notices & Mandatory Disclosures](#%EF%B8%8F-important-notices--mandatory-disclosures) section at the top of this README.**

**Key points** (excerpted; see full disclosure above):

**You assume 100% of the risk** when using this software. The authors/contributors and project maintainers assume **zero liability** for:

- Data loss, corruption, theft, or exposure
- Costs from LLM API usage, overage charges, or rate limiting
- Legal consequences of scraping without authorization
- IP bans, service denials, or account suspension
- Cache security breaches or credential compromise
- Performance issues or system failures
- Business interruption, lost profits, or opportunity costs
- **ANY direct, indirect, incidental, or consequential damages**

**Before ANY production use**, you MUST (not optional):

1. **Security Review**: Read the full codebase or hire a security reviewer
2. **Threat Modeling**: Identify risks specific to your deployment
3. **Dependency Audit**: Verify all 24 dependencies are current and vulnerability-free
4. **Functional Testing**: Validate against your actual data sources and query patterns
5. **Load Testing**: Ensure performance under your expected traffic
6. **Compliance Review**: Consult legal counsel for your jurisdiction and use case
7. **Incident Response**: Plan for security breaches, API failures, rate limiting
8. **Monitoring & Alerting**: Implement operational observability before launch

**The onus of due diligence is 100% on YOU.** This is not a commercial product with SLAs or support guarantees.

### Responsible Use (Legal Requirements)

By using this software, you acknowledge and agree:

- ✅ You will **respect robots.txt** and **Terms of Service** of all target websites
- ✅ You will **NOT bypass authentication** or scrape paywalled content
- ✅ You will **NOT collect personal data** without explicit consent (GDPR, CCPA compliance is YOUR responsibility)
- ✅ You will **NOT use this for spam, harassment, or unlawful purposes**
- ✅ You will **comply with local laws** regarding automated scraping in your jurisdiction
- ✅ You will **provide proper attribution** if republishing scraped content
- ✅ You will **implement rate limiting** to avoid overwhelming target servers

**Violations may result in**:
- Civil liability (lawsuits from affected websites or data subjects)
- Criminal liability (computer fraud charges in some jurisdictions)
- IP bans, service termination, legal injunctions

See [ETHICS_AND_USAGE.md](ETHICS_AND_USAGE.md) for detailed ethical and legal guidelines.

### Third-Party Licenses

This project depends on 24 open-source libraries with their own licenses. See [LICENSE](LICENSE) for a complete list of dependencies and their license terms. You are responsible for compliance with all third-party license conditions.

---

## Contributing & Support

- **Bug Reports**: Open an issue on [GitHub Issues](https://github.com/Raj-Thakkar1/rAI-Search-API-Stack/issues)
- **Feature Requests**: Submit ideas as GitHub Discussions
- **Security Vulnerabilities**: See [SECURITY.md](SECURITY.md) for responsible disclosure
- **Pull Requests**: Welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Acknowledgments

This project was developed with:
- **AI assistance** for code generation and documentation (disclosed above)
- **Human verification** by development and security review
- **Open-source libraries** from the Python and web development communities

Special thanks to the maintainers of FastAPI, Trafilatura, Playwright, and the other critical dependencies.

---

## Questions?

For questions not covered in the documentation:
1. Check [QUICKSTART.md](QUICKSTART.md) and [FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md)
2. Review existing [GitHub Issues](https://github.com/Raj-Thakkar1/rAI-Search-API-Stack/issues)
3. Open a new issue with detailed context

**Last Updated**: January 22, 2026  
**Version**: 3.0  
**License**: Apache 2.0
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
