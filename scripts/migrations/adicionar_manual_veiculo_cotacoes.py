"""
Adiciona campos para cotacao manual e veiculo (carga direta) na tabela carvia_cotacoes.

Campos:
- cotacao_manual: BOOLEAN NOT NULL DEFAULT FALSE — indica cotacao com valor definido manualmente
- valor_manual: NUMERIC(15,2) — valor informado manualmente (quando cotacao_manual=True)
- veiculo_id: INTEGER FK veiculos(id) — veiculo selecionado para carga direta
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_coluna_existe(coluna: str) -> bool:
    result = db.session.execute(db.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = :col
    """), {'col': coluna})
    return result.fetchone() is not None


def verificar_indice_existe(indice: str) -> bool:
    result = db.session.execute(db.text("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'carvia_cotacoes' AND indexname = :idx
    """), {'idx': indice})
    return result.fetchone() is not None


def run():
    app = create_app()
    with app.app_context():
        print("=== BEFORE ===")
        for col in ('cotacao_manual', 'valor_manual', 'veiculo_id'):
            existe = verificar_coluna_existe(col)
            print(f"  {col}: {'EXISTS' if existe else 'NOT FOUND'}")

        colunas = [
            ('cotacao_manual', 'BOOLEAN NOT NULL DEFAULT FALSE'),
            ('valor_manual', 'NUMERIC(15,2)'),
            ('veiculo_id', 'INTEGER REFERENCES veiculos(id)'),
        ]

        adicionadas = 0
        for nome, tipo in colunas:
            if verificar_coluna_existe(nome):
                print(f"  [SKIP] {nome} ja existe.")
                continue
            db.session.execute(db.text(
                f"ALTER TABLE carvia_cotacoes ADD COLUMN {nome} {tipo}"
            ))
            print(f"  [ADD] {nome} {tipo}")
            adicionadas += 1

        # Indice para veiculo_id
        idx_name = 'ix_carvia_cotacoes_veiculo_id'
        if not verificar_indice_existe(idx_name):
            db.session.execute(db.text(
                f"CREATE INDEX {idx_name} ON carvia_cotacoes (veiculo_id)"
            ))
            print(f"  [ADD INDEX] {idx_name}")

        if adicionadas > 0:
            db.session.commit()
            print(f"\n{adicionadas} coluna(s) adicionada(s) com sucesso.")
        else:
            db.session.commit()  # commit do indice se necessario
            print("\nNenhuma coluna adicionada (todas ja existiam).")

        print("\n=== AFTER ===")
        for col in ('cotacao_manual', 'valor_manual', 'veiculo_id'):
            existe = verificar_coluna_existe(col)
            print(f"  {col}: {'EXISTS' if existe else 'NOT FOUND'}")


if __name__ == '__main__':
    run()
