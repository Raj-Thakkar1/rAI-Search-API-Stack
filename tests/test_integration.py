import sys
import os
import asyncio
import pytest
import logging
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, orchestrator
from config import load_config
from synthesis import ZaiSynthesisProvider
from browser_fallback import TieredFetcher, PlaywrightConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntegrationTests")

# Load config
config = load_config()

# --- HELPER FIXTURES ---

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# --- REAL SERVICE TESTS ---

@pytest.mark.asyncio
async def test_real_zai_synthesis():
    """Test Z.ai synthesis with REAL API key (if available)."""
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        pytest.skip("ZAI_API_KEY not set")

    provider = ZaiSynthesisProvider(
        api_key=api_key,
        model=os.getenv("ZAI_MODEL") or "glm-4.7-flash",
        base_url=os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
    )
    
    try:
        response = await asyncio.wait_for(
            provider.generate(
                system_prompt="You are a helper.",
                user_prompt="Say 'Hello Integration Test' and nothing else."
            ),
            timeout=15.0
        )
        logger.info(f"Z.ai Response: {response}")
        assert "Hello" in response or "Integration" in response
    except asyncio.TimeoutError:
        pytest.fail("Z.ai integration timed out")
    except Exception as e:
        pytest.fail(f"Z.ai integration failed: {e}")

@pytest.mark.asyncio
async def test_real_browser_fetch():
    """Test Playwright fetching a real URL (headless)."""
    if not config.playwright:
        pytest.skip("Playwright config missing")
        
    fetcher = TieredFetcher(config.playwright)
    await fetcher.initialize()
    
    url = "https://example.com"
    try:
        html = await asyncio.wait_for(fetcher.fetch_url(url), timeout=15.0)
        assert html is not None
        assert "Example Domain" in html
    except asyncio.TimeoutError:
        pytest.fail("Real browser fetch timed out")
    except Exception as e:
        pytest.fail(f"Real browser fetch failed: {e}")
    finally:
        await fetcher.shutdown()

@pytest.mark.asyncio
async def test_real_search_api_end_to_end():
    """Test the full /search endpoint with a real query."""
    client = TestClient(app)
    
    # We need to ensure startup event runs correctly or orchestrator is init
    # TestClient doesn't always run @app.on_event("startup") automatically in some pytest setups
    # so we manually trigger it if needed, but TestClient usually handles lifespan.
    
    with TestClient(app) as client:
        payload = {
            "query": "What is the capital of France?",
            "max_results": 1,
            "deep_extract": False, # Keep it fast
            "enable_synthesis": True, # Test synthesis if possible
            "enable_chunking": False
        }
        
        response = client.post("/search", json=payload)
        
        if response.status_code == 500:
             pytest.fail(f"Server Error: {response.text}")
             
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == payload["query"]
        assert "results" in data
        assert isinstance(data["results"], list)
        
        # If synthesis worked
        if os.getenv("ZAI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            if data.get("answer"):
                logger.info(f"Generated Answer: {data['answer']}")
                assert len(data["answer"]) > 5
