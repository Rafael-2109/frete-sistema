"""
Script para aumentar campos de codigo/descricao na tabela nf_devolucao_linha.

Problema: Alguns clientes enviam lote/validade concatenado no codigo do produto,
excedendo o limite de 50 caracteres.

Execucao local: python scripts/migrations/fix_nfd_linha_campos.py
Execucao Render: Executar SQL diretamente no Shell
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def alterar_campos():
    """Altera os campos para suportar valores maiores"""
    app = create_app()
    with app.app_context():
        try:
            print("Alterando campos na tabela nf_devolucao_linha...")

            # Alterar codigo_produto_cliente de VARCHAR(50) para VARCHAR(255)
            db.session.execute(text("""
                ALTER TABLE nf_devolucao_linha
                ALTER COLUMN codigo_produto_cliente TYPE VARCHAR(255)
            """))
            print("  codigo_produto_cliente: VARCHAR(50) -> VARCHAR(255)")

            # Alterar descricao_produto_cliente de VARCHAR(255) para TEXT
            db.session.execute(text("""
                ALTER TABLE nf_devolucao_linha
                ALTER COLUMN descricao_produto_cliente TYPE TEXT
            """))
            print("  descricao_produto_cliente: VARCHAR(255) -> TEXT")

            db.session.commit()
            print("\nCampos alterados com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"\nErro ao alterar campos: {e}")
            return False


def verificar_registros_truncados():
    """Verifica se existem registros que podem ter sido truncados"""
    app = create_app()
    with app.app_context():
        resultado = db.session.execute(text("""
            SELECT COUNT(*) as total
            FROM nf_devolucao_linha
            WHERE LENGTH(codigo_produto_cliente) = 50
               OR LENGTH(descricao_produto_cliente) = 255
        """))
        total = resultado.fetchone().total
        if total > 0:
            print(f"\nATENCAO: {total} registro(s) podem ter sido truncados!")
            print("Considere re-importar as NFDs afetadas.")
        else:
            print("\nNenhum registro truncado encontrado.")


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACAO: Aumentar campos nf_devolucao_linha")
    print("=" * 60)

    if alterar_campos():
        verificar_registros_truncados()

    print("\n SQL para executar no Render Shell:")
    print("-" * 60)
    print("""
-- Alterar campos para suportar valores maiores
ALTER TABLE nf_devolucao_linha
ALTER COLUMN codigo_produto_cliente TYPE VARCHAR(255);

ALTER TABLE nf_devolucao_linha
ALTER COLUMN descricao_produto_cliente TYPE TEXT;

-- Verificar se existem registros truncados
SELECT COUNT(*) as possivelmente_truncados
FROM nf_devolucao_linha
WHERE LENGTH(codigo_produto_cliente) = 50
   OR LENGTH(descricao_produto_cliente) = 255;
""")
