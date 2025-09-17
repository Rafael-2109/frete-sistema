"""
Módulo de análise de ruptura para programação em lote
Funções relacionadas à análise de estoque e projeção de ruptura
"""

from typing import Dict, Any, List
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_
import logging

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.estoque.models import MovimentacaoEstoque
from app.producao.models import ProgramacaoProducao

logger = logging.getLogger(__name__)


def analisar_ruptura_lote(cnpjs: List[str], data_agendamento: date) -> Dict[str, Any]:
    """
    Analisa ruptura de estoque para múltiplos CNPJs

    Args:
        cnpjs: Lista de CNPJs para análise
        data_agendamento: Data de agendamento proposta

    Returns:
        Dicionário com análise de ruptura por produto
    """
    try:
        resultado = {
            'produtos_em_ruptura': [],
            'produtos_criticos': [],
            'produtos_ok': [],
            'total_analisado': 0,
            'data_analise': datetime.now().isoformat()
        }

        # Buscar todos os produtos dos CNPJs
        produtos = _buscar_produtos_cnpjs(cnpjs)
        resultado['total_analisado'] = len(produtos)

        for produto in produtos:
            analise = _analisar_produto_ruptura(
                produto['cod_produto'],
                produto['quantidade_total'],
                data_agendamento
            )

            if analise['status'] == 'ruptura':
                resultado['produtos_em_ruptura'].append(analise)
            elif analise['status'] == 'critico':
                resultado['produtos_criticos'].append(analise)
            else:
                resultado['produtos_ok'].append(analise)

        return resultado

    except Exception as e:
        logger.error(f"Erro ao analisar ruptura: {e}")
        return {
            'erro': str(e),
            'produtos_em_ruptura': [],
            'produtos_criticos': [],
            'produtos_ok': []
        }


def _buscar_produtos_cnpjs(cnpjs: List[str]) -> List[Dict[str, Any]]:
    """
    Busca produtos consolidados dos CNPJs
    """
    produtos = {}

    # Buscar da CarteiraPrincipal
    carteira_items = db.session.query(
        CarteiraPrincipal.cod_produto,
        CarteiraPrincipal.nome_produto,
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('quantidade')
    ).filter(
        and_(
            CarteiraPrincipal.cnpj_cpf.in_(cnpjs),
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )
    ).group_by(
        CarteiraPrincipal.cod_produto,
        CarteiraPrincipal.nome_produto
    ).all()

    for item in carteira_items:
        if item.cod_produto not in produtos:
            produtos[item.cod_produto] = {
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'quantidade_total': 0
            }
        produtos[item.cod_produto]['quantidade_total'] += float(item.quantidade or 0)

    # Buscar de Separacao não faturada
    separacao_items = db.session.query(
        Separacao.cod_produto,
        func.sum(Separacao.qtd_saldo).label('quantidade')
    ).filter(
        and_(
            Separacao.cnpj_cpf.in_(cnpjs),
            Separacao.sincronizado_nf == False,
        )
    ).group_by(
        Separacao.cod_produto
    ).all()

    for item in separacao_items:
        if item.cod_produto not in produtos:
            produtos[item.cod_produto] = {
                'cod_produto': item.cod_produto,
                'nome_produto': f"Produto {item.cod_produto}",
                'quantidade_total': 0
            }
        produtos[item.cod_produto]['quantidade_total'] += float(item.quantidade or 0)

    return list(produtos.values())


def _analisar_produto_ruptura(cod_produto: str, quantidade_necessaria: float,
                              data_agendamento: date) -> Dict[str, Any]:
    """
    Analisa ruptura de um produto específico
    """
    # Buscar estoque atual
    estoque_atual = _buscar_estoque_atual(cod_produto)

    # Buscar projeção de saídas até a data
    saidas_projetadas = _calcular_saidas_projetadas(cod_produto, date.today(), data_agendamento)

    # Buscar projeção de entradas (produção)
    entradas_projetadas = _calcular_entradas_projetadas(cod_produto, date.today(), data_agendamento)

    # Calcular estoque projetado
    estoque_projetado = estoque_atual + entradas_projetadas - saidas_projetadas - quantidade_necessaria

    # Determinar status
    if estoque_projetado < 0:
        status = 'ruptura'
    elif estoque_projetado < quantidade_necessaria * 0.2:  # Menos de 20% de margem
        status = 'critico'
    else:
        status = 'ok'

    return {
        'cod_produto': cod_produto,
        'quantidade_necessaria': quantidade_necessaria,
        'estoque_atual': estoque_atual,
        'saidas_projetadas': saidas_projetadas,
        'entradas_projetadas': entradas_projetadas,
        'estoque_projetado': estoque_projetado,
        'status': status,
        'falta': max(0, -estoque_projetado) if estoque_projetado < 0 else 0
    }


