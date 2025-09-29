"""
Rotas simplificadas para TagPlus v2
"""
from flask import Blueprint, render_template, jsonify, request, redirect, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2
from app.integracoes.tagplus.correcao_pedidos_service_v2 import CorrecaoPedidosServiceV2
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

        # O resultado já vem com a estrutura correta em 'clientes'
        return jsonify({
            'success': True,
            'resultado': resultado.get('clientes', {
                'importados': 0,
                'atualizados': 0,
                'erros': []
            })
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

        # Adaptar estrutura para compatibilidade com o template
        resultado_formatado = {
            'notas_fiscais': {
                'importadas': resultado.get('nfs', {}).get('importadas', 0),
                'itens_importados': resultado.get('nfs', {}).get('itens', 0),
                'pendentes': resultado.get('nfs', {}).get('pendentes', 0),
                'erros': len(resultado.get('nfs', {}).get('erros', []))
            },
            'processamento': resultado.get('processamento', None)
        }

        return jsonify({
            'success': True,
            'resultado': resultado_formatado
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


# ========== ROTAS DE CORREÇÃO DE PEDIDOS ==========

@tagplus_bp.route('/pendencias')
@login_required
def pagina_pendencias():
    """Página de NFs pendentes (sem pedido) - Nova tabela NFPendenteTagPlus"""
    try:
        # Usa o novo service V2 que trabalha com NFPendenteTagPlus
        service_v2 = CorrecaoPedidosServiceV2()

        # Buscar estatísticas
        estatisticas = service_v2.estatisticas_pendentes()

        # Buscar NFs pendentes
        nfs_pendentes = service_v2.listar_nfs_pendentes(limite=100)

        return render_template(
            'integracoes/tagplus_correcao_pedidos.html',
            estatisticas=estatisticas,
            nfs_sem_pedido=nfs_pendentes,
            titulo_pagina='NFs Pendentes - TagPlus'
        )
    except Exception as e:
        logger.error(f"Erro ao carregar página de pendências: {e}")
        flash(f"Erro ao carregar página: {str(e)}", 'error')
        return redirect('/integracoes/tagplus/importacao')

@tagplus_bp.route('/correcao-pedidos')
@login_required
def pagina_correcao_pedidos():
    """Página de correção de pedidos em NFs (redireciona para pendências)"""
    # Redirecionar para a nova rota de pendências
    return redirect('/integracoes/tagplus/pendencias')


# Rotas V1 removidas - agora todas usam V2

# ========== ROTAS V2 - NFPendenteTagPlus ==========

@tagplus_bp.route('/api/v2/atualizar-pedido-pendente', methods=['POST'])
@login_required
def api_v2_atualizar_pedido_pendente():
    """API V2 para atualizar pedido em NF pendente e importar"""
    try:
        dados = request.get_json()
        numero_nf = dados.get('numero_nf')
        numero_pedido = dados.get('numero_pedido')
        importar = dados.get('importar', True)  # Por padrão, importa após preencher

        if not numero_nf or not numero_pedido:
            return jsonify({
                'success': False,
                'erro': 'Número da NF e do pedido são obrigatórios'
            }), 400

        service_v2 = CorrecaoPedidosServiceV2()
        resultado = service_v2.atualizar_pedido_nf(
            numero_nf=numero_nf,
            numero_pedido=numero_pedido,
            importar=importar,
            usuario=current_user.username if hasattr(current_user, 'username') else 'Sistema'
        )

        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"Erro ao atualizar pedido pendente: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@tagplus_bp.route('/api/v2/atualizar-pedidos-pendentes-lote', methods=['POST'])
@login_required
def api_v2_atualizar_pedidos_pendentes_lote():
    """API V2 para atualizar múltiplos pedidos pendentes em lote"""
    try:
        dados = request.get_json()
        atualizacoes = dados.get('atualizacoes', [])
        importar = dados.get('importar', True)

        if not atualizacoes:
            return jsonify({
                'success': False,
                'erro': 'Lista de atualizações vazia'
            }), 400

        service_v2 = CorrecaoPedidosServiceV2()
        resultado = service_v2.atualizar_pedidos_em_lote(
            atualizacoes=atualizacoes,
            importar=importar,
            usuario=current_user.username if hasattr(current_user, 'username') else 'Sistema'
        )

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao processar lote de pedidos pendentes: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@tagplus_bp.route('/api/v2/estatisticas-pendentes', methods=['GET'])
@login_required
def api_v2_estatisticas_pendentes():
    """API V2 para obter estatísticas de NFs pendentes"""
    try:
        service_v2 = CorrecaoPedidosServiceV2()
        estatisticas = service_v2.estatisticas_pendentes()

        return jsonify({
            'success': True,
            'estatisticas': estatisticas
        })

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas pendentes: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@tagplus_bp.route('/api/v2/buscar-pedido-sugerido/<numero_nf>', methods=['GET'])
@login_required
def api_v2_buscar_pedido_sugerido(numero_nf):
    """API V2 para buscar sugestão de pedido para uma NF pendente"""
    try:
        service_v2 = CorrecaoPedidosServiceV2()
        sugestao = service_v2.buscar_pedido_sugerido(numero_nf)

        return jsonify({
            'success': True,
            'sugestao': sugestao,
            'tem_sugestao': sugestao is not None
        })

    except Exception as e:
        logger.error(f"Erro ao buscar sugestão: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500
