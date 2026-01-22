# CONTRIBUTING.md — Development Guidelines for Contributors

---

## Welcome!

We appreciate contributions! This document outlines how to contribute to the rAI Search API Stack.

**What we value**:
- Clear, well-tested code
- Documentation-first approach
- Respect for Apache 2.0 licensing
- Ethical scraping practices
- Performance awareness

---

## Code of Conduct

Be respectful and inclusive. No harassment, discrimination, or abuse.

---

## Getting Started

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/rAI-Search-API-Stack.git
cd rAI-Search-API-Stack
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev tools
pip install pytest pytest-asyncio black flake8 mypy

# Run tests
pytest tests/
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/your-bug-name
```

**Branch naming**:
- `feature/...` for new features
- `bugfix/...` for bug fixes
- `docs/...` for documentation
- `refactor/...` for code refactoring
- `perf/...` for performance improvements

---

## Development Workflow

### Before You Code

1. **Check GitHub issues**: Is this already being worked on?
2. **Discuss major changes**: Open an issue first
3. **Review FEATURES_IN_DEPTH.md**: Understand architecture
4. **Check FILE_STRUCTURE.md**: Where to make changes

### While Coding

1. **Write tests first** (TDD when possible)
2. **Follow PEP 8** (use `black`)
3. **Add type hints** (all functions)
4. **Document changes** (docstrings, comments)
5. **Keep commits small** and focused

### Code Style

**Python formatting**:
```bash
black .                          # Auto-format code
flake8 .                         # Lint
mypy .                           # Type checking (optional)
```

**Example**:
```python
# ✅ Good
async def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """
    Fetch URL with timeout.
    
    Args:
        url: Target URL
        timeout: Seconds before timeout
    
    Returns:
        HTML content or None if failed
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(trafilatura.fetch_url, url),
            timeout=float(timeout)
        )
    except asyncio.TimeoutError:
        logger.warning(f"Timeout for {url}")
        return None

# ❌ Bad
def fetch(u,t=30):
    # No docstring, no types, no error handling
    return trafilatura.fetch_url(u)
```

### Testing

**Every change needs tests**:

```python
# tests/test_my_feature.py
import pytest
from my_module import my_function

@pytest.mark.asyncio
async def test_my_function_happy_path():
    result = await my_function("test_input")
    assert result == "expected_output"

@pytest.mark.asyncio
async def test_my_function_error_handling():
    result = await my_function("")  # edge case
    assert result is None
```

**Run tests**:
```bash
pytest tests/test_my_feature.py -v
```

---

## Common Contribution Types

### Adding a New LLM Provider (Synthesis)

**File**: `synthesis.py`

**Steps**:
1. Create new class inheriting `SynthesisProvider`
2. Implement `async def stream()` and `async def generate()`
3. Add to `_init_synthesis_provider()` in `main.py`
4. Write tests in `tests/test_integration.py`

**Example**:
```python
class MyLLMProvider(SynthesisProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        """Stream tokens from LLM."""
        # Implementation
        pass
    
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate full response."""
        # Implementation
        pass
```

### Adding a Configuration Option

**Files**: `config.py`, `.env` (example)

**Steps**:
1. Add to appropriate `Config` class in `config.py`
2. Add environment variable loading
3. Document in `USAGE_GUIDE.md`

**Example**:
```python
# config.py
class MyNewConfig(BaseModel):
    my_setting: str = "default_value"
    my_timeout: int = 30

class Config(BaseModel):
    # ... existing fields ...
    my_new_config: MyNewConfig

def load_config() -> Config:
    return Config(
        # ... existing ...
        my_new_config=MyNewConfig(
            my_setting=os.getenv("MY_SETTING", "default_value"),
            my_timeout=int(os.getenv("MY_TIMEOUT", "30")),
        ),
    )
```

### Fixing a Bug

**Steps**:
1. Write a test that reproduces the bug
2. Verify test fails
3. Fix the bug
4. Verify test passes
5. Run full test suite to check for regressions

**Example**:
```bash
# Create failing test
pytest tests/test_bug_reproduction.py
# >> FAILED

# Fix the bug
# (edit relevant file)

# Test passes
pytest tests/test_bug_reproduction.py
# >> PASSED

