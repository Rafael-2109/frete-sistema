# Database Services for MCP Integration

This module provides optimized database services for integrating the freight management system with the MCP (Model Context Protocol) system.

## Overview

The database services layer provides:
- Optimized query operations for PostgreSQL
- Connection pooling management
- Query caching and performance monitoring
- Comprehensive analytics capabilities
- Model mapping utilities
- Bulk operations support

## Architecture

```
services/database/
├── __init__.py              # Service exports
├── base_service.py          # Base service class with common operations
├── freight_service.py       # Freight operations (fretes, CTe, invoices)
├── order_service.py         # Order management operations
├── portfolio_service.py     # Portfolio and stock projections
├── analytics_service.py     # Analytics and reporting
├── query_optimizer.py       # Query optimization utilities
├── model_mappings.py       # Model registry and transformations
├── examples.py             # Usage examples
└── README.md              # This file
```

## Services

### BaseService

Provides common database operations for all services:
- CRUD operations (Create, Read, Update, Delete)
- Transaction management
- Query building and filtering
- Pagination support
- Bulk operations

### FreightService

Manages freight-related operations:
- Freight search and filtering
- CTe processing
- Invoice management
- Extra expenses tracking
- Current account management
- Approval workflows

### OrderService

Handles order operations:
- Order search and status tracking
- Location normalization
- Quotation integration
- Route management
- Timeline tracking
- Problem detection

### PortfolioService

Manages portfolio and inventory:
- Active portfolio queries
- Stock projections (D0-D28)
- Pre-separation management
- Billing reconciliation
- Aging analysis
- Standby items tracking

### AnalyticsService

Provides advanced analytics:
- Dashboard metrics
- Trend analysis
- Comparative analysis
- Predictive analytics
- Executive reports
- Performance metrics

## Usage Examples

### Basic Operations

```python
from services.database import FreightService, OrderService

# Initialize services
freight_service = FreightService()
order_service = OrderService()

# Search freights
freights = freight_service.search_freights({
    'transportadora_id': 1,
    'status': 'PENDENTE',
    'valor_min': 100.0,
    'data_inicio': date.today() - timedelta(days=30)
})

# Get order statistics
stats = order_service.get_order_statistics()
print(f"Pending quotation: {stats['ABERTO']}")
```

### Analytics

```python
from services.database import AnalyticsService

analytics = AnalyticsService()

# Get dashboard metrics
metrics = analytics.get_dashboard_metrics()

# Trend analysis
trend = analytics.get_trend_analysis(
    metric='freight_volume',
    period='daily',
    days=30
)

# Generate executive report
report = analytics.generate_executive_report(period='monthly')
```

### Query Optimization

```python
from services.database.query_optimizer import QueryOptimizer

optimizer = QueryOptimizer(db.engine)

# Get slow queries
slow_queries = optimizer.get_slow_queries(threshold=1.0)

# Recommend indexes
recommendations = optimizer.recommend_indexes('fretes')

# Optimize connection pool
pool_config = optimizer.optimize_connection_pool({
    'pool_size': 5,
    'max_overflow': 10
})
```

### Cached Queries

```python
from services.database.query_optimizer import cached_query

class MyService(BaseService):
    @cached_query(ttl=300)  # Cache for 5 minutes
    def get_expensive_data(self, param):
        # Expensive query here
        return result
```

## Performance Features

### Connection Pooling

The services use SQLAlchemy's connection pooling with optimized settings:
- Pre-ping connections to detect stale connections
- Connection recycling every 5 minutes
- Automatic retry on connection failure
- Pool size optimization based on usage

### Query Caching

- Automatic caching for expensive queries
- TTL-based cache expiration
- Cache key normalization
- Manual cache clearing support

### Query Monitoring

- Automatic slow query detection
- Query execution statistics
- Performance metrics tracking
- Query plan analysis (PostgreSQL)

## Model Mappings

The `model_mappings.py` module provides:

### Model Registry

```python
from services.database.model_mappings import ModelRegistry

# Get all models
models = ModelRegistry.get_all_models()

# Get model by table name
model = ModelRegistry.get_model_by_table('fretes')

# Get model by name
model = ModelRegistry.get_model_by_name('frete')
```

### Model Transformations

```python
from services.database.model_mappings import ModelMapper

# Convert model to dictionary
frete_dict = ModelMapper.model_to_dict(frete_instance, include_relationships=True)

# Create model from dictionary
frete = ModelMapper.dict_to_model(Frete, data_dict)

# Validate data
errors = ModelMapper.validate_model_data(Frete, data_dict)
```

## Database Tables

### Core Tables

- **fretes**: Freight records with CTe information
- **pedidos**: Orders with status tracking
- **carteira_principal**: Main portfolio with stock projections
- **embarques**: Shipment records
- **transportadoras**: Carrier information

### Supporting Tables

- **faturas_frete**: Freight invoices
- **despesas_extras**: Extra expenses
- **conta_corrente_transportadoras**: Carrier current account
- **carteira_copia**: Portfolio copy for billing control
- **pre_separacao_item**: Pre-separation management

## Best Practices

1. **Use Services Instead of Direct Model Access**
   ```python
   # Good
   freights = freight_service.search_freights(params)
   
   # Avoid
   freights = Frete.query.filter(...).all()
   ```

2. **Handle Transactions Properly**
   ```python
   with freight_service.transaction():
       freight_service.update(id, data)
       order_service.update(id, data)
   ```

3. **Use Pagination for Large Results**
   ```python
   result = freight_service.paginate(
       query, page=1, per_page=50
   )
   ```

4. **Cache Expensive Queries**
   ```python
   @cached_query(ttl=600)
   def get_complex_analytics(self):
       # Expensive operation
   ```

5. **Monitor Query Performance**
   ```python
   slow_queries = optimizer.get_slow_queries()
   # Review and optimize
   ```

## Configuration

Database configuration is managed in `config.py`:

```python
# PostgreSQL optimizations
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 10,
    'max_overflow': 10,
    'connect_args': {
        'client_encoding': 'utf8',
        'connect_timeout': 10
    }
}
```

## Error Handling

All services include comprehensive error handling:
- Automatic transaction rollback on errors
- Detailed logging for debugging
- Graceful degradation for non-critical operations
- Error context in responses

## Future Enhancements

- [ ] Redis integration for distributed caching
- [ ] Elasticsearch integration for advanced search
- [ ] GraphQL API support
- [ ] Real-time change notifications
- [ ] Advanced query builder UI
- [ ] Automated index management

## Contributing

When adding new features:
1. Extend appropriate service class
2. Add comprehensive docstrings
3. Include error handling
4. Add usage examples
5. Update this README

## Testing

Run tests with:
```bash
pytest services/database/tests/
```

## Support

For issues or questions:
- Check examples.py for usage patterns
- Review service docstrings
- Check query optimizer recommendations
- Enable query logging for debugging