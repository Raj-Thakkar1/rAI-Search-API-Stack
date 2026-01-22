# 📘 Deep Search API - Usage & Configuration Guide

This guide covers the operational details of the API, including configuration tuning, endpoint specifications, and client-side integration patterns.

---

## ⚙️ Configuration (`.env`)

The system behaves very differently depending on these settings. Tune them based on your hardware and latency requirements.

### Core Settings

| Variable | Default | Description | Impact |
| :--- | :--- | :--- | :--- |
| `GOOGLE_API_KEY` | *Required* | Gemini API Key. | Required for Reranking & Synthesis. |
| `SEARCH_TIMEOUT` | `30` | Max seconds for the entire request. | Increase to `60` if using deep extraction on slow networks. |
| `DEBUG` | `false` | Verbose logging. | Set `true` to see raw HTML fetch errors and RAG chunk boundaries. |

### Performance Tuning

| Variable | Default | Recommended for 1vCPU | Recommended for 4vCPU | Note |
| :--- | :--- | :--- | :--- | :--- |
| `MAX_BROWSERS` | `4` | `2` | `8` | Controls memory usage. |
| `CACHE_MAX_SIZE_MB`| `2000` | `1000` | `4000` | Disk space usage. Auto-cleans oldest entries when full. |
| `EXTRACTION_WORKERS`| `4` | `2` | `8` | Process pool size for CPU-intensive HTML parsing. |

---

## 📡 API Endpoints

### 1. `POST /search`

The primary engine. It supports both synchronous JSON responses and asynchronous Streaming (SSE).

#### Request Body (JSON)

```json
{
  "query": "Impact of quantum computing on cryptography",
  "max_results": 5,
  "deep_extract": true,
  "stream": false,
  "enable_reranking": true,
  "enable_chunking": true,
  "chunking_strategy": "hybrid"
}
```

#### Parameters Detail

*   **`max_results` (int, 1-20):**
    *   *Tip:* Keep this low (3-5) if `deep_extract` is `true`. Fetching and rendering 20 pages via Headless Chrome will likely hit the 30s timeout.
*   **`deep_extract` (bool):**
    *   `false`: Returns only the snippet and title provided by the search engine (Fast, <2s).
    *   `true`: Visits every URL, renders JS, and extracts full body text (Slow, 5-15s).
*   **`chunking_strategy` (enum):**
    *   `"markdown"`: Respects headers (`#`). Best for technical documentation.
    *   `"semantic"`: Uses embeddings to split by topic. Best for essays/blogs.
    *   `"hybrid"`: The safest default.

---

### 2. Streaming Response (Server-Sent Events)

For better UX, enable `stream: true`. The server will push events as they happen.

**Events:**
1.  `event: status` -> JSON data: `{"message": "Searching web..."}`
2.  `event: status` -> JSON data: `{"message": "Reading 5 pages..."}`
3.  `event: token` -> Raw string: `The` (Part of the synthesized answer)
4.  `event: token` -> Raw string: `future`
5.  `event: final` -> JSON data: `{ "results": [...], "sources": [...] }`

**Client Example (Python):**

```python
import requests
import sseclient  # pip install sseclient-py

url = "http://localhost:8000/search"
payload = {"query": "AI news", "stream": True}

response = requests.post(url, json=payload, stream=True)
client = sseclient.SSEClient(response)

for event in client.events():
    if event.event == "token":
        print(event.data, end="", flush=True)
    elif event.event == "final":
        print("\n[Done] Received full context.")
```

---

### 3. `GET /cache/stats`

Monitor the health of the file-based cache.

**Response:**
```json
{
  "stats": {
    "total_entries": 150,
    "total_size_mb": 45.2,
    "hit_rate": 0.65
  }
}
```
*Tip: If `hit_rate` is low, consider increasing `CACHE_TTL` in .env.*

---

## 🛡️ Production Best Practices

### 1. Security (Apache 2.0 Warning)
This API **does not** include authentication middleware by default.
*   **Do not expose port 8000 to the public internet.**
*   Use a reverse proxy (Nginx, Traefik, or Cloudflare Tunnel) to handle SSL and API Keys (Basic Auth or Bearer Token).

### 2. Rate Limiting
The app includes `slowapi` set to **30 requests/minute** by default to prevent abuse.
*   *Customize:* Edit `RATE_LIMIT` in `.env` (e.g., `RATE_LIMIT=100/minute`).
*   *Client handling:* If you receive `429 Too Many Requests`, implement an exponential backoff retry strategy.

### 3. Handling Timeouts
Complex queries with `deep_extract: true` can take 10-20 seconds.
*   **Client Timeout:** Ensure your HTTP client (axios, requests) has a timeout of at least **45 seconds**.
*   **Retry Logic:** If a request fails with `504 Gateway Timeout`, it usually means the target websites were slow. Retrying immediately often works if the specific slow URL was skipped or cached.

### 4. Docker Volume Persistence
When deploying via Docker, ensure the `/app/cache` volume is mounted to the host. Otherwise, you lose the cache (and the performance benefits) every time you restart the container.

```yaml
# docker-compose.yml
volumes:
  - ./my_local_cache:/app/cache
```