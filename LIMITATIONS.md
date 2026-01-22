# LIMITATIONS.md — Known Issues and Edge Cases

---

## Known Limitations

### 1. JavaScript-Only Sites

**Problem**: Some Single-Page Applications (SPAs) load all content via JavaScript. Playwright may:
- Timeout waiting for content to load
- Miss dynamically-loaded content below the fold
- Use excessive memory/CPU

**Examples**: 
- Certain news sites (CNN, Medium when not cached)
- LinkedIn (requires login, anti-bot measures)
- Twitter/X (without login)

**Workaround**:
```bash
# Increase timeout
PLAYWRIGHT_TIMEOUT=60

# Or disable chunking/synthesis for these sites
"enable_chunking": false
```

---

### 2. Authentication-Required Content

**Problem**: Can't scrape behind login walls (ethical + legal boundary).

**Sites**: LinkedIn, academic paywalls, Substack paid content

**Workaround**: Not applicable. Use official APIs or browser plugins.

---

### 3. Anti-Scraping Measures

**Problem**: Some sites actively block bots:
- Cloudflare (mostly handled by Playwright)
- Rotating IP blocks
- User-Agent detection
- Rate limiting

**Sites**: Some e-commerce, high-traffic news sites

**Status**:
- ✅ Cloudflare: Mostly handled
- ⚠️ IP blocking: Mitigated with User-Agent rotation
- ❌ Aggressive rate limits: May timeout

**Workaround**:
```bash
# Use residential proxy (costs $$)
# or increase timeouts and retry logic
```

---

### 4. Real-Time Data

**Problem**: Cache means searches miss very recent content (< 24 hours).

**Affected**: Stock prices, sports scores, breaking news

**Workaround**:
```bash
# For real-time needs, reduce TTL
CACHE_TTL=3600              # 1 hour instead of 24

# Or disable cache for certain patterns
# (requires code modification)
```

---

### 5. Semantic Accuracy Limitations

**Problem**: Reranking is not perfect. Can rank irrelevant results high in edge cases:
- Homonyms ("Python snake" vs. "Python programming")
- Ambiguous queries ("What is X used for?" - could mean food, medicine, etc.)
- Non-English queries (lower accuracy)

**Example**:
```
Query: "python" 
Reranking might put snake articles above programming articles
(or vice versa, depending on DuckDuckGo's initial ranking)
```

**Workaround**: Use specific query terms, e.g., "Python programming language"

---

### 6. LLM Hallucination

**Problem**: Synthesis can invent facts despite system prompts.

**Risk**: Answer includes `[citation]` but cited source doesn't actually support the claim.

**Mitigation**:
- Strict system prompt (included)
- User should always verify citations
- Consider using GPT-4 (more reliable than GPT-3.5)

**Workaround**: 
```python
# Disable synthesis for safety-critical applications
"enable_synthesis": false
```

---

### 7. Language Support

**Problem**: Primarily tested on English. Other languages have degraded:
- Extraction quality (Trafilatura trained mostly on English)
- Reranking accuracy (embeddings trained on English)
- Synthesis quality (LLMs are English-first)

**Supported**: En, with best-effort support for major languages

**Workaround**: Use English queries when possible

---

### 8. Large Document Handling

**Problem**: Very long documents (>100KB) can:
- Timeout during extraction
- Exhaust memory during chunking
- Create too many chunks

**Example**: Research papers, full books, legal documents

**Workaround**:
```bash
# Increase timeouts
PLAYWRIGHT_TIMEOUT=60
SEARCH_TIMEOUT=120

# Or manually limit chunk count in code
```

---

### 9. Structured Data Extraction

**Problem**: Limited support for tables, forms, and structured data.
- Tables extracted as HTML strings (not parsed)
- Forms not navigable (static content only)
- JSON-LD schemas not extracted

**Workaround**: Use specialized tools (Diffbot, APIs) for structured data

---

### 10. Image/Video Analysis

**Problem**: Images and videos detected but NOT analyzed:
- Image captions extracted if present in HTML
- Video content not transcribed
- Image OCR not performed

**Workaround**: External OCR/video transcription APIs

---

## Site-Specific Issues

| Site | Issue | Status |
|------|-------|--------|
| Wikipedia | Works well | ✅ No issues |
| News sites | Good extraction | ✅ No issues |
| GitHub | Works | ✅ No issues |
| Stack Overflow | Works | ✅ No issues |
| LinkedIn | Blocked | ❌ Login required |
| Twitter | Blocked | ❌ Login + rate limit |
| Medium | Some paywalled | ⚠️ Partial |
| e-commerce sites | Anti-bot | ⚠️ Sometimes blocked |
| PDFs | Not handled | ❌ Not supported |

