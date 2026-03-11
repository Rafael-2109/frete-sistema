import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename
from app import db
from app.cadastros_agendamento.models import ContatoAgendamento
from app.cadastros_agendamento.forms import ContatoAgendamentoForm, ImportarAgendamentosForm, EditarContatoAgendamentoForm, PesquisarAgendamentoForm
from datetime import time as dt_time
from app.utils.timezone import agora_utc_naive

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
            nao_aceita_nf_pallet=form.nao_aceita_nf_pallet.data,
            horario_recebimento_de=form.horario_recebimento_de.data,
            horario_recebimento_ate=form.horario_recebimento_ate.data,
            observacoes_recebimento=form.observacoes_recebimento.data,
            atualizado_em=agora_utc_naive()
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
        contato.nao_aceita_nf_pallet = form.nao_aceita_nf_pallet.data
        contato.horario_recebimento_de = form.horario_recebimento_de.data
        contato.horario_recebimento_ate = form.horario_recebimento_ate.data
        contato.observacoes_recebimento = form.observacoes_recebimento.data
        contato.atualizado_em = agora_utc_naive()

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
            'observacao': contato.observacao,
            'nao_aceita_nf_pallet': contato.nao_aceita_nf_pallet,
            'horario_recebimento_de': contato.horario_recebimento_de.strftime('%H:%M') if contato.horario_recebimento_de else None,
            'horario_recebimento_ate': contato.horario_recebimento_ate.strftime('%H:%M') if contato.horario_recebimento_ate else None,
            'observacoes_recebimento': contato.observacoes_recebimento,
        })

    return jsonify(resultado)


def _parse_time_str(val):
    """Converte string HH:MM para datetime.time ou None."""
    if not val:
        return None
    try:
        partes = val.strip().replace('.', ':').split(':')
        return dt_time(int(partes[0]), int(partes[1]) if len(partes) > 1 else 0)
    except (ValueError, IndexError):
        return None


