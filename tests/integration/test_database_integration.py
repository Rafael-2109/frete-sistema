"""
Database integration tests for MCP system
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

# Import test utilities
from ..conftest import *


class TestDatabaseIntegration:
    """Test database operations and transactions"""
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_database_connection_pool(self, db_engine):
        """Test database connection pooling behavior"""
        # Get pool status before
        pool = db_engine.pool
        initial_size = pool.size()
        initial_checked_out = pool.checked_out_connections()
        
        # Create multiple connections
        connections = []
        for i in range(5):
            conn = db_engine.connect()
            connections.append(conn)
        
        # Check pool grew
        assert pool.checked_out_connections() == 5
        
        # Close connections
        for conn in connections:
            conn.close()
        
        # Verify connections returned to pool
        assert pool.checked_out_connections() == initial_checked_out
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_transaction_isolation(self, db_session):
        """Test transaction isolation levels"""
        # Create test table
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS test_isolation (
                id INTEGER PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        """))
        db_session.commit()
        
        # Insert test data
        db_session.execute(text("""
            INSERT INTO test_isolation (id, value, updated_at)
            VALUES (1, 'initial', :timestamp)
        """), {"timestamp": datetime.utcnow()})
        db_session.commit()
        
        # Start transaction 1
        with db_session.begin():
            # Update in transaction 1
            db_session.execute(text("""
                UPDATE test_isolation 
                SET value = 'updated_tx1' 
                WHERE id = 1
            """))
            
            # Create new session for transaction 2
            engine = db_session.get_bind()
            with Session(engine) as session2:
                # Try to read in transaction 2 (should see old value)
                result = session2.execute(text("""
                    SELECT value FROM test_isolation WHERE id = 1
                """)).scalar()
                assert result == 'initial'  # Isolation working
        
        # After commit, new session should see update
        with Session(engine) as session3:
            result = session3.execute(text("""
                SELECT value FROM test_isolation WHERE id = 1
            """)).scalar()
            assert result == 'updated_tx1'
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_mcp_audit_trail(self, db_session):
        """Test MCP operations audit trail in database"""
        # Create audit table
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                tool_name TEXT,
                user_id TEXT,
                request_data TEXT,
                response_data TEXT,
                status TEXT,
                error_message TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db_session.commit()
        
        # Log MCP operations
        operations = [
            {
                "operation_type": "tool_execution",
                "tool_name": "calculate_freight",
                "user_id": "user_123",
                "request_data": '{"origin": "SP", "destination": "RJ"}',
                "response_data": '{"cost": 250.00}',
                "status": "success",
                "duration_ms": 150
            },
            {
                "operation_type": "natural_language_query",
                "tool_name": None,
                "user_id": "user_456",
                "request_data": '{"query": "Track order 123"}',
                "response_data": '{"intent": "track_order"}',
                "status": "success",
                "duration_ms": 85
            },
            {
                "operation_type": "tool_execution",
                "tool_name": "invalid_tool",
                "user_id": "user_123",
                "request_data": '{"test": "data"}',
                "response_data": None,
                "status": "error",
                "error_message": "Tool not found",
                "duration_ms": 10
            }
        ]
        
        # Insert audit records
        for op in operations:
            db_session.execute(text("""
                INSERT INTO mcp_audit_log 
                (operation_type, tool_name, user_id, request_data, 
                 response_data, status, error_message, duration_ms)
                VALUES 
                (:operation_type, :tool_name, :user_id, :request_data,
                 :response_data, :status, :error_message, :duration_ms)
            """), op)
        db_session.commit()
        
        # Query audit trail
        # Test 1: Get all successful operations
        success_ops = db_session.execute(text("""
            SELECT COUNT(*) FROM mcp_audit_log WHERE status = 'success'
        """)).scalar()
        assert success_ops == 2
        
        # Test 2: Get average duration by operation type
        avg_duration = db_session.execute(text("""
            SELECT operation_type, AVG(duration_ms) as avg_ms
            FROM mcp_audit_log
            GROUP BY operation_type
        """)).fetchall()
        assert len(avg_duration) == 2
        
        # Test 3: Get user activity
        user_activity = db_session.execute(text("""
            SELECT user_id, COUNT(*) as operation_count
            FROM mcp_audit_log
            GROUP BY user_id
        """)).fetchall()
        assert len(user_activity) == 2
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_portfolio_database_schema(self, db_session):
        """Test portfolio integration database schema"""
        # Create portfolio tables
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolio_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                customer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                total_value DECIMAL(10,2),
                freight_cost DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON
            )
        """))
        
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolio_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10,2),
                FOREIGN KEY (order_id) REFERENCES portfolio_orders(id)
            )
        """))
        
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolio_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                location TEXT,
                notes TEXT,
                tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES portfolio_orders(id)
            )
        """))
        
        # Create indexes
        db_session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_orders_customer 
            ON portfolio_orders(customer_id)
        """))
        
        db_session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_orders_status 
            ON portfolio_orders(status)
        """))
        
        db_session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tracking_order 
            ON portfolio_tracking(order_id)
        """))
        
        db_session.commit()
        
        # Test data insertion with relationships
        # Insert order
        db_session.execute(text("""
            INSERT INTO portfolio_orders 
            (order_number, customer_id, status, total_value, freight_cost, metadata)
            VALUES 
            ('ORD-TEST-001', 'CUST-001', 'pending', 1500.00, 150.00, 
             '{"priority": "high", "notes": "VIP customer"}')
        """))
        
        order_id = db_session.execute(text("""
            SELECT id FROM portfolio_orders WHERE order_number = 'ORD-TEST-001'
        """)).scalar()
        
        # Insert order items
        db_session.execute(text("""
            INSERT INTO portfolio_order_items (order_id, sku, quantity, unit_price)
            VALUES 
            (:order_id, 'PROD-001', 5, 200.00),
            (:order_id, 'PROD-002', 10, 50.00)
        """), {"order_id": order_id})
        
        # Insert tracking
        db_session.execute(text("""
            INSERT INTO portfolio_tracking (order_id, status, location, notes)
            VALUES 
            (:order_id, 'created', 'São Paulo', 'Order received'),
            (:order_id, 'processing', 'São Paulo', 'Preparing for shipment')
        """), {"order_id": order_id})
        
        db_session.commit()
        
        # Test complex queries
        # Get order with items and tracking
        order_details = db_session.execute(text("""
            SELECT 
                o.order_number,
                o.status,
                o.total_value,
                COUNT(DISTINCT i.id) as item_count,
                COUNT(DISTINCT t.id) as tracking_count,
                json_extract(o.metadata, '$.priority') as priority
            FROM portfolio_orders o
            LEFT JOIN portfolio_order_items i ON o.id = i.order_id
            LEFT JOIN portfolio_tracking t ON o.id = t.order_id
            WHERE o.order_number = 'ORD-TEST-001'
            GROUP BY o.id
        """)).fetchone()
        
        assert order_details.item_count == 2
        assert order_details.tracking_count == 2
        assert order_details.priority == 'high'
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_memory_system_persistence(self, db_session):
        """Test MCP memory system database persistence"""
        # Create memory tables
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_memory_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                metadata JSON,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP
            )
        """))
        
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_memory_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id TEXT,
                context JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """))
        
        db_session.commit()
        
        # Test memory operations
        # Store memory
        memories = [
            {
                "key": "user_preference_123",
                "value": '{"theme": "dark", "language": "pt-BR"}',
                "metadata": '{"type": "user_preference"}'
            },
            {
                "key": "calculation_cache_abc",
                "value": '{"result": 250.00, "params": {"origin": "SP"}}',
                "metadata": '{"type": "cache", "ttl": 3600}',
                "expires_at": datetime.utcnow() + timedelta(hours=1)
            }
        ]
        
        for memory in memories:
            db_session.execute(text("""
                INSERT INTO mcp_memory_store (key, value, metadata, expires_at)
                VALUES (:key, :value, :metadata, :expires_at)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    metadata = excluded.metadata,
                    expires_at = excluded.expires_at,
                    updated_at = CURRENT_TIMESTAMP,
                    access_count = mcp_memory_store.access_count + 1
            """), memory)
        db_session.commit()
        
        # Retrieve and update access stats
        result = db_session.execute(text("""
            UPDATE mcp_memory_store
            SET access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE key = :key
            RETURNING value, metadata, access_count
        """), {"key": "user_preference_123"}).fetchone()
        
        assert result is not None
        assert result.access_count >= 1
        
        # Clean expired memories
        db_session.execute(text("""
            DELETE FROM mcp_memory_store
            WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
        """))
        db_session.commit()
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_performance_metrics_storage(self, db_session):
        """Test storage of performance metrics"""
        # Create metrics table
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                operation TEXT NOT NULL,
                value DECIMAL(10,4),
                unit TEXT,
                tags JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create aggregated metrics view
        db_session.execute(text("""
            CREATE VIEW IF NOT EXISTS mcp_metrics_summary AS
            SELECT 
                metric_type,
                operation,
                COUNT(*) as sample_count,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                DATE(timestamp) as metric_date
            FROM mcp_performance_metrics
            GROUP BY metric_type, operation, DATE(timestamp)
        """))
        
        db_session.commit()
        
        # Insert sample metrics
        metrics = [
            ("response_time", "calculate_freight", 125.5, "ms", '{"region": "SP-RJ"}'),
            ("response_time", "calculate_freight", 98.2, "ms", '{"region": "SP-MG"}'),
            ("response_time", "calculate_freight", 156.8, "ms", '{"region": "RJ-BA"}'),
            ("cpu_usage", "neural_processing", 45.2, "percent", '{"model": "v2"}'),
            ("memory_usage", "cache_operation", 256.0, "MB", '{"operation": "set"}'),
            ("throughput", "api_requests", 1250.0, "req/min", '{"endpoint": "/mcp/tools"}')
        ]
        
        for metric in metrics:
            db_session.execute(text("""
                INSERT INTO mcp_performance_metrics 
                (metric_type, operation, value, unit, tags)
                VALUES (:type, :op, :val, :unit, :tags)
            """), {
                "type": metric[0],
                "op": metric[1],
                "val": metric[2],
                "unit": metric[3],
                "tags": metric[4]
            })
        db_session.commit()
        
        # Query aggregated metrics
        summary = db_session.execute(text("""
            SELECT * FROM mcp_metrics_summary
            WHERE metric_type = 'response_time'
        """)).fetchone()
        
        assert summary.sample_count == 3
        assert summary.avg_value == pytest.approx(126.83, rel=0.01)
        assert summary.min_value == 98.2
        assert summary.max_value == 156.8
    
    @pytest.mark.integration
    @pytest.mark.mcp
    def test_database_migration_system(self, db_session):
        """Test database migration tracking system"""
        # Create migration tracking table
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum TEXT,
                execution_time_ms INTEGER
            )
        """))
        db_session.commit()
        
        # Simulate migrations
        migrations = [
            ("001", "create_base_tables", "abc123", 125),
            ("002", "add_indexes", "def456", 45),
            ("003", "add_audit_tables", "ghi789", 230)
        ]
        
        for version, name, checksum, exec_time in migrations:
            db_session.execute(text("""
                INSERT INTO mcp_migrations (version, name, checksum, execution_time_ms)
                VALUES (:version, :name, :checksum, :exec_time)
            """), {
                "version": version,
                "name": name,
                "checksum": checksum,
                "exec_time": exec_time
            })
        db_session.commit()
        
        # Check migration status
        latest = db_session.execute(text("""
            SELECT version, name FROM mcp_migrations
            ORDER BY version DESC
            LIMIT 1
        """)).fetchone()
        
        assert latest.version == "003"
        assert latest.name == "add_audit_tables"
        
        # Verify all migrations applied
        count = db_session.execute(text("""
            SELECT COUNT(*) FROM mcp_migrations
        """)).scalar()
        assert count == 3
    
    @pytest.mark.integration
    @pytest.mark.mcp
    async def test_async_database_operations(self, async_db_session):
        """Test asynchronous database operations"""
        # Create test table
        await async_db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS async_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        """))
        await async_db_session.commit()
        
        # Async bulk insert
        async def insert_batch(batch_size):
            for i in range(batch_size):
                await async_db_session.execute(text("""
                    INSERT INTO async_test (data) VALUES (:data)
                """), {"data": f"test_data_{i}"})
            await async_db_session.commit()
        
        # Run concurrent inserts
        await asyncio.gather(
            insert_batch(10),
            insert_batch(10),
            insert_batch(10)
        )
        
        # Verify all inserted
        count = await async_db_session.execute(text("""
            SELECT COUNT(*) FROM async_test
        """))
        result = await count.scalar()
        assert result == 30
        
        # Async update with processing
        async def process_records():
            records = await async_db_session.execute(text("""
                SELECT id, data FROM async_test
                WHERE processed = FALSE
                LIMIT 10
            """))
            
            for record in await records.fetchall():
                # Simulate processing
                await asyncio.sleep(0.01)
                
                await async_db_session.execute(text("""
                    UPDATE async_test 
                    SET processed = TRUE 
                    WHERE id = :id
                """), {"id": record.id})
            
            await async_db_session.commit()
        
        # Process records concurrently
        await asyncio.gather(
            process_records(),
            process_records(),
            process_records()
        )
        
        # Check processing complete
        processed = await async_db_session.execute(text("""
            SELECT COUNT(*) FROM async_test WHERE processed = TRUE
        """))
        processed_count = await processed.scalar()
        assert processed_count == 30