def _buscar_estoque_atual(cod_produto: str) -> float:
    """
    Busca estoque atual do produto
    """
    try:
        # Buscar última movimentação para ter o saldo
        ultima_mov = db.session.query(
            MovimentacaoEstoque.saldo_atual
        ).filter(
            MovimentacaoEstoque.cod_produto == cod_produto
        ).order_by(
            MovimentacaoEstoque.data_movimento.desc()
        ).first()

        if ultima_mov:
            return float(ultima_mov.saldo_atual or 0)

        # Se não houver movimentação, buscar do estoque inicial
        # ou considerar 0
        return 0.0

    except Exception as e:
        logger.error(f"Erro ao buscar estoque de {cod_produto}: {e}")
        return 0.0


def _calcular_saidas_projetadas(cod_produto: str, data_inicio: date, data_fim: date) -> float:
    """
    Calcula saídas projetadas de estoque
    INCLUI ITENS ATRASADOS (expedicao < hoje)
    """
    try:
        hoje = date.today()

        # Buscar pedidos em carteira (incluindo ATRASADOS)
        # Pedidos atrasados
        carteira_atrasada = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
        ).filter(
            and_(
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.expedicao < hoje  # ATRASADOS
            )
        ).scalar()

        # Pedidos no período
        carteira = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
        ).filter(
            and_(
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.expedicao >= data_inicio,
                CarteiraPrincipal.expedicao <= data_fim
            )
        ).scalar()

        # Buscar separações não faturadas (incluindo ATRASADAS)
        # Separações atrasadas
        separacao_atrasada = db.session.query(
            func.sum(Separacao.qtd_saldo)
        ).filter(
            and_(
                Separacao.cod_produto == cod_produto,
                Separacao.sincronizado_nf == False,
                Separacao.expedicao < hoje  # ATRASADAS
            )
        ).scalar()

        # Separações no período
        separacao = db.session.query(
            func.sum(Separacao.qtd_saldo)
        ).filter(
            and_(
                Separacao.cod_produto == cod_produto,
                Separacao.sincronizado_nf == False,
                Separacao.expedicao >= data_inicio,
                Separacao.expedicao <= data_fim
            )
        ).scalar()

        # Somar tudo: atrasados + período
        total = (
            float(carteira_atrasada or 0) +
            float(carteira or 0) +
            float(separacao_atrasada or 0) +
            float(separacao or 0)
        )

        if float(carteira_atrasada or 0) > 0 or float(separacao_atrasada or 0) > 0:
            logger.info(f"[RUPTURA] Produto {cod_produto}: Incluindo atrasados - "
                       f"Carteira: {float(carteira_atrasada or 0):.2f}, "
                       f"Separação: {float(separacao_atrasada or 0):.2f}")

        return total

    except Exception as e:
        logger.error(f"Erro ao calcular saídas de {cod_produto}: {e}")
        return 0.0


def _calcular_entradas_projetadas(cod_produto: str, data_inicio: date, data_fim: date) -> float:
    """
    Calcula entradas projetadas (produção programada)
    """
    try:
        producao = db.session.query(
            func.sum(ProgramacaoProducao.quantidade_programada)
        ).filter(
            and_(
                ProgramacaoProducao.cod_produto == cod_produto,
                ProgramacaoProducao.data_producao >= data_inicio,
                ProgramacaoProducao.data_producao <= data_fim,
                ProgramacaoProducao.status.in_(['programado', 'em_producao'])
            )
        ).scalar()

        return float(producao or 0)

    except Exception as e:
        logger.error(f"Erro ao calcular entradas de {cod_produto}: {e}")
        return 0.0


def sugerir_data_sem_ruptura(cnpjs: List[str], data_inicial: date = None) -> Dict[str, Any]:
    """
    Sugere datas de agendamento sem ruptura

    Args:
        cnpjs: Lista de CNPJs
        data_inicial: Data inicial para busca (padrão: hoje + 2 dias úteis)

    Returns:
        Dicionário com sugestões de datas
    """
    if not data_inicial:
        data_inicial = date.today() + timedelta(days=2)
        # Ajustar para dia útil
        while data_inicial.weekday() >= 5:
            data_inicial += timedelta(days=1)

    resultado = {
        'data_inicial_analisada': data_inicial,
        'sugestoes': [],
        'analise_completa': []
    }

    # Analisar próximos 10 dias úteis
    data_teste = data_inicial
    dias_analisados = 0

    while dias_analisados < 10:
        if data_teste.weekday() < 5:  # Dia útil
            analise = analisar_ruptura_lote(cnpjs, data_teste)

            info_dia = {
                'data': data_teste,
                'produtos_em_ruptura': len(analise.get('produtos_em_ruptura', [])),
                'produtos_criticos': len(analise.get('produtos_criticos', [])),
                'viavel': len(analise.get('produtos_em_ruptura', [])) == 0
            }

            resultado['analise_completa'].append(info_dia)

            if info_dia['viavel']:
                resultado['sugestoes'].append(data_teste)

            dias_analisados += 1

        data_teste += timedelta(days=1)

    return resultado