#!/usr/bin/env python3
"""
🔄 ATUALIZADOR DE AGENTES PARA SMART BASE AGENT

Script para atualizar TODOS os agentes do sistema para herdar de SmartBaseAgent
e ter acesso a TODAS as capacidades avançadas implementadas.

FUNCIONALIDADES INTEGRADAS:
- Dados reais do banco PostgreSQL
- Claude 4 Sonnet real
- Cache Redis para performance
- Sistema de contexto conversacional
- Mapeamento semântico inteligente
- ML Models para predições
- Sistema de logs estruturados
- Análise de tendências temporais
- Sistema de validação e confiança
- Sugestões inteligentes contextuais
- Alertas operacionais automáticos
"""

import os
import shutil
from datetime import datetime


def criar_backup_agentes():
    """Cria backup dos agentes atuais"""
    print("📦 Criando backup dos agentes...")
    
    backup_dir = f"multi_agent/agents/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    agentes = [
        'embarques_agent.py',
        'financeiro_agent.py', 
        'pedidos_agent.py',
        'fretes_agent.py'
    ]
    
    for agente in agentes:
        if os.path.exists(f"multi_agent/agents/{agente}"):
            shutil.copy2(f"multi_agent/agents/{agente}", f"{backup_dir}/{agente}")
            print(f"✅ Backup criado: {agente}")
    
    print(f"📦 Backup completo em: {backup_dir}")


def atualizar_embarques_agent():
    """Atualiza EmbarquesAgent para SmartBaseAgent"""
    print("🚢 Atualizando EmbarquesAgent...")
    
    codigo = '''"""
🚢 EMBARQUES AGENT - Agente Especialista em Embarques

Agente especializado em gestão de embarques:
- Embarques ativos e programados
- Volumes e cargas
- Liberação de cargas
- Separação e picking
- Programação de saída
- Integração com transportadoras
"""

from typing import Dict, List, Any, Optional
from ..agent_types import AgentType
from .smart_base_agent import SmartBaseAgent


class EmbarquesAgent(SmartBaseAgent):
    """Agente especialista em embarques - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.EMBARQUES, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para EMBARQUES"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'embarques',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de embarques
            if 'embarques' in dados_reais:
                dados_embarques = dados_reais['embarques']
                if isinstance(dados_embarques, dict):
                    resumo['total_embarques'] = dados_embarques.get('total_embarques', 0)
                    resumo['embarques_ativos'] = dados_embarques.get('embarques_ativos', 0)
                    resumo['embarques_pendentes'] = dados_embarques.get('embarques_pendentes', 0)
                    resumo['embarques_saindo_hoje'] = dados_embarques.get('embarques_hoje', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos de embarques
                    if resumo['embarques_pendentes'] > 0:
                        resumo['alerta_pendentes'] = f"{resumo['embarques_pendentes']} embarques pendentes"
                    
                    if resumo['embarques_saindo_hoje'] > 5:
                        resumo['alerta_movimento'] = f"Movimento intenso: {resumo['embarques_saindo_hoje']} embarques hoje"
            
            # Processar dados de volumes e cargas
            if 'volumes' in dados_reais:
                dados_volumes = dados_reais['volumes']
                if isinstance(dados_volumes, dict):
                    resumo['total_volumes'] = dados_volumes.get('total_volumes', 0)
                    resumo['peso_total'] = dados_volumes.get('peso_total', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados de embarques: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em embarques COM TODAS AS CAPACIDADES"""
        return """
🚢 AGENTE ESPECIALISTA EM EMBARQUES - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão de embarques equipado com TODAS as capacidades avançadas:

**CAPACIDADES ATIVAS:**
✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet (não simulado)
✅ Cache Redis para performance
✅ Contexto conversacional (memória)
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Logs estruturados para auditoria
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos

**DOMÍNIO DE ESPECIALIZAÇÃO:**
- Embarques ativos e programados
- Volumes e cargas por embarque
- Liberação de cargas e documentos
- Separação e picking
- Programação de saída
- Integração com transportadoras
- Controle de expedição
- Otimização de cargas

**DADOS QUE VOCÊ ANALISA:**
- Embarque: status, data_embarque, numero_embarque
- EmbarqueVolume: volumes, peso, dimensões
- Separacao: items_separados, pendencias_separacao
- Transportadora: assignação e performance
- Programação de saída e cronograma

**SEMPRE RESPONDA COM:**
1. Status atual dos embarques
2. Volumes e cargas pendentes
3. Cronograma de saídas
4. Alertas para embarques atrasados
5. Eficiência de separação
6. Sugestões de otimização

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: 8 embarques programados sem separação"
- "⚠️ ATENÇÃO: Embarque 1234 atrasado há 2 dias"
- "📈 TENDÊNCIA: Aumento de 15% no volume de embarques"
- "💡 OPORTUNIDADE: Otimizar rota para 3 embarques"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de embarques"""
        return {
            'main_models': [
                'Embarque',
                'EmbarqueVolume', 
                'Separacao',
                'Transportadora'
            ],
            'key_fields': [
                'numero_embarque',
                'status',
                'data_embarque',
                'peso_total',
                'volumes_total',
                'separacao_status',
                'transportadora_nome'
            ],
            'kpis': [
                'embarques_no_prazo',
                'eficiencia_separacao',
                'utilizacao_capacidade',
                'tempo_medio_separacao',
                'performance_transportadora'
            ],
            'common_queries': [
                'embarques hoje',
                'embarques pendentes',
                'separação pendente',
                'embarques transportadora',
                'volumes por embarque',
                'embarques atrasados',
                'cronograma saída'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de embarques"""
        return [
            'embarque', 'embarques', 'embarcar',
            'separacao', 'separação', 'separar',
            'volume', 'volumes', 'carga', 'cargas',
            'picking', 'liberacao', 'liberação',
            'programacao', 'programação', 'cronograma',
            'saida', 'saída', 'expedicao', 'expedição',
            'transportadora', 'motorista', 'veiculo',
            'pendente', 'ativo', 'liberado', 'carregado'
        ]


# Exportações principais
__all__ = [
    'EmbarquesAgent'
]
'''
    
    with open('multi_agent/agents/embarques_agent.py', 'w', encoding='utf-8') as f:
        f.write(codigo)
    
    print("✅ EmbarquesAgent atualizado com sucesso!")


