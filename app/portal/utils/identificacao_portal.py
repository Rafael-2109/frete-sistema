"""
API para identificação de portal baseado em lote_id
"""

from flask import Blueprint, jsonify, request
from app import db
from app.separacao.models import Separacao
from app.portal.utils.grupo_empresarial import GrupoEmpresarial
import logging

logger = logging.getLogger(__name__)

identificacao_portal_bp = Blueprint('identificacao_portal', __name__)

@identificacao_portal_bp.route('/api/identificar-portal-por-lote', methods=['POST'])
def identificar_portal_por_lote():
    """
    Identifica qual portal usar baseado no lote_id
    
    Args (via JSON):
        lote_id: ID do lote de separação
        
    Returns:
        JSON com portal identificado e CNPJ
    """
    try:
        data = request.get_json()
        lote_id = data.get('lote_id')
        
        if not lote_id:
            return jsonify({
                'success': False,
                'message': 'lote_id é obrigatório'
            })
        
        # Buscar primeira separação do lote para obter CNPJ
        separacao = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).first()
        
        if not separacao:
            logger.warning(f"Lote {lote_id} não encontrado")
            return jsonify({
                'success': False,
                'message': f'Lote {lote_id} não encontrado'
            })
        
        cnpj_cpf = separacao.cnpj_cpf
        
        # Identificar portal usando GrupoEmpresarial
        portal = GrupoEmpresarial.identificar_portal(cnpj_cpf)
        
        # Se não identificou portal específico, usar 'atacadao' como padrão
        if not portal:
            logger.info(f"Portal não identificado para CNPJ {cnpj_cpf}, usando 'atacadao' como padrão")
            portal = 'atacadao'
        
        logger.info(f"Lote {lote_id} - CNPJ: {cnpj_cpf} - Portal: {portal}")
        
        return jsonify({
            'success': True,
            'lote_id': lote_id,
            'cnpj_cpf': cnpj_cpf,
            'portal': portal,
            'raz_social': separacao.raz_social_red
        })
        
    except Exception as e:
        logger.error(f"Erro ao identificar portal: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao identificar portal: {str(e)}'
        })

@identificacao_portal_bp.route('/api/obter-cnpj-por-lote/<lote_id>', methods=['GET'])
def obter_cnpj_por_lote(lote_id):
    """
    Endpoint GET simples para obter CNPJ por lote_id
    
    Args:
        lote_id: ID do lote (na URL)
        
    Returns:
        JSON com CNPJ
    """
    try:
        # Buscar primeira separação do lote
        separacao = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).first()
        
        if not separacao:
            return jsonify({
                'success': False,
                'message': f'Lote {lote_id} não encontrado'
            })
        
        return jsonify({
            'success': True,
            'lote_id': lote_id,
            'cnpj_cpf': separacao.cnpj_cpf,
            'raz_social': separacao.raz_social_red
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter CNPJ: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao obter CNPJ: {str(e)}'
        })