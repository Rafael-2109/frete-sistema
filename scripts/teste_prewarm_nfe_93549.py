#!/usr/bin/env python3
"""
Teste — Pre-warm NF-e 93549: Validar estrategia antes de aplicar em producao
=============================================================================

Contexto:
- NF-e de transferencia criada pelo robo CIEL IT frequentemente falha na
  transmissao com SEFAZ error 225 ("Falha no Schema XML")
- Causa raiz: campos fiscais NF-e (nfe_infnfe_*, totais de impostos, CFOP)
  ficam em estado "stale" — os @api.depends/@api.compute do l10n_br nao
  sao avaliados pela criacao via robo
- Workaround: chamar action_previsualizar_xml_nfe (ou recalcular impostos)
  ANTES de transmitir, forcando a cadeia de dependencias do ORM

Este script testa a estrategia de pre-warm com a NF 93549 (FB, company_id=1):
  - Estrategia A: action_previsualizar_xml_nfe (mirrors click "Pre-visualizar XML")
  - Estrategia B: onchange_l10n_br_calcular_imposto + _btn (recalculo impostos)
  - Estrategia AB: combinada (B + A)

Execucao:
    source .venv/bin/activate
    python scripts/teste_prewarm_nfe_93549.py --diagnose
    python scripts/teste_prewarm_nfe_93549.py --execute --strategy AB

Flags:
    --diagnose               Apenas le estado, sem acoes (default)
    --execute --strategy X   Executa a estrategia escolhida (A, B ou AB)
"""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NF_NUMERO = '93549'
COMPANY_ID = 1  # FB

# Campos para diagnostico completo da invoice
INVOICE_FIELDS = [
    'id', 'name', 'state', 'move_type',
    'l10n_br_situacao_nf', 'l10n_br_chave_nf',
    'l10n_br_cstat_nf', 'l10n_br_xmotivo_nf',
    'l10n_br_numero_nota_fiscal', 'l10n_br_tipo_documento',
    'company_id', 'invoice_origin', 'ref',
    'amount_total', 'amount_tax', 'amount_untaxed',
]

# Campos das linhas da invoice para diagnostico fiscal
LINE_FIELDS = [
    'id', 'name', 'product_id', 'quantity', 'price_unit',
    'price_subtotal', 'price_total',
    'tax_ids', 'l10n_br_cfop_id',
]


def buscar_invoice_por_numero_nf(odoo, numero_nf, company_id):
    """Busca invoice por l10n_br_numero_nota_fiscal + company_id."""
    logger.info(f"Buscando NF {numero_nf} (company_id={company_id})...")
    result = odoo.execute_kw(
        'account.move', 'search_read',
        [[
            ('l10n_br_numero_nota_fiscal', '=', numero_nf),
            ('company_id', '=', company_id),
        ]],
        {'fields': INVOICE_FIELDS, 'limit': 5}
    )
    if not result:
        logger.error(f"NF {numero_nf} NAO encontrada (company_id={company_id})")
        return None
    if len(result) > 1:
        logger.warning(f"Multiplas invoices encontradas ({len(result)}). Usando a primeira.")
        for inv in result:
            logger.info(f"  - ID={inv['id']}, name={inv['name']}, state={inv['state']}")
    return result[0]