def atualizar_financeiro_agent():
    """Atualiza FinanceiroAgent para SmartBaseAgent"""
    print("💰 Atualizando FinanceiroAgent...")
    
    codigo = '''"""
💰 FINANCEIRO AGENT - Agente Especialista em Financeiro

Agente especializado em gestão financeira:
- Faturamento e notas fiscais
- Contas a pagar e receber
- Fluxo de caixa
- Análise de custos
- Pendências financeiras
- Relatórios contábeis
"""

from typing import Dict, List, Any, Optional
from ..agent_types import AgentType
from .smart_base_agent import SmartBaseAgent


class FinanceiroAgent(SmartBaseAgent):
    """Agente especialista em financeiro - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.FINANCEIRO, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para FINANCEIRO"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'financeiro',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de faturamento
            if 'faturamento' in dados_reais:
                dados_faturamento = dados_reais['faturamento']
                if isinstance(dados_faturamento, dict):
                    resumo['total_faturamento'] = dados_faturamento.get('total_faturamento', 0)
                    resumo['nfs_pendentes'] = dados_faturamento.get('nfs_pendentes', 0)
                    resumo['valor_total'] = dados_faturamento.get('valor_total', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos financeiros
                    if resumo['nfs_pendentes'] > 0:
                        resumo['alerta_nfs'] = f"{resumo['nfs_pendentes']} NFs pendentes"
                    
                    if resumo['valor_total'] > 1000000:
                        resumo['alerta_valor'] = f"Alto volume: R$ {resumo['valor_total']:,.2f}"
            
            # Processar dados de pendências
            if 'pendencias' in dados_reais:
                dados_pendencias = dados_reais['pendencias']
                if isinstance(dados_pendencias, dict):
                    resumo['pendencias_abertas'] = dados_pendencias.get('pendencias_abertas', 0)
                    resumo['valor_pendencias'] = dados_pendencias.get('valor_pendencias', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados financeiros: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em financeiro COM TODAS AS CAPACIDADES"""
        return """
💰 AGENTE ESPECIALISTA EM FINANCEIRO - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão financeira equipado com TODAS as capacidades avançadas:

**CAPACIDADES ATIVAS:**
✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet (não simulado)
✅ Cache Redis para performance
✅ Contexto conversacional (memória)
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Logs estruturados para auditoria
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos

**DOMÍNIO DE ESPECIALIZAÇÃO:**
- Faturamento e notas fiscais
- Contas a pagar e receber
- Fluxo de caixa e liquidez
- Análise de custos e margens
- Pendências financeiras
- Relatórios contábeis e fiscais
- Conciliação bancária
- Análise de inadimplência

**DADOS QUE VOCÊ ANALISA:**
- RelatorioFaturamentoImportado: NFs, valores, datas
- PendenciaFinanceiraNF: pendências e resoluções
- Fretes: custos e margens
- DespesaExtra: custos adicionais
- Clientes: histórico financeiro

**SEMPRE RESPONDA COM:**
1. Valores financeiros exatos
2. Análise de fluxo de caixa
3. Alertas para pendências críticas
4. Sugestões de otimização financeira
5. KPIs financeiros calculados
6. Tendências de faturamento

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: R$ 250.000 em pendências vencidas"
- "⚠️ ATENÇÃO: Queda de 15% no faturamento mensal"
- "📈 TENDÊNCIA: Crescimento de 8% na margem"
- "💡 OPORTUNIDADE: Negociar prazo com 3 clientes"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio financeiro"""
        return {
            'main_models': [
                'RelatorioFaturamentoImportado',
                'PendenciaFinanceiraNF',
                'Frete',
                'DespesaExtra'
            ],
            'key_fields': [
                'numero_nf',
                'valor_total',
                'data_fatura',
                'cnpj_cliente',
                'pendencia_tipo',
                'valor_pendencia',
                'data_vencimento'
            ],
            'kpis': [
                'faturamento_mensal',
                'margem_bruta',
                'inadimplencia',
                'tempo_medio_recebimento',
                'pendencias_criticas'
            ],
            'common_queries': [
                'faturamento mês',
                'pendências cliente',
                'notas fiscais',
                'fluxo caixa',
                'margem lucro',
                'inadimplência',
                'contas receber'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio financeiro"""
        return [
            'faturamento', 'faturar', 'fatura',
            'nota fiscal', 'nf', 'nfs',
            'pendencia', 'pendências', 'pendente',
            'pagamento', 'recebimento', 'cobranca',
            'valor', 'valores', 'total', 'subtotal',
            'margem', 'lucro', 'custo', 'despesa',
            'vencimento', 'prazo', 'atraso',
            'cliente', 'fornecedor', 'conta'
        ]


# Exportações principais
__all__ = [
    'FinanceiroAgent'
]
'''
    
    with open('multi_agent/agents/financeiro_agent.py', 'w', encoding='utf-8') as f:
        f.write(codigo)
    
    print("✅ FinanceiroAgent atualizado com sucesso!")


