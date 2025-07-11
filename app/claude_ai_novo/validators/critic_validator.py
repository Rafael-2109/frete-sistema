"""
🔍 CRITIC AGENT - Agente Crítico Validador

Agente responsável por validar consistência entre respostas dos especialistas.
Detecta inconsistências, conflitos e problemas de validação cruzada.
"""

import logging
import re
from typing import Dict, List, Any

from app.claude_ai_novo.utils.agent_types import ValidationResult

logger = logging.getLogger(__name__)


class CriticAgent:
    """Agente crítico que valida consistência entre especialistas"""
    
    def __init__(self, claude_client=None):
        self.claude_client = claude_client
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> List[Dict[str, Any]]:
        """Carrega regras de validação cruzada"""
        
        return [
            {
                'rule': 'data_consistency',
                'description': 'Datas mencionadas devem ser coerentes entre agentes',
                'validators': ['date_logic', 'timeline_consistency']
            },
            {
                'rule': 'value_consistency', 
                'description': 'Valores financeiros devem bater entre domínios',
                'validators': ['value_cross_check', 'calculation_verification']
            },
            {
                'rule': 'business_logic',
                'description': 'Lógica de negócio deve ser respeitada',
                'validators': ['workflow_validation', 'status_progression']
            },
            {
                'rule': 'data_availability',
                'description': 'Consistência na disponibilidade de dados',
                'validators': ['data_presence_check', 'null_validation']
            },
            {
                'rule': 'numerical_consistency',
                'description': 'Valores numéricos devem ser coerentes',
                'validators': ['sum_validation', 'percentage_check']
            }
        ]
    
    async def validate_responses(self, agent_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida consistência entre respostas dos agentes"""
        
        validation_result = {
            'validation_score': 1.0,
            'inconsistencies': [],
            'recommendations': [],
            'approval': True,
            'cross_validation': {}
        }
        
        # Filtrar apenas respostas válidas
        valid_responses = [r for r in agent_responses if r.get('response')]
        
        if len(valid_responses) < 2:
            validation_result['recommendations'].append("Apenas um agente respondeu - validação cruzada limitada")
            return validation_result
        
        # 1. Validar consistência temporal
        date_consistency = self._validate_date_consistency(valid_responses)
        validation_result['cross_validation']['dates'] = date_consistency
        
        # 2. Validar consistência de dados
        data_consistency = self._validate_data_consistency(valid_responses)
        validation_result['cross_validation']['data'] = data_consistency
        
        # 3. Validar consistência numérica
        numerical_consistency = self._validate_numerical_consistency(valid_responses)
        validation_result['cross_validation']['numerical'] = numerical_consistency
        
        # 4. Validar lógica de negócio
        business_logic = self._validate_business_logic(valid_responses)
        validation_result['cross_validation']['business_logic'] = business_logic
        
        # 5. Consolidar inconsistências
        all_inconsistencies = []
        all_inconsistencies.extend(date_consistency.get('inconsistencies', []))
        all_inconsistencies.extend(data_consistency.get('inconsistencies', []))
        all_inconsistencies.extend(numerical_consistency.get('inconsistencies', []))
        all_inconsistencies.extend(business_logic.get('inconsistencies', []))
        
        validation_result['inconsistencies'] = all_inconsistencies
        
        # 6. Calcular score geral
        consistency_scores = [
            date_consistency.get('score', 1.0),
            data_consistency.get('score', 1.0), 
            numerical_consistency.get('score', 1.0),
            business_logic.get('score', 1.0)
        ]
        validation_result['validation_score'] = sum(consistency_scores) / len(consistency_scores)
        
        # 7. Gerar recomendações baseadas nos problemas encontrados
        validation_result['recommendations'] = self._generate_recommendations(validation_result)
        
        # 8. Determinar aprovação
        validation_result['approval'] = validation_result['validation_score'] >= 0.7
        
        logger.info(f"🔍 Validação concluída: Score={validation_result['validation_score']:.3f}, "
                   f"Inconsistências={len(all_inconsistencies)}, Aprovado={validation_result['approval']}")
        
        return validation_result
    
    def _validate_date_consistency(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida consistência de datas entre respostas"""
        
        # Extrair datas mencionadas nas respostas
        mentioned_dates = []
        for response in responses:
            text = response.get('response', '')
            agent = response.get('agent', 'unknown')
            
            # Regex para encontrar datas em vários formatos
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
                r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
                r'\d{1,2}-\d{1,2}-\d{4}'   # DD-MM-YYYY
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, text)
                mentioned_dates.extend([(agent, date) for date in dates])
        
        # Analisar consistência
        inconsistencies = []
        
        # Verificar se há muitas datas conflitantes
        unique_dates = set(date for _, date in mentioned_dates)
        if len(mentioned_dates) > 0 and len(unique_dates) > len(mentioned_dates) * 0.7:
            inconsistencies.append(f"Muitas datas diferentes mencionadas: {len(unique_dates)} datas únicas em {len(mentioned_dates)} menções")
        
        # Verificar datas obviamente inconsistentes (futuro distante, etc.)
        for agent, date in mentioned_dates:
            if '2030' in date or '2029' in date:
                inconsistencies.append(f"Agente {agent} mencionou data suspeita no futuro: {date}")
        
        score = max(0.0, 1.0 - (len(inconsistencies) * 0.2))
        
        return {
            'score': score,
            'inconsistencies': inconsistencies,
            'dates_found': mentioned_dates,
            'unique_dates': len(unique_dates)
        }
    
    def _validate_data_consistency(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida consistência de dados entre respostas"""
        
        inconsistencies = []
        response_texts = [r.get('response', '') for r in responses]
        
        # 1. Verificar conflitos de disponibilidade de dados
        has_data_responses = [i for i, text in enumerate(response_texts) 
                            if any(indicator in text.lower() for indicator in ['encontrado', 'dados', 'registros', 'resultado'])]
        no_data_responses = [i for i, text in enumerate(response_texts) 
                           if any(indicator in text.lower() for indicator in ['não encontrado', 'sem dados', 'nenhum resultado'])]
        
        if has_data_responses and no_data_responses:
            agents_with_data = [responses[i].get('agent', 'unknown') for i in has_data_responses]
            agents_without_data = [responses[i].get('agent', 'unknown') for i in no_data_responses]
            inconsistencies.append(f"Conflito de dados: {agents_with_data} encontraram dados, {agents_without_data} não encontraram")
        
        # 2. Verificar contradições diretas
        contradiction_keywords = [
            ('aumentou', 'diminuiu'),
            ('melhorou', 'piorou'),
            ('ativo', 'inativo'),
            ('aprovado', 'pendente'),
            ('entregue', 'não entregue')
        ]
        
        for pos_word, neg_word in contradiction_keywords:
            pos_agents = [responses[i].get('agent', 'unknown') for i, text in enumerate(response_texts) if pos_word in text.lower()]
            neg_agents = [responses[i].get('agent', 'unknown') for i, text in enumerate(response_texts) if neg_word in text.lower()]
            
            if pos_agents and neg_agents:
                inconsistencies.append(f"Contradição: {pos_agents} mencionam '{pos_word}', {neg_agents} mencionam '{neg_word}'")
        
        score = max(0.0, 1.0 - (len(inconsistencies) * 0.25))
        
        return {
            'score': score,
            'inconsistencies': inconsistencies,
            'data_availability_conflict': bool(has_data_responses and no_data_responses)
        }
    
    def _validate_numerical_consistency(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida consistência de valores numéricos"""
        
        inconsistencies = []
        
        # Extrair valores numéricos das respostas
        numerical_data = []
        for response in responses:
            text = response.get('response', '')
            agent = response.get('agent', 'unknown')
            
            # Padrões para valores financeiros e quantidades
            patterns = [
                (r'R\$\s*[\d.,]+', 'currency'),
                (r'[\d.,]+%', 'percentage'),
                (r'\b\d+\s+(?:pedidos|entregas|fretes|embarques)', 'count'),
                (r'[\d.,]+\s*(?:kg|ton|toneladas)', 'weight')
            ]
            
            for pattern, value_type in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    numerical_data.append({
                        'agent': agent,
                        'value': match,
                        'type': value_type
                    })
        
        # Detectar discrepâncias significativas em valores similares
        currency_values = [item for item in numerical_data if item['type'] == 'currency']
        if len(currency_values) > 1:
            # Converter valores para comparação (simplificado)
            try:
                parsed_values = []
                for item in currency_values:
                    value_str = re.sub(r'[R$\s]', '', item['value']).replace(',', '.')
                    try:
                        parsed_values.append((float(value_str), item['agent']))
                    except ValueError:
                        continue
                
                if len(parsed_values) > 1:
                    values_only = [v[0] for v in parsed_values]
                    max_val, min_val = max(values_only), min(values_only)
                    
                    # Se a diferença for maior que 50%, flaggar como inconsistência
                    if max_val > 0 and (max_val - min_val) / max_val > 0.5:
                        agents_involved = [agent for _, agent in parsed_values]
                        inconsistencies.append(f"Valores financeiros muito discrepantes entre agentes: {agents_involved}")
                        
            except Exception as e:
                logger.warning(f"Erro na validação numérica: {e}")
        
        score = max(0.0, 1.0 - (len(inconsistencies) * 0.3))
        
        return {
            'score': score,
            'inconsistencies': inconsistencies,
            'numerical_data_found': len(numerical_data)
        }
    
    def _validate_business_logic(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Valida lógica de negócio entre respostas"""
        
        inconsistencies = []
        
        # Regras de negócio específicas do sistema de fretes
        business_rules = [
            {
                'name': 'embarque_entrega_sequence',
                'description': 'Embarques devem sair antes das entregas serem realizadas',
                'keywords': ['embarque', 'entrega']
            },
            {
                'name': 'frete_aprovacao_sequence', 
                'description': 'Fretes devem ser aprovados antes do pagamento',
                'keywords': ['frete', 'aprovação', 'pagamento']
            },
            {
                'name': 'pedido_faturamento_sequence',
                'description': 'Pedidos devem ser faturados antes da entrega',
                'keywords': ['pedido', 'faturamento', 'entrega']
            }
        ]
        
        # Validar cada regra de negócio
        for rule in business_rules:
            rule_violations = self._check_business_rule(responses, rule)
            inconsistencies.extend(rule_violations)
        
        score = max(0.0, 1.0 - (len(inconsistencies) * 0.2))
        
        return {
            'score': score,
            'inconsistencies': inconsistencies,
            'rules_checked': len(business_rules)
        }
    
    def _check_business_rule(self, responses: List[Dict[str, Any]], rule: Dict[str, Any]) -> List[str]:
        """Verifica uma regra de negócio específica"""
        
        violations = []
        
        # Análise simplificada de violações de regras
        # (Em um sistema real, isso seria mais sofisticado)
        
        rule_keywords = rule['keywords']
        relevant_responses = []
        
        for response in responses:
            text = response.get('response', '').lower()
            if any(keyword in text for keyword in rule_keywords):
                relevant_responses.append(response)
        
        # Se múltiplos agentes mencionam keywords da regra, verificar contradições
        if len(relevant_responses) > 1:
            # Placeholder para lógica de validação mais específica
            # Por exemplo, verificar se status de processos são logicamente consistentes
            pass
        
        return violations
    
    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas nos problemas encontrados"""
        
        recommendations = []
        inconsistencies = validation_result.get('inconsistencies', [])
        score = validation_result.get('validation_score', 1.0)
        
        if score < 0.5:
            recommendations.append("Score de validação muito baixo - revisar dados de entrada")
        
        if any('data' in inc.lower() for inc in inconsistencies):
            recommendations.append("Verificar fontes de dados para resolver inconsistências")
        
        if any('date' in inc.lower() or 'data' in inc.lower() for inc in inconsistencies):
            recommendations.append("Revisar datas mencionadas para garantir consistência temporal")
        
        if any('valor' in inc.lower() or 'financeiro' in inc.lower() for inc in inconsistencies):
            recommendations.append("Validar cálculos financeiros para resolver discrepâncias")
        
        if len(inconsistencies) > 3:
            recommendations.append("Múltiplas inconsistências detectadas - considerar consulta mais específica")
        
        if not recommendations:
            recommendations.append("Validação aprovada - respostas consistentes entre agentes")
        
        return recommendations


# Exportações principais
__all__ = [
    'CriticAgent'
] 