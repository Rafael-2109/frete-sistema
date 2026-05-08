from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadReciboForm
from app.motos_assai.services import (
    importar_recibo, get_recibo, listar_recibos, get_compra,
    ReciboParserError,
)
from app.motos_assai.models import AssaiReciboItem


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
            flash(f'Recibo importado via {recibo.parser_usado} '
                  f'(confiança {float(recibo.parsing_confianca):.0%}).', 'success')
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
    items = AssaiReciboItem.query.filter_by(recibo_id=recibo_id).order_by(
        AssaiReciboItem.id
    ).all()
    conferidos = sum(1 for i in items if i.conferido)
    return render_template(
        'motos_assai/recibos/detalhe.html',
        recibo=recibo, items=items, conferidos=conferidos,
    )


@motos_assai_bp.route('/recibos')
@login_required
@require_motos_assai
def recibos_lista():
    recibos = listar_recibos()
    return render_template('motos_assai/recibos/lista.html', recibos=recibos)
