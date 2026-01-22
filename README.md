# 🔍 Deep Search & Extraction API v3.0

**Production-grade semantic search engine with RAG pipeline, anti-blocking extraction, and autonomous query synthesis.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-yellow?style=flat-square)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](Dockerfile)

---

## 📖 Overview

Deep Search API is a middleware layer designed to turn the chaotic web into structured, LLM-ready context. It bridges the gap between simple keyword search and complex RAG (Retrieval Augmented Generation) applications.

Unlike simple wrapper libraries, this is a **stateful, fault-tolerant system** that handles:
1.  **Discovery:** Aggregating results from search providers (DuckDuckGo).
2.  **Acquisition:** Fetching content via tiered strategies (HTTP vs. Headless Browser).
3.  **Intelligence:** Reranking, cleaning, and chunking data for AI consumption.

---

## ⚠️ Legal & Ethical Disclaimer

**Please read this carefully before use.**

This software is released under the **Apache 2.0 License**. However, the *act* of web scraping and data extraction is subject to local laws (e.g., GDPR in Europe, CFAA in the US) and the Terms of Service of target websites.

1.  **Robots.txt:** This tool does **not** automatically adhere to `robots.txt` by default. It is the operator's responsibility to respect exclusion protocols where legally required.
2.  **Copyright:** Extracting full article content for commercial reproduction may infringe on copyright. This tool is intended for **factual extraction, analysis, and fair-use indexing**.
3.  **Rate Limiting:** Aggressive scraping can cause Denial of Service (DoS) to target servers. This API includes a `slowapi` rate limiter; do not disable it in production without understanding the consequences.
4.  **Liability:** The authors provide this software "as is" and hold no liability for how it is used. You are responsible for the traffic you generate.

---

## ✨ Core Capabilities

| Feature | Description | Tech Stack |
| :--- | :--- | :--- |
| **Semantic Reranking** | Re-orders search results by meaning, not just SEO keywords. | Google Gemini / Cross-Encoder |
| **Anti-Blocking** | Detects JS challenges (Cloudflare) and upgrades to a headless browser. | Playwright / Chromium |
| **Smart Chunking** | Splits text into context-aware segments for RAG. | Tiktoken / Transformers |
| **Auto-Caching** | 24h file-based persistence to save bandwidth and compute. | SHA-256 / File System |
| **Query Synthesis** | Deconstructs complex user questions into atomic sub-queries. | LLM / Regex |

---

## ⚡ Performance vs. Cost Matrix

Running this API involves trade-offs. Use this guide to tune your `.env`:

| Mode | `DEEP_EXTRACT` | `RERANKING` | Latency (avg) | Compute Cost | Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fast Lookup** | `False` | `False` | ~1.5s | Low | Chatbot tool calling |
| **Research** | `True` | `False` | ~5-8s | Medium | News aggregation |
| **Deep RAG** | `True` | `True` | ~10-15s | High (GPU/API) | Automated Report Generation |

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/deep-search-api.git
cd deep-search-api

# 2. Setup Env
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 3. Launch
docker-compose up --build -d
```

### Local Python Setup

```bash
# 1. Install Libs
pip install -r requirements.txt

# 2. Install Browsers (Critical)
playwright install chromium

# 3. Run
python main.py
```

---

## 📚 Documentation Map

*   **[QUICKSTART.md](docs/QUICKSTART.md)** - Getting started in 5 minutes.
*   **[USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - API parameters and endpoints.
*   **[FEATURES_IN_DEPTH.md](docs/FEATURES_IN_DEPTH.md)** - Architecture, internals, and pro-tips.
*   **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Scaling, security, and hardware sizing.

---

## 🛡️ License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.

Copyright (c) 2026 Deep Search Team.
