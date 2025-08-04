"""
Entity Mapping Usage Examples

This file demonstrates how to use the entity_mapping module
for various business intelligence and data analysis tasks.
"""

from app.claude_ai_novo.entity_mapping import (
    EntityMapper, EntityPatternAnalyzer,
    create_entity_mapper, analyze_entities, discover_rules, group_clients_by_company
)
from datetime import datetime, timedelta


def example_cnpj_grouping():
    """Example: Group clients by company (CNPJ root)"""
    print("\n=== CNPJ Grouping Example ===")
    
    # Sample client data
    clients = [
        {'id': 1, 'cnpj': '11.222.333/0001-44', 'name': 'ABC Matriz', 'city': 'São Paulo'},
        {'id': 2, 'cnpj': '11.222.333/0002-55', 'name': 'ABC Filial SP', 'city': 'São Paulo'},
        {'id': 3, 'cnpj': '11.222.333/0003-66', 'name': 'ABC Filial RJ', 'city': 'Rio de Janeiro'},
        {'id': 4, 'cnpj': '99.888.777/0001-11', 'name': 'XYZ Ltda', 'city': 'Belo Horizonte'},
        {'id': 5, 'cnpj': '99.888.777/0002-22', 'name': 'XYZ Filial', 'city': 'Uberlândia'},
    ]
    
    # Group by company
    groups = group_clients_by_company(clients)
    
    for cnpj_root, companies in groups.items():
        print(f"\nCompany Group {cnpj_root}:")
        for company in companies:
            print(f"  - {company['name']} ({company['city']})")


def example_client_similarity():
    """Example: Find similar client names"""
    print("\n=== Client Similarity Example ===")
    
    mapper = create_entity_mapper()
    
    # List of existing clients
    existing_clients = [
        "ABC INDUSTRIA E COMERCIO LTDA",
        "ABC IND COM LTDA",
        "ABC LIMITADA",
        "XYZ TRANSPORTES SA",
        "BETA LOGISTICA LTDA",
        "ALFA DISTRIBUIDORA"
    ]
    
    # Search for similar to a new entry
    search_name = "ABC Ind. e Com. Limitada"
    
    similar = mapper.find_similar_clients(search_name, existing_clients, threshold=0.7)
    
    print(f"\nSearching for clients similar to: '{search_name}'")
    print("Similar clients found:")
    for client, score in similar:
        print(f"  - {client} (similarity: {score:.2%})")


def example_location_normalization():
    """Example: Normalize location data"""
    print("\n=== Location Normalization Example ===")
    
    mapper = create_entity_mapper()
    
    # Sample location data with variations
    locations = [
        ("São Paulo", "SP"),
        ("SÃO PAULO", "sp"),
        ("Rio de Janeiro", "RJ"),
        ("Rio De Janeiro", "rj"),
        ("Belo Horizonte", "MG"),
        ("Porto Alegre", "RS"),
        ("Invalid City", "XXX"),  # Invalid state code
    ]
    
    print("\nNormalizing locations:")
    for city, state in locations:
        result = mapper.normalize_location(city, state)
        print(f"  Original: {city}, {state}")
        print(f"  Normalized: {result['city_normalized']}, {result['state_normalized']}")
        if result['needs_validation']:
            print(f"  ⚠️  Needs validation!")
        print()


def example_status_harmonization():
    """Example: Harmonize status values across different contexts"""
    print("\n=== Status Harmonization Example ===")
    
    mapper = create_entity_mapper()
    
    # Sample status values from different modules
    status_samples = [
        # (status, context, description)
        ("ABERTO", "order", "New order"),
        ("Pendente", "order", "Pending order"),
        ("COTADO", "freight", "Quoted freight"),
        ("EMBARCADO", "freight", "Shipped freight"),
        ("Entregue", "delivery", "Delivered"),
        ("NF no CD", "delivery", "Invoice in warehouse"),
        ("CANCELADO", "order", "Cancelled order"),
        ("Em Processamento", "general", "Processing"),
    ]
    
    print("\nHarmonizing status values:")
    for status, context, description in status_samples:
        harmonized = mapper.harmonize_status(status, context)
        print(f"  {status} ({context}) -> {harmonized} # {description}")


def example_pattern_analysis():
    """Example: Analyze patterns in entity data"""
    print("\n=== Pattern Analysis Example ===")
    
    # Sample order data
    orders = [
        {
            'num_pedido': 'PED001',
            'cnpj_cpf': '11.222.333/0001-44',
            'cliente': 'ABC Ltda',
            'valor_total': 5000.00,
            'status': 'FATURADO',
            'data_pedido': datetime.now() - timedelta(days=30),
            'data_entrega': datetime.now() - timedelta(days=25),
            'transportadora': 'Trans X',
        },
        {
            'num_pedido': 'PED002',
            'cnpj_cpf': '11.222.333/0001-44',
            'cliente': 'ABC Ltda',
            'valor_total': 7500.00,
            'status': 'ENTREGUE',
            'data_pedido': datetime.now() - timedelta(days=20),
            'data_entrega': datetime.now() - timedelta(days=15),
            'transportadora': 'Trans X',
        },
        {
            'num_pedido': 'PED003',
            'cnpj_cpf': '99.888.777/0001-11',
            'cliente': 'XYZ SA',
            'valor_total': None,  # Missing value
            'status': 'ABERTO',
            'data_pedido': datetime.now() - timedelta(days=5),
            'data_entrega': None,
            'transportadora': 'Trans Y',
        },
    ]
    
    # Analyze patterns
    analysis = analyze_entities(orders, 'pedidos')
    
    print(f"\nAnalyzed {analysis['total_count']} orders")
    print("\nField Statistics:")
    for field, stats in analysis['field_patterns'].items():
        if stats['null_percentage'] > 0:
            print(f"  {field}: {stats['null_percentage']:.1f}% null values")


