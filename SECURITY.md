# SECURITY.md — Security Policy and Responsible Disclosure

---

## Security Policy

This project is committed to security and responsible disclosure. We appreciate responsible security research.

---

## Reporting Security Vulnerabilities

### DO NOT Open a Public GitHub Issue

If you discover a security vulnerability, **do not** open a public issue. Instead:

1. **Email**: Contact maintainers at [security@example.com](mailto:security@example.com)
   - Replace with actual security contact email in your repo

2. **Subject**: `[SECURITY] Vulnerability Report - [brief description]`

3. **Include**:
   - Detailed description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

4. **Please DO NOT**:
   - Disclose vulnerability publicly before we patch
   - Test on production systems
   - Cause data loss or service disruption
   - Violate privacy

### Response Timeline

- **24 hours**: Initial acknowledgment
- **7 days**: Investigation and patch plan
- **30 days**: Patch release (target)
- **60 days**: Public disclosure (if applicable)

---

## Known Security Considerations

### 1. API Key Management

**Risk**: Exposed API keys (Google, OpenAI, etc.) can be abused.

**Mitigation**:
- ✅ Use environment variables (never hardcode)
- ✅ Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
- ✅ Rotate keys regularly
- ✅ Limit API key scope (read-only if possible)
- ✅ Monitor API usage for anomalies

**Your Responsibility**:
```bash
# ✅ Good
export GOOGLE_API_KEY="$(aws secretsmanager get-secret-value ...)"

# ❌ Bad
GOOGLE_API_KEY="sk-xyz..." git commit .env

# ❌ Very Bad
api_key = "sk-xyz..."  # hardcoded in code
```

### 2. Cache Security

**Risk**: Cached data may contain sensitive information.

**Mitigation**:
- Cache directory permissions: `chmod 700 /cache` (owner-only)
- Encrypted volumes recommended for sensitive data
- TTL cleanup (default 24 hours)
- Manual cache clearing: `POST /cache/clear`

**Your Responsibility**:
```bash
# Encrypt cache volume
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup luksOpen /dev/sdX rai-cache
sudo mkfs.ext4 /dev/mapper/rai-cache
sudo mount /dev/mapper/rai-cache /app/cache
```

### 3. Input Validation

**Risk**: Malicious queries could cause DoS or injection attacks.

**Mitigation**:
- ✅ Query length capped at 500 chars
- ✅ All parameters type-validated by Pydantic
- ✅ URL validation (no `file://` or `gopher://`)
- ✅ Rate limiting (30 requests/minute default)
- ✅ Use reverse proxy WAF (CloudFlare, AWS WAF)

**Tested Against**:
- SQL injection: N/A (queries are strings, not SQL)
- XSS: Input is never rendered; output sanitization recommended
- Command injection: N/A (no shell execution)

### 4. Output Sanitization

**Risk**: Extracted HTML could contain malicious scripts if rendered.

**Mitigation**:
- ✅ HTML extracted but NOT rendered by API
- ⚠️ **Your Responsibility**: Sanitize before displaying
- ✅ Use libraries like `bleach` or `DOMPurify`

**Example** (client-side):
```python
from bleach import clean

html_content = response['results'][0]['content_html']
safe_html = clean(html_content, tags=['p', 'a', 'h1', 'h2'])
display(safe_html)
```

### 5. HTTPS/TLS

**Risk**: Unencrypted traffic exposes credentials and data.

**Mitigation**:
- ✅ Always use HTTPS in production
- ✅ TLS 1.2+ only (no SSL 3.0, TLS 1.0, 1.1)
- ✅ Use strong ciphers
- ✅ HSTS headers enforced

**Configuration** (nginx):
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
add_header Strict-Transport-Security "max-age=31536000" always;
```

### 6. Authentication & Authorization

**Risk**: Unauthorized access to API.

**Mitigation**:
- ⚠️ **Your Responsibility**: No built-in auth (add your own)
- ✅ Options: Basic auth, JWT, API keys, OAuth2
- ✅ Recommended: Place behind reverse proxy with auth layer

**Example** (nginx basic auth):
```nginx
auth_basic "Restricted";
auth_basic_user_file /etc/nginx/.htpasswd;
```

### 7. Rate Limiting

**Risk**: API abuse, DoS attacks.

**Mitigation**:
- ✅ 30 requests/minute per IP (default, configurable)
- ✅ Use nginx rate limiting as first line of defense
- ✅ CloudFlare or AWS WAF for DDoS protection

**Configuration**:
```bash
RATE_LIMIT=30/minute  # Adjust based on your use case
```

### 8. Dependency Vulnerabilities

**Risk**: Outdated packages with known CVEs.

**Mitigation**:
- ✅ Dependencies pinned to specific versions
- ✅ Regular dependency updates (not automated)
- ✅ Use `pip audit` to check for vulnerabilities

**Check Your Environment**:
```bash
pip install pip-audit
pip-audit                    # Check for CVEs
pip list --outdated         # Check for updates
```

### 9. Logging & Monitoring

**Risk**: Sensitive data logged; attacks not detected.

**Mitigation**:
- ✅ Logs don't contain API keys (environment variables)
- ⚠️ **Your Responsibility**: Don't log sensitive queries
- ✅ Centralized logging to secure location
- ✅ Monitoring and alerting for suspicious activity

**Log Levels**:
```bash
DEBUG=false              # Never true in production
LOG_LEVEL=INFO          # Only informational and above
```

### 10. Network Security

**Risk**: Unauthorized access to API port.

**Mitigation**:
- ✅ Firewall rules: Only allow needed ports
- ✅ VPC isolation: API not on public internet
- ✅ Use VPN for remote access
- ✅ SSH key-based auth only (no passwords)

**AWS Security Group** (example):
```
Inbound:
  - Port 443: From CloudFlare (not 0.0.0.0/0)
  - Port 8000: From nginx only (internal)
  - Port 22: From bastion host

