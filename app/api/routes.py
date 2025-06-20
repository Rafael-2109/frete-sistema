from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import tempfile
import pandas as pd
import os

from . import api_bp
from .cors import cors_enabled
from app import db
from app.pedidos.models import Pedido
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.embarques.models import Embarque
from app.fretes.models import Frete
from app.portaria.models import ControlePortaria
from app.transportadoras.models import Transportadora
from sqlalchemy import and_, desc, func

# ============================================================================
# ENDPOINTS DA API MCP
# ============================================================================

@api_bp.route('/embarques', methods=['GET'])
@login_required
def api_consultar_embarques():
    """Consulta embarques via API REST"""
    try:
        status = request.args.get('status', 'ativo')
        limite = int(request.args.get('limite', 10))
        
        query = Embarque.query
        if status:
            query = query.filter(Embarque.status == status)
        
        embarques = query.order_by(Embarque.id.desc()).limit(limite).all()
        
        resultado = []
        for embarque in embarques:
            resultado.append({
                'id': embarque.id,
                'numero': embarque.numero,
                'status': embarque.status,
                'data_embarque': embarque.data_embarque.isoformat() if embarque.data_embarque else None,
                'transportadora': embarque.transportadora.nome if embarque.transportadora else None,
                'total_fretes': len(embarque.fretes) if embarque.fretes else 0
            })
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': len(resultado),
            'usuario': current_user.username,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/fretes', methods=['GET'])
@login_required
def api_consultar_fretes():
    """Consulta fretes via API REST"""
    try:
        status_aprovacao = request.args.get('status_aprovacao', 'pendente')
        limite = int(request.args.get('limite', 10))
        
        query = Frete.query
        if status_aprovacao:
            query = query.filter(Frete.status_aprovacao == status_aprovacao)
        
        fretes = query.order_by(Frete.id.desc()).limit(limite).all()
        
        resultado = []
        for frete in fretes:
            resultado.append({
                'id': frete.id,
                'embarque_numero': frete.embarque.numero if frete.embarque else None,
                'transportadora': frete.transportadora.nome if frete.transportadora else None,
                'valor_cotado': float(frete.valor_cotado) if frete.valor_cotado else None,
                'status_aprovacao': frete.status_aprovacao,
                'tem_cte': bool(frete.numero_cte)
            })
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': len(resultado),
            'usuario': current_user.username,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/monitoramento', methods=['GET'])
@login_required
def api_consultar_monitoramento():
    """Consulta entregas em monitoramento via API REST"""
    try:
        nf_numero = request.args.get('nf_numero')
        pendencia_financeira = request.args.get('pendencia_financeira')
        limite = int(request.args.get('limite', 10))
        
        query = EntregaMonitorada.query
        
        if nf_numero:
            query = query.filter(EntregaMonitorada.numero_nf == nf_numero)
        
        if pendencia_financeira is not None:
            pendencia_bool = pendencia_financeira.lower() == 'true'
            query = query.filter(EntregaMonitorada.pendencia_financeira == pendencia_bool)
        
        entregas = query.order_by(EntregaMonitorada.id.desc()).limit(limite).all()
        
        resultado = []
        for entrega in entregas:
            resultado.append({
                'id': entrega.id,
                'numero_nf': entrega.numero_nf,
                'status': entrega.status_finalizacao,
                'cliente': entrega.cliente,
                'municipio': entrega.municipio,
                'uf': entrega.uf,
                'pendencia_financeira': entrega.pendencia_financeira,
                'valor_nf': float(entrega.valor_nf) if entrega.valor_nf else None,
                'data_faturamento': entrega.data_faturamento.isoformat() if entrega.data_faturamento else None,
                'data_embarque': entrega.data_embarque.isoformat() if entrega.data_embarque else None
            })
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': len(resultado),
            'usuario': current_user.username,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cliente/<cliente_nome>', methods=['GET'])
