"""
Rotas para gerenciamento do De-Para de produtos e filiais do Sendas
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import pandas as pd
import os
import re
from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive
from app.portal.sendas.models import ProdutoDeParaSendas, FilialDeParaSendas
from app.producao.models import CadastroPalletizacao
import logging


def extrair_numero_filial(codigo_filial: str) -> str:
    """
    Extrai o número de 3 dígitos do código da filial.
    Ex: "010 SAO BERNARDO PIRAPORI" -> "010"
    Ex: "007 Santos" -> "007"
    """
    if not codigo_filial:
        return None

    match = re.match(r'^(\d+)', codigo_filial.strip())
    if match:
        return match.group(1).zfill(3)  # Padroniza para 3 dígitos
    return None

logger = logging.getLogger(__name__)

bp = Blueprint('sendas_depara', __name__, url_prefix='/sendas/depara')


# ============== ROTAS DE PRODUTOS ==============

@bp.route('/produtos')
@login_required
def index_produtos():
    total_produtos = ProdutoDeParaSendas.query.count()
    produtos_ativos = ProdutoDeParaSendas.query.filter_by(ativo=True).count()
    produtos_inativos = ProdutoDeParaSendas.query.filter_by(ativo=False).count()

    return render_template('portal/sendas/produtos/index.html',
                        total_produtos=total_produtos,
                        produtos_ativos=produtos_ativos,
                        produtos_inativos=produtos_inativos)

@bp.route('/filiais')
@login_required  
def index_filiais():
    total_filiais = FilialDeParaSendas.query.count()
    filiais_ativas = FilialDeParaSendas.query.filter_by(ativo=True).count()
    filiais_inativas = FilialDeParaSendas.query.filter_by(ativo=False).count()

    return render_template('portal/sendas/filiais/index.html',
                        total_filiais=total_filiais,
                        filiais_ativas=filiais_ativas,
                        filiais_inativas=filiais_inativas)

@bp.route('/produtos/listar')
@login_required
def listar_produtos():
    """Lista todos os mapeamentos De-Para de produtos"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = ProdutoDeParaSendas.query
    
    if search:
        query = query.filter(
            db.or_(
                ProdutoDeParaSendas.codigo_nosso.contains(search),
                ProdutoDeParaSendas.descricao_nosso.contains(search),
                ProdutoDeParaSendas.codigo_sendas.contains(search),
                ProdutoDeParaSendas.descricao_sendas.contains(search)
            )
        )
    
    query = query.order_by(ProdutoDeParaSendas.codigo_nosso)
    
    mapeamentos = query.paginate(page=page, per_page=50, error_out=False)
    
    return render_template('portal/sendas/produtos/listar.html',
                         mapeamentos=mapeamentos,
                         search=search)

