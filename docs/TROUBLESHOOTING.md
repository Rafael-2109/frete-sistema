# MCP Frete Sistema - Troubleshooting Guide

## 🔍 Common Issues and Solutions

This guide helps you diagnose and fix common problems with the MCP Frete Sistema.

## 🚨 Quick Diagnostics

Run the diagnostic tool first:
```bash
npm run diagnose
```

This will check:
- Database connectivity
- API endpoints
- Embedding service
- Cache status
- File permissions
- Memory usage

## 💥 Common Problems

### 1. Connection Issues

#### Problem: "Cannot connect to database"
```
Error: ECONNREFUSED 127.0.0.1:5432
```

**Solutions:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Verify connection settings
psql -h localhost -U your_user -d freight_db

# Check environment variables
echo $DATABASE_URL
```

#### Problem: "MCP server not responding"
```
Error: Connection timeout to MCP server
```

**Solutions:**
```bash
# Check if server is running
ps aux | grep "mcp-frete"

# Check port availability
lsof -i :3000

# Restart server
npm run restart

# Check logs
tail -f logs/mcp-frete.log
```

### 2. Search Issues

#### Problem: "No results for queries that should match"

**Solutions:**
```bash
# Rebuild search index
npm run search:reindex

# Clear embedding cache
npm run embeddings:clear

# Regenerate embeddings
npm run embeddings:generate

# Test specific query
npm run test:query "your search term"
```

#### Problem: "Search is very slow"

**Solutions:**
```sql
-- Check missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'freight' AND n_distinct > 100;

-- Create necessary indexes
CREATE INDEX CONCURRENTLY idx_freight_search 
ON freight USING gin(to_tsvector('portuguese', 
  coalesce(description, '') || ' ' || 
  coalesce(origin, '') || ' ' || 
  coalesce(destination, '')));

-- Vacuum and analyze
VACUUM ANALYZE freight;
```

### 3. Performance Issues

#### Problem: "High memory usage"

**Diagnosis:**
```bash
# Check memory usage
npm run monitor:memory

# Find memory leaks
npm run debug:memory-leak

# Check cache size
npm run cache:stats
```

**Solutions:**
```javascript
// Adjust memory limits in ecosystem.config.js
module.exports = {
  apps: [{
    name: 'mcp-frete',
    script: './dist/index.js',
    max_memory_restart: '1G',
    node_args: '--max-old-space-size=1024'
  }]
};
```

#### Problem: "Slow response times"

**Diagnosis:**
```bash
# Profile slow queries
npm run profile:queries

# Check connection pool
npm run db:pool:stats

# Monitor API latency
npm run monitor:latency
```

**Solutions:**
```bash
# Optimize connection pool
export DB_POOL_MAX=20
export DB_POOL_MIN=5

# Enable query caching
export ENABLE_QUERY_CACHE=true
export CACHE_TTL=3600

# Restart with optimizations
npm run start:optimized
```

### 4. Embedding Issues

#### Problem: "Embeddings not generating"

**Solutions:**
```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Test API connectivity
npm run test:openai

# Regenerate embeddings batch
npm run embeddings:batch --size=100

# Use fallback embeddings
npm run embeddings:fallback:enable
```

#### Problem: "Wrong search results"

**Solutions:**
```bash
# Validate embeddings
npm run embeddings:validate

# Check embedding dimensions
npm run embeddings:info

# Retrain custom embeddings
npm run embeddings:train --data=custom-terms.json

# Reset to defaults
npm run embeddings:reset
```

### 5. Database Issues

#### Problem: "Database disk full"

**Emergency Solutions:**
```bash
# Check disk usage
df -h

# Find large tables
npm run db:table:sizes

# Clean old data
npm run cleanup:old --days=30 --confirm

# Vacuum full (requires downtime)
npm run db:vacuum:full
```

#### Problem: "Too many connections"

**Solutions:**
```sql
-- Check current connections
SELECT count(*) FROM pg_stat_activity;

-- Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND state_change < NOW() - INTERVAL '10 minutes';

-- Adjust connection limits
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

### 6. API Issues

#### Problem: "CORS errors in browser"

**Solutions:**
```javascript
// Update CORS configuration
// config/cors.js
module.exports = {
  origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
};
```

#### Problem: "Rate limiting errors"