def diagnosticar(odoo, inv):
    """Diagnostica estado completo da invoice."""
    invoice_id = inv['id']

    logger.info("=" * 70)
    logger.info("DIAGNOSTICO — NF-e Pre-warm Test")
    logger.info("=" * 70)

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
    amount_total = inv.get('amount_total', 0)
    amount_tax = inv.get('amount_tax', 0)
    amount_untaxed = inv.get('amount_untaxed', 0)

    logger.info(f"\n  Invoice: {name} (ID={invoice_id})")
    logger.info(f"  Company: {company}")
    logger.info(f"  Origin: {origin}")
    logger.info(f"  Tipo documento: {tipo_doc}")
    logger.info(f"  Move type: {inv.get('move_type', '')}")
    logger.info(f"  State: {state}")
    logger.info(f"  Situacao NF: {situacao_nf}")
    logger.info(f"  Numero NF: {numero_nf}")
    logger.info(f"  Chave NF: {chave}")
    logger.info(f"  cStat: {cstat}")
    logger.info(f"  xMotivo: {xmotivo}")
    logger.info(f"  amount_untaxed: {amount_untaxed}")
    logger.info(f"  amount_tax: {amount_tax}")
    logger.info(f"  amount_total: {amount_total}")

    # Ler linhas da invoice para diagnostico fiscal
    logger.info(f"\n  --- Linhas da invoice (diagnostico fiscal) ---")
    try:
        lines = odoo.execute_kw(
            'account.move.line', 'search_read',
            [[
                ('move_id', '=', invoice_id),
                ('display_type', 'not in', ['line_section', 'line_note']),
                ('exclude_from_invoice_tab', '=', False),
            ]],
            {'fields': LINE_FIELDS, 'limit': 20}
        )
        if lines:
            for i, line in enumerate(lines, 1):
                product = line.get('product_id', [])
                product_name = product[1] if isinstance(product, (list, tuple)) and len(product) > 1 else str(product)
                cfop = line.get('l10n_br_cfop_id', [])
                cfop_name = cfop[1] if isinstance(cfop, (list, tuple)) and len(cfop) > 1 else str(cfop)
                tax_ids = line.get('tax_ids', [])
                logger.info(
                    f"  Linha {i}: {product_name[:40]} | "
                    f"qty={line.get('quantity')} | "
                    f"price_unit={line.get('price_unit')} | "
                    f"subtotal={line.get('price_subtotal')} | "
                    f"total={line.get('price_total')} | "
                    f"CFOP={cfop_name} | "
                    f"taxes={len(tax_ids)} tax(es)"
                )
        else:
            logger.warning(f"  Nenhuma linha encontrada na invoice {invoice_id}")
    except Exception as e:
        logger.warning(f"  Erro ao ler linhas: {e}")

    # Analise de estado
    chave_valida = chave and len(str(chave)) == 44

    logger.info(f"\n  --- Analise ---")
    if situacao_nf == 'autorizado' and chave_valida:
        logger.info(f"  RESULTADO: NF-e JA AUTORIZADA com chave valida.")
        logger.info(f"  → Pre-warm NAO necessario.")
        return 'autorizada'

    elif situacao_nf == 'excecao_autorizado' and chave_valida:
        logger.info(f"  RESULTADO: excecao_autorizado COM chave valida.")
        logger.info(f"  → Pode tentar pre-warm + re-transmissao.")
        return 'excecao_com_chave'

    elif situacao_nf in ('rascunho', False, None, ''):
        if state == 'posted':
            logger.info(f"  RESULTADO: Posted + NF-e em rascunho.")
            logger.info(f"  → CANDIDATO IDEAL para pre-warm + transmissao.")
            return 'rascunho'
        elif state == 'draft':
            logger.info(f"  RESULTADO: Invoice DRAFT.")
            logger.info(f"  → Pre-warm + post + transmissao.")
            return 'draft'

    elif situacao_nf == 'excecao_autorizado' and not chave_valida:
        logger.info(f"  RESULTADO: excecao_autorizado SEM chave.")
        logger.info(f"  → CANDIDATO para pre-warm + re-transmissao.")
        return 'excecao_sem_chave'

    else:
        logger.warning(f"  RESULTADO: Estado inesperado (state={state}, situacao={situacao_nf})")
        return 'desconhecido'


def executar_estrategia_a(odoo, invoice_id):
    """Estrategia A: action_previsualizar_xml_nfe (mirrors click "Pre-visualizar XML")."""
    logger.info(f"\n  [Estrategia A] action_previsualizar_xml_nfe({invoice_id})...")
    try:
        result = odoo.execute_kw(
            'account.move', 'action_previsualizar_xml_nfe',
            [[invoice_id]],
            timeout_override=120
        )
        logger.info(f"  [Estrategia A] Retornou: {type(result).__name__}")
        if isinstance(result, dict):
            logger.info(f"  [Estrategia A] Action type: {result.get('type', 'N/A')}")
            if result.get('res_model'):
                logger.info(f"  [Estrategia A] Res model: {result.get('res_model')}")
        return True
    except Exception as e:
        logger.warning(f"  [Estrategia A] Falhou: {e}")
        return False


