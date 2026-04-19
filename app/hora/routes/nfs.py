"""Rotas de NF de entrada (Motochefe → HORA): upload e listagem."""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from app.hora.decorators import require_lojas as login_required

from app.hora.models import HoraLoja, HoraNfEntrada, HoraPedido
from app.hora.routes import hora_bp
from app.hora.services import nf_entrada_service
from app.hora.services.auth_helper import lojas_permitidas_ids, usuario_tem_acesso_a_loja
from app.hora.services.parsers.danfe_adapter import DanfeParseError


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
    pedidos_disponiveis = []
    if not nf.pedido_id:
        pedidos_disponiveis = (
            HoraPedido.query
            .filter(HoraPedido.status.in_(['ABERTO', 'PARCIALMENTE_FATURADO']))
            .order_by(HoraPedido.data_pedido.desc())
            .limit(50)
            .all()
        )
    return render_template(
        'hora/nf_detalhe.html',
        nf=nf,
        pedidos_disponiveis=pedidos_disponiveis,
    )


@hora_bp.route('/nfs/upload', methods=['GET', 'POST'])
@login_required
def nfs_upload():
    """Upload DANFE PDF. Parsea via adapter e cria HoraNfEntrada + itens."""
    pedidos_disponiveis = (
        HoraPedido.query
        .filter(HoraPedido.status.in_(['ABERTO', 'PARCIALMENTE_FATURADO']))
        .order_by(HoraPedido.data_pedido.desc())
        .limit(50)
        .all()
    )
    lojas_ativas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()

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
                f'→ {nf.loja_destino.rotulo_display if nf.loja_destino else "sem loja"}.',
                'success',
            )
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


@hora_bp.route('/nfs/<int:nf_id>/vincular-pedido', methods=['POST'])
@login_required
def nfs_vincular_pedido(nf_id: int):
    pedido_id_str = request.form.get('pedido_id') or ''
    if not pedido_id_str.isdigit():
        flash('Pedido inválido.', 'danger')
        return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
    try:
        nf_entrada_service.vincular_nf_a_pedido(nf_id, int(pedido_id_str))
        flash('NF vinculada ao pedido.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf_id))