@login_required
def api_consultar_cliente_detalhado(cliente_nome):
    """Consulta detalhada por cliente via API REST"""
    try:
        uf_filtro = request.args.get('uf', '').strip().upper()
        limite = int(request.args.get('limite', 5))
        
        # Buscar pedidos do cliente
        query = Pedido.query.filter(
            Pedido.raz_social_red.ilike(f"%{cliente_nome}%")
        )
        
        if uf_filtro:
            query = query.filter(Pedido.cod_uf == uf_filtro)
        
        pedidos = query.order_by(desc(Pedido.data_pedido)).limit(limite).all()
        
        if not pedidos:
            return jsonify({
                'success': False,
                'error': f'Nenhum pedido encontrado para {cliente_nome}' + (f' em {uf_filtro}' if uf_filtro else '')
            }), 404
        
        resultado = []
        
        for pedido in pedidos:
            item_pedido = {
                'pedido': {
                    'numero': pedido.num_pedido,
                    'data': pedido.data_pedido.strftime('%d/%m/%Y') if pedido.data_pedido else '',
                    'cliente': pedido.raz_social_red,
                    'destino': f"{pedido.nome_cidade}/{pedido.cod_uf}",
                    'valor': pedido.valor_saldo_total,
                    'status': pedido.status_calculado,
                    'nf': pedido.nf or ''
                },
                'faturamento': None,
                'monitoramento': None
            }
            
            # Buscar faturamento se tem NF
            if pedido.nf and pedido.nf.strip():
                faturamento = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=pedido.nf
                ).first()
                
                if faturamento:
                    saldo_carteira = 0
                    if pedido.valor_saldo_total and faturamento.valor_total:
                        saldo_carteira = pedido.valor_saldo_total - faturamento.valor_total
                    
                    item_pedido['faturamento'] = {
                        'data_fatura': faturamento.data_fatura.strftime('%d/%m/%Y') if faturamento.data_fatura else '',
                        'valor_nf': faturamento.valor_total,
                        'saldo_carteira': saldo_carteira,
                        'status_faturamento': 'Parcial' if saldo_carteira > 0 else 'Completo'
                    }
                
                # Buscar monitoramento
                entrega = EntregaMonitorada.query.filter_by(
                    numero_nf=pedido.nf
                ).first()
                
                if entrega:
                    item_pedido['monitoramento'] = {
                        'status_entrega': entrega.status_finalizacao or 'Em andamento',
                        'transportadora': entrega.transportadora,
                        'pendencia_financeira': entrega.pendencia_financeira,
                        'data_prevista': entrega.data_entrega_prevista.strftime('%d/%m/%Y') if entrega.data_entrega_prevista else None
                    }
            
            resultado.append(item_pedido)
        
        # Resumo
        total_valor = sum(p.valor_saldo_total for p in pedidos if p.valor_saldo_total)
        pedidos_faturados = sum(1 for p in pedidos if p.nf and p.nf.strip())
        
        return jsonify({
            'success': True,
            'cliente': cliente_nome.upper(),
            'uf': uf_filtro or 'Todas',
            'resumo': {
                'total_pedidos': len(pedidos),
                'valor_total': total_valor,
                'pedidos_faturados': pedidos_faturados,
                'percentual_faturado': round((pedidos_faturados/len(pedidos)*100), 1) if pedidos else 0
            },
            'data': resultado,
            'usuario': current_user.username,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cliente/<cliente_nome>/excel', methods=['GET'])
@login_required
def api_exportar_relatorio_cliente(cliente_nome):
    """Gera e baixa relatório Excel por cliente via API REST"""
    try:
        uf_filtro = request.args.get('uf', '').strip().upper()
        limite = int(request.args.get('limite', 10))
        
        # Reutilizar lógica similar ao MCP
        query = Pedido.query.filter(
            Pedido.raz_social_red.ilike(f"%{cliente_nome}%")
        )
        
        if uf_filtro:
            query = query.filter(Pedido.cod_uf == uf_filtro)
        
        pedidos = query.order_by(desc(Pedido.data_pedido)).limit(limite).all()
        
        if not pedidos:
            return jsonify({
                'success': False,
                'error': f'Nenhum pedido encontrado para {cliente_nome}'
            }), 404
        
        # Preparar dados para Excel (versão simplificada)
        dados_resumo = []
        for pedido in pedidos:
            dados_resumo.append({
                'Pedido': pedido.num_pedido,
                'Data': pedido.data_pedido.strftime('%d/%m/%Y') if pedido.data_pedido else '',
                'Cliente': pedido.raz_social_red,
                'Destino': f"{pedido.nome_cidade}/{pedido.cod_uf}",
                'Valor': pedido.valor_saldo_total,
                'Status': pedido.status_calculado,
                'NF': pedido.nf or '',
                'Transportadora': pedido.transportadora or ''
            })
        
        # Criar Excel
        df = pd.DataFrame(dados_resumo)
        
        # Arquivo temporário
        arquivo_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        df.to_excel(arquivo_temp.name, index=False, engine='xlsxwriter')
        arquivo_temp.close()
        
        # Nome do arquivo para download
        nome_arquivo = f"relatorio_{cliente_nome.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        return send_file(
            arquivo_temp.name,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/estatisticas', methods=['GET'])
@login_required
def api_estatisticas_sistema():
    """Estatísticas do sistema via API REST"""
    try:
        periodo_dias = int(request.args.get('periodo_dias', 30))
        data_inicio = datetime.now() - timedelta(days=periodo_dias)
        
        # Estatísticas básicas
        total_embarques = Embarque.query.count()
        embarques_ativos = Embarque.query.filter(Embarque.status == 'ativo').count()
        
        total_fretes = Frete.query.count()
        fretes_pendentes = Frete.query.filter(Frete.status_aprovacao == 'pendente').count()
        fretes_aprovados = Frete.query.filter(Frete.status_aprovacao == 'aprovado').count()
        
        total_entregas = EntregaMonitorada.query.count()
        entregas_entregues = EntregaMonitorada.query.filter(
            EntregaMonitorada.status_finalizacao == 'Entregue'
        ).count()
        
        pendencias_financeiras = EntregaMonitorada.query.filter(
            EntregaMonitorada.pendencia_financeira == True
        ).count()
        
        total_transportadoras = Transportadora.query.count()
        transportadoras_ativas = Transportadora.query.filter(
            Transportadora.ativa == True
        ).count()
        
        resultado = {
            'periodo_analisado': f'Últimos {periodo_dias} dias',
            'embarques': {
                'total': total_embarques,
                'ativos': embarques_ativos,
                'cancelados': total_embarques - embarques_ativos
            },
            'fretes': {
                'total': total_fretes,
                'pendentes_aprovacao': fretes_pendentes,
                'aprovados': fretes_aprovados,
                'percentual_aprovacao': round((fretes_aprovados / total_fretes * 100), 1) if total_fretes > 0 else 0
            },
            'entregas': {
                'total_monitoradas': total_entregas,
                'entregues': entregas_entregues,
                'pendencias_financeiras': pendencias_financeiras,
                'percentual_entrega': round((entregas_entregues / total_entregas * 100), 1) if total_entregas > 0 else 0
            },
            'transportadoras': {
                'total': total_transportadoras,
                'ativas': transportadoras_ativas
            }
        }
        
        return jsonify({
            'success': True,
            'data': resultado,
            'usuario': current_user.username,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/portaria', methods=['GET'])
@login_required
def api_consultar_portaria():
    """Consulta portaria via API REST"""
    try:
        status = request.args.get('status')
        limite = int(request.args.get('limite', 10))
        
        query = ControlePortaria.query
        if status:
            query = query.filter(ControlePortaria.status == status)
        
        registros = query.order_by(ControlePortaria.data_chegada.desc()).limit(limite).all()
        
        resultado = []
        for registro in registros:
            resultado.append({
                'id': registro.id,
                'placa': registro.placa,
                'status': registro.status,
                'data_chegada': registro.data_chegada.isoformat() if registro.data_chegada else None,
                'tipo_carga': registro.tipo_carga,
                'motorista': registro.motorista.nome if registro.motorista else None
            })
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': len(resultado),
            'usuario': current_user.username,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# ENDPOINT DE SAÚDE E DOCUMENTAÇÃO
# ============================================================================

@api_bp.route('/health', methods=['GET'])
@cors_enabled
def api_health():
    """Endpoint de saúde da API"""
    return jsonify({
        'status': 'healthy',
        'service': 'Sistema de Fretes API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            '/api/v1/embarques',
            '/api/v1/fretes', 
            '/api/v1/monitoramento',
            '/api/v1/cliente/<nome>',
            '/api/v1/cliente/<nome>/excel',
            '/api/v1/estatisticas',
            '/api/v1/portaria'
        ]
    })

@api_bp.route('/docs', methods=['GET'])
@cors_enabled
def api_docs():
    """Documentação da API"""
    docs = {
        'title': 'Sistema de Fretes API',
        'version': '1.0.0',
        'description': 'API REST para consultas do sistema de fretes via MCP',
        'base_url': request.host_url + 'api/v1',
        'authentication': 'Login required for all endpoints except /health and /docs',
        'endpoints': {
            'GET /embarques': {
                'description': 'Lista embarques',
                'parameters': {
                    'status': 'Status do embarque (ativo, cancelado)',
                    'limite': 'Limite de resultados (default: 10)'
                }
            },
            'GET /fretes': {
                'description': 'Lista fretes',
                'parameters': {
                    'status_aprovacao': 'Status da aprovação',
                    'limite': 'Limite de resultados (default: 10)'
                }
            },
            'GET /monitoramento': {
                'description': 'Lista entregas monitoradas',
                'parameters': {
                    'nf_numero': 'Número da NF',
                    'pendencia_financeira': 'true/false',
                    'limite': 'Limite de resultados (default: 10)'
                }
            },
            'GET /cliente/<nome>': {
                'description': 'Consulta detalhada por cliente',
                'parameters': {
                    'uf': 'UF para filtrar',
                    'limite': 'Limite de pedidos (default: 5)'
                }
            },
            'GET /cliente/<nome>/excel': {
                'description': 'Gera e baixa Excel do cliente',
                'parameters': {
                    'uf': 'UF para filtrar',
                    'limite': 'Limite de pedidos (default: 10)'
                }
            },
            'GET /estatisticas': {
                'description': 'Estatísticas do sistema',
                'parameters': {
                    'periodo_dias': 'Período em dias (default: 30)'
                }
            },
            'GET /portaria': {
                'description': 'Consulta portaria',
                'parameters': {
                    'status': 'Status na portaria',
                    'limite': 'Limite de resultados (default: 10)'
                }
            }
        },
        'examples': {
            'consultar_cliente': f"{request.host_url}api/v1/cliente/Assai?uf=SP&limite=5",
            'download_excel': f"{request.host_url}api/v1/cliente/Carrefour/excel?uf=RJ",
            'estatisticas': f"{request.host_url}api/v1/estatisticas?periodo_dias=30"
        }
    }
    
    return jsonify(docs) 