def executar_estrategia_b(odoo, invoice_id):
    """Estrategia B: onchange_l10n_br_calcular_imposto + _btn (recalculo impostos)."""
    sucesso_parcial = False

    logger.info(f"\n  [Estrategia B] onchange_l10n_br_calcular_imposto({invoice_id})...")
    try:
        odoo.execute_kw(
            'account.move', 'onchange_l10n_br_calcular_imposto',
            [[invoice_id]]
        )
        logger.info(f"  [Estrategia B] calcular_imposto executado")
        sucesso_parcial = True
    except Exception as e:
        logger.warning(f"  [Estrategia B] calcular_imposto falhou: {e}")

    logger.info(f"  [Estrategia B] onchange_l10n_br_calcular_imposto_btn({invoice_id})...")
    try:
        odoo.execute_kw(
            'account.move', 'onchange_l10n_br_calcular_imposto_btn',
            [[invoice_id]],
            timeout_override=120
        )
        logger.info(f"  [Estrategia B] calcular_imposto_btn executado")
        sucesso_parcial = True
    except Exception as e:
        logger.warning(f"  [Estrategia B] calcular_imposto_btn falhou: {e}")

    return sucesso_parcial


def executar_prewarm(odoo, invoice_id, strategy):
    """Executa pre-warm conforme estrategia escolhida."""
    logger.info("\n" + "=" * 70)
    logger.info(f"PRE-WARM — Estrategia {strategy}")
    logger.info("=" * 70)

    if strategy == 'A':
        executar_estrategia_a(odoo, invoice_id)
    elif strategy == 'B':
        executar_estrategia_b(odoo, invoice_id)
    elif strategy == 'AB':
        # Combinada: recalculo de impostos primeiro, depois preview XML
        executar_estrategia_b(odoo, invoice_id)
        time.sleep(3)  # Pausa curta entre operacoes
        executar_estrategia_a(odoo, invoice_id)
    else:
        logger.error(f"Estrategia invalida: {strategy}. Use A, B ou AB.")
        return

    # Aguardar processamento do Odoo
    logger.info(f"\n  Aguardando 5s para Odoo processar...")
    time.sleep(5)

    # Re-ler estado apos pre-warm
    logger.info(f"\n  Re-lendo estado apos pre-warm...")
    inv = odoo.execute_kw(
        'account.move', 'read',
        [[invoice_id]],
        {'fields': [
            'state', 'l10n_br_situacao_nf', 'l10n_br_chave_nf',
            'l10n_br_cstat_nf', 'l10n_br_xmotivo_nf',
            'amount_tax', 'amount_total',
        ]}
    )
    if not inv:
        logger.error(f"Invoice {invoice_id} nao encontrada apos pre-warm!")
        return

    inv = inv[0]
    state = inv.get('state', '')
    situacao_nf = inv.get('l10n_br_situacao_nf', '')
    chave = inv.get('l10n_br_chave_nf', '')
    cstat = inv.get('l10n_br_cstat_nf', '')
    xmotivo = inv.get('l10n_br_xmotivo_nf', '')
    amount_tax = inv.get('amount_tax', 0)
    amount_total = inv.get('amount_total', 0)

    logger.info(f"  State: {state}")
    logger.info(f"  Situacao NF: {situacao_nf}")
    logger.info(f"  Chave NF: {chave}")
    logger.info(f"  cStat: {cstat}")
    logger.info(f"  xMotivo: {xmotivo}")
    logger.info(f"  amount_tax: {amount_tax}")
    logger.info(f"  amount_total: {amount_total}")

    chave_valida = chave and len(str(chave)) == 44

    # Se ja autorizou durante pre-warm (action_previsualizar pode disparar transmissao)
    if situacao_nf == 'autorizado' and chave_valida:
        logger.info(f"\n  PRE-WARM RESULTADO: NF-e AUTORIZADA durante pre-warm!")
        return

    if (situacao_nf == 'excecao_autorizado') and chave_valida:
        logger.info(f"\n  PRE-WARM RESULTADO: excecao_autorizado COM chave (aceitavel).")
        return

    # Tentar transmitir se situacao permite
    if situacao_nf in ('rascunho', 'excecao_autorizado', False, None, ''):
        if state == 'posted':
            logger.info(f"\n  Pre-warm concluido. Tentando transmissao (action_gerar_nfe)...")
            try:
                result = odoo.execute_kw(
                    'account.move', 'action_gerar_nfe',
                    [[invoice_id]],
                    timeout_override=120
                )
                logger.info(f"  action_gerar_nfe retornou: {result}")
            except Exception as e:
                logger.warning(f"  action_gerar_nfe falhou: {e}")

            logger.info(f"  Aguardando 15s para SEFAZ processar...")
            time.sleep(15)

            # Verificar resultado final
            inv_final = odoo.execute_kw(
                'account.move', 'read',
                [[invoice_id]],
                {'fields': [
                    'l10n_br_situacao_nf', 'l10n_br_chave_nf',
                    'l10n_br_cstat_nf', 'l10n_br_xmotivo_nf',
                ]}
            )
            if inv_final:
                inv_final = inv_final[0]
                sit_final = inv_final.get('l10n_br_situacao_nf', '')
                chave_final = inv_final.get('l10n_br_chave_nf', '')
                cstat_final = inv_final.get('l10n_br_cstat_nf', '')
                xmotivo_final = inv_final.get('l10n_br_xmotivo_nf', '')
                chave_final_valida = chave_final and len(str(chave_final)) == 44

                logger.info(f"\n  --- RESULTADO FINAL ---")
                logger.info(f"  Situacao: {sit_final}")
                logger.info(f"  Chave: {chave_final}")
                logger.info(f"  cStat: {cstat_final}")
                logger.info(f"  xMotivo: {xmotivo_final}")

                if sit_final == 'autorizado' and chave_final_valida:
                    logger.info(f"  SUCESSO: NF-e AUTORIZADA com chave valida!")
                elif sit_final == 'excecao_autorizado' and chave_final_valida:
                    logger.info(f"  SUCESSO PARCIAL: excecao_autorizado COM chave.")
                else:
                    logger.warning(
                        f"  FALHA: NF-e nao autorizada apos pre-warm + transmissao. "
                        f"Verificar manualmente no Odoo."
                    )
        elif state == 'draft':
            logger.info(
                f"\n  Invoice em DRAFT apos pre-warm. "
                f"Transmissao requer action_post primeiro."
            )
            logger.info(f"  Este script NAO executa action_post (use retry-transfer).")


