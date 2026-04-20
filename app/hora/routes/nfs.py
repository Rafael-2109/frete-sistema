"""Rotas de NF de entrada (Motochefe -> HORA): upload, listagem, vinculo e match."""
from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from app.hora.decorators import require_lojas as login_required

from app.hora.models import HoraLoja, HoraNfEntrada, HoraPedido
from app.hora.routes import hora_bp
from app.hora.services import nf_entrada_service, matching_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)
from app.hora.services.parsers.danfe_adapter import DanfeParseError


def _pedidos_candidatos_para_lojas(permitidas, loja_id=None, limit=50):
    """Helper: lista pedidos ABERTO/PARCIAL filtrando por lojas permitidas
    e opcionalmente por loja especifica.
    """
    query = (
        HoraPedido.query
        .filter(HoraPedido.status.in_(['ABERTO', 'PARCIALMENTE_FATURADO']))
    )
    if permitidas is not None:
        if not permitidas:
            return []
        query = query.filter(HoraPedido.loja_destino_id.in_(permitidas))
    if loja_id:
        query = query.filter(HoraPedido.loja_destino_id == loja_id)
    return (
        query.order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc())
        .limit(limit)
        .all()
    )


def _lojas_ativas_permitidas():
    permitidas = lojas_permitidas_ids()
    q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            return []
        q = q.filter(HoraLoja.id.in_(permitidas))
    return q.order_by(HoraLoja.nome).all()


# ------------------------------------------------------------------------
# Listagem / detalhe
# ------------------------------------------------------------------------

@hora_bp.route('/nfs')
@login_required
def nfs_lista():
    nfs = nf_entrada_service.listar_nfs_entrada(
        limit=200,
        lojas_permitidas_ids=lojas_permitidas_ids(),
    )
    return render_template('hora/nfs_lista.html', nfs=nfs)


@hora_bp.route('/nfs/<int:nf_id>')
@login_required
def nfs_detalhe(nf_id: int):
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        from flask import abort
        abort(403)

    # Lojas permitidas para o caso de a NF estar sem loja_destino_id
    lojas_ativas = _lojas_ativas_permitidas() if not nf.loja_destino_id else []

    # Pedidos candidatos para vinculo rapido (filtrados pela loja da NF)
    pedidos_disponiveis = []
    if not nf.pedido_id and nf.loja_destino_id:
        pedidos_disponiveis = _pedidos_candidatos_para_lojas(
            permitidas=lojas_permitidas_ids(),
            loja_id=nf.loja_destino_id,
            limit=50,
        )
    return render_template(
        'hora/nf_detalhe.html',
        nf=nf,
        pedidos_disponiveis=pedidos_disponiveis,
        lojas_ativas=lojas_ativas,
    )


