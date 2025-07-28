# Natural Response Generator for Freight System
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re
from dataclasses import dataclass
from .neural_processor import ProcessingResult

@dataclass
class GeneratedResponse:
    """Generated natural language response"""
    text: str
    format_type: str  # plain, markdown, json
    metadata: Dict[str, Any]
    suggestions: List[str]

class ResponseGenerator:
    """Generates natural, context-aware responses for the freight system"""
    
    def __init__(self):
        self.response_variations = self._load_response_variations()
        self.context_enhancers = self._load_context_enhancers()
        self.language = 'pt-BR'  # Default to Brazilian Portuguese
        
    def _load_response_variations(self) -> Dict[str, Dict[str, List[str]]]:
        """Load response variations for different contexts"""
        return {
            'greeting': {
                'morning': [
                    "Bom dia! Como posso ajudá-lo com seus fretes hoje?",
                    "Olá, bom dia! Em que posso ser útil?",
                    "Bom dia! Pronto para gerenciar seus fretes?"
                ],
                'afternoon': [
                    "Boa tarde! Como posso auxiliar com seus pedidos?",
                    "Olá, boa tarde! O que você precisa hoje?",
                    "Boa tarde! Em que posso ajudá-lo?"
                ],
                'evening': [
                    "Boa noite! Como posso ajudar com seus fretes?",
                    "Olá, boa noite! Precisa de alguma informação?",
                    "Boa noite! O que você gostaria de verificar?"
                ]
            },
            'success': {
                'create': [
                    "✅ {item} criado com sucesso!",
                    "🎉 Pronto! {item} foi registrado.",
                    "✓ {item} adicionado ao sistema com sucesso."
                ],
                'update': [
                    "✅ {item} atualizado com sucesso!",
                    "✓ As alterações em {item} foram salvas.",
                    "🔄 {item} foi modificado conforme solicitado."
                ],
                'delete': [
                    "✅ {item} removido com sucesso.",
                    "✓ {item} foi excluído do sistema.",
                    "🗑️ {item} deletado conforme solicitado."
                ]
            },
            'error': {
                'not_found': [
                    "❌ Não foi possível encontrar {item}.",
                    "⚠️ {item} não existe em nossos registros.",
                    "🔍 Não localizei {item}. Verifique os dados informados."
                ],
                'validation': [
                    "⚠️ Os dados fornecidos são inválidos: {reason}",
                    "❌ Erro de validação: {reason}",
                    "📋 Por favor, corrija: {reason}"
                ],
                'system': [
                    "⚠️ Ocorreu um erro no sistema. Tente novamente.",
                    "❌ Erro interno. Nossa equipe foi notificada.",
                    "🔧 Estamos com um problema técnico. Por favor, aguarde."
                ]
            },
            'info': {
                'single': [
                    "📋 Aqui estão os detalhes de {item}:",
                    "ℹ️ Informações sobre {item}:",
                    "📄 Dados de {item}:"
                ],
                'list': [
                    "📋 Encontrei {count} {items}:",
                    "📊 Lista de {items} ({count} no total):",
                    "🗂️ Aqui estão os {count} {items} solicitados:"
                ],
                'empty': [
                    "📭 Nenhum {item} encontrado com esses critérios.",
                    "🔍 Não há {items} que correspondam à sua busca.",
                    "📋 A lista de {items} está vazia no momento."
                ]
            },
            'confirmation': {
                'action': [
                    "❓ Tem certeza que deseja {action}?",
                    "🤔 Confirma a ação: {action}?",
                    "⚠️ Esta ação irá {action}. Deseja continuar?"
                ],
                'data': [
                    "📋 Por favor, confirme os dados:\n{details}",
                    "✓ Verifique se está tudo correto:\n{details}",
                    "👀 Revise as informações antes de continuar:\n{details}"
                ]
            }
        }
        
    def _load_context_enhancers(self) -> Dict[str, List[str]]:
        """Load context enhancers for more natural responses"""
        return {
            'polite_prefix': [
                "Com prazer, ",
                "Certamente, ",
                "Claro, ",
                "Sem problemas, "
            ],
            'transition': [
                "Além disso, ",
                "Também, ",
                "Adicionalmente, ",
                "Vale mencionar que "
            ],
            'suggestion': [
                "💡 Sugestão: ",
                "💭 Você também pode: ",
                "📌 Dica: ",
                "ℹ️ Lembre-se: "
            ],
            'closing': [
                "Precisa de mais alguma coisa?",
                "Posso ajudar com algo mais?",
                "Há algo mais que você gostaria de fazer?",
                "Tem outra solicitação?"
            ]
        }
        
    def generate(self, processing_result: ProcessingResult, 
                 data: Optional[Dict[str, Any]] = None) -> GeneratedResponse:
        """Generate natural response based on processing result"""
        
        # Determine response context
        context = self._determine_context(processing_result, data)
        
        # Build base response
        base_response = self._build_base_response(processing_result, context, data)
        
        # Enhance response with natural elements
        enhanced_response = self._enhance_response(base_response, context)
        
        # Format response based on intent
        formatted_response = self._format_response(enhanced_response, processing_result.intent)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(processing_result, data)
        
        # Build metadata
        metadata = {
            'intent': processing_result.intent,
            'confidence': processing_result.confidence,
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'has_data': data is not None
        }
        
        return GeneratedResponse(
            text=formatted_response,
            format_type=self._determine_format_type(processing_result.intent),
            metadata=metadata,
            suggestions=suggestions
        )
        
    def _determine_context(self, result: ProcessingResult, data: Any) -> Dict[str, str]:
        """Determine response context"""
        context = {
            'time_of_day': self._get_time_of_day(),
            'response_type': 'success' if data else 'info',
            'intent': result.intent,
            'has_entities': bool(result.entities)
        }
        
        # Add specific context based on intent
        if result.intent == 'query_freight' and not data:
            context['response_type'] = 'error'
            context['error_type'] = 'not_found'
        elif result.intent in ['create_freight', 'update_status'] and data:
            context['response_type'] = 'success'
            context['action_type'] = 'create' if 'create' in result.intent else 'update'
            
        return context
        
    def _get_time_of_day(self) -> str:
        """Get current time of day for greetings"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        else:
            return 'evening'
            
    def _build_base_response(self, result: ProcessingResult, 
                            context: Dict[str, str], data: Any) -> str:
        """Build base response from template"""
        template = result.response_template
        
        if not data:
            # Use error response if no data
            if context.get('response_type') == 'error':
                error_type = context.get('error_type', 'not_found')
                responses = self.response_variations['error'][error_type]
                template = random.choice(responses)
                
        # Fill template with actual data
        if data:
            response = self._fill_template(template, data, result.entities)
        else:
            response = template.format(
                item=result.entities.get('freight_id', 'o item solicitado'),
                items='fretes',
                count=0
            )
            
        return response
        
    def _fill_template(self, template: str, data: Dict[str, Any], 
                      entities: Dict[str, Any]) -> str:
        """Fill template with actual data"""
        # Extract relevant fields from data
        fields = {
            'freight_id': data.get('id', entities.get('freight_id', 'N/A')),
            'status': data.get('status', 'N/A'),
            'value': self._format_currency(data.get('value', 0)),
            'origin': data.get('origin', {}).get('city', 'N/A'),
            'destination': data.get('destination', {}).get('city', 'N/A'),
            'distance': data.get('distance', 'N/A'),
            'details': self._summarize_data(data),
            'summary': self._create_summary(data),
            'count': 1 if isinstance(data, dict) else len(data),
            'list': self._format_list(data) if isinstance(data, list) else '',
            'filter': self._describe_filter(entities)
        }
        
        # Fill all placeholders
        for key, value in fields.items():
            template = template.replace(f'{{{key}}}', str(value))
            
        return template
        
    def _format_currency(self, value: float) -> str:
        """Format currency value"""
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """Create a summary of the data"""
        if isinstance(data, dict):
            summary_parts = []
            if 'status' in data:
                summary_parts.append(f"Status: {data['status']}")
            if 'value' in data:
                summary_parts.append(f"Valor: {self._format_currency(data['value'])}")
            if 'created_at' in data:
                summary_parts.append(f"Criado em: {self._format_date(data['created_at'])}")
            return ", ".join(summary_parts)
        return "Sem detalhes disponíveis"
        
    def _create_summary(self, data: Any) -> str:
        """Create a comprehensive summary"""
        if isinstance(data, dict):
            return self._summarize_freight(data)
        elif isinstance(data, list):
            return self._summarize_list(data)
        return "Sem dados para resumir"
        
    def _summarize_freight(self, freight: Dict[str, Any]) -> str:
        """Summarize a single freight"""
        parts = []
        
        # Basic info
        parts.append(f"Frete #{freight.get('id', 'N/A')}")
        
        # Route
        if 'origin' in freight and 'destination' in freight:
            origin = freight['origin'].get('city', 'N/A')
            dest = freight['destination'].get('city', 'N/A')
            parts.append(f"{origin} → {dest}")
            
        # Status and value
        if 'status' in freight:
            parts.append(f"Status: {freight['status']}")
        if 'value' in freight:
            parts.append(self._format_currency(freight['value']))
            
        return " | ".join(parts)
        
    def _summarize_list(self, items: List[Dict[str, Any]]) -> str:
        """Summarize a list of items"""
        if not items:
            return "Lista vazia"
            
        # Group by status if available
        status_counts = {}
        total_value = 0
        
        for item in items:
            status = item.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            total_value += item.get('value', 0)
            
        summary_parts = []
        for status, count in status_counts.items():
            summary_parts.append(f"{count} {status}")
            
        summary = f"Total: {len(items)} fretes ({', '.join(summary_parts)})"
        if total_value > 0:
            summary += f" - Valor total: {self._format_currency(total_value)}"
            
        return summary
        
    def _format_list(self, items: List[Dict[str, Any]]) -> str:
        """Format a list of items for display"""
        if not items:
            return "Nenhum item"
            
        formatted_items = []
        for i, item in enumerate(items[:5]):  # Limit to first 5
            formatted_items.append(f"\n  {i+1}. {self._summarize_freight(item)}")
            
        result = "".join(formatted_items)
        
        if len(items) > 5:
            result += f"\n  ... e mais {len(items) - 5} fretes"
            
        return result
        
    def _describe_filter(self, entities: Dict[str, Any]) -> str:
        """Describe the filter applied based on entities"""
        filters = []
        
        if 'status' in entities:
            filters.append(f"com status '{entities['status']}'")
        if 'date' in entities:
            filters.append(f"do dia {entities['date']}")
        if 'location' in entities:
            filters.append(f"para {entities['location']}")
            
        return " ".join(filters) or "solicitados"
        
    def _format_date(self, date_str: str) -> str:
        """Format date for display"""
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date.strftime('%d/%m/%Y às %H:%M')
        except:
            return date_str
            
    def _enhance_response(self, response: str, context: Dict[str, str]) -> str:
        """Enhance response with natural elements"""
        enhanced = response
        
        # Add polite prefix for certain contexts
        if context.get('response_type') == 'success':
            prefix = random.choice(self.context_enhancers['polite_prefix'])
            enhanced = prefix + enhanced.lower()
            
        # Add greeting if appropriate
        if context.get('intent') == 'greeting' or random.random() < 0.1:
            time_greetings = self.response_variations['greeting'][context['time_of_day']]
            greeting = random.choice(time_greetings)
            enhanced = greeting + " " + enhanced
            
        return enhanced
        
    def _format_response(self, response: str, intent: str) -> str:
        """Format response based on intent"""
        # Add emoji indicators for better visual feedback
        if 'error' in response.lower() or 'não' in response.lower():
            if '❌' not in response and '⚠️' not in response:
                response = '⚠️ ' + response
        elif any(word in response.lower() for word in ['sucesso', 'criado', 'atualizado']):
            if '✅' not in response and '✓' not in response:
                response = '✅ ' + response
                
        # Add formatting for lists
        if '\n' in response and intent == 'list_freights':
            lines = response.split('\n')
            formatted_lines = [lines[0]]  # Keep header
            for line in lines[1:]:
                if line.strip() and not line.startswith(' '):
                    formatted_lines.append('  ' + line)
                else:
                    formatted_lines.append(line)
            response = '\n'.join(formatted_lines)
            
        return response
        
    def _determine_format_type(self, intent: str) -> str:
        """Determine the format type based on intent"""
        format_mapping = {
            'list_freights': 'markdown',
            'analyze_performance': 'markdown',
            'query_freight': 'plain',
            'create_freight': 'plain',
            'update_status': 'plain'
        }
        
        return format_mapping.get(intent, 'plain')
        
    def _generate_suggestions(self, result: ProcessingResult, 
                             data: Any) -> List[str]:
        """Generate contextual suggestions"""
        suggestions = []
        
        if result.intent == 'query_freight' and data:
            suggestions.extend([
                "Ver histórico de status",
                "Calcular rota otimizada",
                "Atualizar informações"
            ])
        elif result.intent == 'list_freights':
            suggestions.extend([
                "Filtrar por status",
                "Exportar para relatório",
                "Ver detalhes de um frete específico"
            ])
        elif result.intent == 'create_freight':
            suggestions.extend([
                "Adicionar mais fretes",
                "Calcular rota para este frete",
                "Definir prioridade"
            ])
        elif result.intent == 'unknown':
            suggestions.extend([
                "Listar todos os fretes",
                "Buscar um frete específico",
                "Criar novo frete",
                "Ver relatório de desempenho"
            ])
            
        # Add random helpful suggestion
        if random.random() < 0.3:
            helpful = [
                "💡 Use o ID do frete para buscas mais rápidas",
                "📊 Gere relatórios para análise de desempenho",
                "🚚 Acompanhe seus fretes em tempo real"
            ]
            suggestions.append(random.choice(helpful))
            
        return suggestions[:3]  # Limit to 3 suggestions
        
    def generate_error_response(self, error_type: str, details: str = "") -> GeneratedResponse:
        """Generate error response"""
        error_messages = {
            'validation': f"Erro de validação: {details}",
            'not_found': f"Item não encontrado: {details}",
            'permission': "Você não tem permissão para realizar esta ação",
            'system': "Erro interno do sistema. Tente novamente mais tarde."
        }
        
        message = error_messages.get(error_type, "Ocorreu um erro desconhecido")
        
        return GeneratedResponse(
            text=f"❌ {message}",
            format_type='plain',
            metadata={
                'error_type': error_type,
                'details': details,
                'timestamp': datetime.now().isoformat()
            },
            suggestions=[
                "Verificar os dados informados",
                "Tentar novamente",
                "Contatar suporte se o erro persistir"
            ]
        )
        
    def generate_multi_language_response(self, response: GeneratedResponse, 
                                       language: str) -> GeneratedResponse:
        """Generate response in different languages (future implementation)"""
        # For now, just return the original response
        # In production, this would translate the response
        response.metadata['language'] = language
        return response