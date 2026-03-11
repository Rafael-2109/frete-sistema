"""
Migration: Alterar unique constraint de pendencia_fiscal_ibscbs
================================================================

Problema: chave_acesso tinha UNIQUE simples, mas NF-es podem gerar
multiplas pendencias (uma por NCM prefixo) com a mesma chave_acesso.
Isso causava UniqueViolation (PYTHON-FLASK-19).

Solucao: Trocar unique simples por composite unique (chave_acesso, ncm_prefixo).

Uso:
    source .venv/bin/activate
    python scripts/migrations/alterar_unique_pendencia_fiscal_ibscbs.py

Data: 2026-03-11
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_constraint_existe(nome: str) -> bool:
    """Verifica se uma constraint existe no banco."""
    result = db.session.execute(text(
        "SELECT 1 FROM pg_constraint WHERE conname = :nome"
    ), {'nome': nome})
    return result.scalar() is not None


def executar():
    """Executa a migration."""
    app = create_app()

    with app.app_context():
        # Estado antes
        tem_antiga = verificar_constraint_existe('pendencia_fiscal_ibscbs_chave_acesso_key')
        tem_nova = verificar_constraint_existe('uq_pendencia_fiscal_chave_ncm')

        print(f"Estado ANTES:")
        print(f"  - pendencia_fiscal_ibscbs_chave_acesso_key: {'EXISTE' if tem_antiga else 'NAO EXISTE'}")
        print(f"  - uq_pendencia_fiscal_chave_ncm: {'EXISTE' if tem_nova else 'NAO EXISTE'}")

        if tem_nova and not tem_antiga:
            print("\nMigration ja aplicada — nada a fazer.")
            return

        # 1. Remover unique constraint antiga
        if tem_antiga:
            db.session.execute(text(
                "ALTER TABLE pendencia_fiscal_ibscbs "
                "DROP CONSTRAINT pendencia_fiscal_ibscbs_chave_acesso_key"
            ))
            print("\n[1/3] Constraint antiga removida")
        else:
            print("\n[1/3] Constraint antiga ja nao existe — skip")

        # 2. Criar nova unique constraint composta
        if not tem_nova:
            db.session.execute(text(
                "ALTER TABLE pendencia_fiscal_ibscbs "
                "ADD CONSTRAINT uq_pendencia_fiscal_chave_ncm "
                "UNIQUE (chave_acesso, ncm_prefixo)"
            ))
            print("[2/3] Constraint composta criada")
        else:
            print("[2/3] Constraint composta ja existe — skip")

        # 3. Garantir indice simples para queries
        db.session.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_pendencia_fiscal_ibscbs_chave_acesso "
            "ON pendencia_fiscal_ibscbs (chave_acesso)"
        ))
        print("[3/3] Indice chave_acesso garantido")

        db.session.commit()

        # Verificar estado final
        tem_antiga = verificar_constraint_existe('pendencia_fiscal_ibscbs_chave_acesso_key')
        tem_nova = verificar_constraint_existe('uq_pendencia_fiscal_chave_ncm')

        print(f"\nEstado DEPOIS:")
        print(f"  - pendencia_fiscal_ibscbs_chave_acesso_key: {'EXISTE' if tem_antiga else 'NAO EXISTE'}")
        print(f"  - uq_pendencia_fiscal_chave_ncm: {'EXISTE' if tem_nova else 'NAO EXISTE'}")

        if tem_nova and not tem_antiga:
            print("\nMigration concluida com sucesso!")
        else:
            print("\nATENCAO: estado inesperado — verificar manualmente")


if __name__ == '__main__':
    executar()
