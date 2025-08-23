"""
Rotas para gerenciamento do De-Para de produtos do Atacadão
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import pandas as pd
import os
from datetime import datetime
from app import db
from app.portal.atacadao.models import ProdutoDeParaAtacadao
from app.producao.models import CadastroPalletizacao
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('portal_depara', __name__, url_prefix='/portal/atacadao/depara')

@bp.route('/')
@login_required
def index():
    """Lista todos os mapeamentos De-Para"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = ProdutoDeParaAtacadao.query
    
    if search:
        query = query.filter(
            db.or_(
                ProdutoDeParaAtacadao.codigo_nosso.contains(search),
                ProdutoDeParaAtacadao.descricao_nosso.contains(search),
                ProdutoDeParaAtacadao.codigo_atacadao.contains(search),
                ProdutoDeParaAtacadao.descricao_atacadao.contains(search)
            )
        )
    
    query = query.order_by(ProdutoDeParaAtacadao.codigo_nosso)
    
    mapeamentos = query.paginate(page=page, per_page=50, error_out=False)
    
    return render_template('portal/atacadao/depara/index.html',
                         mapeamentos=mapeamentos,
                         search=search)

@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo mapeamento De-Para"""
    if request.method == 'POST':
        try:
            # Buscar descrição do nosso produto
            codigo_nosso = request.form.get('codigo_nosso', '').strip()
            descricao_nosso = ''
            
            # Buscar em CadastroPalletizacao
            produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
            if produto:
                descricao_nosso = produto.nome_produto
            
            mapeamento = ProdutoDeParaAtacadao(
                codigo_nosso=codigo_nosso,
                descricao_nosso=descricao_nosso or request.form.get('descricao_nosso', ''),
                codigo_atacadao=request.form.get('codigo_atacadao', '').strip(),
                descricao_atacadao=request.form.get('descricao_atacadao', '').strip(),
                cnpj_cliente=request.form.get('cnpj_cliente', '').strip(),
                fator_conversao=float(request.form.get('fator_conversao', 1.0)),
                observacoes=request.form.get('observacoes', ''),
                ativo=request.form.get('ativo') == 'on',
                criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )
            
            db.session.add(mapeamento)
            db.session.commit()
            
            flash('Mapeamento criado com sucesso!', 'success')
            return redirect(url_for('portal.portal_depara.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar mapeamento: {e}")
            flash(f'Erro ao criar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/atacadao/depara/form.html',
                         mapeamento=None,
                         action='novo')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar mapeamento existente"""
    mapeamento = ProdutoDeParaAtacadao.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Buscar descrição atualizada se mudou código
            codigo_nosso = request.form.get('codigo_nosso', '').strip()
            if codigo_nosso != mapeamento.codigo_nosso:
                produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
                if produto:
                    mapeamento.descricao_nosso = produto.nome_produto
            
            mapeamento.codigo_nosso = codigo_nosso
            mapeamento.codigo_atacadao = request.form.get('codigo_atacadao', '').strip()
            mapeamento.descricao_atacadao = request.form.get('descricao_atacadao', '').strip()
            mapeamento.cnpj_cliente = request.form.get('cnpj_cliente', '').strip()
            mapeamento.fator_conversao = float(request.form.get('fator_conversao', 1.0))
            mapeamento.observacoes = request.form.get('observacoes', '')
            mapeamento.ativo = request.form.get('ativo') == 'on'
            mapeamento.atualizado_em = datetime.utcnow()
            
            db.session.commit()
            
            flash('Mapeamento atualizado com sucesso!', 'success')
            return redirect(url_for('portal.portal_depara.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar mapeamento: {e}")
            flash(f'Erro ao atualizar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/atacadao/depara/form.html',
                         mapeamento=mapeamento,
                         action='editar')

@bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    """Excluir mapeamento"""
    try:
        mapeamento = ProdutoDeParaAtacadao.query.get_or_404(id)
        db.session.delete(mapeamento)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mapeamento excluído com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir mapeamento: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

@bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    """Importar mapeamentos via planilha Excel/CSV"""
    if request.method == 'POST':
        try:
            if 'arquivo' not in request.files:
                flash('Nenhum arquivo selecionado', 'warning')
                return redirect(request.url)
            
            arquivo = request.files['arquivo']
            
            if arquivo.filename == '':
                flash('Nenhum arquivo selecionado', 'warning')
                return redirect(request.url)
            
            # Salvar arquivo temporário
            filename = secure_filename(arquivo.filename)
            temp_path = os.path.join('/tmp', filename)
            arquivo.save(temp_path)
            
            # Ler planilha
            if filename.endswith('.csv'):
                df = pd.read_csv(temp_path)
            else:
                df = pd.read_excel(temp_path)
            
            # Validar colunas obrigatórias
            colunas_obrigatorias = ['cod atacadao', 'descricao atacadao', 'nosso cod']
            colunas_existentes = [col.lower() for col in df.columns]
            
            for col in colunas_obrigatorias:
                if col not in colunas_existentes:
                    flash(f'Coluna obrigatória não encontrada: {col}', 'danger')
                    return redirect(request.url)
            
            # Processar linhas
            contador_sucesso = 0
            contador_erro = 0
            erros = []
            
            for index, row in df.iterrows():
                try:
                    codigo_nosso = str(row['nosso cod']).strip()
                    codigo_atacadao = str(row['cod atacadao']).strip()
                    descricao_atacadao = str(row['descricao atacadao']).strip()
                    
                    # Verificar se já existe
                    existe = ProdutoDeParaAtacadao.query.filter_by(
                        codigo_nosso=codigo_nosso,
                        codigo_atacadao=codigo_atacadao
                    ).first()
                    
                    if existe:
                        # Atualizar existente
                        existe.descricao_atacadao = descricao_atacadao
                        existe.atualizado_em = datetime.utcnow()
                    else:
                        # Buscar descrição do nosso produto
                        descricao_nosso = ''
                        produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
                        if produto:
                            descricao_nosso = produto.nome_produto
                        
                        # Criar novo
                        mapeamento = ProdutoDeParaAtacadao(
                            codigo_nosso=codigo_nosso,
                            descricao_nosso=descricao_nosso,
                            codigo_atacadao=codigo_atacadao,
                            descricao_atacadao=descricao_atacadao,
                            fator_conversao=1.0,
                            ativo=True,
                            criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
                        )
                        db.session.add(mapeamento)
                    
                    contador_sucesso += 1
                    
                except Exception as e:
                    contador_erro += 1
                    erros.append(f"Linha {index + 2}: {str(e)}")
                    if contador_erro > 10:  # Limitar erros mostrados
                        break
            
            # Commit se tudo ok
            if contador_sucesso > 0:
                db.session.commit()
                flash(f'✅ {contador_sucesso} mapeamentos importados com sucesso!', 'success')
            
            if contador_erro > 0:
                flash(f'⚠️ {contador_erro} linhas com erro', 'warning')
                for erro in erros[:5]:  # Mostrar até 5 erros
                    flash(erro, 'danger')
            
            # Remover arquivo temporário
            os.remove(temp_path)
            
            return redirect(url_for('portal.portal_depara.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao importar planilha: {e}")
            flash(f'Erro ao importar planilha: {str(e)}', 'danger')
            
            # Remover arquivo temporário se existir
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
    
    return render_template('portal/atacadao/depara/importar.html')

@bp.route('/buscar_produto_nosso/<codigo>')
@login_required
def buscar_produto_nosso(codigo):
    """API para buscar descrição do nosso produto"""
    try:
        produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo).first()
        
        if produto:
            return jsonify({
                'success': True,
                'descricao': produto.nome_produto
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Produto não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao buscar produto: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/converter_codigo/<codigo_nosso>')
@login_required
def converter_codigo(codigo_nosso):
    """API para converter código nosso para código Atacadão"""
    try:
        mapeamento = ProdutoDeParaAtacadao.query.filter_by(
            codigo_nosso=codigo_nosso,
            ativo=True
        ).first()
        
        if mapeamento:
            return jsonify({
                'success': True,
                'codigo_atacadao': mapeamento.codigo_atacadao,
                'descricao_atacadao': mapeamento.descricao_atacadao,
                'fator_conversao': float(mapeamento.fator_conversao)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Mapeamento não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao converter código: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/criar', methods=['POST'])
@login_required
def api_criar():
    """API para criar mapeamento De-Para via AJAX"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        if not data.get('codigo_nosso') or not data.get('codigo_atacadao'):
            return jsonify({
                'success': False,
                'message': 'Códigos são obrigatórios'
            }), 400
        
        # Verificar se já existe
        existe = ProdutoDeParaAtacadao.query.filter_by(
            codigo_nosso=data['codigo_nosso'],
            codigo_atacadao=data['codigo_atacadao']
        ).first()
        
        if existe:
            return jsonify({
                'success': False,
                'message': 'Mapeamento já existe'
            }), 400
        
        # Buscar descrição do nosso produto
        descricao_nosso = ''
        produto = CadastroPalletizacao.query.filter_by(
            cod_produto=data['codigo_nosso']
        ).first()
        if produto:
            descricao_nosso = produto.nome_produto
        
        # Criar novo mapeamento
        mapeamento = ProdutoDeParaAtacadao(
            codigo_nosso=data['codigo_nosso'],
            descricao_nosso=descricao_nosso,
            codigo_atacadao=data['codigo_atacadao'],
            descricao_atacadao=data.get('descricao_atacadao', ''),
            fator_conversao=float(data.get('fator_conversao', 1.0)),
            ativo=True,
            criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
        )
        
        db.session.add(mapeamento)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Mapeamento criado com sucesso',
            'id': mapeamento.id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar mapeamento via API: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500