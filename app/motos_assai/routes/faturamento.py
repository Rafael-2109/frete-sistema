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
    form = UploadNfQpaForm()
    if form.validate_on_submit():
        f = form.pdf.data
        try:
            nf = importar_nf_qpa(
                pdf_bytes=f.read(),
                nome_arquivo=f.filename,
                importada_por_id=current_user.id,
            )
            flash(f'NF {nf.numero} importada — status: {nf.status_match}', 'success')
            return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=nf.id))
        except NfQpaJaImportadaError as e:
            flash(str(e), 'warning')
        except NfQpaParseError as e:
            flash(f'Erro ao parsear NF: {e}', 'danger')
    return render_template('motos_assai/faturamento/upload_nf.html', form=form)


@motos_assai_bp.route('/faturamento/nfs/<int:nf_id>')
@login_required
@require_motos_assai
def faturamento_nf_detalhe(nf_id):
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    items = AssaiNfQpaItem.query.filter_by(nf_id=nf_id).all()
    return render_template('motos_assai/faturamento/nf_detalhe.html', nf=nf, items=items)
