from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required
from app import db
from app.transportadoras.forms import TransportadoraForm, ImportarTransportadorasForm
from app.transportadoras.models import Transportadora
from app.transportadoras import transportadoras_bp
from app.utils.importacao.importar_transportadoras import importar_transportadoras
from app.utils.importacao.utils_importacao import salvar_temp
from sqlalchemy.exc import IntegrityError
import traceback

@transportadoras_bp.route('/', methods=['GET', 'POST'])
@login_required
def cadastrar_transportadora():
    form = TransportadoraForm()
    
    # Recupera erros da sessão
    erros_importacao = session.get('erros_importacao', [])
    
    if form.validate_on_submit():
        # Mantém o CNPJ como digitado (sem limpeza)
        cnpj_digitado = form.cnpj.data.strip()
        
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
            flash('Erro ao cadastrar transportadora. CNPJ já existe.', 'danger')
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
                'ativo': transportadora.ativo if hasattr(transportadora, 'ativo') else True
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
                'message': f'CNPJ já cadastrado para a transportadora: {cnpj_existente.razao_social}'
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
