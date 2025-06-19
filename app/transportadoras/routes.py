from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required
from app import db
from app.transportadoras.forms import TransportadoraForm, ImportarTransportadorasForm
from app.transportadoras.models import Transportadora
from app.transportadoras import transportadoras_bp
from app.utils.importacao.importar_transportadoras import importar_transportadoras
from app.utils.importacao.utils_importacao import salvar_temp
import pandas as pd
from sqlalchemy.exc import IntegrityError
import traceback

@transportadoras_bp.route('/', methods=['GET', 'POST'])
@login_required
def cadastrar_transportadora():
    form = TransportadoraForm()
    
    # Recupera erros da sessão
    erros_importacao = session.get('erros_importacao', [])
    
    if form.validate_on_submit():
        nova = Transportadora(
            cnpj=form.cnpj.data,
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
    
    transportadoras = Transportadora.query.all()
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

@transportadoras_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_transportadora(id):
    transportadora = Transportadora.query.get_or_404(id)
    form = TransportadoraForm(obj=transportadora)
    
    if form.validate_on_submit():
        try:
            transportadora.cnpj = form.cnpj.data
            transportadora.razao_social = form.razao_social.data
            transportadora.cidade = form.cidade.data
            transportadora.uf = form.uf.data.upper()
            transportadora.optante = form.optante.data == 'True'
            transportadora.condicao_pgto = form.condicao_pgto.data
            transportadora.freteiro = form.freteiro.data == 'True'
            
            db.session.commit()
            flash('Transportadora atualizada com sucesso!', 'success')
            return redirect(url_for('transportadoras.cadastrar_transportadora'))
        
        except IntegrityError:
            db.session.rollback()
            flash('Erro ao atualizar. CNPJ já existe para outra transportadora.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar transportadora: {str(e)}', 'danger')
    
    # Ajusta os valores dos campos boolean para string antes de renderizar o form
    form.optante.data = str(transportadora.optante)
    form.freteiro.data = str(transportadora.freteiro)
    
    return render_template('transportadoras/transportadoras.html', 
                         form=form, 
                         transportadoras=Transportadora.query.all())

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

