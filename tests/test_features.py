import sys
import os
import asyncio
import pytest
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache_manager import FileBasedCache
from rag_chunker import RAGChunker, Chunk
from browser_fallback import TieredFetcher, PlaywrightConfig
from synthesis import ZaiSynthesisProvider, SynthesisChunk
from config import Config

# --- CACHE TESTS ---
@pytest.mark.asyncio
async def test_cache_manager():
    cache_dir = "tests/cache_test"
    config = MagicMock()
    config.enabled = True
    config.directory = cache_dir
    config.ttl_seconds = 60
    config.max_size_mb = 10
    
    cache = FileBasedCache(config)
    await cache.clear()
    
    key = "test_key"
    data = {"foo": "bar"}
    
    # Test Set
    await cache.set(key, data)
    
    # Test Get
    cached_data = await cache.get(key)
    assert cached_data == data
    
    # Test Clear
    await cache.clear()
    cached_data = await cache.get(key)
    assert cached_data is None

# --- CHUNKER TESTS ---
@pytest.mark.asyncio
async def test_rag_chunker():
    # Mock SentenceTransformer to prevent dependency issues during unit testing
    with patch("sentence_transformers.SentenceTransformer") as mock_transformer:
        mock_model = MagicMock()
        # Mock encode to return a list of dummy embeddings (numpy arrays)
        import numpy as np
        # Use side_effect to return correct number of embeddings
        mock_model.encode.side_effect = lambda s: [np.array([0.1, 0.2]) for _ in range(len(s))]
        mock_transformer.return_value = mock_model
        
        chunker = RAGChunker(strategy="hybrid", target_chunk_size=50, overlap_tokens=0)
        
        # We also need to ensure tokenizer works or is mocked if tiktoken missing, 
        # but RAGChunker handles tiktoken missing gracefully.
        
        text = "This is a test sentence. " * 20 
        
        result = await chunker.chunk(text)
        assert result.success is True, f"Chunking failed: {result.message}"
        assert len(result.chunks) > 0
        assert isinstance(result.chunks[0], Chunk)

# --- SYNTHESIS TESTS (Z.ai) ---
@pytest.mark.asyncio
async def test_zai_provider():
    api_key = "test_key"
    provider = ZaiSynthesisProvider(api_key=api_key, model="glm-4.7-flash")
    
    # Mock OpenAI client with AsyncMock
    with patch("openai.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock chat.completions.create to be async
        mock_create = MagicMock()
        mock_client.chat.completions.create = mock_create
        
        # Setup return value for generate()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Test response"))
        ]
        
        # Make the return value awaitable
        future = asyncio.Future()
        future.set_result(mock_response)
        mock_create.return_value = future
        
        response = await provider.generate("System", "User")
        assert response == "Test response"
        
        # Verify correct args passed (base_url check)
        mock_openai.assert_called_with(api_key=api_key, base_url="https://api.z.ai/api/paas/v4/")

# --- BROWSER FALLBACK TESTS (Mocked) ---
@pytest.mark.asyncio
async def test_tiered_fetcher():
    config = PlaywrightConfig(
        headless=True,
        allowed_domains=["example.com"],
        timeout_seconds=5,
        user_agent="TestBot",
        max_concurrent_browsers=1,
        disable_images=True
    )
    
    fetcher = TieredFetcher(config)
    
    # Mock Trafilatura (Tier 1)
    with patch("trafilatura.fetch_url", return_value="<html>Tier 1</html>"):
        html = await fetcher.fetch_url("http://example.com")
        assert html == "<html>Tier 1</html>"

# --- RERANKER TESTS (Mocked) ---
@pytest.mark.asyncio
async def test_reranker_initialization():
    # Patch the classes where they are IMPORTED in reranker.py
    with patch("reranker.GoogleGeminiEmbedding"), \
         patch("reranker.LocalCrossEncoderEmbedding"), \
         patch("reranker.GemmaFallbackReranker"):
             
        from reranker import SemanticReranker
        reranker = SemanticReranker(MagicMock(), MagicMock(), MagicMock())
        assert reranker is not None
