"""
Rotas de Pendências Financeiras (Legadas)
Importação, consulta, exportação e exclusão de pendências
"""

import os
import pandas as pd
from flask import render_template, request, redirect, flash, send_from_directory, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from app import db
from app.utils.timezone import agora_utc_naive
from app.financeiro.models import PendenciaFinanceiraNF
from app.financeiro.forms import UploadExcelForm
from app.monitoramento.models import EntregaMonitorada, RegistroLogEntrega
from app.financeiro.routes import financeiro_bp, UPLOAD_FOLDER


@financeiro_bp.route('/importar-pendencias', methods=['GET', 'POST'])
@login_required
def importar_pendencias():
    form = UploadExcelForm()

    if form.validate_on_submit():
        file = request.files.get('arquivo')
        if not file:
            flash("Nenhum arquivo selecionado.", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        df = pd.read_excel(path)
        for _, row in df.iterrows():
            if not pd.isna(row[0]):
                nf_numero = str(row[0])
                entrega = EntregaMonitorada.query.filter_by(numero_nf=nf_numero).first()
                pendencia = PendenciaFinanceiraNF(
                    numero_nf=nf_numero,
                    observacao=row[1] if len(row) > 1 else '',
                    criado_por=current_user.nome,
                    entrega=entrega
                )
                db.session.add(pendencia)

        db.session.commit()
        flash("Pendências importadas com sucesso.", "success")
        return redirect(request.url)

    return render_template('financeiro/importar_pendencias.html', form=form)


@financeiro_bp.route('/modelo-pendencias')
@login_required
def baixar_modelo_pendencias():
    """Download do modelo Excel para importação de pendências financeiras"""
    return send_from_directory(
        directory=os.path.join(os.getcwd(), 'app', 'static', 'modelos'),
        path='modelo_pendencias_financeiras.xlsx',
        as_attachment=True,
        download_name='modelo_pendencias_financeiras.xlsx'
    )


@financeiro_bp.route('/pendencias/<numero_nf>/responder', methods=['POST'])
def responder_pendencia(numero_nf):
    print("DEBUG: Chegou em responder_pendencia")
    print("request.is_json =", request.is_json)
    print("request.data =", request.data)
    data = request.get_json(silent=True)
    print("data =", data)

    if not data:
        return jsonify(success=False, error="Sem JSON"), 400

    resposta = data.get('resposta')
    print("resposta =", resposta)

    pendencia = PendenciaFinanceiraNF.query.filter_by(numero_nf=numero_nf, respondida_em=None).first_or_404()
    pendencia.resposta_logistica = resposta
    pendencia.respondida_em = agora_utc_naive()
    pendencia.respondida_por = current_user.nome
    db.session.commit()

    # Salvar log na entrega (opcional recomendado)
    entrega = pendencia.entrega
    if entrega:
        log = RegistroLogEntrega(
            entrega_id=entrega.id,
            autor=current_user.nome,
            descricao=f"Resposta Pend. Financeira: {resposta}",
            tipo='Ação'
        )
        db.session.add(log)
        db.session.commit()

    return jsonify(success=True)


@financeiro_bp.route('/consultar-pendencias')
@login_required
def consultar_pendencias():
    filtro = request.args.get('filtro', 'total')

    query = PendenciaFinanceiraNF.query.join(EntregaMonitorada, PendenciaFinanceiraNF.numero_nf == EntregaMonitorada.numero_nf)

    if filtro == 'respondidas':
        query = query.filter(PendenciaFinanceiraNF.respondida_em.isnot(None))
    elif filtro == 'pendentes':
        query = query.filter(PendenciaFinanceiraNF.respondida_em.is_(None))

    pendencias = query.all()
    total = PendenciaFinanceiraNF.query.count()
    respondidas = PendenciaFinanceiraNF.query.filter(PendenciaFinanceiraNF.respondida_em.isnot(None)).count()
    pendentes = total - respondidas

    return render_template('financeiro/consultar_pendencias.html', pendencias=pendencias,
                           total=total, respondidas=respondidas, pendentes=pendentes, filtro=filtro)


@financeiro_bp.route('/exportar-pendencias')
@login_required
def exportar_pendencias():
    pendencias = PendenciaFinanceiraNF.query.all()
    dados = [{
        "NF": p.numero_nf,
        "CNPJ": p.entrega.cnpj_cliente if p.entrega else '',
        "Cliente": p.entrega.cliente if p.entrega else '',
        "Valor": p.entrega.valor_nf if p.entrega else 0,
        "Obs. Financeira": p.observacao,
        "Resposta Logística": p.resposta_logistica or ''
    } for p in pendencias]

    df = pd.DataFrame(dados)
    arquivo = 'pendencias_financeiras.xlsx'
    df.to_excel(arquivo, index=False)

    return send_from_directory(os.getcwd(), arquivo, as_attachment=True)


@financeiro_bp.route('/excluir-pendencias-selecionadas', methods=['POST'])
@login_required
def excluir_pendencias_selecionadas():
    ids = request.form.getlist('selecionadas')
    if ids:
        PendenciaFinanceiraNF.query.filter(PendenciaFinanceiraNF.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'{len(ids)} pendências excluídas com sucesso.', 'success')
    else:
        flash('Nenhuma pendência selecionada.', 'warning')
    return redirect(url_for('financeiro.consultar_pendencias'))


@financeiro_bp.route('/excluir-todas-pendencias')
@login_required
def excluir_todas_pendencias():
    PendenciaFinanceiraNF.query.delete()
    db.session.commit()
    flash('Todas as pendências foram excluídas com sucesso.', 'success')
    return redirect(url_for('financeiro.consultar_pendencias'))
