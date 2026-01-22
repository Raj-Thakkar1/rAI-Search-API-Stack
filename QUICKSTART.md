# Quick Start Guide - Deep Search API v2.0

Get up and running in 5 minutes!  🚀

## Prerequisites

- Docker installed
- Google API key (get from [Google Cloud Console](https://console.cloud.google.com/))

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/deep-search-api.git
cd deep-search-api

## Step 2: Configure & Run

```bash
# Copy example env
cp .env.example .env
# Edit .env to add GOOGLE_API_KEY
# ...

# Run server
python main.py
```

## Step 3: Verify Installation

```bash
# Run self-check tests
python tests/run_tests.py
```

**That's it!** API is running at `http://localhost:8000`.