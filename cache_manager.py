"""
File-based caching system with automatic TTL, stats tracking, and content deduplication.
Uses SHA-256 hashing for efficient storage. 
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel

from config import CacheConfig

logger = logging.getLogger("CacheManager")

class CacheEntry(BaseModel):
    """Single cache entry with metadata."""
    key: str
    data: Dict[str, Any]
    timestamp:  str  # ISO format
    ttl_seconds: int
    size_bytes: int
    content_hash: str  # For deduplication

class CacheStats(BaseModel):
    """Cache statistics."""
    total_entries: int
    total_size_mb: float
    hit_count: int
    miss_count:  int
    hit_rate: float
    oldest_entry: Optional[str]  # ISO timestamp
    newest_entry: Optional[str]  # ISO timestamp

class FileBasedCache:
    """
    File-based cache with: 
    - TTL-based expiration (24h default)
    - Content addressable storage (dedupe)
    - Automatic cleanup
    - Hit/miss tracking
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.hit_count = 0
        self.miss_count = 0
        
        # Persistent stats file
        self.stats_file = self.cache_dir / ". cache_stats. json"
        self._load_stats()
        
        logger.info(f"Cache initialized at {self.cache_dir}")
    
    def _load_stats(self):
        """Load persistent hit/miss stats."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    stats = json.load(f)
                    self.hit_count = stats.get('hit_count', 0)
                    self.miss_count = stats.get('miss_count', 0)
            except Exception as e:
                logger.warning(f"Failed to load cache stats: {e}")
    
    def _save_stats(self):
        """Save persistent hit/miss stats."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump({
                    'hit_count':  self.hit_count,
                    'miss_count': self. miss_count,
                    'last_updated': datetime.utcnow().isoformat()
                }, f)
        except Exception as e:
            logger. warning(f"Failed to save cache stats: {e}")
    
    def _hash_key(self, key: str) -> str:
        """Generate SHA-256 hash of cache key."""
        return hashlib. sha256(key.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        key_hash = self._hash_key(key)
        return self. cache_dir / f"{key_hash}.json"
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data. 
        Returns None if not found, expired, or error.
        """
        try:
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                self.miss_count += 1
                self._save_stats()
                logger.debug(f"Cache miss: {key}")
                return None
            
            # Read cache entry
            async_read = await asyncio.to_thread(
                lambda: json.loads(cache_path.read_text())
            )
            entry = CacheEntry(**async_read)
            
            # Check expiration
            timestamp = datetime.fromisoformat(entry.timestamp)
            age_seconds = (datetime.utcnow() - timestamp).total_seconds()
            
            if age_seconds > entry.ttl_seconds:
                logger.debug(f"Cache expired: {key} (age: {age_seconds}s)")
                self.miss_count += 1
                self._save_stats()
                
                # Delete expired entry
                await asyncio.to_thread(cache_path.unlink)
                return None
            
            self. hit_count += 1
            self._save_stats()
            logger.debug(f"Cache hit: {key}")
            return entry. data
            
        except Exception as e:
            logger.error(f"Cache get failed for {key}: {e}")
            self.miss_count += 1
            self._save_stats()
            return None
    
    async def set(
        self,
        key: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store data in cache. 
        """
        try:
            ttl = ttl_seconds or self.config.ttl_seconds
            
            # Compute content hash for deduplication
            content_str = json.dumps(data, sort_keys=True)
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()
            
            entry = CacheEntry(
                key=key,
                data=data,
                timestamp=datetime.utcnow().isoformat(),
                ttl_seconds=ttl,
                size_bytes=len(content_str.encode()),
                content_hash=content_hash
            )
            
            cache_path = self._get_cache_path(key)
            
            # Write async
            await asyncio.to_thread(
                lambda: cache_path.write_text(entry.model_dump_json())
            )
            
            logger.debug(f"Cache set: {key}")
            
            # Check size and cleanup if needed
            await self._cleanup_if_needed()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed for {key}: {e}")
            return False
    
    async def _cleanup_if_needed(self):
        """Remove old entries if cache exceeds max size."""
        try:
            total_size = 0
            entries = []
            
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name == ".cache_stats.json": 
                    continue
                
                size = cache_file.stat().st_size
                total_size += size
                
                # Get timestamp from metadata
                try:
                    data = json.loads(cache_file.read_text())
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    entries.append((cache_file, timestamp, size))
                except:
                    pass
            
            max_bytes = self.config.max_cache_size_mb * 1024 * 1024
            
            if total_size > max_bytes: 
                logger.info(
                    f"Cache size ({total_size / 1024 / 1024:. 1f}MB) exceeds max.  "
                    f"Cleaning up oldest entries..."
                )
                
                # Sort by timestamp (oldest first)
                entries.sort(key=lambda x: x[1])
                
                # Delete oldest until under limit
                for cache_file, _, size in entries:
                    if total_size <= max_bytes * 0.9:  # Clean to 90%
                        break
                    
                    try:
                        cache_file.unlink()
                        total_size -= size
                        logger.debug(f"Deleted old cache entry: {cache_file. name}")
                    except Exception as e:
                        logger. warning(f"Failed to delete cache file: {e}")
        
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")
    
    async def get_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        try:
            total_size = 0
            timestamps = []
            entry_count = 0
            
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name == ".cache_stats.json": 
                    continue
                
                size = cache_file.stat().st_size
                total_size += size
                entry_count += 1
                
                try:
                    data = json.loads(cache_file. read_text())
                    timestamps.append(data['timestamp'])
                except: 
                    pass
            
            hit_rate = (
                self.hit_count / (self.hit_count + self.miss_count)
                if (self.hit_count + self. miss_count) > 0
                else 0.0
            )
            
            oldest = min(timestamps) if timestamps else None
            newest = max(timestamps) if timestamps else None
            
            return CacheStats(
                total_entries=entry_count,
                total_size_mb=total_size / 1024 / 1024,
                hit_count=self.hit_count,
                miss_count=self.miss_count,
                hit_rate=hit_rate,
                oldest_entry=oldest,
                newest_entry=newest
            )
        
        except Exception as e: 
            logger.error(f"Failed to compute cache stats: {e}")
            return CacheStats(
                total_entries=0,
                total_size_mb=0.0,
                hit_count=self.hit_count,
                miss_count=self.miss_count,
                hit_rate=0.0,
                oldest_entry=None,
                newest_entry=None
            )
    
    async def clear(self):
        """Clear all cache entries."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != ".cache_stats.json": 
                    await asyncio.to_thread(cache_file.unlink)
            
            logger.info("Cache cleared")
            return True
        except Exception as e: 
            logger.error(f"Cache clear failed: {e}")
            return False