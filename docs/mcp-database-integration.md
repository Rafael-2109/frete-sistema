# MCP Server Database Integration Architecture

## 🗄️ Database Overview

### Current Infrastructure
- **Database**: PostgreSQL (production) / SQLite (development)
- **ORM**: SQLAlchemy 2.0
- **Migration Tool**: Flask-Migrate (Alembic)
- **Connection Management**: SQLAlchemy connection pooling
- **Encoding**: UTF-8 with explicit client encoding

### Connection Configuration
```python
# Production (Render.com)
DATABASE_URL = "postgresql://user:pass@host:5432/dbname?client_encoding=utf8"

# Development
DATABASE_URL = "sqlite:///frete_sistema.db"
```

## 📊 Database Schema Analysis

### Core Domain Models (20+ tables)

#### 1. **Pedidos (Orders)**
```sql
-- Main order table with 40+ columns
CREATE TABLE pedidos (
    id INTEGER PRIMARY KEY,
    separacao_lote_id VARCHAR(50),
    num_pedido VARCHAR(30) INDEX,
    data_pedido DATE,
    cnpj_cpf VARCHAR(20),
    raz_social_red VARCHAR(255),
    nome_cidade VARCHAR(120),
    cod_uf VARCHAR(2),
    cidade_normalizada VARCHAR(120),
    uf_normalizada VARCHAR(2),
    codigo_ibge VARCHAR(10),
    valor_saldo_total FLOAT,
    pallet_total FLOAT,
    peso_total FLOAT,
    rota VARCHAR(50),
    sub_rota VARCHAR(50),
    transportadora VARCHAR(100),
    valor_frete FLOAT,
    status VARCHAR(50) DEFAULT 'ABERTO',
    nf_cd BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cotacao_id INTEGER REFERENCES cotacoes(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    UNIQUE(num_pedido, expedicao, agendamento, protocolo)
);
```

#### 2. **Fretes (Freight)**
```sql
-- Freight management with CTe tracking
CREATE TABLE fretes (
    id INTEGER PRIMARY KEY,
    embarque_id INTEGER REFERENCES embarques(id),
    cnpj_cliente VARCHAR(20) INDEX,
    nome_cliente VARCHAR(255),
    transportadora_id INTEGER REFERENCES transportadoras(id),
    tipo_carga VARCHAR(20), -- 'FRACIONADA' or 'DIRETA'
    modalidade VARCHAR(50), -- VALOR, PESO, VAN
    peso_total FLOAT,
    valor_total_nfs FLOAT,
    valor_cotado FLOAT,
    valor_cte FLOAT,
    valor_considerado FLOAT,
    valor_pago FLOAT,
    numero_cte VARCHAR(50) INDEX,
    status VARCHAR(20) DEFAULT 'PENDENTE',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. **Carteira Principal**
```sql
-- Portfolio management system
CREATE TABLE carteira_principal (
    id INTEGER PRIMARY KEY,
    num_pedido VARCHAR(50),
    status_pedido VARCHAR(50),
    valor_total FLOAT,
    data_separacao DATE,
    agrupado_em VARCHAR(100),
    workspace_id INTEGER REFERENCES workspaces(id)
);
```

#### 4. **Embarques (Shipments)**
```sql
CREATE TABLE embarques (
    id INTEGER PRIMARY KEY,
    data_embarque DATE,
    transportadora_id INTEGER,
    status VARCHAR(50),
    total_peso FLOAT,
    total_valor FLOAT,
    created_at TIMESTAMP
);
```

### Supporting Tables
- **transportadoras**: Carrier companies
- **cotacoes**: Freight quotes
- **faturas_frete**: Freight invoices
- **despesas_extras**: Additional expenses
- **conta_corrente_transportadoras**: Carrier account balance
- **usuarios**: System users
- **veiculos**: Vehicle fleet
- **localidades**: Cities and states
- **tabelas**: Freight pricing tables

## 🔄 MCP Database Integration Design

### 1. Connection Pool Architecture
```python
class MCPDatabasePool:
    def __init__(self):
        self.engine = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"client_encoding": "utf8"}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def get_connection(self):
        """Get a database connection from pool"""
        return self.SessionLocal()
```

### 2. Query Optimization Strategies

#### Index Strategy
```sql
-- High-frequency query indexes
CREATE INDEX idx_pedidos_status ON pedidos(status);
CREATE INDEX idx_pedidos_data ON pedidos(data_pedido);
CREATE INDEX idx_fretes_transportadora ON fretes(transportadora_id);
CREATE INDEX idx_fretes_vencimento ON fretes(vencimento);
CREATE INDEX idx_carteira_workspace ON carteira_principal(workspace_id);
```

#### Materialized Views for Analytics
```sql
-- Pre-computed freight analytics
CREATE MATERIALIZED VIEW mv_freight_analytics AS
SELECT 
    t.razao_social as carrier,
    COUNT(f.id) as total_shipments,
    SUM(f.valor_pago) as total_paid,
    AVG(f.valor_pago - f.valor_cotado) as avg_difference
FROM fretes f
JOIN transportadoras t ON f.transportadora_id = t.id
GROUP BY t.id
WITH DATA;

