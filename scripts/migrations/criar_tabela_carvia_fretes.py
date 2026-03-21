"""
Migration: Criar tabela carvia_fretes + FK frete_id em custos_entrega e cte_complementares
=============================================================================================

1. Tabela carvia_fretes — frete CarVia por (embarque_id, cnpj_emitente, cnpj_destino)
   - 4 valores CUSTO (cotado, cte, considerado, pago) + valor_venda
   - Unique (embarque_id, cnpj_emitente, cnpj_destino)
   - FKs: subcontrato, operacao, faturas
2. Campo frete_id em carvia_custos_entrega
3. Campo frete_id em carvia_cte_complementares

Uso: python scripts/migrations/criar_tabela_carvia_fretes.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_fretes'
        )
    """))
    existe = result.scalar()
    print(f"[ANTES] Tabela carvia_fretes existe: {existe}")

    for tabela, campo in [('carvia_custos_entrega', 'frete_id'), ('carvia_cte_complementares', 'frete_id')]:
        result = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{tabela}' AND column_name = '{campo}'
            )
        """))
        print(f"[ANTES] {tabela}.{campo} existe: {result.scalar()}")

    return existe


def _extrair_statements(sql):
    """Extrai statements SQL respeitando blocos DO $$ ... END $$."""
    statements = []
    current = []
    in_dollar_block = False

    for line in sql.split('\n'):
        stripped = line.strip()

        # Ignorar linhas de comentario puro
        if stripped.startswith('--') and not in_dollar_block:
            continue

        if not stripped:
            continue

        # Detectar inicio/fim de bloco DO $$
        if 'DO $$' in stripped and not in_dollar_block:
            in_dollar_block = True
            current.append(line)
            continue

        if in_dollar_block:
            current.append(line)
            if stripped.startswith('END $$'):
                # Bloco completo
                statements.append('\n'.join(current))
                current = []
                in_dollar_block = False
            continue

        # Statement normal
        current.append(line)
        if stripped.endswith(';'):
            stmt = '\n'.join(current).strip().rstrip(';').strip()
            if stmt:
                statements.append(stmt)
            current = []

    # Residuo
    if current:
        stmt = '\n'.join(current).strip().rstrip(';').strip()
        if stmt:
            statements.append(stmt)

    return statements


def executar_migration():
    """Executa a migration lendo do arquivo SQL."""
    sql_path = os.path.join(os.path.dirname(__file__), 'criar_tabela_carvia_fretes.sql')
    with open(sql_path, 'r') as f:
        sql = f.read()

    statements = _extrair_statements(sql)
    for i, stmt in enumerate(statements):
        try:
            db.session.execute(text(stmt))
            print(f"  [OK] Statement {i + 1}/{len(statements)}")
        except Exception as e:
            print(f"  [ERRO] Statement {i + 1}: {str(e)[:120]}")
            raise

    db.session.commit()
    print("[OK] Migration executada com sucesso")


def verificar_depois():
    """Verifica estado apos a migration."""
    result = db.session.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'carvia_fretes'
        ORDER BY ordinal_position
    """))
    cols = [(r[0], r[1]) for r in result]
    print(f"[DEPOIS] carvia_fretes: {len(cols)} colunas")
    for nome, tipo in cols:
        print(f"  {nome}: {tipo}")

    # Verificar unique constraint
    result = db.session.execute(text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'carvia_fretes' AND constraint_type = 'UNIQUE'
    """))
    for r in result:
        print(f"[DEPOIS] UNIQUE: {r[0]}")

    # Verificar frete_id nas tabelas filhas
    for tabela in ['carvia_custos_entrega', 'carvia_cte_complementares']:
        result = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{tabela}' AND column_name = 'frete_id'
            )
        """))
        print(f"[DEPOIS] {tabela}.frete_id existe: {result.scalar()}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: criar_tabela_carvia_fretes")
        print("=" * 60)

        existe = verificar_antes()

        if existe:
            print("[SKIP] Tabela carvia_fretes ja existe. Verificando FKs...")
            # Mesmo que tabela exista, FKs podem nao existir
            executar_migration()
        else:
            executar_migration()

        verificar_depois()
        print("[CONCLUIDO]")
