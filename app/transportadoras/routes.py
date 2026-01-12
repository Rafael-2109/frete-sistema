from flask import render_template, redirect, url_for, flash, request, session, jsonify, make_response
from flask_login import login_required
from app import db
from app.transportadoras.forms import TransportadoraForm, ImportarTransportadorasForm
from app.transportadoras.models import Transportadora
from app.transportadoras import transportadoras_bp
from app.utils.importacao.importar_transportadoras import importar_transportadoras
from app.utils.importacao.utils_importacao import salvar_temp
from sqlalchemy.exc import IntegrityError
from io import BytesIO
from datetime import datetime
import traceback
import pandas as pd

@transportadoras_bp.route('/', methods=['GET', 'POST'])
@login_required
def cadastrar_transportadora():
    form = TransportadoraForm()
    
    # Recupera erros da sessão
    erros_importacao = session.get('erros_importacao', [])
    
    if form.validate_on_submit():
        # Mantém o CNPJ como digitado (sem limpeza)
        cnpj_digitado = form.cnpj.data.strip()
        
        # Verifica se o CNPJ já existe ANTES de tentar criar
        transportadora_existente = Transportadora.query.filter_by(cnpj=cnpj_digitado).first()
        if transportadora_existente:
            flash(f'ERRO: CNPJ {cnpj_digitado} já está cadastrado para a transportadora "{transportadora_existente.razao_social}". Não é permitido cadastrar duas transportadoras com o mesmo CNPJ.', 'danger')
            # Não processa o cadastro, apenas retorna o formulário com o erro
        else:
            nova = Transportadora(
                cnpj=cnpj_digitado,
                razao_social=form.razao_social.data,
                cidade=form.cidade.data,
                uf=form.uf.data.upper(),
                optante=form.optante.data == 'True',
                condicao_pgto=form.condicao_pgto.data,
                freteiro=form.freteiro.data == 'True'
            )
            db.session.add(nova)
            try:
                db.session.commit()
                flash('Transportadora cadastrada com sucesso!', 'success')
                return redirect(url_for('transportadoras.cadastrar_transportadora'))
            except IntegrityError:
                db.session.rollback()
                flash(f'ERRO: CNPJ {cnpj_digitado} já existe no banco de dados. Verifique se não está tentando cadastrar uma transportadora duplicada.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao cadastrar transportadora: {str(e)}', 'danger')
    
    transportadoras = Transportadora.query.order_by(Transportadora.razao_social.asc()).all()
    return render_template('transportadoras/transportadoras.html', 
                         form=form, 
                         transportadoras=transportadoras,
                         erros_importacao=erros_importacao)

@transportadoras_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    form = ImportarTransportadorasForm()
    
    print("[DEBUG] Iniciando rota de importação")
    print(f"[DEBUG] Método da requisição: {request.method}")
    
    if request.method == 'POST':
        print("[DEBUG] Dados do formulário:", request.form)
        print("[DEBUG] Arquivos:", request.files)
    
    if form.validate_on_submit():
        try:
            print("[DEBUG] Formulário válido, processando arquivo")
            
            # Salva o arquivo temporariamente
            caminho_arquivo = salvar_temp(form.arquivo.data)
            
            # Importa as transportadoras usando a função utilitária
            resumo = importar_transportadoras(caminho_arquivo)
            
            # Divide o resumo em seções
            secoes = resumo.split('\n=== ')
            
            # Processa cada seção
            for secao in secoes:
                if 'ERROS ENCONTRADOS' in secao:
                    flash(secao, 'danger')
                elif 'TRANSPORTADORAS IMPORTADAS' in secao:
                    flash(secao, 'success')
                elif 'TRANSPORTADORAS ATUALIZADAS' in secao:
                    flash(secao, 'info')
                elif secao.startswith('Total:'):
                    flash(secao, 'primary')
            
            return redirect(url_for('transportadoras.cadastrar_transportadora'))
                
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'danger')
            print(traceback.format_exc())
    
    return render_template('transportadoras/importar.html', 
                         form=form)



