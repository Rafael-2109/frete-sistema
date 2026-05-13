"""Rotas de Carregamento (Fase 3 UI).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md S15.1-15.2
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Tasks 16-25

Decisao N-B1 (rodada 2): rotas GET (telas) usam @login_required + @require_motos_assai;
endpoints AJAX (POST que retornam JSON) NAO usam decorators — tornam-se
chamados de service-layer puros para evitar redirects HTML em respostas JSON.
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import (
    AssaiCarregamento, AssaiCarregamentoItem,
    AssaiPedidoVenda, AssaiLoja,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    CARREGAMENTO_STATUS_FINALIZADO,
    CARREGAMENTO_STATUS_CANCELADO,
)
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item,
    cancelar_carregamento_item, cancelar_carregamento,
    finalizar_carregamento, alterar_carregamento,
    CarregamentoValidationError, CarregamentoConflictError,
    CarregamentoStateError, CarregamentoExcedenteError,
    CarregamentoCrossLojaError,
)


# ============================================================
# Telas (GET) — COM @login_required + @require_motos_assai
# ============================================================

@motos_assai_bp.route('/carregamento', methods=['GET'])
@login_required
@require_motos_assai
def carregamento_lista():
    """Lista carregamentos: em andamento + finalizados recentes + cancelados recentes.

    Renderiza HTML com modal de "Iniciar Carregamento" (form pedido+loja).
    """
    em_andamento = (AssaiCarregamento.query
                    .filter_by(status=CARREGAMENTO_STATUS_EM_CARREGAMENTO)
                    .order_by(AssaiCarregamento.iniciado_em.desc())
                    .all())
    finalizados_recentes = (AssaiCarregamento.query
                            .filter_by(status=CARREGAMENTO_STATUS_FINALIZADO)
                            .order_by(AssaiCarregamento.finalizado_em.desc())
                            .limit(20)
                            .all())
    cancelados_recentes = (AssaiCarregamento.query
                           .filter_by(status=CARREGAMENTO_STATUS_CANCELADO)
                           .order_by(AssaiCarregamento.cancelado_em.desc())
                           .limit(10)
                           .all())

    pedidos_abertos = (AssaiPedidoVenda.query
                       .filter(AssaiPedidoVenda.status.in_([
                           PEDIDO_STATUS_ABERTO,
                           PEDIDO_STATUS_PARCIALMENTE_FATURADO,
                       ]))
                       .order_by(AssaiPedidoVenda.numero)
                       .all())
    lojas = AssaiLoja.query.order_by(AssaiLoja.numero).all()

    return render_template(
        'motos_assai/carregamento/lista.html',
        em_andamento=em_andamento,
        finalizados_recentes=finalizados_recentes,
        cancelados_recentes=cancelados_recentes,
        pedidos_abertos=pedidos_abertos,
        lojas=lojas,
    )


@motos_assai_bp.route('/carregamento/iniciar', methods=['POST'])
@login_required
@require_motos_assai
def carregamento_iniciar():
    """Form HTML POST para iniciar novo carregamento.

    A2: NAO ha UNIQUE em (pedido, loja, EM_CARREGAMENTO) — N carregamentos
    paralelos sao permitidos.
    """
    try:
        pedido_id = int(request.form['pedido_id'])
        loja_id = int(request.form['loja_id'])
    except (KeyError, ValueError):
        flash('Pedido e loja sao obrigatorios.', 'danger')
        return redirect(url_for('motos_assai.carregamento_lista'))

    try:
        car = criar_carregamento(pedido_id, loja_id, operador_id=current_user.id)
        db.session.commit()
        flash(f'Carregamento #{car.id} iniciado.', 'success')
        return redirect(url_for('motos_assai.carregamento_detalhe', carregamento_id=car.id))
    except CarregamentoValidationError as e:
        db.session.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai.carregamento_lista'))


@motos_assai_bp.route('/carregamento/<int:carregamento_id>', methods=['GET'])
@login_required
@require_motos_assai
def carregamento_detalhe(carregamento_id):
    """Tela de escaneio do carregamento.

    Renderiza escanear.html com:
        - Header (pedido + loja + status badge)
        - Input chassi (QR/manual) — somente quando EM_CARREGAMENTO
        - Tabela de items escaneados
        - Botoes Finalizar/Cancelar (EM_CARREGAMENTO) e Alterar (FINALIZADO)
    """
    car = AssaiCarregamento.query.get_or_404(carregamento_id)
    items = (AssaiCarregamentoItem.query
             .filter_by(carregamento_id=car.id)
             .order_by(AssaiCarregamentoItem.escaneado_em.desc())
             .all())

    return render_template(
        'motos_assai/carregamento/escanear.html',
        carregamento=car,
        items=items,
    )


# ============================================================
# AJAX endpoints (POST que retornam JSON) — SEM decorators (N-B1).
# Sessao validada via current_user.is_authenticated; resposta JSON em
# qualquer cenario (200/400/409/422). NUNCA redireciona.
# ============================================================

@motos_assai_bp.route('/carregamento/<int:carregamento_id>/escanear', methods=['POST'])
def carregamento_escanear_ajax(carregamento_id):
    """AJAX: adiciona chassi ao carregamento ativo (S3=c lock pessimista).

    Body JSON: {chassi: str}

    Retorna:
        200 ok=True + item: {id, chassi, modelo}
        400 CarregamentoValidationError
        409 CarregamentoConflictError (chassi em outro car ativo, ja escaneado)
        422 CarregamentoStateError (carregamento nao EM_CARREGAMENTO)
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada. Recarregue a pagina.'}), 401

    data = request.get_json(silent=True) or {}
    chassi = (data.get('chassi') or '').strip().upper()
    if not chassi:
        return jsonify({'ok': False, 'erro': 'Chassi obrigatorio.'}), 400

    try:
        item = escanear_carregamento_item(carregamento_id, chassi, operador_id=current_user.id)
        db.session.commit()
        return jsonify({
            'ok': True,
            'item': {
                'id': item.id,
                'chassi': item.chassi,
                'modelo_codigo': item.modelo.codigo if item.modelo else None,
                'modelo_nome': item.modelo.nome if item.modelo else None,
                'escaneado_em': item.escaneado_em.strftime('%d/%m %H:%M') if item.escaneado_em else None,
            },
        })
    except CarregamentoCrossLojaError as e:
        # Plano 4 Task 3: chassi em sep ativa de outra loja —
        # operador deve confirmar substituicao via modal (HTTP 409 cenario=cross_loja).
        db.session.rollback()
        return jsonify({
            'ok': False,
            'cenario': 'cross_loja',
            'erro': str(e),
            'chassi': e.chassi,
            'sep_origem_id': e.sep_origem_id,
            'loja_origem_id': e.loja_origem_id,
            'carregamento_id': e.carregamento_id,
            'loja_destino_id': e.loja_destino_id,
        }), 409
    except CarregamentoValidationError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except CarregamentoConflictError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e), 'retry': False}), 409
    except CarregamentoStateError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 422


