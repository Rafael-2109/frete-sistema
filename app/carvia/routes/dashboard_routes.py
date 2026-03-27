"""
Dashboard CarVia — Visao geral das operacoes
"""

import logging
from flask import render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import (
    CarviaNf, CarviaOperacao, CarviaSubcontrato,
    CarviaFaturaCliente, CarviaFaturaTransportadora,
    CarviaDespesa, CarviaReceita,
)

logger = logging.getLogger(__name__)


def register_dashboard_routes(bp):

    @bp.route('/') # type: ignore
    @bp.route('/dashboard') # type: ignore
    @login_required
    def dashboard(): # type: ignore
        """Dashboard principal do CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import flash, redirect, url_for
            flash('Acesso negado. Voce nao tem permissao para o sistema CarVia.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Estatisticas basicas (COUNTs simples)
        stats = {}
        try:
            # NFs Venda
            stats['total_nfs'] = db.session.query(
                func.count(CarviaNf.id)
            ).scalar() or 0

            # CTes CarVia (Operacoes)
            stats['total_operacoes'] = db.session.query(
                func.count(CarviaOperacao.id)
            ).scalar() or 0

            stats['operacoes_rascunho'] = db.session.query(
                func.count(CarviaOperacao.id)
            ).filter(CarviaOperacao.status == 'RASCUNHO').scalar() or 0

            stats['operacoes_cotadas'] = db.session.query(
                func.count(CarviaOperacao.id)
            ).filter(CarviaOperacao.status == 'COTADO').scalar() or 0

            stats['operacoes_confirmadas'] = db.session.query(
                func.count(CarviaOperacao.id)
            ).filter(CarviaOperacao.status == 'CONFIRMADO').scalar() or 0

            # CTes Subcontrato
            stats['total_subcontratos'] = db.session.query(
                func.count(CarviaSubcontrato.id)
            ).scalar() or 0

            stats['subcontratos_pendentes'] = db.session.query(
                func.count(CarviaSubcontrato.id)
            ).filter(CarviaSubcontrato.status == 'PENDENTE').scalar() or 0

            stats['subcontratos_cotados'] = db.session.query(
                func.count(CarviaSubcontrato.id)
            ).filter(CarviaSubcontrato.status == 'COTADO').scalar() or 0

            # Faturas
            stats['faturas_carvia_pendentes'] = db.session.query(
                func.count(CarviaFaturaCliente.id)
            ).filter(CarviaFaturaCliente.status == 'PENDENTE').scalar() or 0

            stats['faturas_sub_pendentes'] = db.session.query(
                func.count(CarviaFaturaTransportadora.id)
            ).filter(CarviaFaturaTransportadora.status_conferencia == 'PENDENTE').scalar() or 0

            # Despesas
            stats['despesas_pendentes'] = db.session.query(
                func.count(CarviaDespesa.id)
            ).filter(CarviaDespesa.status == 'PENDENTE').scalar() or 0

            stats['despesas_valor_pendente'] = db.session.query(
                func.coalesce(func.sum(CarviaDespesa.valor), 0)
            ).filter(CarviaDespesa.status == 'PENDENTE').scalar() or 0

            # Receitas
            stats['receitas_pendentes'] = db.session.query(
                func.count(CarviaReceita.id)
            ).filter(CarviaReceita.status == 'PENDENTE').scalar() or 0

            stats['receitas_valor_pendente'] = db.session.query(
                func.coalesce(func.sum(CarviaReceita.valor), 0)
            ).filter(CarviaReceita.status == 'PENDENTE').scalar() or 0

            # Vencidos e vencendo hoje (padrao do context processor em app/__init__.py:968-999)
            from app.utils.timezone import agora_brasil_naive
            hoje = agora_brasil_naive().date()

            venc_cli = db.session.query(func.count(CarviaFaturaCliente.id)).filter(
                CarviaFaturaCliente.vencimento < hoje,
                CarviaFaturaCliente.status.notin_(['PAGA', 'CANCELADA']),
            ).scalar() or 0

            venc_transp = db.session.query(func.count(CarviaFaturaTransportadora.id)).filter(
                CarviaFaturaTransportadora.vencimento < hoje,
                CarviaFaturaTransportadora.status_pagamento == 'PENDENTE',
            ).scalar() or 0

            venc_desp = db.session.query(func.count(CarviaDespesa.id)).filter(
                CarviaDespesa.data_vencimento < hoje,
                CarviaDespesa.status == 'PENDENTE',
            ).scalar() or 0

            stats['vencidos_total'] = venc_cli + venc_transp + venc_desp

            dia_cli = db.session.query(func.count(CarviaFaturaCliente.id)).filter(
                CarviaFaturaCliente.vencimento == hoje,
                CarviaFaturaCliente.status.notin_(['PAGA', 'CANCELADA']),
            ).scalar() or 0

            dia_transp = db.session.query(func.count(CarviaFaturaTransportadora.id)).filter(
                CarviaFaturaTransportadora.vencimento == hoje,
                CarviaFaturaTransportadora.status_pagamento == 'PENDENTE',
            ).scalar() or 0

            dia_desp = db.session.query(func.count(CarviaDespesa.id)).filter(
                CarviaDespesa.data_vencimento == hoje,
                CarviaDespesa.status == 'PENDENTE',
            ).scalar() or 0

            stats['vencimento_hoje_total'] = dia_cli + dia_transp + dia_desp

            # Cotacoes comerciais
            from app.carvia.models import CarviaCotacao
            stats['cotacoes_ativas'] = CarviaCotacao.query.filter(
                CarviaCotacao.status.in_(['RASCUNHO', 'PENDENTE_ADMIN', 'ENVIADO'])
            ).count()

            stats['cotacoes_pendentes_admin'] = CarviaCotacao.query.filter_by(
                status='PENDENTE_ADMIN'
            ).count()

            # Pedidos abertos
            from app.carvia.models import CarviaPedido
            stats['pedidos_abertos'] = CarviaPedido.query.filter(
                CarviaPedido.status == 'ABERTO'
            ).count()

            # Ultimas operacoes
            stats['ultimas_operacoes'] = db.session.query(CarviaOperacao).order_by(
                CarviaOperacao.criado_em.desc()
            ).limit(10).all()

        except Exception as e:
            logger.error(f"Erro ao carregar estatisticas CarVia: {e}")
            stats = {
                'total_nfs': 0,
                'total_operacoes': 0,
                'operacoes_rascunho': 0,
                'operacoes_cotadas': 0,
                'operacoes_confirmadas': 0,
                'total_subcontratos': 0,
                'subcontratos_pendentes': 0,
                'subcontratos_cotados': 0,
                'faturas_carvia_pendentes': 0,
                'faturas_sub_pendentes': 0,
                'despesas_pendentes': 0,
                'despesas_valor_pendente': 0,
                'receitas_pendentes': 0,
                'receitas_valor_pendente': 0,
                'vencidos_total': 0,
                'vencimento_hoje_total': 0,
                'cotacoes_ativas': 0,
                'cotacoes_pendentes_admin': 0,
                'pedidos_abertos': 0,
                'ultimas_operacoes': [],
                'saldo_conta': 0,
            }

        # Saldo da conta (isolado — falha nao zera stats basicas)
        if 'saldo_conta' not in stats:
            try:
                from app.carvia.services.fluxo_caixa_service import FluxoCaixaService
                stats['saldo_conta'] = FluxoCaixaService().obter_saldo_conta() or 0
            except Exception as e:
                logger.warning(f"Erro ao obter saldo conta CarVia: {e}")
                stats['saldo_conta'] = 0

        return render_template('carvia/dashboard.html', stats=stats)
