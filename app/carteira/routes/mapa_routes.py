"""
Rotas para visualização de pedidos no Google Maps
Autor: Sistema Frete
Data: 2025-08-14
"""

import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from app.carteira.services.mapa_service import MapaService
import logging

logger = logging.getLogger(__name__)

# Criar blueprint
bp = Blueprint('mapa', __name__, url_prefix='/carteira/mapa')

# Instanciar serviço
mapa_service = MapaService()

@bp.route('/visualizar')
@login_required
def visualizar_mapa():
    """Página principal de visualização no mapa"""
    try:
        # Obter API key para o template
        api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
        
        # Obter pedidos selecionados da sessão ou query string
        pedidos_selecionados = request.args.getlist('pedidos[]')
        
        if not pedidos_selecionados:
            # Tentar obter da sessão
            pedidos_selecionados = session.get('pedidos_selecionados_mapa', [])
            
        return render_template(
            'carteira/mapa_pedidos.html',
            api_key=api_key,
            pedidos_selecionados=pedidos_selecionados,
            usuario=current_user
        )
        
    except Exception as e:
        logger.error(f"Erro ao carregar página do mapa: {str(e)}")
        return f"Erro ao carregar mapa: {str(e)}", 500
        
@bp.route('/api/pedidos', methods=['POST'])
@login_required
def obter_pedidos_mapa():
    """API para obter dados dos pedidos para o mapa"""
    try:
        data = request.get_json()
        pedido_ids = data.get('pedidos', [])
        
        if not pedido_ids:
            return jsonify({'erro': 'Nenhum pedido selecionado'}), 400
            
        # Salvar na sessão para uso posterior
        session['pedidos_selecionados_mapa'] = pedido_ids
        
        # Obter dados dos pedidos
        pedidos = mapa_service.obter_pedidos_para_mapa(pedido_ids)
        
        if not pedidos:
            return jsonify({'erro': 'Nenhum pedido encontrado com endereço válido'}), 404
            
        return jsonify({
            'sucesso': True,
            'pedidos': pedidos,
            'total': len(pedidos),
            'cd': {
                'nome': mapa_service.nome_cd,
                'endereco': mapa_service.endereco_cd,
                'coordenadas': mapa_service.coordenadas_cd
            },
            'resumo': {
                'valor_total': sum(p['valores']['total'] for p in pedidos),
                'peso_total': sum(p['valores']['peso'] for p in pedidos),
                'pallet_total': sum(p['valores']['pallet'] for p in pedidos)
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter pedidos para mapa: {str(e)}")
        return jsonify({'erro': str(e)}), 500
        
@bp.route('/api/rota-otimizada', methods=['POST'])
@login_required
def calcular_rota():
    """API para calcular rota otimizada"""
    try:
        data = request.get_json()
        pedido_ids = data.get('pedidos', [])
        origem = data.get('origem')
        
        if not pedido_ids:
            return jsonify({'erro': 'Nenhum pedido selecionado'}), 400
            
        # Calcular rota otimizada
        resultado = mapa_service.calcular_rota_otimizada(pedido_ids, origem)
        
        if 'erro' in resultado:
            return jsonify(resultado), 400
            
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro ao calcular rota: {str(e)}")
        return jsonify({'erro': str(e)}), 500
        
@bp.route('/api/densidade-regional', methods=['POST'])
@login_required
def analisar_densidade():
    """API para análise de densidade regional"""
    try:
        data = request.get_json()
        pedido_ids = data.get('pedidos')  # None = todos os pedidos
        
        # Analisar densidade
        densidade = mapa_service.analisar_densidade_regional(pedido_ids)
        
        return jsonify({
            'sucesso': True,
            'densidade': densidade
        })
        
    except Exception as e:
        logger.error(f"Erro ao analisar densidade: {str(e)}")
        return jsonify({'erro': str(e)}), 500
        
@bp.route('/api/matriz-distancias', methods=['POST'])
@login_required
def calcular_matriz():
    """API para calcular matriz de distâncias"""
    try:
        data = request.get_json()
        pedido_ids = data.get('pedidos', [])
        
        if len(pedido_ids) < 2:
            return jsonify({'erro': 'Selecione pelo menos 2 pedidos'}), 400
            
        # Calcular matriz
        matriz = mapa_service.calcular_matriz_distancias(pedido_ids)
        
        if 'erro' in matriz:
            return jsonify(matriz), 400
            
        return jsonify({
            'sucesso': True,
            'matriz': matriz
        })
        
    except Exception as e:
        logger.error(f"Erro ao calcular matriz: {str(e)}")
        return jsonify({'erro': str(e)}), 500
        
@bp.route('/api/geocodificar', methods=['POST'])
@login_required
def geocodificar():
    """API para geocodificar endereço individual"""
    try:
        data = request.get_json()
        endereco = data.get('endereco')
        
        if not endereco:
            return jsonify({'erro': 'Endereço não fornecido'}), 400
            
        # Geocodificar
        lat, lng = mapa_service.geocodificar_endereco(endereco)
        
        if lat and lng:
            return jsonify({
                'sucesso': True,
                'coordenadas': {
                    'lat': lat,
                    'lng': lng
                }
            })
        else:
            return jsonify({'erro': 'Não foi possível geocodificar o endereço'}), 400
            
    except Exception as e:
        logger.error(f"Erro ao geocodificar: {str(e)}")
        return jsonify({'erro': str(e)}), 500
        
@bp.route('/api/salvar-configuracao', methods=['POST'])
@login_required
def salvar_configuracao():
    """Salva configurações do mapa do usuário"""
    try:
        data = request.get_json()
        
        # Salvar na sessão
        session['mapa_config'] = {
            'tipo_mapa': data.get('tipo_mapa', 'roadmap'),
            'zoom': data.get('zoom', 10),
            'centro': data.get('centro'),
            'mostrar_clustering': data.get('mostrar_clustering', True),
            'mostrar_rota': data.get('mostrar_rota', False),
            'mostrar_densidade': data.get('mostrar_densidade', False)
        }
        
        return jsonify({'sucesso': True})
        
    except Exception as e:
        logger.error(f"Erro ao salvar configuração: {str(e)}")
        return jsonify({'erro': str(e)}), 500
        
@bp.route('/api/exportar-mapa', methods=['POST'])
@login_required
def exportar_mapa():
    """Exporta dados do mapa para relatório"""
    try:
        data = request.get_json()
        pedido_ids = data.get('pedidos', [])
        incluir_rota = data.get('incluir_rota', False)
        incluir_densidade = data.get('incluir_densidade', False)
        
        # Preparar dados para exportação
        export_data = {
            'pedidos': mapa_service.obter_pedidos_para_mapa(pedido_ids),
            'gerado_por': current_user.nome,
            'data_geracao': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        if incluir_rota and len(pedido_ids) > 1:
            export_data['rota'] = mapa_service.calcular_rota_otimizada(pedido_ids)
            
        if incluir_densidade:
            export_data['densidade'] = mapa_service.analisar_densidade_regional(pedido_ids)
            
        return jsonify({
            'sucesso': True,
            'dados': export_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao exportar mapa: {str(e)}")
        return jsonify({'erro': str(e)}), 500