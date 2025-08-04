"""
Claude 4 Sonnet Integration for MCP Logística
Provides fallback layer when NLP can't translate to SQL
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import anthropic
from flask import current_app
import hashlib

from .models import db, QueryHistory
from .nlp_engine import ProcessedQuery
from .intent_classifier import Intent

logger = logging.getLogger(__name__)

@dataclass
class ClaudeContext:
    """Context for Claude interactions"""
    user_id: str
    session_id: str
    previous_queries: List[Dict]
    user_preferences: Dict
    domain_context: str
    timestamp: datetime
    
@dataclass
class ClaudeResponse:
    """Response from Claude integration"""
    success: bool
    response_type: str  # 'direct', 'hybrid', 'insight'
    sql_query: Optional[str] = None
    direct_answer: Optional[str] = None
    insights: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    confidence: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ClaudeIntegration:
    """Integrates Claude 4 Sonnet for enhanced natural language understanding"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        if not self.api_key:
            try:
                self.api_key = current_app.config.get('ANTHROPIC_API_KEY')
            except:
                self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        
        self.client = None
        self.enabled = False
        
        if self.api_key:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.enabled = True
                logger.info("Claude integration initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude client: {str(e)}")
                self.enabled = False
        else:
            logger.info("Claude integration disabled - no API key provided")
            
        self.session_contexts = {}  # Store session contexts in memory
        self.max_context_queries = 10  # Maximum queries to keep in context
        
    def _get_session_context(self, user_id: str, session_id: str) -> ClaudeContext:
        """Retrieve or create session context"""
        context_key = f"{user_id}:{session_id}"
        
        if context_key not in self.session_contexts:
            # Initialize new context
            self.session_contexts[context_key] = ClaudeContext(
                user_id=user_id,
                session_id=session_id,
                previous_queries=[],
                user_preferences={},
                domain_context="logistics",
                timestamp=datetime.now()
            )
            
        return self.session_contexts[context_key]
        
    def _update_session_context(self, context: ClaudeContext, query: str, result: Any):
        """Update session context with new query"""
        query_entry = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'success': result.get('success', False) if isinstance(result, dict) else True,
            'intent': result.get('intent', 'unknown') if isinstance(result, dict) else 'unknown'
        }
        
        context.previous_queries.append(query_entry)
        
        # Keep only recent queries
        if len(context.previous_queries) > self.max_context_queries:
            context.previous_queries = context.previous_queries[-self.max_context_queries:]
            
    def _generate_claude_prompt(self, query: str, processed: ProcessedQuery, 
                               intent: Intent, context: ClaudeContext) -> str:
        """Generate optimized prompt for Claude"""
        
        # Build context from previous queries
        history_context = ""
        if context.previous_queries:
            recent_queries = context.previous_queries[-3:]  # Last 3 queries
            history_context = "\n".join([
                f"- {q['query']} (Intent: {q['intent']})"
                for q in recent_queries
            ])
            
        prompt = f"""You are an AI assistant for a logistics management system. Your role is to help users understand and query their logistics data.

Current Query: "{query}"

Detected Intent: {intent.primary}
Confidence: {intent.confidence}
Entities Found: {json.dumps(processed.entities, ensure_ascii=False)}

Previous Queries in Session:
{history_context if history_context else "None"}

Database Schema Context:
- entregas_monitoradas: Delivery tracking (cliente, numero_nf, data_entrega_prevista, status, valor_nf, uf)
- pedidos: Orders (num_pedido, raz_social_red, data_pedido, status)
- embarques: Shipments (data_embarque, transportadora, status)
- fretes: Freight (numero_cte, nome_cliente, valor_frete, data_emissao)

Task:
1. If the NLP system couldn't generate a proper SQL query (low confidence or missing entities), provide:
   - A direct answer based on the query intent
   - Suggestions for clarifying the query
   - Related insights if relevant

2. If a SQL query was generated but might benefit from additional context:
   - Provide insights about the data
   - Suggest related queries
   - Explain any patterns or anomalies

3. Always consider the session history to provide contextual responses.

Response Format:
- Keep responses concise and actionable
- Use bullet points for multiple items
- Include specific examples when suggesting queries
- Maintain professional tone suitable for logistics professionals

Query Analysis:
"""
        
        # Add specific context based on intent
        if intent.confidence < 0.6:
            prompt += f"\nThe intent classification has low confidence ({intent.confidence}). The user might be asking about: {intent.primary}"
            
        if not processed.entities:
            prompt += "\nNo specific entities were detected. The query seems to be general or exploratory."
            
        return prompt
        
    def process_with_fallback(self, query: str, processed_query: ProcessedQuery, 
                            intent: Intent, sql_result: Optional[Dict],
                            user_context: Dict) -> ClaudeResponse:
        """Process query with Claude as fallback or enhancement"""
        
        if not self.enabled or not self.client:
            logger.debug("Claude integration not enabled - returning empty response")
            # Return empty successful response to allow normal flow
            return ClaudeResponse(
                success=True,
                response_type='disabled',
                confidence=0.0,
                metadata={'reason': 'claude_disabled'}
            )
            
        try:
            # Get session context
            session_id = user_context.get('session_id', 'default')
            context = self._get_session_context(user_context['user_id'], session_id)
            context.user_preferences = user_context.get('preferences', {})
            
            # Determine if we need Claude's help
            needs_claude = (
                intent.confidence < 0.7 or  # Low confidence
                not processed_query.entities or  # No entities found
                (sql_result and sql_result.get('error')) or  # SQL error
                intent.primary in ['explicar', 'analisar', 'comparar']  # Complex intents
            )
            
            if not needs_claude and sql_result and sql_result.get('success'):
                # Just enhance the SQL results with insights
                return self._enhance_sql_results(query, sql_result, context)
                
            # Generate Claude prompt
            prompt = self._generate_claude_prompt(query, processed_query, intent, context)
            
            # Add SQL context if available
            if sql_result:
                if sql_result.get('error'):
                    prompt += f"\n\nSQL Error: {sql_result['error']}"
                elif sql_result.get('data'):
                    prompt += f"\n\nSQL Results Summary: {self._summarize_sql_results(sql_result['data'])}"
                    
            # Call Claude
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.2,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse Claude's response
            claude_text = message.content[0].text
            
            # Update session context
            self._update_session_context(context, query, {'success': True, 'intent': intent.primary})
            
            # Determine response type and structure
            if not sql_result or sql_result.get('error'):
                # Pure Claude response
                return ClaudeResponse(
                    success=True,
                    response_type='direct',
                    direct_answer=claude_text,
                    suggestions=self._extract_suggestions(claude_text),
                    confidence=0.8,
                    metadata={
                        'claude_model': 'claude-3-5-sonnet-20241022',
                        'fallback_reason': 'no_sql' if not sql_result else 'sql_error'
                    }
                )
            else:
                # Hybrid response - SQL + Claude insights
                return ClaudeResponse(
                    success=True,
                    response_type='hybrid',
                    sql_query=sql_result.get('sql'),
                    insights=[claude_text],
                    suggestions=self._extract_suggestions(claude_text),
                    confidence=0.9,
                    metadata={
                        'claude_model': 'claude-3-5-sonnet-20241022',
                        'enhancement_type': 'insights'
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in Claude integration: {str(e)}", exc_info=True)
            return ClaudeResponse(
                success=False,
                response_type='error',
                direct_answer=f"Error consulting Claude: {str(e)}",
                confidence=0.0
            )
            
    def _enhance_sql_results(self, query: str, sql_result: Dict, context: ClaudeContext) -> ClaudeResponse:
        """Enhance SQL results with Claude insights for high-confidence queries"""
        
        try:
            # Only enhance if there's meaningful data
            if not sql_result.get('data') or (isinstance(sql_result['data'], list) and len(sql_result['data']) == 0):
                return ClaudeResponse(
                    success=True,
                    response_type='sql_only',
                    sql_query=sql_result.get('sql'),
                    confidence=1.0
                )
                
            # Create a focused prompt for insights
            data_summary = self._summarize_sql_results(sql_result['data'])
            
            prompt = f"""Based on this logistics query and its results, provide brief business insights:

Query: "{query}"
Results: {data_summary}

Provide:
1. One key insight about the data
2. One actionable recommendation
3. One related question the user might want to explore

Keep response under 100 words."""
            
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            insights_text = message.content[0].text
            
            return ClaudeResponse(
                success=True,
                response_type='enhanced',
                sql_query=sql_result.get('sql'),
                insights=[insights_text],
                confidence=1.0,
                metadata={
                    'claude_model': 'claude-3-5-sonnet-20241022',
                    'enhancement_type': 'business_insights'
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to enhance SQL results: {str(e)}")
            # Return SQL results without enhancement
            return ClaudeResponse(
                success=True,
                response_type='sql_only',
                sql_query=sql_result.get('sql'),
                confidence=1.0
            )
            
    def _summarize_sql_results(self, data: Any) -> str:
        """Create a concise summary of SQL results for Claude context"""
        
        if isinstance(data, dict):
            if 'total' in data:
                return f"Total count: {data['total']}"
            elif 'items' in data:
                return f"Found {len(data['items'])} items"
            else:
                return f"Result contains {len(data)} fields"
                
        elif isinstance(data, list):
            if not data:
                return "No results found"
            
            sample = data[0] if len(data) > 0 else {}
            fields = list(sample.keys()) if isinstance(sample, dict) else []
            
            return f"Found {len(data)} records with fields: {', '.join(fields[:5])}"
            
        elif isinstance(data, (int, float)):
            return f"Numeric result: {data}"
            
        else:
            return f"Result type: {type(data).__name__}"
            
    def _extract_suggestions(self, claude_text: str) -> List[str]:
        """Extract actionable suggestions from Claude's response"""
        suggestions = []
        
        # Look for common suggestion patterns
        lines = claude_text.split('\n')
        for line in lines:
            line = line.strip()
            if any(marker in line.lower() for marker in ['try:', 'consider:', 'you could:', 'example:']):
                # Clean up the suggestion
                for marker in ['try:', 'consider:', 'you could:', 'example:', '-', '•', '*']:
                    line = line.replace(marker, '').replace(marker.upper(), '').strip()
                if line and len(line) > 10:
                    suggestions.append(line)
                    
        return suggestions[:3]  # Return top 3 suggestions
        
    def generate_natural_response(self, query_result: Dict, claude_response: ClaudeResponse) -> str:
        """Generate a natural language response combining SQL results and Claude insights"""
        
        response_parts = []
        
        # Add data summary if SQL was successful
        if query_result.get('success') and query_result.get('data'):
            data = query_result['data']
            
            if isinstance(data, dict) and 'total' in data:
                response_parts.append(f"Encontrei {data['total']} registros.")
            elif isinstance(data, list):
                response_parts.append(f"Encontrei {len(data)} resultados.")
                
        # Add Claude's direct answer or insights
        if claude_response.direct_answer:
            response_parts.append(claude_response.direct_answer)
        elif claude_response.insights:
            response_parts.extend(claude_response.insights)
            
        # Add suggestions if available
        if claude_response.suggestions:
            response_parts.append("\nSugestões:")
            for i, suggestion in enumerate(claude_response.suggestions, 1):
                response_parts.append(f"{i}. {suggestion}")
                
        return "\n\n".join(response_parts)
        
    def clear_session_context(self, user_id: str, session_id: str):
        """Clear session context for a user"""
        context_key = f"{user_id}:{session_id}"
        if context_key in self.session_contexts:
            del self.session_contexts[context_key]
            
    def get_session_summary(self, user_id: str, session_id: str) -> Dict:
        """Get summary of session interactions"""
        context = self._get_session_context(user_id, session_id)
        
        return {
            'session_id': session_id,
            'query_count': len(context.previous_queries),
            'session_start': context.timestamp.isoformat(),
            'recent_queries': context.previous_queries[-5:],
            'domains_accessed': list(set(q.get('intent', 'unknown') for q in context.previous_queries))
        }