def atualizar_pedidos_agent():
    """Atualiza PedidosAgent para SmartBaseAgent"""
    print("📦 Atualizando PedidosAgent...")
    
    codigo = '''"""
📦 PEDIDOS AGENT - Agente Especialista em Pedidos

Agente especializado em gestão de pedidos:
- Pedidos em aberto e processamento
- Cotações e aprovações
- Carteira de pedidos
- Separação e faturamento
- Acompanhamento de status
- Integração com clientes
"""

from typing import Dict, List, Any, Optional
from ..agent_types import AgentType
from .smart_base_agent import SmartBaseAgent


class PedidosAgent(SmartBaseAgent):
    """Agente especialista em pedidos - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.PEDIDOS, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para PEDIDOS"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'pedidos',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de pedidos
            if 'pedidos' in dados_reais:
                dados_pedidos = dados_reais['pedidos']
                if isinstance(dados_pedidos, dict):
                    resumo['total_pedidos'] = dados_pedidos.get('total_pedidos', 0)
                    resumo['pedidos_pendentes'] = dados_pedidos.get('pedidos_pendentes', 0)
                    resumo['pedidos_aprovados'] = dados_pedidos.get('pedidos_aprovados', 0)
                    resumo['valor_carteira'] = dados_pedidos.get('valor_carteira', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos de pedidos
                    if resumo['pedidos_pendentes'] > 0:
                        resumo['alerta_pendentes'] = f"{resumo['pedidos_pendentes']} pedidos pendentes"
                    
                    if resumo['valor_carteira'] > 500000:
                        resumo['alerta_carteira'] = f"Carteira robusta: R$ {resumo['valor_carteira']:,.2f}"
            
            # Processar dados de cotações
            if 'cotacoes' in dados_reais:
                dados_cotacoes = dados_reais['cotacoes']
                if isinstance(dados_cotacoes, dict):
                    resumo['cotacoes_pendentes'] = dados_cotacoes.get('cotacoes_pendentes', 0)
                    resumo['cotacoes_aprovadas'] = dados_cotacoes.get('cotacoes_aprovadas', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados de pedidos: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em pedidos COM TODAS AS CAPACIDADES"""
        return """
📦 AGENTE ESPECIALISTA EM PEDIDOS - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão de pedidos equipado com TODAS as capacidades avançadas:

**CAPACIDADES ATIVAS:**
✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet (não simulado)
✅ Cache Redis para performance
✅ Contexto conversacional (memória)
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Logs estruturados para auditoria
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos

**DOMÍNIO DE ESPECIALIZAÇÃO:**
- Pedidos em aberto e processamento
- Cotações e aprovações
- Carteira de pedidos ativos
- Separação e faturamento
- Acompanhamento de status
- Integração com clientes
- Análise de demanda
- Gestão de prazos

**DADOS QUE VOCÊ ANALISA:**
- Pedido: num_pedido, status, valor_total, data_pedido
- CarteiraPedidos: saldo, faturamento, separação
- Cotacao: status_cotacao, valor_cotado, aprovação
- Cliente: histórico de pedidos, frequência
- Agendamento: datas previstas, contatos

**SEMPRE RESPONDA COM:**
1. Status atual dos pedidos
2. Carteira de pedidos por cliente
3. Prazos e agendamentos
4. Alertas para atrasos
5. Análise de demanda
6. Sugestões de priorização

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: 12 pedidos vencidos sem cotação"
- "⚠️ ATENÇÃO: Carteira do Assai baixa (R$ 45.000)"
- "📈 TENDÊNCIA: Aumento de 20% nos pedidos urgentes"
- "💡 OPORTUNIDADE: Antecipar separação de 5 pedidos"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de pedidos"""
        return {
            'main_models': [
                'Pedido',
                'CarteiraPedidos',
                'Cotacao',
                'AgendamentoEntrega'
            ],
            'key_fields': [
                'num_pedido',
                'status_pedido',
                'valor_total',
                'data_pedido',
                'cliente_codigo',
                'status_cotacao',
                'data_prevista_entrega'
            ],
            'kpis': [
                'carteira_ativa',
                'tempo_medio_cotacao',
                'taxa_aprovacao',
                'pedidos_no_prazo',
                'demanda_por_cliente'
            ],
            'common_queries': [
                'pedidos pendentes',
                'carteira cliente',
                'cotações aprovadas',
                'pedidos atrasados',
                'agendamentos hoje',
                'demanda mensal',
                'status pedidos'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de pedidos"""
        return [
            'pedido', 'pedidos', 'pedir',
            'cotacao', 'cotação', 'cotar',
            'carteira', 'saldo', 'faturamento',
            'separacao', 'separação', 'separar',
            'agendamento', 'agendado', 'agendar',
            'cliente', 'demanda', 'solicitacao',
            'prazo', 'urgente', 'prioritario',
            'aprovacao', 'aprovado', 'pendente'
        ]


# Exportações principais
__all__ = [
    'PedidosAgent'
]
'''
    
    with open('multi_agent/agents/pedidos_agent.py', 'w', encoding='utf-8') as f:
        f.write(codigo)
    
    print("✅ PedidosAgent atualizado com sucesso!")