@cadastros_agendamento_bp.route('/api/atualizar/<path:cnpj>', methods=['PUT'])
@login_required
def api_atualizar_contato(cnpj):
    """AJAX endpoint para atualizar contato de agendamento por CNPJ."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON inválido'}), 400

    contato = ContatoAgendamento.query.filter_by(cnpj=cnpj).first()
    if not contato:
        return jsonify({'error': 'Contato não encontrado para este CNPJ'}), 404

    if 'forma' in data:
        contato.forma = data['forma'] or None
    if 'contato' in data:
        contato.contato = data['contato'] or None
    if 'observacao' in data:
        contato.observacao = data['observacao'] or None
    if 'nao_aceita_nf_pallet' in data:
        contato.nao_aceita_nf_pallet = bool(data['nao_aceita_nf_pallet'])
    if 'horario_recebimento_de' in data:
        contato.horario_recebimento_de = _parse_time_str(data['horario_recebimento_de'])
    if 'horario_recebimento_ate' in data:
        contato.horario_recebimento_ate = _parse_time_str(data['horario_recebimento_ate'])
    if 'observacoes_recebimento' in data:
        contato.observacoes_recebimento = data['observacoes_recebimento'] or None

    contato.atualizado_em = agora_utc_naive()
    db.session.commit()

    return jsonify({
        'sucesso': True,
        'mensagem': 'Contato atualizado com sucesso',
        'contato': {
            'cnpj': contato.cnpj,
            'forma': contato.forma,
            'contato': contato.contato,
            'observacao': contato.observacao,
            'nao_aceita_nf_pallet': contato.nao_aceita_nf_pallet,
            'horario_recebimento_de': contato.horario_recebimento_de.strftime('%H:%M') if contato.horario_recebimento_de else None,
            'horario_recebimento_ate': contato.horario_recebimento_ate.strftime('%H:%M') if contato.horario_recebimento_ate else None,
            'observacoes_recebimento': contato.observacoes_recebimento,
        }
    })


@cadastros_agendamento_bp.route('/api/criar', methods=['POST'])
@login_required
def api_criar_contato():
    """AJAX endpoint para criar contato de agendamento."""
    data = request.get_json()
    if not data or not data.get('cnpj'):
        return jsonify({'error': 'CNPJ é obrigatório'}), 400

    cnpj = data['cnpj']

    # Verificar se já existe
    existente = ContatoAgendamento.query.filter_by(cnpj=cnpj).first()
    if existente:
        return jsonify({'error': f'Já existe contato para CNPJ {cnpj}. Use atualizar.'}), 409

    contato = ContatoAgendamento(
        cnpj=cnpj,
        forma=data.get('forma') or None,
        contato=data.get('contato') or None,
        observacao=data.get('observacao') or None,
        nao_aceita_nf_pallet=bool(data.get('nao_aceita_nf_pallet', False)),
        horario_recebimento_de=_parse_time_str(data.get('horario_recebimento_de')),
        horario_recebimento_ate=_parse_time_str(data.get('horario_recebimento_ate')),
        observacoes_recebimento=data.get('observacoes_recebimento') or None,
        atualizado_em=agora_utc_naive()
    )
    db.session.add(contato)
    db.session.commit()

    return jsonify({
        'sucesso': True,
        'mensagem': 'Contato criado com sucesso',
        'contato': {
            'cnpj': contato.cnpj,
            'forma': contato.forma,
            'contato': contato.contato,
            'observacao': contato.observacao,
            'nao_aceita_nf_pallet': contato.nao_aceita_nf_pallet,
            'horario_recebimento_de': contato.horario_recebimento_de.strftime('%H:%M') if contato.horario_recebimento_de else None,
            'horario_recebimento_ate': contato.horario_recebimento_ate.strftime('%H:%M') if contato.horario_recebimento_ate else None,
            'observacoes_recebimento': contato.observacoes_recebimento,
        }
    }), 201


@cadastros_agendamento_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar_contatos():
    import pandas as pd  # Lazy import

    form = ImportarAgendamentosForm()

    if form.validate_on_submit():
        try:
            file = form.arquivo.data
            if not file:
                flash("Nenhum arquivo selecionado.", "danger")
                return redirect(request.url)

            # 📖 Ler o arquivo UMA vez para evitar problemas de arquivo fechado
            import io
            file_content = file.read()
            
            # Salvar para backup local se necessário
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            with open(path, 'wb') as f:
                f.write(file_content)

            # Lê o arquivo Excel usando BytesIO
            df = pd.read_excel(io.BytesIO(file_content), dtype=str)  # Lê como string para evitar problemas
            
            # Verifica se as colunas necessárias existem
            colunas_necessarias = ['CNPJ']
            
            # Verifica colunas obrigatórias
            for coluna in colunas_necessarias:
                if coluna not in df.columns:
                    flash(f"Coluna obrigatória '{coluna}' não encontrada no arquivo.", "danger")
                    return redirect(request.url)

            # Processa colunas opcionais se existirem
            tem_coluna_pallet = 'Aceita NF Pallet' in df.columns
            tem_coluna_horario_de = 'Horário De' in df.columns
            tem_coluna_horario_ate = 'Horário Até' in df.columns
            tem_coluna_obs_recebimento = 'Obs. Recebimento' in df.columns

            contador_importados = 0
            contador_erros = 0

            # Função auxiliar para tratar valores vazios
            def tratar_valor_vazio(valor):
                """Converte valores nan, None ou string vazia para None"""
                if pd.isna(valor) or valor == 'nan' or valor == '' or valor is None:
                    return None
                return str(valor).strip()

            def parse_horario(valor_str):
                """Converte string HH:MM para datetime.time, ou None"""
                if not valor_str:
                    return None
                try:
                    partes = valor_str.replace('.', ':').split(':')
                    return dt_time(int(partes[0]), int(partes[1]) if len(partes) > 1 else 0)
                except (ValueError, IndexError):
                    return None

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

                    # Processa campo "Aceita NF Pallet" se existir
                    # SIM = aceita (nao_aceita_nf_pallet = False), NÃO = não aceita (nao_aceita_nf_pallet = True)
                    nao_aceita_nf_pallet = None
                    if tem_coluna_pallet:
                        valor_pallet = tratar_valor_vazio(row.get("Aceita NF Pallet", ""))
                        if valor_pallet:
                            valor_upper = valor_pallet.upper()
                            if valor_upper in ('NÃO', 'NAO', 'N', 'NAO'):
                                nao_aceita_nf_pallet = True
                            elif valor_upper in ('SIM', 'S'):
                                nao_aceita_nf_pallet = False

                    # Processa campos de recebimento se existirem
                    horario_de = None
                    horario_ate = None
                    obs_recebimento = None
                    if tem_coluna_horario_de:
                        horario_de = parse_horario(tratar_valor_vazio(row.get("Horário De", "")))
                    if tem_coluna_horario_ate:
                        horario_ate = parse_horario(tratar_valor_vazio(row.get("Horário Até", "")))
                    if tem_coluna_obs_recebimento:
                        obs_recebimento = tratar_valor_vazio(row.get("Obs. Recebimento", ""))

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
                        if nao_aceita_nf_pallet is not None:
                            contato_existente.nao_aceita_nf_pallet = nao_aceita_nf_pallet
                        if horario_de is not None:
                            contato_existente.horario_recebimento_de = horario_de
                        if horario_ate is not None:
                            contato_existente.horario_recebimento_ate = horario_ate
                        if obs_recebimento is not None:
                            contato_existente.observacoes_recebimento = obs_recebimento
                        contato_existente.atualizado_em = agora_utc_naive()
                    else:
                        # Cria novo contato
                        novo_contato = ContatoAgendamento(
                            cnpj=cnpj,
                            forma=forma,
                            contato=contato,
                            observacao=observacao,
                            nao_aceita_nf_pallet=nao_aceita_nf_pallet if nao_aceita_nf_pallet is not None else False,
                            horario_recebimento_de=horario_de,
                            horario_recebimento_ate=horario_ate,
                            observacoes_recebimento=obs_recebimento,
                            atualizado_em=agora_utc_naive()
                        )
                        db.session.add(novo_contato)

                    contador_importados += 1

                except Exception as e:
                    print(f"Erro ao processar linha {index + 1}: {e}")  # type: ignore
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
    import pandas as pd  # Lazy import

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
            'Aceita NF Pallet': 'NÃO' if contato.nao_aceita_nf_pallet else 'SIM',
            'Observação': contato.observacao or '',
            'Horário De': contato.horario_recebimento_de.strftime('%H:%M') if contato.horario_recebimento_de else '',
            'Horário Até': contato.horario_recebimento_ate.strftime('%H:%M') if contato.horario_recebimento_ate else '',
            'Obs. Recebimento': contato.observacoes_recebimento or '',
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
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    filename = f"contatos_agendamento_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
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