"""
Fix: Desativar registros duplicados de movimentacao de pallet.

Problema: O ProcessadorFaturamento criava registros FATURAMENTO/VENDA para o produto
208000012 (PALLET), duplicando os registros SAIDA/PALLET criados pelo PalletSyncService.

Este script desativa os 5 registros FATURAMENTO/VENDA que possuem par SAIDA/PALLET,
mantendo apenas o registro enriquecido (com CNPJ, nome comprador, valor).

IDs a desativar: 30932, 45018, 56113, 61354, 67596

Executar no Render Shell:
    python scripts/pallet/fix_duplicacao_movimentacao_pallet.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def fix_duplicacao():
    app = create_app()
    with app.app_context():
        # IDs confirmados como duplicados (FATURAMENTO/VENDA com par SAIDA/PALLET existente)
        ids_duplicados = [30932, 45018, 56113, 61354, 67596]

        # Verificar antes de desativar
        resultado = db.session.execute(text("""
            SELECT id, numero_nf, tipo_movimentacao, local_movimentacao, qtd_movimentacao, ativo
            FROM movimentacao_estoque
            WHERE id IN :ids
        """), {'ids': tuple(ids_duplicados)})

        registros = resultado.fetchall()
        print(f"Registros encontrados: {len(registros)}")
        for r in registros:
            print(f"  ID {r.id}: NF {r.numero_nf} | {r.tipo_movimentacao}/{r.local_movimentacao} | qtd={r.qtd_movimentacao} | ativo={r.ativo}")

        # Confirmar que todos sao FATURAMENTO/VENDA e ativos
        for r in registros:
            if r.tipo_movimentacao != 'FATURAMENTO' or r.local_movimentacao != 'VENDA':
                print(f"\n  ERRO: ID {r.id} nao e FATURAMENTO/VENDA! Abortando.")
                return
            if not r.ativo:
                print(f"\n  AVISO: ID {r.id} ja esta inativo. Pulando.")

        # Desativar
        atualizado = db.session.execute(text("""
            UPDATE movimentacao_estoque
            SET ativo = false,
                atualizado_em = NOW(),
                atualizado_por = 'FIX_DUPLICACAO_PALLET'
            WHERE id IN :ids
              AND ativo = true
        """), {'ids': tuple(ids_duplicados)})

        db.session.commit()
        print(f"\n{atualizado.rowcount} registros desativados com sucesso.")


if __name__ == '__main__':
    fix_duplicacao()
