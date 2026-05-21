"""Rotas de devolucao por NF de venda Q.P.A.

Endpoints:
- GET  /faturamento/nfs/<nf_id>/devolucao        : tela do form de devolucao
- POST /faturamento/nfs/<nf_id>/devolucao        : cria devolucao
- GET  /devolucoes                                : listagem global de NFds
- GET  /devolucoes/<dev_id>                       : detalhe de 1 NFd
- GET  /devolucoes/anexo/<anexo_id>/view          : presigned URL inline
- GET  /devolucoes/anexo/<anexo_id>/download      : presigned URL download
- GET  /devolucoes/chassi/<chassi>/pendencias     : AJAX modal pendencias

Todas usam `@require_motos_assai` + `@login_required`.
"""
from datetime import datetime

from flask import (
    render_template, redirect, url_for, flash, request, jsonify,
    current_app, abort,
)
from flask_login import login_required, current_user

from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import DevolucaoNfForm
from app.motos_assai.models import (
    AssaiNfQpa, AssaiDevolucaoAnexo,
)
from app.motos_assai.services import (
    criar_devolucao, listar_devolucoes, listar_devolucoes_da_nf,
    get_devolucao, pendencias_do_chassi, itens_da_nf_para_tela,
    DevolucaoValidationError,
)
from app.motos_assai.services.devolucao_service import (
    url_visualizacao_anexo as _url_view_devolucao,
    url_download_anexo as _url_dl_devolucao,
)
from app.motos_assai.services.modelo_service import listar_modelos


# ============================================================================
# Submit da devolucao (modal embutido na tela detalhe da NF)
# ============================================================================

@motos_assai_bp.route(
    '/faturamento/nfs/<int:nf_id>/devolucao', methods=['POST'],
)
@login_required
@require_motos_assai
def devolucao_form(nf_id):
    """Submit da devolucao via modal embutido em faturamento_nf_detalhe.html.

    NAO renderiza tela propria — sempre retorna redirect (sucesso ->
    devolucao_detalhe, erro/validacao -> faturamento_nf_detalhe).
    """
    nf = AssaiNfQpa.query.get_or_404(nf_id)

    if nf.status_match == 'CANCELADA':
        flash(
            f'NF {nf.numero} esta CANCELADA — devolucao nao permitida.',
            'danger',
        )
        return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=nf_id))

    form = DevolucaoNfForm()
    if not form.validate_on_submit():
        # CSRF invalido ou campos obrigatorios — flash + volta para NF
        for field, errors in form.errors.items():
            for err in errors:
                flash(f'{field}: {err}', 'danger')
        return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=nf_id))

    chassis_selecionados = request.form.getlist('chassis_selecionados')
    try:
        devolucao = criar_devolucao(
            nf_id=nf_id,
            numero_nfd=form.numero_nfd.data,
            data_devolucao=form.data_devolucao.data,
            motivo=form.motivo.data,
            chassis=chassis_selecionados,
            anexos=form.anexos.data or [],
            operador_id=current_user.id,
        )
        flash(
            f'Devolucao NFd {devolucao.numero_nfd} registrada '
            f'({len(devolucao.itens)} chassis).',
            'success',
        )
        return redirect(url_for(
            'motos_assai.devolucao_detalhe', devolucao_id=devolucao.id,
        ))
    except DevolucaoValidationError as e:
        flash(str(e), 'danger')
    except Exception as e:
        current_app.logger.exception(
            'Erro ao criar devolucao da NF %s', nf_id,
        )
        flash(f'Erro interno: {e}', 'danger')

    return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=nf_id))


# ============================================================================
# Listagem global de devolucoes
# ============================================================================

@motos_assai_bp.route('/devolucoes')
@login_required
@require_motos_assai
def devolucoes_lista():
    """Listagem global de NFds com filtros."""
    nf_numero = request.args.get('nf_numero', '').strip() or None
    numero_nfd = request.args.get('numero_nfd', '').strip() or None
    chassi = request.args.get('chassi', '').strip() or None
    modelo_id = request.args.get('modelo_id', type=int) or None
    data_inicio_s = request.args.get('data_inicio', '').strip()
    data_fim_s = request.args.get('data_fim', '').strip()

    data_inicio = None
    data_fim = None
    try:
        if data_inicio_s:
            data_inicio = datetime.strptime(data_inicio_s, '%Y-%m-%d').date()
        if data_fim_s:
            data_fim = datetime.strptime(data_fim_s, '%Y-%m-%d').date()
    except ValueError:
        flash('Data invalida nos filtros (use AAAA-MM-DD).', 'warning')

    devolucoes = listar_devolucoes(
        nf_numero=nf_numero,
        numero_nfd=numero_nfd,
        chassi=chassi,
        modelo_id=modelo_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    return render_template(
        'motos_assai/devolucao/lista.html',
        devolucoes=devolucoes,
        modelos=listar_modelos(somente_ativos=True),
        filtros={
            'nf_numero': nf_numero or '',
            'numero_nfd': numero_nfd or '',
            'chassi': chassi or '',
            'modelo_id': modelo_id,
            'data_inicio': data_inicio_s,
            'data_fim': data_fim_s,
        },
    )


@motos_assai_bp.route('/devolucoes/<int:devolucao_id>')
@login_required
@require_motos_assai
def devolucao_detalhe(devolucao_id):
    """Detalhe de uma NFd com chassis e anexos."""
    devolucao = get_devolucao(devolucao_id)
    if not devolucao:
        abort(404)

    return render_template(
        'motos_assai/devolucao/detalhe.html',
        devolucao=devolucao,
    )


# ============================================================================
# Anexos: visualizacao e download
# ============================================================================

@motos_assai_bp.route('/devolucoes/anexo/<int:anexo_id>/view')
@login_required
@require_motos_assai
def devolucao_anexo_view(anexo_id):
    """Redireciona para presigned URL de visualizacao inline."""
    anexo = AssaiDevolucaoAnexo.query.get_or_404(anexo_id)
    url = _url_view_devolucao(anexo.s3_key)
    if not url:
        flash('Anexo nao acessivel no momento.', 'danger')
        return redirect(url_for(
            'motos_assai.devolucao_detalhe', devolucao_id=anexo.devolucao_id,
        ))
    return redirect(url)


@motos_assai_bp.route('/devolucoes/anexo/<int:anexo_id>/download')
@login_required
@require_motos_assai
def devolucao_anexo_download(anexo_id):
    """Redireciona para presigned URL com Content-Disposition: attachment."""
    anexo = AssaiDevolucaoAnexo.query.get_or_404(anexo_id)
    url = _url_dl_devolucao(anexo.s3_key, anexo.nome_original)
    if not url:
        flash('Anexo nao acessivel no momento.', 'danger')
        return redirect(url_for(
            'motos_assai.devolucao_detalhe', devolucao_id=anexo.devolucao_id,
        ))
    return redirect(url)


# ============================================================================
# AJAX: pendencias do chassi (modal "Pendencias(qtd)")
# ============================================================================

@motos_assai_bp.route('/devolucoes/chassi/<chassi>/pendencias')
@login_required
@require_motos_assai
def devolucao_pendencias_chassi(chassi):
    """Retorna JSON com historico de pendencias do chassi para popular modal."""
    payload = pendencias_do_chassi(chassi)
    return jsonify(payload)
