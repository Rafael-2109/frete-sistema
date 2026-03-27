"""
Migration: Colunas valor em cotacao_motos + categorias de moto + vinculacao
Data: 2026-03-27
Motivo:
  1. Model CarviaCotacaoMoto declara valor_unitario e valor_total mas migration original nao incluiu.
     Causa erro 500 em /carvia/cotacoes/<id> (Sentry: ProgrammingError UndefinedColumn).
  2. Cadastrar 5 categorias de moto (Leve, Medio, Pesado, Bike, Patinete).
  3. Vincular modelos existentes as categorias por peso medio.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db

# Classificacao por peso medio (kg)
CATEGORIAS = {
    'Patinete': {'descricao': 'Patinetes eletricos (Patinete, G5)', 'ordem': 5},
    'Bike':     {'descricao': 'Bicicletas eletricas (Bike)', 'ordem': 4},
    'Leve':     {'descricao': 'Ate 140 kg (MCQ3, POP, Joy Super, X12, MC20, X11 Mini, Bob)', 'ordem': 1},
    'Medio':    {'descricao': '140 a 190 kg (Ret, Soma, Joy Tri, Mia, Dot, Giga, Sofia, Jet, X15, S8)', 'ordem': 2},
    'Pesado':   {'descricao': 'Acima de 190 kg (Big Tri, Jetmax, Roma, Rome, Ved, Mia Tri)', 'ordem': 3},
}

VINCULOS = {
    'Patinete': ['PATINETE', 'G5'],
    'Bike':     ['BIKE'],
    'Leve':     ['MCQ3', 'POP', 'JOY SUPER', 'X12', 'MC20', 'X11 MINI', 'BOB'],
    'Medio':    ['RET', 'SOMA', 'JOY TRI', 'MIA', 'DOT', 'GIGA', 'SOFIA', 'JET', 'X15', 'S8'],
    'Pesado':   ['BIG TRI', 'JETMAX', 'ROMA', 'ROME', 'VED', 'MIA TRI'],
}


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    # Colunas cotacao_motos
    for coluna in ['valor_unitario', 'valor_total']:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = 'carvia_cotacao_motos' "
            f"  AND column_name = '{coluna}'"
            ")"
        ))
        print(f"[ANTES] carvia_cotacao_motos.{coluna} existe: {result.scalar()}")

    # Categorias
    result = conn.execute(db.text(
        "SELECT COUNT(*) FROM carvia_categorias_moto"
    ))
    print(f"[ANTES] Categorias existentes: {result.scalar()}")

    # Modelos sem categoria
    result = conn.execute(db.text(
        "SELECT COUNT(*) FROM carvia_modelos_moto WHERE categoria_moto_id IS NULL AND ativo = true"
    ))
    print(f"[ANTES] Modelos ativos sem categoria: {result.scalar()}")


def executar_migration(conn):
    """Executa DDL + DML"""
    # 1. Colunas faltantes
    conn.execute(db.text("""
        ALTER TABLE carvia_cotacao_motos
            ADD COLUMN IF NOT EXISTS valor_unitario NUMERIC(15,2),
            ADD COLUMN IF NOT EXISTS valor_total NUMERIC(15,2)
    """))
    print("[OK] Colunas valor_unitario e valor_total adicionadas")

    # 2. Categorias
    for nome, info in CATEGORIAS.items():
        result = conn.execute(db.text(
            "SELECT id FROM carvia_categorias_moto WHERE nome = :nome"
        ), {'nome': nome})
        if result.fetchone():
            print(f"[SKIP] Categoria '{nome}' ja existe")
            continue

        conn.execute(db.text("""
            INSERT INTO carvia_categorias_moto (nome, descricao, ordem, ativo, criado_em, criado_por)
            VALUES (:nome, :descricao, :ordem, true, NOW(), 'rafael')
        """), {'nome': nome, 'descricao': info['descricao'], 'ordem': info['ordem']})
        print(f"[OK] Categoria '{nome}' criada")

    # 3. Vincular modelos
    for cat_nome, modelos in VINCULOS.items():
        cat_id_row = conn.execute(db.text(
            "SELECT id FROM carvia_categorias_moto WHERE nome = :nome"
        ), {'nome': cat_nome}).fetchone()
        if not cat_id_row:
            print(f"[ERRO] Categoria '{cat_nome}' nao encontrada")
            continue

        cat_id = cat_id_row[0]
        for modelo_nome in modelos:
            result = conn.execute(db.text("""
                UPDATE carvia_modelos_moto
                SET categoria_moto_id = :cat_id
                WHERE nome = :nome AND categoria_moto_id IS NULL
            """), {'cat_id': cat_id, 'nome': modelo_nome})
            if result.rowcount > 0:
                print(f"[OK] {modelo_nome} → {cat_nome}")
            else:
                print(f"[SKIP] {modelo_nome} (ja vinculado ou nao encontrado)")


def verificar_depois(conn):
    """Verifica estado apos migration"""
    for coluna in ['valor_unitario', 'valor_total']:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = 'carvia_cotacao_motos' "
            f"  AND column_name = '{coluna}'"
            ")"
        ))
        print(f"[DEPOIS] carvia_cotacao_motos.{coluna} existe: {result.scalar()}")

    result = conn.execute(db.text(
        "SELECT nome, id FROM carvia_categorias_moto ORDER BY ordem"
    ))
    print("[DEPOIS] Categorias:")
    for row in result:
        print(f"  {row[0]} (id={row[1]})")

    result = conn.execute(db.text("""
        SELECT m.nome, c.nome AS categoria
        FROM carvia_modelos_moto m
        LEFT JOIN carvia_categorias_moto c ON c.id = m.categoria_moto_id
        WHERE m.ativo = true
        ORDER BY c.ordem NULLS LAST, m.nome
    """))
    print("[DEPOIS] Modelos vinculados:")
    for row in result:
        print(f"  {row[0]} → {row[1] or 'SEM CATEGORIA'}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: Colunas valor + Categorias moto + Vinculos")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