@bp.route('/produtos/novo', methods=['GET', 'POST'])
@login_required
def novo_produto():
    """Criar novo mapeamento De-Para de produto"""
    if request.method == 'POST':
        try:
            # Buscar descrição do nosso produto
            codigo_nosso = request.form.get('codigo_nosso', '').strip()
            descricao_nosso = ''
            
            # Buscar em CadastroPalletizacao
            produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
            if produto:
                descricao_nosso = produto.nome_produto
            
            mapeamento = ProdutoDeParaSendas(
                codigo_nosso=codigo_nosso,
                descricao_nosso=descricao_nosso or request.form.get('descricao_nosso', ''),
                codigo_sendas=request.form.get('codigo_sendas', '').strip(),
                descricao_sendas=request.form.get('descricao_sendas', '').strip(),
                cnpj_cliente=request.form.get('cnpj_cliente', '').strip() or None,
                fator_conversao=float(request.form.get('fator_conversao', 1.0)),
                observacoes=request.form.get('observacoes', ''),
                ativo=request.form.get('ativo') == 'on',
                criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )
            
            db.session.add(mapeamento)
            db.session.commit()
            
            flash('Mapeamento de produto criado com sucesso!', 'success')
            return redirect(url_for('portal.sendas_depara.index_produtos'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar mapeamento de produto: {e}")
            flash(f'Erro ao criar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/sendas/produtos/form.html',
                         mapeamento=None,
                         action='novo')

@bp.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    """Editar mapeamento de produto existente"""
    mapeamento = ProdutoDeParaSendas.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Buscar descrição atualizada se mudou código
            codigo_nosso = request.form.get('codigo_nosso', '').strip()
            if codigo_nosso != mapeamento.codigo_nosso:
                produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_nosso).first()
                if produto:
                    mapeamento.descricao_nosso = produto.nome_produto
            
            mapeamento.codigo_nosso = codigo_nosso
            mapeamento.codigo_sendas = request.form.get('codigo_sendas', '').strip()
            mapeamento.descricao_sendas = request.form.get('descricao_sendas', '').strip()
            mapeamento.cnpj_cliente = request.form.get('cnpj_cliente', '').strip() or None
            mapeamento.fator_conversao = float(request.form.get('fator_conversao', 1.0))
            mapeamento.observacoes = request.form.get('observacoes', '')
            mapeamento.ativo = request.form.get('ativo') == 'on'
            mapeamento.atualizado_em = agora_utc_naive()
            
            db.session.commit()
            
            flash('Mapeamento de produto atualizado com sucesso!', 'success')
            return redirect(url_for('portal.sendas_depara.index_produtos'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar mapeamento de produto: {e}")
            flash(f'Erro ao atualizar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/sendas/produtos/form.html',
                         mapeamento=mapeamento,
                         action='editar')

@bp.route('/produtos/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_produto(id):
    """Excluir mapeamento de produto"""
    try:
        mapeamento = ProdutoDeParaSendas.query.get_or_404(id)
        db.session.delete(mapeamento)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mapeamento de produto excluído com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir mapeamento de produto: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

@bp.route('/produtos/importar', methods=['GET', 'POST'])
@login_required
def importar_produtos():
    """Importar mapeamentos de produtos via planilha Excel/CSV"""
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
                df = pd.read_csv(temp_path, encoding='utf-8-sig')
            else:
                df = pd.read_excel(temp_path)
            
            # Processar usando o método da model
            resultado = ProdutoDeParaSendas.importar_de_csv(
                temp_path, 
                cnpj_cliente=request.form.get('cnpj_cliente'),
                criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )
            
            # Remover arquivo temporário
            os.remove(temp_path)
            
            flash(f'✅ {resultado["criados"]} produtos criados, {resultado["atualizados"]} atualizados', 'success')
            
            if resultado['erros']:
                for erro in resultado['erros'][:5]:
                    flash(erro, 'warning')
            
            return redirect(url_for('portal.sendas_depara.index_produtos'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao importar produtos: {e}")
            flash(f'Erro ao importar planilha: {str(e)}', 'danger')
            
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
    
    return render_template('portal/sendas/produtos/importar.html')

# ============== ROTAS DE FILIAIS ==============

@bp.route('/filiais/listar')
@login_required
def listar_filiais():
    """Lista todos os mapeamentos De-Para de filiais"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = FilialDeParaSendas.query
    
    if search:
        query = query.filter(
            db.or_(
                FilialDeParaSendas.numero.contains(search),
                FilialDeParaSendas.cnpj.contains(search),
                FilialDeParaSendas.filial.contains(search),
                FilialDeParaSendas.nome_filial.contains(search),
                FilialDeParaSendas.cidade.contains(search)
            )
        )
    
    query = query.order_by(FilialDeParaSendas.numero, FilialDeParaSendas.filial)

    filiais = query.paginate(page=page, per_page=50, error_out=False)
    
    return render_template('portal/sendas/filiais/listar.html',
                         filiais=filiais,
                         search=search)

@bp.route('/filiais/novo', methods=['GET', 'POST'])
@login_required
def nova_filial():
    """Criar novo mapeamento De-Para de filial"""
    if request.method == 'POST':
        try:
            cnpj = request.form.get('cnpj', '').strip()

            # Formatar CNPJ se necessário
            if '.' not in cnpj and '/' not in cnpj and '-' not in cnpj:
                # Se vier sem formatação, formatar
                cnpj = FilialDeParaSendas.formatar_cnpj(cnpj)

            # Extrair número automaticamente do código da filial
            codigo_filial = request.form.get('filial', '').strip()
            numero = extrair_numero_filial(codigo_filial)

            filial = FilialDeParaSendas(
                cnpj=cnpj,
                filial=codigo_filial,
                numero=numero,  # Número extraído automaticamente
                nome_filial=request.form.get('nome_filial', '').strip(),
                cidade=request.form.get('cidade', '').strip(),
                uf=request.form.get('uf', '').strip().upper(),
                ativo=request.form.get('ativo') == 'on',
                criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )

            db.session.add(filial)
            db.session.commit()
            
            flash('Mapeamento de filial criado com sucesso!', 'success')
            return redirect(url_for('portal.sendas_depara.index_filiais'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar mapeamento de filial: {e}")
            flash(f'Erro ao criar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/sendas/filiais/form.html',
                         filial=None,
                         action='novo')

@bp.route('/filiais/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_filial(id):
    """Editar mapeamento de filial existente"""
    filial = FilialDeParaSendas.query.get_or_404(id)

    if request.method == 'POST':
        try:
            cnpj = request.form.get('cnpj', '').strip()

            # Formatar CNPJ se necessário
            if '.' not in cnpj and '/' not in cnpj and '-' not in cnpj:
                cnpj = FilialDeParaSendas.formatar_cnpj(cnpj)

            # Extrair número automaticamente do código da filial
            codigo_filial = request.form.get('filial', '').strip()
            numero = extrair_numero_filial(codigo_filial)

            filial.cnpj = cnpj
            filial.filial = codigo_filial
            filial.numero = numero  # Atualiza número automaticamente
            filial.nome_filial = request.form.get('nome_filial', '').strip()
            filial.cidade = request.form.get('cidade', '').strip()
            filial.uf = request.form.get('uf', '').strip().upper()
            filial.ativo = request.form.get('ativo') == 'on'
            filial.atualizado_em = agora_utc_naive()

            db.session.commit()
            
            flash('Mapeamento de filial atualizado com sucesso!', 'success')
            return redirect(url_for('portal.sendas_depara.index_filiais'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar mapeamento de filial: {e}")
            flash(f'Erro ao atualizar mapeamento: {str(e)}', 'danger')
    
    return render_template('portal/sendas/filiais/form.html',
                         filial=filial,
                         action='editar')

@bp.route('/filiais/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_filial(id):
    """Excluir mapeamento de filial"""
    try:
        filial = FilialDeParaSendas.query.get_or_404(id)
        db.session.delete(filial)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mapeamento de filial excluído com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir mapeamento de filial: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

@bp.route('/filiais/importar', methods=['GET', 'POST'])
@login_required
def importar_filiais():
    """Importar mapeamentos de filiais via planilha Excel/CSV"""
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
            
            # Processar usando o método da model
            resultado = FilialDeParaSendas.importar_filiais_csv(
                temp_path,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )
            
            # Remover arquivo temporário
            os.remove(temp_path)
            
            flash(f'✅ {resultado["criados"]} filiais criadas, {resultado["atualizados"]} atualizadas', 'success')
            
            if resultado['erros']:
                for erro in resultado['erros'][:5]:
                    flash(erro, 'warning')
            
            return redirect(url_for('portal.sendas_depara.index_filiais'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao importar filiais: {e}")
            flash(f'Erro ao importar planilha: {str(e)}', 'danger')
            
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
    
    return render_template('portal/sendas/filiais/importar.html')

# ============== APIs ==============

@bp.route('/api/buscar_produto_nosso/<codigo>')
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

@bp.route('/api/converter_produto/<codigo_nosso>')
@login_required
def converter_produto(codigo_nosso):
    """API para converter código nosso para código Sendas"""
    try:
        # Tentar com CNPJ específico se fornecido
        cnpj_cliente = request.args.get('cnpj_cliente')
        
        codigo_sendas = ProdutoDeParaSendas.obter_codigo_sendas(codigo_nosso, cnpj_cliente)
        
        if codigo_sendas:
            mapeamento = ProdutoDeParaSendas.query.filter_by(
                codigo_nosso=codigo_nosso,
                codigo_sendas=codigo_sendas,
                ativo=True
            ).first()
            
            return jsonify({
                'success': True,
                'codigo_sendas': codigo_sendas,
                'descricao_sendas': mapeamento.descricao_sendas if mapeamento else '',
                'fator_conversao': float(mapeamento.fator_conversao) if mapeamento else 1.0
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

@bp.route('/api/converter_cnpj/<cnpj>')
@login_required
def converter_cnpj(cnpj):
    """API para converter CNPJ para código de filial"""
    try:
        filial = FilialDeParaSendas.cnpj_to_filial(cnpj)
        
        if filial:
            info = FilialDeParaSendas.obter_info_filial(cnpj)
            return jsonify({
                'success': True,
                'filial': filial,
                'info': info
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Filial não encontrada'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao converter CNPJ: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/api/converter_filial/<filial>')
@login_required
def converter_filial(filial):
    """API para converter código de filial para CNPJ"""
    try:
        cnpj = FilialDeParaSendas.filial_to_cnpj(filial)
        
        if cnpj:
            info = FilialDeParaSendas.obter_info_filial(filial)
            return jsonify({
                'success': True,
                'cnpj': cnpj,
                'cnpj_limpo': FilialDeParaSendas.limpar_cnpj(cnpj),
                'info': info
            })
        else:
            return jsonify({
                'success': False,
                'message': 'CNPJ não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao converter filial: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ============== ROTAS DE EXPORTAÇÃO ==============

@bp.route('/produtos/exportar')
@login_required
def exportar_produtos():
    """Exporta mapeamentos de produtos para XLSX"""
    try:
        from flask import send_file
        from io import BytesIO
        
        # Obter bytes do Excel
        excel_bytes = ProdutoDeParaSendas.exportar_para_xlsx()
        
        # Criar objeto BytesIO para enviar como arquivo
        output = BytesIO(excel_bytes)
        output.seek(0)
        
        # Gerar nome do arquivo com timestamp
        filename = f"produtos_depara_sendas_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar produtos: {e}")
        flash(f'Erro ao exportar produtos: {str(e)}', 'danger')
        return redirect(url_for('portal.sendas_depara.listar_produtos'))

@bp.route('/filiais/exportar')
@login_required
def exportar_filiais():
    """Exporta mapeamentos de filiais para XLSX"""
    try:
        from flask import send_file
        from io import BytesIO
        
        # Obter bytes do Excel
        excel_bytes = FilialDeParaSendas.exportar_filiais_xlsx()
        
        # Criar objeto BytesIO para enviar como arquivo
        output = BytesIO(excel_bytes)
        output.seek(0)
        
        # Gerar nome do arquivo com timestamp
        filename = f"filiais_depara_sendas_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar filiais: {e}")
        flash(f'Erro ao exportar filiais: {str(e)}', 'danger')
        return redirect(url_for('portal.sendas_depara.listar_filiais'))