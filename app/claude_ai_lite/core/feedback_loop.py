"""
Feedback Loop Service - Análise automática de perguntas não respondidas.

Responsabilidades:
1. Agrupa perguntas não respondidas por padrão semântico
2. Identifica gaps comuns no sistema
3. Sugere criação de capacidades/loaders
4. Gera insights para melhoria contínua

Criado em: 24/11/2025
Limite: 300 linhas
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# === PADRÕES DE PERGUNTAS CONHECIDOS ===
# Usado para agrupar perguntas semelhantes

PADROES_CONHECIDOS = [
    {
        'nome': 'cliente_sem_condicao',
        'padrao': r'pedidos?\s+(do|da|para)\s+(?:cliente\s+)?(\w+)\s+sem\s+(\w+)',
        'template': 'Pedidos do cliente {cliente} sem {condicao}',
        'sugestao': 'Criar filtro composto: cliente + condição NULL'
    },
    {
        'nome': 'cliente_com_condicao',
        'padrao': r'pedidos?\s+(do|da|para)\s+(?:cliente\s+)?(\w+)\s+com\s+(\w+)',
        'template': 'Pedidos do cliente {cliente} com {condicao}',
        'sugestao': 'Criar filtro composto: cliente + condição NOT NULL'
    },
    {
        'nome': 'produto_estoque',
        'padrao': r'(quando|ter[aá]?|vai\s+ter)\s+estoque\s+(de|do|da)?\s*(\w+)',
        'template': 'Quando terá estoque de {produto}',
        'sugestao': 'Integrar com projeção de estoque'
    },
    {
        'nome': 'cliente_data_envio',
        'padrao': r'(o\s+que|quais?)\s+(posso|pode)\s+enviar\s+(para|pro|pra)\s+(\w+)\s+(hoje|amanh[aã]|dia\s+\d+)',
        'template': 'O que posso enviar para {cliente} em {data}',
        'sugestao': 'Criar capacidade: cliente + data + disponibilidade'
    },
    {
        'nome': 'lista_atrasados',
        'padrao': r'(pedidos?|itens?)\s+(atrasados?|vencidos?|pendentes?)',
        'template': 'Pedidos atrasados/pendentes',
        'sugestao': 'Criar filtro: data < hoje + status aberto'
    },
    {
        'nome': 'total_por_rota',
        'padrao': r'(quanto|total|valor)\s+(tem|de)?\s+(?:para\s+)?(rota\s+)?(\w{2,3})',
        'template': 'Total/Quanto tem para rota {rota}',
        'sugestao': 'Criar agregação: SUM por rota'
    },
    {
        'nome': 'multiplos_pedidos',
        'padrao': r'(VCD\d+).*?(VCD\d+)',
        'template': 'Consulta múltiplos pedidos',
        'sugestao': 'Criar capacidade: busca batch de pedidos'
    },
]


class FeedbackLoopService:
    """Serviço de análise e feedback de perguntas não respondidas."""

    def __init__(self):
        self.padroes = PADROES_CONHECIDOS

    def analisar_perguntas_recentes(self, dias: int = 7) -> Dict[str, Any]:
        """
        Analisa perguntas não respondidas dos últimos N dias.

        Returns:
            Dict com análise completa e sugestões
        """
        from ..models import ClaudePerguntaNaoRespondida

        data_limite = datetime.now() - timedelta(days=dias)

        # Busca perguntas pendentes
        perguntas = ClaudePerguntaNaoRespondida.query.filter(
            ClaudePerguntaNaoRespondida.criado_em >= data_limite,
            ClaudePerguntaNaoRespondida.status == 'pendente'
        ).all()

        if not perguntas:
            return {
                'total_analisado': 0,
                'grupos': [],
                'insights': [],
                'sugestoes_priorizadas': []
            }

        # Agrupa por padrão
        grupos = self._agrupar_por_padrao(perguntas)

        # Gera insights
        insights = self._gerar_insights(perguntas, grupos)

        # Prioriza sugestões
        sugestoes = self._priorizar_sugestoes(grupos)

        return {
            'total_analisado': len(perguntas),
            'periodo_dias': dias,
            'grupos': grupos,
            'insights': insights,
            'sugestoes_priorizadas': sugestoes
        }

    def _agrupar_por_padrao(self, perguntas) -> List[Dict]:
        """Agrupa perguntas por padrão semântico."""
        grupos = defaultdict(list)
        nao_classificadas = []

        for pergunta in perguntas:
            texto = pergunta.consulta.lower()
            classificado = False

            for padrao_cfg in self.padroes:
                match = re.search(padrao_cfg['padrao'], texto)
                if match:
                    grupos[padrao_cfg['nome']].append({
                        'id': pergunta.id,
                        'consulta': pergunta.consulta,
                        'motivo': pergunta.motivo_falha,
                        'match_grupos': match.groups(),
                        'criado_em': pergunta.criado_em.isoformat() if pergunta.criado_em else None
                    })
                    classificado = True
                    break

            if not classificado:
                nao_classificadas.append({
                    'id': pergunta.id,
                    'consulta': pergunta.consulta,
                    'motivo': pergunta.motivo_falha
                })

        # Monta resultado
        resultado = []
        for nome_padrao, itens in grupos.items():
            padrao_cfg = next((p for p in self.padroes if p['nome'] == nome_padrao), {})
            resultado.append({
                'padrao': nome_padrao,
                'template': padrao_cfg.get('template', nome_padrao),
                'sugestao': padrao_cfg.get('sugestao', ''),
                'total': len(itens),
                'exemplos': itens[:5],  # Limita exemplos
                'prioridade': self._calcular_prioridade(len(itens))
            })

        # Adiciona não classificadas
        if nao_classificadas:
            resultado.append({
                'padrao': 'outros',
                'template': 'Perguntas não classificadas',
                'sugestao': 'Analisar manualmente para identificar padrões',
                'total': len(nao_classificadas),
                'exemplos': nao_classificadas[:5],
                'prioridade': 'baixa'
            })

        # Ordena por total (mais frequentes primeiro)
        resultado.sort(key=lambda x: x['total'], reverse=True)

        return resultado

    def _calcular_prioridade(self, total: int) -> str:
        """Calcula prioridade baseada na frequência."""
        if total >= 10:
            return 'critica'
        elif total >= 5:
            return 'alta'
        elif total >= 3:
            return 'media'
        return 'baixa'

    def _gerar_insights(self, perguntas, grupos: List[Dict]) -> List[str]:
        """Gera insights da análise."""
        insights = []

        # Total de perguntas
        insights.append(f"Total de {len(perguntas)} perguntas não respondidas analisadas")

        # Grupos críticos
        criticos = [g for g in grupos if g['prioridade'] == 'critica']
        if criticos:
            nomes = ", ".join(g['template'] for g in criticos)
            insights.append(f"🚨 {len(criticos)} padrão(ões) crítico(s): {nomes}")

        # Motivos mais comuns
        motivos = defaultdict(int)
        for p in perguntas:
            motivos[p.motivo_falha] += 1

        motivo_principal = max(motivos.items(), key=lambda x: x[1])
        insights.append(f"Motivo de falha mais comum: {motivo_principal[0]} ({motivo_principal[1]}x)")

        # Padrões compostos
        compostas = sum(1 for p in perguntas if p.tipo_pergunta == 'composta')
        if compostas > 0:
            pct = (compostas / len(perguntas)) * 100
            insights.append(f"{pct:.0f}% das perguntas são compostas (cliente + condição)")

        return insights

    def _priorizar_sugestoes(self, grupos: List[Dict]) -> List[Dict]:
        """Prioriza sugestões de implementação."""
        sugestoes = []

        for grupo in grupos:
            if grupo['padrao'] == 'outros':
                continue

            # Calcula score de impacto
            score = grupo['total'] * 10
            if grupo['prioridade'] == 'critica':
                score *= 2
            elif grupo['prioridade'] == 'alta':
                score *= 1.5

            sugestoes.append({
                'padrao': grupo['padrao'],
                'acao': grupo['sugestao'],
                'impacto': f"Resolveria ~{grupo['total']} perguntas",
                'score': score,
                'exemplos': [e['consulta'] for e in grupo['exemplos'][:3]]
            })

        # Ordena por score
        sugestoes.sort(key=lambda x: x['score'], reverse=True)

        return sugestoes[:5]  # Top 5

    def sugerir_loader_para_padrao(self, padrao_nome: str) -> Optional[Dict]:
        """
        Sugere estrutura de loader para um padrão específico.

        Args:
            padrao_nome: Nome do padrão (ex: 'cliente_sem_condicao')

        Returns:
            Sugestão de loader em formato JSON
        """
        templates_loader = {
            'cliente_sem_condicao': {
                'modelo_base': 'Separacao',
                'filtros': [
                    {'campo': 'raz_social_red', 'operador': 'ilike', 'valor': '$cliente'},
                    {'campo': '$campo_condicao', 'operador': 'is_null'},
                    {'campo': 'sincronizado_nf', 'operador': '==', 'valor': False}
                ],
                'campos_retorno': ['num_pedido', 'raz_social_red', '$campo_condicao', 'qtd_saldo', 'valor_saldo'],
                'ordenar': [{'campo': 'num_pedido', 'direcao': 'asc'}],
                'limite': 100
            },
            'lista_atrasados': {
                'modelo_base': 'Separacao',
                'filtros': [
                    {'campo': 'expedicao', 'operador': '<', 'valor': '$hoje'},
                    {'campo': 'sincronizado_nf', 'operador': '==', 'valor': False}
                ],
                'campos_retorno': ['num_pedido', 'raz_social_red', 'expedicao', 'qtd_saldo'],
                'ordenar': [{'campo': 'expedicao', 'direcao': 'asc'}],
                'limite': 100
            },
            'total_por_rota': {
                'modelo_base': 'Separacao',
                'filtros': [
                    {'campo': 'rota', 'operador': '==', 'valor': '$rota'},
                    {'campo': 'sincronizado_nf', 'operador': '==', 'valor': False}
                ],
                'agregacao': {
                    'tipo': 'agrupar',
                    'por': ['rota'],
                    'funcoes': [
                        {'func': 'sum', 'campo': 'qtd_saldo', 'alias': 'total_qtd'},
                        {'func': 'sum', 'campo': 'valor_saldo', 'alias': 'total_valor'},
                        {'func': 'count', 'alias': 'total_pedidos'}
                    ]
                },
                'limite': 50
            }
        }

        return templates_loader.get(padrao_nome)

    def marcar_como_analisado(self, ids: List[int], notas: str = None) -> int:
        """
        Marca perguntas como analisadas.

        Args:
            ids: Lista de IDs das perguntas
            notas: Notas opcionais da análise

        Returns:
            Número de registros atualizados
        """
        from ..models import ClaudePerguntaNaoRespondida
        from app import db

        atualizados = 0
        for id_pergunta in ids:
            pergunta = ClaudePerguntaNaoRespondida.query.get(id_pergunta)
            if pergunta:
                pergunta.status = 'analisado'
                pergunta.analisado_em = datetime.now()
                if notas:
                    pergunta.notas_analise = notas
                atualizados += 1

        db.session.commit()
        return atualizados


# Singleton
_service: Optional[FeedbackLoopService] = None


def get_feedback_service() -> FeedbackLoopService:
    """Retorna instância do serviço."""
    global _service
    if _service is None:
        _service = FeedbackLoopService()
    return _service


def analisar_gaps(dias: int = 7) -> Dict[str, Any]:
    """Função de conveniência para análise."""
    return get_feedback_service().analisar_perguntas_recentes(dias)