# ------------------------------------------------------------------------
# Upload DANFE
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/upload', methods=['GET', 'POST'])
@login_required
def nfs_upload():
    """Upload DANFE PDF. Parsea via adapter e cria HoraNfEntrada + itens."""
    permitidas = lojas_permitidas_ids()
    lojas_ativas = _lojas_ativas_permitidas()

    # Pedidos por loja (para o auto-fill no JS do template)
    pedidos_disponiveis = _pedidos_candidatos_para_lojas(
        permitidas=permitidas, loja_id=None, limit=100,
    )

    if request.method == 'POST':
        arquivo = request.files.get('pdf')
        if not arquivo or arquivo.filename == '':
            flash('Selecione um arquivo PDF.', 'danger')
            return render_template(
                'hora/nf_upload.html',
                pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
            )

        pedido_id_str = request.form.get('pedido_id') or ''
        pedido_id_sugerido = int(pedido_id_str) if pedido_id_str.isdigit() else None

        loja_destino_str = request.form.get('loja_destino_id') or ''
        loja_destino_id = int(loja_destino_str) if loja_destino_str.isdigit() else None

        # Valida permissao sobre a loja selecionada
        if loja_destino_id and not usuario_tem_acesso_a_loja(loja_destino_id):
            flash('Acesso negado a essa loja.', 'danger')
            return render_template(
                'hora/nf_upload.html',
                pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
            )

        # Valida permissao sobre o pedido (se informado)
        if pedido_id_sugerido:
            ped = HoraPedido.query.get(pedido_id_sugerido)
            if not ped or (
                ped.loja_destino_id
                and not usuario_tem_acesso_a_loja(ped.loja_destino_id)
            ):
                flash('Acesso negado ao pedido selecionado.', 'danger')
                return render_template(
                    'hora/nf_upload.html',
                    pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
                )

        try:
            pdf_bytes = arquivo.read()
            nf = nf_entrada_service.importar_danfe_pdf(
                pdf_bytes=pdf_bytes,
                nome_arquivo_origem=arquivo.filename,
                pedido_id_sugerido=pedido_id_sugerido,
                loja_destino_id=loja_destino_id,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            flash(
                f'NF {nf.numero_nf} importada ({len(nf.itens)} chassi(s)) '
                f'-> {nf.loja_destino.rotulo_display if nf.loja_destino else "sem loja"}.',
                'success',
            )
            # Se nao foi vinculada a pedido, vai para modal de match
            if not nf.pedido_id:
                return redirect(url_for('hora.nfs_match', nf_id=nf.id))
            return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))
        except nf_entrada_service.NfEntradaJaImportada as exc:
            flash(str(exc), 'warning')
        except (ValueError, DanfeParseError) as exc:
            flash(f'Erro ao importar: {exc}', 'danger')
        except Exception as exc:  # pragma: no cover
            flash(f'Erro inesperado: {exc}', 'danger')

    return render_template(
        'hora/nf_upload.html',
        pedidos=pedidos_disponiveis, lojas_ativas=lojas_ativas,
    )


# ------------------------------------------------------------------------
# Definir loja (NF legada)
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/definir-loja', methods=['POST'])
@login_required
def nfs_definir_loja(nf_id: int):
    """Preenche loja_destino_id em NF legada (pre-requisito para match)."""
    from app import db
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id:
        flash('NF ja tem loja definida.', 'warning')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    loja_str = (request.form.get('loja_destino_id') or '').strip()
    if not loja_str.isdigit():
        flash('Selecione a loja de destino.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    loja_id = int(loja_str)
    if not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    loja = HoraLoja.query.get(loja_id)
    if not loja:
        flash(f'Loja {loja_id} nao encontrada.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    nf.loja_destino_id = loja_id
    db.session.commit()
    flash(f'Loja {loja.rotulo_display} definida para a NF.', 'success')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))


