# Permission System Test Suite

Comprehensive test suite for the permission system including unit tests, integration tests, performance tests, and edge case validation.

## Test Structure

```
app/permissions/tests/
├── __init__.py                    # Test configuration
├── base_test.py                   # Base test class with utilities
├── run_tests.py                   # Main test runner
├── test_report.py                 # Report generator
├── README.md                      # This file
│
├── unit/                          # Unit tests
│   ├── test_models.py            # Model tests
│   └── test_edge_cases.py        # Edge case tests
│
├── integration/                   # Integration tests
│   ├── test_api.py               # API endpoint tests
│   └── test_ui_interactions.py   # UI interaction tests
│
├── performance/                   # Performance tests
│   └── test_performance.py       # Performance and load tests
│
└── fixtures/                      # Test data
    └── test_data.py              # Test fixtures and scenarios
```

## Running Tests

### Run All Tests
```bash
python app/permissions/tests/run_tests.py
```

### Run Specific Test Types
```bash
# Only unit tests
python app/permissions/tests/run_tests.py --types unit

# Only integration tests
python app/permissions/tests/run_tests.py --types integration

# Only performance tests
python app/permissions/tests/run_tests.py --types performance

# Multiple types
python app/permissions/tests/run_tests.py --types unit integration
```

### Run Without Coverage
```bash
python app/permissions/tests/run_tests.py --no-coverage
```

### Run With Different Verbosity
```bash
# Quiet mode
python app/permissions/tests/run_tests.py --verbosity 0

# Normal mode
python app/permissions/tests/run_tests.py --verbosity 1

# Verbose mode (default)
python app/permissions/tests/run_tests.py --verbosity 2
```

## Test Categories

### 1. Unit Tests (`unit/`)

#### Model Tests (`test_models.py`)
- **PerfilUsuario**: User profile creation and hierarchy
- **ModuloSistema**: System module management
- **FuncaoModulo**: Module function operations
- **PermissaoUsuario**: User permission CRUD
- **UsuarioVendedor**: Vendor associations
- **UsuarioEquipeVendas**: Team associations
- **LogPermissao**: Audit logging
- **Hierarchical Models**: Category/Module/SubModule hierarchy
- **PermissionTemplate**: Template management

#### Edge Case Tests (`test_edge_cases.py`)
- **Circular Dependencies**: Prevention and handling
- **Batch Operations**: Large-scale operations
- **Concurrent Access**: Thread safety
- **Data Integrity**: Constraints and validation
- **Boundary Conditions**: Limits and edge values

### 2. Integration Tests (`integration/`)

#### API Tests (`test_api.py`)
- Health check endpoint
- Category/Module/SubModule CRUD
- User permission management
- Vendor/Team assignment
- Batch operations
- Template application
- Audit log retrieval
- Error handling
- Pagination

#### UI Interaction Tests (`test_ui_interactions.py`)
- Permission tree view
- Form submissions
- AJAX operations
- Real-time updates
- Form validations
- Accessibility features
- Search and filtering

### 3. Performance Tests (`performance/`)

#### Performance Metrics (`test_performance.py`)
- Query performance (< 100ms target)
- Bulk operations (> 100 ops/sec)
- Concurrent access handling
- Memory usage optimization
- Audit log performance

## Test Fixtures

The `fixtures/test_data.py` module provides:

- **TestDataGenerator**: Create test data programmatically
- **TestScenarios**: Pre-built test scenarios
  - Basic scenario (5 users, simple hierarchy)
  - Performance scenario (100 users, complex hierarchy)
  - Edge case scenario (problematic data)
- **Fixture constants**: Reusable test data

## Code Coverage

Tests aim for > 80% code coverage. Coverage reports are generated in:
- Console output
- HTML report: `htmlcov_permissions/`
- XML report: `coverage_permissions.xml`

## Test Reports

After running tests, reports are generated in `test_reports/`:
- `permission_tests.html` - HTML report with visualizations
- `permission_tests.json` - JSON format for CI/CD
- `permission_tests.md` - Markdown summary

## Performance Benchmarks

| Metric | Target | Typical Result |
|--------|--------|----------------|
| Permission Check | < 10ms | ~5ms |
| Bulk Assignment (500 perms) | < 2s | ~1.2s |
| API Response | < 200ms | ~120ms |
| Concurrent Checks (20 threads) | < 1s | ~0.6s |
| Query with Hierarchy | < 20ms | ~15ms |

## Writing New Tests

### 1. Extend BasePermissionTest
```python
from app.permissions.tests.base_test import BasePermissionTest

class TestNewFeature(BasePermissionTest):
    def test_something(self):
        # Use helper methods
        user = self._create_test_user('Test', 'test@example.com')
        permission = self._create_test_permission(user, 'module', 'function')
        
        # Make assertions
        self.assert_permission_granted(user, 'module', 'function')
```

### 2. Use Test Fixtures
```python
from app.permissions.tests.fixtures.test_data import TestScenarios

class TestWithFixtures(BasePermissionTest):
    def setUp(self):
        super().setUp()
        self.scenario = TestScenarios.setup_basic_scenario()
        
    def test_with_fixtures(self):
        users = self.scenario['users']
        # Test with pre-created data
```

### 3. Add to Test Runner
Update `run_tests.py` to include new test classes:
```python
from app.permissions.tests.unit.test_new_feature import TestNewFeature

# In appropriate test suite
unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestNewFeature))
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Permission Tests
  run: |
    python app/permissions/tests/run_tests.py
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage_permissions.xml
    flags: permissions
```

### Jenkins Example
```groovy
stage('Permission Tests') {
    steps {
        sh 'python app/permissions/tests/run_tests.py'
        publishHTML([
            reportDir: 'htmlcov_permissions',
            reportFiles: 'index.html',
            reportName: 'Permission Coverage'
        ])
    }
}
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure project root is in PYTHONPATH
2. **Database Errors**: Check test database configuration
3. **Timeout Errors**: Increase timeout for slow operations
4. **Memory Issues**: Run performance tests separately

### Debug Mode

Set environment variables for debugging:
```bash
export PERMISSION_TEST_DEBUG=1
export PERMISSION_TEST_DB_ECHO=1
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Always clean up test data
3. **Assertions**: Use specific assertions
4. **Performance**: Keep tests fast (< 100ms each)
5. **Coverage**: Aim for > 80% code coverage
6. **Documentation**: Document complex test scenarios

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure all tests pass
3. Add edge case tests
4. Update performance benchmarks
5. Document new test scenarios