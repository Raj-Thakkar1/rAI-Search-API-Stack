import asyncio
import sys
from playwright.sync_api import sync_playwright

def test_playwright():
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    if sys.platform.startswith("win"):
        # The default in 3.12 should be Proactor
        loop_policy = asyncio.get_event_loop_policy()
        print(f"Current loop policy: {type(loop_policy).__name__}")
        
    try:
        with sync_playwright() as p:
            print("Launching browser...")
            browser = p.chromium.launch()
            print("Browser launched successfully!")
            page = browser.new_page()
            page.goto("https://example.com")
            print(f"Title: {page.title()}")
            browser.close()
            print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_playwright()
