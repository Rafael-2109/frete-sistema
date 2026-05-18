"""Rotas para CCe (Carta de Correcao Eletronica) como entidade avulsa.

Feature 2026-05-13:
- Upload avulso: PDF da CCe pode chegar ANTES da NF correspondente
- Se NF ja existe → aplica chassis imediatamente
- Se NF nao existe → registra como PENDENTE; ao importar a NF, match reverso aplica

Endpoints:
- GET  /motos-assai/cce             — lista (com filtros por status/tipo/tem_nf)
- GET  /motos-assai/cce/upload      — formulario
- POST /motos-assai/cce/upload      — processa upload de 1+ PDFs
- GET  /motos-assai/cce/<id>        — detalhe
"""
from flask import (
    render_template, request, redirect, url_for, flash, jsonify,
    current_app, abort,
)
from flask_login import login_required, current_user

from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadCceForm
from app.motos_assai.models import (
    AssaiCce,
    CCE_STATUS_PENDENTE, CCE_STATUS_APLICADA,
    CCE_STATUS_IGNORADA, CCE_STATUS_ERRO,
    CCE_STATUS_VALIDOS,
)
from app.motos_assai.services.cce_service import (
    registrar_cce, CceServiceError,
)
from app.utils.file_storage import FileStorage


@motos_assai_bp.route('/cce')
@login_required
@require_motos_assai
def cce_lista():
    """Lista de CCes registradas com filtros."""
    status_filtro = request.args.get('status', '').strip().upper()
    tipo_filtro = request.args.get('tipo', '').strip().upper()
    tem_nf_filtro = request.args.get('tem_nf', '').strip().lower()
    busca = request.args.get('q', '').strip()

    q = AssaiCce.query

    if status_filtro and status_filtro in CCE_STATUS_VALIDOS:
        q = q.filter(AssaiCce.status == status_filtro)
    if tipo_filtro in ('CHASSI', 'DUPLICATAS', 'ENDERECO', 'OUTRO'):
        q = q.filter(AssaiCce.tipo_correcao == tipo_filtro)
    if tem_nf_filtro in ('sim', 'true', '1'):
        q = q.filter(AssaiCce.tem_nf == True)  # noqa: E712
    elif tem_nf_filtro in ('nao', 'false', '0'):
        q = q.filter(AssaiCce.tem_nf == False)  # noqa: E712
    if busca:
        like = f'%{busca}%'
        q = q.filter(
            (AssaiCce.protocolo_cce.ilike(like))
            | (AssaiCce.chave_nfe.ilike(like))
            | (AssaiCce.numero_nf_referenciada.ilike(like))
            | (AssaiCce.numero_cce.ilike(like))
        )

    cces = q.order_by(AssaiCce.criado_em.desc()).limit(500).all()

    # Estatisticas para cabecalho
    stats = {
        'total': AssaiCce.query.count(),
        'pendentes': AssaiCce.query.filter_by(status=CCE_STATUS_PENDENTE).count(),
        'aplicadas': AssaiCce.query.filter_by(status=CCE_STATUS_APLICADA).count(),
        'ignoradas': AssaiCce.query.filter_by(status=CCE_STATUS_IGNORADA).count(),
        'erros': AssaiCce.query.filter_by(status=CCE_STATUS_ERRO).count(),
    }

    return render_template(
        'motos_assai/cce/lista.html',
        cces=cces,
        stats=stats,
        status_filtro=status_filtro,
        tipo_filtro=tipo_filtro,
        tem_nf_filtro=tem_nf_filtro,
        busca=busca,
    )


