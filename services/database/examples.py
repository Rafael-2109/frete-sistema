"""
Examples of Database Service Usage

This module provides examples of how to use the database services
for MCP integration with the freight management system.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any

# Import services
from services.database import (
    FreightService, OrderService, PortfolioService, 
    AnalyticsService, BaseService
)
from services.database.query_optimizer import QueryOptimizer, cached_query, monitor_query_performance
from services.database.model_mappings import ModelRegistry, ModelMapper, DataTransformers

# Initialize services
freight_service = FreightService()
order_service = OrderService()
portfolio_service = PortfolioService()
analytics_service = AnalyticsService()


def example_freight_operations():
    """Example freight operations"""
    print("=== Freight Service Examples ===\n")
    
    # 1. Search freights with multiple criteria
    search_params = {
        'transportadora_id': 1,
        'status': 'PENDENTE',
        'valor_min': 100.0,
        'valor_max': 5000.0,
        'data_inicio': date.today() - timedelta(days=30),
        'data_fim': date.today(),
        'sort_by': 'valor_pago',
        'order': 'desc'
    }
    
    freights = freight_service.search_freights(search_params)
    print(f"Found {len(freights)} freights matching criteria")
    
    # 2. Get freight analytics
    analytics = freight_service.get_freight_analytics(
        start_date=date.today() - timedelta(days=30),
        end_date=date.today(),
        group_by='transportadora'
    )
    
    print("\nTop carriers by volume:")
    for item in analytics[:5]:
        print(f"  {item['name']}: {item['count']} freights, R$ {item['total_value']:,.2f}")
        
    # 3. Process freight approval
    pending = freight_service.get_pending_approvals()
    if pending:
        freight = pending[0]
        success = freight_service.approve_freight(
            freight_id=freight.id,
            approved_by='system_admin',
            observations='Approved via MCP integration'
        )
        print(f"\nFreight {freight.numero_cte} approval: {'Success' if success else 'Failed'}")
        
    # 4. Get carrier current account balance
    balance = freight_service.get_current_account_balance(transportadora_id=1)
    print(f"\nCarrier balance: R$ {balance['balance']:,.2f}")
    

def example_order_operations():
    """Example order operations"""
    print("\n=== Order Service Examples ===\n")
    
    # 1. Get order statistics
    stats = order_service.get_order_statistics()
    print("Order Status Distribution:")
    for status, count in stats.items():
        if status != 'total':
            print(f"  {status}: {count}")
            
    # 2. Search orders
    search_params = {
        'uf': 'SP',
        'valor_min': 1000.0,
        'data_pedido_inicio': date.today() - timedelta(days=7),
        'sort_by': 'valor_saldo_total',
        'order': 'desc'
    }
    
    orders = order_service.search_orders(search_params)
    print(f"\nFound {len(orders)} orders in SP from last week")
    
    # 3. Get route summary
    route_summary = order_service.get_route_summary()
    print("\nTop routes by volume:")
    for route in route_summary[:5]:
        print(f"  {route['rota']}/{route['sub_rota']}: {route['order_count']} orders")
        
    # 4. Update order quotation
    if orders:
        order = orders[0]
        quotation_data = {
            'cotacao_id': 123,
            'transportadora': 'Transportadora XYZ',
            'valor_frete': 250.00,
            'valor_por_kg': 0.50,
            'modalidade': 'PESO',
            'lead_time': 3
        }
        
        success = order_service.update_order_quotation(order.id, quotation_data)
        print(f"\nOrder quotation update: {'Success' if success else 'Failed'}")
        

def example_portfolio_operations():
    """Example portfolio operations"""
    print("\n=== Portfolio Service Examples ===\n")
    
    # 1. Get portfolio summary
    summary = portfolio_service.get_portfolio_summary()
    print("Portfolio Summary:")
    print(f"  Active Orders: {summary['total_orders']:,}")
    print(f"  Total Value: R$ {summary['total_value']:,.2f}")
    print(f"  Total Customers: {summary['total_customers']:,}")
    
    # 2. Analyze stock rupture risk
    rupture_analysis = portfolio_service.analyze_stock_rupture(days_ahead=7)
    print(f"\nProducts at risk of rupture in 7 days: {len(rupture_analysis)}")
    for product in rupture_analysis[:3]:
        print(f"  {product['nome_produto']}: {product['days_to_rupture']} days")
        
    # 3. Get portfolio aging analysis
    aging = portfolio_service.analyze_portfolio_aging()
    print("\nPortfolio Aging:")
    for range_name, items in aging.items():
        total_value = sum(item['total_value'] for item in items)
        print(f"  {range_name}: R$ {total_value:,.2f}")
        
    # 4. Create pre-separation
    items_to_separate = [
        {
            'num_pedido': 'PED001',
            'cod_produto': 'PROD001',
            'qtd_selecionada': 100,
            'agendamento': date.today() + timedelta(days=2),
            'protocolo': 'PROT001'
        }
    ]
    
    lote_id = portfolio_service.create_pre_separation(
        items=items_to_separate,
        user='operator1',
        expedition_date=date.today() + timedelta(days=1)
    )
    print(f"\nPre-separation created: {lote_id}")
    

def example_analytics_operations():
    """Example analytics operations"""
    print("\n=== Analytics Service Examples ===\n")
    
    # 1. Get dashboard metrics
    metrics = analytics_service.get_dashboard_metrics()
    print("Dashboard Metrics:")
    print(f"  Total Freights: {metrics['freight']['total_freights']:,}")
    print(f"  Growth: {metrics['freight']['growth_percentage']}%")
    print(f"  Active Portfolio: R$ {metrics['portfolio']['total_value']:,.2f}")
    
    # 2. Get trend analysis
    trend = analytics_service.get_trend_analysis(
        metric='freight_volume',
        period='weekly',
        days=30
    )
    print(f"\nFreight volume trend: {trend.get('trend', {}).get('direction', 'N/A')}")
    
    # 3. Comparative analysis
    comparison = analytics_service.get_comparative_analysis(
        dimension='carrier',
        metric='efficiency',
        period_days=30
    )
    print("\nCarrier Efficiency Ranking:")
    for i, (carrier, efficiency) in enumerate(zip(comparison['labels'], comparison['values'])):
        print(f"  {i+1}. {carrier}: {efficiency:.1f}%")
        
    # 4. Generate executive report
    report = analytics_service.generate_executive_report(period='monthly')
    print(f"\nExecutive Report for {report['period']['start']} to {report['period']['end']}:")
    print(f"  Total Freights: {report['summary']['total_freights']:,}")
    print(f"  Total Value: R$ {report['summary']['total_value']:,.2f}")
    

def example_query_optimization():
    """Example query optimization"""
    print("\n=== Query Optimization Examples ===\n")
    
    from app import db
    optimizer = QueryOptimizer(db.engine)
    
    # 1. Get slow queries
    slow_queries = optimizer.get_slow_queries(threshold=0.5)
    if slow_queries:
        print("Slow Queries Detected:")
        for query in slow_queries[:3]:
            print(f"  Query: {query['query_key'][:50]}...")
            print(f"  Avg Time: {query['avg_time']}s")
            
    # 2. Recommend indexes
    recommendations = optimizer.recommend_indexes('fretes', min_usage=20)
    print("\nIndex Recommendations for 'fretes' table:")
    for rec in recommendations[:3]:
        print(f"  {rec['sql']}")
        print(f"  Reason: {rec['reason']}")
        
    # 3. Get table statistics
    stats = optimizer.get_table_statistics('fretes')
    print(f"\nTable 'fretes' Statistics:")
    print(f"  Rows: {stats['row_count']:,}")
    print(f"  Size: {stats['size']}")
    print(f"  Indexes: {len(stats['indexes'])}")
    
    # 4. Connection pool recommendations
    current_config = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 300
    }
    
    pool_recommendations = optimizer.optimize_connection_pool(current_config)
    print("\nConnection Pool Recommendations:")
    for key, value in pool_recommendations.items():
        if key != 'reasoning':
            print(f"  {key}: {value}")
            

def example_model_operations():
    """Example model mapping operations"""
    print("\n=== Model Mapping Examples ===\n")
    
    # 1. Get model schema
    from app.fretes.models import Frete
    schema = ModelMapper.get_model_schema(Frete)
    print(f"Frete Model Schema:")
    print(f"  Table: {schema['table_name']}")
    print(f"  Columns: {len(schema['columns'])}")
    print(f"  Relationships: {list(schema['relationships'].keys())}")
    
    # 2. Convert model to dict
    frete = freight_service.get_by_id(1)
    if frete:
        frete_dict = ModelMapper.model_to_dict(frete, include_relationships=True)
        print(f"\nFrete as dict: {list(frete_dict.keys())[:5]}...")
        
    # 3. Validate data
    test_data = {
        'numero_cte': '123456',
        'valor_pago': 'invalid',  # Should be numeric
        'transportadora_id': 1
    }
    
    errors = ModelMapper.validate_model_data(Frete, test_data)
    if errors:
        print("\nValidation Errors:")
        for field, messages in errors.items():
            print(f"  {field}: {', '.join(messages)}")
            
    # 4. Get relationship graph
    from services.database.model_mappings import ModelRelationships
    graph = ModelRelationships.get_relationship_graph('frete', depth=2)
    print("\nFrete Relationship Graph:")
    for model, related in graph.items():
        print(f"  {model} -> {', '.join(related)}")
        

def example_cached_operations():
    """Example of using cached queries"""
    print("\n=== Cached Query Examples ===\n")
    
    # Define a cached service method
    class CachedFreightService(FreightService):
        @cached_query(ttl=600)  # Cache for 10 minutes
        def get_expensive_analytics(self, start_date, end_date):
            # Simulate expensive query
            return self.get_freight_analytics(start_date, end_date, 'transportadora')
            
    cached_service = CachedFreightService()
    
    # First call - hits database
    start = datetime.now()
    result1 = cached_service.get_expensive_analytics(
        date.today() - timedelta(days=30),
        date.today()
    )
    duration1 = (datetime.now() - start).total_seconds()
    print(f"First call duration: {duration1:.3f}s")
    
    # Second call - hits cache
    start = datetime.now()
    result2 = cached_service.get_expensive_analytics(
        date.today() - timedelta(days=30),
        date.today()
    )
    duration2 = (datetime.now() - start).total_seconds()
    print(f"Second call duration: {duration2:.3f}s (cached)")
    print(f"Speed improvement: {duration1/duration2:.1f}x")
    

def example_bulk_operations():
    """Example bulk operations"""
    print("\n=== Bulk Operations Examples ===\n")
    
    # 1. Bulk create freights
    freight_records = [
        {
            'embarque_id': 1,
            'cnpj_cliente': '12345678901234',
            'nome_cliente': 'Cliente A',
            'transportadora_id': 1,
            'tipo_carga': 'FRACIONADA',
            'modalidade': 'PESO',
            'uf_destino': 'SP',
            'cidade_destino': 'São Paulo',
            'peso_total': 100.0,
            'valor_total_nfs': 1000.0,
            'quantidade_nfs': 1,
            'numeros_nfs': '001',
            'valor_cotado': 50.0,
            'valor_considerado': 50.0,
            'criado_por': 'system'
        }
        for i in range(5)
    ]
    
    # This would create multiple freights in one operation
    # freights = freight_service.bulk_create(freight_records)
    # print(f"Created {len(freights)} freights in bulk")
    
    # 2. Bulk update routes
    route_updates = [
        {'order_id': 1, 'rota': 'SP-CAPITAL', 'sub_rota': 'ZONA-SUL'},
        {'order_id': 2, 'rota': 'SP-CAPITAL', 'sub_rota': 'ZONA-NORTE'},
        {'order_id': 3, 'rota': 'SP-INTERIOR', 'sub_rota': 'CAMPINAS'}
    ]
    
    updated_count = order_service.bulk_update_routes(route_updates)
    print(f"Updated routes for {updated_count} orders")
    

def main():
    """Run all examples"""
    print("MCP Database Integration Examples")
    print("=" * 50)
    
    try:
        example_freight_operations()
        example_order_operations()
        example_portfolio_operations()
        example_analytics_operations()
        example_query_optimization()
        example_model_operations()
        example_cached_operations()
        example_bulk_operations()
        
    except Exception as e:
        print(f"\nError running examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()