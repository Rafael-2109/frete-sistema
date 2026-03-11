"""
Migration: Adicionar campos de horário e observações de recebimento em contatos_agendamento
Data: 2026-03-11

Novos campos:
  - horario_recebimento_de (TIME) — horário início do recebimento
  - horario_recebimento_ate (TIME) — horário fim do recebimento
  - observacoes_recebimento (TEXT) — restrições específicas do cliente
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(conn, tabela, coluna):
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :tabela AND column_name = :coluna"
    ), {'tabela': tabela, 'coluna': coluna})
    return result.fetchone() is not None


def run():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        colunas = [
            ('horario_recebimento_de', 'TIME'),
            ('horario_recebimento_ate', 'TIME'),
            ('observacoes_recebimento', 'TEXT'),
        ]

        print("=== Migration: add_campos_recebimento_contatos_agendamento ===")
        print()

        # Before: verificar estado atual
        print("BEFORE:")
        for col_name, col_type in colunas:
            existe = verificar_coluna_existe(conn, 'contatos_agendamento', col_name)
            print(f"  {col_name}: {'EXISTS' if existe else 'NOT EXISTS'}")

        # Executar DDL
        print()
        print("Executando DDL...")
        for col_name, col_type in colunas:
            if not verificar_coluna_existe(conn, 'contatos_agendamento', col_name):
                conn.execute(text(
                    f"ALTER TABLE contatos_agendamento ADD COLUMN {col_name} {col_type}"
                ))
                print(f"  + {col_name} ({col_type}) adicionada")
            else:
                print(f"  ~ {col_name} já existe, pulando")

        conn.commit()

        # After: verificar resultado
        print()
        print("AFTER:")
        for col_name, col_type in colunas:
            existe = verificar_coluna_existe(conn, 'contatos_agendamento', col_name)
            print(f"  {col_name}: {'EXISTS' if existe else 'NOT EXISTS'}")
            if not existe:
                print(f"  *** ERRO: {col_name} deveria existir! ***")

        conn.close()
        print()
        print("Migration concluída com sucesso!")


if __name__ == '__main__':
    run()