@motos_assai_bp.route('/cce/upload', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def cce_upload():
    """Upload avulso de PDF(s) da CCe. Aceita 1 ou N arquivos."""
    form = UploadCceForm()

    if form.validate_on_submit():
        arquivos = form.pdfs.data or []
        if not arquivos:
            flash('Selecione ao menos 1 PDF.', 'warning')
            return redirect(url_for('motos_assai.cce_upload'))

        resultados = []
        for arquivo in arquivos:
            try:
                pdf_bytes = arquivo.read()
                resultado = registrar_cce(
                    pdf_bytes=pdf_bytes,
                    nome_arquivo=arquivo.filename or 'cce.pdf',
                    operador_id=current_user.id,
                    divergencia_id=None,
                )
                resultados.append({
                    'arquivo': arquivo.filename,
                    'ok': resultado['ok'],
                    'cce_id': resultado['cce_id'],
                    'status': resultado['status'],
                    'tipo_correcao': resultado.get('tipo_correcao'),
                    'tem_nf': resultado.get('tem_nf'),
                    'mensagem': resultado['mensagem'],
                    'duplicada': resultado.get('duplicada', False),
                })
            except CceServiceError as e:
                resultados.append({
                    'arquivo': arquivo.filename,
                    'ok': False,
                    'cce_id': None,
                    'status': 'ERRO',
                    'mensagem': str(e),
                    'duplicada': False,
                })
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception(
                    'cce_upload arquivo %s falhou', arquivo.filename,
                )
                resultados.append({
                    'arquivo': arquivo.filename,
                    'ok': False,
                    'cce_id': None,
                    'status': 'ERRO',
                    'mensagem': f'Erro interno: {e}',
                    'duplicada': False,
                })

        # 1 arquivo + sucesso → redireciona para detalhe (UX limpa)
        if len(resultados) == 1 and resultados[0]['ok'] and resultados[0]['cce_id']:
            r = resultados[0]
            flash(r['mensagem'], 'success' if r['status'] == 'APLICADA' else 'info')
            return redirect(url_for('motos_assai.cce_detalhe', cce_id=r['cce_id']))

        # N arquivos ou erros → tela de resultado
        resumo = {
            'total': len(resultados),
            'aplicadas': sum(1 for r in resultados if r['status'] == 'APLICADA'),
            'pendentes': sum(1 for r in resultados if r['status'] == 'PENDENTE'),
            'ignoradas': sum(1 for r in resultados if r['status'] == 'IGNORADA'),
            'duplicadas': sum(1 for r in resultados if r.get('duplicada')),
            'erros': sum(1 for r in resultados if not r['ok']),
        }
        return render_template(
            'motos_assai/cce/upload_resultado.html',
            resultados=resultados,
            resumo=resumo,
        )

    return render_template('motos_assai/cce/upload.html', form=form)


@motos_assai_bp.route('/cce/<int:cce_id>')
@login_required
@require_motos_assai
def cce_detalhe(cce_id):
    """Detalhe de uma CCe com dados parseados, NF vinculada e ciclo de vida."""
    cce = AssaiCce.query.get_or_404(cce_id)

    # Tentar re-resolver NF se ainda tem_nf=False (operador pode ter importado
    # NF depois e quer ver status atualizado)
    nf_atual = cce.nf
    if not nf_atual and cce.status == CCE_STATUS_PENDENTE:
        from app.motos_assai.services.cce_service import _resolver_nf_da_cce
        nf_atual = _resolver_nf_da_cce(cce)

    return render_template(
        'motos_assai/cce/detalhe.html',
        cce=cce,
        nf_atual=nf_atual,
    )


@motos_assai_bp.route('/cce/<int:cce_id>/pdf')
@login_required
@require_motos_assai
def cce_pdf(cce_id):
    """Redireciona para presigned URL S3 (ou serve local) do PDF original da CCe.

    Bloqueia se a CCe nao tem `pdf_s3_key` (upload S3 falhou no registro).
    """
    cce = AssaiCce.query.get_or_404(cce_id)
    if not cce.pdf_s3_key:
        flash(
            f'CCe {cce.protocolo_cce} nao tem PDF armazenado '
            '(upload S3 falhou no registro).',
            'warning',
        )
        return redirect(url_for('motos_assai.cce_detalhe', cce_id=cce_id))

    storage = FileStorage()
    if not storage.file_exists(cce.pdf_s3_key):
        current_app.logger.warning(
            'pdf_s3_key da CCe %s sumiu do storage: %s', cce_id, cce.pdf_s3_key,
        )
        flash('Arquivo PDF nao encontrado no storage.', 'danger')
        return redirect(url_for('motos_assai.cce_detalhe', cce_id=cce_id))

    if storage.use_s3 and not cce.pdf_s3_key.startswith('uploads/'):
        url = storage.get_presigned_url(cce.pdf_s3_key, expires_in=300)
        if not url:
            abort(500)
        return redirect(url)

    url = storage.get_file_url(cce.pdf_s3_key)
    if not url:
        abort(500)
    return redirect(url)


@motos_assai_bp.route('/cce/<int:cce_id>/tentar-aplicar', methods=['POST'])
@login_required
@require_motos_assai
def cce_tentar_aplicar(cce_id):
    """Re-tenta aplicar uma CCe PENDENTE (caso NF tenha chegado depois e o
    match reverso nao tenha rodado por algum motivo)."""
    cce = AssaiCce.query.get_or_404(cce_id)

    if cce.status not in (CCE_STATUS_PENDENTE, CCE_STATUS_ERRO):
        return jsonify({
            'ok': False,
            'erro': (
                f'CCe status={cce.status} — apenas PENDENTE ou ERRO podem ser '
                'reprocessadas.'
            ),
        }), 400

    # Fix H3 (code review 2026-05-13): bloquear retry se chassis ja foram
    # aplicados anteriormente. Caso edge: alguem reseta status manualmente
    # para PENDENTE/ERRO via DB console depois de APLICADA — retry faria
    # double-swap (B -> A em vez de A -> B), corrompendo dados.
    if cce.chassis_aplicados:
        return jsonify({
            'ok': False,
            'erro': (
                f'CCe {cce.protocolo_cce} ja possui {len(cce.chassis_aplicados)} '
                'chassis aplicados em historico. Retry bloqueado para evitar '
                'double-swap. Investigue o motivo do status atual antes de prosseguir.'
            ),
            'chassis_ja_aplicados': cce.chassis_aplicados,
        }), 400

    try:
        from app import db
        from app.motos_assai.services.cce_service import _tentar_aplicar_cce
        resultado = _tentar_aplicar_cce(
            cce, operador_id=current_user.id, divergencia_id=cce.divergencia_origem_id,
        )
        db.session.commit()
        return jsonify({
            'ok': True,
            'status': cce.status,
            'tem_nf': cce.tem_nf,
            'mensagem': resultado['mensagem'],
        })
    except Exception as e:
        from app import db
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception('cce_tentar_aplicar(%s) falhou', cce_id)
        return jsonify({'ok': False, 'erro': str(e)}), 500