def example_business_rules_discovery():
    """Example: Discover business rules from data"""
    print("\n=== Business Rules Discovery Example ===")
    
    # Sample data with patterns
    deliveries = []
    
    # Pattern 1: Company A always uses same transporter
    for i in range(10):
        deliveries.append({
            'cnpj': '11.222.333/0001-44',
            'transportadora': 'Express Log',
            'forma_pgto_pedido': '30 dias',
            'vendedor': 'João Silva',
            'data_pedido': datetime.now() - timedelta(days=30-i),
            'data_entrega': datetime.now() - timedelta(days=25-i),
        })
    
    # Pattern 2: Company B uses multiple transporters
    for i in range(5):
        deliveries.append({
            'cnpj': '99.888.777/0001-11',
            'transportadora': f'Trans {chr(65+i)}',  # Trans A, B, C, D, E
            'forma_pgto_pedido': 'À vista',
            'vendedor': 'Maria Santos',
            'data_pedido': datetime.now() - timedelta(days=20-i),
            'data_entrega': datetime.now() - timedelta(days=18-i),
        })
    
    # Discover rules
    rules = discover_rules(deliveries)
    
    print("\nDiscovered Business Rules:")
    for rule in rules:
        if rule['confidence'] > 0.7:  # High confidence rules
            print(f"\n  Rule Type: {rule['type']}")
            print(f"  Description: {rule['rule']}")
            print(f"  Confidence: {rule['confidence']:.1%}")
            print(f"  Support: {rule['support_count']} occurrences")


def example_query_pattern_generation():
    """Example: Generate dynamic query patterns"""
    print("\n=== Query Pattern Generation Example ===")
    
    mapper = create_entity_mapper()
    
    # User filter criteria
    user_filters = {
        'data_pedido': {
            'start': '2024-01-01',
            'end': '2024-01-31'
        },
        'status': ['ABERTO', 'COTADO', 'FATURADO'],
        'valor_total': {
            'min': 1000.0,
            'max': 50000.0
        },
        'cliente': '%ABC%',  # LIKE pattern
        'transportadora': 'Express Log',
        'cnpj_cpf': '11.222.333/0001-44',
    }
    
    # Generate query pattern
    query_pattern = mapper.generate_dynamic_query_pattern(user_filters)
    
    print("\nGenerated Query Pattern:")
    print(f"  Date Ranges: {query_pattern['date_ranges']}")
    print(f"  Status Filters: {query_pattern['status_filters']}")
    print(f"  Numeric Ranges: {query_pattern['numeric_ranges']}")
    print(f"  Text Searches: {query_pattern['text_searches']}")
    print(f"  Base Filters: {query_pattern['base_filters']}")


def example_optimization_suggestions():
    """Example: Get optimization suggestions based on usage patterns"""
    print("\n=== Optimization Suggestions Example ===")
    
    mapper = create_entity_mapper()
    
    # Simulated usage statistics
    entity_stats = {
        'frequent_queries': {
            'cnpj_cpf': 15000,
            'status': 12000,
            'data_pedido': 8000,
            'cliente': 5000,
            'transportadora': 3000,
            'observacoes': 100,  # Rarely queried
        },
        'indexed_fields': ['id', 'num_pedido', 'cnpj_cpf'],
        'join_patterns': {
            'pedidos_x_entregas': 800,
            'pedidos_x_fretes': 600,
            'entregas_x_fretes': 400,
        },
        'null_percentages': {
            'telefone': 75,
            'email': 60,
            'observacoes': 85,
            'complemento_endereco': 90,
        }
    }
    
    # Get suggestions
    suggestions = mapper.suggest_entity_optimizations(entity_stats)
    
    print("\nOptimization Suggestions:")
    for suggestion in suggestions:
        print(f"\n  Type: {suggestion['type']}")
        print(f"  Priority: {suggestion['priority']}")
        print(f"  Reason: {suggestion['reason']}")
        if 'field' in suggestion:
            print(f"  Field: {suggestion['field']}")
        if 'pattern' in suggestion:
            print(f"  Pattern: {suggestion['pattern']}")


def main():
    """Run all examples"""
    print("Entity Mapping Module - Usage Examples")
    print("=" * 50)
    
    example_cnpj_grouping()
    example_client_similarity()
    example_location_normalization()
    example_status_harmonization()
    example_pattern_analysis()
    example_business_rules_discovery()
    example_query_pattern_generation()
    example_optimization_suggestions()
    
    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    main()