"""
Rotas para gerenciar De-Para do Portal Tenda
- Importação e manutenção de De-Para EAN
- Importação e manutenção de De-Para Local de Entrega
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename
from app import db
from app.portal.tenda.models import ProdutoDeParaEAN, LocalEntregaDeParaTenda
import os
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('portal_tenda_depara', __name__, url_prefix='/tenda/depara')

# Configuração para upload
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
@login_required
def index():
    """Página principal do De-Para Tenda - Redireciona para index_ean"""
    return redirect(url_for('portal_tenda_depara.index_ean'))

@bp.route('/ean')
@login_required
def index_ean():
    """Página principal do De-Para EAN"""
    return render_template('portal/tenda/depara/index_ean.html')

@bp.route('/filiais')
@login_required
def index_filiais():
    """Página principal do De-Para Filiais"""
    return render_template('portal/tenda/depara/index_filiais.html')

# ========== ROTAS DE-PARA EAN ==========

@bp.route('/ean/listar')
@login_required
def listar_ean():
    """Lista todos os De-Para EAN cadastrados"""
    try:
        # Buscar com paginação
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        query = ProdutoDeParaEAN.query.filter_by(ativo=True)
        
        # Filtros opcionais
        codigo_nosso = request.args.get('codigo_nosso')
        if codigo_nosso:
            query = query.filter(ProdutoDeParaEAN.codigo_nosso.like(f'%{codigo_nosso}%'))
        
        ean = request.args.get('ean')
        if ean:
            query = query.filter(ProdutoDeParaEAN.ean.like(f'%{ean}%'))
        
        # Ordenar e paginar
        depara_list = query.order_by(ProdutoDeParaEAN.codigo_nosso).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            'portal/tenda/depara/listar_ean.html',
            depara_list=depara_list
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar De-Para EAN: {e}")
        flash('Erro ao carregar lista de De-Para EAN', 'error')
        return redirect(url_for('portal_tenda_depara.index'))

@bp.route('/ean/novo', methods=['GET', 'POST'])
@login_required
def novo_ean():
    """Cadastrar novo De-Para EAN"""
    if request.method == 'POST':
        try:
            # Pegar dados do formulário
            codigo_nosso = request.form.get('codigo_nosso')
            descricao_nosso = request.form.get('descricao_nosso')
            ean = request.form.get('ean')
            descricao_ean = request.form.get('descricao_ean')
            fator_conversao = request.form.get('fator_conversao', 1.0, type=float)
            cnpj_cliente = request.form.get('cnpj_cliente')
            
            # Verificar se já existe
            existe = ProdutoDeParaEAN.query.filter_by(
                codigo_nosso=codigo_nosso,
                ean=ean,
                cnpj_cliente=cnpj_cliente if cnpj_cliente else None
            ).first()
            
            if existe:
                flash('De-Para já cadastrado para este código e EAN', 'warning')
                return redirect(url_for('portal_tenda_depara.listar_ean'))
            
            # Criar novo
            novo_depara = ProdutoDeParaEAN(
                codigo_nosso=codigo_nosso,
                descricao_nosso=descricao_nosso,
                ean=ean,
                descricao_ean=descricao_ean,
                fator_conversao=fator_conversao,
                cnpj_cliente=cnpj_cliente if cnpj_cliente else None,
                ativo=True
            )
            
            db.session.add(novo_depara)
            db.session.commit()
            
            flash('De-Para EAN cadastrado com sucesso!', 'success')
            return redirect(url_for('portal_tenda_depara.listar_ean'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cadastrar De-Para EAN: {e}")
            flash(f'Erro ao cadastrar: {str(e)}', 'error')
    
    return render_template('portal/tenda/depara/novo_ean.html')

@bp.route('/ean/importar', methods=['GET', 'POST'])
@login_required
def importar_ean():
    """Importar De-Para EAN via CSV"""
    if request.method == 'POST':
        try:
            # Verificar se tem arquivo
            if 'arquivo' not in request.files:
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            file = request.files['arquivo']
            
            if file.filename == '':
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                # Salvar temporariamente
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Pegar CNPJ se informado
                cnpj_cliente = request.form.get('cnpj_cliente')
                
                # Importar
                resultado = ProdutoDeParaEAN.importar_de_xlsx(
                    filepath,
                    cnpj_cliente=cnpj_cliente if cnpj_cliente else None
                )
                
                # Remover arquivo temporário
                os.remove(filepath)
                
                # Mostrar resultado
                flash(f"Importação concluída: {resultado['criados']} criados, {resultado['atualizados']} atualizados", 'success')
                
                if resultado['erros']:
                    for erro in resultado['erros'][:5]:  # Mostrar até 5 erros
                        flash(erro, 'warning')
                
                return redirect(url_for('portal_tenda_depara.listar_ean'))
                
        except Exception as e:
            logger.error(f"Erro ao importar De-Para EAN: {e}")
            flash(f'Erro na importação: {str(e)}', 'error')
    
    return render_template('portal/tenda/depara/importar_ean.html')

@bp.route('/ean/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_ean(id):
    """Editar De-Para EAN existente"""
    depara = ProdutoDeParaEAN.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            depara.descricao_nosso = request.form.get('descricao_nosso')
            depara.descricao_ean = request.form.get('descricao_ean')
            depara.fator_conversao = request.form.get('fator_conversao', 1.0, type=float)
            
            db.session.commit()
            flash('De-Para atualizado com sucesso!', 'success')
            return redirect(url_for('portal_tenda_depara.listar_ean'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar De-Para EAN: {e}")
            flash(f'Erro ao atualizar: {str(e)}', 'error')
    
    return render_template('portal/tenda/depara/editar_ean.html', depara=depara)

@bp.route('/ean/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_ean(id):
    """Excluir (desativar) De-Para EAN"""
    try:
        depara = ProdutoDeParaEAN.query.get_or_404(id)
        depara.ativo = False
        db.session.commit()
        
        flash('De-Para removido com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir De-Para EAN: {e}")
        flash(f'Erro ao remover: {str(e)}', 'error')
    
    return redirect(url_for('portal_tenda_depara.listar_ean'))

# ========== ROTAS DE-PARA LOCAL ENTREGA ==========

@bp.route('/local')
@login_required
def listar_local():
    """Lista todos os De-Para de Local de Entrega cadastrados"""
    try:
        locais = LocalEntregaDeParaTenda.query.filter_by(ativo=True).all()
        
        return render_template(
            'portal/tenda/depara/listar_local.html',
            locais=locais
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar De-Para Local: {e}")
        flash('Erro ao carregar lista de locais', 'error')
        return redirect(url_for('portal_tenda_depara.index'))

@bp.route('/local/novo', methods=['GET', 'POST'])
@login_required
def novo_local():
    """Cadastrar novo De-Para de Local de Entrega"""
    if request.method == 'POST':
        try:
            from app.portal.utils.grupo_empresarial import GrupoEmpresarial
            
            # Pegar dados do formulário
            cnpj_cliente = GrupoEmpresarial.limpar_cnpj(request.form.get('cnpj_cliente'))
            nome_cliente = request.form.get('nome_cliente')
            grupo_empresarial_nome = request.form.get('grupo_empresarial_nome')
            filial_nome = request.form.get('filial_nome')
            
            # Verificar se já existe
            existe = LocalEntregaDeParaTenda.query.filter_by(
                cnpj_cliente=cnpj_cliente
            ).first()
            
            if existe:
                flash('Local já cadastrado para este CNPJ', 'warning')
                return redirect(url_for('portal_tenda_depara.listar_local'))
            
            # Criar novo
            novo_local = LocalEntregaDeParaTenda(
                cnpj_cliente=cnpj_cliente,
                nome_cliente=nome_cliente,
                grupo_empresarial_nome=grupo_empresarial_nome,
                filial_nome=filial_nome,
                ativo=True
            )
            
            db.session.add(novo_local)
            db.session.commit()
            
            flash('Local de entrega cadastrado com sucesso!', 'success')
            return redirect(url_for('portal_tenda_depara.listar_local'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao cadastrar Local: {e}")
            flash(f'Erro ao cadastrar: {str(e)}', 'error')
    
    return render_template('portal/tenda/depara/novo_local.html')

@bp.route('/local/importar', methods=['GET', 'POST'])
@login_required
def importar_local():
    """Importar De-Para de Local de Entrega via CSV"""
    if request.method == 'POST':
        try:
            # Verificar se tem arquivo
            if 'arquivo' not in request.files:
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            file = request.files['arquivo']
            
            if file.filename == '':
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                # Salvar temporariamente
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Importar
                resultado = LocalEntregaDeParaTenda.importar_de_xlsx(filepath)
                
                # Remover arquivo temporário
                os.remove(filepath)
                
                # Mostrar resultado
                flash(f"Importação concluída: {resultado['criados']} criados, {resultado['atualizados']} atualizados", 'success')
                
                if resultado['erros']:
                    for erro in resultado['erros'][:5]:  # Mostrar até 5 erros
                        flash(erro, 'warning')
                
                return redirect(url_for('portal_tenda_depara.listar_local'))
                
        except Exception as e:
            logger.error(f"Erro ao importar Local: {e}")
            flash(f'Erro na importação: {str(e)}', 'error')
    
    return render_template('portal/tenda/depara/importar_local.html')

@bp.route('/local/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_local(id):
    """Editar De-Para de Local de Entrega existente"""
    local = LocalEntregaDeParaTenda.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            local.nome_cliente = request.form.get('nome_cliente')
            local.grupo_empresarial_nome = request.form.get('grupo_empresarial_nome')
            local.filial_nome = request.form.get('filial_nome')
            
            db.session.commit()
            flash('Local atualizado com sucesso!', 'success')
            return redirect(url_for('portal_tenda_depara.listar_local'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar Local: {e}")
            flash(f'Erro ao atualizar: {str(e)}', 'error')
    
    return render_template('portal/tenda/depara/editar_local.html', local=local)

@bp.route('/local/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_local(id):
    """Excluir (desativar) De-Para de Local de Entrega"""
    try:
        local = LocalEntregaDeParaTenda.query.get_or_404(id)
        local.ativo = False
        db.session.commit()
        
        flash('Local removido com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir Local: {e}")
        flash(f'Erro ao remover: {str(e)}', 'error')
    
    return redirect(url_for('portal_tenda_depara.listar_local'))

# ========== ROTAS API (JSON) ==========

@bp.route('/api/ean/buscar/<codigo_nosso>')
@login_required
def api_buscar_ean(codigo_nosso):
    """API para buscar EAN por código nosso"""
    try:
        cnpj_cliente = request.args.get('cnpj')
        ean = ProdutoDeParaEAN.obter_ean(codigo_nosso, cnpj_cliente)
        
        if ean:
            return jsonify({'success': True, 'ean': ean})
        else:
            return jsonify({'success': False, 'message': 'EAN não encontrado'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/local/buscar/<cnpj>')
@login_required
def api_buscar_local(cnpj):
    """API para buscar local de entrega por CNPJ"""
    try:
        local = LocalEntregaDeParaTenda.obter_local_entrega(cnpj)
        
        if local:
            return jsonify({'success': True, 'local': local})
        else:
            return jsonify({'success': False, 'message': 'Local não encontrado'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500