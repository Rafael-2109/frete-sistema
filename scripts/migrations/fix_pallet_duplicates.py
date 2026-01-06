"""
Script para corrigir duplicatas de pallet (mesma NF como REMESSA e SAIDA)

O problema: sincronizacao de vendas criava SAIDA para NFs que ja eram REMESSA
(tipo vasilhame), resultando na mesma NF aparecendo duas vezes.

Solucao: Remover registros SAIDA que tem a mesma NF de um registro REMESSA existente.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def identificar_duplicatas():
    """Identifica NFs que aparecem como REMESSA e SAIDA"""
    app = create_app()
    with app.app_context():
        resultado = db.session.execute(text("""
            SELECT
                r.numero_nf,
                r.id as remessa_id,
                r.nome_destinatario as remessa_dest,
                r.qtd_movimentacao as remessa_qtd,
                s.id as saida_id,
                s.nome_destinatario as saida_dest,
                s.qtd_movimentacao as saida_qtd
            FROM movimentacao_estoque r
            JOIN movimentacao_estoque s ON r.numero_nf = s.numero_nf
            WHERE r.local_movimentacao = 'PALLET'
              AND s.local_movimentacao = 'PALLET'
              AND r.tipo_movimentacao = 'REMESSA'
              AND s.tipo_movimentacao = 'SAIDA'
              AND r.ativo = TRUE
              AND s.ativo = TRUE
            ORDER BY r.numero_nf
        """))

        duplicatas = resultado.fetchall()

        if not duplicatas:
            print("Nenhuma duplicata encontrada.")
            return []

        print(f"\n{'='*80}")
        print(f"DUPLICATAS ENCONTRADAS: {len(duplicatas)}")
        print(f"{'='*80}\n")

        for d in duplicatas:
            print(f"NF: {d.numero_nf}")
            print(f"  REMESSA (ID {d.remessa_id}): {d.remessa_dest} - {int(d.remessa_qtd)} pallets")
            print(f"  SAIDA   (ID {d.saida_id}): {d.saida_dest} - {int(d.saida_qtd)} pallets")
            print()

        return [d.saida_id for d in duplicatas]


def remover_duplicatas(saida_ids, dry_run=True):
    """Remove registros SAIDA duplicados"""
    if not saida_ids:
        print("Nenhum registro para remover.")
        return

    app = create_app()
    with app.app_context():
        if dry_run:
            print(f"\n[DRY RUN] Seriam removidos {len(saida_ids)} registros SAIDA:")
            print(f"  IDs: {saida_ids}")
            print("\nPara executar de verdade, rode com --execute")
            return

        try:
            # Desativar (soft delete) em vez de deletar
            resultado = db.session.execute(text("""
                UPDATE movimentacao_estoque
                SET ativo = FALSE,
                    observacao = COALESCE(observacao, '') || ' [DUPLICATA REMOVIDA - era REMESSA]'
                WHERE id = ANY(:ids)
            """), {'ids': saida_ids})

            db.session.commit()
            print(f"\n✅ {resultado.rowcount} registros desativados com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao remover duplicatas: {e}")


if __name__ == '__main__':
    print("=" * 80)
    print("CORRECAO DE DUPLICATAS DE PALLET")
    print("=" * 80)

    saida_ids = identificar_duplicatas()

    if saida_ids:
        dry_run = '--execute' not in sys.argv
        remover_duplicatas(saida_ids, dry_run=dry_run)
