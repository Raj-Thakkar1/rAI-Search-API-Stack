"""
Playwright-based headless browser fallback for anti-blocking. 
Tiered fetching:  Fast (HTTPX) -> Slow (Playwright) -> Fail

Uses synchronous Playwright API in a thread pool to avoid Windows asyncio subprocess issues.
"""

import asyncio
import logging
import sys
import threading
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

import trafilatura
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from config import PlaywrightConfig

logger = logging.getLogger("BrowserFallback")


class SyncBrowserPool:
    """
    Manages Playwright browser instances using the synchronous API.
    Runs in a dedicated thread to avoid asyncio event loop issues on Windows.
    """
    
    def __init__(self, config: PlaywrightConfig):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self._lock = threading.Lock()
        self._initialized = False
    
    def initialize(self):
        """Initialize the browser pool (synchronous, called from thread)."""
        with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing Playwright browser (sync mode)")
            try:
                self.playwright = sync_playwright().start()
                
                # Build launch args, filtering out empty strings
                launch_args = [
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-sync",
                ]
                if self.config.disable_images:
                    launch_args.append("--disable-images")
                
                self.browser = self.playwright.chromium.launch(
                    headless=self.config.headless,
                    args=launch_args
                )
                self._initialized = True
                logger.info("Playwright browser initialized successfully (sync mode)")
            except Exception as e:
                logger.error(f"Failed to initialize Playwright: {e}")
                raise
    
    def fetch_with_js(self, url: str) -> Optional[str]:
        """
        Fetch URL with JavaScript rendering via Playwright (synchronous).
        Returns HTML content or None if failed.
        """
        if not self._initialized or not self.browser:
            logger.error("Browser not initialized")
            return None
        
        page: Optional[Page] = None
        try:
            page = self.browser.new_page(
                user_agent=self.config.user_agent
            )
            
            # Set timeout
            page.set_default_timeout(self.config.timeout_seconds * 1000)
            
            # Navigate
            page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout_seconds * 1000)
            
            # Get rendered HTML
            html = page.content()
            logger.info(f"Successfully rendered {url} with Playwright (sync)")
            return html
            
        except PlaywrightTimeoutError:
            logger.warning(f"Playwright timeout for {url}")
            return None
        except Exception as e:
            logger.error(f"Playwright fetch failed for {url}: {e}")
            return None
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
    
    def shutdown(self):
        """Cleanup browser pool."""
        with self._lock:
            logger.info("Shutting down browser pool (sync)")
            if self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
            
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
            
            self._initialized = False


class TieredFetcher:
    """
    Tiered fetching strategy:
    1. Fast HTTPX fetch (200ms)
    2. Fallback to Playwright (3-5s) - runs in thread pool
    3. Return None if both fail
    """
    
    def __init__(self, config: PlaywrightConfig):
        self.config = config
        self._browser_pool: Optional[SyncBrowserPool] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the fetcher."""
        # Create thread pool for Playwright operations
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_concurrent_browsers,
            thread_name_prefix="playwright"
        )
        
        # Initialize browser pool in thread
        self._browser_pool = SyncBrowserPool(self.config)
        
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(self._executor, self._browser_pool.initialize)
            self._initialized = True
            logger.info("TieredFetcher initialized with sync Playwright")
        except Exception as e:
            logger.error(f"Failed to initialize TieredFetcher: {e}")
            # Don't fail completely - we can still use Tier 1 (HTTP fetch)
            self._browser_pool = None
            self._initialized = True
            logger.warning("Continuing without Playwright fallback")
    
    async def fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL with fallback strategy.
        Try fast fetch first, then Playwright. 
        """
        # Tier 1: Fast HTTPX fetch via Trafilatura
        try:
            logger.debug(f"Tier 1: Fast fetch for {url}")
            html = await asyncio.wait_for(
                asyncio.to_thread(trafilatura.fetch_url, url),
                timeout=5.0
            )
            
            if html:
                logger.info(f"Tier 1 success for {url}")
                return html
            
        except asyncio.TimeoutError:
            logger.debug(f"Tier 1 timeout for {url}")
        except Exception as e:
            logger.debug(f"Tier 1 failed for {url}: {e}")
        
        # Tier 2: Playwright fallback (runs in thread pool)
        logger.debug(f"Tier 2: Playwright fallback for {url}")
        if self._browser_pool and self._executor:
            try:
                loop = asyncio.get_running_loop()
                html = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor,
                        self._browser_pool.fetch_with_js,
                        url
                    ),
                    timeout=self.config.timeout_seconds + 5  # Extra buffer for thread overhead
                )
                if html:
                    logger.info(f"Tier 2 success for {url}")
                    return html
            except asyncio.TimeoutError:
                logger.warning(f"Tier 2 timeout for {url}")
            except Exception as e:
                logger.error(f"Tier 2 failed for {url}: {e}")
        
        # Both tiers failed
        logger.error(f"All fetch strategies failed for {url}")
        return None
    
    async def shutdown(self):
        """Cleanup resources."""
        if self._browser_pool:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(self._executor, self._browser_pool.shutdown)
            except Exception as e:
                logger.warning(f"Error shutting down browser pool: {e}")
        
        if self._executor:
            self._executor.shutdown(wait=False)
            logger.info("Thread pool shut down")