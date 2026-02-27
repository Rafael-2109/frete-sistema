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
)

logger = logging.getLogger(__name__)


def register_dashboard_routes(bp):

    @bp.route('/')
    @bp.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard principal do CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import flash, redirect, url_for
            flash('Acesso negado. Voce nao tem permissao para o sistema CarVia.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Estatisticas
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
                'ultimas_operacoes': [],
            }

        return render_template('carvia/dashboard.html', stats=stats)
