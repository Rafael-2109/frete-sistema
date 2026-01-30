"""
Rotas para visualização de pedidos no Google Maps
Autor: Sistema Frete
Data: 2025-08-14
"""

import os
from datetime import datetime
from io import BytesIO
from flask import Blueprint, render_template, request, jsonify, session, send_file, url_for
from flask_login import login_required, current_user
from app.carteira.services.mapa_service import MapaService
import logging
import pandas as pd

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
    """API para obter dados dos pedidos para o mapa (versão antiga - mantida para compatibilidade)"""
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


@bp.route('/api/clientes', methods=['POST'])
@login_required
def obter_clientes_mapa():
    """API para obter dados dos clientes (agrupados por CNPJ+endereço) para o mapa"""
    try:
        data = request.get_json()
        pedido_ids = data.get('pedidos', [])

        if not pedido_ids:
            return jsonify({'erro': 'Nenhum pedido selecionado'}), 400

        # Salvar na sessão para uso posterior
        session['pedidos_selecionados_mapa'] = pedido_ids

        # Obter dados dos clientes agrupados
        clientes = mapa_service.obter_clientes_para_mapa(pedido_ids)

        if not clientes:
            return jsonify({'erro': 'Nenhum cliente encontrado com endereço válido'}), 404

        # Calcular resumo
        resumo = {
            'total_clientes': len(clientes),
            'total_pedidos': sum(c['totais']['qtd_pedidos'] for c in clientes),
            'valor_total': sum(c['totais']['valor'] for c in clientes),
            'peso_total': sum(c['totais']['peso'] for c in clientes),
            'pallet_total': sum(c['totais']['pallet'] for c in clientes)
        }

        return jsonify({
            'sucesso': True,
            'clientes': clientes,
            'total': len(clientes),
            'cd': {
                'nome': mapa_service.nome_cd,
                'endereco': mapa_service.endereco_cd,
                'coordenadas': mapa_service.coordenadas_cd
            },
            'resumo': resumo
        })

    except Exception as e:
        logger.error(f"Erro ao obter clientes para mapa: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500
        
@bp.route('/api/rota-otimizada', methods=['POST'])
@login_required
def calcular_rota():
    """API para calcular rota otimizada (versão antiga - mantida para compatibilidade)"""
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


@bp.route('/api/rota-clientes', methods=['POST'])
@login_required
def calcular_rota_clientes():
    """API para calcular rota otimizada entre clientes (agrupados)"""
    try:
        data = request.get_json()
        clientes = data.get('clientes', [])
        origem = data.get('origem')

        if not clientes:
            return jsonify({'erro': 'Nenhum cliente selecionado'}), 400

        # Calcular rota otimizada para clientes
        resultado = mapa_service.calcular_rota_clientes(clientes, origem)

        if 'erro' in resultado:
            return jsonify(resultado), 400

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao calcular rota de clientes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
    """Exporta dados do mapa para relatório (versão JSON - mantida para compatibilidade)"""
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


@bp.route('/api/exportar-excel', methods=['POST'])
@login_required
def exportar_mapa_excel():
    """Exporta dados do mapa em Excel com clientes e pedidos"""
    try:
        data = request.get_json()
        clientes = data.get('clientes', [])
        rota = data.get('rota', None)

        if not clientes:
            return jsonify({'erro': 'Nenhum cliente para exportar'}), 400

        # Montar dados para Excel
        linhas = []
        for i, cliente in enumerate(clientes):
            for pedido in cliente.get('pedidos', []):
                linhas.append({
                    'Ordem': i + 1 if rota else '',
                    'Cliente': cliente.get('cliente', {}).get('nome', ''),
                    'CNPJ': cliente.get('cliente', {}).get('cnpj', ''),
                    'Pedido': pedido.get('num_pedido', ''),
                    'Valor (R$)': pedido.get('valor', 0),
                    'Peso (kg)': pedido.get('peso', 0),
                    'Pallets': pedido.get('pallet', 0),
                    'Expedição': pedido.get('expedicao', ''),
                    'Agendamento': pedido.get('agendamento', ''),
                    'Status Agend.': 'Confirmado' if pedido.get('agendamento_confirmado') else 'Aguardando Aprovação',
                    'Cidade': cliente.get('endereco', {}).get('cidade', ''),
                    'UF': cliente.get('endereco', {}).get('uf', ''),
                    'Endereço': cliente.get('endereco', {}).get('completo', '')
                })

        df = pd.DataFrame(linhas)

        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Pedidos', index=False)

            # Ajustar largura das colunas
            worksheet = writer.sheets['Pedidos']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(idx, idx, min(max_len, 50))

            # Se tem rota, adicionar aba com resumo
            if rota:
                resumo_data = [{
                    'Informação': 'Distância Total',
                    'Valor': f"{rota.get('distancia_total_km', 0):.1f} km"
                }, {
                    'Informação': 'Tempo Estimado',
                    'Valor': rota.get('tempo_formatado', '')
                }, {
                    'Informação': 'Total de Clientes',
                    'Valor': len(clientes)
                }, {
                    'Informação': 'Total de Pedidos',
                    'Valor': len(linhas)
                }, {
                    'Informação': 'Valor Total',
                    'Valor': f"R$ {sum(l['Valor (R$)'] for l in linhas):,.2f}"
                }, {
                    'Informação': 'Peso Total',
                    'Valor': f"{sum(l['Peso (kg)'] for l in linhas):,.2f} kg"
                }]
                resumo_df = pd.DataFrame(resumo_data)
                resumo_df.to_excel(writer, sheet_name='Resumo Rota', index=False)

                # Aba com ordem de entrega
                ordem_data = []
                ordem_clientes = rota.get('ordem_clientes', [])
                for idx, cliente_id in enumerate(ordem_clientes):
                    cliente_match = next((c for c in clientes if c.get('cliente_id') == cliente_id), None)
                    if cliente_match:
                        pedidos_str = ', '.join([p.get('num_pedido', '') for p in cliente_match.get('pedidos', [])])
                        ordem_data.append({
                            'Ordem': idx + 1,
                            'Cliente': cliente_match.get('cliente', {}).get('nome', ''),
                            'CNPJ': cliente_match.get('cliente', {}).get('cnpj', ''),
                            'Pedidos': pedidos_str,
                            'Qtd. Pedidos': len(cliente_match.get('pedidos', [])),
                            'Valor Total': sum(p.get('valor', 0) for p in cliente_match.get('pedidos', [])),
                            'Peso Total': sum(p.get('peso', 0) for p in cliente_match.get('pedidos', []))
                        })
                if ordem_data:
                    ordem_df = pd.DataFrame(ordem_data)
                    ordem_df.to_excel(writer, sheet_name='Ordem de Entrega', index=False)

        output.seek(0)
        nome_arquivo = f"mapa_pedidos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )

    except Exception as e:
        logger.error(f"Erro ao exportar Excel: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/cotar-frete', methods=['POST'])
@login_required
def cotar_frete_mapa():
    """Prepara cotação de frete para pedidos selecionados no mapa"""
    try:
        from app.separacao.models import Separacao

        data = request.get_json()
        pedido_ids = data.get('pedidos', [])  # Lista de num_pedido

        if not pedido_ids:
            return jsonify({'erro': 'Nenhum pedido selecionado'}), 400

        # Buscar separacao_lote_ids correspondentes
        separacoes = Separacao.query.filter(
            Separacao.num_pedido.in_(pedido_ids),
            Separacao.sincronizado_nf == False
        ).all()

        lotes = list(set([s.separacao_lote_id for s in separacoes if s.separacao_lote_id]))

        if not lotes:
            return jsonify({'erro': 'Nenhuma separação encontrada para os pedidos selecionados'}), 400

        # Salvar na sessão com as mesmas chaves que iniciar_cotacao usa
        session['cotacao_lotes'] = lotes
        session['cotacao_pedidos'] = lotes  # Retrocompatibilidade

        # Limpar alteração de embarque anterior se houver
        session.pop('alterando_embarque', None)

        return jsonify({
            'sucesso': True,
            'total_lotes': len(lotes),
            'lotes': lotes,
            'redirect': url_for('cotacao.tela_cotacao')
        })

    except Exception as e:
        logger.error(f"Erro ao preparar cotação do mapa: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500