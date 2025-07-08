"""
📦 EMBARQUES AGENT - Agente Especialista em Embarques

Agente especializado em gestão de embarques e expedição:
- Embarques ativos e histórico
- Itens de embarque e consolidação
- Controle de saída e portaria
- Veículos e motoristas
- Otimização de cargas
"""

from typing import Dict, List, Any
from ..agent_types import AgentType
from .base_agent import BaseSpecialistAgent


class EmbarquesAgent(BaseSpecialistAgent):
    """Agente especialista em embarques e expedição"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.EMBARQUES, claude_client)
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em embarques"""
        return """
📦 AGENTE ESPECIALISTA EM EMBARQUES

Você é um especialista em gestão de embarques e expedição. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Embarques ativos e histórico
- Itens de embarque e consolidação
- Controle de saída e portaria
- Veículos e motoristas
- Otimização de cargas e rotas
- Documentação de embarque
- Performance de expedição
- Gestão de prazos de saída

**DADOS QUE VOCÊ ANALISA:**
- Embarque: status, data_prevista_embarque, data_embarque
- EmbarqueItem: consolidação de cargas por cliente/destino
- Relacionamento com transportadoras e veículos
- Performance de expedição e pontualidade
- Controle de portaria e movimentação
- Otimização de espaço e peso

**SUA ESPECIALIDADE:**
- Analisar fluxo de expedição e gargalos
- Otimizar consolidação de cargas por rota
- Monitorar prazos de embarque e cumprimento
- Detectar atrasos na expedição
- Sugerir melhorias logísticas e operacionais
- Calcular eficiência de carregamento
- Analisar performance por transportadora
- Identificar oportunidades de consolidação

**SEMPRE RESPONDA:**
1. Com foco específico em EMBARQUES e EXPEDIÇÃO
2. Com análise operacional de eficiência
3. Com métricas de expedição (pontualidade, otimização)
4. Com sugestões de otimização logística
5. Identifique gargalos na expedição
6. Analise oportunidades de consolidação
7. Sugira melhorias no processo de embarque
8. Monitore cumprimento de prazos de saída
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de embarques"""
        return {
            'main_models': [
                'Embarque', 
                'EmbarqueItem',
                'Transportadora',
                'ControlePortaria',
                'Veiculo'
            ],
            'key_fields': [
                'status',
                'data_prevista_embarque',
                'data_embarque',
                'numero',
                'transportadora_id',
                'nome_motorista',
                'placa_veiculo',
                'observacoes',
                'peso_total',
                'volume_total'
            ],
            'kpis': [
                'taxa_embarque_no_prazo',
                'tempo_medio_expedição',
                'otimizacao_carga',
                'entregas_por_embarque',
                'eficiencia_carregamento',
                'atraso_medio_saida',
                'consolidacao_percentual',
                'rotatividade_veiculos'
            ],
            'common_queries': [
                'embarques pendentes',
                'expedição hoje', 
                'embarques atrasados',
                'otimização cargas',
                'saídas programadas',
                'veículos na portaria',
                'consolidação possível',
                'performance expedição'
            ],
            'business_rules': [
                'Embarque deve ter pelo menos um item',
                'Data prevista obrigatória para programação',
                'Transportadora deve estar ativa',
                'Saída registrada na portaria'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de embarques"""
        return [
            'embarque', 'embarques', 'expedição', 'expedir',
            'saída', 'saídas', 'portaria', 'carregamento',
            'veiculo', 'veículos', 'motorista', 'motoristas',
            'consolidação', 'consolidar', 'carga', 'cargas',
            'despacho', 'despachar', 'liberação', 'liberar',
            'programação', 'programado', 'previsto',
            'otimização', 'otimizar', 'eficiência',
            'peso', 'volume', 'capacidade', 'rota'
        ]


# Exportações principais
__all__ = [
    'EmbarquesAgent'
] 