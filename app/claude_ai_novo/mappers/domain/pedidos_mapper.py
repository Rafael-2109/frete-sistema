"""
Mapeador de domínio para pedidos.
Mapeia campos específicos do domínio de pedidos para consultas semânticas.
"""

from typing import Dict, List, Any
from .base_mapper import BaseMapper


class PedidosMapper(BaseMapper):
    """Mapeador específico para o domínio de pedidos."""
    
    def __init__(self):
        super().__init__("pedidos")
        self.domain = "pedidos"
    
    def _criar_mapeamentos(self) -> Dict[str, Dict[str, Any]]:
        """Configurar mapeamentos específicos de pedidos."""
        return {
            # Identificação
            "num_pedido": {
                "campo_principal": "num_pedido",
                "termos_naturais": ["número", "pedido", "numero pedido", "código pedido"],
                "tipo": "integer",
                "observacao": "Número único do pedido"
            },
            "cliente_id": {
                "campo_principal": "cliente_id", 
                "termos_naturais": ["cliente", "destinatário", "comprador"],
                "tipo": "integer",
                "observacao": "ID do cliente"
            },
            "vendedor_codigo": {
                "campo_principal": "vendedor_codigo",
                "termos_naturais": ["vendedor", "representante", "código vendedor"],
                "tipo": "string",
                "observacao": "Código do vendedor"
            },
            
            # Status e situação
            "status_calculado": {
                "campo_principal": "status_calculado",
                "termos_naturais": ["status", "situação", "estado pedido"],
                "tipo": "string",
                "observacao": "Status calculado do pedido"
            },
            "status_separacao": {
                "campo_principal": "status_separacao",
                "termos_naturais": ["separação", "picking", "status separação"],
                "tipo": "string",
                "observacao": "Status da separação"
            },
            "status_faturamento": {
                "campo_principal": "status_faturamento",
                "termos_naturais": ["faturamento", "nota fiscal", "NF"],
                "tipo": "string",
                "observacao": "Status do faturamento"
            },
            
            # Datas
            "data_pedido": {
                "campo_principal": "data_pedido",
                "termos_naturais": ["data", "quando", "período", "data pedido"],
                "tipo": "datetime",
                "observacao": "Data do pedido"
            },
            "data_prevista_entrega": {
                "campo_principal": "data_prevista_entrega",
                "termos_naturais": ["entrega", "prazo", "previsão"],
                "tipo": "datetime",
                "observacao": "Data prevista para entrega"
            },
            "data_separacao": {
                "campo_principal": "data_separacao",
                "termos_naturais": ["separado", "picking", "data separação"],
                "tipo": "datetime",
                "observacao": "Data da separação"
            },
            
            # Valores
            "valor_total": {
                "campo_principal": "valor_total",
                "termos_naturais": ["valor", "total", "preço", "montante"],
                "tipo": "decimal",
                "observacao": "Valor total do pedido"
            },
            "peso_total": {
                "campo_principal": "peso_total",
                "termos_naturais": ["peso", "quilos", "kg", "toneladas"],
                "tipo": "decimal",
                "observacao": "Peso total do pedido"
            },
            "volume_total": {
                "campo_principal": "volume_total",
                "termos_naturais": ["volume", "m3", "metros cúbicos"],
                "tipo": "decimal",
                "observacao": "Volume total do pedido"
            },
            
            # Localização
            "uf_destino": {
                "campo_principal": "uf_destino",
                "termos_naturais": ["estado", "UF", "destino", "localização"],
                "tipo": "string",
                "observacao": "Estado de destino"
            },
            "cidade_destino": {
                "campo_principal": "cidade_destino",
                "termos_naturais": ["cidade", "município", "local"],
                "tipo": "string",
                "observacao": "Cidade de destino"
            },
            
            # Observações
            "observacoes": {
                "campo_principal": "observacoes",
                "termos_naturais": ["observação", "comentário", "nota", "obs"],
                "tipo": "string",
                "observacao": "Observações do pedido"
            }
        }
    
    def map_query_to_filters(self, query: str) -> Dict[str, Any]:
        """
        Mapear consulta em linguagem natural para filtros de pedidos.
        
        Args:
            query: Consulta em linguagem natural
            
        Returns:
            Dict com filtros aplicáveis
        """
        filters = {}
        query_lower = query.lower()
        
        # Detectar cliente específico
        if "assai" in query_lower:
            filters["cliente_nome"] = "assai"
        elif "atacadão" in query_lower:
            filters["cliente_nome"] = "atacadão"
        elif "carrefour" in query_lower:
            filters["cliente_nome"] = "carrefour"
        
        # Detectar status
        if any(word in query_lower for word in ["pendente", "falta", "aguardando"]):
            filters["status_pendente"] = True
        elif any(word in query_lower for word in ["separado", "picking"]):
            filters["status_separacao"] = "separado"
        elif any(word in query_lower for word in ["faturado", "nota fiscal"]):
            filters["status_faturamento"] = "faturado"
        
        # Detectar período
        if "hoje" in query_lower:
            filters["periodo"] = "hoje"
        elif "ontem" in query_lower:
            filters["periodo"] = "ontem"
        elif "semana" in query_lower:
            filters["periodo"] = "semana"
        elif "mês" in query_lower or "mes" in query_lower:
            filters["periodo"] = "mes"
        
        # Detectar UF
        ufs = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        for uf in ufs:
            if uf.lower() in query_lower:
                filters["uf_destino"] = uf
                break
        
        return filters
    
    def get_semantic_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """
        Gerar sugestões semânticas baseadas no contexto.
        
        Args:
            context: Contexto da consulta
            
        Returns:
            Lista de sugestões
        """
        suggestions = []
        
        # Sugestões baseadas em cliente
        if "cliente" in context:
            suggestions.extend([
                f"Pedidos pendentes do {context['cliente']}",
                f"Histórico de pedidos {context['cliente']}",
                f"Valor total pedidos {context['cliente']}"
            ])
        
        # Sugestões baseadas em período
        if "periodo" in context:
            suggestions.extend([
                f"Pedidos {context['periodo']} por cliente",
                f"Análise de pedidos {context['periodo']}",
                f"Ranking clientes {context['periodo']}"
            ])
        
        # Sugestões gerais
        suggestions.extend([
            "Pedidos pendentes cotação",
            "Pedidos atrasados entrega",
            "Pedidos faturamento parcial",
            "Ranking clientes por volume",
            "Análise performance vendedores"
        ])
        
        return suggestions[:10]  # Limitar a 10 sugestões 