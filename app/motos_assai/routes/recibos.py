from flask import (
    abort, render_template, request, redirect, url_for, flash, current_app, jsonify,
)
from flask_login import login_required, current_user

from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadReciboForm
from app.motos_assai.services import (
    importar_recibo, get_recibo, listar_recibos, get_compra,
    ReciboParserError, ReciboValidationError,
    listar_duplicidades, recibos_antigos_passiveis_de_exclusao,
    opcao_a_excluir_novo, opcao_b_excluir_antigo,
    opcao_c_remover_chassi_antigo, opcao_c_remover_chassi_novo,
    inativar_recibo_item, reativar_recibo_item, excluir_recibo,
)
from app.motos_assai.models import (
    AssaiReciboItem, AssaiReciboMotochefe,
    RECIBO_STATUS_RESOLVENDO_DUPLICIDADE,
)
from app.utils.file_storage import FileStorage


@motos_assai_bp.route('/compras/<int:compra_id>/recibos/upload', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def recibos_upload(compra_id):
    compra = get_compra(compra_id)
    form = UploadReciboForm()
    if form.validate_on_submit():
        f = form.arquivo.data
        try:
            recibo = importar_recibo(
                compra_id=compra_id,
                file_bytes=f.read(),
                nome_arquivo=f.filename,
                mime_type=f.mimetype,
                importado_por_id=current_user.id,
            )
            if recibo.status == RECIBO_STATUS_RESOLVENDO_DUPLICIDADE:
                flash(
                    f'Recibo importado, mas ha chassis duplicados. '
                    f'Resolva a duplicidade antes de iniciar a conferencia.',
                    'warning',
                )
                return redirect(url_for(
                    'motos_assai.recibos_resolver_duplicidade',
                    recibo_id=recibo.id,
                ))
            flash(
                f'Recibo importado via {recibo.parser_usado} '
                f'(confianca {float(recibo.parsing_confianca):.0%}).',
                'success',
            )
            return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo.id))
        except ReciboParserError as e:
            current_app.logger.exception('Erro recibo')
            flash(str(e), 'danger')
    return render_template('motos_assai/recibos/upload.html', form=form, compra=compra)


@motos_assai_bp.route('/recibos/<int:recibo_id>')
@login_required
@require_motos_assai
def recibos_detalhe(recibo_id):
    recibo = get_recibo(recibo_id)
    items_ativos = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id, ativo=True)
        .order_by(AssaiReciboItem.id)
        .all()
    )
    items_inativos = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id, ativo=False)
        .order_by(AssaiReciboItem.id)
        .all()
    )
    conferidos = sum(1 for i in items_ativos if i.conferido)
    pode_excluir = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id, conferido=True)
        .first()
    ) is None
    return render_template(
        'motos_assai/recibos/detalhe.html',
        recibo=recibo, items=items_ativos,
        items_inativos=items_inativos,
        conferidos=conferidos,
        pode_excluir=pode_excluir,
    )


@motos_assai_bp.route('/recibos')
@login_required
@require_motos_assai
def recibos_lista():
    recibos = listar_recibos()
    pode_excluir_map = {}
    if recibos:
        com_recebida = {
            r[0] for r in (
                AssaiReciboItem.query
                .with_entities(AssaiReciboItem.recibo_id)
                .filter(AssaiReciboItem.conferido.is_(True))
                .filter(AssaiReciboItem.recibo_id.in_([r.id for r in recibos]))
                .distinct()
                .all()
            )
        }
        pode_excluir_map = {r.id: (r.id not in com_recebida) for r in recibos}
    return render_template(
        'motos_assai/recibos/lista.html',
        recibos=recibos,
        pode_excluir_map=pode_excluir_map,
    )


# ---------------------------------------------------------------------------
# Resolucao de duplicidade
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/recibos/<int:recibo_id>/resolver-duplicidade')
@login_required
@require_motos_assai
def recibos_resolver_duplicidade(recibo_id):
    recibo = get_recibo(recibo_id)
    if recibo.status != RECIBO_STATUS_RESOLVENDO_DUPLICIDADE:
        flash('Este recibo nao esta em resolucao de duplicidade.', 'info')
        return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))

    duplicidades = listar_duplicidades(recibo_id)
    antigos_elegiveis = recibos_antigos_passiveis_de_exclusao(recibo_id)
    return render_template(
        'motos_assai/recibos/resolver_duplicidade.html',
        recibo=recibo,
        duplicidades=duplicidades,
        antigos_elegiveis=antigos_elegiveis,
    )


@motos_assai_bp.route('/recibos/<int:recibo_id>/resolver/opcao-a', methods=['POST'])
@login_required
@require_motos_assai
def recibos_resolver_opcao_a(recibo_id):
    """Excluir recibo NOVO inteiro."""
    try:
        compra_id_redirect = (
            AssaiReciboMotochefe.query.with_entities(AssaiReciboMotochefe.compra_id)
            .filter_by(id=recibo_id).scalar()
        )
        opcao_a_excluir_novo(recibo_id)
    except ReciboValidationError as e:
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai.recibos_resolver_duplicidade', recibo_id=recibo_id))
    flash('Recibo novo descartado.', 'success')
    if compra_id_redirect:
        return redirect(url_for('motos_assai.compras_detalhe', compra_id=compra_id_redirect))
    return redirect(url_for('motos_assai.recibos_lista'))


