from flask import render_template, redirect, url_for, flash, Response, current_app
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import gerar_excel_qpa
from app.motos_assai.models import (
    AssaiSeparacao, AssaiNfQpa, AssaiNfQpaItem,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA,
)
from app.motos_assai.forms import UploadNfQpaForm
from app.motos_assai.services.parsers.nf_qpa_adapter import (
    importar_nf_qpa, NfQpaParseError, NfQpaJaImportadaError,
)


@motos_assai_bp.route('/faturamento')
@login_required
@require_motos_assai
def faturamento_lista():
    seps = (
        AssaiSeparacao.query
        .filter(AssaiSeparacao.status.in_([SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA]))
        .order_by(AssaiSeparacao.fechada_em.desc())
        .limit(250)
        .all()
    )
    return render_template('motos_assai/faturamento/lista_separacoes.html', separacoes=seps)


@motos_assai_bp.route('/faturamento/separacao/<int:separacao_id>/excel')
@login_required
@require_motos_assai
def faturamento_solicitacao_excel(separacao_id):
    try:
        bytes_xlsx, s3_key = gerar_excel_qpa(separacao_id, current_user.id)
    except ValueError as e:
        # H3: separação em status inválido para geração de Excel
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai.faturamento_lista'))
    # H1: s3_key pode ser None se FileStorage falhar — log mas não bloquear download
    if not s3_key:
        current_app.logger.error('S3 save falhou para separacao %s', separacao_id)
    return Response(
        bytes_xlsx,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="solicitacao_qpa_{separacao_id}.xlsx"',
        },
    )


@motos_assai_bp.route('/faturamento/separacao/<int:separacao_id>/upload-nf', methods=['GET', 'POST'])
@motos_assai_bp.route('/faturamento/upload-nf', methods=['GET', 'POST'], defaults={'separacao_id': None})
@login_required
@require_motos_assai
def faturamento_upload_nf(separacao_id):
    """Upload de 1 ou N PDFs de NF Q.P.A.

    - 1 PDF + sucesso → redirect para detalhe (UX antiga preservada).
    - 1 PDF + erro/duplicada → flash + render upload novamente.
    - N PDFs (qualquer combinação de sucesso/erro) → render relatório batch.
    """
    form = UploadNfQpaForm()
    if form.validate_on_submit():
        arquivos = form.pdfs.data or []
        # MultipleFileField pode entregar lista com 1 FileStorage vazio em alguns edge cases
        arquivos = [f for f in arquivos if f and getattr(f, 'filename', '')]
        resultados = []  # cada item: dict(filename, status, nf, erro)
        for f in arquivos:
            try:
                nf = importar_nf_qpa(
                    pdf_bytes=f.read(),
                    nome_arquivo=f.filename,
                    importada_por_id=current_user.id,
                )
                resultados.append({
                    'filename': f.filename,
                    'status': 'ok',
                    'status_match': nf.status_match,
                    'nf_id': nf.id,
                    'nf_numero': nf.numero,
                    'erro': None,
                })
            except NfQpaJaImportadaError as e:
                resultados.append({
                    'filename': f.filename,
                    'status': 'duplicada',
                    'status_match': None,
                    'nf_id': None,
                    'nf_numero': None,
                    'erro': str(e),
                })
            except NfQpaParseError as e:
                resultados.append({
                    'filename': f.filename,
                    'status': 'erro_parse',
                    'status_match': None,
                    'nf_id': None,
                    'nf_numero': None,
                    'erro': str(e),
                })

        # 1 arquivo + sucesso → preserva UX antiga
        if len(resultados) == 1 and resultados[0]['status'] == 'ok':
            r = resultados[0]
            flash(f'NF {r["nf_numero"]} importada — status: {r["status_match"]}', 'success')
            return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=r['nf_id']))

        # 1 arquivo + erro → flash e re-render upload
        if len(resultados) == 1 and resultados[0]['status'] != 'ok':
            r = resultados[0]
            categoria = 'warning' if r['status'] == 'duplicada' else 'danger'
            prefix = '' if r['status'] == 'duplicada' else 'Erro ao parsear NF: '
            flash(f'{prefix}{r["erro"]}', categoria)
            return render_template('motos_assai/faturamento/upload_nf.html', form=form, separacao_id=separacao_id)

        # N arquivos → relatório batch
        resumo = {
            'total': len(resultados),
            'ok': sum(1 for r in resultados if r['status'] == 'ok'),
            'duplicada': sum(1 for r in resultados if r['status'] == 'duplicada'),
            'erro_parse': sum(1 for r in resultados if r['status'] == 'erro_parse'),
        }
        return render_template(
            'motos_assai/faturamento/upload_nf_resultado.html',
            resultados=resultados, resumo=resumo, separacao_id=separacao_id,
        )

    return render_template('motos_assai/faturamento/upload_nf.html', form=form, separacao_id=separacao_id)


@motos_assai_bp.route('/faturamento/nfs/<int:nf_id>')
@login_required
@require_motos_assai
def faturamento_nf_detalhe(nf_id):
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    items = AssaiNfQpaItem.query.filter_by(nf_id=nf_id).all()
    return render_template('motos_assai/faturamento/nf_detalhe.html', nf=nf, items=items)
