"""
Migration: Adicionar Empresa Compradora + Reducao BC ICMS
=========================================================

Fase 1 - Validacao Fiscal - Alteracoes:
1. Adicionar cnpj_empresa_compradora em 4 tabelas
2. Adicionar reducao_bc_icms em perfil e primeira_compra
3. Alterar constraint unica do perfil fiscal

Empresas Compradoras:
- NACOM GOYA - CD (ID 34): 61.724.241/0003-30
- NACOM GOYA - FB (ID 1): 61.724.241/0001-78
- NACOM GOYA - SC (ID 33): 61.724.241/0002-59
- LA FAMIGLIA - LF (ID 35): 18.467.441/0001-63

Data: 22/01/2026
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Executa a migration para adicionar empresa compradora e reducao BC ICMS"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Empresa Compradora + Reducao BC ICMS")
            print("=" * 60)

            # 1. Adicionar campos na tabela perfil_fiscal_produto_fornecedor
            print("\n[1/8] Adicionando campos em perfil_fiscal_produto_fornecedor...")
            db.session.execute(text("""
                ALTER TABLE perfil_fiscal_produto_fornecedor
                ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
                ADD COLUMN IF NOT EXISTS reducao_bc_icms_esperada NUMERIC(5,2);
            """))
            print("      OK - Campos cnpj_empresa_compradora e reducao_bc_icms_esperada adicionados")

            # 2. Adicionar campos na tabela divergencia_fiscal
            print("\n[2/8] Adicionando campos em divergencia_fiscal...")
            db.session.execute(text("""
                ALTER TABLE divergencia_fiscal
                ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
                ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);
            """))
            print("      OK - Campos cnpj_empresa_compradora e razao_empresa_compradora adicionados")

            # 3. Adicionar campos na tabela cadastro_primeira_compra
            print("\n[3/8] Adicionando campos em cadastro_primeira_compra...")
            db.session.execute(text("""
                ALTER TABLE cadastro_primeira_compra
                ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
                ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255),
                ADD COLUMN IF NOT EXISTS reducao_bc_icms NUMERIC(5,2);
            """))
            print("      OK - Campos cnpj_empresa_compradora, razao_empresa_compradora e reducao_bc_icms adicionados")

            # 4. Adicionar campos na tabela validacao_fiscal_dfe
            print("\n[4/8] Adicionando campos em validacao_fiscal_dfe...")
            db.session.execute(text("""
                ALTER TABLE validacao_fiscal_dfe
                ADD COLUMN IF NOT EXISTS cnpj_empresa_compradora VARCHAR(20),
                ADD COLUMN IF NOT EXISTS razao_empresa_compradora VARCHAR(255);
            """))
            print("      OK - Campos cnpj_empresa_compradora e razao_empresa_compradora adicionados")

            # 5. Criar indices
            print("\n[5/8] Criando indices...")

            # Indice para perfil_fiscal_produto_fornecedor
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_perfil_fiscal_cnpj_empresa
                ON perfil_fiscal_produto_fornecedor(cnpj_empresa_compradora);
            """))

            # Indice para divergencia_fiscal
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_divergencia_cnpj_empresa
                ON divergencia_fiscal(cnpj_empresa_compradora);
            """))

            # Indice para cadastro_primeira_compra
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_primeira_compra_cnpj_empresa
                ON cadastro_primeira_compra(cnpj_empresa_compradora);
            """))

            # Indice para validacao_fiscal_dfe
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_dfe_cnpj_empresa
                ON validacao_fiscal_dfe(cnpj_empresa_compradora);
            """))
            print("      OK - 4 indices criados")

            # 6. Remover constraint antiga (se existir)
            print("\n[6/8] Removendo constraint antiga...")
            try:
                db.session.execute(text("""
                    ALTER TABLE perfil_fiscal_produto_fornecedor
                    DROP CONSTRAINT IF EXISTS uq_perfil_fiscal_produto_fornecedor;
                """))
                print("      OK - Constraint antiga removida")
            except Exception as e:
                print(f"      AVISO - Constraint nao existia: {e}")

            # 7. Criar nova constraint
            print("\n[7/8] Criando nova constraint unica...")
            db.session.execute(text("""
                ALTER TABLE perfil_fiscal_produto_fornecedor
                ADD CONSTRAINT uq_perfil_fiscal_empresa_fornecedor_produto
                UNIQUE (cnpj_empresa_compradora, cnpj_fornecedor, cod_produto);
            """))
            print("      OK - Nova constraint criada: (empresa + fornecedor + produto)")

            # 8. Commit
            print("\n[8/8] Commitando transacao...")
            db.session.commit()
            print("      OK - Commit realizado")

            print("\n" + "=" * 60)
            print("MIGRATION CONCLUIDA COM SUCESSO!")
            print("=" * 60)

            # Resumo
            print("\nResumo das alteracoes:")
            print("- perfil_fiscal_produto_fornecedor: +2 campos, nova constraint")
            print("- divergencia_fiscal: +2 campos")
            print("- cadastro_primeira_compra: +3 campos")
            print("- validacao_fiscal_dfe: +2 campos")
            print("- 4 novos indices criados")

            return True

        except Exception as e:
            print(f"\n[ERRO] Migration falhou: {e}")
            db.session.rollback()
            return False


def verificar_migration():
    """Verifica se a migration foi aplicada corretamente"""
    app = create_app()
    with app.app_context():
        try:
            print("\nVerificando migration...")

            # Verificar campos
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'perfil_fiscal_produto_fornecedor'
                AND column_name IN ('cnpj_empresa_compradora', 'reducao_bc_icms_esperada')
            """))
            campos = [row[0] for row in result]
            print(f"Campos encontrados em perfil_fiscal: {campos}")

            # Verificar constraint
            result = db.session.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'perfil_fiscal_produto_fornecedor'
                AND constraint_type = 'UNIQUE'
            """))
            constraints = [row[0] for row in result]
            print(f"Constraints unicas: {constraints}")

            if 'cnpj_empresa_compradora' in campos and 'reducao_bc_icms_esperada' in campos:
                print("\nMigration verificada com sucesso!")
                return True
            else:
                print("\nMigration incompleta!")
                return False

        except Exception as e:
            print(f"Erro na verificacao: {e}")
            return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migration: Empresa Compradora + Reducao BC ICMS')
    parser.add_argument('--verificar', action='store_true', help='Apenas verificar se migration foi aplicada')

    args = parser.parse_args()

    if args.verificar:
        verificar_migration()
    else:
        sucesso = executar_migration()
        if sucesso:
            verificar_migration()