@transportadoras_bp.route('/dados/<int:id>')
@login_required
def dados_transportadora(id):
    """Retorna dados da transportadora em JSON para o modal"""
    try:
        transportadora = Transportadora.query.get_or_404(id)
        
        # Garante que os valores boolean sejam tratados corretamente
        optante_valor = transportadora.optante if transportadora.optante is not None else False
        freteiro_valor = transportadora.freteiro if transportadora.freteiro is not None else False
        nao_aceita_nf_pallet_valor = transportadora.nao_aceita_nf_pallet if hasattr(transportadora, 'nao_aceita_nf_pallet') and transportadora.nao_aceita_nf_pallet is not None else False

        return jsonify({
            'success': True,
            'transportadora': {
                'id': transportadora.id,
                'cnpj': transportadora.cnpj or '',
                'razao_social': transportadora.razao_social or '',
                'cidade': transportadora.cidade or '',
                'uf': transportadora.uf or '',
                'optante': optante_valor,
                'freteiro': freteiro_valor,
                'condicao_pgto': transportadora.condicao_pgto or '',
                'ativo': transportadora.ativo if hasattr(transportadora, 'ativo') else True,
                'nao_aceita_nf_pallet': nao_aceita_nf_pallet_valor,
                # Campos financeiros
                'banco': transportadora.banco or '',
                'agencia': transportadora.agencia or '',
                'conta': transportadora.conta or '',
                'tipo_conta': transportadora.tipo_conta or '',
                'pix': transportadora.pix or '',
                'cpf_cnpj_favorecido': transportadora.cpf_cnpj_favorecido or '',
                'obs_financ': transportadora.obs_financ or ''
            }
        })
    except Exception as e:
        print(f"[ERRO] Erro ao buscar transportadora {id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@transportadoras_bp.route('/editar/<int:id>', methods=['POST'])
@login_required
def editar_transportadora_ajax(id):
    """Edita transportadora via AJAX"""
    try:
        transportadora = Transportadora.query.get_or_404(id)
        
        # Mantém o CNPJ como recebido (sem limpeza)
        cnpj_recebido = request.form.get('cnpj', '').strip()
        
        # Verifica se o CNPJ já existe para outra transportadora
        cnpj_existente = Transportadora.query.filter(
            Transportadora.cnpj == cnpj_recebido,
            Transportadora.id != id
        ).first()
        
        if cnpj_existente:
            return jsonify({
                'success': False, 
                'message': f'ERRO: CNPJ {cnpj_recebido} já está cadastrado para a transportadora "{cnpj_existente.razao_social}". Não é permitido ter duas transportadoras com o mesmo CNPJ. Por favor, verifique o CNPJ informado.'
            })
        
        # Atualiza os dados
        transportadora.cnpj = cnpj_recebido
        transportadora.razao_social = request.form.get('razao_social', '')
        transportadora.cidade = request.form.get('cidade', '')
        transportadora.uf = request.form.get('uf', '').upper()
        transportadora.optante = request.form.get('optante') == 'True'
        transportadora.freteiro = request.form.get('freteiro') == 'True'
        transportadora.condicao_pgto = request.form.get('condicao_pgto', '')
        # Campo ativo - checkbox envia 'on' quando marcado
        transportadora.ativo = request.form.get('ativo') == 'on'
        # Campo NF de pallet - checkbox envia 'on' quando marcado
        transportadora.nao_aceita_nf_pallet = request.form.get('nao_aceita_nf_pallet') == 'on'

        # Campos financeiros
        transportadora.banco = request.form.get('banco', '').strip() or None
        transportadora.agencia = request.form.get('agencia', '').strip() or None
        transportadora.conta = request.form.get('conta', '').strip() or None
        transportadora.tipo_conta = request.form.get('tipo_conta', '').strip() or None
        transportadora.pix = request.form.get('pix', '').strip() or None
        transportadora.cpf_cnpj_favorecido = request.form.get('cpf_cnpj_favorecido', '').strip() or None
        transportadora.obs_financ = request.form.get('obs_financ', '').strip() or None

        # TODO: Adicionar campos de auditoria no futuro
        # transportadora.alterado_por = current_user.nome
        # transportadora.alterado_em = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Transportadora atualizada com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao atualizar transportadora: {str(e)}'})

@transportadoras_bp.route('/excluir/<int:id>')
@login_required
def excluir_transportadora(id):
    try:
        transportadora = Transportadora.query.get_or_404(id)
        db.session.delete(transportadora)
        db.session.commit()
        flash('Transportadora excluída com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir transportadora: {str(e)}', 'danger')
    
    return redirect(url_for('transportadoras.cadastrar_transportadora'))

@transportadoras_bp.route('/config-frete/<int:id>', methods=['GET'])
@login_required
def obter_config_frete(id):
    """Obtém configurações de cálculo de frete da transportadora"""
    try:
        transportadora = Transportadora.query.get_or_404(id)
        
        # Retorna as configurações atuais
        config = {
            'aplica_gris_pos_minimo': transportadora.aplica_gris_pos_minimo or False,
            'aplica_adv_pos_minimo': transportadora.aplica_adv_pos_minimo or False,
            'aplica_rca_pos_minimo': transportadora.aplica_rca_pos_minimo or False,
            'aplica_pedagio_pos_minimo': transportadora.aplica_pedagio_pos_minimo or False,
            'aplica_tas_pos_minimo': transportadora.aplica_tas_pos_minimo or False,
            'aplica_despacho_pos_minimo': transportadora.aplica_despacho_pos_minimo or False,
            'aplica_cte_pos_minimo': transportadora.aplica_cte_pos_minimo or False,
            'pedagio_por_fracao': transportadora.pedagio_por_fracao if transportadora.pedagio_por_fracao is not None else True
        }
        
        return jsonify({
            'success': True,
            'transportadora': {
                'id': transportadora.id,
                'razao_social': transportadora.razao_social
            },
            'config': config
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@transportadoras_bp.route('/config-frete/<int:id>', methods=['POST'])
@login_required
def salvar_config_frete(id):
    """Salva configurações de cálculo de frete da transportadora"""
    try:
        transportadora = Transportadora.query.get_or_404(id)
        data = request.get_json()
        
        # Atualiza as configurações
        transportadora.aplica_gris_pos_minimo = data.get('aplica_gris_pos_minimo', False)
        transportadora.aplica_adv_pos_minimo = data.get('aplica_adv_pos_minimo', False)
        transportadora.aplica_rca_pos_minimo = data.get('aplica_rca_pos_minimo', False)
        transportadora.aplica_pedagio_pos_minimo = data.get('aplica_pedagio_pos_minimo', False)
        transportadora.aplica_tas_pos_minimo = data.get('aplica_tas_pos_minimo', False)
        transportadora.aplica_despacho_pos_minimo = data.get('aplica_despacho_pos_minimo', False)
        transportadora.aplica_cte_pos_minimo = data.get('aplica_cte_pos_minimo', False)
        transportadora.pedagio_por_fracao = data.get('pedagio_por_fracao', True)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Configuração salva com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao salvar configuração: {str(e)}'})


@transportadoras_bp.route('/exportar')
@login_required
def exportar_transportadoras():
    """Exporta todas as transportadoras para Excel"""
    try:
        transportadoras = Transportadora.query.order_by(Transportadora.razao_social.asc()).all()

        # Prepara os dados para o DataFrame
        dados = []
        for t in transportadoras:
            dados.append({
                'CNPJ': t.cnpj or '',
                'Razão Social': t.razao_social or '',
                'Cidade': t.cidade or '',
                'UF': t.uf or '',
                'Optante Simples': 'Sim' if t.optante else 'Não',
                'Freteiro': 'Sim' if t.freteiro else 'Não',
                'Aceita NF Pallet': 'Não' if t.nao_aceita_nf_pallet else 'Sim',
                'Condição de Pagamento': t.condicao_pgto or '',
                'Status': 'Ativo' if t.ativo else 'Inativo',
                # Campos financeiros
                'Banco': t.banco or '',
                'Agência': t.agencia or '',
                'Conta': t.conta or '',
                'Tipo Conta': t.tipo_conta.replace('corrente', 'Corrente').replace('poupanca', 'Poupança') if t.tipo_conta else '',
                'PIX': t.pix or '',
                'CPF/CNPJ Favorecido': t.cpf_cnpj_favorecido or '',
                'Obs. Financeira': t.obs_financ or ''
            })

        # Cria o DataFrame
        df = pd.DataFrame(dados)

        # Cria o arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Transportadoras')

            # Ajusta a largura das colunas
            worksheet = writer.sheets['Transportadoras']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx) if idx < 26 else 'A' + chr(65 + idx - 26)].width = min(max_length, 50)

        output.seek(0)

        # Cria a resposta com o arquivo
        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=transportadoras_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return response

    except Exception as e:
        flash(f'Erro ao exportar transportadoras: {str(e)}', 'danger')
        return redirect(url_for('transportadoras.cadastrar_transportadora'))
