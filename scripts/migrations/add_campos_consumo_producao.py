#!/usr/bin/env python3
"""
Script de migracao: Adicionar campos de vinculacao de consumo/producao
na tabela movimentacao_estoque

Uso local:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source venv/bin/activate
    python scripts/migrations/add_campos_consumo_producao.py

Autor: Claude Code
Data: 2025-12-09
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(coluna: str) -> bool:
    """Verifica se a coluna ja existe na tabela"""
    resultado = db.session.execute(text(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'movimentacao_estoque'
        AND column_name = '{coluna}'
    """)).fetchone()
    return resultado is not None


def adicionar_colunas():
    """Adiciona colunas de vinculacao de producao/consumo"""
    app = create_app()

    with app.app_context():
        colunas_adicionadas = []

        try:
            # 1. operacao_producao_id - PseudoID da operacao
            # Formato: PROD_YYYYMMDD_HHMMSS_XXXX
            if not verificar_coluna_existe('operacao_producao_id'):
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN operacao_producao_id VARCHAR(50) NULL
                """))
                colunas_adicionadas.append('operacao_producao_id')
                print("✅ Coluna 'operacao_producao_id' adicionada")
            else:
                print("ℹ️ Coluna 'operacao_producao_id' ja existe")

            # 2. tipo_origem_producao - Tipo de origem da movimentacao
            # Valores: RAIZ, CONSUMO_DIRETO, PRODUCAO_AUTO, CONSUMO_AUTO
            if not verificar_coluna_existe('tipo_origem_producao'):
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN tipo_origem_producao VARCHAR(20) NULL
                """))
                colunas_adicionadas.append('tipo_origem_producao')
                print("✅ Coluna 'tipo_origem_producao' adicionada")
            else:
                print("ℹ️ Coluna 'tipo_origem_producao' ja existe")

            # 3. cod_produto_raiz - Codigo do produto raiz da operacao
            if not verificar_coluna_existe('cod_produto_raiz'):
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN cod_produto_raiz VARCHAR(50) NULL
                """))
                colunas_adicionadas.append('cod_produto_raiz')
                print("✅ Coluna 'cod_produto_raiz' adicionada")
            else:
                print("ℹ️ Coluna 'cod_produto_raiz' ja existe")

            # 4. producao_pai_id - FK para producao que gerou este consumo
            if not verificar_coluna_existe('producao_pai_id'):
                db.session.execute(text("""
                    ALTER TABLE movimentacao_estoque
                    ADD COLUMN producao_pai_id INTEGER NULL
                """))
                colunas_adicionadas.append('producao_pai_id')
                print("✅ Coluna 'producao_pai_id' adicionada")

                # Adicionar FK constraint separadamente para evitar problemas
                try:
                    db.session.execute(text("""
                        ALTER TABLE movimentacao_estoque
                        ADD CONSTRAINT fk_movimentacao_producao_pai
                        FOREIGN KEY (producao_pai_id)
                        REFERENCES movimentacao_estoque(id)
                        ON DELETE SET NULL
                    """))
                    print("✅ FK constraint 'fk_movimentacao_producao_pai' adicionada")
                except Exception as e:
                    print(f"⚠️ FK constraint ja existe ou erro: {e}")
            else:
                print("ℹ️ Coluna 'producao_pai_id' ja existe")

            # Criar indices para performance
            print("\n📊 Criando indices...")

            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_movimentacao_operacao
                    ON movimentacao_estoque(operacao_producao_id)
                """))
                print("✅ Indice 'idx_movimentacao_operacao' criado")
            except Exception as e:
                print(f"⚠️ Indice 'idx_movimentacao_operacao': {e}")

            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_movimentacao_produto_raiz
                    ON movimentacao_estoque(cod_produto_raiz)
                """))
                print("✅ Indice 'idx_movimentacao_produto_raiz' criado")
            except Exception as e:
                print(f"⚠️ Indice 'idx_movimentacao_produto_raiz': {e}")

            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_movimentacao_producao_pai
                    ON movimentacao_estoque(producao_pai_id)
                """))
                print("✅ Indice 'idx_movimentacao_producao_pai' criado")
            except Exception as e:
                print(f"⚠️ Indice 'idx_movimentacao_producao_pai': {e}")

            db.session.commit()
            print(f"\n✅ Migracao concluida! {len(colunas_adicionadas)} coluna(s) adicionada(s)")

            if colunas_adicionadas:
                print(f"   Colunas: {', '.join(colunas_adicionadas)}")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro na migracao: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACAO: Campos de Consumo/Producao em MovimentacaoEstoque")
    print("=" * 60)
    print()

    sucesso = adicionar_colunas()

    print()
    print("=" * 60)
    if sucesso:
        print("MIGRACAO FINALIZADA COM SUCESSO")
    else:
        print("MIGRACAO FALHOU - VERIFIQUE OS ERROS ACIMA")
    print("=" * 60)
