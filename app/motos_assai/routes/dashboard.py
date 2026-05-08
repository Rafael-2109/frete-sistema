from flask import render_template
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda,
    AssaiCompraMotochefe, AssaiSeparacao, AssaiMotoEvento,
    PEDIDO_STATUS_VALIDOS,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA,
)
from app import db
from sqlalchemy import func


@motos_assai_bp.route('/')
@login_required
@require_motos_assai
def dashboard():
    """Dashboard principal — métricas completas do pipeline Motos Assaí."""
    cd = AssaiCd.query.filter_by(ativo=True).first()
    lojas_ativas = AssaiLoja.query.filter_by(ativo=True).count()
    modelos_ativos = AssaiModelo.query.filter_by(ativo=True).count()

    # Counts de pedido/compra/separação
    pedidos_por_status = dict(
        db.session.query(AssaiPedidoVenda.status, func.count(AssaiPedidoVenda.id))
        .group_by(AssaiPedidoVenda.status)
        .all()
    )
    compras_abertas = AssaiCompraMotochefe.query.filter_by(status='ABERTA').count()
    separacoes_em = AssaiSeparacao.query.filter_by(status='EM_SEPARACAO').count()

    # Estoque por status efetivo (tipo do último evento por chassi)
    sub = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )
    estoque_por_status = dict(
        db.session.query(AssaiMotoEvento.tipo, func.count(AssaiMotoEvento.id))
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .group_by(AssaiMotoEvento.tipo)
        .all()
    )

    return render_template(
        'motos_assai/dashboard.html',
        cd=cd,
        lojas_ativas=lojas_ativas,
        modelos_ativos=modelos_ativos,
        pedidos_por_status=pedidos_por_status,
        compras_abertas=compras_abertas,
        separacoes_em=separacoes_em,
        estoque_por_status=estoque_por_status,
        EVENTO_ESTOQUE=EVENTO_ESTOQUE,
        EVENTO_MONTADA=EVENTO_MONTADA,
        EVENTO_PENDENTE=EVENTO_PENDENTE,
        EVENTO_DISPONIVEL=EVENTO_DISPONIVEL,
        EVENTO_SEPARADA=EVENTO_SEPARADA,
    )