---

## Non-Goals (Out of Scope)

### Features We Won't Implement

1. **Full-text indexing**: Use Elasticsearch/Solr instead
2. **Real-time index**: 24-hour crawl lag by design
3. **Deep web crawling**: Only surface web (public)
4. **Form submission**: Would require sophisticated automation
5. **CAPTCHA solving**: Ethical + legal issues
6. **PDF parsing**: Different tool needed (PyPDF2, pdfplumber)
7. **Video transcription**: Requires separate service
8. **Image OCR**: Requires separate service
9. **Multi-modal search**: Not designed for image queries
10. **Persistent indexing**: Each search is fresh

### Why These Are Out of Scope

- **Complexity**: Would massively increase codebase
- **Maintenance burden**: More dependencies = more bugs
- **Legal risk**: CAPTCHA solving, content scraping
- **Cost**: Would require significant infrastructure
- **Philosophy**: "Do one thing well" - focus on fresh, semantic search

---

## Performance Limitations

### Latency

| Scenario | Latency | Limit |
|----------|---------|-------|
| Cache hit | 10-50ms | Excellent |
| Tier 1 fetch (fast) | 1-3s | Good |
| Tier 2 fetch (Playwright) | 3-8s | Acceptable |
| Full pipeline | 8-15s | Acceptable |
| With synthesis | 15-25s | Slow |

**Timeout**: Hard limit 30s (configurable)

### Throughput

| Configuration | Max QPS | Notes |
|---------------|---------|-------|
| Single instance | 2-5 QPS | Limited by Playwright |
| With caching | 10-30 QPS | Depends on hit rate |
| 4 instances (load balanced) | 8-20 QPS | Shared cache bottleneck |
| With Redis | 30-50 QPS | Distributed cache |

---

## Memory Limitations

| Operation | Memory |
|-----------|--------|
| API baseline | ~200MB |
| Per Playwright browser | ~150-200MB |
| Cache (1GB data) | ~1.5GB (overhead) |
| Typical search pipeline | ~500MB peak |

**Total on 16GB machine**: Comfortable (leaves 12GB for OS + buffers)

---

## Error Recovery

### What Fails Gracefully

✅ Individual URL fetch fails → Skip that URL  
✅ Reranking API fails → Return DuckDuckGo order  
✅ Synthesis fails → Return null answer  
✅ Chunking fails → Return unchunked content  
✅ Cache write fails → Continue without caching  

### What Fails Completely

❌ No internet connection → No results  
❌ DuckDuckGo unreachable → No results  
❌ All URLs fail to fetch → Empty results  
❌ Invalid API keys (all) → Reranking disabled  

---

## Browser Compatibility

**Tested on**: Chromium (Playwright default)

**Not tested**: Firefox, Safari (would require code changes)

**Reason**: Chromium best for headless automation + Cloudflare handling

---

## Compliance Limitations

### GDPR

**⚠️ Your responsibility to ensure**:
- Users can request data deletion
- Cache respects data retention policies
- PII not stored in cache longer than necessary

**Note**: This tool doesn't auto-implement GDPR compliance

### CCPA

**⚠️ Your responsibility**:
- User data rights (access, deletion)
- Opt-out mechanisms
- Privacy policy transparency

---

## Recommended Workarounds

| Problem | Solution |
|---------|----------|
| "My site isn't working" | Check DuckDuckGo; add site: operator |
| "Results are old" | Reduce CACHE_TTL or clear cache |
| "Slow searches" | Reduce max_results, disable synthesis |
| "Memory leak" | Monitor with `top`, restart periodically |
| "Wrong results ranked high" | Use specific query terms, disable reranking |
| "Synthesis is hallucinating" | Disable synthesis, verify manually |
| "Can't access site X" | It's likely rate-limited; try later |

---

## Getting Help

If you hit a limitation:

1. **Check this document**: Often a known issue
2. **Search GitHub issues**: Might be already discussed
3. **Read FEATURES_IN_DEPTH.md**: Understand design tradeoffs
4. **File an issue**: Describe what you're trying to do
5. **Consider alternatives**: Might need a different tool

---

## Future Roadmap to Address Limitations

- [ ] **v3.1**: Improve JavaScript rendering (wait for lazy-loading)
- [ ] **v3.2**: Add database option for persistent indexing
- [ ] **v3.3**: Multi-language support improvements
- [ ] **v3.4**: Image OCR integration
- [ ] **v4.0**: Distributed architecture for better throughput

---

**Last Updated**: January 2026
