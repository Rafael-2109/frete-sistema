#!/usr/bin/env python3
"""
Correcao — RecebimentoLf ID 10: Transmissao NF-e Transfer (incidente 2026-02-18)
=================================================================================

Contexto:
- ID 10: RQ job timeout (5400s) durante pipeline transfer FB->CD
- etapa_atual=22 (step 22 completo, step 23 nao executou)
- odoo_transfer_invoice_id=500900
- Problema potencial: NF-e com erro SEFAZ 225 ("Falha no Schema XML")

Workaround manual descoberto pelo usuario:
  1. Clicar "Transmitir" (action_gerar_nfe) → erro 225
  2. Clicar "Pre-visualizar XML" (action_previsualizar_xml_nfe) → Odoo resolve
  3. NF-e fica autorizada

Este script reproduz o workaround via XML-RPC:
  1. Verifica estado atual da invoice 500900
  2. Se nao autorizada: chama action_gerar_nfe
  3. Se ainda nao autorizada: chama action_previsualizar_xml_nfe (workaround)
  4. Verifica resultado final

Execucao:
    source .venv/bin/activate
    python scripts/migrations/corrigir_recebimento_lf_10_nfe.py [--dry-run] [--execute]

Flags:
    --dry-run    Apenas diagnostica, sem executar acoes (default)
    --execute    Executa o workaround no Odoo
"""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INVOICE_ID = 500900
RECEBIMENTO_LF_ID = 10

# Campos para diagnostico completo da invoice
INVOICE_FIELDS = [
    'id', 'name', 'state', 'move_type',
    'l10n_br_situacao_nf', 'l10n_br_chave_nf',
    'l10n_br_cstat_nf', 'l10n_br_xmotivo_nf',
    'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_documento',
    'company_id', 'invoice_origin', 'ref',
]


def ler_invoice(odoo, invoice_id):
    """Le estado completo da invoice no Odoo."""
    result = odoo.execute_kw(
        'account.move', 'read',
        [[invoice_id]],
        {'fields': INVOICE_FIELDS}
    )
    if result:
        return result[0]
    return None


def diagnosticar(odoo):
    """Diagnostica estado atual da invoice e do recebimento."""
    logger.info("=" * 60)
    logger.info("DIAGNOSTICO — Invoice Transfer ID 10")
    logger.info("=" * 60)

    inv = ler_invoice(odoo, INVOICE_ID)
    if not inv:
        logger.error(f"Invoice {INVOICE_ID} NAO encontrada no Odoo!")
        return None

    state = inv.get('state', '')
    situacao_nf = inv.get('l10n_br_situacao_nf', '')
    chave = inv.get('l10n_br_chave_nf', '')
    cstat = inv.get('l10n_br_cstat_nf', '')
    xmotivo = inv.get('l10n_br_xmotivo_nf', '')
    name = inv.get('name', '')
    numero_nf = inv.get('l10n_br_numero_nota_fiscal', '')
    tipo_doc = inv.get('l10n_br_tipo_documento', '')
    company = inv.get('company_id', [])
    origin = inv.get('invoice_origin', '')

    logger.info(f"\n  Invoice: {name} (ID={INVOICE_ID})")
    logger.info(f"  Company: {company}")
    logger.info(f"  Origin: {origin}")
    logger.info(f"  Tipo documento: {tipo_doc}")
    logger.info(f"  State: {state}")
    logger.info(f"  Situacao NF: {situacao_nf}")
    logger.info(f"  Numero NF: {numero_nf}")
    logger.info(f"  Chave NF: {chave}")
    logger.info(f"  cStat: {cstat}")
    logger.info(f"  xMotivo: {xmotivo}")

    # Analise
    chave_valida = chave and len(str(chave)) == 44

    if situacao_nf == 'autorizado' and chave_valida:
        logger.info(f"\n  ✓ NF-e JA AUTORIZADA com chave valida!")
        logger.info(f"  → Retry-transfer deve funcionar sem intervencao.")
        return 'autorizada'

    elif situacao_nf == 'excecao_autorizado' and chave_valida:
        logger.info(f"\n  ⚠ NF-e excecao_autorizado MAS com chave valida.")
        logger.info(f"  → Step 23 aceitaria com ressalva. Retry deve funcionar.")
        return 'excecao_com_chave'

    elif situacao_nf == 'excecao_autorizado' and not chave_valida:
        logger.info(f"\n  ✗ NF-e excecao_autorizado SEM chave valida.")
        logger.info(f"  → Precisa workaround (action_gerar_nfe + preview XML).")
        return 'excecao_sem_chave'

    elif situacao_nf in ('rascunho', False, None):
        if state == 'posted':
            logger.info(f"\n  ✗ Invoice postada mas NF-e em rascunho.")
            logger.info(f"  → Precisa transmitir (action_gerar_nfe).")
            return 'rascunho'
        elif state == 'draft':
            logger.info(f"\n  ✗ Invoice ainda DRAFT.")
            logger.info(f"  → Retry-transfer fara post + transmissao completa.")
            return 'draft'

    else:
        logger.warning(f"\n  ? Estado inesperado: state={state}, situacao={situacao_nf}")
        return 'desconhecido'


