# ⚡ Quick Start Guide

Get the Deep Search API running in under 5 minutes.

## 🛠️ Prerequisites

Before you begin, ensure you have the following:

1.  **Google Gemini API Key:** Required for the semantic reranking and synthesis features.
    *   *Get it here:* [Google AI Studio](https://aistudio.google.com/) (Free tier available).
2.  **Runtime Environment:**
    *   **Option A (Recommended):** Docker & Docker Compose.
    *   **Option B (Manual):** Python 3.10+ and Node.js (for some Playwright deps).

---

## 📦 Option A: Docker (Production-Ready)

This is the cleanest way to run the API, as it handles the complex Playwright browser dependencies automatically.

### 1. Clone & Configure
```bash
git clone https://github.com/yourusername/deep-search-api.git
cd deep-search-api

# Create configuration file
cp .env.example .env
```

### 2. Add API Keys
Open `.env` in your editor and set your key:
```ini
GOOGLE_API_KEY=AIzaSy...
```

### 3. Launch
```bash
docker-compose up --build -d
```
*Note: The first build may take 2-3 minutes to download the base Python image and Chromium browsers.*

---

## 🐍 Option B: Local Python (Development)

Use this if you want to modify the code or debug locally.

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Headless Browsers (Critical)
The API will fail if you skip this step.
```bash
playwright install chromium
```
*Pro Tip: You don't need firefox or webkit, just chromium is enough.*

### 3. Configuration
```bash
# Windows (PowerShell)
copy .env.example .env

# Linux/Mac
cp .env.example .env
```
*Edit `.env` to add your `GOOGLE_API_KEY`.*

### 4. Start the Server
```bash
python main.py
```
*Do not use `uvicorn main:app` directly from the CLI on Windows. `python main.py` ensures the correct AsyncIO event loop is loaded for Playwright.*

---

## ✅ Verification

Once running (default port `8000`), run this smoke test to ensure the full pipeline (Search -> Fetch -> Rerank -> Chunk) is working.

**Linux/Mac (Curl):**
```bash
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "deep learning vs machine learning", "max_results": 3, "deep_extract": true}'
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/search" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"query": "deep learning vs machine learning", "max_results": 3, "deep_extract": true}'
```

---

## 🛑 Common Startup Issues

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `BrowserType.launch: Executable doesn't exist` | Playwright not installed. | Run `playwright install chromium`. |
| `NotImplementedError` (Windows) | Wrong Event Loop. | Run via `python main.py`, not `uvicorn`. |
| `401 Unauthorized` (Logs) | Invalid Google API Key. | Check `.env` and restart server. |
| Server hangs on search | First run warm-up. | The first request initializes models; give it 10s. |

---

## ⚖️ Next Steps

*   Explore the full capabilities in **[USAGE_GUIDE.md](USAGE_GUIDE.md)**.
*   Understand the architecture in **[FEATURES_IN_DEPTH.md](FEATURES_IN_DEPTH.md)**.