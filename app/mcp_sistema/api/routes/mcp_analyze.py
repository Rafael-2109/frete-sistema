"""
MCP Analyze endpoint - Analyze patterns in data and provide insights
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, date
import logging
from sqlalchemy.orm import Session

from ...models.database import get_db
from ...services.mcp.analyzer import DataAnalyzer
from ..dependencies import get_mcp_service

logger = logging.getLogger(__name__)
router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request model for data analysis"""
    analysis_type: Literal[
        "freight_trends",
        "order_patterns", 
        "delivery_performance",
        "cost_analysis",
        "customer_behavior",
        "transporter_performance",
        "anomaly_detection",
        "predictive",
        "custom"
    ] = Field(..., description="Type of analysis to perform")
    
    date_range: Optional[Dict[str, date]] = Field(
        None,
        description="Date range for analysis {'start': '2024-01-01', 'end': '2024-12-31'}"
    )
    
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Analysis-specific parameters"
    )
    
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filters to apply to data"
    )
    
    group_by: Optional[List[str]] = Field(
        None,
        description="Fields to group results by"
    )
    
    include_predictions: bool = Field(
        False,
        description="Include predictive analytics"
    )


class AnalysisResponse(BaseModel):
    """Response model for analysis results"""
    success: bool
    analysis_type: str
    summary: Dict[str, Any]
    insights: List[Dict[str, Any]]
    charts_data: Optional[List[Dict[str, Any]]]
    recommendations: Optional[List[str]]
    metadata: Dict[str, Any]


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_data(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> AnalysisResponse:
    """
    Perform intelligent analysis on freight and order data.
    
    Analysis types:
    - freight_trends: Analyze freight cost trends and patterns
    - order_patterns: Identify ordering patterns and seasonality
    - delivery_performance: Analyze delivery times and delays
    - cost_analysis: Deep dive into cost structure
    - customer_behavior: Customer ordering and payment patterns
    - transporter_performance: Evaluate transporter efficiency
    - anomaly_detection: Detect unusual patterns or outliers
    - predictive: Forecast future trends
    - custom: Custom analysis based on parameters
    """
    start_time = datetime.utcnow()
    
    try:
        # Initialize analyzer
        analyzer = DataAnalyzer(db, mcp_service)
        
        # Perform analysis
        result = await analyzer.analyze(
            analysis_type=request.analysis_type,
            date_range=request.date_range,
            parameters=request.parameters,
            filters=request.filters,
            group_by=request.group_by,
            include_predictions=request.include_predictions
        )
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return AnalysisResponse(
            success=True,
            analysis_type=request.analysis_type,
            summary=result.get("summary", {}),
            insights=result.get("insights", []),
            charts_data=result.get("charts_data"),
            recommendations=result.get("recommendations"),
            metadata={
                "processing_time": processing_time,
                "data_points_analyzed": result.get("data_points", 0),
                "confidence_score": result.get("confidence", 0.0),
                "timestamp": datetime.utcnow().isoformat(),
                "parameters": request.parameters or {}
            }
        )
        
    except ValueError as e:
        logger.warning(f"Invalid analysis request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error performing analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform analysis: {str(e)}"
        )


@router.get("/analyze/freight-cost-trends")
async def analyze_freight_cost_trends(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    group_by: str = Query("month", description="Grouping: day, week, month"),
    transporter_id: Optional[int] = Query(None, description="Filter by transporter"),
    uf_destino: Optional[str] = Query(None, description="Filter by destination state"),
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Quick endpoint for freight cost trend analysis
    """
    analyzer = DataAnalyzer(db, mcp_service)
    
    result = await analyzer.analyze_freight_trends(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
        filters={
            "transporter_id": transporter_id,
            "uf_destino": uf_destino
        }
    )
    
    return result


@router.get("/analyze/order-velocity")
async def analyze_order_velocity(
    customer_cnpj: Optional[str] = Query(None, description="Filter by customer"),
    product_code: Optional[str] = Query(None, description="Filter by product"),
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Analyze order velocity and patterns
    """
    analyzer = DataAnalyzer(db, mcp_service)
    
    result = await analyzer.analyze_order_velocity(
        customer_cnpj=customer_cnpj,
        product_code=product_code,
        days=days
    )
    
    return result


@router.post("/analyze/compare")
async def compare_periods(
    period1: Dict[str, date],
    period2: Dict[str, date],
    metrics: List[str] = Query(..., description="Metrics to compare"),
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Compare metrics between two periods
    """
    analyzer = DataAnalyzer(db, mcp_service)
    
    result = await analyzer.compare_periods(
        period1=period1,
        period2=period2,
        metrics=metrics
    )
    
    return result


@router.get("/analyze/anomalies")
async def detect_anomalies(
    metric: str = Query(..., description="Metric to analyze for anomalies"),
    sensitivity: float = Query(0.95, description="Sensitivity level (0-1)"),
    days: int = Query(90, description="Days of data to analyze"),
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Detect anomalies in specified metrics
    """
    analyzer = DataAnalyzer(db, mcp_service)
    
    result = await analyzer.detect_anomalies(
        metric=metric,
        sensitivity=sensitivity,
        days=days
    )
    
    return result


@router.get("/analyze/insights/recent")
async def get_recent_insights(
    limit: int = Query(10, description="Number of insights to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get recently generated insights
    """
    # TODO: Implement insight storage and retrieval
    return [
        {
            "id": 1,
            "category": "cost_optimization",
            "insight": "Freight costs increased 15% last month",
            "recommendation": "Consider negotiating rates with top 3 transporters",
            "impact": "high",
            "created_at": datetime.utcnow().isoformat()
        }
    ]