# ------------------------------------------------------------------------
# Vinculo manual rapido (form do nf_detalhe)
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/vincular-pedido', methods=['POST'])
@login_required
def nfs_vincular_pedido(nf_id: int):
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        from flask import abort
        abort(403)

    pedido_id_str = request.form.get('pedido_id') or ''
    if not pedido_id_str.isdigit():
        flash('Pedido invalido.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
    pedido_id = int(pedido_id_str)

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        flash(f'Pedido {pedido_id} nao encontrado.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
    # Valida loja
    if nf.loja_destino_id and pedido.loja_destino_id and nf.loja_destino_id != pedido.loja_destino_id:
        flash('Pedido e de loja diferente da NF.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        from flask import abort
        abort(403)

    try:
        nf_entrada_service.vincular_nf_a_pedido(nf_id, pedido_id)
        flash('NF vinculada ao pedido.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))


# ------------------------------------------------------------------------
# Modal de match NF x Pedido
# ------------------------------------------------------------------------

@hora_bp.route('/nfs/<int:nf_id>/match')
@login_required
def nfs_match(nf_id: int):
    """Modal/tela de vinculo NF -> Pedido com candidatos ordenados por match."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        from flask import abort
        abort(403)

    # Se NF nao tem loja, nao da pra casar
    if not nf.loja_destino_id:
        flash(
            'NF ainda nao tem loja definida. Preencha a loja antes de vincular pedido.',
            'warning',
        )
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    try:
        candidatos = matching_service.candidatos_pedidos_para_nf(nf.id)
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))

    # Auto-sugestao: primeiro com match > 0, senao o de maior pendente
    sugerido_id = None
    for s in candidatos:
        if s.match > 0:
            sugerido_id = s.pedido_id
            break
    if sugerido_id is None and candidatos:
        sugerido_id = candidatos[0].pedido_id

    return render_template(
        'hora/nf_match_modal.html',
        nf=nf,
        candidatos=[c.to_dict() for c in candidatos],
        sugerido_id=sugerido_id,
    )


@hora_bp.route('/nfs/<int:nf_id>/match/preview')
@login_required
def nfs_match_preview(nf_id: int):
    """JSON com itens NF + itens do pedido escolhido + totais (verde/vermelho)."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    pedido_id_str = request.args.get('pedido_id') or ''
    if not pedido_id_str.isdigit():
        return jsonify({'ok': False, 'erro': 'pedido_id invalido'}), 400
    pedido_id = int(pedido_id_str)

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        return jsonify({'ok': False, 'erro': f'pedido {pedido_id} nao encontrado'}), 404
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado ao pedido'}), 403
    if nf.loja_destino_id and pedido.loja_destino_id and nf.loja_destino_id != pedido.loja_destino_id:
        return jsonify({'ok': False, 'erro': 'pedido de outra loja'}), 400

    try:
        data = matching_service.preview_match(nf.id, pedido.id)
    except ValueError as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400

    data['ok'] = True
    return jsonify(data)


@hora_bp.route('/nfs/<int:nf_id>/match/corrigir-pedido', methods=['POST'])
@login_required
def nfs_match_corrigir_pedido(nf_id: int):
    """Copia chassi da NF para o item do pedido (preenche pendente ou substitui)."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    try:
        pedido_id = int(request.form.get('pedido_id') or '')
        pedido_item_id = int(request.form.get('pedido_item_id') or '')
        nf_item_id = int(request.form.get('nf_item_id') or '')
    except ValueError:
        return jsonify({'ok': False, 'erro': 'parametros invalidos'}), 400

    try:
        res = matching_service.aplicar_correcao_pedido_item(
            nf_id=nf.id,
            pedido_id=pedido_id,
            pedido_item_id=pedido_item_id,
            nf_item_id=nf_item_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        return jsonify(res)
    except ValueError as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400


@hora_bp.route('/nfs/<int:nf_id>/match/corrigir-nf', methods=['POST'])
@login_required
def nfs_match_corrigir_nf(nf_id: int):
    """Copia chassi do pedido para o item da NF."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    try:
        pedido_id = int(request.form.get('pedido_id') or '')
        pedido_item_id = int(request.form.get('pedido_item_id') or '')
        nf_item_id = int(request.form.get('nf_item_id') or '')
    except ValueError:
        return jsonify({'ok': False, 'erro': 'parametros invalidos'}), 400

    try:
        res = matching_service.aplicar_correcao_nf_item(
            nf_id=nf.id,
            pedido_id=pedido_id,
            pedido_item_id=pedido_item_id,
            nf_item_id=nf_item_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        return jsonify(res)
    except ValueError as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400


@hora_bp.route('/nfs/<int:nf_id>/match/confirmar', methods=['POST'])
@login_required
def nfs_match_confirmar(nf_id: int):
    """Confirma vinculo final (depois de corrigir divergencias)."""
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        from flask import abort
        abort(403)

    pedido_id_str = (request.form.get('pedido_id') or '').strip()
    if not pedido_id_str.isdigit():
        flash('Selecione um pedido.', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))

    pedido_id = int(pedido_id_str)
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        flash(f'Pedido {pedido_id} nao encontrado.', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))
    if pedido.loja_destino_id != nf.loja_destino_id:
        flash('Pedido de outra loja.', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))
    if not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        from flask import abort
        abort(403)

    try:
        nf_entrada_service.vincular_nf_a_pedido(nf.id, pedido.id)
        flash(f'NF vinculada ao pedido {pedido.numero_pedido}.', 'success')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.nfs_match', nf_id=nf.id))