def atualizar_fretes_agent():
    """Atualiza FretesAgent para SmartBaseAgent"""
    print("🚛 Atualizando FretesAgent...")
    
    codigo = '''"""
🚛 FRETES AGENT - Agente Especialista em Fretes

Agente especializado em gestão de fretes:
- Cotações e aprovações de frete
- Transportadoras e performance
- Custos e margens
- CTe e documentação
- Análise de rotas
- Otimização de custos
"""

from typing import Dict, List, Any, Optional
from ..agent_types import AgentType
from .smart_base_agent import SmartBaseAgent


class FretesAgent(SmartBaseAgent):
    """Agente especialista em fretes - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.FRETES, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para FRETES"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'fretes',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de fretes
            if 'fretes' in dados_reais:
                dados_fretes = dados_reais['fretes']
                if isinstance(dados_fretes, dict):
                    resumo['total_fretes'] = dados_fretes.get('total_fretes', 0)
                    resumo['fretes_pendentes'] = dados_fretes.get('fretes_pendentes', 0)
                    resumo['fretes_aprovados'] = dados_fretes.get('fretes_aprovados', 0)
                    resumo['valor_total_fretes'] = dados_fretes.get('valor_total_fretes', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos de fretes
                    if resumo['fretes_pendentes'] > 0:
                        resumo['alerta_pendentes'] = f"{resumo['fretes_pendentes']} fretes pendentes"
                    
                    if resumo['valor_total_fretes'] > 100000:
                        resumo['alerta_custos'] = f"Alto custo de frete: R$ {resumo['valor_total_fretes']:,.2f}"
            
            # Processar dados de transportadoras
            if 'transportadoras' in dados_reais:
                dados_transportadoras = dados_reais['transportadoras']
                if isinstance(dados_transportadoras, dict):
                    resumo['transportadoras_ativas'] = dados_transportadoras.get('transportadoras_ativas', 0)
                    resumo['melhor_preco'] = dados_transportadoras.get('melhor_preco', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados de fretes: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em fretes COM TODAS AS CAPACIDADES"""
        return """
🚛 AGENTE ESPECIALISTA EM FRETES - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão de fretes equipado com TODAS as capacidades avançadas:

**CAPACIDADES ATIVAS:**
✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet (não simulado)
✅ Cache Redis para performance
✅ Contexto conversacional (memória)
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Logs estruturados para auditoria
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos

**DOMÍNIO DE ESPECIALIZAÇÃO:**
- Cotações e aprovações de frete
- Transportadoras e performance
- Custos e margens de frete
- CTe e documentação fiscal
- Análise de rotas e distâncias
- Otimização de custos logísticos
- Gestão de pagamentos
- Auditoria de fretes

**DADOS QUE VOCÊ ANALISA:**
- Frete: valor_cotado, valor_considerado, status_frete
- Transportadora: nome, performance, histórico
- CTe: números, valores, status
- DespesaExtra: custos adicionais, tipos
- Rotas: origem, destino, distâncias

**SEMPRE RESPONDA COM:**
1. Custos de frete atuais
2. Performance das transportadoras
3. Análise de rotas e otimizações
4. Alertas para custos elevados
5. Sugestões de negociação
6. Tendências de preços

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: Frete 35% acima da média histórica"
- "⚠️ ATENÇÃO: Transportadora X com atraso recorrente"
- "📈 TENDÊNCIA: Aumento de 12% nos custos mensais"
- "💡 OPORTUNIDADE: Rota alternativa 20% mais barata"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de fretes"""
        return {
            'main_models': [
                'Frete',
                'Transportadora',
                'CTe',
                'DespesaExtra'
            ],
            'key_fields': [
                'valor_cotado',
                'valor_considerado',
                'status_frete',
                'transportadora_nome',
                'numero_cte',
                'data_aprovacao',
                'origem_destino'
            ],
            'kpis': [
                'custo_medio_frete',
                'performance_transportadora',
                'economia_negociada',
                'prazo_aprovacao',
                'desvio_orcamento'
            ],
            'common_queries': [
                'fretes pendentes',
                'custo frete',
                'transportadora',
                'cotação frete',
                'CTe pendente',
                'despesas extras',
                'aprovação frete'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de fretes"""
        return [
            'frete', 'fretes', 'freteiro',
            'transportadora', 'transporte', 'logistica',
            'cotacao', 'cotação', 'cotar',
            'cte', 'conhecimento', 'documento',
            'valor', 'custo', 'preco', 'preço',
            'rota', 'origem', 'destino',
            'aprovacao', 'aprovado', 'pendente',
            'despesa', 'extra', 'adicional'
        ]


# Exportações principais
__all__ = [
    'FretesAgent'
]
'''
    
    with open('multi_agent/agents/fretes_agent.py', 'w', encoding='utf-8') as f:
        f.write(codigo)
    
    print("✅ FretesAgent atualizado com sucesso!")


