#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Limpar registros intercompany de contas_a_pagar e contas_a_receber
==================================================================

O filtro intercompany foi adicionado em:
- sincronizacao_contas_pagar_service.py:508
- contas_receber_service.py:314

Registros importados ANTES do fix ainda existem. Este script remove.

CNPJs do grupo Nacom:
- 61.724.241 (Nacom Goya — matriz e filiais)
- 18.467.441 (La Famiglia)

Dependencias FK:
- extrato_item_titulo.titulo_pagar_id   → contas_a_pagar.id
- extrato_item_titulo.titulo_receber_id → contas_a_receber.id
- contas_a_receber_reconciliacao.conta_a_receber_id → contas_a_receber.id
- baixa_pagamento_item.titulo_id → Odoo line ID (NAO FK local — nao precisa limpar)

Uso:
    # Dry-run (padrao): apenas mostra contagens
    python scripts/migrations/limpar_intercompany_contas.py

    # Executar limpeza de fato
    python scripts/migrations/limpar_intercompany_contas.py --execute

Autor: Sistema de Fretes
Data: 2026-02-23
"""

import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

logger = logging.getLogger(__name__)

# CNPJs raiz do grupo Nacom (formatado e sem formatacao para seguranca)
# FONTE: sincronizacao_contas_pagar_service.py:35
# FONTE: .claude/references/odoo/IDS_FIXOS.md:18-25
CNPJ_PATTERNS = [
    '61.724.241%',  # Nacom Goya (formatado)
    '18.467.441%',  # La Famiglia (formatado)
    '61724241%',    # Nacom Goya (sem formatacao — registros antigos)
    '18467441%',    # La Famiglia (sem formatacao — registros antigos)
]

# Clausula WHERE reutilizavel
CNPJ_WHERE = " OR ".join([f"cnpj LIKE :p{i}" for i in range(len(CNPJ_PATTERNS))])
CNPJ_PARAMS = {f"p{i}": p for i, p in enumerate(CNPJ_PATTERNS)}


def verificar_contagens():
    """Fase 1: Verificacao — mostra contagens antes do cleanup."""
    print("\n" + "=" * 70)
    print("FASE 1: VERIFICACAO PRE-CLEANUP")
    print("=" * 70)

    checks = [
        (
            "contas_a_pagar intercompany",
            f"SELECT COUNT(*) FROM contas_a_pagar WHERE {CNPJ_WHERE}",
        ),
        (
            "contas_a_receber intercompany",
            f"SELECT COUNT(*) FROM contas_a_receber WHERE {CNPJ_WHERE}",
        ),
        (
            "extrato_item_titulo (pagar)",
            f"""SELECT COUNT(*) FROM extrato_item_titulo
                WHERE titulo_pagar_id IN (
                    SELECT id FROM contas_a_pagar WHERE {CNPJ_WHERE}
                )""",
        ),
        (
            "extrato_item_titulo (receber)",
            f"""SELECT COUNT(*) FROM extrato_item_titulo
                WHERE titulo_receber_id IN (
                    SELECT id FROM contas_a_receber WHERE {CNPJ_WHERE}
                )""",
        ),
        (
            "contas_a_receber_reconciliacao",
            f"""SELECT COUNT(*) FROM contas_a_receber_reconciliacao
                WHERE conta_a_receber_id IN (
                    SELECT id FROM contas_a_receber WHERE {CNPJ_WHERE}
                )""",
        ),
    ]

    contagens = {}
    for label, sql in checks:
        result = db.session.execute(text(sql), CNPJ_PARAMS).scalar()
        contagens[label] = result
        print(f"  {label}: {result}")

    # Amostra de registros pagar
    amostra_pagar = db.session.execute(text(f"""
        SELECT id, cnpj, raz_social_red, titulo_nf, parcela, empresa
        FROM contas_a_pagar WHERE {CNPJ_WHERE}
        LIMIT 5
    """), CNPJ_PARAMS).fetchall()

    if amostra_pagar:
        print(f"\n  Amostra contas_a_pagar:")
        for r in amostra_pagar:
            print(f"    ID={r[0]} CNPJ={r[1]} Nome={r[2]} NF={r[3]} Parc={r[4]} Emp={r[5]}")

    # Amostra de registros receber
    amostra_receber = db.session.execute(text(f"""
        SELECT id, cnpj, raz_social, titulo_nf, parcela, empresa
        FROM contas_a_receber WHERE {CNPJ_WHERE}
        LIMIT 5
    """), CNPJ_PARAMS).fetchall()

    if amostra_receber:
        print(f"\n  Amostra contas_a_receber:")
        for r in amostra_receber:
            print(f"    ID={r[0]} CNPJ={r[1]} Nome={r[2]} NF={r[3]} Parc={r[4]} Emp={r[5]}")

    return contagens


def executar_cleanup():
    """Fase 2: Cleanup — remove registros intercompany dentro de transacao."""
    print("\n" + "=" * 70)
    print("FASE 2: EXECUTANDO CLEANUP")
    print("=" * 70)

    try:
        # Step 1: Remover vinculos extrato ↔ titulo pagar intercompany
        result = db.session.execute(text(f"""
            DELETE FROM extrato_item_titulo
            WHERE titulo_pagar_id IN (
                SELECT id FROM contas_a_pagar WHERE {CNPJ_WHERE}
            )
        """), CNPJ_PARAMS)
        print(f"  Step 1: {result.rowcount} extrato_item_titulo (pagar) removidos")

        # Step 2: Remover vinculos extrato ↔ titulo receber intercompany
        result = db.session.execute(text(f"""
            DELETE FROM extrato_item_titulo
            WHERE titulo_receber_id IN (
                SELECT id FROM contas_a_receber WHERE {CNPJ_WHERE}
            )
        """), CNPJ_PARAMS)
        print(f"  Step 2: {result.rowcount} extrato_item_titulo (receber) removidos")

        # Step 3: Remover reconciliacoes de receber intercompany
        result = db.session.execute(text(f"""
            DELETE FROM contas_a_receber_reconciliacao
            WHERE conta_a_receber_id IN (
                SELECT id FROM contas_a_receber WHERE {CNPJ_WHERE}
            )
        """), CNPJ_PARAMS)
        print(f"  Step 3: {result.rowcount} contas_a_receber_reconciliacao removidos")

        # Step 4: Remover contas a pagar intercompany
        result = db.session.execute(text(f"""
            DELETE FROM contas_a_pagar WHERE {CNPJ_WHERE}
        """), CNPJ_PARAMS)
        print(f"  Step 4: {result.rowcount} contas_a_pagar removidos")

        # Step 5: Remover contas a receber intercompany
        result = db.session.execute(text(f"""
            DELETE FROM contas_a_receber WHERE {CNPJ_WHERE}
        """), CNPJ_PARAMS)
        print(f"  Step 5: {result.rowcount} contas_a_receber removidos")

        db.session.commit()
        print("\n  COMMIT realizado com sucesso!")

    except Exception as e:
        db.session.rollback()
        print(f"\n  ROLLBACK! Erro: {e}")
        raise


def verificar_pos_cleanup():
    """Fase 3: Verificacao pos — deve retornar 0 para ambas."""
    print("\n" + "=" * 70)
    print("FASE 3: VERIFICACAO POS-CLEANUP")
    print("=" * 70)

    pagar = db.session.execute(text(f"""
        SELECT COUNT(*) FROM contas_a_pagar WHERE {CNPJ_WHERE}
    """), CNPJ_PARAMS).scalar()

    receber = db.session.execute(text(f"""
        SELECT COUNT(*) FROM contas_a_receber WHERE {CNPJ_WHERE}
    """), CNPJ_PARAMS).scalar()

    print(f"  contas_a_pagar intercompany:  {pagar}")
    print(f"  contas_a_receber intercompany: {receber}")

    if pagar == 0 and receber == 0:
        print("\n  Cleanup completo! Nenhum registro intercompany restante.")
    else:
        print(f"\n  ATENCAO: Ainda restam registros! Pagar={pagar}, Receber={receber}")


def main():
    print("=" * 70)
    print("LIMPAR REGISTROS INTERCOMPANY (Nacom/La Famiglia)")
    print("=" * 70)
    print(f"  CNPJ patterns: {CNPJ_PATTERNS}")

    execute = '--execute' in sys.argv

    app = create_app()
    with app.app_context():
        # Fase 1: Verificacao
        contagens = verificar_contagens()

        total_pais = (
            contagens.get("contas_a_pagar intercompany", 0)
            + contagens.get("contas_a_receber intercompany", 0)
        )

        if total_pais == 0:
            print("\n  Nenhum registro intercompany encontrado. Nada a fazer.")
            return

        if not execute:
            print("\n" + "-" * 70)
            print("  [DRY RUN] Nenhuma alteracao realizada.")
            print("  Para executar de fato, rode com: --execute")
            print("-" * 70)
            return

        # Fase 2: Cleanup
        executar_cleanup()

        # Fase 3: Verificacao pos
        verificar_pos_cleanup()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    main()
