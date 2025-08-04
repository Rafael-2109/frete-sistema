"""
API para atualização de notas fiscais em EmbarqueItem
"""
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required
from app.faturamento.services.atualizar_nf_embarque import (
    atualizar_nf_embarque_items_com_erro,
    atualizar_nf_embarque_item_especifico,
    buscar_preview_nf_pendentes,
    atualizar_nf_embarque_items_selecionados
)
import logging

logger = logging.getLogger(__name__)

atualizar_nf_bp = Blueprint('atualizar_nf', __name__, url_prefix='/faturamento')


@atualizar_nf_bp.route('/atualizar-nf-pendentes')
@login_required
def atualizar_nf_pendentes_view():
    """
    Renderiza a página de visualização e atualização de NFs pendentes
    """
    return render_template('faturamento/atualizar_nf_pendentes.html')


@atualizar_nf_bp.route('/api/preview-nf-pendentes', methods=['GET'])
@login_required
def api_preview_nf_pendentes():
    """
    API para buscar preview dos EmbarqueItems com NFs pendentes
    """
    try:
        preview_items = buscar_preview_nf_pendentes()
        
        return jsonify({
            'sucesso': True,
            'items': preview_items,
            'total': len(preview_items)
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao buscar preview: {str(e)}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@atualizar_nf_bp.route('/api/atualizar-nf-selecionados', methods=['POST'])
@login_required
def api_atualizar_nf_selecionados():
    """
    API para atualizar apenas os EmbarqueItems selecionados
    """
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])
        
        if not item_ids:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum item selecionado'
            }), 400
            
        resultado = atualizar_nf_embarque_items_selecionados(item_ids)
        
        return jsonify({
            'sucesso': True,
            'relatorio': resultado
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao atualizar itens selecionados: {str(e)}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@atualizar_nf_bp.route('/api/atualizar-nf-embarques', methods=['POST'])
@login_required
def atualizar_nf_embarques():
    """
    Atualiza notas fiscais de todos os EmbarqueItem com erro_validacao
    """
    try:
        logger.info("Iniciando atualização de NFs em EmbarqueItems com erro")
        
        resultado = atualizar_nf_embarque_items_com_erro()
        
        return jsonify({
            'sucesso': True,
            'relatorio': resultado
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao atualizar NFs: {str(e)}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@atualizar_nf_bp.route('/api/atualizar-nf-embarque/<int:embarque_item_id>', methods=['POST'])
@login_required
def atualizar_nf_embarque_especifico(embarque_item_id):
    """
    Atualiza nota fiscal de um EmbarqueItem específico
    """
    try:
        logger.info(f"Atualizando NF do EmbarqueItem {embarque_item_id}")
        
        resultado = atualizar_nf_embarque_item_especifico(embarque_item_id)
        
        if resultado['sucesso']:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Erro ao atualizar NF do item {embarque_item_id}: {str(e)}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@atualizar_nf_bp.route('/api/verificar-nf-pendentes', methods=['GET'])
@login_required
def verificar_nf_pendentes():
    """
    Verifica quantidade de EmbarqueItems com erro_validacao pendentes
    """
    try:
        from app.embarques.models import EmbarqueItem, Embarque
        from sqlalchemy import and_
        from app import db
        
        # Contar itens pendentes
        count = db.session.query(EmbarqueItem).join(
            Embarque, EmbarqueItem.embarque_id == Embarque.id
        ).filter(
            and_(
                EmbarqueItem.erro_validacao is not None,
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            )
        ).count()
        
        return jsonify({
            'sucesso': True,
            'total_pendentes': count
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao verificar NFs pendentes: {str(e)}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500