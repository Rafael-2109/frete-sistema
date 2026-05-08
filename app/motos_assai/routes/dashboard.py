from flask import render_template
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda,
    AssaiCompraMotochefe, AssaiSeparacao,
    PEDIDO_STATUS_VALIDOS,
)
from app import db
from sqlalchemy import func


@motos_assai_bp.route('/')
@login_required
@require_motos_assai
def dashboard():
    """Dashboard inicial — métricas básicas. Será enriquecido nos Planos 2 e 3."""
    cd = AssaiCd.query.filter_by(ativo=True).first()
    lojas_ativas = AssaiLoja.query.filter_by(ativo=True).count()
    modelos_ativos = AssaiModelo.query.filter_by(ativo=True).count()

    # Counts por status (placeholder — vazio até Plano 2)
    pedidos_por_status = dict(
        db.session.query(AssaiPedidoVenda.status, func.count(AssaiPedidoVenda.id))
        .group_by(AssaiPedidoVenda.status)
        .all()
    )
    compras_abertas = AssaiCompraMotochefe.query.filter_by(status='ABERTA').count()
    separacoes_em = AssaiSeparacao.query.filter_by(status='EM_SEPARACAO').count()

    return render_template(
        'motos_assai/dashboard.html',
        cd=cd,
        lojas_ativas=lojas_ativas,
        modelos_ativos=modelos_ativos,
        pedidos_por_status=pedidos_por_status,
        compras_abertas=compras_abertas,
        separacoes_em=separacoes_em,
    )
