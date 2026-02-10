# -*- coding: utf-8 -*-
"""
Script de limpeza de itens duplicados em baixa_titulo_item.
============================================================

Contexto (2026-02-10):
- 167 itens duplicados (99 grupos), todos com status ERRO
- Mesma NF+parcela+journal importados multiplas vezes
- Nenhum duplicado com SUCESSO (nao ha pagamentos a reverter)

Logica:
1. Agrupar por (nf_excel, parcela_excel, journal_excel) onde status=ERRO e COUNT>1
2. Para cada grupo: manter item com maior ID (mais recente)
3. Inativar os demais: ativo=False, mensagem atualizada
4. Logar cada grupo processado

Uso:
    source .venv/bin/activate
    python scripts/limpar_duplicados_baixa.py [--dry-run]
"""

import argparse
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.financeiro.models import BaixaTituloItem
from sqlalchemy import func


def limpar_duplicados(dry_run: bool = False):
    """
    Remove duplicados de baixa_titulo_item mantendo o item mais recente (maior ID).
    """
    app = create_app()

    with app.app_context():
        # 1. Encontrar grupos duplicados (status=ERRO, agrupados por nf+parcela+journal)
        grupos = (
            db.session.query(
                BaixaTituloItem.nf_excel,
                BaixaTituloItem.parcela_excel,
                BaixaTituloItem.journal_excel,
                func.count(BaixaTituloItem.id).label('qtd'),
                func.max(BaixaTituloItem.id).label('max_id')
            )
            .filter(
                BaixaTituloItem.status == 'ERRO',
                BaixaTituloItem.ativo == True
            )
            .group_by(
                BaixaTituloItem.nf_excel,
                BaixaTituloItem.parcela_excel,
                BaixaTituloItem.journal_excel
            )
            .having(func.count(BaixaTituloItem.id) > 1)
            .all()
        )

        total_grupos = len(grupos)
        total_inativados = 0
        data_limpeza = date.today().strftime('%d/%m/%Y')

        print(f"{'[DRY-RUN] ' if dry_run else ''}Encontrados {total_grupos} grupos com duplicatas")
        print("=" * 70)

        for grupo in grupos:
            nf = grupo.nf_excel
            parcela = grupo.parcela_excel
            journal = grupo.journal_excel
            qtd = grupo.qtd
            manter_id = grupo.max_id

            # Buscar itens duplicados (todos exceto o mais recente)
            duplicados = BaixaTituloItem.query.filter(
                BaixaTituloItem.nf_excel == nf,
                BaixaTituloItem.parcela_excel == parcela,
                BaixaTituloItem.journal_excel == journal,
                BaixaTituloItem.status == 'ERRO',
                BaixaTituloItem.ativo == True,
                BaixaTituloItem.id != manter_id
            ).all()

            ids_inativados = []
            for item in duplicados:
                if not dry_run:
                    item.ativo = False
                    item.mensagem = f"Duplicidade removida automaticamente (limpeza {data_limpeza})"
                ids_inativados.append(item.id)
                total_inativados += 1

            print(f"  NF {nf} P{parcela} [{journal}]: {qtd} itens -> manter ID {manter_id}, inativar {ids_inativados}")

        if not dry_run and total_inativados > 0:
            db.session.commit()
            print("=" * 70)
            print(f"COMMIT realizado. {total_inativados} itens inativados em {total_grupos} grupos.")
        elif dry_run:
            print("=" * 70)
            print(f"[DRY-RUN] Seriam inativados {total_inativados} itens em {total_grupos} grupos.")
            print("[DRY-RUN] Execute sem --dry-run para aplicar as mudancas.")
        else:
            print("=" * 70)
            print("Nenhum duplicado encontrado. Nada a fazer.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Limpa itens duplicados de baixa_titulo_item')
    parser.add_argument('--dry-run', action='store_true', help='Simula sem alterar o banco')
    args = parser.parse_args()

    limpar_duplicados(dry_run=args.dry_run)
