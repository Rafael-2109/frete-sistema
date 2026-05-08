from flask import render_template, request, redirect, url_for, flash, abort, Response
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import NovaCompraForm
from app.motos_assai.services import (
    listar_pedidos_consolidaveis, calcular_totalizadores_por_modelo,
    criar_consolidado, get_compra, listar_compras, gerar_pdf_po,
    CompraValidationError,
)


@motos_assai_bp.route('/compras/nova', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def compras_nova():
    form = NovaCompraForm()
    pedidos_disponiveis = listar_pedidos_consolidaveis()
    pedido_ids_pre = request.args.getlist('pedido_ids', type=int)
    pedido_ids_post = request.form.getlist('pedido_ids', type=int)

    # POST: tenta criar
    if request.method == 'POST' and form.validate_on_submit():
        if not pedido_ids_post:
            flash('Selecione ao menos 1 pedido.', 'warning')
        else:
            try:
                compra = criar_consolidado(
                    pedido_ids=pedido_ids_post,
                    motochefe_cnpj=form.motochefe_cnpj.data.strip() if form.motochefe_cnpj.data else None,
                    criada_por_id=current_user.id,
                )
                flash(f'PO {compra.numero} gerado.', 'success')
                return redirect(url_for('motos_assai.compras_detalhe', compra_id=compra.id))
            except CompraValidationError as e:
                flash(str(e), 'danger')

    # Preview de totais (se pedidos selecionados via GET ou POST)
    pedido_ids_preview = pedido_ids_post or pedido_ids_pre
    totais_preview = (
        calcular_totalizadores_por_modelo(pedido_ids_preview)
        if pedido_ids_preview else []
    )

    return render_template(
        'motos_assai/compras/nova.html',
        form=form,
        pedidos=pedidos_disponiveis,
        pedido_ids_preview=set(pedido_ids_preview),
        totais_preview=totais_preview,
    )


@motos_assai_bp.route('/compras/<int:compra_id>')
@login_required
@require_motos_assai
def compras_detalhe(compra_id):
    compra = get_compra(compra_id)
    pedido_ids = [link.pedido_id for link in compra.pedido_links]
    totais = calcular_totalizadores_por_modelo(pedido_ids) if pedido_ids else []
    return render_template(
        'motos_assai/compras/detalhe.html',
        compra=compra,
        totais=totais,
    )


@motos_assai_bp.route('/compras/<int:compra_id>/pdf')
@login_required
@require_motos_assai
def compras_pdf(compra_id):
    pdf_bytes = gerar_pdf_po(compra_id)
    compra = get_compra(compra_id)
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="PO_{compra.numero}.pdf"'
        },
    )


@motos_assai_bp.route('/compras')
@login_required
@require_motos_assai
def compras_lista():
    compras = listar_compras()
    return render_template('motos_assai/compras/lista.html', compras=compras)
