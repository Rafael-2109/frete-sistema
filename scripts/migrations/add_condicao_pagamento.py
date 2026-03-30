"""Migration: Adicionar campo condicao_pagamento em cotacoes e fretes.

Armazena condicao de pagamento: "A Vista" ou "XX dias" (ex: "30 dias").
Exibido na cotacao e na secao de venda do frete.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    for tabela in ('cotacoes', 'fretes'):
        result = db.session.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = 'condicao_pagamento'
        """), {'tabela': tabela}).scalar()
        existe = 'SIM' if result else 'NAO'
        print(f"[BEFORE] {tabela}.condicao_pagamento existe = {existe}")


def executar_migration():
    """Executa a migration."""
    db.session.execute(db.text(
        "ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(50)"
    ))
    db.session.execute(db.text(
        "ALTER TABLE fretes ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(50)"
    ))
    db.session.commit()
    print("[OK] condicao_pagamento adicionado em cotacoes e fretes")


def verificar_depois():
    """Verifica estado apos a migration."""
    for tabela in ('cotacoes', 'fretes'):
        result = db.session.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = 'condicao_pagamento'
        """), {'tabela': tabela}).scalar()
        assert result is not None, f"Campo condicao_pagamento NAO encontrado em {tabela}"
        print(f"[AFTER] {tabela}.condicao_pagamento existe = SIM")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
