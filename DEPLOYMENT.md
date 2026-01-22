# DEPLOYMENT.md — Production Deployment & Scaling

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Docker Deployment](#docker-deployment)
4. [Environment Hardening](#environment-hardening)
5. [Scaling Strategies](#scaling-strategies)
6. [Cloud Deployment Patterns](#cloud-deployment-patterns)
7. [API Gateway Integration](#api-gateway-integration)
8. [Caching in Production](#caching-in-production)
9. [Rate Limiting & Abuse Prevention](#rate-limiting--abuse-prevention)
10. [Observability & Logging](#observability--logging)
11. [Security Best Practices](#security-best-practices)
12. [Cost Optimization](#cost-optimization)
13. [Disaster Recovery](#disaster-recovery)

---

## Overview

This guide assumes:
- **Target**: Production environment (AWS, GCP, Azure, or bare metal)
- **Scale**: 1vCPU + 12-16GB RAM to start
- **Load**: 30-100 requests/minute
- **Users**: Internal API, not public-facing (add auth layer)

---

## Pre-Deployment Checklist

### Security

- [ ] API keys stored in secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] `.env` file is in `.gitignore` and **never committed**
- [ ] HTTPS/TLS enabled at reverse proxy (nginx, CloudFront)
- [ ] Authentication layer added (JWT, API keys, OAuth2)
- [ ] CORS policy configured (restrict origins)
- [ ] Rate limiting enabled (30/minute or adjusted)
- [ ] Input validation on query length (<500 chars)
- [ ] Firewall rules restrict API access to trusted networks

### Performance

- [ ] Cache TTL tuned for use case (24h default)
- [ ] Max cache size configured for disk space
- [ ] Browser pool size appropriate (MAX_BROWSERS=4)
- [ ] Playwright timeout set reasonably (30s default)
- [ ] Search timeout ≥ Playwright timeout + fetching overhead

### Reliability

- [ ] Health check configured (`/health` endpoint)
- [ ] Logging enabled and shipped to centralized logging (CloudWatch, ELK)
- [ ] Monitoring/alerting set up (CPU, memory, error rate)
- [ ] Error budgets defined
- [ ] Rollback plan documented
- [ ] Backup/snapshot strategy for cache directory

### Compliance

- [ ] Legal review completed (scraping terms)
- [ ] Privacy policy updated if caching user queries
- [ ] Data retention policy defined
- [ ] GDPR/CCPA compliance verified for your use case
- [ ] robots.txt compliance configured

---

## Docker Deployment

### Build Production Image

```bash
# Build with buildkit for caching
DOCKER_BUILDKIT=1 docker build \
  -t rai-search-api:v3.0 \
  -t rai-search-api:latest \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  .
```

### Run Container

```bash
docker run -d \
  --name rai-search-api \
  --restart unless-stopped \
  -e GOOGLE_API_KEY="your-key-here" \
  -e CACHE_ENABLED="true" \
  -e CACHE_DIR="/app/cache" \
  -e CACHE_MAX_SIZE_MB="2000" \
  -e DEBUG="false" \
  -p 8000:8000 \
  -v rai-cache:/app/cache \
  -v rai-logs:/app/logs \
  --memory="14g" \
  --cpus="1" \
  rai-search-api:latest
```

### Environment Variables (Production)

```bash
# Secrets (use secrets manager, NOT hardcoded)
GOOGLE_API_KEY="$(aws secretsmanager get-secret-value --secret-id rai-api-keys --query 'SecretString' | jq -r '.google_api_key')"

# Cache tuning
CACHE_ENABLED="true"
CACHE_DIR="/app/cache"           # Persistent volume
CACHE_TTL="604800"                # 1 week for evergreen content
CACHE_MAX_SIZE_MB="2000"          # Adjust for disk size

# Browser tuning
PLAYWRIGHT_TIMEOUT="40"            # Conservative
MAX_BROWSERS="4"                  # Depends on RAM (1 browser ≈ 200MB)

# Search tuning
SEARCH_TIMEOUT="60"               # Allow 30s buffer
RERANKER_USE_CLOUD="true"        # Use Gemini if key available

# Chunking
CHUNKING_STRATEGY="hybrid"        # Balanced default
CHUNK_SIZE="350"

# Logging
DEBUG="false"                     # Never true in production
LOG_LEVEL="INFO"
```

### Health Check (Docker)

```yaml
# In docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s                # Wait for Playwright init
```

---

## Environment Hardening

### 1. Reverse Proxy (nginx)

```nginx
upstream rai_api {
    server localhost:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL/TLS
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # CORS
    add_header Access-Control-Allow-Origin "https://app.example.com" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;

    # Rate limiting (nginx level)
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
    limit_req zone=api_limit burst=5 nodelay;

    # Proxy
    location / {
        # Authentication (basic auth or JWT)
        auth_basic "Restricted API";
        auth_basic_user_file /etc/nginx/.htpasswd;

        proxy_pass http://rai_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Cache static responses
    location ~* ^/health$ {
        proxy_pass http://rai_api;
        proxy_cache_valid 200 10s;
        proxy_cache api_cache;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

### 2. Firewall Rules (AWS Security Group)

```
Inbound:
  - Port 443: From CloudFront or known IPs (not 0.0.0.0/0)
  - Port 8000: From nginx server only
  - Port 22: From bastion host only

Outbound:
  - Port 443: To Google APIs (googleapis.com)
  - Port 443: To DuckDuckGo (duckduckgo.com)
  - Port 53: To DNS resolver
  - All ports: Within VPC
```

### 3. File System Permissions

```bash
# Cache directory (owned by container)
chown -R 1000:1000 /var/lib/rai-cache
chmod 700 /var/lib/rai-cache

# Logs directory
mkdir -p /var/log/rai-api
chmod 755 /var/log/rai-api
```

### 4. Secrets Management

**Never store secrets in environment variables or code:**

```bash
# Option 1: AWS Secrets Manager
aws secretsmanager create-secret \
  --name rai-api-keys \
  --secret-string '{"google_api_key":"...","openai_api_key":"..."}'

# Option 2: HashiCorp Vault
vault kv put secret/rai-api google_api_key="..."

# Option 3: .env file (git-ignored, only on disk)
echo ".env" >> .gitignore
cat > .env << EOF
GOOGLE_API_KEY="..."
EOF
```

---

## Scaling Strategies

### Vertical Scaling (Single Instance)

**For 100-500 requests/minute:**

```bash
# Increase resources
Memory: 16GB → 32GB
CPU: 1 vCPU → 2-4 vCPU
Disk: 50GB → 200GB (for cache)

# Adjust configuration
MAX_BROWSERS=8              # More concurrent browsers
CACHE_MAX_SIZE_MB=5000      # Larger cache
SEARCH_TIMEOUT=90           # More time for complex queries
```

### Horizontal Scaling (Multiple Instances)

**For >500 requests/minute:**

#### Option A: File-Based Cache (Shared NFS)

```
┌─────────────┐
│   nginx     │
│ Load Balancer
└──────┬──────┘
       │
   ┌───┴────┬────────┬────────┐
   ↓        ↓        ↓        ↓
 [API 1] [API 2] [API 3] [API 4]
   │        │        │        │
   └────────┼────────┼────────┘
            │
        [NFS Mount]
        /shared/cache/
```

**Setup**:
```bash
# On NFS server (AWS EFS)
# Mount on all instances
mount -t nfs4 nfs-server:/cache /mnt/cache

# In .env
CACHE_DIR="/mnt/cache"

# Concern: NFS latency on cache hits (~50ms vs. 10ms local)
```

#### Option B: Redis Cache (Recommended)

```
┌─────────────┐
│   nginx     │ Load Balancer
└──────┬──────┘
       │
   ┌───┴────┬────────┬────────┐
   ↓        ↓        ↓        ↓
 [API 1] [API 2] [API 3] [API 4]
   └────────┼────────┼────────┘
            │
        [Redis Cluster]
     (in-memory cache)
```

**Setup**:
```bash
# Modify cache_manager.py to use Redis (requires code change)
# Or use external caching layer

# Docker Compose with Redis
services:
  rai-api:
    image: rai-search-api:latest
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
```

**Benefits**: Sub-millisecond hits, shared across instances

### Horizontal Scaling (Load Balancing)

**nginx configuration for multiple backends:**

```nginx
upstream rai_api_cluster {
    least_conn;                    # Least connections algorithm
    server api1.internal:8000;
    server api2.internal:8000;
    server api3.internal:8000;
    server api4.internal:8000;
    
    keepalive 32;                 # Connection pooling
}

server {
    location / {
        proxy_pass http://rai_api_cluster;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

---

## Cloud Deployment Patterns

### AWS ECS (Recommended)

```yaml
# task-definition.json
{
  "family": "rai-search-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "14336",
  "containerDefinitions": [
    {
      "name": "rai-api",
      "image": "ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/rai-search-api:v3.0",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "CACHE_ENABLED", "value": "true"},
        {"name": "DEBUG", "value": "false"}
      ],
      "secrets": [
        {
          "name": "GOOGLE_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:rai/google-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rai-search-api",
          "awslogs-region": "REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**Deploy**:
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service \
  --cluster rai-production \
  --service-name rai-api \
  --task-definition rai-search-api:1 \
  --desired-count 4 \
  --load-balancers targetGroupArn=arn:aws:...,containerName=rai-api,containerPort=8000
```

### Kubernetes (Advanced)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rai-search-api
spec:
  replicas: 4
  selector:
    matchLabels:
      app: rai-search-api
  template:
    metadata:
      labels:
        app: rai-search-api
    spec:
      containers:
      - name: api
        image: rai-search-api:v3.0
        ports:
        - containerPort: 8000
        env:
        - name: CACHE_ENABLED
          value: "true"
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: rai-secrets
              key: google-api-key
        resources:
          requests:
            memory: "12Gi"
            cpu: "1"
          limits:
            memory: "14Gi"
            cpu: "1.2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: cache
          mountPath: /app/cache
      volumes:
      - name: cache
        persistentVolumeClaim:
          claimName: rai-cache-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: rai-search-api
spec:
  selector:
    app: rai-search-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Deploy**:
```bash
kubectl apply -f deployment.yaml
kubectl autoscale deployment rai-search-api --min=4 --max=20 --cpu-percent=70
```

---

## API Gateway Integration

### AWS API Gateway

```python
# Add to main.py for AWS integration
from mangum import Mangum

handler = Mangum(app)

# Deploy with: serverless deploy
# Or use AWS Console to create REST API → Lambda
```

### CloudFlare Workers (Edge Caching)

```javascript
// wrangler.toml
name = "rai-search-proxy"
main = "src/index.js"

[env.production]
routes = [{pattern = "api.example.com/*"}]

// src/index.js
export default {
  async fetch(request) {
    // Cache GET /health for 10s
    if (request.url.includes("/health")) {
      const response = await fetch(request);
      return new Response(response.body, {
        ...response,
        headers: {
          ...response.headers,
          "Cache-Control": "max-age=10"
        }
      });
    }
    
    return fetch(request);
  }
};
```

---

## Caching in Production

### Cache Warming

Pre-populate cache with common searches:

```python
# warm_cache.py
import asyncio
from main import orchestrator, SearchRequest

async def warm_cache():
    queries = [
        "Python best practices",
        "machine learning tutorials",
        "web development frameworks"
    ]
    
    for query in queries:
        request = SearchRequest(query=query, max_results=5)
        async for _ in orchestrator.stream_answer_engine(request):
            pass
        print(f"Warmed: {query}")

if __name__ == "__main__":
    asyncio.run(warm_cache())
```

**Run on deployment:**
```bash
python warm_cache.py
```

### Cache Invalidation

Strategies for keeping cache fresh:

```bash
# 1. Time-based (default, 24h TTL)
CACHE_TTL=86400

# 2. Manual invalidation on content updates
curl -X POST http://localhost:8000/cache/clear

# 3. Partial invalidation (requires code change)
# Add endpoint to clear specific patterns: /cache/clear?pattern=python*

# 4. Webhook-based invalidation
# Listen for updates from source sites (if available)
```

---

## Rate Limiting & Abuse Prevention

### Application-Level Rate Limiting

```bash
# .env
RATE_LIMIT=30/minute              # 30 requests per minute

# Per-IP limiting (add to nginx)
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
limit_req zone=api_limit burst=5 nodelay;
```

### DDoS Protection

```bash
# Option 1: CloudFlare
# Enable in CloudFlare dashboard: Security → DDoS Protection → High

# Option 2: AWS WAF
wafv2_rules:
  - RateLimitRule:
      Limit: 2000
      AggregateKeyType: IP
  - GeoBlockingRule:
      BlockedCountries: [KP, IR]  # Example: block specific countries
```

### Query Validation

```python
# In main.py
@app.post("/search")
async def search(payload: SearchRequest):
    # Validate query length
    if len(payload.query) > 500:
        raise HTTPException(status_code=400, detail="Query too long")
    
    # Validate max_results
    if payload.max_results > 20:
        raise HTTPException(status_code=400, detail="max_results too high")
    
    # Anti-SQL injection (pydantic does this by default)
    # Anti-XSS: query is treated as string, never rendered as HTML
```

---

## Observability & Logging

### Centralized Logging

**AWS CloudWatch**:
```python
# Update logging in main.py
import watchtower
import logging

logger = logging.getLogger("DeepSearchAPI")
logger.addHandler(watchtower.CloudWatchLogHandler())
```

**Configuration**:
```bash
# Send logs to CloudWatch
docker run -e AWS_REGION=us-west-2 \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  rai-search-api:latest
```

### Metrics & Monitoring

**Prometheus**:
```python
# Add to main.py
from prometheus_client import Counter, Histogram, start_http_server

search_counter = Counter('rai_searches_total', 'Total searches')
search_duration = Histogram('rai_search_duration_seconds', 'Search duration')
cache_hit_rate = Gauge('rai_cache_hit_rate', 'Cache hit rate')

@app.post("/search")
async def search(...):
    with search_duration.time():
        result = await orchestrator.stream_answer_engine(payload)
    search_counter.inc()
    return result
```

**Scrape config** (Prometheus):
```yaml
scrape_configs:
  - job_name: 'rai-api'
    static_configs:
      - targets: ['localhost:8001']  # Metrics exposed on :8001
```

### Alerting

**Alert examples** (Prometheus AlertManager):
```yaml
groups:
  - name: rai-api
    rules:
      - alert: HighErrorRate
        expr: rate(rai_errors_total[5m]) > 0.05
        annotations:
          summary: "Error rate > 5%"
      
      - alert: HighSearchLatency
        expr: histogram_quantile(0.95, rai_search_duration_seconds) > 30
        annotations:
          summary: "p95 search latency > 30s"
      
      - alert: LowCacheHitRate
        expr: rai_cache_hit_rate < 0.5
        annotations:
          summary: "Cache hit rate < 50%"
```

---

## Security Best Practices

### Input Validation

- ✅ Query length: Max 500 chars
- ✅ max_results: Max 20
- ✅ All parameters type-checked by Pydantic
- ✅ URLs validated (no `file://`, `gopher://`, etc.)

### Output Sanitization

```python
# DON'T do this:
return {"content": content_html}  # Raw HTML vulnerable to XSS

# DO this:
import bleach
clean_html = bleach.clean(content_html, tags=['p', 'a', 'h1', 'h2'])
return {"content": clean_html}
```

### API Key Management

```bash
# ✅ Use secrets manager
AWS Secrets Manager / HashiCorp Vault / Kubernetes Secrets

# ❌ Never do this:
GOOGLE_API_KEY="sk-..." git commit  # DON'T

# ✅ Instead:
echo ".env" >> .gitignore
```

### HTTPS Only

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}

# Enforce HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

## Cost Optimization

### Reduce API Calls

```bash
# Increase cache TTL for evergreen content
CACHE_TTL=604800              # 1 week instead of 1 day

# Disable unnecessary features
ENABLE_RERANKING=false        # If not needed
ENABLE_SYNTHESIS=false        # If not needed
ENABLE_CHUNKING=false         # If not needed
```

### Reduce Egress Costs

```bash
# Use local reranker instead of Gemini
RERANKER_USE_CLOUD=false      # Saves ~$0.02 per search

# But if you must use cloud, batch requests:
# 100 searches/day × $0.02 = $2/day = $60/month
```

### Resource Optimization

```bash
# Right-size instances
# Monitor: CPU, memory, network

# AWS Compute Optimizer
aws compute-optimizer get-ec2-instance-recommendations

# Spot instances (for batch workloads)
--instance-market-options SpotOptions={MaxPrice=0.05}
```

---

## Disaster Recovery

### Backup Strategy

```bash
# Daily cache backup
0 2 * * * tar -czf /backups/cache-$(date +\%Y\%m\%d).tar.gz /var/lib/rai-cache

# S3 sync (AWS)
0 3 * * * aws s3 sync /backups/ s3://rai-backups/
```

### Failover Setup

```bash
# Multi-region deployment
# Region 1 (Primary): us-west-2
# Region 2 (Secondary): eu-west-1

# Route53 health check
aws route53 create-health-check --health-check-config \
  IPAddress=primary-api.example.com,Port=443,Type=HTTPS
```

### Rollback Plan

```bash
# Tag releases
docker tag rai-search-api:latest rai-search-api:v3.0
docker tag rai-search-api:latest rai-search-api:v3.0-stable

# Rollback command
docker pull rai-search-api:v3.0-stable
# Restart with previous version
```

---

## Production Checklist

- [ ] HTTPS/TLS enabled
- [ ] Authentication layer added
- [ ] Rate limiting configured
- [ ] Logging centralized
- [ ] Monitoring/alerting set up
- [ ] Secrets managed (not in code)
- [ ] Cache strategy decided (file/Redis/other)
- [ ] Backup/restore tested
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Security audit passed
- [ ] Legal/compliance review done
- [ ] Documentation updated
- [ ] Runbook created for operators

---

**Questions?** Check [PERFORMANCE.md](PERFORMANCE.md) for tuning, or contact team.

**Last Updated**: January 2026