@motos_assai_bp.route('/carregamento/item/<int:item_id>/cancelar', methods=['POST'])
def carregamento_item_cancelar_ajax(item_id):
    """AJAX: remove item do carregamento (apenas durante EM_CARREGAMENTO).

    Retorna:
        200 ok=True
        400 CarregamentoValidationError (item nao existe)
        422 CarregamentoStateError (carregamento ja FINALIZADO/CANCELADO)
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada. Recarregue a pagina.'}), 401

    try:
        cancelar_carregamento_item(item_id, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True})
    except CarregamentoValidationError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except CarregamentoStateError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 422


@motos_assai_bp.route('/carregamento/<int:carregamento_id>/finalizar', methods=['POST'])
def carregamento_finalizar_ajax(carregamento_id):
    """AJAX: finaliza carregamento (algoritmo §6 com 8 fases).

    Retorna:
        200 ok=True + sep_id + redirect (faturamento_lista)
        400 CarregamentoValidationError
        409 cenario='excedente' + qtd_excedente + seps_bloqueadas (S14=a)
        422 CarregamentoStateError
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada. Recarregue a pagina.'}), 401

    try:
        sep = finalizar_carregamento(carregamento_id, operador_id=current_user.id)
        db.session.commit()
        return jsonify({
            'ok': True,
            'sep_id': sep.id if sep else None,
            'redirect': url_for('motos_assai.faturamento_lista'),
        })
    except CarregamentoExcedenteError as e:
        db.session.rollback()
        return jsonify({
            'ok': False,
            'erro': str(e),
            'cenario': 'excedente',
            'qtd_excedente': e.qtd_excedente,
            'seps_bloqueadas': e.seps_bloqueadas,
        }), 409
    except CarregamentoValidationError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except CarregamentoStateError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 422


@motos_assai_bp.route('/carregamento/<int:carregamento_id>/cancelar', methods=['POST'])
def carregamento_cancelar_ajax(carregamento_id):
    """AJAX: cancela carregamento (S5).

    Body JSON: {motivo: str (min 3 chars)}

    Retorna:
        200 ok=True + redirect (carregamento_lista)
        400 CarregamentoValidationError (motivo vazio/curto)
        422 CarregamentoStateError (ja CANCELADO)
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada. Recarregue a pagina.'}), 401

    data = request.get_json(silent=True) or {}
    motivo = (data.get('motivo') or '').strip()

    try:
        cancelar_carregamento(carregamento_id, motivo=motivo, operador_id=current_user.id)
        db.session.commit()
        return jsonify({
            'ok': True,
            'redirect': url_for('motos_assai.carregamento_lista'),
        })
    except CarregamentoValidationError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except CarregamentoStateError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 422


@motos_assai_bp.route('/carregamento/<int:carregamento_id>/alterar', methods=['POST'])
def carregamento_alterar_ajax(carregamento_id):
    """AJAX: reabre carregamento FINALIZADO -> EM_CARREGAMENTO (S6=a).

    H3 fix: sep vinculada CARREGADA -> FECHADA (mantem invariante).

    Retorna:
        200 ok=True + redirect (carregamento_detalhe — para continuar escaneando)
        400 CarregamentoValidationError
        422 CarregamentoStateError (ja EM_CARREGAMENTO ou CANCELADO)
    """
    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada. Recarregue a pagina.'}), 401

    try:
        alterar_carregamento(carregamento_id, operador_id=current_user.id)
        db.session.commit()
        return jsonify({
            'ok': True,
            'redirect': url_for('motos_assai.carregamento_detalhe',
                                carregamento_id=carregamento_id),
        })
    except CarregamentoValidationError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except CarregamentoStateError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 422
