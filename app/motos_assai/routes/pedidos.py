from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadPedidoVoeForm
from app.motos_assai.services import (
    importar_pdf_voe, PedidoVoeJaExisteError, PedidoVoeParserError,
)


@motos_assai_bp.route('/pedidos/upload', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def pedidos_upload():
    form = UploadPedidoVoeForm()
    if form.validate_on_submit():
        pdf_file = form.pdf.data
        pdf_bytes = pdf_file.read()
        try:
            pedido = importar_pdf_voe(
                pdf_bytes=pdf_bytes,
                nome_arquivo=pdf_file.filename or 'pedido.pdf',
                importado_por_id=current_user.id,
            )
            flash(
                f'Pedido {pedido.numero} importado via {pedido.parser_usado} '
                f'(confiança {float(pedido.parsing_confianca):.0%}).',
                'success',
            )
            return redirect(url_for('motos_assai.pedidos_detalhe', pedido_id=pedido.id))
        except PedidoVoeJaExisteError as e:
            flash(str(e), 'warning')
        except PedidoVoeParserError as e:
            current_app.logger.exception('Erro ao parsear pedido VOE')
            flash(f'Erro ao parsear PDF: {e}', 'danger')
    return render_template('motos_assai/pedidos/upload.html', form=form)
