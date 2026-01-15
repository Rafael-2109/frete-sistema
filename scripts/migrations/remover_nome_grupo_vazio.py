"""
MIGRAÇÃO: Remover registros com nome_grupo vazio ou NULL
Data: 2026-01-15
Descrição: Remove duplicatas de previsao_demanda causadas por
           importação com nome_grupo vazio ou NULL

Uso:
    source .venv/bin/activate && python scripts/migrations/remover_nome_grupo_vazio.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_registros():
    """Verifica registros que serão afetados"""
    print("\n" + "=" * 60)
    print("PASSO 1: Verificando registros com nome_grupo vazio/NULL")
    print("=" * 60)

    resultado = db.session.execute(text("""
        SELECT
            CASE
                WHEN nome_grupo IS NULL THEN 'NULL'
                WHEN nome_grupo = '' THEN 'VAZIO'
                ELSE nome_grupo
            END as tipo_grupo,
            COUNT(*) as registros,
            SUM(qtd_demanda_prevista) as total_qtd
        FROM previsao_demanda
        WHERE nome_grupo IS NULL OR nome_grupo = ''
        GROUP BY nome_grupo
    """))

    registros_afetados = 0
    for row in resultado:
        print(f"  Tipo: {row.tipo_grupo:10} | Registros: {row.registros:5} | Qtd Total: {float(row.total_qtd or 0):,.0f}")
        registros_afetados += row.registros

    return registros_afetados


def remover_registros_vazios():
    """Remove registros com nome_grupo vazio ou NULL"""
    print("\n" + "=" * 60)
    print("PASSO 2: Removendo registros com nome_grupo vazio/NULL")
    print("=" * 60)

    resultado = db.session.execute(text("""
        DELETE FROM previsao_demanda
        WHERE nome_grupo IS NULL OR nome_grupo = ''
    """))

    registros_deletados = resultado.rowcount
    print(f"  Registros deletados: {registros_deletados}")

    return registros_deletados


def verificar_resultado_final():
    """Verifica o estado final da tabela"""
    print("\n" + "=" * 60)
    print("PASSO 3: Verificando resultado final")
    print("=" * 60)

    resultado = db.session.execute(text("""
        SELECT
            nome_grupo,
            COUNT(*) as registros,
            SUM(qtd_demanda_prevista) as total_qtd
        FROM previsao_demanda
        GROUP BY nome_grupo
        ORDER BY nome_grupo
    """))

    for row in resultado:
        nome = row.nome_grupo or 'NULL'
        print(f"  Grupo: {nome:20} | Registros: {row.registros:5} | Qtd Total: {float(row.total_qtd or 0):,.0f}")


def main(confirmar=False):
    app = create_app()

    with app.app_context():
        try:
            # Verificar registros antes
            registros_afetados = verificar_registros()

            if registros_afetados == 0:
                print("\n✅ Nenhum registro com nome_grupo vazio/NULL encontrado.")
                print("   Migração não é necessária.")
                return

            # Confirmar com usuário (ou pular se --confirmar)
            print(f"\n⚠️  ATENÇÃO: {registros_afetados} registros serão DELETADOS!")

            if not confirmar:
                resposta = input("   Deseja continuar? (s/N): ").strip().lower()
                if resposta != 's':
                    print("\n❌ Migração cancelada pelo usuário.")
                    return
            else:
                print("   [--confirmar] Prosseguindo automaticamente...")

            # Remover registros
            registros_deletados = remover_registros_vazios()

            # Commit
            db.session.commit()

            # Verificar resultado
            verificar_resultado_final()

            print("\n" + "=" * 60)
            print(f"✅ MIGRAÇÃO CONCLUÍDA: {registros_deletados} registros removidos")
            print("=" * 60)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Remover registros com nome_grupo vazio/NULL')
    parser.add_argument('--confirmar', action='store_true', help='Pular confirmação interativa')
    args = parser.parse_args()
    main(confirmar=args.confirmar)
