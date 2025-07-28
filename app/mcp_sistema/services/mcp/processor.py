"""
Intelligent processor for natural language queries
"""
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from app.fretes.models import Frete
from app.carteira.models import CarteiraPrincipal
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora

logger = logging.getLogger(__name__)


class IntelligentProcessor:
    """
    Process natural language queries and convert them to database operations
    """
    
    def __init__(self, db: Session, mcp_service: Any = None):
        self.db = db
        self.mcp_service = mcp_service
        
        # Query patterns and their handlers
        self.patterns = self._initialize_patterns()
        
        # Entity mappings
        self.entity_mappings = {
            "freight": ["frete", "fretes", "freight", "freights", "carga", "cargas"],
            "order": ["pedido", "pedidos", "order", "orders", "encomenda"],
            "transporter": ["transportadora", "transportadoras", "transporter", "carrier"],
            "customer": ["cliente", "clientes", "customer", "client"],
            "delivery": ["entrega", "entregas", "delivery", "deliveries"],
            "status": ["status", "situação", "estado", "condition"]
        }
    
    def _initialize_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """
        Initialize query patterns for natural language processing
        """
        return [
            # Status queries
            (re.compile(r"(show|list|find|get).*(pending|pendente|aguardando)", re.I), "pending_items"),
            (re.compile(r"(show|list|find|get).*(approved|aprovado|aprovados)", re.I), "approved_items"),
            (re.compile(r"(show|list|find|get).*(rejected|rejeitado|rejeitados)", re.I), "rejected_items"),
            
            # Time-based queries
            (re.compile(r"(today|hoje)", re.I), "today_filter"),
            (re.compile(r"(yesterday|ontem)", re.I), "yesterday_filter"),
            (re.compile(r"(this week|esta semana)", re.I), "this_week_filter"),
            (re.compile(r"(last|últimos?)\s+(\d+)\s+(days?|dias?)", re.I), "last_n_days"),
            (re.compile(r"(this month|este mês)", re.I), "this_month_filter"),
            (re.compile(r"(last month|mês passado)", re.I), "last_month_filter"),
            
            # Top/ranking queries
            (re.compile(r"top\s+(\d+)", re.I), "top_n"),
            (re.compile(r"(highest|maior|maiores)", re.I), "highest"),
            (re.compile(r"(lowest|menor|menores)", re.I), "lowest"),
            
            # Location queries
            (re.compile(r"(in|em|para)\s+([A-Za-zÀ-ú\s]+)(?:\s+state|\s+estado)?", re.I), "location_filter"),
            
            # Cost/value queries
            (re.compile(r"(cost|custo|valor|price|preço)\s*(above|acima|maior que)\s*(\d+)", re.I), "cost_above"),
            (re.compile(r"(cost|custo|valor|price|preço)\s*(below|abaixo|menor que)\s*(\d+)", re.I), "cost_below"),
            
            # Aggregation queries
            (re.compile(r"(total|sum|soma)", re.I), "sum_aggregation"),
            (re.compile(r"(average|avg|média)", re.I), "avg_aggregation"),
            (re.compile(r"(count|quantidade|qtd)", re.I), "count_aggregation"),
        ]
    
    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        format: str = "detailed",
        include_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Process a natural language query and return results
        """
        try:
            # Parse the query
            interpretation = self._interpret_query(query)
            
            # Determine the main entity
            entity_type = self._identify_entity(query)
            
            # Build the database query
            db_query = self._build_query(entity_type, interpretation, filters)
            
            # Execute and format results
            raw_results = self._execute_query(db_query, entity_type)
            
            # Format results based on requested format
            formatted_data = self._format_results(raw_results, entity_type, format)
            
            # Generate insights if requested
            insights = []
            if include_analysis and raw_results:
                insights = self._generate_insights(raw_results, entity_type, interpretation)
            
            return {
                "interpretation": interpretation,
                "data": formatted_data,
                "insights": insights,
                "entity_type": entity_type,
                "record_count": len(raw_results) if isinstance(raw_results, list) else 1
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise
    
    def _interpret_query(self, query: str) -> Dict[str, Any]:
        """
        Interpret the natural language query
        """
        interpretation = {
            "original_query": query,
            "filters": {},
            "aggregations": [],
            "sorting": None,
            "limit": None,
            "time_range": None
        }
        
        # Check each pattern
        for pattern, pattern_type in self.patterns:
            match = pattern.search(query)
            if match:
                if pattern_type == "pending_items":
                    interpretation["filters"]["status"] = "PENDENTE"
                
                elif pattern_type == "approved_items":
                    interpretation["filters"]["status"] = "APROVADO"
                
                elif pattern_type == "rejected_items":
                    interpretation["filters"]["status"] = "REJEITADO"
                
                elif pattern_type == "today_filter":
                    interpretation["time_range"] = {
                        "start": date.today(),
                        "end": date.today()
                    }
                
                elif pattern_type == "yesterday_filter":
                    yesterday = date.today() - timedelta(days=1)
                    interpretation["time_range"] = {
                        "start": yesterday,
                        "end": yesterday
                    }
                
                elif pattern_type == "this_week_filter":
                    today = date.today()
                    start_of_week = today - timedelta(days=today.weekday())
                    interpretation["time_range"] = {
                        "start": start_of_week,
                        "end": today
                    }
                
                elif pattern_type == "last_n_days":
                    days = int(match.group(2))
                    interpretation["time_range"] = {
                        "start": date.today() - timedelta(days=days),
                        "end": date.today()
                    }
                
                elif pattern_type == "top_n":
                    interpretation["limit"] = int(match.group(1))
                    interpretation["sorting"] = "desc"
                
                elif pattern_type == "location_filter":
                    location = match.group(2).strip()
                    interpretation["filters"]["location"] = location
                
                elif pattern_type == "cost_above":
                    value = float(match.group(3))
                    interpretation["filters"]["cost_min"] = value
                
                elif pattern_type == "cost_below":
                    value = float(match.group(3))
                    interpretation["filters"]["cost_max"] = value
                
                elif pattern_type in ["sum_aggregation", "avg_aggregation", "count_aggregation"]:
                    interpretation["aggregations"].append(pattern_type.replace("_aggregation", ""))
        
        return interpretation
    
    def _identify_entity(self, query: str) -> str:
        """
        Identify the main entity type from the query
        """
        query_lower = query.lower()
        
        for entity, keywords in self.entity_mappings.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return entity
        
        # Default to freight if no specific entity found
        return "freight"
    
    def _build_query(
        self,
        entity_type: str,
        interpretation: Dict[str, Any],
        additional_filters: Optional[Dict[str, Any]] = None
    ):
        """
        Build SQLAlchemy query based on entity type and interpretation
        """
        if entity_type == "freight":
            query = self.db.query(Frete)
            
            # Apply status filter
            if "status" in interpretation["filters"]:
                query = query.filter(Frete.status == interpretation["filters"]["status"])
            
            # Apply time range
            if interpretation["time_range"]:
                query = query.filter(
                    Frete.criado_em >= interpretation["time_range"]["start"],
                    Frete.criado_em <= interpretation["time_range"]["end"] + timedelta(days=1)
                )
            
            # Apply location filter
            if "location" in interpretation["filters"]:
                query = query.filter(
                    or_(
                        Frete.cidade_destino.ilike(f"%{interpretation['filters']['location']}%"),
                        Frete.uf_destino.ilike(f"%{interpretation['filters']['location']}%")
                    )
                )
            
            # Apply cost filters
            if "cost_min" in interpretation["filters"]:
                query = query.filter(Frete.valor_cotado >= interpretation["filters"]["cost_min"])
            
            if "cost_max" in interpretation["filters"]:
                query = query.filter(Frete.valor_cotado <= interpretation["filters"]["cost_max"])
            
            # Apply sorting
            if interpretation["sorting"] == "desc":
                query = query.order_by(desc(Frete.valor_cotado))
            
            # Apply limit
            if interpretation["limit"]:
                query = query.limit(interpretation["limit"])
        
        elif entity_type == "order":
            query = self.db.query(CarteiraPrincipal)
            
            # Apply filters for orders
            if interpretation["time_range"]:
                query = query.filter(
                    CarteiraPrincipal.data_pedido >= interpretation["time_range"]["start"],
                    CarteiraPrincipal.data_pedido <= interpretation["time_range"]["end"]
                )
            
            # Apply additional entity-specific filters
            # ...
        
        # Apply additional filters if provided
        if additional_filters:
            for key, value in additional_filters.items():
                if hasattr(query.column_descriptions[0]['type'], key):
                    query = query.filter(getattr(query.column_descriptions[0]['type'], key) == value)
        
        return query
    
    def _execute_query(self, query, entity_type: str) -> List[Any]:
        """
        Execute the query and return results
        """
        try:
            results = query.all()
            return results
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def _format_results(self, results: List[Any], entity_type: str, format: str) -> Any:
        """
        Format results based on requested format
        """
        if not results:
            return []
        
        if format == "summary":
            # Return summarized data
            if entity_type == "freight":
                return [{
                    "id": r.id,
                    "numero_cte": r.numero_cte,
                    "valor": r.valor_cotado,
                    "status": r.status,
                    "destino": f"{r.cidade_destino}/{r.uf_destino}"
                } for r in results]
        
        elif format == "detailed":
            # Return full details
            if entity_type == "freight":
                return [{
                    "id": r.id,
                    "embarque_id": r.embarque_id,
                    "cnpj_cliente": r.cnpj_cliente,
                    "nome_cliente": r.nome_cliente,
                    "transportadora_id": r.transportadora_id,
                    "tipo_carga": r.tipo_carga,
                    "modalidade": r.modalidade,
                    "destino": {
                        "uf": r.uf_destino,
                        "cidade": r.cidade_destino
                    },
                    "valores": {
                        "cotado": r.valor_cotado,
                        "cte": r.valor_cte,
                        "considerado": r.valor_considerado,
                        "pago": r.valor_pago
                    },
                    "cte": {
                        "numero": r.numero_cte,
                        "data_emissao": r.data_emissao_cte.isoformat() if r.data_emissao_cte else None,
                        "vencimento": r.vencimento.isoformat() if r.vencimento else None
                    },
                    "status": r.status,
                    "criado_em": r.criado_em.isoformat() if r.criado_em else None
                } for r in results]
        
        else:  # raw format
            return [r.__dict__ for r in results]
    
    def _generate_insights(
        self,
        results: List[Any],
        entity_type: str,
        interpretation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate insights from the results
        """
        insights = []
        
        if entity_type == "freight" and results:
            # Calculate basic statistics
            valores = [r.valor_cotado for r in results if r.valor_cotado]
            if valores:
                avg_value = sum(valores) / len(valores)
                max_value = max(valores)
                min_value = min(valores)
                
                insights.append({
                    "type": "statistics",
                    "title": "Value Statistics",
                    "content": f"Average freight value: R$ {avg_value:.2f}, "
                              f"Range: R$ {min_value:.2f} - R$ {max_value:.2f}",
                    "importance": "medium"
                })
            
            # Status distribution
            status_counts = {}
            for r in results:
                status_counts[r.status] = status_counts.get(r.status, 0) + 1
            
            if status_counts:
                insights.append({
                    "type": "distribution",
                    "title": "Status Distribution",
                    "content": status_counts,
                    "importance": "high" if status_counts.get("PENDENTE", 0) > len(results) * 0.5 else "medium"
                })
            
            # Destination analysis
            destination_counts = {}
            for r in results:
                dest = r.uf_destino
                destination_counts[dest] = destination_counts.get(dest, 0) + 1
            
            if destination_counts:
                top_destination = max(destination_counts.items(), key=lambda x: x[1])
                insights.append({
                    "type": "pattern",
                    "title": "Top Destination",
                    "content": f"Most frequent destination: {top_destination[0]} ({top_destination[1]} shipments)",
                    "importance": "low"
                })
        
        return insights
    
    async def get_query_suggestions(self, partial_query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get query suggestions based on partial input
        """
        suggestions = []
        
        # Common query templates
        templates = [
            "Show all pending freight orders",
            "List orders from last 7 days",
            "Find freight costs above 1000",
            "Show top 10 transporters by volume",
            "Analyze delivery performance this month",
            "Get orders with delivery issues",
            "Show freight to São Paulo",
            "List approved orders today",
            "Find delayed deliveries",
            "Show cost trends last 30 days"
        ]
        
        # Filter templates that match partial query
        partial_lower = partial_query.lower()
        for template in templates:
            if partial_lower in template.lower():
                suggestions.append({
                    "query": template,
                    "category": self._categorize_query(template),
                    "description": self._describe_query(template)
                })
        
        return suggestions[:limit]
    
    def _categorize_query(self, query: str) -> str:
        """
        Categorize a query for suggestions
        """
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["cost", "price", "valor", "freight"]):
            return "financial"
        elif any(word in query_lower for word in ["delivery", "entrega", "delayed"]):
            return "logistics"
        elif any(word in query_lower for word in ["analyze", "trend", "performance"]):
            return "analytics"
        else:
            return "general"
    
    def _describe_query(self, query: str) -> str:
        """
        Generate a description for a query suggestion
        """
        descriptions = {
            "Show all pending freight orders": "View freight orders awaiting approval or processing",
            "List orders from last 7 days": "Recent orders from the past week",
            "Find freight costs above 1000": "High-value freight shipments",
            "Show top 10 transporters by volume": "Most active transportation partners",
            "Analyze delivery performance this month": "Monthly delivery metrics and KPIs",
            "Get orders with delivery issues": "Orders with delays or problems",
            "Show freight to São Paulo": "Shipments destined for São Paulo",
            "List approved orders today": "Orders approved in the current day",
            "Find delayed deliveries": "Shipments past their expected delivery date",
            "Show cost trends last 30 days": "Freight cost analysis for the past month"
        }
        
        return descriptions.get(query, "Custom query")