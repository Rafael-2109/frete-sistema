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
        # Buscar todas as separações do pedido
        separacoes = db.session.query(Separacao).filter(
            Separacao.num_pedido == num_pedido
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
            
            # Dados básicos da separação
            sep_data = {
                'separacao_lote_id': sep.separacao_lote_id,
                'num_pedido': sep.num_pedido,
                'expedicao': sep.expedicao.isoformat() if sep.expedicao else None,
                'agendamento': sep.agendamento.isoformat() if sep.agendamento else None,
                'protocolo': sep.protocolo,
                'status': pedido.status if pedido else 'ABERTO',
                'valor_total': float(sep.valor_saldo or 0),
                'peso_total': float(sep.peso or 0),
                'pallet_total': float(sep.pallet or 0),
                'produtos': []
            }
            
            # Buscar produtos da separação
            produtos = db.session.query(Separacao).filter(
                and_(
                    Separacao.separacao_lote_id == sep.separacao_lote_id,
                    Separacao.num_pedido == num_pedido
                )
            ).all()
            
            for prod in produtos:
                sep_data['produtos'].append({
                    'cod_produto': prod.cod_produto,
                    'nome_produto': prod.nome_produto,
                    'qtd_saldo': float(prod.qtd_saldo or 0),
                    'valor_saldo': float(prod.valor_saldo or 0),
                    'peso': float(prod.peso or 0),
                    'pallet': float(prod.pallet or 0)
                })
            
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
                                transportadora = transp.nome
                        
                        sep_data['embarque'] = {
                            'numero': embarque.numero,
                            'transportadora': transportadora,
                            'data_prevista_embarque': embarque.data_prevista_embarque.isoformat() if embarque.data_prevista_embarque else None
                        }
            
            separacoes_data.append(sep_data)
        
        # Calcular totais (considerando que produtos podem estar duplicados)
        totais_unicos = {}
        for sep in separacoes_data:
            if sep['separacao_lote_id'] not in totais_unicos:
                totais_unicos[sep['separacao_lote_id']] = {
                    'valor': sep['valor_total'],
                    'peso': sep['peso_total'],
                    'pallet': sep['pallet_total']
                }
        
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