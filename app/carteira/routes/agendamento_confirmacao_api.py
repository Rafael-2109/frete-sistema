"""
API simplificada para confirmação de agendamento em Separações
Funciona para qualquer status
✅ ATUALIZADO: Sincroniza com EmbarqueItem (se existir) via SincronizadorAgendamentoService
"""

from flask import jsonify
from flask_login import login_required, current_user
from app import db
from app.separacao.models import Separacao
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route('/api/separacao/<string:lote_id>/confirmar-agendamento', methods=['POST'])
@login_required
def confirmar_agendamento_separacao(lote_id):
    """Confirmar agendamento. Suporta Nacom (Separacao) e CarVia (CarviaCotacao)."""
    try:
        # ===== CarVia =====
        if str(lote_id).startswith('CARVIA-'):
            return _toggle_agendamento_carvia(lote_id, confirmar=True)

        # ===== Nacom: fluxo original =====
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma separação encontrada para o lote {lote_id}'
            }), 404

        # Verificar se todas têm data de agendamento
        sem_agendamento = [s for s in separacoes if not s.agendamento]
        if sem_agendamento:
            return jsonify({
                'success': False,
                'error': f'{len(sem_agendamento)} de {len(separacoes)} itens não possuem data de agendamento'
            }), 400

        # Confirmar agendamento de todas
        for sep in separacoes:
            sep.agendamento_confirmado = True

        db.session.commit()

        logger.info(f"Agendamento confirmado para lote {lote_id} ({len(separacoes)} itens) por {current_user.nome}")

        # ✅ SINCRONIZAR com EmbarqueItem (se existir)
        tabelas_sincronizadas = []
        try:
            from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

            sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
            resultado_sync = sincronizador.sincronizar_desde_separacao(
                separacao_lote_id=lote_id,
                criar_agendamento=False  # Não criar AgendamentoEntrega pois pode não existir EntregaMonitorada
            )

            if resultado_sync['success']:
                tabelas_sincronizadas = resultado_sync.get('tabelas_atualizadas', [])
                if tabelas_sincronizadas:
                    logger.info(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(tabelas_sincronizadas)}")
        except Exception as sync_error:
            logger.warning(f"Aviso na sincronização: {sync_error}")

        return jsonify({
            'success': True,
            'message': f'Agendamento confirmado para {len(separacoes)} itens',
            'tabelas_sincronizadas': tabelas_sincronizadas
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
    """Reverter confirmação de agendamento. Suporta Nacom e CarVia."""
    try:
        # ===== CarVia =====
        if str(lote_id).startswith('CARVIA-'):
            return _toggle_agendamento_carvia(lote_id, confirmar=False)

        # ===== Nacom: fluxo original =====
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

        # ✅ SINCRONIZAR com EmbarqueItem (se existir)
        tabelas_sincronizadas = []
        try:
            from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

            sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
            resultado_sync = sincronizador.sincronizar_desde_separacao(
                separacao_lote_id=lote_id,
                criar_agendamento=False
            )

            if resultado_sync['success']:
                tabelas_sincronizadas = resultado_sync.get('tabelas_atualizadas', [])
                if tabelas_sincronizadas:
                    logger.info(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(tabelas_sincronizadas)}")
        except Exception as sync_error:
            logger.warning(f"Aviso na sincronização: {sync_error}")

        return jsonify({
            'success': True,
            'message': f'Confirmação revertida para {len(separacoes)} itens',
            'tabelas_sincronizadas': tabelas_sincronizadas
        })

    except Exception as e:
        logger.error(f"Erro ao reverter agendamento do lote {lote_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _toggle_agendamento_carvia(lote_id, confirmar=True):
    """Toggle agendamento_confirmado para cotações CarVia."""
    from app.carvia.models import CarviaCotacao, CarviaPedido

    # Resolver cotação a partir do lote_id
    if str(lote_id).startswith('CARVIA-PED-'):
        ped_id = int(str(lote_id).replace('CARVIA-PED-', ''))
        pedido = db.session.get(CarviaPedido, ped_id)
        if not pedido:
            return jsonify({'success': False, 'error': f'Pedido CarVia {lote_id} não encontrado'}), 404
        cot = pedido.cotacao
    else:
        cot_id = int(str(lote_id).replace('CARVIA-', ''))
        cot = db.session.get(CarviaCotacao, cot_id)

    if not cot:
        return jsonify({'success': False, 'error': f'Cotação CarVia não encontrada'}), 404

    # Verificar se tem data_agenda
    if confirmar and not cot.data_agenda:
        return jsonify({
            'success': False,
            'error': 'Cotação CarVia não possui data de agendamento'
        }), 400

    cot.agendamento_confirmado = confirmar
    db.session.commit()

    acao = 'confirmado' if confirmar else 'revertido'
    logger.info(f"Agendamento CarVia {acao} para {lote_id} (cotação {cot.numero_cotacao}) por {current_user.nome}")

    return jsonify({
        'success': True,
        'message': f'Agendamento {acao} para cotação CarVia {cot.numero_cotacao}',
        'tabelas_sincronizadas': []
    })