def executar_workaround(odoo):
    """Executa o workaround: action_gerar_nfe + action_previsualizar_xml_nfe."""
    logger.info("\n" + "=" * 60)
    logger.info("EXECUTANDO WORKAROUND — Transmissao NF-e")
    logger.info("=" * 60)

    # Passo 1: Chamar action_gerar_nfe (equivale a "Transmitir")
    logger.info(f"\n  Passo 1: Chamando action_gerar_nfe({INVOICE_ID})...")
    try:
        result = odoo.execute_kw(
            'account.move', 'action_gerar_nfe',
            [[INVOICE_ID]],
            timeout_override=120
        )
        logger.info(f"  action_gerar_nfe retornou: {result}")
    except Exception as e:
        logger.warning(f"  action_gerar_nfe falhou (esperado para erro 225): {e}")

    # Aguardar processamento
    logger.info(f"  Aguardando 10s para processamento...")
    time.sleep(10)

    # Verificar estado apos action_gerar_nfe
    inv = ler_invoice(odoo, INVOICE_ID)
    if inv:
        sit = inv.get('l10n_br_situacao_nf', '')
        chave = inv.get('l10n_br_chave_nf', '')
        cstat = inv.get('l10n_br_cstat_nf', '')
        xmotivo = inv.get('l10n_br_xmotivo_nf', '')
        logger.info(f"  Apos action_gerar_nfe: situacao={sit}, chave={chave}, cstat={cstat}")

        if sit == 'autorizado' and chave and len(str(chave)) == 44:
            logger.info(f"  ✓ NF-e autorizada apos action_gerar_nfe!")
            return True

    # Passo 2: Chamar action_previsualizar_xml_nfe (equivale a "Pre-visualizar XML")
    logger.info(f"\n  Passo 2: Chamando action_previsualizar_xml_nfe({INVOICE_ID})...")
    try:
        result = odoo.execute_kw(
            'account.move', 'action_previsualizar_xml_nfe',
            [[INVOICE_ID]],
            timeout_override=120
        )
        logger.info(f"  action_previsualizar_xml_nfe retornou: {type(result).__name__}")
        if isinstance(result, dict):
            # Pode retornar uma action dict (abrir wizard, etc.)
            action_type = result.get('type', '')
            logger.info(f"  Action type: {action_type}")
            if result.get('res_model'):
                logger.info(f"  Res model: {result.get('res_model')}")
    except Exception as e:
        logger.warning(f"  action_previsualizar_xml_nfe falhou: {e}")

    # Aguardar processamento
    logger.info(f"  Aguardando 15s para processamento...")
    time.sleep(15)

    # Verificar estado final
    inv = ler_invoice(odoo, INVOICE_ID)
    if inv:
        sit = inv.get('l10n_br_situacao_nf', '')
        chave = inv.get('l10n_br_chave_nf', '')
        cstat = inv.get('l10n_br_cstat_nf', '')
        xmotivo = inv.get('l10n_br_xmotivo_nf', '')
        logger.info(f"\n  Estado final: situacao={sit}, chave={chave}, cstat={cstat}")
        logger.info(f"  xMotivo: {xmotivo}")

        chave_valida = chave and len(str(chave)) == 44
        if sit == 'autorizado' and chave_valida:
            logger.info(f"  ✓ NF-e AUTORIZADA com sucesso!")
            return True
        elif sit == 'excecao_autorizado' and chave_valida:
            logger.info(f"  ⚠ excecao_autorizado COM chave — aceitavel.")
            return True
        else:
            logger.warning(
                f"  ✗ NF-e ainda nao autorizada apos workaround. "
                f"Pode ser necessario repetir ou verificar manualmente."
            )

            # Passo 3: Tentar action_gerar_nfe mais uma vez (apos preview)
            logger.info(f"\n  Passo 3: Re-chamando action_gerar_nfe apos preview...")
            try:
                odoo.execute_kw(
                    'account.move', 'action_gerar_nfe',
                    [[INVOICE_ID]],
                    timeout_override=120
                )
            except Exception as e:
                logger.warning(f"  action_gerar_nfe (retry) falhou: {e}")

            time.sleep(15)

            inv = ler_invoice(odoo, INVOICE_ID)
            if inv:
                sit = inv.get('l10n_br_situacao_nf', '')
                chave = inv.get('l10n_br_chave_nf', '')
                logger.info(f"  Estado apos retry: situacao={sit}, chave={chave}")
                chave_valida = chave and len(str(chave)) == 44
                if (sit == 'autorizado' or sit == 'excecao_autorizado') and chave_valida:
                    logger.info(f"  ✓ NF-e resolvida apos retry!")
                    return True

            return False

    return False


