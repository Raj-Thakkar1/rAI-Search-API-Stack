# Project Structure - Deep Search API v2.0

```playlist
deep-search-api/
├── main.py                  # Entry point (FastAPI app)
├── config.py                # Configuration management
├── requirements.txt         # Python dependencies
├── .env.example             # Template for environment variables
├── Dockerfile              # Docker build instructions
├── docker-compose.yml       # Docker Compose setup
│
├── core/                    # Core logic (implicit in root for now, but conceptual)
│   ├── browser_fallback.py  # Playwright TieredFetcher
│   ├── cache_manager.py     # FileBasedCache implementation
│   ├── embeddings.py        # Google & Local embedding wrappers
│   ├── pipeline.py          # PipelineOrchestrator logic
│   ├── rag_chunker.py       # RAGChunker (Markdown/Semantic)
│   ├── reranker.py          # SemanticReranker
│   ├── synthesis.py         # LLM Synthesis (Z.ai/OpenAI)
│   └── trafilatura_patch.py # Custom extraction logic
│
├── tests/                   # Comprehensive Test Suite
│   ├── run_tests.py         # Runner for unit/feature tests
│   ├── test_features.py     # Unit tests for all components
│   ├── test_server.py       # API endpoint tests
│   ├── test_integration.py  # Real-world integration tests
│   ├── reliability_suite.py # Production crawler stress test
│   └── reliability_report.md # Output of stress tests
│
└── docs/                    # Documentation
    ├── FILE_STRUCTURE.md
    ├── USAGE_GUIDE.md
    ├── QUICKSTART.md
    └── README.md
```
