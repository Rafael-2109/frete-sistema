# MCP Security System

Comprehensive security framework for the MCP (Model Context Protocol) system providing multi-layered protection against various attack vectors.

## Features

### 🛡️ Rate Limiting
- **Token Bucket Algorithm**: Configurable rate limits per user, IP, and endpoint
- **Distributed Support**: Redis backend for multi-instance deployments
- **Smart Whitelisting**: Automatic bypass for trusted services
- **Endpoint-Specific Limits**: Different limits for various API endpoints

### 🚫 DDoS Protection
- **Sliding Window Detection**: Real-time request pattern analysis
- **Connection Limiting**: Concurrent connection limits per IP
- **Pattern Analysis**: Behavioral anomaly detection
- **Emergency Mode**: Automatic protection escalation during attacks

### 🌐 IP Management
- **Reputation System**: Dynamic IP scoring based on behavior
- **Geographic Analysis**: GeoIP integration for location-based decisions
- **Threat Intelligence**: Automatic updates from security feeds
- **Flexible Lists**: Support for IP and subnet whitelisting/blacklisting

### 🔍 Threat Detection
- **ML-Based Analysis**: Machine learning for anomaly detection
- **Pattern Recognition**: Detection of SQL injection, XSS, path traversal
- **Behavioral Analysis**: Bot and scanner identification
- **Real-time Monitoring**: Continuous threat assessment

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 FastAPI Application                     │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│         IntegratedSecurityMiddleware                    │
│  ┌─────────────┬─────────────┬─────────────┬─────────┐  │
│  │Rate Limiter │DDoS Protect │IP Manager   │Threat   │  │
│  │             │             │             │Detector │  │
│  └─────────────┴─────────────┴─────────────┴─────────┘  │
└─────────────────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              Redis (Optional)                           │
│         ┌─────────────────────────────────────┐         │
│         │  - Rate limit state                 │         │
│         │  - IP reputation data               │         │
│         │  - Threat intelligence cache        │         │
│         └─────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

## Installation

### 1. Install Dependencies

```bash
pip install fastapi redis aiofiles scikit-learn numpy geoip2 aiohttp
```

### 2. Optional: GeoIP Database

Download MaxMind GeoLite2 database for geographic IP analysis:

```bash
# Register at https://www.maxmind.com/ and download GeoLite2-City.mmdb
export GEOIP_DATABASE_PATH="/path/to/GeoLite2-City.mmdb"
```

### 3. Redis Setup (Optional but Recommended)

```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis

# Set Redis URL
export REDIS_URL="redis://localhost:6379/0"
```

## Configuration

### Environment Variables

```bash
# Security Features
SECURITY_ENABLE_RATE_LIMITING=true
SECURITY_ENABLE_DDOS_PROTECTION=true
SECURITY_ENABLE_IP_MANAGEMENT=true
SECURITY_ENABLE_THREAT_DETECTION=true

# Rate Limiting
SECURITY_RATE_LIMIT_GLOBAL_CAPACITY=1000
SECURITY_RATE_LIMIT_GLOBAL_REFILL_RATE=100
SECURITY_RATE_LIMIT_PER_USER_CAPACITY=100
SECURITY_RATE_LIMIT_PER_IP_CAPACITY=200

# DDoS Protection
SECURITY_DDOS_REQUESTS_PER_SECOND_THRESHOLD=50
SECURITY_DDOS_REQUESTS_PER_MINUTE_THRESHOLD=1000
SECURITY_DDOS_CONCURRENT_CONNECTIONS_LIMIT=100

# IP Management
SECURITY_IP_AUTO_BLACKLIST_THRESHOLD=10
SECURITY_IP_TEMP_BLOCK_DURATION=3600

# Threat Detection
SECURITY_THREAT_ANOMALY_THRESHOLD=0.7
SECURITY_THREAT_ML_RETRAIN_INTERVAL=3600

# External Services
REDIS_URL=redis://localhost:6379/0
GEOIP_DATABASE_PATH=/path/to/GeoLite2-City.mmdb
```

## Integration

### FastAPI Integration

```python
from fastapi import FastAPI
from security import init_security_system, create_security_middleware

app = FastAPI()

# Initialize security system
await init_security_system()

# Add security middleware
security_middleware = create_security_middleware(app)
app.add_middleware(security_middleware)
```

### Manual Configuration

```python
from security import init_security_system

# Custom configuration
config_overrides = {
    "ENABLE_RATE_LIMITING": True,
    "RATE_LIMIT_GLOBAL_CAPACITY": 2000,
    "DDOS_REQUESTS_PER_SECOND_THRESHOLD": 100,
}

await init_security_system(config_overrides)
```

