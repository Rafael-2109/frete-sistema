import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from werkzeug.utils import secure_filename
from app import db
from app.cadastros_agendamento.models import ContatoAgendamento
from app.cadastros_agendamento.forms import ContatoAgendamentoForm
from datetime import datetime

cadastros_agendamento_bp = Blueprint('cadastros_agendamento', __name__, url_prefix='/cadastros-agendamento')

UPLOAD_FOLDER = 'uploads/agendamentos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@cadastros_agendamento_bp.route('/contatos', methods=['GET', 'POST'])
@login_required
def listar_contatos():
    form = ContatoAgendamentoForm()
    if form.validate_on_submit():
        contato = ContatoAgendamento(
            cnpj=form.cnpj.data,
            forma=form.forma.data,
            contato=form.contato.data,
            observacao=form.observacao.data,
            atualizado_em=datetime.utcnow()
        )
        db.session.add(contato)
        db.session.commit()
        flash("Contato salvo com sucesso.", "success")
        return redirect(url_for('cadastros_agendamento.listar_contatos'))

    contatos = ContatoAgendamento.query.order_by(ContatoAgendamento.cnpj).all()
    return render_template('cadastros_agendamento/listar_contatos.html', form=form, contatos=contatos)

@cadastros_agendamento_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar_contatos():
    if request.method == 'POST':
        file = request.files.get('arquivo')
        if not file:
            flash("Nenhum arquivo selecionado.", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        try:
            df = pd.read_excel(path)
            for _, row in df.iterrows():
                if not pd.isna(row["CNPJ"]):
                    contato = ContatoAgendamento(
                        cnpj=str(row["CNPJ"]),
                        forma=row.get("Forma"),
                        contato=row.get("Contato"),
                        observacao=row.get("Observação", ""),
                        atualizado_em=datetime.utcnow()
                    )
                    db.session.add(contato)
            db.session.commit()
            flash("Contatos importados com sucesso.", "success")
        except Exception as e:
            flash(f"Erro ao importar: {e}", "danger")

        return redirect(url_for('cadastros_agendamento.importar_contatos'))

    return render_template('cadastros_agendamento/importar_contatos.html')