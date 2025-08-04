# MCP Sistema Test Suite

Comprehensive test suite for the Model Context Protocol (MCP) integration system.

## Test Structure

```
tests/mcp_sistema/
├── conftest.py                    # Shared fixtures and test configuration
├── pytest.ini                     # Pytest configuration
├── fixtures/                      # Test data and fixtures
│   ├── __init__.py
│   └── sample_data.py            # Sample queries and mock data
├── unit/                         # Unit tests
│   ├── test_entity_mapping.py    # Entity recognition tests
│   ├── test_nlp_engine.py        # NLP processing tests
│   └── test_learning.py          # Learning system tests
├── integration/                  # Integration tests
│   ├── test_api_endpoints.py     # API endpoint tests
│   └── test_integration_scenarios.py  # Real-world scenarios
└── performance/                  # Performance tests
    └── test_performance_benchmarks.py  # Performance benchmarks

```

## Running Tests

### Run All Tests
```bash
pytest tests/mcp_sistema/
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/mcp_sistema/ -m unit

# Integration tests only
pytest tests/mcp_sistema/ -m integration

# Performance tests only
pytest tests/mcp_sistema/ -m performance

# API tests only
pytest tests/mcp_sistema/ -m api

# NLP tests only
pytest tests/mcp_sistema/ -m nlp
```

### Run with Coverage
```bash
pytest tests/mcp_sistema/ --cov=app.mcp_sistema --cov-report=html
```

### Run Specific Test Files
```bash
# Entity mapping tests
pytest tests/mcp_sistema/test_entity_mapping.py

# API endpoint tests
pytest tests/mcp_sistema/test_api_endpoints.py

# Performance benchmarks
pytest tests/mcp_sistema/test_performance_benchmarks.py
```

## Test Categories

### 1. Entity Mapping Tests (`test_entity_mapping.py`)
- Entity creation and updates
- Mapping confidence scores
- Fuzzy search and pattern matching
- Special character handling
- Bulk operations
- Version tracking

### 2. NLP Engine Tests (`test_nlp_engine.py`)
- Query processing pipeline
- Intent classification
- Context management
- Multi-language support
- Error handling
- Performance metrics

### 3. API Endpoint Tests (`test_api_endpoints.py`)
- Authentication flows
- MCP query processing
- User preferences
- Rate limiting
- Error responses
- CORS configuration

### 4. Learning System Tests (`test_learning.py`)
- Feedback processing
- Pattern recognition
- Model training
- Active learning
- Performance optimization
- Cross-user learning

### 5. Performance Benchmarks (`test_performance_benchmarks.py`)
- Response time metrics
- Concurrent request handling
- Memory efficiency
- Database query performance
- Cache effectiveness
- Sustained load testing

### 6. Integration Scenarios (`test_integration_scenarios.py`)
- Complete user journeys
- Month-end closing
- Emergency shipments
- Batch operations
- Error recovery

## Key Fixtures

### Authentication
- `auth_headers`: JWT authentication headers
- `test_user`: Pre-created test user
- `jwt_service`: JWT token service

### Data Fixtures
- `sample_queries_pt_br`: Brazilian Portuguese test queries
- `entity_mappings`: Pre-configured entity mappings
- `mock_database_data`: Mock freight and client data
- `user_preferences`: User preference settings

### Performance
- `performance_metrics`: Performance thresholds
- `learning_scenarios`: Learning system test cases

## Performance Targets

- **API Response Time**: < 100ms average
- **NLP Processing**: < 50ms per query
- **Database Queries**: < 20ms average
- **Cache Hit Ratio**: > 80%
- **Concurrent Users**: 100+
- **Memory Usage**: < 512MB

## Coverage Requirements

- **Overall Coverage**: > 80%
- **Critical Paths**: > 90%
- **API Endpoints**: 100%
- **Error Handling**: > 85%

## Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Mocking**: Mock external services
4. **Performance**: Include performance assertions
5. **Documentation**: Document complex test scenarios

## Debugging Tests

### Verbose Output
```bash
pytest tests/mcp_sistema/ -v -s
```

### Debug Specific Test
```bash
pytest tests/mcp_sistema/test_nlp_engine.py::TestNLPEngine::test_process_query_basic -vv
```

### Show Local Variables on Failure
```bash
pytest tests/mcp_sistema/ --showlocals
```

## CI/CD Integration

Tests are automatically run on:
- Pull requests
- Main branch commits
- Release tags

Performance benchmarks are tracked over time to detect regressions.