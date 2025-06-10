import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename
from app import db
from app.cadastros_agendamento.models import ContatoAgendamento
from app.cadastros_agendamento.forms import ContatoAgendamentoForm, ImportarAgendamentosForm, EditarContatoAgendamentoForm, PesquisarAgendamentoForm
from datetime import datetime
from sqlalchemy import or_

cadastros_agendamento_bp = Blueprint('cadastros_agendamento', __name__, url_prefix='/cadastros-agendamento')

UPLOAD_FOLDER = 'uploads/agendamentos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@cadastros_agendamento_bp.route('/contatos', methods=['GET', 'POST'])
@login_required
def listar_contatos():
    form = ContatoAgendamentoForm()
    pesquisa_form = PesquisarAgendamentoForm()
    
    # Processar novo cadastro
    if form.validate_on_submit():
        # Verificar se já existe contato para este CNPJ
        contato_existente = ContatoAgendamento.query.filter_by(cnpj=form.cnpj.data).first()
        
        if contato_existente:
            flash(f"Já existe um contato para o CNPJ {form.cnpj.data}. Use a função editar.", "warning")
            return redirect(url_for('cadastros_agendamento.listar_contatos'))
        
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

    # Processar pesquisa
    query = ContatoAgendamento.query
    filtros_ativos = {}
    
    if request.method == 'GET':
        cnpj_pesq = request.args.get('cnpj', '').strip()
        forma_pesq = request.args.get('forma', '')
        contato_pesq = request.args.get('contato', '').strip()
        
        if cnpj_pesq:
            query = query.filter(ContatoAgendamento.cnpj.ilike(f'%{cnpj_pesq}%'))
            filtros_ativos['cnpj'] = cnpj_pesq
            pesquisa_form.cnpj.data = cnpj_pesq
            
        if forma_pesq:
            query = query.filter(ContatoAgendamento.forma == forma_pesq)
            filtros_ativos['forma'] = forma_pesq
            pesquisa_form.forma.data = forma_pesq
            
        if contato_pesq:
            query = query.filter(ContatoAgendamento.contato.ilike(f'%{contato_pesq}%'))
            filtros_ativos['contato'] = contato_pesq
            pesquisa_form.contato.data = contato_pesq
    
    # Ordenação e paginação
    page = request.args.get('page', 1, type=int)
    contatos = query.order_by(ContatoAgendamento.cnpj).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template(
        'cadastros_agendamento/listar_contatos.html', 
        form=form, 
        pesquisa_form=pesquisa_form,
        contatos=contatos,
        filtros_ativos=filtros_ativos
    )

@cadastros_agendamento_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_contato(id):
    contato = ContatoAgendamento.query.get_or_404(id)
    form = EditarContatoAgendamentoForm(obj=contato)
    
    if form.validate_on_submit():
        # Verificar se CNPJ mudou e se já existe outro registro com esse CNPJ
        if form.cnpj.data != contato.cnpj:
            contato_existente = ContatoAgendamento.query.filter_by(cnpj=form.cnpj.data).first()
            if contato_existente:
                flash(f"Já existe um contato para o CNPJ {form.cnpj.data}.", "warning")
                return render_template('cadastros_agendamento/editar_contato.html', form=form, contato=contato)
        
        contato.cnpj = form.cnpj.data
        contato.forma = form.forma.data
        contato.contato = form.contato.data
        contato.observacao = form.observacao.data
        contato.atualizado_em = datetime.utcnow()
        
        db.session.commit()
        flash("Contato atualizado com sucesso.", "success")
        return redirect(url_for('cadastros_agendamento.listar_contatos'))
    
    return render_template('cadastros_agendamento/editar_contato.html', form=form, contato=contato)

@cadastros_agendamento_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_contato(id):
    contato = ContatoAgendamento.query.get_or_404(id)
    
    try:
        db.session.delete(contato)
        db.session.commit()
        flash(f"Contato para CNPJ {contato.cnpj} excluído com sucesso.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir contato.", "danger")
    
    return redirect(url_for('cadastros_agendamento.listar_contatos'))

@cadastros_agendamento_bp.route('/buscar-cnpj')
@login_required
def buscar_cnpj():
    """AJAX endpoint para buscar contatos por CNPJ"""
    cnpj = request.args.get('cnpj', '')
    
    if len(cnpj) < 3:
        return jsonify([])
    
    contatos = ContatoAgendamento.query.filter(
        ContatoAgendamento.cnpj.ilike(f'%{cnpj}%')
    ).limit(10).all()
    
    resultado = []
    for contato in contatos:
        resultado.append({
            'id': contato.id,
            'cnpj': contato.cnpj,
            'forma': contato.forma,
            'contato': contato.contato,
            'observacao': contato.observacao
        })
    
    return jsonify(resultado)

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

@cadastros_agendamento_bp.route('/exportar-contatos')
@login_required
def exportar_contatos():
    """Exporta contatos filtrados para Excel"""
    
    # Aplicar mesmos filtros da listagem
    query = ContatoAgendamento.query
    
    cnpj_pesq = request.args.get('cnpj', '').strip()
    forma_pesq = request.args.get('forma', '')
    contato_pesq = request.args.get('contato', '').strip()
    
    if cnpj_pesq:
        query = query.filter(ContatoAgendamento.cnpj.ilike(f'%{cnpj_pesq}%'))
        
    if forma_pesq:
        query = query.filter(ContatoAgendamento.forma == forma_pesq)
        
    if contato_pesq:
        query = query.filter(ContatoAgendamento.contato.ilike(f'%{contato_pesq}%'))
    
    contatos = query.order_by(ContatoAgendamento.cnpj).all()
    
    # Criar dados para exportação
    dados_exportacao = []
    for contato in contatos:
        dados_exportacao.append({
            'CNPJ': contato.cnpj,
            'Forma': contato.forma or '',
            'Contato': contato.contato or '',
            'Observação': contato.observacao or '',
            'Atualizado Em': contato.atualizado_em.strftime('%d/%m/%Y %H:%M')
        })
    
    # Criar arquivo Excel
    df = pd.DataFrame(dados_exportacao)
    
    from io import BytesIO
    import openpyxl
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Contatos Agendamento', index=False)
        
        # Ajustar largura das colunas
        worksheet = writer.sheets['Contatos Agendamento']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    filename = f"contatos_agendamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

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