@motos_assai_bp.route(
    '/recibos/<int:recibo_id>/resolver/opcao-b/<int:antigo_id>',
    methods=['POST'],
)
@login_required
@require_motos_assai
def recibos_resolver_opcao_b(recibo_id, antigo_id):
    """Excluir recibo ANTIGO inteiro (precisa nao ter motos recebidas)."""
    try:
        opcao_b_excluir_antigo(recibo_id, antigo_id)
    except ReciboValidationError as e:
        flash(str(e), 'danger')
    else:
        flash(f'Recibo antigo #{antigo_id} excluido.', 'success')
    return redirect(url_for('motos_assai.recibos_resolver_duplicidade', recibo_id=recibo_id))


@motos_assai_bp.route(
    '/recibos/<int:recibo_id>/resolver/opcao-c/manter-novo/<int:item_antigo_id>',
    methods=['POST'],
)
@login_required
@require_motos_assai
def recibos_resolver_opcao_c_manter_novo(recibo_id, item_antigo_id):
    """Manter chassi no recibo NOVO -> remove do antigo (soft-delete)."""
    try:
        opcao_c_remover_chassi_antigo(recibo_id, item_antigo_id)
    except ReciboValidationError as e:
        flash(str(e), 'danger')
    return redirect(url_for('motos_assai.recibos_resolver_duplicidade', recibo_id=recibo_id))


@motos_assai_bp.route(
    '/recibos/<int:recibo_id>/resolver/opcao-c/manter-antigo/<int:item_novo_id>',
    methods=['POST'],
)
@login_required
@require_motos_assai
def recibos_resolver_opcao_c_manter_antigo(recibo_id, item_novo_id):
    """Manter chassi no recibo ANTIGO -> descarta do novo (mantem inativo)."""
    try:
        opcao_c_remover_chassi_novo(recibo_id, item_novo_id)
    except ReciboValidationError as e:
        flash(str(e), 'danger')
    return redirect(url_for('motos_assai.recibos_resolver_duplicidade', recibo_id=recibo_id))


# ---------------------------------------------------------------------------
# Excluir recibo / inativar / reativar item
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/recibos/<int:recibo_id>/download')
@login_required
@require_motos_assai
def recibos_download(recibo_id):
    """Redireciona para presigned URL S3 (ou serve o arquivo local) do PDF/XLSX
    importado. Bloqueia se o recibo nao tem `doc_s3_key`."""
    recibo = get_recibo(recibo_id)
    if not recibo.doc_s3_key:
        flash('Este recibo nao tem arquivo armazenado.', 'warning')
        return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))

    storage = FileStorage()
    if not storage.file_exists(recibo.doc_s3_key):
        current_app.logger.warning(
            f'doc_s3_key sumiu do storage: {recibo.doc_s3_key} (recibo {recibo_id})'
        )
        flash('Arquivo nao encontrado no storage.', 'danger')
        return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))

    # S3: presigned URL de visualizacao inline (browser oferece download conforme Content-Type)
    if storage.use_s3 and not recibo.doc_s3_key.startswith('uploads/'):
        url = storage.get_presigned_url(recibo.doc_s3_key, expires_in=300)
        if not url:
            abort(500)
        return redirect(url)

    # Local: serve direto via static
    url = storage.get_file_url(recibo.doc_s3_key)
    if not url:
        abort(500)
    return redirect(url)


@motos_assai_bp.route('/recibos/<int:recibo_id>/excluir', methods=['POST'])
@login_required
@require_motos_assai
def recibos_excluir(recibo_id):
    """Excluir recibo inteiro (somente se nenhum chassi foi recebido)."""
    compra_id_redirect = (
        AssaiReciboMotochefe.query.with_entities(AssaiReciboMotochefe.compra_id)
        .filter_by(id=recibo_id).scalar()
    )
    try:
        excluir_recibo(recibo_id)
    except ReciboValidationError as e:
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))
    flash('Recibo excluido.', 'success')
    if compra_id_redirect:
        return redirect(url_for('motos_assai.compras_detalhe', compra_id=compra_id_redirect))
    return redirect(url_for('motos_assai.recibos_lista'))


@motos_assai_bp.route('/recibos/itens/<int:item_id>/inativar', methods=['POST'])
@login_required
@require_motos_assai
def recibos_item_inativar(item_id):
    """Inativa um chassi de um recibo (somente se nao foi recebido).

    Aceita form-encoded (redireciona) ou JSON (responde JSON).
    """
    item = AssaiReciboItem.query.get_or_404(item_id)
    recibo_id = item.recibo_id
    quer_json = (request.is_json or request.headers.get('Accept', '').startswith('application/json'))
    try:
        inativar_recibo_item(item_id)
    except ReciboValidationError as e:
        if quer_json:
            return jsonify({'ok': False, 'erro': str(e)}), 400
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))
    if quer_json:
        return jsonify({'ok': True})
    flash(f'Chassi {item.chassi} inativado.', 'success')
    return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))


@motos_assai_bp.route('/recibos/itens/<int:item_id>/reativar', methods=['POST'])
@login_required
@require_motos_assai
def recibos_item_reativar(item_id):
    """Reativa um chassi inativado (bloqueado se ja existe ativo em outro recibo)."""
    item = AssaiReciboItem.query.get_or_404(item_id)
    recibo_id = item.recibo_id
    quer_json = (request.is_json or request.headers.get('Accept', '').startswith('application/json'))
    try:
        reativar_recibo_item(item_id)
    except ReciboValidationError as e:
        if quer_json:
            return jsonify({'ok': False, 'erro': str(e)}), 400
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))
    if quer_json:
        return jsonify({'ok': True})
    flash(f'Chassi {item.chassi} reativado.', 'success')
    return redirect(url_for('motos_assai.recibos_detalhe', recibo_id=recibo_id))
