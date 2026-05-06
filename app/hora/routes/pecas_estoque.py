"""Rotas de Estoque de Pecas (movimentacao)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja, HoraPeca
from app.hora.routes import hora_bp
from app.hora.services import peca_estoque_service, peca_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)


def _operador() -> str:
    if hasattr(current_user, 'nome'):
        return current_user.nome
    return getattr(current_user, 'email', 'desconhecido')


@hora_bp.route('/pecas/estoque')
@require_hora_perm('pecas_estoque', 'ver')
def pecas_estoque_lista():
    permitidas = lojas_permitidas_ids()
    loja_id_str = (request.args.get('loja_id') or '').strip()
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    busca = (request.args.get('busca') or '').strip() or None
    somente_pos = request.args.get('somente_positivo') != '0'

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.pecas_estoque_lista'))

    rows = peca_estoque_service.listar_estoque(
        loja_id=loja_id, busca=busca,
        somente_positivo=somente_pos,
        lojas_permitidas_ids=permitidas,
    )

    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas))
    lojas_ativas = lojas_q.order_by(HoraLoja.nome).all()

    return render_template(
        'hora/pecas_estoque_lista.html',
        rows=rows,
        lojas_ativas=lojas_ativas,
        filtro_loja_id=loja_id,
        filtro_busca=busca,
        filtro_somente_positivo=somente_pos,
    )


@hora_bp.route('/pecas/estoque/<int:peca_id>/<int:loja_id>')
@require_hora_perm('pecas_estoque', 'ver')
def pecas_estoque_detalhe(peca_id: int, loja_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    l = HoraLoja.query.get_or_404(loja_id)
    if not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.pecas_estoque_lista'))

    saldo = peca_estoque_service.saldo(peca_id, loja_id)
    movimentos = peca_estoque_service.historico(peca_id, loja_id, limit=200)
    return render_template(
        'hora/pecas_estoque_detalhe.html',
        peca=p, loja=l, saldo=saldo, movimentos=movimentos,
        foto_url=peca_service.get_foto_url(p),
    )


@hora_bp.route('/pecas/estoque/ajuste', methods=['POST'])
@require_hora_perm('pecas_estoque', 'editar')
def pecas_estoque_ajuste():
    try:
        peca_id = int(request.form.get('peca_id'))
        loja_id = int(request.form.get('loja_id'))
        qtd = Decimal((request.form.get('qtd_signed') or '0').replace(',', '.'))
        motivo = (request.form.get('motivo') or '').strip()
        if not usuario_tem_acesso_a_loja(loja_id):
            flash('Acesso negado a essa loja.', 'danger')
            return redirect(url_for('hora.pecas_estoque_lista'))
        peca_estoque_service.ajuste_manual(
            peca_id=peca_id, loja_id=loja_id,
            qtd_signed=qtd, motivo=motivo, operador=_operador(),
        )
        flash('Ajuste registrado.', 'success')
    except (ValueError, InvalidOperation, TypeError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(request.referrer or url_for('hora.pecas_estoque_lista'))


@hora_bp.route('/pecas/estoque/transferencia', methods=['POST'])
@require_hora_perm('pecas_estoque', 'editar')
def pecas_estoque_transferencia():
    try:
        peca_id = int(request.form.get('peca_id'))
        origem = int(request.form.get('loja_origem_id'))
        destino = int(request.form.get('loja_destino_id'))
        qtd = Decimal((request.form.get('qtd') or '0').replace(',', '.'))
        motivo = (request.form.get('motivo') or '').strip()
        if not usuario_tem_acesso_a_loja(origem):
            flash('Acesso negado a loja origem.', 'danger')
            return redirect(url_for('hora.pecas_estoque_lista'))
        peca_estoque_service.transferencia(
            peca_id=peca_id, loja_origem_id=origem, loja_destino_id=destino,
            qtd=qtd, motivo=motivo, operador=_operador(),
        )
        flash(f'Transferencia de {qtd} pecas realizada.', 'success')
    except (ValueError, InvalidOperation, TypeError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(request.referrer or url_for('hora.pecas_estoque_lista'))


@hora_bp.route('/pecas/estoque/saldo/<int:peca_id>')
@require_hora_perm('pecas_estoque', 'ver')
def pecas_estoque_saldo_json(peca_id: int):
    """JSON com saldo por loja (para autocomplete em wizard de venda)."""
    saldos = peca_estoque_service.saldos_por_loja(peca_id)
    return jsonify({str(k): str(v) for k, v in saldos.items()})
