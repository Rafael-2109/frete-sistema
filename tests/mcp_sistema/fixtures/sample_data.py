"""
Sample data fixtures for MCP tests
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any


def get_sample_queries_pt_br() -> List[Dict[str, Any]]:
    """Get sample queries in Brazilian Portuguese"""
    return [
        # Shipment operations
        {
            "query": "criar embarque para São Paulo com 50 caixas",
            "intent": "create_shipment",
            "entities": {
                "action": "criar",
                "object": "embarque",
                "destination": "São Paulo",
                "quantity": 50,
                "unit": "caixas"
            },
            "expected_response": "Embarque criado com sucesso"
        },
        {
            "query": "adicionar 20 paletes ao embarque EMB001",
            "intent": "add_items_to_shipment",
            "entities": {
                "action": "adicionar",
                "quantity": 20,
                "unit": "paletes",
                "shipment_id": "EMB001"
            }
        },
        
        # Freight operations
        {
            "query": "aprovar todos os fretes pendentes do cliente ABC Transportes",
            "intent": "approve_freights",
            "entities": {
                "action": "aprovar",
                "object": "fretes",
                "status": "pendentes",
                "client": "ABC Transportes"
            }
        },
        {
            "query": "calcular frete para 1500kg de São Paulo para Rio de Janeiro",
            "intent": "calculate_freight",
            "entities": {
                "action": "calcular",
                "weight": 1500,
                "unit": "kg",
                "origin": "São Paulo",
                "destination": "Rio de Janeiro"
            }
        },
        
        # Status and tracking
        {
            "query": "qual o status da entrega do pedido 98765",
            "intent": "check_delivery_status",
            "entities": {
                "action": "verificar",
                "object": "entrega",
                "order_id": "98765"
            }
        },
        {
            "query": "rastrear embarque EMB123 em tempo real",
            "intent": "track_shipment",
            "entities": {
                "action": "rastrear",
                "object": "embarque",
                "shipment_id": "EMB123",
                "mode": "tempo real"
            }
        },
        
        # Reports and analytics
        {
            "query": "gerar relatório de faturamento do mês passado",
            "intent": "generate_report",
            "entities": {
                "action": "gerar",
                "report_type": "faturamento",
                "period": "mês passado"
            }
        },
        {
            "query": "mostrar gráfico de entregas da última semana por região",
            "intent": "show_analytics",
            "entities": {
                "action": "mostrar",
                "visualization": "gráfico",
                "metric": "entregas",
                "period": "última semana",
                "grouping": "região"
            }
        },
        
        # Financial operations
        {
            "query": "quanto foi faturado hoje até agora",
            "intent": "check_revenue",
            "entities": {
                "metric": "faturamento",
                "period": "hoje",
                "time_reference": "até agora"
            }
        },
        {
            "query": "listar faturas vencidas há mais de 30 dias",
            "intent": "list_overdue_invoices",
            "entities": {
                "action": "listar",
                "object": "faturas",
                "status": "vencidas",
                "days_overdue": 30
            }
        },
        
        # Client operations
        {
            "query": "cadastrar novo cliente Empresa XYZ LTDA com CNPJ 12345678000190",
            "intent": "create_client",
            "entities": {
                "action": "cadastrar",
                "object": "cliente",
                "name": "Empresa XYZ LTDA",
                "cnpj": "12345678000190"
            }
        },
        {
            "query": "histórico de embarques do cliente 456 dos últimos 6 meses",
            "intent": "client_history",
            "entities": {
                "object": "embarques",
                "client_id": "456",
                "period": "últimos 6 meses"
            }
        }
    ]


def get_mock_freight_data() -> List[Dict[str, Any]]:
    """Get mock freight data for testing"""
    base_date = datetime.now()
    return [
        {
            "id": 1,
            "numero": "FRT20240101",
            "cliente_id": 1,
            "origem": "São Paulo",
            "destino": "Rio de Janeiro",
            "peso": 1500.0,
            "valor": 2500.00,
            "status": "pendente",
            "created_at": base_date - timedelta(days=5),
            "prazo_entrega": base_date + timedelta(days=2)
        },
        {
            "id": 2,
            "numero": "FRT20240102",
            "cliente_id": 2,
            "origem": "Belo Horizonte",
            "destino": "Salvador",
            "peso": 3000.0,
            "valor": 4500.00,
            "status": "aprovado",
            "created_at": base_date - timedelta(days=3),
            "prazo_entrega": base_date + timedelta(days=4)
        },
        {
            "id": 3,
            "numero": "FRT20240103",
            "cliente_id": 1,
            "origem": "Curitiba",
            "destino": "Porto Alegre",
            "peso": 800.0,
            "valor": 1200.00,
            "status": "em_transito",
            "created_at": base_date - timedelta(days=2),
            "prazo_entrega": base_date + timedelta(days=1),
            "data_saida": base_date - timedelta(days=1)
        },
        {
            "id": 4,
            "numero": "FRT20240104",
            "cliente_id": 3,
            "origem": "Recife",
            "destino": "Fortaleza",
            "peso": 2200.0,
            "valor": 3100.00,
            "status": "entregue",
            "created_at": base_date - timedelta(days=7),
            "prazo_entrega": base_date - timedelta(days=2),
            "data_entrega": base_date - timedelta(days=3)
        }
    ]


def get_mock_client_data() -> List[Dict[str, Any]]:
    """Get mock client data for testing"""
    return [
        {
            "id": 1,
            "nome": "ABC Transportes LTDA",
            "cnpj": "12345678000190",
            "email": "contato@abctransportes.com.br",
            "telefone": "(11) 98765-4321",
            "endereco": "Rua das Flores, 123 - São Paulo/SP",
            "ativo": True,
            "limite_credito": 50000.00,
            "saldo_devedor": 12500.00
        },
        {
            "id": 2,
            "nome": "Logística Rápida S.A.",
            "cnpj": "98765432000121",
            "email": "financeiro@logisticarapida.com",
            "telefone": "(21) 91234-5678",
            "endereco": "Av. Principal, 456 - Rio de Janeiro/RJ",
            "ativo": True,
            "limite_credito": 75000.00,
            "saldo_devedor": 4500.00
        },
        {
            "id": 3,
            "nome": "Transporte Sul EIRELI",
            "cnpj": "45678901000156",
            "email": "sul@transportesul.net",
            "telefone": "(51) 93456-7890",
            "endereco": "Travessa Industrial, 789 - Porto Alegre/RS",
            "ativo": True,
            "limite_credito": 30000.00,
            "saldo_devedor": 0.00
        }
    ]


def get_performance_test_data() -> Dict[str, Any]:
    """Get data for performance testing"""
    return {
        "large_query_batch": [
            f"criar embarque {i} para cidade {i % 20}"
            for i in range(1000)
        ],
        "complex_queries": [
            "calcular frete para 5 embarques com destinos diferentes considerando prazo de entrega e seguro",
            "gerar relatório consolidado de todos os fretes do último trimestre agrupados por cliente e região com análise de margem",
            "otimizar rota de entrega para 15 pedidos na região metropolitana considerando janelas de tempo e capacidade dos veículos"
        ],
        "concurrent_users": 100,
        "requests_per_second": 50,
        "test_duration_seconds": 300
    }


def get_entity_mapping_seeds() -> List[Dict[str, Any]]:
    """Get seed data for entity mappings"""
    return [
        # Actions
        {"type": "action", "value": "criar", "mapped": "create", "confidence": 0.95},
        {"type": "action", "value": "gerar", "mapped": "generate", "confidence": 0.93},
        {"type": "action", "value": "aprovar", "mapped": "approve", "confidence": 0.97},
        {"type": "action", "value": "cancelar", "mapped": "cancel", "confidence": 0.96},
        {"type": "action", "value": "verificar", "mapped": "check", "confidence": 0.94},
        {"type": "action", "value": "listar", "mapped": "list", "confidence": 0.95},
        {"type": "action", "value": "buscar", "mapped": "search", "confidence": 0.92},
        {"type": "action", "value": "calcular", "mapped": "calculate", "confidence": 0.96},
        {"type": "action", "value": "rastrear", "mapped": "track", "confidence": 0.94},
        {"type": "action", "value": "exportar", "mapped": "export", "confidence": 0.93},
        
        # Objects
        {"type": "object", "value": "embarque", "mapped": "shipment", "confidence": 0.98},
        {"type": "object", "value": "frete", "mapped": "freight", "confidence": 0.97},
        {"type": "object", "value": "entrega", "mapped": "delivery", "confidence": 0.96},
        {"type": "object", "value": "cliente", "mapped": "client", "confidence": 0.98},
        {"type": "object", "value": "fatura", "mapped": "invoice", "confidence": 0.95},
        {"type": "object", "value": "pedido", "mapped": "order", "confidence": 0.96},
        {"type": "object", "value": "relatório", "mapped": "report", "confidence": 0.94},
        {"type": "object", "value": "pagamento", "mapped": "payment", "confidence": 0.95},
        
        # Status
        {"type": "status", "value": "pendente", "mapped": "pending", "confidence": 0.97},
        {"type": "status", "value": "aprovado", "mapped": "approved", "confidence": 0.98},
        {"type": "status", "value": "em trânsito", "mapped": "in_transit", "confidence": 0.95},
        {"type": "status", "value": "entregue", "mapped": "delivered", "confidence": 0.98},
        {"type": "status", "value": "cancelado", "mapped": "cancelled", "confidence": 0.96},
        {"type": "status", "value": "vencido", "mapped": "overdue", "confidence": 0.94},
        
        # Time periods
        {"type": "period", "value": "hoje", "mapped": "today", "confidence": 0.99},
        {"type": "period", "value": "ontem", "mapped": "yesterday", "confidence": 0.99},
        {"type": "period", "value": "semana passada", "mapped": "last_week", "confidence": 0.97},
        {"type": "period", "value": "mês passado", "mapped": "last_month", "confidence": 0.97},
        {"type": "period", "value": "último trimestre", "mapped": "last_quarter", "confidence": 0.96},
        
        # Brazilian cities
        {"type": "location", "value": "são paulo", "mapped": "SAO_PAULO", "confidence": 0.99},
        {"type": "location", "value": "rio de janeiro", "mapped": "RIO_DE_JANEIRO", "confidence": 0.99},
        {"type": "location", "value": "belo horizonte", "mapped": "BELO_HORIZONTE", "confidence": 0.99},
        {"type": "location", "value": "porto alegre", "mapped": "PORTO_ALEGRE", "confidence": 0.99},
        {"type": "location", "value": "curitiba", "mapped": "CURITIBA", "confidence": 0.99},
        {"type": "location", "value": "salvador", "mapped": "SALVADOR", "confidence": 0.99},
        {"type": "location", "value": "recife", "mapped": "RECIFE", "confidence": 0.99},
        {"type": "location", "value": "fortaleza", "mapped": "FORTALEZA", "confidence": 0.99},
        {"type": "location", "value": "brasília", "mapped": "BRASILIA", "confidence": 0.99},
        {"type": "location", "value": "manaus", "mapped": "MANAUS", "confidence": 0.99}
    ]


def get_learning_scenarios() -> List[Dict[str, Any]]:
    """Get scenarios for learning system testing"""
    return [
        {
            "name": "New User Onboarding",
            "description": "User learning to use the system",
            "interactions": [
                {"query": "como criar embarque", "intent": "help", "feedback": "positive"},
                {"query": "crir embarque", "intent": "create_shipment", "feedback": "corrected"},
                {"query": "criar embarque SP", "intent": "create_shipment", "feedback": "positive"},
                {"query": "adicionar items", "intent": "add_items", "feedback": "positive"}
            ],
            "expected_learning": {
                "typo_correction": ["crir" -> "criar"],
                "abbreviation_learning": ["SP" -> "São Paulo"],
                "user_preference": "simplified_queries"
            }
        },
        {
            "name": "Expert User Optimization",
            "description": "Advanced user with complex queries",
            "interactions": [
                {
                    "query": "bulk approve pending freights client:ABC status:pending created:last_week",
                    "intent": "bulk_approve",
                    "feedback": "positive"
                },
                {
                    "query": "generate comparative report Q1 vs Q2 groupby:region metrics:revenue,volume",
                    "intent": "advanced_report",
                    "feedback": "positive"
                }
            ],
            "expected_learning": {
                "query_style": "advanced",
                "preferred_syntax": "key:value",
                "common_filters": ["client", "status", "created"]
            }
        },
        {
            "name": "Regional Language Variations",
            "description": "Learning regional Portuguese variations",
            "interactions": [
                {"query": "despachar encomenda", "intent": "dispatch_order", "region": "PT"},
                {"query": "liberar guia", "intent": "release_document", "region": "BR-NE"},
                {"query": "tirar romaneio", "intent": "generate_manifest", "region": "BR-SP"}
            ],
            "expected_learning": {
                "regional_mappings": {
                    "encomenda": ["pedido", "carga"],
                    "guia": ["documento", "nota"],
                    "romaneio": ["manifesto", "lista"]
                }
            }
        }
    ]