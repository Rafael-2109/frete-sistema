# Load Testing Suite for Freight Management System

This comprehensive load testing suite verifies the system can handle **1000+ requests per minute** with various traffic patterns and user behaviors.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or using the run script
./run_load_tests.sh  # Will auto-install if needed
```

### Running Tests

```bash
# Interactive menu
./run_load_tests.sh

# Direct execution
./run_load_tests.sh smoke      # Quick validation
./run_load_tests.sh api        # API load test (1000+ req/min)
./run_load_tests.sh concurrent # Concurrent users test
./run_load_tests.sh spike      # Spike test
./run_load_tests.sh all        # Run all scenarios
./run_load_tests.sh stress     # Stress test (caution!)
```

## 📊 Test Scenarios

### 1. API Load Test (`api_load.py`)
- **Goal**: Verify system handles 1000+ requests/minute
- **Features**:
  - Gradual ramp-up from 10 to 250 users
  - Realistic API endpoint distribution
  - Authentication and session management
  - Complex request patterns

### 2. Concurrent Users Test (`concurrent_users.py`)
- **Goal**: Test high concurrent user load
- **Features**:
  - Up to 1000 concurrent users
  - Mixed read/write operations
  - WebSocket simulation
  - Bulk operations testing

### 3. Spike Test (`spike_test.py`)
- **Goal**: Verify system resilience under sudden traffic spikes
- **Features**:
  - Multiple spike patterns
  - Extreme load scenarios (up to 1200 users)
  - Adaptive user behavior
  - Cache-busting operations

### 4. Main Scenario (`locustfile.py`)
- **Goal**: Mixed realistic user behaviors
- **Features**:
  - Multiple user types (Customer, Driver, Admin, Mobile)
  - WebSocket connections
  - Real-world usage patterns
  - Performance monitoring hooks

## 🎯 Performance Targets

- **Throughput**: 1000+ requests per minute (16.67 RPS)
- **Response Time P95**: < 300ms
- **Response Time P99**: < 1000ms
- **Error Rate**: < 1%
- **Success Rate**: > 99%

## 📈 Monitoring & Reporting

### Real-time Monitoring
The `monitoring.py` module provides:
- Live performance metrics
- Threshold violation alerts
- Request/error tracking
- Response time percentiles

### Generated Reports
After each test run:
- HTML report with interactive charts
- CSV files with detailed metrics
- JSON export for further analysis
- Performance visualization graphs

### Report Location
```
test_results/
├── [scenario]_[timestamp]/
│   ├── report.html           # Locust HTML report
│   ├── results_stats.csv      # Detailed statistics
│   ├── results_failures.csv   # Failure details
│   ├── final_report.txt       # Summary report
│   ├── metrics.json           # Full metrics export
│   └── performance_viz.png    # Performance graphs
```

## 🔧 Configuration

### Environment Variables
```bash
HOST="http://localhost:8000"   # Target host
USERS=100                       # Number of users
SPAWN_RATE=10                   # Users spawned/second
RUN_TIME="5m"                   # Test duration
TEST_ENV="local"                # Environment (local/staging/production)
```

### Performance Configuration
Edit `performance_config.py` to adjust:
- Performance thresholds
- API endpoints
- User scenarios
- Load test stages
- Monitoring settings

## 📚 Usage Examples

### 1. Development Testing
```bash
# Quick smoke test
./run_load_tests.sh smoke

# API performance check
HOST="http://localhost:8000" USERS=50 ./run_load_tests.sh api
```

### 2. Staging Validation
```bash
# Full test suite
TEST_ENV=staging HOST="https://staging-api.example.com" ./run_load_tests.sh all
```

### 3. Production Load Test
```bash
# Careful load test
TEST_ENV=production HOST="https://api.example.com" \
  USERS=100 SPAWN_RATE=5 RUN_TIME="10m" \
  ./run_load_tests.sh api
```

### 4. Custom Scenarios
```bash
# Using Locust directly
locust -f locustfile.py --host=http://localhost:8000 \
  --users=200 --spawn-rate=20 --run-time=10m

# With web UI
locust -f scenarios/api_load.py --host=http://localhost:8000
# Open http://localhost:8089
```

## 🎛️ Advanced Features

### Custom Load Shapes
- `StepLoadShape`: Gradual load increase
- `SpikeLoadShape`: Sudden traffic spikes
- `ConcurrentLoadShape`: Rapid user ramp-up

### Adaptive Testing
- Users adjust behavior based on response times
- Automatic back-off during system stress
- Intelligent request distribution

### Performance Hooks
- Pre/post request monitoring
- Custom metrics collection
- Real-time threshold checking

## 🚨 Monitoring Alerts

The system will alert when:
- Error rate exceeds 1%
- P95 response time > 300ms
- P99 response time > 1000ms
- Throughput drops below target

## 📋 Best Practices

1. **Start Small**: Run smoke tests first
2. **Monitor Resources**: Watch CPU, memory, and network
3. **Incremental Load**: Gradually increase user count
4. **Analyze Results**: Review all generated reports
5. **Test Regularly**: Include in CI/CD pipeline

## 🔍 Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check target host is accessible
   - Verify SSL certificates for HTTPS
   - Ensure sufficient file descriptors

2. **High Error Rates**
   - Review server logs
   - Check for rate limiting
   - Verify authentication tokens

3. **Poor Performance**
   - Monitor server resources
   - Check database connections
   - Review application logs

### Debug Mode
```bash
# Enable debug logging
locust -f locustfile.py --host=http://localhost:8000 \
  --loglevel=DEBUG
```

## 📊 Interpreting Results

### Key Metrics
- **RPS (Requests Per Second)**: Should exceed 16.67 for 1000+/min
- **Response Times**: Check P50, P95, P99 percentiles
- **Error Rate**: Must stay below 1%
- **Concurrent Users**: Maximum supported without degradation

### Performance Grades
- **A**: Meets all thresholds with 20% buffer
- **B**: Meets all thresholds
- **C**: Minor threshold violations (<5%)
- **D**: Significant violations (5-10%)
- **F**: Major violations (>10%)

## 🔗 Integration

### CI/CD Pipeline
```yaml
# Example GitHub Actions
- name: Run Load Tests
  run: |
    ./run_load_tests.sh smoke
    ./run_load_tests.sh api
```

### Monitoring Integration
- Prometheus metrics export
- Grafana dashboard support
- Custom metrics via monitoring.py

## 📝 Contributing

To add new test scenarios:
1. Create a new file in `scenarios/`
2. Extend appropriate user classes
3. Define tasks with proper weights
4. Add to `run_load_tests.sh`

## 📜 License

Part of the Freight Management System project.