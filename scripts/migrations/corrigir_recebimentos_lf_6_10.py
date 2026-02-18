#!/usr/bin/env python3
"""
Correção de dados — Recebimentos LF IDs 6-10 (incidente 2026-02-18)
====================================================================

Contexto:
- IDs 6-7: Worker morto por deploy enquanto processava (etapa 3, status 'processando')
- ID 8: Step 25 fez match com CTe 33120 (DFe errado — sem filtro CNPJ emitente)
- ID 9: OK — concluído com sucesso (nenhuma ação)
- ID 10: Robot Odoo timeout — invoice transfer não criada no prazo

Ações deste script:
1. IDs 6-7: Reset para 'erro' + liberar locks Redis
2. ID 8: Verificar DFe 33120 no Odoo, limpar odoo_cd_dfe_id, resetar etapa para 24
3. ID 9: Pular (já concluído)
4. ID 10: Verificar estado no Odoo, flaggar para retry-transfer

Execução:
    source .venv/bin/activate
    python scripts/migrations/corrigir_recebimentos_lf_6_10.py [--dry-run] [--skip-odoo]

Flags:
    --dry-run    Mostra o que faria sem executar (default)
    --execute    Executa as correções
    --skip-odoo  Pula verificações no Odoo (útil se sem VPN)
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verificar_odoo_dfe(odoo, dfe_id, company_id):
    """Verifica estado de um DFe no Odoo."""
    try:
        result = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'read',
            [[dfe_id]],
            {'fields': [
                'id', 'l10n_br_status', 'purchase_id',
                'nfe_infnfe_ide_nnf', 'nfe_infnfe_emit_cnpj',
                'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_mod',
                'company_id',
            ]}
        )
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.warning(f"  Erro ao verificar DFe {dfe_id}: {e}")
        return None


def verificar_picking_invoice_transfer(odoo, rec):
    """Verifica se o picking de saída FB tem invoice vinculada (para ID 10)."""
    try:
        picking_id = rec.odoo_transfer_out_picking_id
        if not picking_id:
            return None

        result = odoo.execute_kw(
            'stock.picking', 'read',
            [[picking_id]],
            {'fields': ['id', 'name', 'state', 'invoice_ids']}
        )
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.warning(f"  Erro ao verificar picking {rec.odoo_transfer_out_picking_id}: {e}")
        return None


def verificar_invoice_transfer(odoo, invoice_id):
    """Verifica estado da invoice de transferência no Odoo (para ID 10).

    Cenários após RQ timeout no step 23:
    - draft: action_post nunca executou
    - posted + rascunho: postou mas não transmitiu NF-e
    - posted + autorizado: tudo OK, step 23 completaria idempotente
    - posted + excecao_autorizado: transmissão falhou, retry tentará novamente
    """
    try:
        result = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': [
                'id', 'name', 'state', 'l10n_br_situacao_nf',
                'l10n_br_numero_nota_fiscal', 'ref',
                'invoice_origin', 'company_id',
            ]}
        )
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.warning(f"  Erro ao verificar invoice {invoice_id}: {e}")
        return None


def liberar_lock_redis(dfe_id):
    """Libera lock Redis de um DFe."""
    try:
        from redis import Redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_conn = Redis.from_url(redis_url)
        key = f'recebimento_lf_lock:{dfe_id}'
        deleted = redis_conn.delete(key)
        return deleted > 0
    except Exception as e:
        logger.warning(f"  Erro ao liberar lock Redis para DFe {dfe_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Corrigir Recebimentos LF IDs 6-10')
    parser.add_argument('--execute', action='store_true', help='Executar correções (default: dry-run)')
    parser.add_argument('--skip-odoo', action='store_true', help='Pular verificações no Odoo')
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        logger.info("=" * 60)
        logger.info("MODO DRY-RUN — nenhuma alteração será feita")
        logger.info("Use --execute para aplicar as correções")
        logger.info("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("MODO EXECUÇÃO — alterações serão aplicadas!")
        logger.info("=" * 60)

    from app import create_app, db
    app = create_app()

    with app.app_context():
        from app.recebimento.models import RecebimentoLf

        # Conectar Odoo se necessário
        odoo = None
        if not args.skip_odoo:
            try:
                from app.odoo.utils.connection import get_odoo_connection
                odoo = get_odoo_connection()
                logger.info("Conexão Odoo estabelecida")
            except Exception as e:
                logger.warning(f"Sem conexão Odoo ({e}). Use --skip-odoo para pular.")
                odoo = None

        # ===== DIAGNÓSTICO =====
        logger.info("\n" + "=" * 60)
        logger.info("DIAGNÓSTICO — Estado atual dos IDs 6-10")
        logger.info("=" * 60)

        recebimentos = RecebimentoLf.query.filter(
            RecebimentoLf.id.in_([6, 7, 8, 9, 10])
        ).order_by(RecebimentoLf.id).all()

        rec_map = {r.id: r for r in recebimentos}
        acoes = {}  # id -> ação a tomar

        for rec in recebimentos:
            logger.info(
                f"\nID {rec.id}: status={rec.status}, etapa={rec.etapa_atual}, "
                f"transfer_status={rec.transfer_status}, "
                f"odoo_dfe_id={rec.odoo_dfe_id}, odoo_cd_dfe_id={rec.odoo_cd_dfe_id}"
            )
            if rec.erro_mensagem:
                logger.info(f"  erro_mensagem: {rec.erro_mensagem[:200]}")
            if rec.transfer_erro_mensagem:
                logger.info(f"  transfer_erro: {rec.transfer_erro_mensagem[:200]}")

        # ===== ID 9 — OK =====
        rec9 = rec_map.get(9)
        if rec9:
            if rec9.status == 'processado' and rec9.transfer_status == 'concluido' and rec9.etapa_atual == 37:
                logger.info(f"\n✓ ID 9: Completo com sucesso (etapa 37, concluido). NENHUMA AÇÃO.")
                acoes[9] = 'ok'
            else:
                logger.warning(f"\n⚠ ID 9: Estado inesperado! Verificar manualmente.")
                acoes[9] = 'verificar'

        # ===== IDs 6-7 — Worker morto =====
        for rid in [6, 7]:
            rec = rec_map.get(rid)
            if not rec:
                logger.warning(f"\nID {rid}: Não encontrado!")
                continue

            if rec.status == 'erro':
                # Já foi corrigido (cleanup automático ou manual)
                logger.info(f"\n✓ ID {rid}: Já está com status='erro'. Provavelmente cleanup automático já rodou.")
                acoes[rid] = 'ja_corrigido'
            elif rec.status == 'processando':
                logger.info(f"\n→ ID {rid}: Preso em 'processando' (etapa {rec.etapa_atual}). Será resetado para 'erro'.")
                acoes[rid] = 'reset_erro'
            elif rec.status == 'pendente':
                logger.info(f"\n✓ ID {rid}: Já está 'pendente' (retry em andamento?).")
                acoes[rid] = 'ja_corrigido'
            else:
                logger.info(f"\n✓ ID {rid}: status={rec.status}. Nenhuma ação automática.")
                acoes[rid] = 'ok'

        # ===== ID 8 — CTe match errado =====
        rec8 = rec_map.get(8)
        if rec8:
            logger.info(f"\n--- ID 8: Análise DFe CD ---")
            logger.info(f"  odoo_cd_dfe_id={rec8.odoo_cd_dfe_id} (suspeito CTe)")
            logger.info(f"  transfer_status={rec8.transfer_status}")
            logger.info(f"  etapa_atual={rec8.etapa_atual}")

            if odoo and rec8.odoo_cd_dfe_id:
                dfe_info = verificar_odoo_dfe(odoo, rec8.odoo_cd_dfe_id, 4)  # COMPANY_CD=4
                if dfe_info:
                    modelo = dfe_info.get('nfe_infnfe_ide_mod', '')
                    cnpj_emit = dfe_info.get('nfe_infnfe_emit_cnpj', '')
                    numero = dfe_info.get('nfe_infnfe_ide_nnf', '')
                    status_dfe = dfe_info.get('l10n_br_status', '')
                    purchase = dfe_info.get('purchase_id', False)
                    logger.info(
                        f"  Odoo DFe {rec8.odoo_cd_dfe_id}: modelo={modelo}, "
                        f"cnpj_emit={cnpj_emit}, numero={numero}, "
                        f"status={status_dfe}, purchase={purchase}"
                    )
                    if modelo == '57' or (cnpj_emit and cnpj_emit != '61.724.241/0001-78'):
                        logger.info(f"  CONFIRMADO: DFe {rec8.odoo_cd_dfe_id} é CTe (modelo={modelo}) ou emitente diferente.")
                        logger.info(f"  → Será limpo do recebimento (odoo_cd_dfe_id=NULL, etapa=24).")
                        acoes[8] = 'reset_cd_dfe'
                    elif purchase:
                        logger.warning(
                            f"  ⚠ DFe {rec8.odoo_cd_dfe_id} tem PO vinculado ({purchase}). "
                            f"Verificar se PO foi criado indevidamente."
                        )
                        acoes[8] = 'reset_cd_dfe'
                    else:
                        logger.info(f"  DFe parece ser NF-e válida da FB. Verificar manualmente.")
                        acoes[8] = 'verificar'
                else:
                    logger.warning(f"  DFe {rec8.odoo_cd_dfe_id} não encontrado no Odoo!")
                    acoes[8] = 'reset_cd_dfe'
            elif rec8.odoo_cd_dfe_id:
                logger.info(f"  Sem Odoo — assumindo CTe errado (conforme diagnóstico original).")
                acoes[8] = 'reset_cd_dfe'
            else:
                logger.info(f"  odoo_cd_dfe_id já é NULL. Verificar se precisa reset de etapa.")
                if rec8.etapa_atual > 24 and rec8.transfer_status == 'erro':
                    acoes[8] = 'reset_etapa_only'
                else:
                    acoes[8] = 'ja_corrigido'

        # ===== ID 10 — Robot timeout =====
        rec10 = rec_map.get(10)
        if rec10:
            logger.info(f"\n--- ID 10: Análise Transfer Timeout ---")
            logger.info(f"  etapa_atual={rec10.etapa_atual}, transfer_status={rec10.transfer_status}")
            logger.info(f"  odoo_transfer_out_picking_id={rec10.odoo_transfer_out_picking_id}")
            logger.info(f"  odoo_transfer_invoice_id={rec10.odoo_transfer_invoice_id}")

            # Verificar estado da invoice de transferência (crítico para entender o timeout)
            if odoo and rec10.odoo_transfer_invoice_id:
                inv_info = verificar_invoice_transfer(odoo, rec10.odoo_transfer_invoice_id)
                if inv_info:
                    inv_state = inv_info.get('state', '')
                    situacao_nf = inv_info.get('l10n_br_situacao_nf', '')
                    inv_name = inv_info.get('name', '')
                    numero_nf_transfer = inv_info.get('l10n_br_numero_nota_fiscal', '')
                    logger.info(
                        f"  Invoice {inv_name} (ID={rec10.odoo_transfer_invoice_id}): "
                        f"state={inv_state}, situacao_nf={situacao_nf}, "
                        f"numero_nf={numero_nf_transfer}"
                    )

                    if situacao_nf == 'autorizado':
                        logger.info(
                            f"  ✓ Invoice JÁ AUTORIZADA! Step 23 completou antes do timeout "
                            f"(ou robo autorizou depois). Retry-transfer prosseguirá do step 24."
                        )
                        acoes[10] = 'retry_transfer'
                    elif inv_state == 'posted' and situacao_nf in ('rascunho', 'excecao_autorizado', False, None):
                        logger.info(
                            f"  ⚠ Invoice postada mas NF-e NÃO autorizada (situacao={situacao_nf}). "
                            f"Step 23 executou parcialmente. Retry-transfer tentará action_gerar_nfe."
                        )
                        acoes[10] = 'retry_transfer'
                    elif inv_state == 'draft':
                        logger.info(
                            f"  Invoice ainda DRAFT. Step 23 NÃO executou action_post. "
                            f"Retry-transfer fará post + transmissão completa."
                        )
                        acoes[10] = 'retry_transfer'
                    else:
                        logger.warning(
                            f"  Estado inesperado: state={inv_state}, situacao={situacao_nf}. "
                            f"Verificar manualmente."
                        )
                        acoes[10] = 'verificar'
                else:
                    logger.warning(f"  Invoice {rec10.odoo_transfer_invoice_id} NÃO encontrada no Odoo!")
                    acoes[10] = 'verificar'

            elif odoo and rec10.odoo_transfer_out_picking_id:
                # Sem invoice_id — verificar picking
                picking_info = verificar_picking_invoice_transfer(odoo, rec10)
                if picking_info:
                    invoice_ids = picking_info.get('invoice_ids', [])
                    state = picking_info.get('state', '')
                    name = picking_info.get('name', '')
                    logger.info(
                        f"  Picking {name}: state={state}, invoice_ids={invoice_ids}"
                    )
                    if invoice_ids:
                        logger.info(f"  ✓ Robot criou invoice(s) {invoice_ids}.")
                        acoes[10] = 'retry_transfer'
                    else:
                        logger.info(f"  ✗ Picking sem invoice.")
                        acoes[10] = 'retry_transfer'
                else:
                    logger.warning(f"  Picking não encontrado no Odoo!")
                    acoes[10] = 'verificar'
            else:
                logger.info(
                    f"  Sem Odoo — retry-transfer deve funcionar. "
                    f"Steps 19-22 são idempotentes, step 23 trata todos os estados da invoice."
                )
                acoes[10] = 'retry_transfer'

        # ===== EXECUÇÃO DAS CORREÇÕES =====
        logger.info("\n" + "=" * 60)
        logger.info("PLANO DE CORREÇÃO")
        logger.info("=" * 60)

        for rid in [6, 7, 8, 9, 10]:
            acao = acoes.get(rid, 'desconhecido')
            logger.info(f"  ID {rid}: {acao}")

        if dry_run:
            logger.info("\n[DRY-RUN] Nenhuma alteração aplicada. Use --execute para executar.")
            return

        # Aplicar correções
        alterados = []

        # IDs 6-7: Reset para 'erro'
        for rid in [6, 7]:
            rec = rec_map.get(rid)
            if not rec:
                continue
            acao = acoes.get(rid)
            if acao == 'reset_erro':
                rec.status = 'erro'
                rec.erro_mensagem = (
                    f'Processamento interrompido (etapa: {rec.etapa_atual}, '
                    f'ultimo checkpoint: {rec.ultimo_checkpoint_em}). '
                    f'Deploy do worker em 2026-02-18 15:56.'
                )
                alterados.append(rid)
                logger.info(f"  ID {rid}: status → 'erro'")

                # Liberar lock Redis
                if rec.odoo_dfe_id:
                    freed = liberar_lock_redis(rec.odoo_dfe_id)
                    logger.info(f"  ID {rid}: Lock Redis DFe {rec.odoo_dfe_id} {'liberado' if freed else 'não existia'}")
            elif acao == 'ja_corrigido':
                logger.info(f"  ID {rid}: Já corrigido — pulando")

        # ID 8: Reset CD DFe
        rec8 = rec_map.get(8)
        if rec8:
            acao = acoes.get(8)
            if acao == 'reset_cd_dfe':
                old_cd_dfe = rec8.odoo_cd_dfe_id
                rec8.odoo_cd_dfe_id = None
                rec8.odoo_cd_po_id = None
                rec8.odoo_cd_po_name = None
                rec8.odoo_cd_invoice_id = None
                rec8.odoo_cd_invoice_name = None
                rec8.etapa_atual = 24
                rec8.transfer_status = 'erro'
                rec8.transfer_erro_mensagem = (
                    f'Corrigido: DFe CD {old_cd_dfe} era CTe (match errado por numero_nf). '
                    f'Resetado para etapa 24 para retry com filtro CNPJ emitente.'
                )
                alterados.append(8)
                logger.info(
                    f"  ID 8: odoo_cd_dfe_id {old_cd_dfe} → NULL, "
                    f"etapa 26 → 24, campos CD limpos"
                )
            elif acao == 'reset_etapa_only':
                rec8.etapa_atual = 24
                rec8.transfer_erro_mensagem = 'Resetado para etapa 24 para retry.'
                alterados.append(8)
                logger.info(f"  ID 8: etapa → 24")
            elif acao == 'ja_corrigido':
                logger.info(f"  ID 8: Já corrigido — pulando")

        # ID 10: Apenas flaggar para retry (não precisa alterar dados)
        rec10 = rec_map.get(10)
        if rec10 and acoes.get(10) == 'retry_transfer':
            logger.info(
                f"  ID 10: Pronto para retry-transfer (etapa {rec10.etapa_atual}). "
                f"Use: POST /recebimento/lf/status/10/retry-transfer"
            )

        # Commit
        if alterados:
            db.session.commit()
            logger.info(f"\n✓ Commit realizado. IDs alterados: {alterados}")
        else:
            logger.info(f"\nNenhum registro alterado.")

        # Resumo final
        logger.info("\n" + "=" * 60)
        logger.info("PRÓXIMOS PASSOS")
        logger.info("=" * 60)

        for rid in [6, 7]:
            acao = acoes.get(rid)
            if acao in ('reset_erro', 'ja_corrigido'):
                logger.info(f"  ID {rid}: POST /recebimento/lf/status/{rid}/retry")

        if acoes.get(8) in ('reset_cd_dfe', 'reset_etapa_only', 'ja_corrigido'):
            logger.info(f"  ID 8: POST /recebimento/lf/status/8/retry-transfer")

        logger.info(f"  ID 9: Nenhuma ação (concluido)")

        if acoes.get(10) == 'retry_transfer':
            logger.info(f"  ID 10: POST /recebimento/lf/status/10/retry-transfer")

        logger.info("\nScript concluído.")


if __name__ == '__main__':
    main()
