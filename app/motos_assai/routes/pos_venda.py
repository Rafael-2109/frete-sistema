"""Rotas de Pos-Venda do modulo Motos Assai.

URL prefix: /motos-assai/pos-venda (herdado do blueprint).

Telas:
  GET  /                                 -> listagem de motos vendidas com filtros
  GET  /ocorrencias/<chassi>             -> modal/pagina de ocorrencias de 1 chassi
                                            (HTML; aceita ?embed=1 para fragmento)
  POST /ocorrencias/<chassi>             -> AJAX: criar ocorrencia (JSON)
  PUT  /ocorrencias/<oc_id>              -> AJAX: atualizar ocorrencia (JSON)
  DELETE /ocorrencias/<oc_id>            -> AJAX: excluir ocorrencia (JSON)
  POST /ocorrencias/<oc_id>/anexos       -> AJAX: upload N anexos (multipart)
  GET  /anexos/<anexo_id>/visualizar     -> redirect presigned URL inline
  GET  /anexos/<anexo_id>/download       -> redirect presigned URL download
  DELETE /anexos/<anexo_id>              -> AJAX: excluir anexo (JSON)
  POST /ocorrencias/<oc_id>/gerar-pendencia -> AJAX: gera AssaiPendencia (JSON)
"""

from flask import (
    render_template, request, jsonify, redirect, current_app, abort, url_for,
)
from flask_login import login_required, current_user

from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    listar_motos_vendidas, contexto_moto_por_chassi,
    listar_ocorrencias, criar_ocorrencia, atualizar_ocorrencia, excluir_ocorrencia,
    adicionar_anexo, excluir_anexo,
    url_visualizacao_anexo, url_download_anexo,
    listar_lojas, listar_modelos,
    PosVendaValidationError,
    gerar_pendencia_de_ocorrencia, pendencias_da_ocorrencia,
    contar_pendencias_abertas_por_chassis,
    registrar_troca, listar_substitutos, TrocaGarantiaError,
)
from app.motos_assai.services.pendencia_service import PendenciaError
from app.motos_assai.models import (
    AssaiPosVendaOcorrencia, AssaiPosVendaOcorrenciaAnexo,
    CATEGORIA_LOJA, CATEGORIA_CLIENTE,
    AssaiMoto, AssaiNfQpa,
)


# ---------------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/pos-venda')
@login_required
@require_motos_assai
def pos_venda_lista():
    """Tela de listagem com filtros (NF, loja, modelo, cor, chassi)."""
    nf_numero = (request.args.get('nf') or '').strip() or None
    loja_id_raw = (request.args.get('loja_id') or '').strip()
    modelo_id_raw = (request.args.get('modelo_id') or '').strip()
    cor = (request.args.get('cor') or '').strip() or None
    chassi = (request.args.get('chassi') or '').strip() or None

    try:
        loja_id = int(loja_id_raw) if loja_id_raw else None
    except ValueError:
        loja_id = None
    try:
        modelo_id = int(modelo_id_raw) if modelo_id_raw else None
    except ValueError:
        modelo_id = None

    linhas = listar_motos_vendidas(
        nf_numero=nf_numero,
        loja_id=loja_id,
        modelo_id=modelo_id,
        cor=cor,
        chassi=chassi,
        limit=500,
    )
    # Enriquece cada linha com a contagem de pendencias abertas do chassi
    # (geradas via pos-venda ou qualquer outra origem) — badge "Pendências (N)".
    # Batched em 1 query (evita N+1 — ate 500 round-trips antes desta troca).
    contagens = contar_pendencias_abertas_por_chassis([linha.chassi for linha in linhas])
    for linha in linhas:
        chave = (linha.chassi or '').strip().upper()
        linha.qtd_pendencias_abertas = contagens.get(chave, 0)

    return render_template(
        'motos_assai/pos_venda/lista.html',
        linhas=linhas,
        lojas=listar_lojas(somente_ativas=True),
        modelos=listar_modelos(somente_ativos=True),
        filtros={
            'nf': nf_numero or '',
            'loja_id': loja_id or '',
            'modelo_id': modelo_id or '',
            'cor': cor or '',
            'chassi': chassi or '',
        },
    )


