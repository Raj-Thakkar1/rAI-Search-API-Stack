"""
Playwright-based headless browser fallback for anti-blocking. 
Tiered fetching:  Fast (HTTPX) -> Slow (Playwright) -> Fail
"""

import asyncio
import logging
from typing import Optional, List
from concurrent.futures import ProcessPoolExecutor

import trafilatura
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from config import PlaywrightConfig

logger = logging.getLogger("BrowserFallback")

class BrowserPool:
    """
    Manages a pool of Playwright browser instances.
    Prevents thread blocking by using a dedicated executor.
    """
    
    def __init__(self, config: PlaywrightConfig):
        self.config = config
        self.browsers: List[Browser] = []
        self.page_semaphore = asyncio.Semaphore(config.max_concurrent_browsers)
    
    async def initialize(self):
        """Initialize the browser pool."""
        logger.info(f"Initializing {self.config.max_concurrent_browsers} Playwright browsers")
        self.playwright = await async_playwright().start()
        
        # Pre-launch browsers
        for _ in range(self.config.max_concurrent_browsers):
            try:
                browser = await self.playwright.chromium.launch(
                    headless=self.config.headless,
                    args=[
                        "--disable-images" if self.config.disable_images else "",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-sync",
                    ]
                )
                self.browsers.append(browser)
            except Exception as e:
                logger.warning(f"Failed to pre-launch browser: {e}")
        
        logger.info(f"Browser pool initialized with {len(self. browsers)} browsers")
    
    async def fetch_with_js(self, url: str) -> Optional[str]:
        """
        Fetch URL with JavaScript rendering via Playwright.
        Returns HTML content or None if failed.
        """
        async with self.page_semaphore:  # Limit concurrent pages
            browser = self.browsers[0] if self.browsers else None
            if not browser:
                logger.error("No available browser in pool")
                return None
            
            page:  Optional[Page] = None
            try:
                page = await browser.new_page(
                    user_agent=self.config.user_agent
                )
                
                # Set timeout
                page.set_default_timeout(self.config.timeout_seconds * 1000)
                
                # Navigate with timeout
                await asyncio.wait_for(
                    page.goto(url, wait_until="domcontentloaded"),
                    timeout=self.config.timeout_seconds
                )
                
                # Wait for network idle (optional, can be removed for speed)
                # await page.wait_for_load_state("networkidle", timeout=5000)
                
                # Get rendered HTML
                html = await page.content()
                logger.info(f"Successfully rendered {url} with Playwright")
                return html
                
            except PlaywrightTimeoutError:
                logger.warning(f"Playwright timeout for {url}")
                return None
            except asyncio.TimeoutError:
                logger.warning(f"Asyncio timeout for {url}")
                return None
            except Exception as e:
                logger.error(f"Playwright fetch failed for {url}: {e}")
                return None
            finally: 
                if page:
                    await page.close()
    
    async def shutdown(self):
        """Cleanup browser pool."""
        logger.info("Shutting down browser pool")
        for browser in self.browsers:
            try:
                await browser.close()
            except Exception as e: 
                logger.warning(f"Error closing browser: {e}")
        
        await self.playwright.stop()

class TieredFetcher:
    """
    Tiered fetching strategy:
    1. Fast HTTPX fetch (200ms)
    2. Fallback to Playwright (3-5s)
    3. Return None if both fail
    """
    
    def __init__(self, config: PlaywrightConfig):
        self.config = config
        self.browser_pool:  Optional[BrowserPool] = None
    
    async def initialize(self):
        """Initialize the fetcher."""
        self.browser_pool = BrowserPool(self.config)
        await self.browser_pool.initialize()
    
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
                logger. info(f"Tier 1 success for {url}")
                return html
            
        except asyncio.TimeoutError:
            logger.debug(f"Tier 1 timeout for {url}")
        except Exception as e:
            logger. debug(f"Tier 1 failed for {url}: {e}")
        
        # Tier 2: Playwright fallback
        logger.debug(f"Tier 2: Playwright fallback for {url}")
        if self.browser_pool:
            try:
                html = await self.browser_pool.fetch_with_js(url)
                if html:
                    logger.info(f"Tier 2 success for {url}")
                    return html
            except Exception as e:
                logger.error(f"Tier 2 failed for {url}: {e}")
        
        # Both tiers failed
        logger.error(f"All fetch strategies failed for {url}")
        return None
    
    async def shutdown(self):
        """Cleanup resources."""
        if self.browser_pool:
            await self.browser_pool.shutdown()