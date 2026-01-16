"""
Script de migration: Adiciona campo transportadora_id na tabela despesas_extras

Este campo permite vincular uma despesa extra a uma transportadora diferente
da transportadora do frete original. Útil para casos como:
- Devolução coletada por outro transportador
- Despesas de freteiros avulsos

Se transportadora_id for NULL, o sistema usa a transportadora do frete (comportamento padrão).

Data: 2025-01-16
"""
import sys
import os

# Adiciona o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_campo_transportadora():
    """Adiciona campo transportadora_id na tabela despesas_extras"""
    app = create_app()
    with app.app_context():
        try:
            # Verifica se o campo já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'despesas_extras'
                AND column_name = 'transportadora_id'
            """))

            if resultado.fetchone():
                print("Campo 'transportadora_id' já existe na tabela despesas_extras.")
                return

            # Adiciona o campo
            print("Adicionando campo transportadora_id...")
            db.session.execute(text("""
                ALTER TABLE despesas_extras
                ADD COLUMN transportadora_id INTEGER REFERENCES transportadoras(id)
            """))

            # Cria o índice para performance
            print("Criando índice ix_despesas_extras_transportadora_id...")
            db.session.execute(text("""
                CREATE INDEX ix_despesas_extras_transportadora_id
                ON despesas_extras(transportadora_id)
            """))

            db.session.commit()
            print("Campo e índice criados com sucesso!")

            # Mostra estatísticas
            total = db.session.execute(text("SELECT COUNT(*) FROM despesas_extras")).scalar()
            print(f"\nTotal de despesas extras existentes: {total}")
            print("Todas as despesas existentes terão transportadora_id = NULL")
            print("(Usarão automaticamente a transportadora do frete)")

        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
            raise


def verificar_campo():
    """Verifica se o campo foi criado corretamente"""
    app = create_app()
    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_name = 'despesas_extras'
                AND column_name = 'transportadora_id'
            """))

            row = resultado.fetchone()
            if row:
                print(f"Campo encontrado: {row[0]}, Tipo: {row[1]}, Nullable: {row[2]}")
            else:
                print("Campo não encontrado!")

        except Exception as e:
            print(f"Erro ao verificar: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Migration: Add transportadora_id to despesas_extras')
    parser.add_argument('--verificar', action='store_true', help='Apenas verificar se campo existe')

    args = parser.parse_args()

    if args.verificar:
        verificar_campo()
    else:
        adicionar_campo_transportadora()
