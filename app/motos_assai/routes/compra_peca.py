"""Rotas de Pedido de Compra de Peça (GARANTIA/COMPRA à Motochefe) — Spec 2 Task 12.

Cria PC-AAAA-NNNN com N itens (peça/quantidade/custo estimado), recebe item a
item (→ ENTRADA no ledger via `movimento_service.registrar_entrada`) e cancela.
`compra_peca_service` faz add+flush SEM commit — a rota controla a transação.
"""
from decimal import InvalidOperation

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm

from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import compra_peca_service, peca_service
from app.motos_assai.services.compra_peca_service import CompraPecaError
from app.motos_assai.services.movimento_service import EstoqueError
from app.motos_assai.models import AssaiPecaCompra

# Erros de conversão numérica que devem virar flash gracioso, não 500.
# `compra_peca_service._decimal` já embrulha `Decimal(str(valor))` em CompraPecaError,
# mas capturamos também InvalidOperation/ValueError como defesa em profundidade
# (mesma classe de bug do Task 10/11 — não confiar cegamente que o service cobre tudo).
_ERROS_ENTRADA_INVALIDA = (CompraPecaError, InvalidOperation, ValueError)

# `receber_item` repassa `custo_unitario` para `movimento_service.registrar_entrada`,
# cujo `_decimal` levanta `EstoqueError` (não `CompraPecaError`) para valor malformado.
# Tupla dedicada só para essa rota — não alarga o catch de `nova`/`cancelar`, que
# nunca tocam `movimento_service` (Task 12 review — fix do 500 em custo malformado).
_ERROS_RECEBER_ITEM = _ERROS_ENTRADA_INVALIDA + (EstoqueError,)


def _br(s):
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


@motos_assai_bp.route('/compras-peca')
@login_required
@require_motos_assai
def compra_peca_lista():
    compras = AssaiPecaCompra.query.order_by(AssaiPecaCompra.id.desc()).all()
    return render_template('motos_assai/compras_pecas/lista.html', compras=compras)


@motos_assai_bp.route('/compras-peca/nova', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def compra_peca_nova():
    if request.method == 'POST':
        peca_ids = request.form.getlist('peca_id', type=int)
        qtds = request.form.getlist('quantidade')
        custos = request.form.getlist('custo_estimado')
        itens = [{'peca_id': pid, 'quantidade': _br(qtds[i]),
                  'custo_estimado': _br(custos[i]) if i < len(custos) else None}
                 for i, pid in enumerate(peca_ids) if pid and i < len(qtds) and _br(qtds[i])]
        try:
            c = compra_peca_service.criar_compra(
                tipo=request.form.get('tipo'), itens=itens,
                operador_id=current_user.id,
                fornecedor=request.form.get('fornecedor') or 'MOTOCHEFE')
            db.session.commit(); flash(f'Compra {c.numero} criada.', 'success')
            return redirect(url_for('motos_assai.compra_peca_detalhe', cid=c.id))
        except _ERROS_ENTRADA_INVALIDA as e:
            db.session.rollback(); flash(str(e), 'danger')
    pecas = peca_service.listar(ativo=True)
    return render_template('motos_assai/compras_pecas/nova.html', pecas=pecas, form=FlaskForm())


@motos_assai_bp.route('/compras-peca/<int:cid>')
@login_required
@require_motos_assai
def compra_peca_detalhe(cid):
    c = db.session.get(AssaiPecaCompra, cid)
    if not c:
        flash('Compra não encontrada.', 'danger')
        return redirect(url_for('motos_assai.compra_peca_lista'))
    return render_template('motos_assai/compras_pecas/detalhe.html', c=c, form=FlaskForm())


@motos_assai_bp.route('/compras-peca/<int:cid>/receber-item', methods=['POST'])
@login_required
@require_motos_assai
def compra_peca_receber_item(cid):
    try:
        compra_peca_service.receber_item(
            compra_item_id=request.form.get('compra_item_id', type=int),
            quantidade=_br(request.form.get('quantidade')),
            custo_unitario=_br(request.form.get('custo_unitario')),
            operador_id=current_user.id)
        db.session.commit(); flash('Item recebido (entrada no estoque).', 'success')
    except _ERROS_RECEBER_ITEM as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(url_for('motos_assai.compra_peca_detalhe', cid=cid))


@motos_assai_bp.route('/compras-peca/<int:cid>/cancelar', methods=['POST'])
@login_required
@require_motos_assai
def compra_peca_cancelar(cid):
    try:
        compra_peca_service.cancelar_compra(compra_id=cid, operador_id=current_user.id)
        db.session.commit(); flash('Compra cancelada.', 'success')
    except CompraPecaError as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(url_for('motos_assai.compra_peca_detalhe', cid=cid))