def main():
    parser = argparse.ArgumentParser(description='Corrigir RecebimentoLf ID 10 — NF-e Transfer')
    parser.add_argument('--execute', action='store_true', help='Executar workaround (default: dry-run)')
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        logger.info("=" * 60)
        logger.info("MODO DRY-RUN — apenas diagnostico, sem acoes no Odoo")
        logger.info("Use --execute para aplicar o workaround")
        logger.info("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("MODO EXECUCAO — acoes serao executadas no Odoo!")
        logger.info("=" * 60)

    from app import create_app
    app = create_app()

    with app.app_context():
        # Estado local (verificado via Render MCP — dados de producao):
        # ID 10: status=processado, etapa_atual=22, transfer_status=erro
        #   odoo_transfer_invoice_id=500900
        #   transfer_erro_mensagem="Timeout RQ: Task exceeded maximum timeout value (5400 seconds)"
        logger.info(f"\n--- Estado RecebimentoLf ID {RECEBIMENTO_LF_ID} (producao via MCP) ---")
        logger.info(f"  status=processado, etapa_atual=22")
        logger.info(f"  transfer_status=erro")
        logger.info(f"  odoo_transfer_invoice_id={INVOICE_ID}")
        logger.info(f"  transfer_erro_mensagem=Timeout RQ (5400s)")

        # Conectar Odoo
        try:
            from app.odoo.utils.connection import get_odoo_connection
            odoo = get_odoo_connection()
            if not odoo.authenticate():
                logger.error("Falha na autenticacao com Odoo!")
                return
            logger.info("✓ Conexao Odoo estabelecida")
        except Exception as e:
            logger.error(f"Erro ao conectar Odoo: {e}")
            return

        # Diagnosticar
        estado = diagnosticar(odoo)

        if estado in ('autorizada', 'excecao_com_chave'):
            logger.info("\n" + "=" * 60)
            logger.info("PROXIMO PASSO")
            logger.info("=" * 60)
            logger.info(f"  NF-e ja esta OK. Disparar retry-transfer:")
            logger.info(f"  POST /recebimento/lf/status/{RECEBIMENTO_LF_ID}/retry-transfer")
            return

        if estado == 'draft':
            logger.info("\n  Invoice em draft — retry-transfer fara todo o fluxo.")
            logger.info(f"  POST /recebimento/lf/status/{RECEBIMENTO_LF_ID}/retry-transfer")
            return

        if dry_run:
            logger.info("\n" + "=" * 60)
            logger.info("[DRY-RUN] Workaround NAO executado.")
            logger.info("Use --execute para tentar action_gerar_nfe + preview XML.")
            logger.info("=" * 60)
            return

        # Executar workaround
        if estado in ('excecao_sem_chave', 'rascunho', 'desconhecido'):
            sucesso = executar_workaround(odoo)

            logger.info("\n" + "=" * 60)
            if sucesso:
                logger.info("RESULTADO: NF-e resolvida com sucesso!")
                logger.info("PROXIMO PASSO:")
                logger.info(f"  POST /recebimento/lf/status/{RECEBIMENTO_LF_ID}/retry-transfer")
            else:
                logger.warning("RESULTADO: NF-e NAO resolvida.")
                logger.warning("Acoes possiveis:")
                logger.warning("  1. Verificar manualmente no Odoo (invoice 500900)")
                logger.warning("  2. Executar script novamente (--execute)")
                logger.warning("  3. Tentar retry-transfer mesmo assim (step 23 tem retry interno)")
            logger.info("=" * 60)


if __name__ == '__main__':
    main()
