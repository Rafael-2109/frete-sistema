from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadPedidoVoeForm
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiModelo,
    PEDIDO_STATUS_ABERTO,
)
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


@motos_assai_bp.route('/pedidos/<int:pedido_id>')
@login_required
@require_motos_assai
def pedidos_detalhe(pedido_id):
    pedido = AssaiPedidoVenda.query.get_or_404(pedido_id)

    # Totais por modelo (cross-loja)
    totais_por_modelo = (
        db.session.query(
            AssaiModelo.codigo,
            AssaiModelo.nome,
            func.sum(AssaiPedidoVendaItem.qtd_pedida).label('qtd'),
            func.sum(AssaiPedidoVendaItem.valor_total).label('valor'),
        )
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.modelo_id == AssaiModelo.id)
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .group_by(AssaiModelo.id, AssaiModelo.codigo, AssaiModelo.nome)
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # Lojas com seus items
    lojas_items = (
        db.session.query(AssaiLoja, AssaiPedidoVendaItem, AssaiModelo)
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.loja_id == AssaiLoja.id)
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .order_by(AssaiLoja.numero, AssaiModelo.codigo)
        .all()
    )

    # Agrupa por loja para template
    por_loja: dict = {}
    for loja, item, modelo in lojas_items:
        por_loja.setdefault(loja.id, {'loja': loja, 'items': []})
        por_loja[loja.id]['items'].append({'item': item, 'modelo': modelo})

    return render_template(
        'motos_assai/pedidos/detalhe.html',
        pedido=pedido,
        totais_por_modelo=totais_por_modelo,
        por_loja=list(por_loja.values()),
    )


@motos_assai_bp.route('/pedidos')
@login_required
@require_motos_assai
def pedidos_lista():
    status = request.args.get('status', '').strip() or None
    q = AssaiPedidoVenda.query

    if status:
        q = q.filter_by(status=status)

    pedidos = q.order_by(AssaiPedidoVenda.criado_em.desc()).limit(250).all()

    return render_template(
        'motos_assai/pedidos/lista.html',
        pedidos=pedidos,
        status_filtro=status,
        statuses=['ABERTO', 'EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL', 'FATURADO', 'CANCELADO'],
    )
