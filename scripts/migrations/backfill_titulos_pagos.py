#!/usr/bin/env python3
"""
Backfill Marco Zero: Corrigir títulos pagos no Odoo mas com parcela_paga=False local
====================================================================================

PROBLEMA:
Os serviços de sync de contas_a_pagar e contas_a_receber filtravam apenas títulos
em aberto (amount_residual < 0 / balance > 0). Quando um título era pago no Odoo,
ele saía do filtro e nunca mais era atualizado — resultando em ~99% dos títulos
com parcela_paga=False mesmo quando já pagos.

SOLUÇÃO:
Este script é um one-time backfill que consulta o Odoo para cada título com
parcela_paga=False e atualiza os que estão pagos.

Padrão "detach-first" para evitar SSL timeout (limite 30s no Render):
- Fase 1: Lê dados do DB → extrai para plain dicts → fecha session
- Fase 2: Chama Odoo API (sem conexão DB aberta)
- Fase 3: Aplica updates por chunk com commit + close imediato

FLUXOS:
- ContasAPagar: Usa odoo_line_id (FK direta) para consultar em chunks
- ContasAReceber: Usa odoo_line_id (quando disponível) + fallback por (empresa, titulo_nf, parcela)

Executar:
    source .venv/bin/activate
    python scripts/migrations/backfill_titulos_pagos.py              # dry-run
    python scripts/migrations/backfill_titulos_pagos.py --execute    # executa

Data: 2026-02-21
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.financeiro.models import ContasAPagar, ContasAReceber
from app.financeiro.parcela_utils import parcela_to_str
from app.financeiro.constants import EMPRESA_MAP
from app.odoo.utils.connection import get_odoo_connection
from sqlalchemy import text

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mapeamento inverso: codigo interno -> company_id Odoo
# Baseado em EMPRESA_MAP: {'NACOM GOYA - FB': 1, 'NACOM GOYA - SC': 2, 'NACOM GOYA - CD': 3}
EMPRESA_CODIGO_PARA_NOME = {v: k for k, v in EMPRESA_MAP.items()}


def backfill_contas_a_pagar(connection, dry_run: bool = True) -> dict:
    """
    Backfill para contas_a_pagar.

    Padrão detach-first:
    - Fase 1: Lê DB → plain dicts → close
    - Fase 2: Odoo API (sem DB aberto)
    - Fase 3: Updates atômicos por batch

    Returns:
        dict com estatísticas
    """
    stats = {
        'total_verificados': 0,
        'atualizados': 0,
        'sem_match_odoo': 0,
        'ja_em_aberto': 0,
        'erros': 0,
    }

    logger.info("=" * 60)
    logger.info("BACKFILL CONTAS A PAGAR")
    logger.info("=" * 60)

    # =========================================================================
    # FASE 1: Ler dados do DB → plain Python → fechar session
    # =========================================================================
    logger.info("\n[FASE 1] Lendo dados do banco...")

    titulos_raw = db.session.query(
        ContasAPagar.id, ContasAPagar.odoo_line_id, ContasAPagar.status_sistema,
        ContasAPagar.metodo_baixa
    ).filter(
        ContasAPagar.parcela_paga == False,
        ContasAPagar.odoo_line_id.isnot(None)
    ).all()

    stats['total_verificados'] = len(titulos_raw)
    logger.info(f"  {len(titulos_raw)} títulos com parcela_paga=False e odoo_line_id")

    if not titulos_raw:
        db.session.close()
        return stats

    # Extrair para plain dicts: {odoo_line_id: {id, status_sistema, metodo_baixa}}
    titulos_por_line_id = {}
    for row_id, line_id, status_sis, met_baixa in titulos_raw:
        titulos_por_line_id[line_id] = {
            'id': row_id,
            'status_sistema': status_sis,
            'metodo_baixa': met_baixa,
        }

    # Fechar session
    db.session.close()

    # =========================================================================
    # FASE 2: Consultar Odoo API (sem conexão DB aberta)
    # =========================================================================
    logger.info("\n[FASE 2] Consultando Odoo...")

    line_ids = list(titulos_por_line_id.keys())
    CHUNK_SIZE = 200

    # Coletar updates: lista de dicts com campos para atualizar
    updates_pendentes = []

    for i in range(0, len(line_ids), CHUNK_SIZE):
        chunk = line_ids[i:i + CHUNK_SIZE]
        logger.info(f"  Chunk {i // CHUNK_SIZE + 1}/{(len(line_ids) - 1) // CHUNK_SIZE + 1}: {len(chunk)} IDs")

        try:
            dados_odoo = connection.search_read(
                'account.move.line',
                [['id', 'in', chunk]],
                fields=['id', 'l10n_br_paga', 'reconciled', 'amount_residual'],
                limit=len(chunk)
            ) or []
        except Exception as e:
            logger.error(f"  ERRO ao consultar Odoo: {e}")
            stats['erros'] += len(chunk)
            continue

        odoo_por_id = {r['id']: r for r in dados_odoo}

        for line_id in chunk:
            odoo_rec = odoo_por_id.get(line_id)
            titulo_info = titulos_por_line_id[line_id]

            if not odoo_rec:
                stats['sem_match_odoo'] += 1
                continue

            paga = bool(odoo_rec.get('l10n_br_paga'))
            amount_residual = float(odoo_rec.get('amount_residual', 0) or 0)
            reconciliado = bool(odoo_rec.get('reconciled'))

            if paga or amount_residual >= 0:
                # Determinar novo status_sistema
                novo_status = titulo_info['status_sistema']
                if novo_status == 'PENDENTE':
                    novo_status = 'PAGO'

                updates_pendentes.append({
                    'id': titulo_info['id'],
                    'parcela_paga': True,
                    'reconciliado': reconciliado,
                    'valor_residual': abs(amount_residual),
                    'status_sistema': novo_status,
                    'metodo_baixa': titulo_info['metodo_baixa'] or 'ODOO_DIRETO',
                    'atualizado_por': 'Backfill Marco Zero',
                })
                stats['atualizados'] += 1
            else:
                stats['ja_em_aberto'] += 1

    logger.info(f"\n  Total updates coletados: {len(updates_pendentes)}")

    # =========================================================================
    # FASE 3: Aplicar updates atômicos por batch
    # =========================================================================
    if not dry_run and updates_pendentes:
        logger.info("\n[FASE 3] Aplicando updates...")

        BATCH_SIZE = 200
        for i in range(0, len(updates_pendentes), BATCH_SIZE):
            batch = updates_pendentes[i:i + BATCH_SIZE]

            try:
                for upd in batch:
                    db.session.execute(
                        text("""
                            UPDATE contas_a_pagar
                            SET parcela_paga = :parcela_paga,
                                reconciliado = :reconciliado,
                                valor_residual = :valor_residual,
                                status_sistema = :status_sistema,
                                metodo_baixa = :metodo_baixa,
                                atualizado_por = :atualizado_por
                            WHERE id = :id
                        """),
                        upd
                    )
                db.session.commit()
                logger.info(
                    f"  Batch {i // BATCH_SIZE + 1}: "
                    f"{len(batch)} updates (total: {i + len(batch)})"
                )
            except Exception as e:
                db.session.rollback()
                logger.error(f"  ERRO batch {i // BATCH_SIZE + 1}: {e}")
                stats['erros'] += len(batch)
                stats['atualizados'] -= len(batch)
            finally:
                db.session.close()
    elif dry_run:
        logger.info("\n[FASE 3] DRY-RUN — nenhum update aplicado")

    logger.info(f"\nRESUMO CONTAS A PAGAR:")
    logger.info(f"  Verificados:    {stats['total_verificados']}")
    logger.info(f"  Atualizados:    {stats['atualizados']}")
    logger.info(f"  Em aberto:      {stats['ja_em_aberto']}")
    logger.info(f"  Sem match Odoo: {stats['sem_match_odoo']}")
    logger.info(f"  Erros:          {stats['erros']}")

    return stats


def backfill_contas_a_receber(connection, dry_run: bool = True) -> dict:
    """
    Backfill para contas_a_receber.

    Duas estratégias:
    - Path A: Registros COM odoo_line_id → lookup direto por ID (O(1), como ContasAPagar)
    - Path B: Registros SEM odoo_line_id → match por (empresa, titulo_nf, parcela)

    Padrão detach-first em ambos os paths.

    Returns:
        dict com estatísticas
    """
    stats = {
        'total_verificados': 0,
        'path_a_total': 0,
        'path_a_atualizados': 0,
        'path_a_em_aberto': 0,
        'path_b_total': 0,
        'path_b_atualizados': 0,
        'atualizados': 0,
        'sem_match_odoo': 0,
        'ja_em_aberto': 0,
        'erros': 0,
    }

    logger.info("\n" + "=" * 60)
    logger.info("BACKFILL CONTAS A RECEBER")
    logger.info("=" * 60)

    # =========================================================================
    # FASE 1: Ler dados do DB → plain Python → fechar session
    # =========================================================================
    logger.info("\n[FASE 1] Lendo dados do banco...")

    titulos_raw = db.session.query(
        ContasAReceber.id, ContasAReceber.empresa,
        ContasAReceber.titulo_nf, ContasAReceber.parcela,
        ContasAReceber.metodo_baixa, ContasAReceber.odoo_line_id
    ).filter(
        ContasAReceber.parcela_paga == False
    ).all()

    stats['total_verificados'] = len(titulos_raw)
    logger.info(f"  {len(titulos_raw)} títulos com parcela_paga=False")

    if not titulos_raw:
        db.session.close()
        return stats

    # Separar em dois grupos
    # Path A: com odoo_line_id → lookup direto
    titulos_com_line_id = {}  # {odoo_line_id: {id, metodo_baixa}}
    # Path B: sem odoo_line_id → match por chave composta
    titulos_por_chave = {}    # {(empresa, titulo_nf, parcela): [{id, metodo_baixa}]}
    por_empresa = {}          # {empresa: set(titulo_nf)}

    for row_id, empresa, titulo_nf, parcela, met_baixa, odoo_line_id in titulos_raw:
        if odoo_line_id:
            titulos_com_line_id[odoo_line_id] = {
                'id': row_id,
                'metodo_baixa': met_baixa,
            }
        else:
            chave = (empresa, titulo_nf, parcela)
            titulos_por_chave.setdefault(chave, []).append({
                'id': row_id,
                'metodo_baixa': met_baixa,
            })
            por_empresa.setdefault(empresa, set()).add(titulo_nf)

    stats['path_a_total'] = len(titulos_com_line_id)
    stats['path_b_total'] = stats['total_verificados'] - stats['path_a_total']
    logger.info(f"  Path A (com odoo_line_id): {stats['path_a_total']}")
    logger.info(f"  Path B (sem odoo_line_id): {stats['path_b_total']}")

    # Fechar session
    db.session.close()

    updates_pendentes = []

    # =========================================================================
    # FASE 2A: Path A — Consultar Odoo por IDs diretos (rápido)
    # =========================================================================
    if titulos_com_line_id:
        logger.info("\n[FASE 2A] Consultando Odoo por odoo_line_id...")

        line_ids = list(titulos_com_line_id.keys())
        CHUNK_SIZE = 200

        for i in range(0, len(line_ids), CHUNK_SIZE):
            chunk = line_ids[i:i + CHUNK_SIZE]
            logger.info(f"  Chunk {i // CHUNK_SIZE + 1}/{(len(line_ids) - 1) // CHUNK_SIZE + 1}: {len(chunk)} IDs")

            try:
                dados_odoo = connection.search_read(
                    'account.move.line',
                    [['id', 'in', chunk]],
                    fields=['id', 'l10n_br_paga', 'balance'],
                    limit=len(chunk)
                ) or []
            except Exception as e:
                logger.error(f"  ERRO Odoo (chunk {i}): {e}")
                stats['erros'] += len(chunk)
                continue

            odoo_por_id = {r['id']: r for r in dados_odoo}

            for line_id in chunk:
                odoo_rec = odoo_por_id.get(line_id)
                titulo_info = titulos_com_line_id[line_id]

                if not odoo_rec:
                    stats['sem_match_odoo'] += 1
                    continue

                paga = bool(odoo_rec.get('l10n_br_paga'))
                balance = float(odoo_rec.get('balance', 0) or 0)

                if paga or balance <= 0:
                    updates_pendentes.append({
                        'id': titulo_info['id'],
                        'metodo_baixa': titulo_info['metodo_baixa'] or 'ODOO_DIRETO',
                    })
                    stats['path_a_atualizados'] += 1
                else:
                    stats['path_a_em_aberto'] += 1

    # =========================================================================
    # FASE 2B: Path B — Consultar Odoo por NF/parcela (fallback)
    # =========================================================================
    if titulos_por_chave:
        logger.info("\n[FASE 2B] Consultando Odoo por NF/parcela (fallback)...")

        CHUNK_SIZE = 100
        matched_ids = set()

        for empresa_cod, nfs_set in por_empresa.items():
            empresa_nome = EMPRESA_CODIGO_PARA_NOME.get(empresa_cod)
            if not empresa_nome:
                logger.warning(f"  Empresa {empresa_cod}: sem mapeamento, pulando")
                continue

            nfs_unicas = list(nfs_set)
            logger.info(
                f"\n  Empresa {empresa_cod} ({empresa_nome}): {len(nfs_unicas)} NFs únicas"
            )

            for i in range(0, len(nfs_unicas), CHUNK_SIZE):
                chunk_nfs = nfs_unicas[i:i + CHUNK_SIZE]

                try:
                    dados_odoo = connection.search_read(
                        'account.move.line',
                        [
                            ['x_studio_nf_e', 'in', chunk_nfs],
                            ['account_type', '=', 'asset_receivable'],
                            ['parent_state', '=', 'posted'],
                        ],
                        fields=[
                            'id', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
                            'l10n_br_paga', 'balance', 'company_id',
                        ],
                        limit=len(chunk_nfs) * 5
                    ) or []
                except Exception as e:
                    logger.error(f"  ERRO Odoo (chunk {i}): {e}")
                    stats['erros'] += len(chunk_nfs)
                    continue

                for rec in dados_odoo:
                    nf = str(rec.get('x_studio_nf_e') or '').strip()
                    if not nf:
                        continue

                    parcela = parcela_to_str(rec.get('l10n_br_cobranca_parcela')) or '1'
                    company_nome = rec.get('company_id', [None, ''])[1] or ''

                    rec_empresa = _mapear_empresa(company_nome)
                    if rec_empresa != empresa_cod:
                        continue

                    paga = bool(rec.get('l10n_br_paga'))
                    balance = float(rec.get('balance', 0) or 0)

                    if not (paga or balance <= 0):
                        continue

                    chave = (empresa_cod, nf, parcela)
                    titulos_locais = titulos_por_chave.get(chave, [])

                    for titulo_info in titulos_locais:
                        if titulo_info['id'] in matched_ids:
                            continue
                        matched_ids.add(titulo_info['id'])

                        updates_pendentes.append({
                            'id': titulo_info['id'],
                            'metodo_baixa': titulo_info['metodo_baixa'] or 'ODOO_DIRETO',
                        })
                        stats['path_b_atualizados'] += 1

    stats['atualizados'] = stats['path_a_atualizados'] + stats['path_b_atualizados']
    stats['ja_em_aberto'] = stats['path_a_em_aberto']
    logger.info(f"\n  Total updates coletados: {len(updates_pendentes)}")

    # =========================================================================
    # FASE 3: Aplicar updates atômicos por batch
    # =========================================================================
    if not dry_run and updates_pendentes:
        logger.info("\n[FASE 3] Aplicando updates...")

        BATCH_SIZE = 200
        for i in range(0, len(updates_pendentes), BATCH_SIZE):
            batch = updates_pendentes[i:i + BATCH_SIZE]

            try:
                for upd in batch:
                    db.session.execute(
                        text("""
                            UPDATE contas_a_receber
                            SET parcela_paga = TRUE,
                                metodo_baixa = :metodo_baixa,
                                atualizado_por = 'Backfill Marco Zero'
                            WHERE id = :id
                        """),
                        upd
                    )
                db.session.commit()
                logger.info(
                    f"  Batch {i // BATCH_SIZE + 1}: "
                    f"{len(batch)} updates (total: {i + len(batch)})"
                )
            except Exception as e:
                db.session.rollback()
                logger.error(f"  ERRO batch {i // BATCH_SIZE + 1}: {e}")
                stats['erros'] += len(batch)
                stats['atualizados'] -= len(batch)
            finally:
                db.session.close()
    elif dry_run:
        logger.info("\n[FASE 3] DRY-RUN — nenhum update aplicado")

    # Contar títulos sem match
    stats['sem_match_odoo'] += stats['total_verificados'] - stats['atualizados'] - stats['ja_em_aberto'] - stats['sem_match_odoo']

    logger.info(f"\nRESUMO CONTAS A RECEBER:")
    logger.info(f"  Verificados:      {stats['total_verificados']}")
    logger.info(f"  Path A (line_id): {stats['path_a_total']} → {stats['path_a_atualizados']} atualizados, {stats['path_a_em_aberto']} em aberto")
    logger.info(f"  Path B (NF):      {stats['path_b_total']} → {stats['path_b_atualizados']} atualizados")
    logger.info(f"  Total atualiz.:   {stats['atualizados']}")
    logger.info(f"  Sem match Odoo:   {stats['sem_match_odoo']}")
    logger.info(f"  Erros:            {stats['erros']}")

    return stats


def _mapear_empresa(nome_empresa: str) -> int:
    """Mapeia o nome da empresa Odoo para o código interno."""
    if not nome_empresa:
        return 0

    for nome, codigo in EMPRESA_MAP.items():
        if nome.upper() in nome_empresa.upper() or nome_empresa.upper() in nome.upper():
            return codigo

    nome_upper = nome_empresa.upper()
    if '- FB' in nome_upper or nome_upper.endswith('FB'):
        return 1
    elif '- SC' in nome_upper or nome_upper.endswith('SC'):
        return 2
    elif '- CD' in nome_upper or nome_upper.endswith('CD'):
        return 3

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Backfill Marco Zero: Corrigir títulos pagos no Odoo'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Executar as alterações (default: dry-run)'
    )
    parser.add_argument(
        '--apenas-pagar',
        action='store_true',
        help='Executar apenas o fluxo de Contas a Pagar'
    )
    parser.add_argument(
        '--apenas-receber',
        action='store_true',
        help='Executar apenas o fluxo de Contas a Receber'
    )
    args = parser.parse_args()

    dry_run = not args.execute

    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("BACKFILL MARCO ZERO: TÍTULOS PAGOS NO ODOO")
        print("=" * 70)

        if dry_run:
            print("MODO DRY-RUN: Nenhuma alteração será salva")
        else:
            print("MODO EXECUÇÃO: As alterações serão salvas no banco!")

        print()

        # Conectar ao Odoo
        logger.info("Conectando ao Odoo...")
        connection = get_odoo_connection()
        if not connection.authenticate():
            logger.error("Falha na autenticação com Odoo")
            sys.exit(1)
        logger.info("Conectado ao Odoo com sucesso")

        stats_pagar = None
        stats_receber = None

        # Executar backfills
        if not args.apenas_receber:
            stats_pagar = backfill_contas_a_pagar(connection, dry_run=dry_run)

        if not args.apenas_pagar:
            stats_receber = backfill_contas_a_receber(connection, dry_run=dry_run)

        # Relatório final
        print("\n" + "=" * 70)
        print("RELATÓRIO FINAL")
        print("=" * 70)

        if stats_pagar:
            print(f"\nCONTAS A PAGAR:")
            print(f"  Verificados:    {stats_pagar['total_verificados']}")
            print(f"  Atualizados:    {stats_pagar['atualizados']}")
            print(f"  Em aberto:      {stats_pagar['ja_em_aberto']}")
            print(f"  Sem match Odoo: {stats_pagar['sem_match_odoo']}")
            print(f"  Erros:          {stats_pagar['erros']}")

        if stats_receber:
            print(f"\nCONTAS A RECEBER:")
            print(f"  Verificados:      {stats_receber['total_verificados']}")
            print(f"  Path A (line_id): {stats_receber['path_a_total']} → {stats_receber['path_a_atualizados']} atualizados, {stats_receber['path_a_em_aberto']} em aberto")
            print(f"  Path B (NF):      {stats_receber['path_b_total']} → {stats_receber['path_b_atualizados']} atualizados")
            print(f"  Total atualiz.:   {stats_receber['atualizados']}")
            print(f"  Sem match Odoo:   {stats_receber['sem_match_odoo']}")
            print(f"  Erros:            {stats_receber['erros']}")

        total_atualizados = (
            (stats_pagar['atualizados'] if stats_pagar else 0) +
            (stats_receber['atualizados'] if stats_receber else 0)
        )

        print(f"\nTOTAL ATUALIZADOS: {total_atualizados}")

        if dry_run:
            print("\nDRY-RUN: Nenhuma alteração foi aplicada.")
            print("Execute com --execute para aplicar as mudanças.")
        else:
            print(f"\n{total_atualizados} títulos atualizados com sucesso.")


if __name__ == '__main__':
    main()
