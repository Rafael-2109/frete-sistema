from flask import render_template, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import gerar_excel_qpa
from app.motos_assai.models import (
    AssaiSeparacao, SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA,
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
    bytes_xlsx, s3_key = gerar_excel_qpa(separacao_id, current_user.id)
    return Response(
        bytes_xlsx,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="solicitacao_qpa_{separacao_id}.xlsx"',
        },
    )
