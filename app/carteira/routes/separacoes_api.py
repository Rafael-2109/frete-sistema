"""
API para buscar separações completas com informações de embarque
"""

from flask import jsonify
from flask_login import login_required
from app import db
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem
from app.transportadoras.models import Transportadora
from sqlalchemy import and_
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pedido/<num_pedido>/separacoes-completas', methods=['GET'])
@login_required
def obter_separacoes_completas(num_pedido):
    """
    Retorna todas as separações de um pedido com informações completas,
    incluindo dados de embarque quando status = COTADO
    """
    try:
        # Buscar apenas separações com status ABERTO ou COTADO (não FATURADO)
        separacoes = db.session.query(Separacao).join(
            Pedido,
            and_(
                Separacao.num_pedido == Pedido.num_pedido,
                Separacao.separacao_lote_id == Pedido.separacao_lote_id
            )
        ).filter(
            Separacao.num_pedido == num_pedido,
            Pedido.status.in_(['ABERTO', 'COTADO'])  # Excluir FATURADO
        ).order_by(Separacao.criado_em.desc()).all()
        
        separacoes_data = []
        
        for sep in separacoes:
            # Buscar o status do pedido associado
            pedido = db.session.query(Pedido).filter(
                and_(
                    Pedido.num_pedido == sep.num_pedido,
                    Pedido.separacao_lote_id == sep.separacao_lote_id
                )
            ).first()
            
            # Buscar produtos da separação
            produtos = db.session.query(Separacao).filter(
                and_(
                    Separacao.separacao_lote_id == sep.separacao_lote_id,
                    Separacao.num_pedido == num_pedido
                )
            ).all()
            
            # Calcular totais somando todos os produtos
            valor_total = 0
            peso_total = 0
            pallet_total = 0
            
            produtos_data = []
            for prod in produtos:
                valor_total += float(prod.valor_saldo or 0)
                peso_total += float(prod.peso or 0)
                pallet_total += float(prod.pallet or 0)
                
                produtos_data.append({
                    'cod_produto': prod.cod_produto,
                    'nome_produto': prod.nome_produto,
                    'qtd_saldo': float(prod.qtd_saldo or 0),
                    'valor_saldo': float(prod.valor_saldo or 0),
                    'peso': float(prod.peso or 0),
                    'pallet': float(prod.pallet or 0)
                })
            
            # Protocolo já vem direto da Separacao
            # Não precisa buscar de outra tabela!
            
            # Dados básicos da separação com totais corretos
            sep_data = {
                'separacao_lote_id': sep.separacao_lote_id,
                'num_pedido': sep.num_pedido,
                'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                'agendamento': sep.agendamento.isoformat() if sep.agendamento else None,
                'protocolo': sep.protocolo,
                'agendamento_confirmado': sep.agendamento_confirmado if hasattr(sep, 'agendamento_confirmado') else False,
                'status': pedido.status if pedido else 'ABERTO',
                'valor_total': valor_total,
                'peso_total': peso_total,
                'pallet_total': pallet_total,
                'produtos': produtos_data
            }
            
            # Se status for COTADO, buscar informações do embarque
            if pedido and pedido.status == 'COTADO':
                # Buscar item de embarque
                embarque_item = db.session.query(EmbarqueItem).filter(
                    EmbarqueItem.separacao_lote_id == sep.separacao_lote_id
                ).first()
                
                if embarque_item:
                    # Buscar embarque
                    embarque = db.session.query(Embarque).filter(
                        Embarque.id == embarque_item.embarque_id
                    ).first()
                    
                    if embarque:
                        # Buscar transportadora
                        transportadora = None
                        if embarque.transportadora_id:
                            transp = db.session.query(Transportadora).filter(
                                Transportadora.id == embarque.transportadora_id
                            ).first()
                            if transp:
                                transportadora = transp.razao_social
                        
                        sep_data['embarque'] = {
                            'numero': embarque.numero,
                            'transportadora': transportadora,
                            'data_prevista_embarque': embarque.data_prevista_embarque.isoformat() if embarque.data_prevista_embarque else None
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
        
        # Se tem confirmação e data, atualizar separação
        if resultado.get('success') and lote_id and resultado.get('agendamento_confirmado') and resultado.get('data_aprovada'):
            try:
                from datetime import datetime
                separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
                for sep in separacoes:
                    sep.agendamento_confirmado = True
                    sep.agendamento = datetime.strptime(resultado['data_aprovada'], '%Y-%m-%d').date()
                db.session.commit()
                logger.info(f"Separação atualizada com confirmação do agendamento")
            except Exception as e:
                logger.error(f"Erro ao atualizar separação: {e}")
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
        
        for sep in separacoes:
            if agendamento:
                # Converter string para date se necessário
                if isinstance(agendamento, str):
                    sep.agendamento = datetime.strptime(agendamento, '%Y-%m-%d').date()
                else:
                    sep.agendamento = agendamento
            sep.agendamento_confirmado = agendamento_confirmado
        
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