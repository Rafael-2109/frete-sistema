"""
Endpoint TEMPORARIO para atualizar status no DB apos correcao manual Odoo (20/02/2026).
REMOVER apos execucao bem-sucedida.

Protegido por token em ADMIN_CORRECTION_TOKEN env var.

Contexto: Reconciliacao Odoo ja executada via script correcao_odoo_direto.py.
Falta apenas refletir o sucesso no banco de producao (status dos itens e lancamento).
"""
import os
import logging

from flask import jsonify, request

from app.financeiro.routes import financeiro_bp
from app import db

logger = logging.getLogger(__name__)

# IDs dos itens com status ERRO (batch de 20/02/2026, lote 3532)
# Todos ja reconciliados no Odoo via correcao_odoo_direto.py
ITEM_IDS_CORRIGIDOS = [
    19544, 19561, 19564, 19569, 19581, 19582, 19583, 19584, 19585,
    19596, 19601, 19603, 19606, 19618, 19620, 19630, 19632, 19635,
]

# Lancamento 12201 — full_reconcile_extrato_id obtido do Odoo apos reconciliacao
LANC_12201_FULL_RECONCILE_EXTRATO_ID = 55784


@financeiro_bp.route('/admin/correcao-db-status-20250220', methods=['POST'])
def admin_correcao_db_status_20250220():
    """
    Endpoint TEMPORARIO: atualiza status no DB para refletir reconciliacao Odoo ja feita.
    NAO faz nenhuma operacao no Odoo — apenas UPDATE no banco local.
    Protegido por ADMIN_CORRECTION_TOKEN.
    REMOVER apos uso.
    """
    token = request.headers.get('X-Admin-Token', '')
    expected = os.environ.get('ADMIN_CORRECTION_TOKEN', '')

    if not expected or token != expected:
        return jsonify({'error': 'unauthorized'}), 401

    dry_run = request.args.get('dry_run') == '1'

    try:
        from app.financeiro.models import ExtratoItem
        from app.financeiro.models_comprovante import LancamentoComprovante
        from app.utils.timezone import agora_utc_naive

        resultados = {'itens_extrato': [], 'lancamento_12201': None}

        # --- Parte A: 18 itens de extrato ---
        itens = ExtratoItem.query.filter(
            ExtratoItem.id.in_(ITEM_IDS_CORRIGIDOS),
        ).order_by(ExtratoItem.id).all()

        for item in itens:
            info = {
                'id': item.id,
                'status_antes': item.status,
                'titulo_nf': item.titulo_nf,
                'titulo_parcela': item.titulo_parcela,
            }
            if item.status == 'ERRO':
                if not dry_run:
                    item.status = 'CONCILIADO'
                    item.mensagem = 'Conciliado via script de correcao 20/02'
                info['status_depois'] = 'CONCILIADO'
                info['acao'] = 'atualizado'
            elif item.status == 'CONCILIADO':
                info['status_depois'] = 'CONCILIADO'
                info['acao'] = 'ja_ok'
            else:
                info['status_depois'] = item.status
                info['acao'] = 'skip_status_inesperado'

            resultados['itens_extrato'].append(info)

        # --- Parte B: Lancamento 12201 ---
        lanc = db.session.get(LancamentoComprovante, 12201)
        if lanc:
            info_lanc = {
                'id': 12201,
                'status_antes': lanc.status,
                'odoo_payment_id': lanc.odoo_payment_id,
            }
            if lanc.status in ('REJEITADO', 'ERRO'):
                if not dry_run:
                    lanc.status = 'LANCADO'
                    lanc.lancado_em = agora_utc_naive()
                    lanc.lancado_por = 'script_correcao_20250220'
                    lanc.erro_lancamento = None
                    lanc.odoo_full_reconcile_extrato_id = LANC_12201_FULL_RECONCILE_EXTRATO_ID

                    comp = lanc.comprovante
                    if comp:
                        comp.odoo_is_reconciled = True

                info_lanc['status_depois'] = 'LANCADO'
                info_lanc['full_reconcile_extrato_id'] = LANC_12201_FULL_RECONCILE_EXTRATO_ID
                info_lanc['acao'] = 'atualizado'
            elif lanc.status == 'LANCADO':
                info_lanc['status_depois'] = 'LANCADO'
                info_lanc['acao'] = 'ja_ok'
            else:
                info_lanc['status_depois'] = lanc.status
                info_lanc['acao'] = 'skip_status_inesperado'

            resultados['lancamento_12201'] = info_lanc

        # Commit
        if not dry_run:
            db.session.commit()
            logger.info(
                f"CORRECAO DB STATUS 20/02: {len(ITEM_IDS_CORRIGIDOS)} itens + lanc 12201 atualizados"
            )

        atualizados = sum(1 for i in resultados['itens_extrato'] if i['acao'] == 'atualizado')
        return jsonify({
            'status': 'ok' if not dry_run else 'dry_run',
            'itens_atualizados': atualizados,
            'lancamento_atualizado': (
                resultados['lancamento_12201']['acao'] == 'atualizado'
                if resultados['lancamento_12201'] else False
            ),
            'detalhes': resultados,
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"CORRECAO DB STATUS FALHA: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
