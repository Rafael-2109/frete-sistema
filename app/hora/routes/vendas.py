"""Rotas de Venda (NF de saida HORA -> consumidor final): upload, listagem,
detalhe, edicao, definicao de loja, cancelamento e resolucao de divergencias.
"""
from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja, HoraVenda, HoraVendaDivergencia
from app.hora.routes import hora_bp
from app.hora.services import venda_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)
from app.hora.services.parsers.danfe_adapter import DanfeParseError


def _lojas_ativas_permitidas():
    permitidas = lojas_permitidas_ids()
    q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            return []
        q = q.filter(HoraLoja.id.in_(permitidas))
    return q.order_by(HoraLoja.nome).all()


def _operador_atual() -> str:
    return getattr(current_user, 'nome', None) or 'desconhecido'


# ------------------------------------------------------------------------
# Listagem
# ------------------------------------------------------------------------

@hora_bp.route('/vendas')
@require_hora_perm('vendas', 'ver')
def vendas_lista():
    vendas = venda_service.listar_vendas(
        limit=200,
        lojas_permitidas_ids=lojas_permitidas_ids(),
    )
    return render_template('hora/vendas_lista.html', vendas=vendas)


# ------------------------------------------------------------------------
# Upload DANFE -> cria venda
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/upload', methods=['GET', 'POST'])
@require_hora_perm('vendas', 'criar')
def vendas_upload():
    """Upload DANFE PDF emitido pela loja HORA. Parseia via adapter e cria
    HoraVenda + itens + eventos VENDIDA + divergencias.

    Nao pede loja nem cliente — tudo vem da NF. Operador preenche vendedor e
    forma_pagamento depois na tela de detalhe.
    """
    if request.method == 'POST':
        arquivo = request.files.get('pdf')
        if not arquivo or arquivo.filename == '':
            flash('Selecione um arquivo PDF.', 'danger')
            return render_template('hora/venda_upload.html')

        try:
            pdf_bytes = arquivo.read()
            venda = venda_service.importar_nf_saida_pdf(
                pdf_bytes=pdf_bytes,
                nome_arquivo_origem=arquivo.filename,
                criado_por=_operador_atual(),
            )
            qtd_chassis = len(venda.itens)
            qtd_div = len(venda.divergencias_abertas)
            loja_txt = (
                venda.loja.rotulo_display
                if venda.loja else 'sem loja (CNPJ nao cadastrado)'
            )
            msg = (
                f'Venda #{venda.id} importada — NF {venda.nf_saida_numero} '
                f'({qtd_chassis} chassi(s)) para {venda.nome_cliente} '
                f'em {loja_txt}.'
            )
            if qtd_div > 0:
                msg += f' ATENCAO: {qtd_div} divergencia(s) — revise na tela de detalhe.'
                flash(msg, 'warning')
            else:
                flash(msg, 'success')
            return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))
        except venda_service.NfSaidaJaImportada as exc:
            flash(str(exc), 'warning')
        except (ValueError, DanfeParseError) as exc:
            flash(f'Erro ao importar: {exc}', 'danger')
        except Exception as exc:  # pragma: no cover
            flash(f'Erro inesperado: {exc}', 'danger')

    return render_template('hora/venda_upload.html')


# ------------------------------------------------------------------------
# Detalhe
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>')
@require_hora_perm('vendas', 'ver')
def vendas_detalhe(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado: venda de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    # Venda sem loja (loja_id=NULL) so e acessivel para admin (lojas_permitidas_ids=None).
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        flash(
            'Esta venda ainda nao tem loja definida — apenas administradores podem abrir.',
            'warning',
        )
        return redirect(url_for('hora.vendas_lista'))

    lojas_ativas = _lojas_ativas_permitidas() if not venda.loja_id else []

    return render_template(
        'hora/venda_detalhe.html',
        venda=venda,
        lojas_ativas=lojas_ativas,
    )


# ------------------------------------------------------------------------
# Download PDF
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/download-pdf')
@require_hora_perm('vendas', 'ver')
def vendas_download_pdf(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if not venda.arquivo_pdf_s3_key:
        flash('PDF desta venda nao esta armazenado.', 'warning')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    from app.utils.file_storage import FileStorage
    url = FileStorage().get_file_url(venda.arquivo_pdf_s3_key)
    if not url:
        flash('Falha ao gerar URL do PDF.', 'danger')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))
    return redirect(url)


# ------------------------------------------------------------------------
# Editar (vendedor, forma_pagamento, contato, observacoes)
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/editar', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_editar(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        flash('Venda sem loja definida — apenas admin edita.', 'warning')
        return redirect(url_for('hora.vendas_lista'))

    try:
        venda_service.editar_venda(
            venda_id=venda.id,
            vendedor=request.form.get('vendedor'),
            forma_pagamento=request.form.get('forma_pagamento'),
            telefone_cliente=request.form.get('telefone_cliente'),
            email_cliente=request.form.get('email_cliente'),
            observacoes=request.form.get('observacoes'),
        )
        flash('Venda atualizada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Definir loja (resolve CNPJ_DESCONHECIDO)
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/definir-loja', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_definir_loja(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id:
        flash('Venda ja tem loja definida.', 'warning')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    # Apenas admin abre venda com loja=NULL — coerente com vendas_detalhe.
    if lojas_permitidas_ids() is not None:
        flash('Apenas administradores podem definir loja de venda sem loja.', 'danger')
        return redirect(url_for('hora.vendas_lista'))

    loja_str = (request.form.get('loja_id') or '').strip()
    if not loja_str.isdigit():
        flash('Selecione a loja.', 'danger')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    try:
        venda_service.definir_loja_venda(
            venda_id=venda.id,
            loja_id=int(loja_str),
            usuario=_operador_atual(),
        )
        flash('Loja definida e divergencia CNPJ_DESCONHECIDO resolvida.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Cancelar venda
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/cancelar', methods=['POST'])
@require_hora_perm('vendas', 'apagar')
def vendas_cancelar(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        flash('Venda sem loja definida — apenas admin cancela.', 'warning')
        return redirect(url_for('hora.vendas_lista'))

    motivo = (request.form.get('motivo') or '').strip()
    try:
        venda_service.cancelar_venda(
            venda_id=venda.id,
            motivo=motivo,
            usuario=_operador_atual(),
        )
        flash('Venda cancelada. Chassis marcados como DEVOLVIDA.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Resolver divergencia (marca como tratada)
# ------------------------------------------------------------------------

@hora_bp.route(
    '/vendas/<int:venda_id>/divergencias/<int:div_id>/resolver',
    methods=['POST'],
)
@require_hora_perm('vendas', 'editar')
def vendas_resolver_divergencia(venda_id: int, div_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    is_ajax = request.is_json or request.headers.get('Accept') == 'application/json'

    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))

    # Venda sem loja (loja_id=NULL) so resolve por admin — mesma regra das
    # outras rotas desta venda (vendas_detalhe/editar/cancelar).
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'venda sem loja — apenas admin'}), 403
        flash('Venda sem loja definida — apenas admin resolve divergencias.', 'warning')
        return redirect(url_for('hora.vendas_lista'))

    div = HoraVendaDivergencia.query.get_or_404(div_id)
    if div.venda_id != venda.id:
        flash('Divergencia nao pertence a essa venda.', 'danger')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    try:
        venda_service.resolver_divergencia(
            divergencia_id=div_id,
            usuario=_operador_atual(),
        )
        flash('Divergencia marcada como resolvida.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))