## API Endpoints

### Security Status

```http
GET /api/security/status
```

Returns comprehensive security system status including:
- Component status
- Statistics
- Configuration summary

### IP Management

```http
POST /api/security/ip/whitelist
Content-Type: application/json

{
    "ip": "192.168.1.100",
    "reason": "Trusted service"
}
```

```http
POST /api/security/ip/blacklist
Content-Type: application/json

{
    "ip": "1.2.3.4",
    "reason": "Malicious activity detected"
}
```

### Threat Assessment

```http
GET /api/security/threat/{ip_address}
```

Returns detailed threat assessment for specific IP.

## Security Responses

### Rate Limiting

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200

{
    "error": "Too many requests",
    "detail": "Rate limit exceeded",
    "type": "rate_limited",
    "retry_after": 60
}
```

### DDoS Protection

```http
HTTP/1.1 429 Too Many Requests

{
    "error": "Request blocked by DDoS protection",
    "detail": "Suspicious request pattern detected",
    "type": "ddos_blocked"
}
```

### IP Blocking

```http
HTTP/1.1 403 Forbidden

{
    "error": "Access denied by security policy",
    "detail": "IP is blacklisted",
    "type": "ip_blocked"
}
```

## Monitoring and Alerting

### Metrics

The security system provides detailed metrics:

```python
from security import security_middleware

stats = security_middleware.get_statistics()
# {
#     "total_requests": 10000,
#     "blocked_requests": 45,
#     "rate_limited": 20,
#     "ddos_blocked": 15,
#     "ip_blocked": 10,
#     "threat_detected": 25
# }
```

### Logging

Security events are logged with structured data:

```python
2025-07-27 23:30:15 WARNING  security.ddos_protection: DDoS protection blocked request from 1.2.3.4: High request rate
2025-07-27 23:31:22 INFO     security.ip_manager: Added 1.2.3.5 to blacklist: Auto-blacklisted due to low reputation
2025-07-27 23:32:10 WARNING  security.threat_detector: Threats detected for IP 1.2.3.6: ['sql_injection', 'xss_attack']
```

## Performance

### Benchmarks

- **Rate Limiting**: < 1ms per request
- **DDoS Detection**: < 2ms per request  
- **IP Management**: < 0.5ms per request
- **Threat Analysis**: Background processing

### Resource Usage

- **Memory**: ~10MB base + ~1KB per tracked IP
- **CPU**: < 5% overhead on typical workloads
- **Storage**: ~100MB for ML models and data

## Security Considerations

### Default Security

- All components disabled by default
- Explicit configuration required
- Fail-open on component errors
- Comprehensive logging

### Data Privacy

- IP addresses are hashed for storage
- Request data anonymized after analysis
- GDPR compliance considerations
- Configurable data retention

### High Availability

- Redis failover support
- Component independence
- Graceful degradation
- Health check endpoints

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```
   WARN: Redis connection failed, using local rate limiting
   ```
   - Check Redis server status
   - Verify REDIS_URL configuration
   - Ensure network connectivity

2. **GeoIP Database Not Found**
   ```
   INFO: IP manager initialized without GeoIP database
   ```
   - Download GeoLite2 database
   - Set GEOIP_DATABASE_PATH
   - Restart application

3. **High False Positives**
   ```
   WARN: Threats detected for legitimate IP
   ```
   - Adjust threshold configurations
   - Add IPs to whitelist
   - Review threat detection patterns

### Debug Mode

Enable verbose logging:

```python
import logging
logging.getLogger('security').setLevel(logging.DEBUG)
```

### Performance Monitoring

Monitor component performance:

```python
from security import get_security_status

status = await get_security_status()
print(status['statistics'])
```

## Development

### Running Tests

```bash
python -m pytest tests/security/
```

### Adding Custom Threat Patterns

```python
from security.threat_detector import threat_detector

@threat_detector.add_pattern("custom_attack")
async def detect_custom_attack(ip: str, request: dict):
    # Custom detection logic
    if suspicious_pattern_detected:
        return ThreatIndicator(
            timestamp=datetime.now(),
            ip=ip,
            threat_type=ThreatType.CUSTOM,
            severity=ThreatSeverity.HIGH,
            confidence=0.9,
            details={"pattern": "custom"},
            indicators=["Custom attack pattern detected"]
        )
    return None
```

## License

This security system is part of the MCP project and follows the same licensing terms.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error details
3. Submit issues with detailed error information
4. Include configuration and environment details