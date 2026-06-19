"""
Rotas para visualização de pedidos no Google Maps
Autor: Sistema Frete
Data: 2025-08-14
"""

import os
from io import BytesIO
from flask import Blueprint, render_template, request, jsonify, session, send_file, url_for
from flask_login import login_required, current_user
from app.carteira.services.mapa_service import MapaService
import logging
import pandas as pd
from app.utils.timezone import agora_utc_naive
from app.carteira.services.roteirizacao_service import (
    otimizar_rota, selecionar_veiculo, calcular_custo_operacional,
)
from app.veiculos.models import Veiculo
from app.carteira.models import RotaSalva
from app import db
logger = logging.getLogger(__name__)

# Criar blueprint
bp = Blueprint('mapa', __name__, url_prefix='/carteira/mapa')

# Instanciar serviço
mapa_service = MapaService()

@bp.route('/visualizar')
@login_required
def visualizar_mapa():
    """Página principal de visualização no mapa.

    Aceita ?lotes[]=... (preferido — separacao_lote_id, distingue CarVia)
    ou ?pedidos[]=... (legado — num_pedido).
    """
    try:
        # Obter API key para o template
        api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')

        # Preferir lotes (separacao_lote_id) — robusto para NACOM + CarVia
        lotes_selecionados = request.args.getlist('lotes[]')
        # Compat: aceitar pedidos[] (legado, num_pedido)
        pedidos_selecionados = request.args.getlist('pedidos[]')

        # Resgatar uma rota salva por ?rota_id= (preserva a ordem e nao estoura a
        # URL; usado pelo acumulo a partir de lista_pedidos — item #6)
        rota_id = request.args.get('rota_id')
        if rota_id:
            rota = RotaSalva.query.get(rota_id)
            if rota and rota.lotes:
                lotes_selecionados = list(rota.lotes)

        if not lotes_selecionados and not pedidos_selecionados:
            # Tentar obter da sessão
            lotes_selecionados = session.get('lotes_selecionados_mapa', [])
            pedidos_selecionados = session.get('pedidos_selecionados_mapa', [])

        return render_template(
            'carteira/mapa_pedidos.html',
            api_key=api_key,
            pedidos_selecionados=pedidos_selecionados,
            lotes_selecionados=lotes_selecionados,
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
    """API para obter dados dos clientes (agrupados por CNPJ+endereço) para o mapa.

    Body JSON:
      - lotes: lista de separacao_lote_id (preferido — distingue CarVia via prefixo)
      - pedidos: lista de num_pedido (legado/compat)
    """
    try:
        data = request.get_json() or {}
        lotes = data.get('lotes', []) or []
        pedido_ids = data.get('pedidos', []) or []

        if not lotes and not pedido_ids:
            return jsonify({'erro': 'Nenhum pedido selecionado'}), 400

        # Salvar na sessão para uso posterior
        session['lotes_selecionados_mapa'] = lotes
        session['pedidos_selecionados_mapa'] = pedido_ids

        # Obter dados dos clientes agrupados (suporta NACOM + CarVia)
        clientes = mapa_service.obter_clientes_para_mapa(
            pedido_ids, lotes=lotes
        )

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


@bp.route('/api/matriz-clientes', methods=['POST'])
@login_required
def calcular_matriz_clientes_route():
    """Matriz de distancias par-a-par entre as paradas selecionadas no mapa
    (clientes agrupados com coordenadas). Alinha com o fluxo por lotes/CarVia."""
    try:
        data = request.get_json() or {}
        clientes = data.get('clientes', [])
        if len(clientes) < 2:
            return jsonify({'erro': 'Selecione pelo menos 2 entregas'}), 400
        matriz = mapa_service.calcular_matriz_clientes(clientes)
        if 'erro' in matriz:
            return jsonify(matriz), 400
        return jsonify({'sucesso': True, 'matriz': matriz})
    except Exception as e:
        logger.error(f"Erro ao calcular matriz de clientes: {str(e)}")
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
            'data_geracao': agora_utc_naive().strftime('%d/%m/%Y %H:%M')
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
                max_len = max(df[col].fillna('').astype(str).map(len).max(), len(col)) + 2
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
        nome_arquivo = f"mapa_pedidos_{agora_utc_naive().strftime('%Y%m%d_%H%M')}.xlsx"

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


@bp.route('/api/rota/otimizar', methods=['POST'])
@login_required
def rota_otimizar():
    """Otimiza a rota das paradas + custo parametrico por tipo de veiculo."""
    try:
        data = request.get_json() or {}
        clientes = data.get('clientes', [])
        if not clientes:
            return jsonify({'erro': 'Nenhuma parada informada'}), 400

        inclui_volta = bool(data.get('inclui_volta'))
        dias_viagem = int(data.get('dias_viagem') or 0)
        # otimizar=False => respeita a ordem recebida (drag-and-drop manual)
        respeitar_ordem = not bool(data.get('otimizar', True))

        # Origem como 'lat,lng' (Route Optimization exige coordenadas; Directions tambem aceita)
        origem_in = data.get('origem')
        if origem_in:
            o_lat, o_lng = mapa_service.geocodificar_endereco(origem_in)
            origem = f"{o_lat},{o_lng}" if o_lat is not None else origem_in
        else:
            cd = mapa_service.coordenadas_cd
            origem = f"{cd['lat']},{cd['lng']}"

        paradas = [{'id': c['id'], 'lat': c['lat'], 'lng': c['lng']} for c in clientes]
        rota = otimizar_rota(paradas, origem=origem, inclui_volta=inclui_volta,
                             respeitar_ordem=respeitar_ordem)

        # Enriquecer a rota para o DESENHO no mapa (unificacao R1: desenho + custo
        # vem da MESMA chamada — aliases p/ o formato que o front ja consome).
        seg = int(round((rota.get('tempo_min') or 0) * 60))
        rota_out = dict(rota)
        rota_out['ordem_clientes'] = rota.get('ordem', [])
        rota_out['ordem_pedidos'] = rota.get('ordem', [])
        rota_out['distancia_total_km'] = rota.get('distancia_km', 0.0)
        rota_out['tempo_total_minutos'] = rota.get('tempo_min', 0.0)
        rota_out['tempo_formatado'] = mapa_service._formatar_tempo(seg)

        peso = sum(float(c.get('peso') or 0) for c in clientes)
        pallets = sum(float(c.get('pallet') or 0) for c in clientes)
        m3 = sum(float(c.get('m3') or 0) for c in clientes)

        veiculo = (Veiculo.query.get(data['veiculo_id'])
                   if data.get('veiculo_id') else selecionar_veiculo(peso, pallets, m3))

        custo = (calcular_custo_operacional(rota['distancia_km'], rota['tempo_min'],
                                            veiculo, dias_viagem=dias_viagem)
                 if veiculo else {})
        pedagio = mapa_service._calcular_pedagio_estimado(rota['distancia_km'], veiculo)
        valor_pedagio = pedagio.get('valor_total', 0) if isinstance(pedagio, dict) else 0
        total = round(custo.get('custo_operacional', 0) + valor_pedagio, 2)

        # Receita CarVia dos lotes selecionados (viabilidade pre-embarque)
        from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
        carvia = receita_carvia_por_lotes(data.get('lotes') or [])

        return jsonify({
            'sucesso': True,
            'rota': rota_out,
            'veiculo': {
                'id': veiculo.id, 'nome': veiculo.nome,
                'peso_maximo': veiculo.peso_maximo,
                'tipo': veiculo.tipo_veiculo,
                'eixos': veiculo.qtd_eixos,
                'capacidade_pallets': veiculo.capacidade_pallets,
                'capacidade_m3': veiculo.capacidade_m3,
                'multiplicador_pedagio': veiculo.multiplicador_pedagio,
            } if veiculo else None,
            'custo': {
                'dias': custo.get('dias', dias_viagem),
                'combustivel': custo.get('custo_combustivel', 0),
                'motorista': custo.get('custo_motorista', 0),
                'fixo': custo.get('custo_fixo', 0),
                'depreciacao': custo.get('custo_depreciacao', 0),
                'pedagio': valor_pedagio,
                'total': total,
            },
            'pedagio': pedagio if isinstance(pedagio, dict) else None,
            'carvia_receita_total': carvia['total'],
            'carvia_por_lote': carvia['por_lote'],
            'viabilidade': round(carvia['total'] - total, 2),
        })
    except Exception as e:
        logger.error(f"Erro em rota_otimizar: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rota/salvar', methods=['POST'])
@login_required
def rota_salvar():
    """Persiste uma rota (agrupamento de lotes + parametros + custo snapshot)."""
    try:
        data = request.get_json() or {}
        if not data.get('lotes'):
            return jsonify({'erro': 'Rota sem lotes'}), 400
        custo = data.get('custo') or {}
        rota = RotaSalva(
            nome=(data.get('nome') or None),
            criado_por=getattr(current_user, 'id', None),
            veiculo_id=data.get('veiculo_id'),
            origem_endereco=data.get('origem'),
            inclui_volta=bool(data.get('inclui_volta')),
            dias_viagem=int(data.get('dias_viagem') or 0),
            lotes=data.get('lotes'),
            ordem_otimizada=data.get('ordem_otimizada'),
            distancia_km=data.get('distancia_km'),
            tempo_min=data.get('tempo_min'),
            peso_total=data.get('peso_total'),
            pallet_total=data.get('pallet_total'),
            valor_total=data.get('valor_total'),
            custo_combustivel=custo.get('combustivel'),
            custo_motorista=custo.get('motorista'),
            custo_fixo=custo.get('fixo'),
            custo_depreciacao=custo.get('depreciacao'),
            custo_pedagio=custo.get('pedagio'),
            custo_total=custo.get('total'),
            polyline=data.get('polyline'),
            status='salva',
        )
        db.session.add(rota)
        db.session.commit()
        return jsonify({'sucesso': True, 'id': rota.id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar rota: {e}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rotas', methods=['GET'])
@login_required
def rota_listar():
    """Lista as rotas salvas — COMPARTILHADAS entre todos os usuarios.

    Carregar/excluir/cotar uma rota ja operam por id sem dono; a listagem
    tambem nao filtra por `criado_por` (rotas sao um recurso de equipe).
    """
    rotas = (
        RotaSalva.query
        .order_by(RotaSalva.criado_em.desc())
        .limit(200)
        .all()
    )
    return jsonify({'sucesso': True, 'rotas': [r.to_dict() for r in rotas]})


@bp.route('/api/rota/<int:rota_id>', methods=['GET'])
@login_required
def rota_carregar(rota_id):
    rota = RotaSalva.query.get(rota_id)
    if not rota:
        return jsonify({'erro': 'Rota nao encontrada'}), 404
    return jsonify({'sucesso': True, 'rota': rota.to_dict()})


@bp.route('/api/rota/<int:rota_id>', methods=['DELETE'])
@login_required
def rota_excluir(rota_id):
    rota = RotaSalva.query.get(rota_id)
    if not rota:
        return jsonify({'erro': 'Rota nao encontrada'}), 404
    db.session.delete(rota)
    db.session.commit()
    return jsonify({'sucesso': True})


@bp.route('/api/rota/adicionar-cliente', methods=['POST'])
@login_required
def rota_adicionar_cliente():
    """Busca cliente(s) por lote/pedido p/ incluir on-demand no mapa.

    Retorna no MESMO formato de /api/clientes (o front faz push em clientesData,
    re-plota e re-otimiza). Reaproveita obter_clientes_para_mapa (sem duplicar).
    """
    try:
        data = request.get_json() or {}
        lotes = data.get('lotes', []) or []
        pedidos = data.get('pedidos', []) or []
        if not lotes and not pedidos:
            return jsonify({'erro': 'Informe lotes ou pedidos'}), 400
        clientes = mapa_service.obter_clientes_para_mapa(pedidos, lotes=lotes)
        if not clientes:
            return jsonify({'erro': 'Nenhum cliente encontrado'}), 404
        return jsonify({'sucesso': True, 'clientes': clientes})
    except Exception as e:
        logger.error(f"Erro ao adicionar cliente: {e}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rota/<int:rota_id>/cotar', methods=['POST'])
@login_required
def rota_cotar(rota_id):
    """Cota o frete a partir de uma rota salva: popula a sessao de cotacao com os
    lotes da rota e redireciona para o wizard (mesmo contrato de cotar_frete_mapa)."""
    try:
        rota = RotaSalva.query.get(rota_id)
        if not rota:
            return jsonify({'erro': 'Rota nao encontrada'}), 404
        lotes = list(rota.lotes or [])
        if not lotes:
            return jsonify({'erro': 'Rota sem lotes'}), 400
        session['cotacao_lotes'] = lotes
        session['cotacao_pedidos'] = lotes  # retrocompat
        session.pop('alterando_embarque', None)
        return jsonify({
            'sucesso': True,
            'total_lotes': len(lotes),
            'lotes': lotes,
            'redirect': url_for('cotacao.tela_cotacao'),
        })
    except Exception as e:
        logger.error(f"Erro ao cotar rota salva: {e}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rota/buscar-pendentes', methods=['POST'])
@login_required
def rota_buscar_pendentes():
    """Busca Separacoes pendentes de embarque com filtros (modal do mapa, item #7).
    Retorna lotes para o usuario escolher e incluir via /api/rota/adicionar-cliente."""
    try:
        filtros = request.get_json() or {}
        resultados = mapa_service.buscar_separacoes_pendentes(filtros)
        return jsonify({'sucesso': True, 'resultados': resultados, 'total': len(resultados)})
    except Exception as e:
        logger.error(f"Erro ao buscar pendentes: {e}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rota/sub-rotas-pendentes', methods=['GET'])
@login_required
def rota_sub_rotas_pendentes():
    """Sub-rotas distintas das Separacoes pendentes — popula o select do modal."""
    return jsonify({'sucesso': True, 'sub_rotas': mapa_service.sub_rotas_pendentes()})


@bp.route('/api/parada-extra', methods=['POST'])
@login_required
def parada_extra():
    """Geocodifica uma parada extra por CNPJ (ReceitaWS) ou endereco livre, para
    incluir no mapa um ponto que afeta a rota/custo mas NAO entra na cotacao
    (placeholder no front, sem lote/pedido) — item #5."""
    try:
        data = request.get_json() or {}
        cnpj = (data.get('cnpj') or '').strip()
        endereco_in = (data.get('endereco') or '').strip()
        nome, cidade, uf = 'Parada extra', '', ''

        if cnpj:
            from app.utils.api_receita import APIReceita
            dados = APIReceita.buscar_cnpj(cnpj)
            if not dados:
                return jsonify({'erro': 'CNPJ nao encontrado'}), 404
            nome = dados.get('nome') or dados.get('fantasia') or 'Parada extra'
            cidade = dados.get('municipio') or ''
            uf = dados.get('uf') or ''
            partes = [dados.get('logradouro'), dados.get('numero'), dados.get('bairro'),
                      cidade, uf, dados.get('cep'), 'Brasil']
            endereco_str = ', '.join(str(p) for p in partes if p)
        elif endereco_in:
            endereco_str = endereco_in
        else:
            return jsonify({'erro': 'Informe um CNPJ ou endereco'}), 400

        lat, lng = mapa_service.geocodificar_endereco(endereco_str)
        if lat is None or lng is None:
            return jsonify({'erro': 'Nao foi possivel localizar o endereco'}), 400

        return jsonify({
            'sucesso': True,
            'coordenadas': {'lat': lat, 'lng': lng},
            'endereco': endereco_str, 'cidade': cidade, 'uf': uf,
            'nome': nome, 'cnpj': cnpj or None,
        })
    except Exception as e:
        logger.error(f"Erro em parada_extra: {e}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rota/acumular', methods=['POST'])
@login_required
def rota_acumular():
    """Acumula lotes numa rota salva SEM abrir o mapa (chamado de lista_pedidos).

    Com `rota_id` anexa os lotes (deduplicando) a uma rota existente; sem ele cria
    uma nova RotaSalva 'rascunho'. Permite somar pedidos de filtros diferentes e
    depois resgatar tudo no mapa via ?rota_id= (item #6)."""
    try:
        data = request.get_json() or {}
        lotes_novos = [l for l in (data.get('lotes') or []) if l]
        if not lotes_novos:
            return jsonify({'erro': 'Nenhum lote informado'}), 400

        rota_id = data.get('rota_id')
        if rota_id:
            rota = RotaSalva.query.get(rota_id)
            if not rota:
                return jsonify({'erro': 'Rota nao encontrada'}), 404
            atuais = list(rota.lotes or [])
            for l in lotes_novos:
                if l not in atuais:
                    atuais.append(l)
            rota.lotes = atuais  # reatribui (JSON) p/ o SQLAlchemy detectar a mudanca
        else:
            rota = RotaSalva(
                nome=(data.get('nome') or None),
                criado_por=getattr(current_user, 'id', None),
                lotes=lotes_novos,
                status='rascunho',
            )
            db.session.add(rota)
        db.session.commit()
        return jsonify({'sucesso': True, 'id': rota.id, 'nome': rota.nome,
                        'total_lotes': len(rota.lotes or [])})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao acumular rota: {e}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rota/agrupar', methods=['POST'])
@login_required
def rota_agrupar():
    """Cria uma NOVA RotaSalva unindo os lotes de rota(s) salva(s) com os lotes em
    avaliacao no mapa, SEM alterar as rotas de origem (diferente de `rota_acumular`,
    que muta a rota existente).

    Ex.: Rota 1 (5 lotes) + avaliacao (5 lotes) -> a Rota 1 permanece intacta e cria
    a Rota 2 com os 10 lotes (deduplicados, ordem preservada). Body JSON:
      - rota_ids: lista de ids de RotaSalva a unir (ou `rota_id` unico, compat)
      - lotes: separacao_lote_id em avaliacao a somar
      - nome: nome opcional da nova rota
    """
    try:
        data = request.get_json() or {}
        rota_ids = list(data.get('rota_ids') or [])
        if not rota_ids and data.get('rota_id'):
            rota_ids = [data.get('rota_id')]
        lotes_avaliacao = [l for l in (data.get('lotes') or []) if l]

        if not rota_ids and not lotes_avaliacao:
            return jsonify({'erro': 'Informe ao menos uma rota e/ou lotes'}), 400

        # Uniao preservando ordem: lotes das rotas base (na ordem dos ids) e depois
        # os lotes em avaliacao; cada lote entra uma unica vez.
        lotes_union, vistos = [], set()
        for rid in rota_ids:
            rota = RotaSalva.query.get(rid)
            if not rota:
                return jsonify({'erro': f'Rota {rid} nao encontrada'}), 404
            for l in (rota.lotes or []):
                if l not in vistos:
                    vistos.add(l)
                    lotes_union.append(l)
        for l in lotes_avaliacao:
            if l not in vistos:
                vistos.add(l)
                lotes_union.append(l)

        if not lotes_union:
            return jsonify({'erro': 'Nenhum lote para agrupar'}), 400

        nova = RotaSalva(
            nome=(data.get('nome') or None),
            criado_por=getattr(current_user, 'id', None),
            lotes=lotes_union,
            status='salva',
        )
        db.session.add(nova)
        db.session.commit()
        return jsonify({'sucesso': True, 'id': nova.id, 'nome': nova.nome,
                        'total_lotes': len(lotes_union)})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao agrupar rotas: {e}")
        return jsonify({'erro': str(e)}), 500