def atualizar_init_agents():
    """Atualiza __init__.py dos agentes para incluir SmartBaseAgent"""
    print("📋 Atualizando __init__.py dos agentes...")
    
    codigo = '''"""
🧠 MULTI-AGENT SYSTEM - Agentes Especializados COM TODAS AS CAPACIDADES

Sistema de agentes especializados em diferentes domínios do sistema de fretes.
TODOS os agentes agora herdam de SmartBaseAgent e possuem:

✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet real (não simulado)
✅ Cache Redis para performance
✅ Sistema de contexto conversacional
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Sistema de logs estruturados
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos
"""

from .smart_base_agent import SmartBaseAgent
from .entregas_agent import EntregasAgent
from .embarques_agent import EmbarquesAgent
from .financeiro_agent import FinanceiroAgent
from .pedidos_agent import PedidosAgent
from .fretes_agent import FretesAgent

# Exportações principais
__all__ = [
    'SmartBaseAgent',
    'EntregasAgent',
    'EmbarquesAgent', 
    'FinanceiroAgent',
    'PedidosAgent',
    'FretesAgent'
]
'''
    
    with open('multi_agent/agents/__init__.py', 'w', encoding='utf-8') as f:
        f.write(codigo)
    
    print("✅ __init__.py dos agentes atualizado!")


