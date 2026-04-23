"""Dashboard HORA — visão geral de estoque, recebimentos pendentes, vendas recentes."""
from __future__ import annotations

from flask import render_template
from app.hora.decorators import require_hora_perm
from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraLoja,
    HoraMoto,
    HoraMotoEvento,
    HoraPedido,
    HoraNfEntrada,
    HoraRecebimento,
)
from app.hora.routes import hora_bp


@hora_bp.route('/')
@require_hora_perm('dashboard', 'ver')
def dashboard():
    """Dashboard do módulo HORA."""
    total_motos = db.session.query(func.count(HoraMoto.numero_chassi)).scalar() or 0
    total_lojas = db.session.query(func.count(HoraLoja.id)).filter_by(ativa=True).scalar() or 0
    total_pedidos_abertos = (
        db.session.query(func.count(HoraPedido.id))
        .filter(HoraPedido.status.in_(['ABERTO', 'PARCIALMENTE_FATURADO']))
        .scalar() or 0
    )
    total_nfs = db.session.query(func.count(HoraNfEntrada.id)).scalar() or 0
    total_recebimentos_em_conferencia = (
        db.session.query(func.count(HoraRecebimento.id))
        .filter_by(status='EM_CONFERENCIA')
        .scalar() or 0
    )
    total_recebimentos_com_divergencia = (
        db.session.query(func.count(HoraRecebimento.id))
        .filter_by(status='COM_DIVERGENCIA')
        .scalar() or 0
    )

    eventos_recentes = (
        HoraMotoEvento.query
        .order_by(HoraMotoEvento.timestamp.desc())
        .limit(20)
        .all()
    )

    return render_template(
        'hora/dashboard.html',
        total_motos=total_motos,
        total_lojas=total_lojas,
        total_pedidos_abertos=total_pedidos_abertos,
        total_nfs=total_nfs,
        total_recebimentos_em_conferencia=total_recebimentos_em_conferencia,
        total_recebimentos_com_divergencia=total_recebimentos_com_divergencia,
        eventos_recentes=eventos_recentes,
    )