# ---------------------------------------------------------------------------
# Ocorrencias por chassi (modal HTML + CRUD JSON)
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/pos-venda/ocorrencias/<chassi>', methods=['GET'])
@login_required
@require_motos_assai
def pos_venda_ocorrencias(chassi):
    """Pagina/fragmento com 2 secoes (Loja x Cliente) de ocorrencias do chassi.

    ?embed=1 retorna apenas o conteudo do modal (sem base).
    """
    chassi = (chassi or '').strip()
    if not chassi:
        abort(404)

    ctx = contexto_moto_por_chassi(chassi)
    if not ctx:
        abort(404)

    todas = listar_ocorrencias(chassi)
    loja = [o for o in todas if o.categoria == CATEGORIA_LOJA]
    cliente = [o for o in todas if o.categoria == CATEGORIA_CLIENTE]
    # Pendencias ja geradas por ocorrencia (Spec 2 Task 13 — acompanhar).
    pendencias_map = {oc.id: pendencias_da_ocorrencia(oc.id) for oc in todas}

    template = (
        'motos_assai/pos_venda/_modal_ocorrencias.html'
        if request.args.get('embed') == '1'
        else 'motos_assai/pos_venda/ocorrencias.html'
    )
    return render_template(
        template,
        chassi=chassi,
        ctx=ctx,
        oc_loja=loja,
        oc_cliente=cliente,
        pendencias_map=pendencias_map,
        CATEGORIA_LOJA=CATEGORIA_LOJA,
        CATEGORIA_CLIENTE=CATEGORIA_CLIENTE,
    )


@motos_assai_bp.route('/pos-venda/ocorrencias/<chassi>', methods=['POST'])
@login_required
@require_motos_assai
def pos_venda_ocorrencia_criar(chassi):
    """POST AJAX: cria nova ocorrencia para o chassi.

    Body JSON: {categoria: 'LOJA'|'CLIENTE', descricao: str}
    """
    data = request.get_json(silent=True) or request.form
    categoria = (data.get('categoria') or '').strip().upper()
    descricao = (data.get('descricao') or '').strip()
    try:
        oc = criar_ocorrencia(
            chassi=chassi,
            categoria=categoria,
            descricao=descricao,
            operador_id=current_user.id,
        )
    except PosVendaValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception:
        current_app.logger.exception('Erro ao criar ocorrencia pos-venda')
        return jsonify({'ok': False, 'erro': 'Erro interno ao criar ocorrencia'}), 500

    return jsonify({
        'ok': True,
        'ocorrencia': _serialize_ocorrencia(oc),
    })


@motos_assai_bp.route('/pos-venda/ocorrencias/<int:ocorrencia_id>', methods=['PUT', 'POST'])
@login_required
@require_motos_assai
def pos_venda_ocorrencia_atualizar(ocorrencia_id):
    """PUT (ou POST com _method=PUT) atualiza descricao/categoria."""
    data = request.get_json(silent=True) or request.form
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    if categoria:
        categoria = categoria.strip().upper()
    try:
        oc = atualizar_ocorrencia(
            ocorrencia_id=ocorrencia_id,
            descricao=descricao,
            categoria=categoria,
            operador_id=current_user.id,
        )
    except PosVendaValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception:
        current_app.logger.exception('Erro ao atualizar ocorrencia')
        return jsonify({'ok': False, 'erro': 'Erro interno'}), 500
    return jsonify({'ok': True, 'ocorrencia': _serialize_ocorrencia(oc)})


@motos_assai_bp.route('/pos-venda/ocorrencias/<int:ocorrencia_id>', methods=['DELETE'])
@login_required
@require_motos_assai
def pos_venda_ocorrencia_excluir(ocorrencia_id):
    """DELETE AJAX: exclui ocorrencia + anexos (S3 best-effort)."""
    try:
        excluir_ocorrencia(ocorrencia_id)
    except PosVendaValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 404
    except Exception:
        current_app.logger.exception('Erro ao excluir ocorrencia')
        return jsonify({'ok': False, 'erro': 'Erro interno'}), 500
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Gerar pendencia a partir de uma ocorrencia (Spec 2 Task 13)
# ---------------------------------------------------------------------------