**Solutions:**
```bash
# Check rate limit settings
npm run config:get rate-limit

# Adjust limits
npm run config:set rate-limit.max=1000

# Whitelist IP
npm run whitelist:add 192.168.1.100

# Clear rate limit cache
npm run cache:clear:ratelimit
```

## 🛠️ Advanced Troubleshooting

### Debug Mode

Enable detailed debugging:
```bash
# Full debug mode
export DEBUG=mcp:*
npm run start

# Specific modules
export DEBUG=mcp:search,mcp:embeddings
npm run start

# SQL query logging
export LOG_SQL=true
npm run start
```

### Performance Profiling

```bash
# CPU profiling
npm run profile:cpu --duration=30s

# Memory profiling
npm run profile:memory

# Flame graph generation
npm run profile:flame

# Analyze results
npm run profile:analyze
```

### Log Analysis

```bash
# Search for errors
grep -i error logs/*.log | less

# Find slow queries
awk '/Query took/ && $4 > 1000' logs/mcp-frete.log

# Extract stack traces
npm run logs:extract:errors > errors.txt

# Generate log report
npm run logs:report --format=html
```

## 🔧 Recovery Procedures

### Database Recovery

```bash
# 1. Stop application
npm run stop

# 2. Backup current state
pg_dump freight_db > backup_emergency.sql

# 3. Check database integrity
npm run db:check:integrity

# 4. Repair if needed
npm run db:repair

# 5. Restart
npm run start
```

### Cache Corruption

```bash
# Clear all caches
npm run cache:clear:all

# Rebuild caches
npm run cache:rebuild

# Verify cache integrity
npm run cache:verify
```

### Index Corruption

```sql
-- Identify corrupted indexes
SELECT schemaname, tablename, indexname 
FROM pg_stat_user_indexes 
WHERE idx_scan = 0 AND idx_tup_read > 0;

-- Rebuild specific index
REINDEX INDEX CONCURRENTLY idx_name;

-- Rebuild all indexes
REINDEX DATABASE freight_db;
```

## 📊 Monitoring and Alerts

### Health Check Endpoints

```bash
# Basic health
curl http://localhost:3000/health

# Detailed health
curl http://localhost:3000/health/detailed

# Component health
curl http://localhost:3000/health/db
curl http://localhost:3000/health/cache
curl http://localhost:3000/health/embeddings
```

### Setting Up Alerts

```yaml
# alerts.yml
- alert: HighErrorRate
  expr: rate(errors_total[5m]) > 0.05
  annotations:
    summary: "High error rate detected"
    
- alert: SlowQueries
  expr: query_duration_seconds > 2
  annotations:
    summary: "Queries taking longer than 2 seconds"
    
- alert: LowDiskSpace
  expr: disk_free_percent < 10
  annotations:
    summary: "Less than 10% disk space remaining"
```

## 🚑 Emergency Contacts

### Escalation Path

1. **Level 1**: Check this guide and logs
2. **Level 2**: Internal documentation and runbooks
3. **Level 3**: Development team
4. **Level 4**: Database administrator
5. **Level 5**: System architect

### Useful Commands Cheatsheet

```bash
# Quick health check
npm run health

# View recent errors
npm run errors:recent

# Emergency restart
npm run emergency:restart

# Generate diagnostic report
npm run report:diagnostic

# Contact support with diagnostics
npm run support:contact
```

## 🔍 Debugging Specific Features

### Natural Language Processing

```bash
# Test NLP parsing
npm run nlp:test "sua consulta aqui"

# Check language model
npm run nlp:model:info

# Rebuild NLP index
npm run nlp:rebuild
```

### Embedding Search

```bash
# Test embedding generation
npm run embeddings:test "freight to São Paulo"

# Compare embeddings
npm run embeddings:compare "query1" "query2"

# Visualize embedding space
npm run embeddings:visualize
```

### API Response Issues

```bash
# Test specific endpoint
npm run api:test POST /search '{"query": "test"}'

# Validate response format
npm run api:validate

# Check middleware order
npm run api:middleware:list
```

## 📝 Reporting Issues

When reporting issues, include:

1. **Diagnostic report**:
   ```bash
   npm run report:generate > diagnostic-report.txt
   ```

2. **Steps to reproduce**

3. **Expected vs actual behavior**

4. **Environment details**:
   ```bash
   npm run env:info
   ```

5. **Recent changes**:
   ```bash
   git log --oneline -10
   ```

Remember: Most issues can be resolved by checking logs, verifying configuration, and ensuring all services are running correctly!