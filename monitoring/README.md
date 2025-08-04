# MCP Frete Sistema - Monitoring Dashboard

Comprehensive monitoring solution for the MCP Frete Sistema with real-time metrics, alerts, and performance tracking.

## Features

### Real-time Monitoring
- **System Metrics**: CPU, memory, disk usage, network I/O
- **API Performance**: Request rates, response times, error rates
- **Database Metrics**: Connection pools, query performance, table statistics
- **Cache Performance**: Hit rates, memory usage, connection stats
- **Business Metrics**: Orders, quotes, revenue, active users

### Alerting System
- Multi-level alerts (Info, Warning, Critical, Emergency)
- Multiple notification channels (Email, Slack, Webhooks)
- Customizable alert rules and thresholds
- Alert acknowledgment and resolution tracking

### Visualization
- Real-time dashboard with WebSocket updates
- Interactive charts for historical data
- Prometheus metrics export
- Grafana integration ready

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   MCP System    │────▶│ Metrics Collector│────▶│     Redis       │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
┌─────────────────┐     ┌──────────────────┐              │
│                 │     │                  │              │
│   PostgreSQL    │────▶│   Collectors     │──────────────┘
│                 │     │                  │
└─────────────────┘     └──────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   Dashboard     │────▶│  Alert Manager   │────▶│  Notifications  │
│   (Flask)       │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘

┌─────────────────┐     ┌──────────────────┐
│                 │     │                  │
│   Prometheus    │────▶│     Grafana      │
│                 │     │                  │
└─────────────────┘     └──────────────────┘
```

## Components

### 1. Dashboard (Flask + SocketIO)
- Real-time web interface
- WebSocket for live updates
- RESTful API for metrics
- Location: `monitoring/dashboard/`

### 2. Metrics Collector
- Collects system, API, database, and cache metrics
- Stores in Redis for real-time access
- Aggregates data for different time windows
- Location: `monitoring/collectors/`

### 3. Alert Manager
- Evaluates metrics against alert rules
- Manages alert lifecycle (active, acknowledged, resolved)
- Sends notifications through multiple channels
- Location: `monitoring/alerts/`

### 4. Prometheus Exporter
- Exports metrics in Prometheus format
- Integrates with existing Prometheus infrastructure
- Supports custom business metrics
- Location: `monitoring/exporters/`

## Quick Start

### 1. Using Docker Compose

```bash
# Start the monitoring stack
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Check status
docker-compose -f monitoring/docker-compose.monitoring.yml ps

# View logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs -f
```

### 2. Manual Installation

```bash
# Install dependencies
cd monitoring/dashboard
pip install -r requirements.txt

# Set environment variables
export DB_HOST=localhost
export DB_NAME=frete_sistema
export DB_USER=postgres
export DB_PASSWORD=yourpassword
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Run the dashboard
python app.py

# In another terminal, run the metrics collector
cd monitoring/collectors
python metrics_collector.py

# In another terminal, run the alert manager
cd monitoring/alerts
python alert_manager.py
```

## Configuration

### Environment Variables

```bash
# Database
DB_HOST=localhost
DB_NAME=frete_sistema
DB_USER=postgres
DB_PASSWORD=yourpassword

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Monitoring
MONITORING_PORT=5001
SECRET_KEY=your-secret-key

# Alerts - Email
EMAIL_ALERTS_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_FROM_EMAIL=alerts@frete-sistema.com
ALERT_TO_EMAIL_1=admin@company.com

# Alerts - Slack
SLACK_ALERTS_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#alerts

# Alerts - Webhook
WEBHOOK_ALERTS_ENABLED=true
ALERT_WEBHOOK_URL=https://your-webhook-endpoint.com
WEBHOOK_AUTH_TOKEN=your-auth-token

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

### Alert Configuration

Edit `monitoring/config/monitoring.yaml` to customize:
- Alert thresholds
- Cooldown periods
- Notification channels
- Metric collection intervals

## Usage

### Accessing the Dashboard

1. Open http://localhost:5001 in your browser
2. View real-time metrics and charts
3. Monitor alerts and system health