@motos_assai_bp.route(
    '/pos-venda/ocorrencias/<int:oc_id>/gerar-pendencia', methods=['POST']
)
@login_required
@require_motos_assai
def pos_venda_gerar_pendencia(oc_id):
    """POST AJAX: gera uma AssaiPendencia a partir de uma ocorrencia pos-venda.

    Body JSON/form: {categoria: 'AVARIA'|'FALTA_PECA'|'REVISAO', retorno_fisico: bool}
    Origem (POS_VENDA_LOJA/_CLIENTE) e derivada da categoria da ocorrencia, nao
    do body. Rota commita (service so add+flush).
    """
    data = request.get_json(silent=True) or request.form
    categoria = (data.get('categoria') or '').strip().upper()
    retorno_fisico = str(data.get('retorno_fisico')) in ('1', 'true', 'on', 'True')

    try:
        ficha = gerar_pendencia_de_ocorrencia(
            ocorrencia_id=oc_id,
            categoria=categoria,
            retorno_fisico=retorno_fisico,
            operador_id=current_user.id,
        )
        db.session.commit()
    except (PosVendaValidationError, PendenciaError) as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Erro ao gerar pendencia de ocorrencia pos-venda')
        return jsonify({'ok': False, 'erro': 'Erro interno ao gerar pendência'}), 500

    return jsonify({
        'ok': True,
        'pendencia_id': ficha.id,
        'pendencia': {
            'id': ficha.id,
            'categoria': ficha.categoria,
            'esta_aberta': ficha.esta_aberta,
            'url': url_for('motos_assai.pendencia_detalhe', pid=ficha.id),
        },
    })


# ---------------------------------------------------------------------------
# Troca em Garantia
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/pos-venda/troca/<chassi_a>', methods=['GET'])
@login_required
@require_motos_assai
def pos_venda_troca_form(chassi_a):
    """Tela de registro de troca em garantia para a moto defeituosa (A)."""
    chassi_a = (chassi_a or '').strip().upper()
    ctx = contexto_moto_por_chassi(chassi_a)
    if not ctx:
        abort(404)
    moto_a = AssaiMoto.query.filter_by(chassi=chassi_a).first()
    if not moto_a:
        abort(404)
    nfs = (
        AssaiNfQpa.query
        .join(AssaiNfQpa.itens)
        .filter_by(chassi=chassi_a)
        .all()
    )
    return render_template(
        'motos_assai/pos_venda/troca_garantia.html',
        chassi_a=chassi_a, ctx=ctx, modelo_id=moto_a.modelo_id, nfs=nfs,
    )


@motos_assai_bp.route('/pos-venda/troca/<chassi_a>/substitutos', methods=['GET'])
@login_required
@require_motos_assai
def pos_venda_troca_substitutos(chassi_a):
    """AJAX: candidatos a substituto (B) do mesmo modelo de A."""
    chassi_a = (chassi_a or '').strip().upper()
    moto_a = AssaiMoto.query.filter_by(chassi=chassi_a).first()
    if not moto_a:
        return jsonify({'ok': False, 'erro': 'moto A nao encontrada'}), 404
    return jsonify(listar_substitutos(moto_a.modelo_id))


@motos_assai_bp.route('/pos-venda/troca/<chassi_a>', methods=['POST'])
@login_required
@require_motos_assai
def pos_venda_troca_registrar(chassi_a):
    """POST AJAX: executa a troca A->B. Body JSON: {chassi_b, nf_id, motivo}."""
    data = request.get_json(silent=True) or request.form
    chassi_b = (data.get('chassi_b') or '').strip().upper()
    motivo = (data.get('motivo') or '').strip()
    try:
        nf_id = int(data.get('nf_id'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'erro': 'nf_id invalido'}), 400
    try:
        res = registrar_troca(
            nf_id=nf_id, chassi_a=chassi_a, chassi_b=chassi_b,
            operador_id=current_user.id, motivo=motivo, dry_run=False,
        )
    except TrocaGarantiaError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception:
        current_app.logger.exception('Erro ao registrar troca em garantia')
        return jsonify({'ok': False, 'erro': 'Erro interno ao registrar troca'}), 500
    return jsonify(res)


# ---------------------------------------------------------------------------
# Anexos
# ---------------------------------------------------------------------------