Outbound:
  - Port 443: To internet (Google, DuckDuckGo, LLM APIs)
```

---

## Security Checklist

### Before Deploying to Production

- [ ] API keys in secrets manager (not environment files)
- [ ] HTTPS/TLS enabled with strong ciphers
- [ ] Authentication layer added (JWT, API keys, etc.)
- [ ] Rate limiting configured
- [ ] Firewall rules restricting access
- [ ] Input validation enabled (all parameters)
- [ ] Output sanitization in client code
- [ ] Logging doesn't contain sensitive data
- [ ] Centralized logging to secure location
- [ ] Monitoring and alerting set up
- [ ] Cache directory permissions (700)
- [ ] Dependencies checked for vulnerabilities
- [ ] Regular backups tested and working
- [ ] Incident response plan documented
- [ ] Security audit completed

---

## Security Best Practices

### 1. Principle of Least Privilege

```bash
# ✅ Good
API accessed only by authorized services
Limited to specific IP ranges
Read-only cache permissions

# ❌ Bad
API exposed to 0.0.0.0/0
All users have full access
World-readable cache files
```

### 2. Defense in Depth

```
┌─────────────────────────────────────┐
│ CDN/DDoS Protection (CloudFlare)    │
├─────────────────────────────────────┤
│ WAF (AWS WAF, ModSecurity)          │
├─────────────────────────────────────┤
│ Firewall (Security Groups)          │
├─────────────────────────────────────┤
│ Authentication (nginx basic auth)   │
├─────────────────────────────────────┤
│ API Rate Limiting (nginx)           │
├─────────────────────────────────────┤
│ Input Validation (Pydantic)         │
├─────────────────────────────────────┤
│ TLS Encryption (HTTPS)              │
└─────────────────────────────────────┘
```

### 3. Regular Updates

```bash
# Monthly: Check for updates
pip list --outdated

# Quarterly: Security audit
pip audit
# Also check GitHub security advisories
```

### 4. Monitoring & Logging

```bash
# Monitor these metrics:
- Error rate (spike = attack?)
- Latency (slow = Playwright timeout?)
- Cache hit rate (low = normal?)
- API key usage (unusual = compromise?)
```

### 5. Incident Response

**Plan for when things go wrong**:

1. **Detect**: Monitoring alerts
2. **Respond**: Kill process, isolate, investigate
3. **Contain**: Rotate credentials, block IPs
4. **Eradicate**: Apply patches, update logs
5. **Recover**: Restore from backup
6. **Review**: Post-mortem analysis

---

## Scope of Security Responsibility

### We're Responsible For

✅ API endpoint security (input validation, rate limiting)  
✅ HTTPS support (configure on your end)  
✅ Code quality (no obvious vulnerabilities)  
✅ Dependency management (regular updates)  
✅ Graceful error handling (no information leakage)  

### You're Responsible For

❌ Authentication layer (add your own)  
❌ Firewall rules (AWS Security Groups, etc.)  
❌ Secrets management (AWS Secrets Manager, Vault)  
❌ TLS certificate management  
❌ Monitoring and alerting  
❌ Backup and disaster recovery  
❌ Compliance (GDPR, CCPA, etc.)  
❌ Security testing in your environment  

---

## Vulnerability Scanning

### OWASP Top 10 Coverage

| OWASP Top 10 | Risk | Status | Mitigation |
|---|---|---|---|
| A01: Broken Access Control | Medium | ⚠️ Partially | Add auth layer |
| A02: Cryptographic Failures | Medium | ✅ OK | Use HTTPS |
| A03: Injection | Low | ✅ OK | Pydantic validation |
| A04: Insecure Design | Medium | ⚠️ Partially | Follow security checklist |
| A05: Security Misconfiguration | High | ⚠️ Partially | Production checklist |
| A06: Vulnerable Components | Medium | ✅ OK | Regular updates |
| A07: Authentication Failure | High | ⚠️ Partially | Add auth layer |
| A08: Data Integrity Failure | Low | ✅ OK | Use HTTPS |
| A09: Logging Failure | Medium | ✅ OK | Enable logging |
| A10: SSRF | Low | ✅ OK | URL validation |

---

## Security Advisories

### Past Security Issues

None reported yet.

### Future Advisories

Will be posted in this section and on GitHub security advisories.

---

## Security Contacts

**Report vulnerabilities to**: [security@example.com](mailto:security@example.com)  
**General security questions**: GitHub Discussions (Security tag)  

---

## Legal Notice

This project is provided "AS IS" without warranties. The authors assume no liability for security breaches, data loss, or other damages resulting from use of this software.

---

**Last Updated**: January 2026
