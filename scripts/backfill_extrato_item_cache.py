# -*- coding: utf-8 -*-
"""
Backfill: Preencher campos cache de ExtratoItem
================================================

Corrige itens que têm titulo_pagar_id preenchido mas campos cache vazios
(titulo_valor, titulo_vencimento, titulo_cliente, titulo_cnpj).

Causa raiz: sync_comprovante_para_extrato não preenchia esses campos.

Uso:
    source .venv/bin/activate
    python scripts/backfill_extrato_item_cache.py [--dry-run]

Autor: Sistema de Fretes
Data: 2026-02-10
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.financeiro.models import ExtratoItem, ContasAPagar


def backfill_cache(dry_run: bool = False) -> dict:
    """
    Preenche campos cache para itens com titulo_pagar_id mas titulo_valor IS NULL.

    Returns:
        Dict com estatísticas
    """
    # Buscar itens com FK preenchida mas cache vazio
    itens = ExtratoItem.query.filter(
        ExtratoItem.titulo_pagar_id.isnot(None),
        ExtratoItem.titulo_valor.is_(None),
    ).all()

    stats = {
        'encontrados': len(itens),
        'atualizados': 0,
        'titulo_nao_encontrado': 0,
    }

    print(f"Itens com titulo_pagar_id mas sem cache: {len(itens)}")

    for item in itens:
        titulo = db.session.get(ContasAPagar, item.titulo_pagar_id)
        if not titulo:
            stats['titulo_nao_encontrado'] += 1
            print(f"  [WARN] Item {item.id}: titulo_pagar_id={item.titulo_pagar_id} nao encontrado")
            continue

        print(
            f"  Item {item.id}: titulo_pagar_id={item.titulo_pagar_id} "
            f"→ valor={titulo.valor_residual}, venc={titulo.vencimento}, "
            f"fornecedor={titulo.raz_social_red or titulo.raz_social}"
        )

        if not dry_run:
            item.titulo_valor = titulo.valor_residual
            item.titulo_vencimento = titulo.vencimento
            item.titulo_cliente = titulo.raz_social_red or titulo.raz_social
            item.titulo_cnpj = titulo.cnpj

        stats['atualizados'] += 1

    if not dry_run and stats['atualizados'] > 0:
        db.session.commit()
        print(f"\nCommit realizado: {stats['atualizados']} itens atualizados")
    elif dry_run:
        print(f"\n[DRY-RUN] {stats['atualizados']} itens seriam atualizados")
    else:
        print("\nNenhum item para atualizar")

    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill cache de ExtratoItem')
    parser.add_argument('--dry-run', action='store_true', help='Simular sem gravar')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        resultado = backfill_cache(dry_run=args.dry_run)
        print(f"\nResultado: {resultado}")