# Check no regressions
pytest tests/
# >> All passed
```

### Improving Performance

**Require**:
1. Benchmark before/after (include in PR)
2. Explain the optimization
3. Ensure tests still pass
4. Document any trade-offs

**Example** (in PR description):
```
**Performance Improvement**
- Cache hits: 10ms → 5ms (50% faster)
- Full search: 12s → 9s (25% faster)

**Trade-off**: None; pure optimization

**Benchmark**:
```
Before: 100 requests/minute (avg: 12s per search)
After:  140 requests/minute (avg: 9s per search)
```
```

### Documentation Improvements

**No code changes needed!** Just:
1. Edit `.md` files
2. Clarify existing sections
3. Add examples
4. Fix typos

**Submit**:
```bash
git add docs/
git commit -m "docs: improve setup instructions"
```

---

## Submitting Changes

### Pre-Submission Checklist

- [ ] Code is formatted with `black`
- [ ] Linting passes with `flake8`
- [ ] All new tests pass
- [ ] Full test suite passes
- [ ] Documentation updated (if needed)
- [ ] Commits are small and focused
- [ ] Commit messages are clear
- [ ] No debugging code left in (no `print()`, `breakpoint()`)
- [ ] Environment variables handled correctly
- [ ] Error handling is graceful

### Create a Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Go to GitHub and create PR
# Fill out PR template:
```

**PR Template**:
```markdown
## Description
Brief explanation of changes

## Type
- [ ] Bug fix
- [ ] Feature
- [ ] Performance improvement
- [ ] Documentation

## Tests
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code formatted with `black`
- [ ] Tests pass: `pytest`
- [ ] Documentation updated
```

### Code Review Process

1. **Maintainers review** your PR
2. **You address feedback** (respond to comments)
3. **Tests pass** on our CI/CD
4. **Merge** when approved

**Be patient**: Reviews take time.

---

## Setting Up Locally for Testing

### Running the API Locally

```bash
export GOOGLE_API_KEY="test-key-or-real-key"
python main.py
# API runs on http://localhost:8000
```

### Testing with Real APIs

```bash
# Tests that contact real services
pytest tests/test_integration.py -v

# Tests that use only mocks
pytest tests/test_features.py tests/test_server.py -v
```

---

## Reporting Bugs

### How to Report

1. **Check existing issues**: Don't duplicate
2. **Describe the bug clearly**:
   - What you did
   - What happened
   - What you expected
3. **Provide reproduction steps**
4. **Include environment info**:
   - Python version
   - OS
   - Dependencies (from `pip freeze`)

### Example Bug Report

```markdown
# Bug: Cache not persisting between restarts

## Steps to Reproduce
1. Start API: `python main.py`
2. Make a search: `curl -X POST http://localhost:8000/search ...`
3. Check cache: `curl http://localhost:8000/cache/stats`
4. Stop API: Ctrl+C
5. Start API again
6. Check cache: `curl http://localhost:8000/cache/stats`

## Expected
Cache entry should still be present (TTL: 24h)

## Actual
Cache is empty after restart

## Environment
- Python 3.11.2
- macOS 12.6
- Cache enabled: true
- Cache dir: ./cache
```

---

## Feature Requests

### How to Request

Describe:
- **Problem**: What problem does this solve?
- **Solution**: How should it work?
- **Examples**: How would users use it?
- **Alternatives**: Other solutions you considered?

### Example Feature Request

```markdown
# Feature: Support for OpenAI GPT-4 synthesis

## Problem
Current synthesis only supports Gemini. Some users prefer GPT-4.

## Solution
Add `SynthesisProvider` for OpenAI (similar to Gemini provider)

## Example Usage
```python
{
  "query": "best Python practices",
  "enable_synthesis": true,
  "synthesis_provider": "openai",  # new field
  "synthesis_model": "gpt-4"       # new field
}
```

## Alternatives
- Users could deploy their own wrapper

---

## Legal & Licensing

### Apache 2.0 License

By contributing, you agree that your work is released under Apache 2.0.

**Important**:
- Don't include GPL or other copyleft code
- Don't copy from other projects without attribution
- Include proper license headers in new files

**File header**:
```python
"""
Module description.

Licensed under Apache License 2.0. See LICENSE for details.
"""
```

---

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open an Issue
- **Security**: Email maintainers privately
- **Chat**: (if we have a community Discord/Slack, mention here)

---

## Recognition

**Contributors are recognized in**:
- CHANGELOG.md
- GitHub contributor graphs
- Release notes

Thank you for contributing! ❤️

---

**Last Updated**: January 2026
