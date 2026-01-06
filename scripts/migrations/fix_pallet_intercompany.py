"""
Script para desativar movimentacoes de pallet intercompany (Nacom/La Famiglia)

Essas NFs nao devem ser controladas pois sao entre empresas do grupo.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

# Prefixos CNPJ das empresas do grupo
CNPJS_INTERCOMPANY_PREFIXOS = [
    '61724241',  # Nacom Goya (matriz e filiais)
    '18467441',  # La Famiglia
]


def identificar_intercompany():
    """Identifica movimentacoes de pallet intercompany"""
    app = create_app()
    with app.app_context():
        # Criar pattern para LIKE
        patterns = " OR ".join([f"cnpj_destinatario LIKE '{p}%'" for p in CNPJS_INTERCOMPANY_PREFIXOS])

        resultado = db.session.execute(text(f"""
            SELECT
                id,
                numero_nf,
                tipo_movimentacao,
                cnpj_destinatario,
                nome_destinatario,
                qtd_movimentacao,
                data_movimentacao
            FROM movimentacao_estoque
            WHERE local_movimentacao = 'PALLET'
              AND ativo = TRUE
              AND ({patterns})
            ORDER BY data_movimentacao DESC
        """))

        registros = resultado.fetchall()

        if not registros:
            print("Nenhum registro intercompany encontrado.")
            return []

        print(f"\n{'='*80}")
        print(f"REGISTROS INTERCOMPANY ENCONTRADOS: {len(registros)}")
        print(f"{'='*80}\n")

        for r in registros:
            print(f"ID {r.id}: NF {r.numero_nf} | {r.tipo_movimentacao} | {r.nome_destinatario} | {int(r.qtd_movimentacao)} pallets")

        return [r.id for r in registros]


def desativar_intercompany(ids, dry_run=True):
    """Desativa registros intercompany"""
    if not ids:
        print("Nenhum registro para desativar.")
        return

    app = create_app()
    with app.app_context():
        if dry_run:
            print(f"\n[DRY RUN] Seriam desativados {len(ids)} registros intercompany")
            print(f"  IDs: {ids}")
            print("\nPara executar de verdade, rode com --execute")
            return

        try:
            resultado = db.session.execute(text("""
                UPDATE movimentacao_estoque
                SET ativo = FALSE,
                    observacao = COALESCE(observacao, '') || ' [DESATIVADO - INTERCOMPANY]'
                WHERE id = ANY(:ids)
            """), {'ids': ids})

            db.session.commit()
            print(f"\n✅ {resultado.rowcount} registros desativados com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao desativar registros: {e}")


if __name__ == '__main__':
    print("=" * 80)
    print("DESATIVAR MOVIMENTACOES INTERCOMPANY (Nacom/La Famiglia)")
    print("=" * 80)

    ids = identificar_intercompany()

    if ids:
        dry_run = '--execute' not in sys.argv
        desativar_intercompany(ids, dry_run=dry_run)
