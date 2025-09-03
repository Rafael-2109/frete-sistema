"""
API para buscar separações completas com informações de embarque
"""

from flask import jsonify, request
from flask_login import login_required
from app import db
from app.separacao.models import Separacao
from app.embarques.models import Embarque, EmbarqueItem
from app.transportadoras.models import Transportadora
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/separacoes-completas', methods=['GET'])
@login_required
def obter_separacoes_completas(num_pedido):
    """
    API UNIFICADA: Retorna TODAS as separações de um pedido (incluindo PREVISAO),
    com informações completas, cálculos de peso/pallet e dados de embarque.
    Substitui a necessidade de múltiplas APIs.
    """
    try:
        # QUERY ÚNICA: Buscar TODAS as separações (incluindo PREVISAO)
        # Incluindo apenas não faturadas (sincronizado_nf=False)
        todas_separacoes = db.session.query(Separacao).filter(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf == False  # Apenas não faturadas
            # REMOVIDO filtro de status != 'PREVISAO' - agora retorna TUDO
        ).order_by(
            Separacao.separacao_lote_id,
            Separacao.criado_em.desc()
        ).all()
        
        if not todas_separacoes:
            return jsonify({
                'success': True,
                'separacoes': [],
                'total_separacoes': 0
            })
        
        # Coletar lote_ids únicos e determinar status por lote
        lotes_info = {}
        for sep in todas_separacoes:
            lote_id = sep.separacao_lote_id
            if lote_id not in lotes_info:
                lotes_info[lote_id] = {
                    'status': sep.status,  # Status vem direto da Separacao
                    'primeira_sep': sep
                }
        
        # QUERY OTIMIZADA 2: Buscar embarques para lotes COTADOS ou FATURADOS
        embarques_dict = {}
        lotes_cotados = [lote_id for lote_id, info in lotes_info.items() 
                        if info['status'] in ['COTADO', 'FATURADO']]
        
        if lotes_cotados:
            embarques = db.session.query(
                EmbarqueItem,
                Embarque,
                Transportadora
            ).join(
                Embarque,
                EmbarqueItem.embarque_id == Embarque.id
            ).outerjoin(
                Transportadora,
                Embarque.transportadora_id == Transportadora.id
            ).filter(
                EmbarqueItem.separacao_lote_id.in_(lotes_cotados),
                EmbarqueItem.status == 'ativo'
            ).all()
            
            for item, embarque, transportadora in embarques:
                embarques_dict[item.separacao_lote_id] = {
                    'item': item,
                    'embarque': embarque,
                    'transportadora': transportadora
                }
        
        # Agrupar separações por lote_id
        separacoes_por_lote = {}
        for sep in todas_separacoes:
            lote_id = sep.separacao_lote_id
            
            # Processar todas as separações (sem verificar Pedido)
            
            if lote_id not in separacoes_por_lote:
                separacoes_por_lote[lote_id] = {
                    'produtos': [],
                    'valor_total': 0,
                    'peso_total': 0,
                    'pallet_total': 0,
                    'primeira_sep': sep  # Guardar primeira separação para dados gerais
                }
            
            # Adicionar produto
            separacoes_por_lote[lote_id]['produtos'].append({
                'cod_produto': sep.cod_produto,
                'nome_produto': sep.nome_produto,
                'qtd_saldo': float(sep.qtd_saldo or 0),
                'valor_saldo': float(sep.valor_saldo or 0),
                'peso': float(sep.peso or 0),
                'pallet': float(sep.pallet or 0)
            })
            
            # Somar totais
            separacoes_por_lote[lote_id]['valor_total'] += float(sep.valor_saldo or 0)
            separacoes_por_lote[lote_id]['peso_total'] += float(sep.peso or 0)
            separacoes_por_lote[lote_id]['pallet_total'] += float(sep.pallet or 0)
        
        # Montar resposta final
        separacoes_data = []
        for lote_id, dados in separacoes_por_lote.items():
            sep = dados['primeira_sep']
            info_lote = lotes_info.get(lote_id, {})
            
            # Dados básicos da separação com totais corretos
            sep_data = {
                'separacao_lote_id': lote_id,
                'num_pedido': sep.num_pedido,
                'expedicao': sep.expedicao.strftime('%Y-%m-%d') if sep.expedicao else None,
                'agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None,
                'protocolo': sep.protocolo,
                'agendamento_confirmado': sep.agendamento_confirmado if hasattr(sep, 'agendamento_confirmado') else False,
                'status': info_lote.get('status', sep.status),  # Status vem da Separacao
                'valor_total': dados['valor_total'],
                'peso_total': dados['peso_total'],
                'pallet_total': dados['pallet_total'],
                'produtos': dados['produtos']
            }
            
            # Se status for COTADO ou FATURADO, adicionar informações do embarque
            if info_lote.get('status') in ['COTADO', 'FATURADO'] and lote_id in embarques_dict:
                embarque_info = embarques_dict[lote_id]
                embarque = embarque_info['embarque']
                transportadora = embarque_info['transportadora']
                
                # Dados do embarque já foram buscados na query otimizada
                sep_data['embarque'] = {
                    'numero': embarque.numero,
                    'transportadora': transportadora.razao_social if transportadora else None,
                    'data_prevista_embarque': embarque.data_prevista_embarque.strftime('%Y-%m-%d') if embarque.data_prevista_embarque else None
                }
            
            separacoes_data.append(sep_data)
        
        # Limpar duplicatas - agrupar por separacao_lote_id
        separacoes_unicas = {}
        for sep in separacoes_data:
            lote_id = sep['separacao_lote_id']
            if lote_id not in separacoes_unicas:
                separacoes_unicas[lote_id] = sep
        
        return jsonify({
            'success': True,
            'separacoes': list(separacoes_unicas.values()),
            'total_separacoes': len(separacoes_unicas)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar separações completas: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/separacoes-compactas-lote', methods=['POST'])
@login_required
def obter_separacoes_compactas_lote():
    """
    API otimizada para buscar separações de múltiplos pedidos em lote
    Retorna apenas dados essenciais para o contador de protocolos
    
    Payload esperado:
    {
        "pedidos": ["00001", "00002", "00003", ...],
        "limite": 100  // opcional, default 100
    }
    """
    try:
        data = request.get_json()
        pedidos = data.get('pedidos', [])
        limite = min(data.get('limite', 100), 500)  # Máximo 500 pedidos por vez
        
        if not pedidos:
            return jsonify({
                'success': False,
                'error': 'Nenhum pedido fornecido'
            }), 400
        
        # Limitar quantidade de pedidos
        pedidos = pedidos[:limite]
        
        logger.info(f"Buscando separações em lote para {len(pedidos)} pedidos")
        
        # Query otimizada: buscar todas as separações de uma vez
        # Filtrar apenas não faturadas (sincronizado_nf=False)
        separacoes = db.session.query(
            Separacao.num_pedido,
            Separacao.separacao_lote_id,
            Separacao.expedicao,
            Separacao.protocolo,
            Separacao.agendamento,
            Separacao.agendamento_confirmado,
            Separacao.status,
            Separacao.tipo_envio,
            Separacao.valor_saldo,
            Separacao.peso,
            Separacao.pallet
        ).filter(
            Separacao.num_pedido.in_(pedidos),
            Separacao.sincronizado_nf == False  # Apenas não faturadas
        ).all()
        
        # Agrupar por pedido E por lote_id (para mostrar apenas um registro por lote)
        separacoes_por_pedido = {}
        lotes_processados = {}  # Para agrupar por lote_id
        
        for sep in separacoes:
            num_pedido = sep.num_pedido
            lote_id = sep.separacao_lote_id
            
            if num_pedido not in separacoes_por_pedido:
                separacoes_por_pedido[num_pedido] = []
            
            # Chave única para o lote
            chave_lote = f"{num_pedido}_{lote_id}"
            
            # Se já processamos este lote, apenas somar valores
            if chave_lote in lotes_processados:
                lotes_processados[chave_lote]['valor'] += float(sep.valor_saldo or 0)
                lotes_processados[chave_lote]['peso'] += float(sep.peso or 0)
                lotes_processados[chave_lote]['pallet'] += float(sep.pallet or 0)
            else:
                # Criar novo registro para o lote
                lote_data = {
                    'tipo': 'separacao',
                    'lote_id': lote_id,
                    'protocolo': sep.protocolo,
                    'expedicao': sep.expedicao.strftime('%Y-%m-%d') if sep.expedicao else None,
                    'agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None,
                    'agendamento_confirmado': sep.agendamento_confirmado or False,
                    'status': sep.status,
                    'tipo_envio': sep.tipo_envio,
                    'valor': float(sep.valor_saldo or 0),
                    'peso': float(sep.peso or 0),
                    'pallet': float(sep.pallet or 0)
                }
                lotes_processados[chave_lote] = lote_data
                separacoes_por_pedido[num_pedido].append(lote_data)
        
        # Contar totais
        total_pedidos = len(separacoes_por_pedido)
        total_separacoes = len(separacoes)
        
        # Contar protocolos únicos
        protocolos_unicos = set()
        for seps in separacoes_por_pedido.values():
            for sep in seps:
                if sep['protocolo'] and not sep['agendamento_confirmado']:
                    protocolos_unicos.add(sep['protocolo'])
        
        logger.info(f"Retornando {total_separacoes} separações de {total_pedidos} pedidos")
        
        # LOG DE DEBUG: Verificar estrutura antes de enviar
        if separacoes_por_pedido:
            primeiro_pedido = list(separacoes_por_pedido.keys())[0] if separacoes_por_pedido else None
            if primeiro_pedido and separacoes_por_pedido[primeiro_pedido]:
                primeira_sep = separacoes_por_pedido[primeiro_pedido][0]
                logger.info(f"DEBUG - Exemplo de separação sendo enviada: {primeira_sep}")
                logger.info(f"DEBUG - Campos expedição e agendamento: expedicao={primeira_sep.get('expedicao')}, agendamento={primeira_sep.get('agendamento')}")
        
        return jsonify({
            'success': True,
            'pedidos': separacoes_por_pedido,
            'totais': {
                'pedidos_com_separacao': total_pedidos,
                'total_separacoes': total_separacoes,
                'protocolos_unicos_pendentes': len(protocolos_unicos)
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar separações em lote: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/verificar-protocolo-portal', methods=['POST'])
@login_required
def verificar_protocolo_portal():
    """
    Rota proxy para verificar protocolo no portal
    Redireciona para o módulo portal/atacadao
    """
    from flask import request
    from app.portal.atacadao.verificacao_protocolo import VerificadorProtocoloAtacadao
    
    try:
        data = request.get_json()
        lote_id = data.get('lote_id')
        protocolo = data.get('protocolo')
        
        if not protocolo:
            return jsonify({
                'success': False,
                'message': 'Protocolo é obrigatório'
            })
        
        logger.info(f"Verificando protocolo {protocolo} via carteira API")
        
        # Usar a classe verificadora
        verificador = VerificadorProtocoloAtacadao()
        resultado = verificador.verificar_protocolo_completo(protocolo, lote_id)
        
        # Se tem confirmação e data, atualizar separação e pedido
        if resultado.get('success') and lote_id and resultado.get('agendamento_confirmado') and resultado.get('data_aprovada'):
            try:
                from datetime import datetime
                
                separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
                for sep in separacoes:
                    sep.agendamento_confirmado = True
                    sep.agendamento = datetime.strptime(resultado['data_aprovada'], '%Y-%m-%d').date()
                
                # Não precisa atualizar Pedido pois é uma VIEW das Separações
                logger.info(f"Separações do lote {lote_id} atualizadas com confirmação do agendamento")
                
                db.session.commit()
                logger.info(f"Separações atualizadas com confirmação do agendamento")
            except Exception as e:
                logger.error(f"Erro ao atualizar separação/pedido: {e}")
                db.session.rollback()
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Erro na verificação de protocolo: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao verificar protocolo: {str(e)}'
        }), 500


@carteira_bp.route('/api/atualizar-status-separacao', methods=['POST'])
@login_required
def atualizar_status_separacao():
    """
    Atualiza status da separação com dados do portal
    """
    from flask import request
    from datetime import datetime
    
    try:
        data = request.get_json()
        lote_id = data.get('lote_id')
        agendamento = data.get('agendamento')
        agendamento_confirmado = data.get('agendamento_confirmado', False)
        
        if not lote_id:
            return jsonify({
                'success': False,
                'message': 'Lote ID é obrigatório'
            })
        
        # Buscar e atualizar separações
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        if not separacoes:
            return jsonify({
                'success': False,
                'message': 'Separação não encontrada'
            })
        
        # Converter data de agendamento uma vez
        data_agendamento = None
        if agendamento:
            if isinstance(agendamento, str):
                data_agendamento = datetime.strptime(agendamento, '%Y-%m-%d').date()
            else:
                data_agendamento = agendamento
        
        # Atualizar separações
        for sep in separacoes:
            if data_agendamento:
                sep.agendamento = data_agendamento
            sep.agendamento_confirmado = agendamento_confirmado
        
        # Não precisa atualizar Pedido pois é uma VIEW das Separações
        logger.info(f"Separações do lote {lote_id} atualizadas")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar status: {str(e)}'
        }), 500