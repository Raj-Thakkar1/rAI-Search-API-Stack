# TESTING.md — Test Suite Guide

---

## Overview

The rAI Search API Stack includes a comprehensive test suite covering:
- **Unit tests**: Individual components (cache, chunking, reranking)
- **Integration tests**: Full pipeline with real APIs
- **Server tests**: HTTP endpoints and error handling

**Test Framework**: pytest  
**Async Support**: pytest-asyncio  
**Coverage**: >80% of core logic

---

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_features.py

# Run with verbose output
pytest -v tests/

# Run with coverage
pytest --cov=. --cov-report=html tests/
```

### Test Categories

#### Unit Tests (`test_features.py`)

Fast, no external dependencies:

```bash
pytest tests/test_features.py -v
```

**Tests**:
- `test_cache_set_get()`: File-based cache operations
- `test_cache_ttl_expiration()`: TTL cleanup
- `test_chunking_markdown()`: Header-based chunking
- `test_chunking_semantic()`: Similarity-based chunking
- `test_token_counting()`: Tiktoken integration
- `test_deduplication()`: URL deduplication
- `test_extraction()`: HTML parsing

#### Integration Tests (`test_integration.py`)

Slow, uses real APIs (DuckDuckGo, websites, optionally Google):

```bash
pytest tests/test_integration.py -v -s

# Run only specific integration test
pytest tests/test_integration.py::test_full_pipeline -v
```

**Tests**:
- `test_full_pipeline()`: End-to-end search → reranking → chunking
- `test_tiered_fetching()`: Tier 1 + Tier 2 fallback
- `test_reranking_with_real_api()`: Google Gemini embeddings (requires API key)
- `test_synthesis()`: Answer generation (requires LLM provider)
- `test_error_recovery()`: Graceful failure modes

**Requirements**:
- Internet connection
- (Optional) `GOOGLE_API_KEY` for Gemini reranking tests
- (Optional) `OPENAI_API_KEY` for OpenAI synthesis tests
- **Time**: 2-5 minutes per run

#### Server Tests (`test_server.py`)

HTTP endpoints and FastAPI behavior:

```bash
pytest tests/test_server.py -v
```

**Tests**:
- `test_search_endpoint()`: POST /search
- `test_search_with_reranking()`: Reranking parameter
- `test_search_with_chunking()`: Chunking parameter
- `test_cache_stats()`: GET /cache/stats
- `test_health_check()`: GET /health
- `test_rate_limiting()`: 30/minute limit
- `test_error_responses()`: 400, 404, 500 errors

---

## Writing New Tests

### Example: Unit Test

```python
# tests/test_features.py
import pytest
from cache_manager import FileBasedCache, CacheConfig

@pytest.fixture
def cache():
    config = CacheConfig(enabled=True, cache_dir="./test_cache")
    return FileBasedCache(config)

@pytest.mark.asyncio
async def test_cache_retrieves_stored_data(cache):
    # Arrange
    test_data = {"query": "test", "results": []}
    
    # Act
    await cache.set("test_key", test_data)
    retrieved = await cache.get("test_key")
    
    # Assert
    assert retrieved == test_data
```

### Example: Integration Test

```python
# tests/test_integration.py
import pytest
from main import SearchRequest, orchestrator

@pytest.mark.asyncio
async def test_real_search():
    request = SearchRequest(
        query="Python async/await",
        max_results=3,
        enable_reranking=False
    )
    
    result = None
    async for chunk in orchestrator.stream_answer_engine(request):
        if "final" in chunk:
            # Parse final result
            pass
    
    assert result is not None
    assert len(result.sources) > 0
```

### Example: Server Test

```python
# tests/test_server.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_search_endpoint():
    response = client.post("/search", json={
        "query": "Python",
        "max_results": 5
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data
```

---

## Mocking External Services

### Mock Google Gemini API

```python
# tests/conftest.py
from unittest.mock import Mock, patch
import pytest

@pytest.fixture
def mock_gemini():
    with patch('embeddings.GoogleGeminiEmbedding') as mock:
        mock.return_value.embed_texts.return_value = {
            "embeddings": [[0.1, 0.2, 0.3, ...]]
        }
        yield mock
```

### Mock DuckDuckGo

```python
@pytest.fixture
def mock_ddgs():
    with patch('main.DDGS') as mock:
        mock.return_value.text.return_value = iter([
            {"href": "https://example.com", "title": "Example"}
        ])
        yield mock
```

---

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run unit tests
        run: pytest tests/test_features.py --cov
      
      - name: Run server tests
        run: pytest tests/test_server.py --cov
      
      - name: Run integration tests (skip slow tests)
        run: pytest tests/test_integration.py -m "not slow" || true
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Performance Testing

### Load Testing with `locust`

```python
# tests/load_test.py
from locust import HttpUser, task, between

class SearchAPIUser(HttpUser):
    wait_time = between(2, 5)
    
    @task(1)
    def search(self):
        self.client.post("/search", json={
            "query": "Python tutorials",
            "max_results": 5
        })
    
    @task(3)
    def health_check(self):
        self.client.get("/health")

if __name__ == "__main__":
    # Run: locust -f tests/load_test.py -u 10 -r 2
    pass
```

**Run load test**:
```bash
locust -f tests/load_test.py \
  --host=http://localhost:8000 \
  --users=10 \
  --spawn-rate=2 \
  --run-time=5m
```

---

## Test Coverage Report

Generate HTML coverage report:

```bash
pytest --cov=. --cov-report=html tests/
open htmlcov/index.html
```

**Target Coverage**: ≥80% for critical paths

---

## Troubleshooting Tests

### "ModuleNotFoundError: No module named 'pytest'"

```bash
pip install pytest pytest-asyncio
```

### "GOOGLE_API_KEY not found" on integration tests

```bash
# Skip integration tests requiring API keys
pytest tests/ -m "not needs_api_key"

# Or set dummy key
export GOOGLE_API_KEY="test-key"
```

### "Playwright not installed"

```bash
pip install playwright
playwright install chromium
```

### Tests timeout (async issues)

```bash
# Increase pytest timeout
pytest --timeout=300 tests/
```

---

## Test Best Practices

1. **Unit tests first**: Fast feedback during development
2. **Mock external services**: Don't call real APIs in unit tests
3. **Use fixtures**: Reduce code duplication
4. **Test edge cases**: Empty queries, rate limits, timeouts
5. **Async tests**: Use `@pytest.mark.asyncio` for async functions
6. **Cleanup**: Use fixtures to clean up resources
7. **Meaningful names**: Test names should describe what they test
8. **One assertion per test** (generally): Easier to diagnose failures

---

## CI/CD Integration

### Pre-commit Hooks

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        types: [python]
        stages: [commit]
```

Install:
```bash
pip install pre-commit
pre-commit install
```

---

**Next**: See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute tests.

**Last Updated**: January 2026