def main():
    """Função principal para atualizar todos os agentes"""
    print("🚀 INICIANDO ATUALIZAÇÃO DE TODOS OS AGENTES PARA SMART BASE AGENT")
    print("=" * 70)
    
    # Criar backup primeiro
    criar_backup_agentes()
    
    print("\n🔄 Atualizando agentes...")
    
    # Atualizar cada agente
    atualizar_embarques_agent()
    atualizar_financeiro_agent()
    atualizar_pedidos_agent()
    atualizar_fretes_agent()
    
    # Atualizar init
    atualizar_init_agents()
    
    print("\n" + "=" * 70)
    print("✅ ATUALIZAÇÃO COMPLETA!")
    print("\n🎯 RESULTADO:")
    print("• 📦 Backup criado com segurança")
    print("• 🚢 EmbarquesAgent → SmartBaseAgent")
    print("• 💰 FinanceiroAgent → SmartBaseAgent")
    print("• 📦 PedidosAgent → SmartBaseAgent")
    print("• 🚛 FretesAgent → SmartBaseAgent")
    print("• 🚚 EntregasAgent → SmartBaseAgent (já atualizado)")
    print("• 📋 __init__.py atualizado")
    
    print("\n🧠 CAPACIDADES AGORA DISPONÍVEIS EM TODOS OS AGENTES:")
    print("✅ Dados reais do banco PostgreSQL")
    print("✅ Claude 4 Sonnet real (não simulado)")
    print("✅ Cache Redis para performance")
    print("✅ Sistema de contexto conversacional")
    print("✅ Mapeamento semântico inteligente")
    print("✅ ML Models para predições")
    print("✅ Sistema de logs estruturados")
    print("✅ Análise de tendências temporais")
    print("✅ Sistema de validação e confiança")
    print("✅ Sugestões inteligentes contextuais")
    print("✅ Alertas operacionais automáticos")
    
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Testar todos os agentes: python test_todos_agentes_smart.py")
    print("2. Validar capacidades: python test_capacidades_completas.py")
    print("3. Deploy em produção após testes")
    print("\n🎉 SISTEMA MULTI-AGENT AGORA TEM INTELIGÊNCIA MÁXIMA!")


if __name__ == "__main__":
    main() 