-- Refresh strategy
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_freight_analytics;
```

### 3. MCP Tool Database Mappings

#### Tool: freight_quote
```python
async def freight_quote(params):
    """Calculate freight quote"""
    # Query pattern
    query = """
    SELECT 
        t.id, t.razao_social, tb.valor_kg, tb.percentual_valor,
        tb.frete_minimo_valor, tb.icms, tb.percentual_gris
    FROM transportadoras t
    JOIN tabelas tb ON t.id = tb.transportadora_id
    WHERE tb.uf_destino = :uf AND tb.ativo = true
    ORDER BY tb.valor_kg ASC
    LIMIT 5
    """
```

#### Tool: order_status
```python
async def order_status(params):
    """Check order status with related data"""
    # Optimized join query
    query = """
    SELECT 
        p.*,
        c.id as cotacao_id,
        c.valor_total as valor_cotado,
        e.data_embarque,
        f.numero_cte,
        f.status as frete_status
    FROM pedidos p
    LEFT JOIN cotacoes c ON p.cotacao_id = c.id
    LEFT JOIN embarques e ON p.num_pedido = ANY(e.pedidos_ids)
    LEFT JOIN fretes f ON e.id = f.embarque_id
    WHERE p.num_pedido = :order_number
    """
```

#### Tool: portfolio_analysis
```python
async def portfolio_analysis(params):
    """Analyze order portfolio"""
    # Complex aggregation query
    query = """
    WITH portfolio_stats AS (
        SELECT 
            workspace_id,
            COUNT(*) as total_orders,
            SUM(valor_total) as total_value,
            COUNT(CASE WHEN status_pedido = 'SEPARADO' THEN 1 END) as separated,
            COUNT(CASE WHEN agrupado_em IS NOT NULL THEN 1 END) as grouped
        FROM carteira_principal
        WHERE workspace_id = :workspace_id
        GROUP BY workspace_id
    )
    SELECT * FROM portfolio_stats
    """
```

### 4. Caching Strategy

#### Redis Integration
```python
class MCPCacheLayer:
    def __init__(self):
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        
    def cache_query(self, key: str, query_func, ttl: int = 300):
        """Cache database query results"""
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
            
        result = query_func()
        self.redis.setex(key, ttl, json.dumps(result))
        return result
```

#### Cache Patterns
- **Freight Tables**: Cache for 1 hour (slowly changing)
- **Order Status**: Cache for 5 minutes (frequently updated)
- **Analytics**: Cache for 30 minutes (computed views)
- **User Permissions**: Cache for 15 minutes

### 5. Data Access Patterns

#### Repository Pattern
```python
class OrderRepository:
    def __init__(self, session):
        self.session = session
        
    def find_by_number(self, order_number: str):
        return self.session.query(Pedido)\
            .filter(Pedido.num_pedido == order_number)\
            .first()
            
    def find_pending_quotes(self, limit: int = 100):
        return self.session.query(Pedido)\
            .filter(Pedido.status == 'ABERTO')\
            .order_by(Pedido.criado_em.desc())\
            .limit(limit)\
            .all()
```

#### Unit of Work Pattern
```python
class UnitOfWork:
    def __init__(self):
        self.session = SessionLocal()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.rollback()
        self.session.close()
        
    def commit(self):
        self.session.commit()
        
    def rollback(self):
        self.session.rollback()
```

### 6. Performance Monitoring

#### Query Performance Tracking
```python
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 1.0:  # Log slow queries
        logger.warning(f"Slow query ({total:.2f}s): {statement[:100]}...")
```

### 7. Data Migration Strategy

#### Async Data Processing
```python
async def process_large_dataset():
    """Process large datasets in chunks"""
    CHUNK_SIZE = 1000
    offset = 0
    
    while True:
        chunk = session.query(Pedido)\
            .offset(offset)\
            .limit(CHUNK_SIZE)\
            .all()
            
        if not chunk:
            break
            
        await process_chunk(chunk)
        offset += CHUNK_SIZE
```

## 🔐 Security Considerations

### 1. SQL Injection Prevention
- Use parameterized queries exclusively
- Validate all user inputs
- Escape special characters in LIKE queries

### 2. Access Control
```python
def check_data_access(user_id: int, resource_type: str, resource_id: int):
    """Verify user has access to specific data"""
    # Implement row-level security
    pass
```

### 3. Data Encryption
- Encrypt sensitive fields (CPF/CNPJ)
- Use SSL/TLS for database connections
- Implement field-level encryption for PII

## 📈 Monitoring & Observability

### 1. Database Metrics
- Connection pool usage
- Query execution time
- Cache hit rates
- Transaction rollback rates

### 2. Health Checks
```python
async def database_health_check():
    """Check database connectivity and performance"""
    try:
        start = time.time()
        result = session.execute("SELECT 1")
        latency = time.time() - start
        
        return {
            "status": "healthy",
            "latency_ms": latency * 1000,
            "connections": engine.pool.size()
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## 🚀 Implementation Roadmap

### Phase 1: Core Integration (Week 1)
- [ ] Set up connection pooling
- [ ] Implement basic CRUD operations
- [ ] Create order and freight tools

### Phase 2: Query Optimization (Week 2)
- [ ] Add database indexes
- [ ] Implement caching layer
- [ ] Create materialized views

### Phase 3: Advanced Features (Week 3)
- [ ] Implement real-time subscriptions
- [ ] Add batch processing capabilities
- [ ] Set up monitoring and alerts

### Phase 4: Performance Tuning (Week 4)
- [ ] Query optimization
- [ ] Connection pool tuning
- [ ] Load testing and benchmarking