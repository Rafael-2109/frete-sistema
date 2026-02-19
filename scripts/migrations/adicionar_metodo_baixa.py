"""
Migration: Adicionar coluna metodo_baixa em contas_a_receber e contas_a_pagar.

Rastreabilidade: indica COMO o titulo foi baixado.
Valores: CNAB, EXCEL, COMPROVANTE, EXTRATO, ODOO_DIRETO

Executar: source .venv/bin/activate && python scripts/migrations/adicionar_metodo_baixa.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se coluna existe na tabela."""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = :tabela AND column_name = :coluna"
        ")"
    ), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def verificar_indice_existe(conn, nome_indice):
    """Verifica se indice existe."""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM pg_indexes WHERE indexname = :nome"
        ")"
    ), {'nome': nome_indice})
    return result.scalar()


def main():
    app = create_app()

    with app.app_context():
        # ── BEFORE ──
        print("=" * 60)
        print("BEFORE: Verificando estado atual")
        print("=" * 60)

        with db.engine.connect() as conn:
            for tabela in ['contas_a_receber', 'contas_a_pagar']:
                existe = verificar_coluna_existe(conn, tabela, 'metodo_baixa')
                print(f"  {tabela}.metodo_baixa: {'JA EXISTE' if existe else 'NAO EXISTE'}")

            for idx in ['idx_conta_receber_metodo_baixa', 'idx_conta_pagar_metodo_baixa']:
                existe = verificar_indice_existe(conn, idx)
                print(f"  Indice {idx}: {'JA EXISTE' if existe else 'NAO EXISTE'}")

        # ── EXECUTE ──
        print("\n" + "=" * 60)
        print("EXECUTE: Adicionando colunas e indices")
        print("=" * 60)

        with db.engine.begin() as conn:
            # Adicionar colunas
            conn.execute(db.text(
                "ALTER TABLE contas_a_receber ADD COLUMN IF NOT EXISTS metodo_baixa VARCHAR(30)"
            ))
            print("  + contas_a_receber.metodo_baixa adicionado")

            conn.execute(db.text(
                "ALTER TABLE contas_a_pagar ADD COLUMN IF NOT EXISTS metodo_baixa VARCHAR(30)"
            ))
            print("  + contas_a_pagar.metodo_baixa adicionado")

            # Criar indices
            conn.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_conta_receber_metodo_baixa "
                "ON contas_a_receber (metodo_baixa)"
            ))
            print("  + idx_conta_receber_metodo_baixa criado")

            conn.execute(db.text(
                "CREATE INDEX IF NOT EXISTS idx_conta_pagar_metodo_baixa "
                "ON contas_a_pagar (metodo_baixa)"
            ))
            print("  + idx_conta_pagar_metodo_baixa criado")

        # ── AFTER ──
        print("\n" + "=" * 60)
        print("AFTER: Verificando resultado")
        print("=" * 60)

        with db.engine.connect() as conn:
            ok = True
            for tabela in ['contas_a_receber', 'contas_a_pagar']:
                existe = verificar_coluna_existe(conn, tabela, 'metodo_baixa')
                status = 'OK' if existe else 'FALHOU'
                if not existe:
                    ok = False
                print(f"  {tabela}.metodo_baixa: {status}")

            for idx in ['idx_conta_receber_metodo_baixa', 'idx_conta_pagar_metodo_baixa']:
                existe = verificar_indice_existe(conn, idx)
                status = 'OK' if existe else 'FALHOU'
                if not existe:
                    ok = False
                print(f"  Indice {idx}: {status}")

        if ok:
            print("\nMigration concluida com SUCESSO!")
        else:
            print("\nMigration FALHOU em algum ponto. Verificar logs acima.")
            sys.exit(1)


if __name__ == '__main__':
    main()
