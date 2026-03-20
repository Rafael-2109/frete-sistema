"""
Migration: Padronizar medidas de modelos de moto para centimetros (CM)
======================================================================

As colunas comprimento/largura/altura de carvia_modelos_moto armazenavam
valores em metros (ex: 1.37 = 1.37m). Esta migration converte para
centimetros (ex: 137 = 137cm) multiplicando por 100.

Idempotencia: WHERE comprimento < 10 AND largura < 10 AND altura < 10
- Moto em M: sempre < 10 (max ~2.5m) → sera multiplicado
- Moto em CM: sempre >= 50 (minimo ~50cm) → nao sera multiplicado

NAO toca em carvia_operacoes.cubagem_* (ja estao em CM).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def verificar_antes(conn):
    """Mostra estado atual dos modelos de moto."""
    result = conn.execute("""
        SELECT id, nome, comprimento, largura, altura
        FROM carvia_modelos_moto
        ORDER BY nome
    """)
    rows = result.fetchall()

    if not rows:
        print("Nenhum modelo de moto encontrado.")
        return False

    print(f"\n{'ID':>4}  {'Nome':<20}  {'Comp':>10}  {'Larg':>10}  {'Alt':>10}  {'Unidade'}")
    print("-" * 75)
    for row in rows:
        # Detectar se ja esta em CM (>= 10) ou ainda em M (< 10)
        unidade = "M (converter)" if row[2] < 10 and row[3] < 10 and row[4] < 10 else "CM (ok)"
        print(f"{row[0]:>4}  {row[1]:<20}  {row[2]:>10.4f}  {row[3]:>10.4f}  {row[4]:>10.4f}  {unidade}")

    em_metros = sum(1 for r in rows if r[2] < 10 and r[3] < 10 and r[4] < 10)
    print(f"\nTotal: {len(rows)} modelos, {em_metros} em metros (a converter)")
    return em_metros > 0


def executar_migration(conn):
    """Multiplica comprimento/largura/altura por 100 onde valores estao em metros."""
    result = conn.execute("""
        UPDATE carvia_modelos_moto
        SET comprimento = comprimento * 100,
            largura = largura * 100,
            altura = altura * 100
        WHERE comprimento < 10
          AND largura < 10
          AND altura < 10
    """)
    print(f"\n{result.rowcount} modelo(s) convertido(s) de metros para centimetros.")
    return result.rowcount


def verificar_depois(conn):
    """Confirma que todos os modelos estao em CM."""
    result = conn.execute("""
        SELECT id, nome, comprimento, largura, altura
        FROM carvia_modelos_moto
        ORDER BY nome
    """)
    rows = result.fetchall()

    print(f"\n{'ID':>4}  {'Nome':<20}  {'Comp (cm)':>10}  {'Larg (cm)':>10}  {'Alt (cm)':>10}")
    print("-" * 65)
    for row in rows:
        print(f"{row[0]:>4}  {row[1]:<20}  {row[2]:>10.1f}  {row[3]:>10.1f}  {row[4]:>10.1f}")

    ainda_em_metros = sum(1 for r in rows if r[2] < 10 and r[3] < 10 and r[4] < 10)
    if ainda_em_metros:
        print(f"\nATENCAO: {ainda_em_metros} modelo(s) ainda parecem estar em metros!")
    else:
        print(f"\nTodos {len(rows)} modelos estao em centimetros.")


if __name__ == "__main__":
    from app import create_app
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        from app import db
        conn = db.session.connection()

        print("=" * 65)
        print("Migration: Padronizar medidas de moto para CM")
        print("=" * 65)

        # Wrap strings em text() para SQLAlchemy
        class TextConn:
            def __init__(self, conn):
                self._conn = conn

            def execute(self, sql):
                return self._conn.execute(text(sql))

        tc = TextConn(conn)

        tem_conversao = verificar_antes(tc)

        if not tem_conversao:
            print("\nNada a converter. Todos os modelos ja estao em CM (ou tabela vazia).")
        else:
            executar_migration(tc)
            db.session.commit()
            verificar_depois(tc)

        print("\nMigration concluida.")