def main():
    parser = argparse.ArgumentParser(
        description='Teste Pre-warm NF-e 93549 — Validar estrategia de pre-warm'
    )
    parser.add_argument(
        '--diagnose', action='store_true', default=True,
        help='Apenas diagnostica, sem executar acoes (default)'
    )
    parser.add_argument(
        '--execute', action='store_true',
        help='Executa a estrategia de pre-warm'
    )
    parser.add_argument(
        '--strategy', choices=['A', 'B', 'AB'], default='AB',
        help='Estrategia: A=preview XML, B=recalc impostos, AB=combinada (default: AB)'
    )
    args = parser.parse_args()

    execute = args.execute

    if execute:
        logger.info("=" * 70)
        logger.info(f"MODO EXECUCAO — Estrategia {args.strategy}")
        logger.info("=" * 70)
    else:
        logger.info("=" * 70)
        logger.info("MODO DIAGNOSTICO — apenas leitura, sem acoes no Odoo")
        logger.info("Use --execute --strategy AB para executar pre-warm")
        logger.info("=" * 70)

    from app import create_app
    app = create_app()

    with app.app_context():
        # Conectar ao Odoo
        try:
            from app.odoo.utils.connection import get_odoo_connection
            odoo = get_odoo_connection()
            if not odoo.authenticate():
                logger.error("Falha na autenticacao com Odoo!")
                return
            logger.info("Conexao Odoo estabelecida")
        except Exception as e:
            logger.error(f"Erro ao conectar Odoo: {e}")
            return

        # Buscar NF 93549
        inv = buscar_invoice_por_numero_nf(odoo, NF_NUMERO, COMPANY_ID)
        if not inv:
            return

        invoice_id = inv['id']

        # Diagnosticar
        estado = diagnosticar(odoo, inv)

        if estado == 'autorizada':
            logger.info("\n  NF-e ja autorizada. Nenhuma acao necessaria.")
            return

        if not execute:
            logger.info("\n" + "=" * 70)
            logger.info("[DIAGNOSTICO] Pre-warm NAO executado.")
            logger.info("Use --execute --strategy AB para testar pre-warm.")
            logger.info("=" * 70)
            return

        # Executar pre-warm
        executar_prewarm(odoo, invoice_id, args.strategy)


if __name__ == '__main__':
    main()
