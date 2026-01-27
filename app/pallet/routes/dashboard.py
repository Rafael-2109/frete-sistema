"""
Routes do Dashboard de Pallets v2

Dashboard principal com 3 tabs:
- Tab 1: NFs de Remessa (ponto de partida)
- Tab 2: Controle dos Pallets (Domínio A)
- Tab 3: Tratativa das NFs (Domínio B)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
import logging
from datetime import date, timedelta

from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.pallet.models import (
    PalletNFRemessa, PalletCredito, PalletDocumento,
    PalletSolucao, PalletNFSolucao
)
from app.pallet.services import CreditoService

logger = logging.getLogger(__name__)

# Sub-blueprint para dashboard
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """
    Dashboard principal de Gestão de Pallets v2.

    Exibe:
    - Cards de resumo geral
    - 3 tabs principais (NFs Remessa, Controle Pallets, Tratativa NFs)
    - Ações rápidas
    """
    hoje = date.today()

    # =====================================================
    # ESTATÍSTICAS GERAIS (Cards no topo)
    # =====================================================

    # Total de pallets em terceiros (soma dos saldos pendentes)
    total_em_terceiros = db.session.query(
        func.coalesce(func.sum(PalletCredito.qtd_saldo), 0)
    ).filter(
        PalletCredito.ativo == True,
        PalletCredito.status != 'RESOLVIDO'
    ).scalar() or 0

    # Total de créditos pendentes de solução
    creditos_pendentes = PalletCredito.query.filter(
        PalletCredito.ativo == True,
        PalletCredito.status.in_(['PENDENTE', 'PARCIAL'])
    ).count()

    # NFs pendentes de vinculação (Domínio B)
    nfs_pendentes_vinculacao = PalletNFRemessa.query.filter(
        PalletNFRemessa.ativo == True,
        PalletNFRemessa.status == 'ATIVA'
    ).count()

    # Vales/canhotos próximos do vencimento (7 dias)
    creditos_proximos_vencer = CreditoService.listar_vencimentos_proximos(dias=7)

    # =====================================================
    # TAB 1: NFs DE REMESSA
    # =====================================================

    # NFs ativas com status
    nfs_ativas = PalletNFRemessa.query.filter(
        PalletNFRemessa.ativo == True,
        PalletNFRemessa.status == 'ATIVA'
    ).order_by(PalletNFRemessa.data_emissao.desc()).limit(20).all()

    # NFs resolvidas (últimas 10)
    nfs_resolvidas = PalletNFRemessa.query.filter(
        PalletNFRemessa.ativo == True,
        PalletNFRemessa.status == 'RESOLVIDA'
    ).order_by(PalletNFRemessa.atualizado_em.desc()).limit(10).all()

    # NFs canceladas (últimas 10)
    nfs_canceladas = PalletNFRemessa.query.filter(
        PalletNFRemessa.ativo == True,
        PalletNFRemessa.status == 'CANCELADA'
    ).order_by(PalletNFRemessa.cancelada_em.desc()).limit(10).all()

    stats_nf_remessa = {
        'total_ativas': len(nfs_ativas),
        'total_resolvidas': PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'RESOLVIDA'
        ).count(),
        'total_canceladas': PalletNFRemessa.query.filter(
            PalletNFRemessa.ativo == True,
            PalletNFRemessa.status == 'CANCELADA'
        ).count()
    }

    # =====================================================
    # TAB 2: CONTROLE DOS PALLETS (Domínio A)
    # =====================================================

    # Créditos por status
    creditos_por_status = db.session.query(
        PalletCredito.status,
        func.count(PalletCredito.id).label('quantidade'),
        func.sum(PalletCredito.qtd_saldo).label('saldo_total')
    ).filter(
        PalletCredito.ativo == True
    ).group_by(PalletCredito.status).all()

    stats_creditos = {
        'pendentes': 0,
        'parciais': 0,
        'resolvidos': 0,
        'saldo_pendente': 0,
        'saldo_parcial': 0
    }
    for row in creditos_por_status:
        if row.status == 'PENDENTE':
            stats_creditos['pendentes'] = row.quantidade
            stats_creditos['saldo_pendente'] = row.saldo_total or 0
        elif row.status == 'PARCIAL':
            stats_creditos['parciais'] = row.quantidade
            stats_creditos['saldo_parcial'] = row.saldo_total or 0
        elif row.status == 'RESOLVIDO':
            stats_creditos['resolvidos'] = row.quantidade

    # Documentos por status
    docs_pendentes = PalletDocumento.query.filter(
        PalletDocumento.ativo == True,
        PalletDocumento.recebido == False
    ).count()

    docs_recebidos = PalletDocumento.query.filter(
        PalletDocumento.ativo == True,
        PalletDocumento.recebido == True
    ).count()

    # Soluções recentes (últimos 30 dias)
    inicio_mes = hoje - timedelta(days=30)
    solucoes_recentes = db.session.query(
        PalletSolucao.tipo,
        func.count(PalletSolucao.id).label('quantidade'),
        func.sum(PalletSolucao.quantidade).label('qtd_total')
    ).filter(
        PalletSolucao.ativo == True,
        PalletSolucao.criado_em >= inicio_mes
    ).group_by(PalletSolucao.tipo).all()

    stats_solucoes_mes = {
        'BAIXA': {'count': 0, 'qtd': 0},
        'VENDA': {'count': 0, 'qtd': 0},
        'RECEBIMENTO': {'count': 0, 'qtd': 0},
        'SUBSTITUICAO': {'count': 0, 'qtd': 0}
    }
    for row in solucoes_recentes:
        if row.tipo in stats_solucoes_mes:
            stats_solucoes_mes[row.tipo] = {
                'count': row.quantidade,
                'qtd': row.qtd_total or 0
            }

    # =====================================================
    # TAB 3: TRATATIVA DAS NFs (Domínio B)
    # =====================================================

    # Soluções de NF por tipo
    nf_solucoes_por_tipo = db.session.query(
        PalletNFSolucao.tipo,
        func.count(PalletNFSolucao.id).label('quantidade'),
        func.sum(PalletNFSolucao.quantidade).label('qtd_total')
    ).filter(
        PalletNFSolucao.ativo == True
    ).group_by(PalletNFSolucao.tipo).all()

    stats_nf_solucoes = {
        'DEVOLUCAO': {'count': 0, 'qtd': 0},
        'RECUSA': {'count': 0, 'qtd': 0},
        'CANCELAMENTO': {'count': 0, 'qtd': 0},
        'NOTA_CREDITO': {'count': 0, 'qtd': 0}
    }
    for row in nf_solucoes_por_tipo:
        if row.tipo in stats_nf_solucoes:
            stats_nf_solucoes[row.tipo] = {
                'count': row.quantidade,
                'qtd': row.qtd_total or 0
            }

    # Sugestões pendentes de confirmação (usa confirmado=False, não confirmado_em IS NULL)
    sugestoes_pendentes = PalletNFSolucao.query.filter(
        PalletNFSolucao.ativo == True,
        PalletNFSolucao.vinculacao == 'SUGESTAO',
        PalletNFSolucao.confirmado == False,
        PalletNFSolucao.rejeitado == False
    ).count()

    return render_template(
        'pallet/v2/dashboard.html',
        # Gerais
        total_em_terceiros=int(total_em_terceiros),
        creditos_pendentes=creditos_pendentes,
        nfs_pendentes_vinculacao=nfs_pendentes_vinculacao,
        creditos_proximos_vencer=creditos_proximos_vencer,

        # Tab 1: NFs Remessa
        nfs_ativas=nfs_ativas,
        nfs_resolvidas=nfs_resolvidas,
        nfs_canceladas=nfs_canceladas,
        stats_nf_remessa=stats_nf_remessa,

        # Tab 2: Controle Pallets
        stats_creditos=stats_creditos,
        docs_pendentes=docs_pendentes,
        docs_recebidos=docs_recebidos,
        stats_solucoes_mes=stats_solucoes_mes,

        # Tab 3: Tratativa NFs
        stats_nf_solucoes=stats_nf_solucoes,
        sugestoes_pendentes=sugestoes_pendentes
    )


@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """
    API para obter estatísticas do dashboard em JSON.

    Retorna dados atualizados para refresh via AJAX.
    """
    hoje = date.today()

    # Total de pallets em terceiros
    total_em_terceiros = db.session.query(
        func.coalesce(func.sum(PalletCredito.qtd_saldo), 0)
    ).filter(
        PalletCredito.ativo == True,
        PalletCredito.status != 'RESOLVIDO'
    ).scalar() or 0

    # Créditos por status
    creditos_por_status = db.session.query(
        PalletCredito.status,
        func.count(PalletCredito.id).label('quantidade'),
        func.sum(PalletCredito.qtd_saldo).label('saldo_total')
    ).filter(
        PalletCredito.ativo == True
    ).group_by(PalletCredito.status).all()

    stats_creditos = {}
    for row in creditos_por_status:
        stats_creditos[row.status] = {
            'count': row.quantidade,
            'saldo': int(row.saldo_total or 0)
        }

    # NFs por status
    nfs_por_status = db.session.query(
        PalletNFRemessa.status,
        func.count(PalletNFRemessa.id).label('quantidade')
    ).filter(
        PalletNFRemessa.ativo == True
    ).group_by(PalletNFRemessa.status).all()

    stats_nfs = {}
    for row in nfs_por_status:
        stats_nfs[row.status] = row.quantidade

    # Sugestões pendentes (usa confirmado=False, não confirmado_em IS NULL)
    sugestoes_pendentes = PalletNFSolucao.query.filter(
        PalletNFSolucao.ativo == True,
        PalletNFSolucao.vinculacao == 'SUGESTAO',
        PalletNFSolucao.confirmado == False,
        PalletNFSolucao.rejeitado == False
    ).count()

    return jsonify({
        'total_em_terceiros': int(total_em_terceiros),
        'creditos': stats_creditos,
        'nfs': stats_nfs,
        'sugestoes_pendentes': sugestoes_pendentes
    })


@dashboard_bp.route('/api/creditos-vencendo')
@login_required
def api_creditos_vencendo():
    """
    API para listar créditos próximos do vencimento.

    Query params:
    - dias: número de dias para considerar (default: 7)
    """
    from flask import request
    dias = request.args.get('dias', 7, type=int)

    creditos = CreditoService.listar_vencimentos_proximos(dias=dias)

    return jsonify([{
        'id': c.id,
        'nf_remessa_id': c.nf_remessa_id,
        'numero_nf': c.nf_remessa.numero_nf if c.nf_remessa else None,
        'qtd_saldo': c.qtd_saldo,
        'responsavel': c.nome_responsavel,
        'cnpj': c.cnpj_responsavel,
        'data_vencimento': c.data_vencimento.isoformat() if c.data_vencimento else None,
        'dias_para_vencer': (c.data_vencimento - date.today()).days if c.data_vencimento else None
    } for c in creditos])
