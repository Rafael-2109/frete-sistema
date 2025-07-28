"""
MCP Process endpoint - Handle natural language queries about freight/orders
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json
from sqlalchemy.orm import Session

from ...models.database import get_db
from ...services.mcp.processor import IntelligentProcessor
from ..dependencies import get_mcp_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ProcessRequest(BaseModel):
    """Request model for processing natural language queries"""
    query: str = Field(..., description="Natural language query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    include_analysis: bool = Field(True, description="Include AI analysis in response")
    format: Optional[str] = Field("detailed", description="Response format: summary, detailed, raw")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters")


class ProcessResponse(BaseModel):
    """Response model for processed queries"""
    success: bool
    query: str
    interpretation: Dict[str, Any]
    data: Any
    insights: Optional[List[Dict[str, Any]]]
    metadata: Dict[str, Any]
    processing_time: float


@router.post("/process", response_model=ProcessResponse)
async def process_query(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> ProcessResponse:
    """
    Process natural language queries about freight and orders.
    
    Examples:
    - "Show me all pending freight orders"
    - "What are the top transporters by volume this month?"
    - "Find orders with delivery issues in São Paulo"
    - "Analyze freight costs trend for the last 3 months"
    """
    start_time = datetime.utcnow()
    
    try:
        # Initialize processor
        processor = IntelligentProcessor(db, mcp_service)
        
        # Process the query
        result = await processor.process_query(
            query=request.query,
            context=request.context,
            filters=request.filters,
            format=request.format,
            include_analysis=request.include_analysis
        )
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log successful processing in background
        background_tasks.add_task(
            log_query_processing,
            query=request.query,
            success=True,
            processing_time=processing_time,
            db=db
        )
        
        return ProcessResponse(
            success=True,
            query=request.query,
            interpretation=result.get("interpretation", {}),
            data=result.get("data"),
            insights=result.get("insights"),
            metadata={
                "processing_time": processing_time,
                "record_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else 1,
                "format": request.format,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except ValueError as e:
        logger.warning(f"Invalid query: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        
        # Log failed processing in background
        background_tasks.add_task(
            log_query_processing,
            query=request.query,
            success=False,
            error=str(e),
            db=db
        )
        
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/process/batch")
async def process_batch_queries(
    queries: List[ProcessRequest],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    mcp_service: Any = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """
    Process multiple queries in batch for better performance
    """
    if len(queries) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 queries allowed per batch"
        )
    
    results = []
    processor = IntelligentProcessor(db, mcp_service)
    
    for query_request in queries:
        try:
            result = await processor.process_query(
                query=query_request.query,
                context=query_request.context,
                filters=query_request.filters,
                format=query_request.format,
                include_analysis=query_request.include_analysis
            )
            results.append({
                "query": query_request.query,
                "success": True,
                "result": result
            })
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            results.append({
                "query": query_request.query,
                "success": False,
                "error": str(e)
            })
    
    return {
        "total_queries": len(queries),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@router.get("/process/suggestions")
async def get_query_suggestions(
    partial_query: str,
    limit: int = 5,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get query suggestions based on partial input
    """
    processor = IntelligentProcessor(db, None)
    suggestions = await processor.get_query_suggestions(partial_query, limit)
    
    return suggestions


async def log_query_processing(
    query: str,
    success: bool,
    processing_time: float = None,
    error: str = None,
    db: Session = None
):
    """
    Log query processing for analytics and improvement
    """
    try:
        # TODO: Implement query logging to database
        logger.info(f"Query processed: {query}, Success: {success}, Time: {processing_time}s")
    except Exception as e:
        logger.error(f"Failed to log query processing: {e}")