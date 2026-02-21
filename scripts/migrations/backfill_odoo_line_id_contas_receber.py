#!/usr/bin/env python3
"""
Backfill odoo_line_id para contas_a_receber
=============================================

Popula o campo odoo_line_id (account.move.line ID do Odoo) em registros existentes
que foram criados antes da adição desse campo.

Padrão "detach-first" para evitar SSL timeout (limite 30s no Render):
- Fase 1: Lê dados do DB → extrai para plain dicts → fecha session
- Fase 2: Chama Odoo API (sem conexão DB aberta)
- Fase 3: Aplica updates por chunk com commit + close imediato

Executar:
    source .venv/bin/activate
    python scripts/migrations/backfill_odoo_line_id_contas_receber.py              # dry-run
    python scripts/migrations/backfill_odoo_line_id_contas_receber.py --execute    # executa

Data: 21/02/2026
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.financeiro.models import ContasAReceber
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

# Mapeamento inverso: codigo interno -> nome empresa Odoo
EMPRESA_CODIGO_PARA_NOME = {v: k for k, v in EMPRESA_MAP.items()}


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


def backfill_odoo_line_id(connection, dry_run: bool = True) -> dict:
    """
    Popula odoo_line_id em registros de contas_a_receber que não o possuem.

    Usa padrão "detach-first" em 3 fases para evitar SSL timeout:
    - Fase 1: Lê DB → plain dicts → close
    - Fase 2: Odoo API (sem DB)
    - Fase 3: Updates atômicos por chunk

    Args:
        connection: Conexão Odoo autenticada
        dry_run: Se True, não aplica mudanças

    Returns:
        dict com estatísticas
    """
    stats = {
        'total_sem_line_id': 0,
        'atualizados': 0,
        'sem_match_odoo': 0,
        'duplicados_ignorados': 0,
        'erros': 0,
    }

    logger.info("=" * 60)
    logger.info("BACKFILL odoo_line_id — CONTAS A RECEBER")
    logger.info("=" * 60)

    # =========================================================================
    # FASE 1: Ler dados do DB → plain Python → fechar session
    # =========================================================================
    logger.info("\n[FASE 1] Lendo dados do banco...")

    # Extrair para plain tuples (id, empresa, titulo_nf, parcela)
    titulos_raw = db.session.query(
        ContasAReceber.id, ContasAReceber.empresa,
        ContasAReceber.titulo_nf, ContasAReceber.parcela
    ).filter(
        ContasAReceber.odoo_line_id.is_(None)
    ).all()

    stats['total_sem_line_id'] = len(titulos_raw)
    logger.info(f"  {len(titulos_raw)} títulos sem odoo_line_id")

    if not titulos_raw:
        db.session.close()
        return stats

    # Coletar line_ids já existentes para evitar conflito UNIQUE
    existing_raw = db.session.query(ContasAReceber.odoo_line_id).filter(
        ContasAReceber.odoo_line_id.isnot(None)
    ).all()
    line_ids_usados = {r[0] for r in existing_raw}
    logger.info(f"  {len(line_ids_usados)} odoo_line_id já existentes")

    # Fechar session — libera conexão PostgreSQL
    db.session.close()

    # Organizar em plain dicts
    # {(empresa, titulo_nf, parcela): id_local}
    chave_para_id = {}
    por_empresa = {}
    for row_id, empresa, titulo_nf, parcela in titulos_raw:
        chave = (empresa, titulo_nf, parcela)
        chave_para_id.setdefault(chave, []).append(row_id)
        por_empresa.setdefault(empresa, set()).add(titulo_nf)

    # =========================================================================
    # FASE 2: Consultar Odoo API (sem conexão DB aberta)
    # =========================================================================
    logger.info("\n[FASE 2] Consultando Odoo...")

    CHUNK_SIZE = 100
    # Resultado: lista de (id_local, odoo_line_id) para aplicar
    updates_pendentes = []

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
                        'company_id',
                    ],
                    limit=len(chunk_nfs) * 5
                ) or []
            except Exception as e:
                logger.error(f"  ERRO Odoo (chunk {i}): {e}")
                stats['erros'] += len(chunk_nfs)
                continue

            # Match por (empresa, titulo_nf, parcela)
            for rec in dados_odoo:
                line_id = rec.get('id')
                if not line_id:
                    continue

                nf = str(rec.get('x_studio_nf_e') or '').strip()
                if not nf:
                    continue

                parcela = parcela_to_str(rec.get('l10n_br_cobranca_parcela')) or '1'
                company_nome = rec.get('company_id', [None, ''])[1] or ''

                rec_empresa = _mapear_empresa(company_nome)
                if rec_empresa != empresa_cod:
                    continue

                # UNIQUE constraint
                if line_id in line_ids_usados:
                    stats['duplicados_ignorados'] += 1
                    continue

                chave = (empresa_cod, nf, parcela)
                ids_locais = chave_para_id.get(chave, [])

                for id_local in ids_locais:
                    # Marcar para update
                    updates_pendentes.append((id_local, line_id))
                    line_ids_usados.add(line_id)
                    stats['atualizados'] += 1
                    break  # 1:1 — um line_id por título

    logger.info(f"\n  Total de updates coletados: {len(updates_pendentes)}")

    # =========================================================================
    # FASE 3: Aplicar updates atômicos por chunk (commit + close por batch)
    # =========================================================================
    if not dry_run and updates_pendentes:
        logger.info("\n[FASE 3] Aplicando updates...")

        BATCH_SIZE = 200  # Commit a cada 200 — bem dentro dos 30s
        for i in range(0, len(updates_pendentes), BATCH_SIZE):
            batch = updates_pendentes[i:i + BATCH_SIZE]

            try:
                for id_local, line_id in batch:
                    db.session.execute(
                        text("UPDATE contas_a_receber SET odoo_line_id = :line_id WHERE id = :id"),
                        {'line_id': line_id, 'id': id_local}
                    )
                db.session.commit()
                logger.info(
                    f"  Batch {i // BATCH_SIZE + 1}: "
                    f"{len(batch)} updates aplicados (total: {i + len(batch)})"
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

    # Contar sem match
    stats['sem_match_odoo'] = (
        stats['total_sem_line_id'] - stats['atualizados'] - stats['duplicados_ignorados']
    )
    if stats['sem_match_odoo'] < 0:
        stats['sem_match_odoo'] = 0

    logger.info(f"\nRESUMO:")
    logger.info(f"  Sem odoo_line_id: {stats['total_sem_line_id']}")
    logger.info(f"  Atualizados:     {stats['atualizados']}")
    logger.info(f"  Sem match Odoo:  {stats['sem_match_odoo']}")
    logger.info(f"  Duplicados:      {stats['duplicados_ignorados']}")
    logger.info(f"  Erros:           {stats['erros']}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Backfill odoo_line_id em contas_a_receber'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Executar as alterações (default: dry-run)'
    )
    args = parser.parse_args()

    dry_run = not args.execute

    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("BACKFILL odoo_line_id — CONTAS A RECEBER")
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

        stats = backfill_odoo_line_id(connection, dry_run=dry_run)

        # Relatório final
        print("\n" + "=" * 70)
        print("RELATÓRIO FINAL")
        print("=" * 70)
        print(f"  Sem odoo_line_id: {stats['total_sem_line_id']}")
        print(f"  Atualizados:     {stats['atualizados']}")
        print(f"  Sem match Odoo:  {stats['sem_match_odoo']}")
        print(f"  Duplicados:      {stats['duplicados_ignorados']}")
        print(f"  Erros:           {stats['erros']}")

        if dry_run:
            print("\nDRY-RUN: Nenhuma alteração foi aplicada.")
            print("Execute com --execute para aplicar as mudanças.")
        else:
            print(f"\n{stats['atualizados']} títulos atualizados com odoo_line_id.")


if __name__ == '__main__':
    main()
