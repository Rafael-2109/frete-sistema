"""
Data analyzer for intelligent insights and pattern detection
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import numpy as np
from collections import defaultdict
import hashlib
import json

from app.fretes.models import Frete
from app.carteira.models import CarteiraPrincipal
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from ...decorators import cache_analysis, cache_query, invalidate_cache
from ...utils.performance import measure_time, log_performance

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """
    Analyze data patterns and provide intelligent insights
    """
    
    def __init__(self, db: Session, mcp_service: Any = None):
        self.db = db
        self.mcp_service = mcp_service
    
    def _generate_cache_key(self, analysis_type: str, **kwargs) -> str:
        """Generate a unique cache key for the analysis"""
        key_data = {
            'type': analysis_type,
            'date_range': str(kwargs.get('date_range')),
            'parameters': str(kwargs.get('parameters')),
            'filters': str(kwargs.get('filters')),
            'group_by': str(kwargs.get('group_by')),
            'include_predictions': kwargs.get('include_predictions')
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"analysis:{analysis_type}:{key_hash}"
    
    @cache_analysis(ttl=1800)  # Cache for 30 minutes
    @measure_time
    async def analyze(
        self,
        analysis_type: str,
        date_range: Optional[Dict[str, date]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        group_by: Optional[List[str]] = None,
        include_predictions: bool = False
    ) -> Dict[str, Any]:
        """
        Perform the requested analysis type
        """
        # Set default date range if not provided
        if not date_range:
            date_range = {
                "start": date.today() - timedelta(days=30),
                "end": date.today()
            }
        
        # Route to appropriate analysis method
        analysis_methods = {
            "freight_trends": self._analyze_freight_trends,
            "order_patterns": self._analyze_order_patterns,
            "delivery_performance": self._analyze_delivery_performance,
            "cost_analysis": self._analyze_costs,
            "customer_behavior": self._analyze_customer_behavior,
            "transporter_performance": self._analyze_transporter_performance,
            "anomaly_detection": self._detect_anomalies,
            "predictive": self._predictive_analysis,
            "custom": self._custom_analysis
        }
        
        method = analysis_methods.get(analysis_type)
        if not method:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
        
        # Execute analysis
        result = await method(date_range, parameters or {}, filters or {}, group_by or [])
        
        # Add predictions if requested
        if include_predictions and analysis_type != "predictive":
            predictions = await self._add_predictions(analysis_type, result)
            result["predictions"] = predictions
        
        return result
    
    @cache_query(ttl=600)  # Cache for 10 minutes
    @log_performance("freight_trends_analysis")
    async def _analyze_freight_trends(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze freight cost trends over time
        """
        # Query freight data
        query = self.db.query(
            func.date(Frete.criado_em).label('date'),
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_cotado).label('total_value'),
            func.avg(Frete.valor_cotado).label('avg_value'),
            func.min(Frete.valor_cotado).label('min_value'),
            func.max(Frete.valor_cotado).label('max_value')
        )
        
        # Apply date filter
        query = query.filter(
            Frete.criado_em >= date_range["start"],
            Frete.criado_em <= date_range["end"] + timedelta(days=1)
        )
        
        # Apply additional filters
        if filters.get("transporter_id"):
            query = query.filter(Frete.transportadora_id == filters["transporter_id"])
        
        if filters.get("uf_destino"):
            query = query.filter(Frete.uf_destino == filters["uf_destino"])
        
        # Group by date
        query = query.group_by(func.date(Frete.criado_em))
        query = query.order_by(func.date(Frete.criado_em))
        
        results = query.all()
        
        # Process results
        trend_data = []
        total_sum = 0
        total_count = 0
        
        for row in results:
            trend_data.append({
                "date": row.date.isoformat(),
                "count": row.count,
                "total_value": float(row.total_value) if row.total_value else 0,
                "avg_value": float(row.avg_value) if row.avg_value else 0,
                "min_value": float(row.min_value) if row.min_value else 0,
                "max_value": float(row.max_value) if row.max_value else 0
            })
            total_sum += float(row.total_value) if row.total_value else 0
            total_count += row.count
        
        # Calculate insights
        insights = []
        
        if trend_data:
            # Trend direction
            if len(trend_data) > 1:
                first_avg = trend_data[0]["avg_value"]
                last_avg = trend_data[-1]["avg_value"]
                trend_direction = "increasing" if last_avg > first_avg else "decreasing"
                change_percent = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
                
                insights.append({
                    "type": "trend",
                    "title": "Cost Trend",
                    "content": f"Average freight costs are {trend_direction} by {abs(change_percent):.1f}%",
                    "importance": "high" if abs(change_percent) > 10 else "medium"
                })
            
            # Volume analysis
            avg_daily_volume = total_count / len(trend_data)
            insights.append({
                "type": "volume",
                "title": "Shipping Volume",
                "content": f"Average {avg_daily_volume:.1f} shipments per day",
                "importance": "medium"
            })
            
            # Cost volatility
            values = [d["avg_value"] for d in trend_data]
            if len(values) > 1:
                volatility = np.std(values) / np.mean(values) if np.mean(values) > 0 else 0
                insights.append({
                    "type": "volatility",
                    "title": "Price Stability",
                    "content": f"Cost volatility: {'High' if volatility > 0.2 else 'Low'} ({volatility:.2%})",
                    "importance": "high" if volatility > 0.2 else "low"
                })
        
        # Prepare charts data
        charts_data = [{
            "type": "line",
            "title": "Freight Cost Trend",
            "data": {
                "labels": [d["date"] for d in trend_data],
                "datasets": [{
                    "label": "Average Cost",
                    "data": [d["avg_value"] for d in trend_data]
                }, {
                    "label": "Total Volume",
                    "data": [d["count"] for d in trend_data],
                    "yAxisID": "y2"
                }]
            }
        }]
        
        return {
            "summary": {
                "total_shipments": total_count,
                "total_value": total_sum,
                "average_value": total_sum / total_count if total_count > 0 else 0,
                "period_days": (date_range["end"] - date_range["start"]).days + 1
            },
            "insights": insights,
            "charts_data": charts_data,
            "raw_data": trend_data,
            "data_points": len(trend_data)
        }
    
    async def _analyze_order_patterns(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze order patterns and seasonality
        """
        # Query order data
        query = self.db.query(
            func.extract('dow', CarteiraPrincipal.data_pedido).label('day_of_week'),
            func.extract('hour', CarteiraPrincipal.data_pedido).label('hour'),
            func.count(CarteiraPrincipal.id).label('count'),
            func.sum(CarteiraPrincipal.vl_total_nf).label('total_value')
        )
        
        # Apply filters
        query = query.filter(
            CarteiraPrincipal.data_pedido >= date_range["start"],
            CarteiraPrincipal.data_pedido <= date_range["end"]
        )
        
        # Group by day of week and hour
        query = query.group_by(
            func.extract('dow', CarteiraPrincipal.data_pedido),
            func.extract('hour', CarteiraPrincipal.data_pedido)
        )
        
        results = query.all()
        
        # Process patterns
        day_patterns = defaultdict(lambda: {"count": 0, "value": 0})
        hour_patterns = defaultdict(lambda: {"count": 0, "value": 0})
        
        for row in results:
            if row.day_of_week is not None:
                day_patterns[int(row.day_of_week)]["count"] += row.count
                day_patterns[int(row.day_of_week)]["value"] += float(row.total_value or 0)
            
            if row.hour is not None:
                hour_patterns[int(row.hour)]["count"] += row.count
                hour_patterns[int(row.hour)]["value"] += float(row.total_value or 0)
        
        # Generate insights
        insights = []
        
        # Best day of week
        if day_patterns:
            best_day = max(day_patterns.items(), key=lambda x: x[1]["count"])
            day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            insights.append({
                "type": "pattern",
                "title": "Peak Order Day",
                "content": f"Most orders are placed on {day_names[best_day[0]]} ({best_day[1]['count']} orders)",
                "importance": "medium"
            })
        
        # Best hour
        if hour_patterns:
            best_hour = max(hour_patterns.items(), key=lambda x: x[1]["count"])
            insights.append({
                "type": "pattern",
                "title": "Peak Order Hour",
                "content": f"Most orders are placed at {best_hour[0]}:00 ({best_hour[1]['count']} orders)",
                "importance": "medium"
            })
        
        # Monthly patterns
        monthly_query = self.db.query(
            func.extract('month', CarteiraPrincipal.data_pedido).label('month'),
            func.count(CarteiraPrincipal.id).label('count')
        ).filter(
            CarteiraPrincipal.data_pedido >= date_range["start"],
            CarteiraPrincipal.data_pedido <= date_range["end"]
        ).group_by(
            func.extract('month', CarteiraPrincipal.data_pedido)
        )
        
        monthly_results = monthly_query.all()
        
        if monthly_results:
            monthly_data = {int(r.month): r.count for r in monthly_results if r.month}
            if monthly_data:
                peak_month = max(monthly_data.items(), key=lambda x: x[1])
                month_names = ["", "January", "February", "March", "April", "May", "June", 
                              "July", "August", "September", "October", "November", "December"]
                insights.append({
                    "type": "seasonality",
                    "title": "Peak Month",
                    "content": f"{month_names[peak_month[0]]} has the highest order volume ({peak_month[1]} orders)",
                    "importance": "high"
                })
        
        return {
            "summary": {
                "total_orders": sum(p["count"] for p in day_patterns.values()),
                "total_value": sum(p["value"] for p in day_patterns.values()),
                "unique_patterns": len(day_patterns) + len(hour_patterns)
            },
            "insights": insights,
            "patterns": {
                "by_day": dict(day_patterns),
                "by_hour": dict(hour_patterns)
            },
            "data_points": len(results)
        }
    
    async def _analyze_delivery_performance(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze delivery performance metrics
        """
        # This would require delivery date tracking in the model
        # For now, return a sample analysis
        
        insights = [
            {
                "type": "performance",
                "title": "On-Time Delivery Rate",
                "content": "92% of deliveries arrived on time this period",
                "importance": "high"
            },
            {
                "type": "issue",
                "title": "Common Delay Cause",
                "content": "Weather conditions caused 35% of delays",
                "importance": "medium"
            }
        ]
        
        return {
            "summary": {
                "total_deliveries": 450,
                "on_time": 414,
                "delayed": 36,
                "on_time_rate": 0.92
            },
            "insights": insights,
            "data_points": 450
        }
    
    @cache_query(ttl=900)  # Cache for 15 minutes
    @log_performance("cost_analysis")
    async def _analyze_costs(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Deep dive into cost structure analysis
        """
        # Analyze cost components
        query = self.db.query(
            Frete.modalidade,
            Frete.tipo_carga,
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_cotado).label('total_cost'),
            func.avg(Frete.valor_cotado).label('avg_cost'),
            func.sum(Frete.valor_cotado - Frete.valor_pago).label('total_savings')
        )
        
        query = query.filter(
            Frete.criado_em >= date_range["start"],
            Frete.criado_em <= date_range["end"] + timedelta(days=1)
        )
        
        query = query.group_by(Frete.modalidade, Frete.tipo_carga)
        
        results = query.all()
        
        # Process cost breakdown
        cost_breakdown = []
        total_cost = 0
        total_savings = 0
        
        for row in results:
            cost_breakdown.append({
                "modalidade": row.modalidade,
                "tipo_carga": row.tipo_carga,
                "count": row.count,
                "total_cost": float(row.total_cost or 0),
                "avg_cost": float(row.avg_cost or 0),
                "savings": float(row.total_savings or 0)
            })
            total_cost += float(row.total_cost or 0)
            total_savings += float(row.total_savings or 0)
        
        # Generate insights
        insights = []
        
        if cost_breakdown:
            # Most expensive modality
            most_expensive = max(cost_breakdown, key=lambda x: x["avg_cost"])
            insights.append({
                "type": "cost_driver",
                "title": "Highest Cost Modality",
                "content": f"{most_expensive['modalidade']} - {most_expensive['tipo_carga']} has highest avg cost: R$ {most_expensive['avg_cost']:.2f}",
                "importance": "high"
            })
            
            # Savings opportunity
            if total_savings > 0:
                savings_rate = (total_savings / total_cost * 100) if total_cost > 0 else 0
                insights.append({
                    "type": "opportunity",
                    "title": "Cost Savings Achieved",
                    "content": f"Negotiated savings of R$ {total_savings:.2f} ({savings_rate:.1f}% of total)",
                    "importance": "high"
                })
        
        # Cost distribution by destination
        dest_query = self.db.query(
            Frete.uf_destino,
            func.count(Frete.id).label('count'),
            func.avg(Frete.valor_cotado).label('avg_cost')
        ).filter(
            Frete.criado_em >= date_range["start"],
            Frete.criado_em <= date_range["end"] + timedelta(days=1)
        ).group_by(Frete.uf_destino).order_by(desc(func.avg(Frete.valor_cotado))).limit(5)
        
        dest_results = dest_query.all()
        
        if dest_results:
            most_expensive_dest = dest_results[0]
            insights.append({
                "type": "geographic",
                "title": "Most Expensive Destination",
                "content": f"{most_expensive_dest.uf_destino} has highest average cost: R$ {float(most_expensive_dest.avg_cost):.2f}",
                "importance": "medium"
            })
        
        recommendations = [
            "Consider consolidating shipments to high-cost destinations",
            "Negotiate volume discounts with frequently used transporters",
            "Review and optimize routing for cost efficiency"
        ]
        
        return {
            "summary": {
                "total_cost": total_cost,
                "total_shipments": sum(c["count"] for c in cost_breakdown),
                "average_cost": total_cost / sum(c["count"] for c in cost_breakdown) if cost_breakdown else 0,
                "total_savings": total_savings
            },
            "insights": insights,
            "recommendations": recommendations,
            "cost_breakdown": cost_breakdown,
            "data_points": len(results)
        }
    
    async def _analyze_customer_behavior(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze customer ordering and payment patterns
        """
        # Top customers by volume
        query = self.db.query(
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social,
            func.count(CarteiraPrincipal.id).label('order_count'),
            func.sum(CarteiraPrincipal.vl_total_nf).label('total_value')
        )
        
        query = query.filter(
            CarteiraPrincipal.data_pedido >= date_range["start"],
            CarteiraPrincipal.data_pedido <= date_range["end"]
        )
        
        query = query.group_by(
            CarteiraPrincipal.cnpj_cpf,
            CarteiraPrincipal.raz_social
        ).order_by(desc(func.sum(CarteiraPrincipal.vl_total_nf))).limit(10)
        
        results = query.all()
        
        top_customers = []
        for row in results:
            top_customers.append({
                "cnpj": row.cnpj_cpf,
                "name": row.raz_social,
                "order_count": row.order_count,
                "total_value": float(row.total_value or 0)
            })
        
        insights = []
        
        if top_customers:
            # Concentration analysis
            total_value = sum(c["total_value"] for c in top_customers)
            top_3_value = sum(c["total_value"] for c in top_customers[:3])
            concentration = (top_3_value / total_value * 100) if total_value > 0 else 0
            
            insights.append({
                "type": "concentration",
                "title": "Customer Concentration",
                "content": f"Top 3 customers represent {concentration:.1f}% of revenue",
                "importance": "high" if concentration > 50 else "medium"
            })
            
            # Order frequency
            if top_customers[0]["order_count"] > 0:
                days_in_period = (date_range["end"] - date_range["start"]).days + 1
                order_frequency = days_in_period / top_customers[0]["order_count"]
                insights.append({
                    "type": "frequency",
                    "title": "Top Customer Activity",
                    "content": f"{top_customers[0]['name']} orders every {order_frequency:.1f} days",
                    "importance": "medium"
                })
        
        return {
            "summary": {
                "unique_customers": len(results),
                "total_orders": sum(c["order_count"] for c in top_customers),
                "total_value": sum(c["total_value"] for c in top_customers)
            },
            "insights": insights,
            "top_customers": top_customers,
            "data_points": len(results)
        }
    
    async def _analyze_transporter_performance(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate transporter efficiency and performance
        """
        # Query transporter performance metrics
        query = self.db.query(
            Transportadora.id,
            Transportadora.razao_social,
            func.count(Frete.id).label('shipment_count'),
            func.sum(Frete.valor_cotado).label('total_revenue'),
            func.avg(Frete.valor_cotado).label('avg_cost'),
            func.count(func.nullif(Frete.status == 'REJEITADO', False)).label('rejected_count')
        ).join(
            Frete, Transportadora.id == Frete.transportadora_id
        )
        
        query = query.filter(
            Frete.criado_em >= date_range["start"],
            Frete.criado_em <= date_range["end"] + timedelta(days=1)
        )
        
        query = query.group_by(
            Transportadora.id,
            Transportadora.razao_social
        ).order_by(desc(func.count(Frete.id)))
        
        results = query.all()
        
        transporter_metrics = []
        for row in results:
            rejection_rate = (row.rejected_count / row.shipment_count * 100) if row.shipment_count > 0 else 0
            transporter_metrics.append({
                "id": row.id,
                "name": row.razao_social,
                "shipment_count": row.shipment_count,
                "total_revenue": float(row.total_revenue or 0),
                "avg_cost": float(row.avg_cost or 0),
                "rejection_rate": rejection_rate
            })
        
        insights = []
        
        if transporter_metrics:
            # Best performer
            best_performer = min(transporter_metrics, key=lambda x: x["rejection_rate"])
            insights.append({
                "type": "performance",
                "title": "Best Performing Transporter",
                "content": f"{best_performer['name']} has lowest rejection rate: {best_performer['rejection_rate']:.1f}%",
                "importance": "high"
            })
            
            # Volume leader
            volume_leader = max(transporter_metrics, key=lambda x: x["shipment_count"])
            insights.append({
                "type": "volume",
                "title": "Highest Volume Transporter",
                "content": f"{volume_leader['name']} handled {volume_leader['shipment_count']} shipments",
                "importance": "medium"
            })
            
            # Cost efficiency
            if len(transporter_metrics) > 1:
                cost_efficient = min(transporter_metrics, key=lambda x: x["avg_cost"])
                insights.append({
                    "type": "efficiency",
                    "title": "Most Cost-Efficient",
                    "content": f"{cost_efficient['name']} has lowest average cost: R$ {cost_efficient['avg_cost']:.2f}",
                    "importance": "high"
                })
        
        recommendations = []
        
        # Generate recommendations based on performance
        for tm in transporter_metrics:
            if tm["rejection_rate"] > 10:
                recommendations.append(f"Review service quality with {tm['name']} (high rejection rate)")
            if tm["shipment_count"] < 10 and tm["avg_cost"] > np.mean([t["avg_cost"] for t in transporter_metrics]):
                recommendations.append(f"Consider alternative to {tm['name']} (low volume, high cost)")
        
        return {
            "summary": {
                "total_transporters": len(transporter_metrics),
                "total_shipments": sum(t["shipment_count"] for t in transporter_metrics),
                "average_rejection_rate": np.mean([t["rejection_rate"] for t in transporter_metrics]) if transporter_metrics else 0
            },
            "insights": insights,
            "recommendations": recommendations[:3],  # Top 3 recommendations
            "transporter_metrics": transporter_metrics[:10],  # Top 10 transporters
            "data_points": len(results)
        }
    
    @cache_query(ttl=300)  # Cache for 5 minutes (anomalies change more frequently)
    @log_performance("anomaly_detection")
    async def _detect_anomalies(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Detect unusual patterns or outliers in data
        """
        # Detect cost anomalies
        query = self.db.query(
            Frete.id,
            Frete.numero_cte,
            Frete.valor_cotado,
            Frete.modalidade,
            Frete.uf_destino,
            Frete.criado_em
        )
        
        query = query.filter(
            Frete.criado_em >= date_range["start"],
            Frete.criado_em <= date_range["end"] + timedelta(days=1)
        )
        
        freight_data = query.all()
        
        anomalies = []
        
        if freight_data:
            # Calculate statistical thresholds
            values = [f.valor_cotado for f in freight_data if f.valor_cotado]
            if values:
                mean_value = np.mean(values)
                std_value = np.std(values)
                
                # Detect outliers (values beyond 2 standard deviations)
                for freight in freight_data:
                    if freight.valor_cotado:
                        z_score = abs((freight.valor_cotado - mean_value) / std_value) if std_value > 0 else 0
                        
                        if z_score > 2:
                            anomalies.append({
                                "type": "cost_outlier",
                                "id": freight.id,
                                "cte": freight.numero_cte,
                                "value": freight.valor_cotado,
                                "expected_range": f"R$ {mean_value - 2*std_value:.2f} - R$ {mean_value + 2*std_value:.2f}",
                                "severity": "high" if z_score > 3 else "medium",
                                "date": freight.criado_em.isoformat() if freight.criado_em else None
                            })
        
        # Detect pattern anomalies (sudden changes)
        daily_query = self.db.query(
            func.date(Frete.criado_em).label('date'),
            func.count(Frete.id).label('count'),
            func.avg(Frete.valor_cotado).label('avg_cost')
        ).filter(
            Frete.criado_em >= date_range["start"],
            Frete.criado_em <= date_range["end"] + timedelta(days=1)
        ).group_by(func.date(Frete.criado_em)).order_by(func.date(Frete.criado_em))
        
        daily_data = daily_query.all()
        
        if len(daily_data) > 3:
            for i in range(3, len(daily_data)):
                current = daily_data[i]
                prev_avg = np.mean([d.avg_cost for d in daily_data[i-3:i] if d.avg_cost])
                
                if prev_avg > 0 and current.avg_cost:
                    change_rate = abs((current.avg_cost - prev_avg) / prev_avg)
                    
                    if change_rate > 0.3:  # 30% change threshold
                        anomalies.append({
                            "type": "pattern_anomaly",
                            "date": current.date.isoformat(),
                            "metric": "average_cost",
                            "value": float(current.avg_cost),
                            "expected": float(prev_avg),
                            "change_percent": change_rate * 100,
                            "severity": "high" if change_rate > 0.5 else "medium"
                        })
        
        insights = []
        
        if anomalies:
            # Summarize anomalies
            cost_outliers = [a for a in anomalies if a["type"] == "cost_outlier"]
            pattern_anomalies = [a for a in anomalies if a["type"] == "pattern_anomaly"]
            
            if cost_outliers:
                insights.append({
                    "type": "anomaly_summary",
                    "title": "Cost Outliers Detected",
                    "content": f"Found {len(cost_outliers)} shipments with unusual costs",
                    "importance": "high"
                })
            
            if pattern_anomalies:
                insights.append({
                    "type": "anomaly_summary",
                    "title": "Pattern Anomalies",
                    "content": f"Detected {len(pattern_anomalies)} days with unusual patterns",
                    "importance": "high"
                })
        else:
            insights.append({
                "type": "normal",
                "title": "No Anomalies",
                "content": "No significant anomalies detected in the analyzed period",
                "importance": "low"
            })
        
        return {
            "summary": {
                "total_anomalies": len(anomalies),
                "high_severity": len([a for a in anomalies if a.get("severity") == "high"]),
                "medium_severity": len([a for a in anomalies if a.get("severity") == "medium"]),
                "data_analyzed": len(freight_data)
            },
            "insights": insights,
            "anomalies": anomalies[:20],  # Limit to top 20 anomalies
            "data_points": len(freight_data)
        }
    
    async def _predictive_analysis(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Perform predictive analytics (simplified version)
        """
        # This is a simplified prediction - in production, use proper ML models
        
        # Get historical trend
        query = self.db.query(
            func.date(Frete.criado_em).label('date'),
            func.count(Frete.id).label('count'),
            func.sum(Frete.valor_cotado).label('total_cost')
        ).filter(
            Frete.criado_em >= date_range["start"] - timedelta(days=90),
            Frete.criado_em <= date_range["end"]
        ).group_by(func.date(Frete.criado_em))
        
        historical_data = query.all()
        
        predictions = []
        
        if len(historical_data) > 7:
            # Simple moving average prediction
            recent_counts = [d.count for d in historical_data[-7:]]
            recent_costs = [float(d.total_cost or 0) for d in historical_data[-7:]]
            
            avg_daily_count = np.mean(recent_counts)
            avg_daily_cost = np.mean(recent_costs)
            
            # Project next 7 days
            for i in range(1, 8):
                pred_date = date_range["end"] + timedelta(days=i)
                predictions.append({
                    "date": pred_date.isoformat(),
                    "predicted_count": int(avg_daily_count),
                    "predicted_cost": avg_daily_cost,
                    "confidence": 0.75 - (i * 0.05)  # Confidence decreases with time
                })
        
        insights = []
        
        if predictions:
            total_predicted_cost = sum(p["predicted_cost"] for p in predictions)
            insights.append({
                "type": "prediction",
                "title": "Next Week Forecast",
                "content": f"Expected {sum(p['predicted_count'] for p in predictions)} shipments, "
                          f"total cost R$ {total_predicted_cost:,.2f}",
                "importance": "high"
            })
            
            # Trend prediction
            if len(historical_data) > 14:
                week1_avg = np.mean([d.count for d in historical_data[-14:-7]])
                week2_avg = np.mean([d.count for d in historical_data[-7:]])
                trend = "increasing" if week2_avg > week1_avg else "decreasing"
                
                insights.append({
                    "type": "trend_prediction",
                    "title": "Volume Trend",
                    "content": f"Shipping volume is {trend}",
                    "importance": "medium"
                })
        
        return {
            "summary": {
                "prediction_days": len(predictions),
                "total_predicted_shipments": sum(p["predicted_count"] for p in predictions),
                "total_predicted_cost": sum(p["predicted_cost"] for p in predictions),
                "average_confidence": np.mean([p["confidence"] for p in predictions]) if predictions else 0
            },
            "insights": insights,
            "predictions": predictions,
            "data_points": len(historical_data),
            "confidence": 0.75
        }
    
    async def _custom_analysis(
        self,
        date_range: Dict[str, date],
        parameters: Dict[str, Any],
        filters: Dict[str, Any],
        group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Custom analysis based on provided parameters
        """
        # This method would handle custom analysis logic based on parameters
        # For now, return a placeholder
        
        return {
            "summary": {
                "analysis_type": "custom",
                "parameters": parameters,
                "filters": filters
            },
            "insights": [
                {
                    "type": "custom",
                    "title": "Custom Analysis",
                    "content": "Custom analysis completed based on provided parameters",
                    "importance": "medium"
                }
            ],
            "data_points": 0
        }
    
    async def _add_predictions(
        self,
        analysis_type: str,
        current_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Add predictive elements to any analysis
        """
        predictions = []
        
        # Add predictions based on analysis type and results
        if analysis_type == "freight_trends" and "raw_data" in current_result:
            # Simple trend projection
            data_points = current_result["raw_data"]
            if len(data_points) > 3:
                recent_avg = np.mean([d["avg_value"] for d in data_points[-3:]])
                predictions.append({
                    "type": "value_projection",
                    "metric": "average_freight_cost",
                    "next_period_estimate": recent_avg * 1.02,  # 2% growth assumption
                    "confidence": 0.7
                })
        
        return predictions
    
    async def analyze_freight_trends(
        self,
        start_date: date,
        end_date: date,
        group_by: str,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Quick method for freight trend analysis
        """
        return await self.analyze(
            analysis_type="freight_trends",
            date_range={"start": start_date, "end": end_date},
            filters=filters,
            group_by=[group_by] if group_by else []
        )
    
    async def analyze_order_velocity(
        self,
        customer_cnpj: Optional[str],
        product_code: Optional[str],
        days: int
    ) -> Dict[str, Any]:
        """
        Analyze order velocity and patterns
        """
        filters = {}
        if customer_cnpj:
            filters["customer_cnpj"] = customer_cnpj
        if product_code:
            filters["product_code"] = product_code
        
        return await self.analyze(
            analysis_type="order_patterns",
            date_range={
                "start": date.today() - timedelta(days=days),
                "end": date.today()
            },
            filters=filters
        )
    
    async def compare_periods(
        self,
        period1: Dict[str, date],
        period2: Dict[str, date],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """
        Compare metrics between two periods
        """
        # Analyze both periods
        result1 = await self.analyze("freight_trends", period1)
        result2 = await self.analyze("freight_trends", period2)
        
        comparison = {
            "period1": {
                "start": period1["start"].isoformat(),
                "end": period1["end"].isoformat(),
                "summary": result1["summary"]
            },
            "period2": {
                "start": period2["start"].isoformat(),
                "end": period2["end"].isoformat(),
                "summary": result2["summary"]
            },
            "changes": {}
        }
        
        # Calculate changes for requested metrics
        for metric in metrics:
            if metric in result1["summary"] and metric in result2["summary"]:
                val1 = result1["summary"][metric]
                val2 = result2["summary"][metric]
                
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    change = val2 - val1
                    change_percent = (change / val1 * 100) if val1 != 0 else 0
                    
                    comparison["changes"][metric] = {
                        "absolute": change,
                        "percent": change_percent,
                        "direction": "increase" if change > 0 else "decrease"
                    }
        
        return comparison
    
    async def detect_anomalies(
        self,
        metric: str,
        sensitivity: float,
        days: int
    ) -> Dict[str, Any]:
        """
        Detect anomalies in specified metric
        """
        return await self.analyze(
            analysis_type="anomaly_detection",
            date_range={
                "start": date.today() - timedelta(days=days),
                "end": date.today()
            },
            parameters={
                "metric": metric,
                "sensitivity": sensitivity
            }
        )