"""
API para confirmação de agendamento em Separações e Pré-Separações
"""

from flask import jsonify
from flask_login import login_required, current_user
from app import db
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/pre-separacao/<int:pre_sep_id>/confirmar-agendamento', methods=['POST'])
@login_required
def confirmar_agendamento_pre_separacao(pre_sep_id):
    """Confirmar agendamento de uma pré-separação"""
    try:
        pre_sep = PreSeparacaoItem.query.get_or_404(pre_sep_id)
        
        # Verificar se tem data de agendamento
        if not pre_sep.data_agendamento_editada:
            return jsonify({
                'success': False,
                'error': 'Pré-separação não possui data de agendamento'
            }), 400
        
        # Confirmar agendamento
        pre_sep.agendamento_confirmado = True
        db.session.commit()
        
        logger.info(f"Agendamento confirmado para pré-separação {pre_sep_id} por {current_user.nome}")
        
        return jsonify({
            'success': True,
            'message': 'Agendamento confirmado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao confirmar agendamento de pré-separação {pre_sep_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/pre-separacao/<int:pre_sep_id>/reverter-agendamento', methods=['POST'])
@login_required
def reverter_agendamento_pre_separacao(pre_sep_id):
    """Reverter confirmação de agendamento de uma pré-separação"""
    try:
        pre_sep = PreSeparacaoItem.query.get_or_404(pre_sep_id)
        
        # Reverter confirmação
        pre_sep.agendamento_confirmado = False
        db.session.commit()
        
        logger.info(f"Confirmação de agendamento revertida para pré-separação {pre_sep_id} por {current_user.nome}")
        
        return jsonify({
            'success': True,
            'message': 'Confirmação de agendamento revertida'
        })
        
    except Exception as e:
        logger.error(f"Erro ao reverter agendamento de pré-separação {pre_sep_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/separacao/<string:lote_id>/confirmar-agendamento', methods=['POST'])
@login_required
def confirmar_agendamento_separacao(lote_id):
    """Confirmar agendamento de todas as separações de um lote"""
    try:
        # Buscar todas as separações do lote
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        
        if not separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma separação encontrada para o lote {lote_id}'
            }), 404
        
        # Verificar se todas têm data de agendamento
        for sep in separacoes:
            if not sep.agendamento:
                return jsonify({
                    'success': False,
                    'error': 'Uma ou mais separações não possuem data de agendamento'
                }), 400
        
        # Confirmar agendamento de todas
        for sep in separacoes:
            sep.agendamento_confirmado = True
        
        db.session.commit()
        
        logger.info(f"Agendamento confirmado para lote {lote_id} ({len(separacoes)} itens) por {current_user.nome}")
        
        return jsonify({
            'success': True,
            'message': f'Agendamento confirmado para {len(separacoes)} itens'
        })
        
    except Exception as e:
        logger.error(f"Erro ao confirmar agendamento do lote {lote_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/separacao/<string:lote_id>/reverter-agendamento', methods=['POST'])
@login_required
def reverter_agendamento_separacao(lote_id):
    """Reverter confirmação de agendamento de todas as separações de um lote"""
    try:
        # Buscar todas as separações do lote
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        
        if not separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma separação encontrada para o lote {lote_id}'
            }), 404
        
        # Reverter confirmação de todas
        for sep in separacoes:
            sep.agendamento_confirmado = False
        
        db.session.commit()
        
        logger.info(f"Confirmação de agendamento revertida para lote {lote_id} ({len(separacoes)} itens) por {current_user.nome}")
        
        return jsonify({
            'success': True,
            'message': f'Confirmação revertida para {len(separacoes)} itens'
        })
        
    except Exception as e:
        logger.error(f"Erro ao reverter agendamento do lote {lote_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/pre-separacao/lote/<string:lote_id>/confirmar-agendamento', methods=['POST'])
@login_required
def confirmar_agendamento_lote_pre_separacao(lote_id):
    """Confirmar agendamento de todas as pré-separações de um lote"""
    try:
        # Buscar todas as pré-separações do lote
        pre_separacoes = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.separacao_lote_id == lote_id,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).all()
        
        if not pre_separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma pré-separação encontrada para o lote {lote_id}'
            }), 404
        
        # Verificar se todas têm data de agendamento
        for pre_sep in pre_separacoes:
            if not pre_sep.data_agendamento_editada:
                return jsonify({
                    'success': False,
                    'error': 'Uma ou mais pré-separações não possuem data de agendamento'
                }), 400
        
        # Confirmar agendamento de todas
        for pre_sep in pre_separacoes:
            pre_sep.agendamento_confirmado = True
        
        db.session.commit()
        
        logger.info(f"Agendamento confirmado para lote de pré-separação {lote_id} ({len(pre_separacoes)} itens) por {current_user.nome}")
        
        return jsonify({
            'success': True,
            'message': f'Agendamento confirmado para {len(pre_separacoes)} itens'
        })
        
    except Exception as e:
        logger.error(f"Erro ao confirmar agendamento do lote de pré-separação {lote_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route('/api/pre-separacao/lote/<string:lote_id>/reverter-agendamento', methods=['POST'])
@login_required
def reverter_agendamento_lote_pre_separacao(lote_id):
    """Reverter confirmação de agendamento de todas as pré-separações de um lote"""
    try:
        # Buscar todas as pré-separações do lote
        pre_separacoes = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.separacao_lote_id == lote_id,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).all()
        
        if not pre_separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma pré-separação encontrada para o lote {lote_id}'
            }), 404
        
        # Reverter confirmação de todas
        for pre_sep in pre_separacoes:
            pre_sep.agendamento_confirmado = False
        
        db.session.commit()
        
        logger.info(f"Confirmação de agendamento revertida para lote de pré-separação {lote_id} ({len(pre_separacoes)} itens) por {current_user.nome}")
        
        return jsonify({
            'success': True,
            'message': f'Confirmação revertida para {len(pre_separacoes)} itens'
        })
        
    except Exception as e:
        logger.error(f"Erro ao reverter agendamento do lote de pré-separação {lote_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500