@motos_assai_bp.route(
    '/pos-venda/ocorrencias/<int:ocorrencia_id>/anexos', methods=['POST']
)
@login_required
@require_motos_assai
def pos_venda_anexo_upload(ocorrencia_id):
    """POST multipart: upload de 1 ou N anexos para a ocorrencia.

    Aceita field 'arquivos' (lista) ou 'arquivo' (1).
    """
    arquivos = request.files.getlist('arquivos')
    if not arquivos:
        single = request.files.get('arquivo')
        arquivos = [single] if single else []
    arquivos = [a for a in arquivos if a and getattr(a, 'filename', '')]
    if not arquivos:
        return jsonify({'ok': False, 'erro': 'nenhum arquivo enviado'}), 400

    salvos, erros = [], []
    for f in arquivos:
        try:
            anexo = adicionar_anexo(
                ocorrencia_id=ocorrencia_id,
                arquivo=f,
                operador_id=current_user.id,
            )
            salvos.append(_serialize_anexo(anexo))
        except PosVendaValidationError as e:
            erros.append({'arquivo': f.filename, 'erro': str(e)})
        except Exception as e:
            current_app.logger.exception('Erro ao salvar anexo pos-venda')
            erros.append({'arquivo': f.filename, 'erro': 'Erro interno ao salvar'})

    return jsonify({
        'ok': len(salvos) > 0,
        'anexos': salvos,
        'erros': erros,
    })


@motos_assai_bp.route('/pos-venda/anexos/<int:anexo_id>/visualizar')
@login_required
@require_motos_assai
def pos_venda_anexo_visualizar(anexo_id):
    """Redirect para presigned URL inline (1h)."""
    anexo = AssaiPosVendaOcorrenciaAnexo.query.get_or_404(anexo_id)
    url = url_visualizacao_anexo(anexo.s3_key)
    if not url:
        abort(404)
    return redirect(url)


@motos_assai_bp.route('/pos-venda/anexos/<int:anexo_id>/download')
@login_required
@require_motos_assai
def pos_venda_anexo_download(anexo_id):
    """Redirect para presigned URL com Content-Disposition: attachment."""
    anexo = AssaiPosVendaOcorrenciaAnexo.query.get_or_404(anexo_id)
    url = url_download_anexo(anexo.s3_key, anexo.nome_original)
    if not url:
        # fallback inline
        url = url_visualizacao_anexo(anexo.s3_key)
    if not url:
        abort(404)
    return redirect(url)


@motos_assai_bp.route('/pos-venda/anexos/<int:anexo_id>', methods=['DELETE'])
@login_required
@require_motos_assai
def pos_venda_anexo_excluir(anexo_id):
    """DELETE AJAX: exclui anexo (DB + S3 best-effort)."""
    try:
        excluir_anexo(anexo_id)
    except PosVendaValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 404
    except Exception:
        current_app.logger.exception('Erro ao excluir anexo')
        return jsonify({'ok': False, 'erro': 'Erro interno'}), 500
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Helpers de serializacao
# ---------------------------------------------------------------------------

def _serialize_ocorrencia(oc: AssaiPosVendaOcorrencia) -> dict:
    return {
        'id': oc.id,
        'chassi': oc.chassi,
        'categoria': oc.categoria,
        'descricao': oc.descricao,
        'criado_em': oc.criado_em.strftime('%d/%m/%Y %H:%M') if oc.criado_em else None,
        'criado_por': getattr(oc.criado_por, 'nome', None) or '',
        'atualizado_em': (
            oc.atualizado_em.strftime('%d/%m/%Y %H:%M') if oc.atualizado_em else None
        ),
        'atualizado_por': (
            getattr(oc.atualizado_por, 'nome', None) or ''
        ) if oc.atualizado_por_id else '',
        'anexos': [_serialize_anexo(a) for a in oc.anexos],
    }


def _serialize_anexo(a: AssaiPosVendaOcorrenciaAnexo) -> dict:
    return {
        'id': a.id,
        'ocorrencia_id': a.ocorrencia_id,
        'tipo': a.tipo,
        'nome_original': a.nome_original,
        'criado_em': a.criado_em.strftime('%d/%m/%Y %H:%M') if a.criado_em else None,
        'visualizar_url': url_for(
            'motos_assai.pos_venda_anexo_visualizar', anexo_id=a.id,
        ),
        'download_url': url_for(
            'motos_assai.pos_venda_anexo_download', anexo_id=a.id,
        ),
    }
