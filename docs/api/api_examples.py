"""
API Request/Response Examples for Frete Sistema

This module contains comprehensive examples for all API endpoints,
demonstrating proper usage and expected responses.
"""

from typing import Dict, Any


# ============================================================================
# AUTHENTICATION EXAMPLES
# ============================================================================

AUTH_EXAMPLES = {
    "login": {
        "request": {
            "url": "POST /api/v1/auth/login",
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                "email": "admin@fretesistema.com.br",
                "password": "senha123"
            }
        },
        "response_success": {
            "success": True,
            "message": "Login successful",
            "timestamp": "2024-01-15T10:30:00Z",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        },
        "response_error": {
            "success": False,
            "error": "Invalid credentials",
            "error_code": "AUTH_FAILED",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "refresh_token": {
        "request": {
            "url": "POST /api/v1/auth/refresh",
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "response": {
            "success": True,
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600
        }
    }
}

# ============================================================================
# EMBARQUES (SHIPMENTS) EXAMPLES
# ============================================================================

EMBARQUES_EXAMPLES = {
    "list_embarques": {
        "request": {
            "url": "GET /api/v1/embarques?status=ativo&page=1&limit=10",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "response": {
            "success": True,
            "data": [
                {
                    "id": 1234,
                    "numero": "EMB-2024-001",
                    "status": "ativo",
                    "data_embarque": "2024-01-15T08:00:00Z",
                    "transportadora_id": 45,
                    "transportadora": {
                        "id": 45,
                        "razao_social": "Transportadora ABC Ltda",
                        "cnpj": "12.345.678/0001-90",
                        "ativa": True
                    },
                    "total_fretes": 15,
                    "valor_total": 25650.75,
                    "created_at": "2024-01-14T15:30:00Z",
                    "updated_at": None
                },
                {
                    "id": 1235,
                    "numero": "EMB-2024-002",
                    "status": "ativo",
                    "data_embarque": "2024-01-16T08:00:00Z",
                    "transportadora_id": 12,
                    "transportadora": {
                        "id": 12,
                        "razao_social": "Express Logística S/A",
                        "cnpj": "98.765.432/0001-10",
                        "ativa": True
                    },
                    "total_fretes": 8,
                    "valor_total": 12800.50,
                    "created_at": "2024-01-15T09:15:00Z",
                    "updated_at": None
                }
            ],
            "total": 156,
            "page": 1,
            "pages": 16,
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "create_embarque": {
        "request": {
            "url": "POST /api/v1/embarques",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Content-Type": "application/json"
            },
            "body": {
                "numero": "EMB-2024-003",
                "status": "ativo",
                "data_embarque": "2024-01-17T08:00:00Z",
                "transportadora_id": 45,
                "observacoes": "Carga refrigerada - manter temperatura",
                "fretes_ids": [567, 568, 569, 570]
            }
        },
        "response": {
            "success": True,
            "message": "Embarque criado com sucesso",
            "data": {
                "id": 1236,
                "numero": "EMB-2024-003",
                "status": "ativo",
                "data_embarque": "2024-01-17T08:00:00Z",
                "transportadora_id": 45,
                "transportadora": {
                    "id": 45,
                    "razao_social": "Transportadora ABC Ltda",
                    "cnpj": "12.345.678/0001-90",
                    "ativa": True
                },
                "total_fretes": 4,
                "valor_total": 8950.00,
                "created_at": "2024-01-15T10:30:00Z",
                "observacoes": "Carga refrigerada - manter temperatura"
            }
        }
    },
    "update_embarque": {
        "request": {
            "url": "PUT /api/v1/embarques/1234",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Content-Type": "application/json"
            },
            "body": {
                "status": "finalizado",
                "observacoes": "Entrega concluída sem intercorrências"
            }
        },
        "response": {
            "success": True,
            "message": "Embarque atualizado com sucesso",
            "data": {
                "id": 1234,
                "numero": "EMB-2024-001",
                "status": "finalizado",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }
}

# ============================================================================
# FRETES (FREIGHT) EXAMPLES
# ============================================================================

FRETES_EXAMPLES = {
    "list_fretes": {
        "request": {
            "url": "GET /api/v1/fretes?status_aprovacao=pendente&limit=5",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "response": {
            "success": True,
            "data": [
                {
                    "id": 5678,
                    "embarque_id": 1234,
                    "embarque_numero": "EMB-2024-001",
                    "transportadora_id": 45,
                    "transportadora": {
                        "id": 45,
                        "razao_social": "Transportadora ABC Ltda",
                        "cnpj": "12.345.678/0001-90",
                        "ativa": True
                    },
                    "valor_cotado": 1250.50,
                    "valor_aprovado": None,
                    "status_aprovacao": "pendente",
                    "numero_cte": None,
                    "tem_cte": False,
                    "created_at": "2024-01-14T15:30:00Z"
                }
            ],
            "total": 23,
            "pending_approval": 23,
            "total_value": 28750.25,
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "approve_frete": {
        "request": {
            "url": "PUT /api/v1/fretes/5678/approve",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Content-Type": "application/json"
            },
            "body": {
                "valor_aprovado": 1200.00,
                "observacoes": "Valor negociado com transportadora"
            }
        },
        "response": {
            "success": True,
            "message": "Frete aprovado com sucesso",
            "data": {
                "id": 5678,
                "status_aprovacao": "aprovado",
                "valor_aprovado": 1200.00,
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    },
    "add_cte": {
        "request": {
            "url": "PUT /api/v1/fretes/5678/cte",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Content-Type": "application/json"
            },
            "body": {
                "numero_cte": "35240112345678000190570010000123450123456789"
            }
        },
        "response": {
            "success": True,
            "message": "CT-e vinculado com sucesso",
            "data": {
                "id": 5678,
                "numero_cte": "35240112345678000190570010000123450123456789",
                "tem_cte": True
            }
        }
    }
}

# ============================================================================
# MONITORAMENTO (MONITORING) EXAMPLES
# ============================================================================

MONITORAMENTO_EXAMPLES = {
    "list_entregas": {
        "request": {
            "url": "GET /api/v1/monitoramento?pendencia_financeira=true&limit=10",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "response": {
            "success": True,
            "data": [
                {
                    "id": 7890,
                    "numero_nf": "NF-123456",
                    "cliente": "Supermercados União",
                    "municipio": "São Paulo",
                    "uf": "SP",
                    "valor_nf": 15750.90,
                    "pendencia_financeira": True,
                    "status_finalizacao": "em_andamento",
                    "transportadora": "Express Logística S/A",
                    "data_faturamento": "2024-01-10T00:00:00Z",
                    "data_embarque": "2024-01-12T08:00:00Z",
                    "data_entrega_prevista": "2024-01-16T18:00:00Z",
                    "data_entrega_real": None,
                    "dias_em_transito": 3
                }
            ],
            "total": 45,
            "entregues": 12,
            "pendencias": 15,
            "em_transito": 18,
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "update_entrega": {
        "request": {
            "url": "PUT /api/v1/monitoramento/7890",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Content-Type": "application/json"
            },
            "body": {
                "status_finalizacao": "entregue",
                "data_entrega_real": "2024-01-16T14:30:00Z",
                "observacoes": "Entregue ao responsável do setor de recebimento"
            }
        },
        "response": {
            "success": True,
            "message": "Entrega atualizada com sucesso",
            "data": {
                "id": 7890,
                "status_finalizacao": "entregue",
                "data_entrega_real": "2024-01-16T14:30:00Z"
            }
        }
    }
}

# ============================================================================
# CLIENTE (CLIENT) EXAMPLES
# ============================================================================

CLIENTE_EXAMPLES = {
    "consultar_cliente": {
        "request": {
            "url": "GET /api/v1/cliente/Supermercados%20União?uf=SP&limite=5",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "response": {
            "success": True,
            "cliente": "SUPERMERCADOS UNIÃO",
            "uf": "SP",
            "resumo": {
                "total_pedidos": 47,
                "valor_total": 856790.50,
                "pedidos_faturados": 35,
                "percentual_faturado": 74.5
            },
            "data": [
                {
                    "pedido": {
                        "numero": "PED-2024-0789",
                        "data": "15/01/2024",
                        "cliente": "Supermercados União",
                        "destino": "São Paulo/SP",
                        "valor": 25650.75,
                        "status": "faturado",
                        "nf": "NF-123456"
                    },
                    "faturamento": {
                        "data_fatura": "12/01/2024",
                        "valor_nf": 25650.75,
                        "saldo_carteira": 0.00,
                        "status_faturamento": "Completo"
                    },
                    "monitoramento": {
                        "status_entrega": "em_andamento",
                        "transportadora": "Express Logística S/A",
                        "pendencia_financeira": False,
                        "data_prevista": "16/01/2024"
                    }
                }
            ],
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "exportar_excel": {
        "request": {
            "url": "GET /api/v1/cliente/Carrefour/excel?uf=RJ&limite=20",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "response": {
            "description": "Returns Excel file for download",
            "headers": {
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": "attachment; filename=relatorio_Carrefour_20240115_1030.xlsx"
            }
        }
    }
}

# ============================================================================
# ESTATISTICAS (STATISTICS) EXAMPLES
# ============================================================================

ESTATISTICAS_EXAMPLES = {
    "system_stats": {
        "request": {
            "url": "GET /api/v1/estatisticas?periodo_dias=30",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "response": {
            "success": True,
            "periodo_analisado": "Últimos 30 dias",
            "embarques": {
                "total": 456,
                "ativos": 125,
                "cancelados": 12,
                "em_transito": 319
            },
            "fretes": {
                "total": 3847,
                "pendentes_aprovacao": 234,
                "aprovados": 3456,
                "rejeitados": 157,
                "percentual_aprovacao": 89.8
            },
            "entregas": {
                "total_monitoradas": 3215,
                "entregues": 2890,
                "pendencias_financeiras": 156,
                "percentual_entrega": 89.9,
                "tempo_medio_entrega": 3.5
            },
            "transportadoras": {
                "total": 78,
                "ativas": 65,
                "inativas": 13,
                "melhor_desempenho": "Express Logística S/A"
            },
            "metricas_adicionais": {
                "valor_total_fretes": 4567890.50,
                "ticket_medio": 1187.25,
                "rotas_mais_frequentes": ["SP-RJ", "SP-MG", "RJ-ES"]
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
}

# ============================================================================
# MCP (MODEL CONTEXT PROTOCOL) EXAMPLES
# ============================================================================

MCP_EXAMPLES = {
    "analyze_query": {
        "request": {
            "url": "POST /api/v1/mcp/analyze",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Content-Type": "application/json"
            },
            "body": {
                "query": "Show me all pending shipments for Carrefour in São Paulo",
                "context": {
                    "user_role": "manager",
                    "previous_query": None
                },
                "include_suggestions": True
            }
        },
        "response": {
            "success": True,
            "interpretation": "Searching for active shipments with pending status for client 'Carrefour' in São Paulo state",
            "suggested_actions": [
                "View detailed shipment list",
                "Export results to Excel",
                "Check payment status",
                "Contact transporters"
            ],
            "relevant_data": {
                "found_shipments": 5,
                "total_value": 45670.50,
                "average_delay": 1.5,
                "filters_applied": {
                    "client": "Carrefour",
                    "state": "SP",
                    "status": "pending"
                }
            },
            "confidence_score": 0.92,
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "process_command": {
        "request": {
            "url": "POST /api/v1/mcp/process",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Content-Type": "application/json"
            },
            "body": {
                "command": "approve_freight",
                "parameters": {
                    "freight_id": 5678,
                    "approved_value": 1200.00,
                    "notes": "Negotiated value"
                },
                "auto_execute": False
            }
        },
        "response": {
            "success": True,
            "command_type": "freight_approval",
            "executed": False,
            "result": None,
            "requires_confirmation": True,
            "safety_score": 0.95,
            "message": "Command ready for execution. Requires user confirmation.",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
}

# ============================================================================
# ERROR EXAMPLES
# ============================================================================

ERROR_EXAMPLES = {
    "validation_error": {
        "status_code": 422,
        "response": {
            "success": False,
            "error": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": [
                {
                    "field": "email",
                    "message": "Invalid email format",
                    "type": "email"
                },
                {
                    "field": "password",
                    "message": "Password must be at least 6 characters",
                    "type": "min_length"
                }
            ],
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "not_found": {
        "status_code": 404,
        "response": {
            "success": False,
            "error": "Resource not found",
            "error_code": "NOT_FOUND",
            "resource_type": "embarque",
            "resource_id": 9999,
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "unauthorized": {
        "status_code": 401,
        "response": {
            "success": False,
            "error": "Unauthorized",
            "error_code": "AUTH_REQUIRED",
            "details": {
                "reason": "Token expired",
                "expired_at": "2024-01-15T09:30:00Z"
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "forbidden": {
        "status_code": 403,
        "response": {
            "success": False,
            "error": "Forbidden",
            "error_code": "INSUFFICIENT_PERMISSIONS",
            "required_permissions": ["admin", "freight_approval"],
            "timestamp": "2024-01-15T10:30:00Z"
        }
    },
    "rate_limit": {
        "status_code": 429,
        "response": {
            "success": False,
            "error": "Too many requests",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "details": {
                "limit": 100,
                "window": "1 minute",
                "retry_after": 45
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
}

# ============================================================================
# POSTMAN COLLECTION GENERATOR
# ============================================================================

def generate_postman_collection() -> Dict[str, Any]:
    """Generate Postman collection from examples"""
    return {
        "info": {
            "name": "Frete Sistema API",
            "description": "Complete API collection for freight management system",
            "version": "1.0.0"
        },
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{access_token}}",
                    "type": "string"
                }
            ]
        },
        "variable": [
            {
                "key": "base_url",
                "value": "http://localhost:5000/api/v1",
                "type": "string"
            },
            {
                "key": "access_token",
                "value": "",
                "type": "string"
            }
        ],
        "item": [
            {
                "name": "Authentication",
                "item": [
                    {
                        "name": "Login",
                        "request": {
                            "method": "POST",
                            "header": [],
                            "body": {
                                "mode": "raw",
                                "raw": AUTH_EXAMPLES["login"]["request"]["body"]
                            },
                            "url": "{{base_url}}/auth/login"
                        }
                    }
                ]
            },
            {
                "name": "Embarques",
                "item": [
                    {
                        "name": "List Embarques",
                        "request": {
                            "method": "GET",
                            "url": "{{base_url}}/embarques?status=ativo&limit=10"
                        }
                    }
                ]
            }
        ]
    }