"""
Rotas simplificadas para TagPlus v2
"""
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import login_required
from datetime import datetime, timedelta, date
from app import db
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
import logging

logger = logging.getLogger(__name__)

tagplus_bp = Blueprint('tagplus', __name__, url_prefix='/integracoes/tagplus')

@tagplus_bp.route('/importacao')
@login_required
def pagina_importacao():
    """Página de importação TagPlus"""
    return render_template('integracoes/tagplus_importacao.html', 
                         date=date, 
                         timedelta=timedelta)

@tagplus_bp.route('/importar')
@login_required
def importar():
    """Redireciona para página OAuth"""
    return redirect('/tagplus/oauth/')

@tagplus_bp.route('/api/testar-conexao', methods=['POST'])
@login_required
def testar_conexao():
    """Testa conexão com TagPlus"""
    try:
        importador = ImportadorTagPlusV2()
        resultado = importador.testar_conexoes()
        
        sucesso_total = any([
            resultado.get('clientes', {}).get('sucesso'),
            resultado.get('notas', {}).get('sucesso')
        ])
        
        if sucesso_total:
            return jsonify({
                'success': True,
                'mensagem': 'Conexão estabelecida!',
                'detalhes': resultado
            })
        else:
            return jsonify({
                'success': False,
                'erro': 'Nenhuma API conectada. Faça a autorização OAuth2 primeiro.',
                'detalhes': resultado
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/api/importar-clientes', methods=['POST'])
@login_required
def importar_clientes():
    """Importa clientes do TagPlus"""
    try:
        dados = request.get_json()
        limite = dados.get('limite', 100)
        
        importador = ImportadorTagPlusV2()
        resultado = importador.importar_clientes(limite=limite)
        
        return jsonify({
            'success': True,
            'resultado': resultado
        })
        
    except Exception as e:
        logger.error(f"Erro ao importar clientes: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/api/importar-nfs', methods=['POST'])
@login_required
def importar_nfs():
    """Importa NFs do TagPlus"""
    try:
        dados = request.get_json()
        
        # Pega datas do request
        if dados.get('data_inicio'):
            data_inicio = datetime.strptime(dados['data_inicio'], '%Y-%m-%d').date()
        else:
            data_inicio = datetime.now().date() - timedelta(days=7)
        
        if dados.get('data_fim'):
            data_fim = datetime.strptime(dados['data_fim'], '%Y-%m-%d').date()
        else:
            data_fim = datetime.now().date()
        
        limite = dados.get('limite', 100)
        
        importador = ImportadorTagPlusV2()
        resultado = importador.importar_nfs(
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=limite
        )
        
        return jsonify({
            'success': True,
            'resultado': resultado
        })
        
    except Exception as e:
        logger.error(f"Erro ao importar NFs: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@tagplus_bp.route('/api/status', methods=['GET'])
@login_required
def status_api():
    """Retorna status das APIs"""
    try:
        importador = ImportadorTagPlusV2()
        resultado = importador.testar_conexoes()
        
        return jsonify({
            'success': True,
            'apis': resultado
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500