"""
Configuration management for the Deep Search & Extraction API. 
Centralized settings for all modules. 
"""

import os
from typing import Literal
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class GoogleEmbeddingConfig(BaseModel):
    """Google Gemini Embedding API configuration."""
    api_key: str
    model:  str = "models/embedding-001"  # gemini-embedding-1. 0
    
class GoogleFallbackConfig(BaseModel):
    """Google Gemma fallback model configuration."""
    api_key: str
    model:  str = "google/gemma-3-27b"  # Fallback for reranking if embedding fails
    max_tokens: int = 150
    temperature: float = 0.3

class PlaywrightConfig(BaseModel):
    """Playwright browser automation configuration."""
    timeout_seconds: int = 30
    headless: bool = True
    disable_images: bool = True  # Faster rendering
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    max_concurrent_browsers: int = 4  # For 1vCPU, 16GB RAM

class CacheConfig(BaseModel):
    """File-based caching configuration."""
    enabled: bool = True
    cache_dir: str = "./cache"
    ttl_seconds: int = 86400  # 24 hours
    max_cache_size_mb: int = 2000  # 2GB for 16GB RAM machine
    
class ChunkingConfig(BaseModel):
    """RAG-ready chunking configuration."""
    strategy: Literal["markdown", "semantic", "hybrid"] = "hybrid"
    target_chunk_size: int = 350  # tokens, roughly 250-400 words
    overlap_tokens: int = 50  # For context continuity
    tokenizer:  str = "gpt2"  # Using tiktoken

class RerankerConfig(BaseModel):
    """Semantic reranking configuration."""
    enabled: bool = True
    cloud_model: str = "models/embedding-001"  # Google Gemini
    local_fallback_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    use_cloud:  bool = True  # Try cloud first
    
class SearchConfig(BaseModel):
    """Global search configuration."""
    max_results: int = 20
    max_results_to_rerank: int = 10  # User can override
    search_timeout_seconds: int = 30
    
class Config(BaseModel):
    """Master configuration class."""
    google_embedding: GoogleEmbeddingConfig
    google_fallback:  GoogleFallbackConfig
    playwright: PlaywrightConfig
    cache: CacheConfig
    chunking: ChunkingConfig
    reranker: RerankerConfig
    search: SearchConfig
    debug: bool = False

# Load from environment
def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config(
        google_embedding=GoogleEmbeddingConfig(
            api_key=os.getenv("GOOGLE_API_KEY", ""),
        ),
        google_fallback=GoogleFallbackConfig(
            api_key=os.getenv("GOOGLE_API_KEY", ""),
        ),
        playwright=PlaywrightConfig(
            timeout_seconds=int(os.getenv("PLAYWRIGHT_TIMEOUT", "30")),
            max_concurrent_browsers=int(os.getenv("MAX_BROWSERS", "4")),
        ),
        cache=CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            cache_dir=os.getenv("CACHE_DIR", "./cache"),
            ttl_seconds=int(os.getenv("CACHE_TTL", "86400")),
        ),
        chunking=ChunkingConfig(
            strategy=os.getenv("CHUNKING_STRATEGY", "hybrid"),
            target_chunk_size=int(os.getenv("CHUNK_SIZE", "350")),
        ),
        reranker=RerankerConfig(
            use_cloud=os.getenv("RERANKER_USE_CLOUD", "true").lower() == "true",
        ),
        search=SearchConfig(
            search_timeout_seconds=int(os.getenv("SEARCH_TIMEOUT", "30")),
        ),
        debug=os.getenv("DEBUG", "false").lower() == "true",
    )

# Global config instance
config = load_config()