### API Endpoints

```bash
# Get current metrics
curl http://localhost:5001/api/metrics/current

# Get metric history
curl http://localhost:5001/api/metrics/cpu_usage?limit=100

# Get alerts
curl http://localhost:5001/api/alerts

# Get system info
curl http://localhost:5001/api/system/info

# Get user activity
curl http://localhost:5001/api/user/activity

# Prometheus metrics
curl http://localhost:5001/metrics
```

### Recording Custom Metrics

From your application code:

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379)

# Record a custom metric
redis_client.hset('mcp:custom_metric:user_registrations', mapping={
    'value': 42,
    'tags': json.dumps({'plan': 'premium'})
})
redis_client.sadd('mcp:custom_metrics', 'user_registrations')

# Record API metrics
redis_client.incr('mcp:metrics:request_count')
redis_client.incr('mcp:metrics:error_count')
redis_client.lpush('mcp:metrics:response_times', 0.125)

# Record business metrics
redis_client.set('mcp:metrics:orders:today', 150)
redis_client.set('mcp:metrics:revenue:today', 45000.00)
```

### Setting Up Grafana Dashboards

1. Access Grafana at http://localhost:3001
2. Login with admin/admin (change on first login)
3. Add Prometheus data source:
   - URL: http://prometheus:9090
   - Access: Server (Default)
4. Import dashboards from `monitoring/grafana/dashboards/`

## Alert Rules

### System Alerts
- **High CPU Usage**: > 90% for 5 minutes
- **High Memory Usage**: > 85% for 5 minutes
- **Critical Memory**: > 95% for 2 minutes
- **High Disk Usage**: > 90% for 10 minutes

### API Alerts
- **High Error Rate**: > 5% errors for 5 minutes
- **Critical Errors**: > 10% errors for 2 minutes
- **Slow Response**: P95 > 1 second for 5 minutes

### Database Alerts
- **High Connections**: > 80 connections for 5 minutes
- **Slow Queries**: Average > 500ms for 5 minutes

### Cache Alerts
- **Low Hit Rate**: < 80% for 10 minutes
- **Critical Hit Rate**: < 60% for 5 minutes

## Troubleshooting

### Dashboard Not Loading
```bash
# Check if services are running
docker-compose -f monitoring/docker-compose.monitoring.yml ps

# Check logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs mcp-dashboard

# Test database connection
psql -h localhost -U postgres -d frete_sistema -c "SELECT 1"

# Test Redis connection
redis-cli ping
```

### Metrics Not Updating
```bash
# Check metrics collector logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs metrics-collector

# Verify Redis has data
redis-cli keys "mcp:metrics:*"

# Check Prometheus targets
curl http://localhost:9091/api/v1/targets
```

### Alerts Not Firing
```bash
# Check alert manager logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs alert-manager

# Verify alert rules
curl http://localhost:9091/api/v1/rules

# Test notification channels
# Check SMTP settings, Slack webhook, etc.
```

## Performance Optimization

1. **Adjust collection intervals** in `monitoring.yaml`
2. **Set appropriate retention periods** to manage storage
3. **Use metric aggregation** for historical data
4. **Enable Prometheus remote storage** for long-term retention
5. **Optimize database queries** with proper indexes

## Security Considerations

1. **Enable authentication** on all monitoring endpoints
2. **Use HTTPS** for production deployments
3. **Secure Redis** with password authentication
4. **Restrict network access** to monitoring services
5. **Rotate alert webhook tokens** regularly
6. **Audit access logs** for monitoring dashboards

## Development

### Adding New Metrics

1. Update the collector in `collectors/metrics_collector.py`
2. Add Prometheus metrics in `exporters/prometheus_exporter.py`
3. Create alert rules in `config/alerting_rules.yml`
4. Update dashboard to display new metrics

### Adding New Alert Channels

1. Create new notification class in `alerts/alert_manager.py`
2. Implement the `send()` method
3. Add configuration in `monitoring.yaml`
4. Test the notification channel

## License

This monitoring system is part of the MCP Frete Sistema project.