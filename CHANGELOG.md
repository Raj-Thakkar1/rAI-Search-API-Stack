# CHANGELOG.md — Version History

---

## [3.0] — January 2026 (Current)

### ✨ Major Features

- **Semantic Reranking**: Google Gemini embeddings with local cross-encoder fallback
- **Tiered Fetching**: HTTPX (fast) → Playwright (fallback) with graceful failure
- **RAG Chunking**: Markdown, semantic, and hybrid strategies for LLM context windows
- **Generative Synthesis**: Multi-provider LLM integration (Gemini, OpenAI, Zai) with inline citations
- **Intelligent Caching**: File-based cache with SHA-256 deduplication and TTL management
- **Query Deconstruction**: Automatic multi-part query decomposition (e.g., "compare X vs Y")
- **Streaming Responses**: Server-Sent Events (SSE) for real-time result streaming
- **Production Features**: Rate limiting, health checks, comprehensive logging, Docker support

### 🛡️ Quality Assurance

- Full test suite (unit, integration, server tests)
- >80% code coverage
- Apache 2.0 licensing
- Professional documentation suite

### 📚 Documentation

- Comprehensive README with vision and scope
- 5-minute QUICKSTART guide
- Full USAGE_GUIDE API reference
- FEATURES_IN_DEPTH architecture documentation
- FILE_STRUCTURE project layout guide
- DEPLOYMENT production hardening guide
- TESTING test suite documentation
- LIMITATIONS known issues and workarounds
- CONTRIBUTING developer guidelines

---

## [2.9] — December 2025 (Unreleased)

### 🧪 Beta Testing

- Internal testing of v3.0 features
- API schema finalization
- Performance tuning

---

## [3.1] — Planned (Q1 2026)

### Planned Features

- [ ] Parallel sub-query execution for faster multi-part searches
- [ ] Advanced query understanding (NLP-based intent detection)
- [ ] Database-backed cache option (PostgreSQL, Redis) for multi-instance deployments
- [ ] Real-time crawl scheduling for fresh content indexing
- [ ] Improved JavaScript rendering (lazy-loading support)

---

## [3.2] — Planned (Q2 2026)

### Planned Features

- [ ] GraphQL API endpoint
- [ ] Batch search endpoint for multiple queries
- [ ] Fine-tuned reranking models for domain-specific search
- [ ] Webhook notifications for async search completion
- [ ] Image caption extraction and analysis

---

## [3.3] — Planned (Q3 2026)

### Planned Features

- [ ] Multi-language support improvements
- [ ] Advanced error recovery and retry logic
- [ ] Custom chunking strategies via plugins
- [ ] Performance profiling and auto-tuning

---

## [4.0] — Planned (Q4 2026)

### Major Changes

- [ ] Distributed architecture for horizontal scaling
- [ ] Built-in LLM fine-tuning on search+synthesis patterns
- [ ] Integration with knowledge graphs for entity disambiguation
- [ ] Privacy-mode option (no caching, local-only processing)
- [ ] Support for multiple search backends (not just DuckDuckGo)

---

## Deprecation Policy

We follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** (3.0 → 4.0): Breaking API changes
- **MINOR** (3.0 → 3.1): New features, backward compatible
- **PATCH** (3.0 → 3.0.1): Bug fixes, backward compatible

**Deprecation Timeline**:
- Features marked `@deprecated` will work for 2 minor versions
- Example: Feature deprecated in v3.1 works until v3.3

---

## Upgrade Guide

### Upgrading from Earlier Versions

Coming soon as project matures.

---

## Contributors

**v3.0**:
- Lead: rAI Search Team
- Contributors: Community

---

## License

All releases licensed under Apache License 2.0. See LICENSE file.

---

**Last Updated**: January 2026
