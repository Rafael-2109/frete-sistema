import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required
from werkzeug.utils import secure_filename
from app import db
from app.cadastros_agendamento.models import ContatoAgendamento
from app.cadastros_agendamento.forms import ContatoAgendamentoForm, ImportarAgendamentosForm
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
    form = ImportarAgendamentosForm()

    if form.validate_on_submit():
        try:
            file = form.arquivo.data
            if not file:
                flash("Nenhum arquivo selecionado.", "danger")
                return redirect(request.url)

            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)

            # Lê o arquivo Excel
            df = pd.read_excel(path, dtype=str)  # Lê como string para evitar problemas
            
            # Verifica se as colunas necessárias existem
            colunas_necessarias = ['CNPJ']
            colunas_opcionais = ['Forma', 'Contato', 'Observação']
            
            # Verifica colunas obrigatórias
            for coluna in colunas_necessarias:
                if coluna not in df.columns:
                    flash(f"Coluna obrigatória '{coluna}' não encontrada no arquivo.", "danger")
                    return redirect(request.url)

            contador_importados = 0
            contador_erros = 0
            
            # Função auxiliar para tratar valores vazios
            def tratar_valor_vazio(valor):
                """Converte valores nan, None ou string vazia para None"""
                if pd.isna(valor) or valor == 'nan' or valor == '' or valor is None:
                    return None
                return str(valor).strip()
            
            for index, row in df.iterrows():
                try:
                    cnpj = tratar_valor_vazio(row.get("CNPJ", ""))
                    
                    # Verifica se CNPJ não está vazio
                    if not cnpj:
                        contador_erros += 1
                        continue
                    
                    # Processa outros campos
                    forma = tratar_valor_vazio(row.get("Forma", ""))
                    contato = tratar_valor_vazio(row.get("Contato", ""))
                    observacao = tratar_valor_vazio(row.get("Observação", ""))
                    
                    # Verifica se já existe um contato para este CNPJ
                    contato_existente = ContatoAgendamento.query.filter_by(cnpj=cnpj).first()
                    
                    if contato_existente:
                        # Atualiza o contato existente (só atualiza se o novo valor não for None)
                        if forma is not None:
                            contato_existente.forma = forma
                        if contato is not None:
                            contato_existente.contato = contato
                        if observacao is not None:
                            contato_existente.observacao = observacao
                        contato_existente.atualizado_em = datetime.utcnow()
                    else:
                        # Cria novo contato
                        novo_contato = ContatoAgendamento(
                            cnpj=cnpj,
                            forma=forma,  # Pode ser None
                            contato=contato,  # Pode ser None
                            observacao=observacao,  # Pode ser None
                            atualizado_em=datetime.utcnow()
                        )
                        db.session.add(novo_contato)
                    
                    contador_importados += 1
                    
                except Exception as e:
                    print(f"Erro ao processar linha {index + 1}: {e}")
                    contador_erros += 1
                    continue

            # Commit das alterações
            db.session.commit()
            
            # Remove o arquivo temporário
            if os.path.exists(path):
                os.remove(path)
            
            # Mensagem de sucesso
            if contador_importados > 0:
                flash(f"Importação concluída! {contador_importados} contatos processados.", "success")
                if contador_erros > 0:
                    flash(f"Aviso: {contador_erros} linhas apresentaram erro e foram ignoradas.", "warning")
            else:
                flash("Nenhum contato foi importado. Verifique o arquivo.", "warning")
                
        except Exception as e:
            db.session.rollback()
            flash(f"Erro na importação: {str(e)}", "danger")
            print(f"Erro detalhado na importação: {e}")

        return redirect(url_for('cadastros_agendamento.importar_contatos'))

    return render_template('cadastros_agendamento/importar_contatos.html', form=form)

@cadastros_agendamento_bp.route('/modelo-agendamentos')
@login_required
def baixar_modelo_agendamentos():
    """Download do modelo Excel para importação de agendamentos"""
    return send_from_directory(
        directory=os.path.join(os.getcwd(), 'app', 'static', 'modelos'),
        path='modelo_agendamentos.xlsx',
        as_attachment=True,
        download_name='modelo_agendamentos.xlsx'
    )