"""
TEMPLATE: Script de Migração para Campos Odoo
==============================================

Copie este template e adapte para sua entidade.
Substitua 'xxx' pelo nome da sua tabela (ex: fretes, despesas_extras, etc.)

Arquivos de referência:
- scripts_migracao/06_adicionar_campos_despesa_extra_odoo.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(nome_tabela, nome_coluna):
    """Verifica se uma coluna já existe na tabela"""
    resultado = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :nome_tabela
        AND column_name = :nome_coluna;
    """), {'nome_tabela': nome_tabela, 'nome_coluna': nome_coluna})
    return resultado.fetchone() is not None


def adicionar_campos_odoo():
    """Adiciona campos para integração Odoo na tabela xxx"""

    app = create_app()
    NOME_TABELA = 'xxx'  # ALTERAR: nome da sua tabela

    with app.app_context():
        try:
            print("=" * 80)
            print(f"MIGRAÇÃO: Adicionar campos Odoo em {NOME_TABELA}")
            print("=" * 80)
            print()

            # ================================================================
            # CAMPOS DE INTEGRAÇÃO ODOO
            # ================================================================
            campos_odoo = [
                ('odoo_dfe_id', 'INTEGER', True),          # Com índice
                ('odoo_purchase_order_id', 'INTEGER', False),
                ('odoo_invoice_id', 'INTEGER', False),
                ('lancado_odoo_em', 'TIMESTAMP', False),
                ('lancado_odoo_por', 'VARCHAR(100)', False),
            ]

            for campo, tipo, criar_indice in campos_odoo:
                print(f"📋 Campo: {campo}")
                if verificar_coluna_existe(NOME_TABELA, campo):
                    print(f"   ⚠️  Já existe. Pulando...")
                else:
                    print(f"   📝 Adicionando...")
                    db.session.execute(text(f"""
                        ALTER TABLE {NOME_TABELA}
                        ADD COLUMN {campo} {tipo};
                    """))

                    if criar_indice:
                        db.session.execute(text(f"""
                            CREATE INDEX idx_{NOME_TABELA}_{campo}
                            ON {NOME_TABELA}({campo});
                        """))
                        print(f"   ✅ Adicionado com índice!")
                    else:
                        print(f"   ✅ Adicionado!")
                print()

            # ================================================================
            # CAMPO STATUS (se não existir)
            # ================================================================
            print("📋 Campo: status")
            if verificar_coluna_existe(NOME_TABELA, 'status'):
                print("   ⚠️  Já existe. Verificando valores...")
            else:
                print("   📝 Adicionando...")
                db.session.execute(text(f"""
                    ALTER TABLE {NOME_TABELA}
                    ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';
                """))
                db.session.execute(text(f"""
                    CREATE INDEX idx_{NOME_TABELA}_status
                    ON {NOME_TABELA}(status);
                """))
                print("   ✅ Adicionado com índice!")
            print()

            # ================================================================
            # CAMPO VÍNCULO COM CTe (se aplicável)
            # ================================================================
            # Descomente se precisar de vínculo com CTe
            #
            # print("📋 Campo: xxx_cte_id (FK)")
            # if verificar_coluna_existe(NOME_TABELA, 'xxx_cte_id'):
            #     print("   ⚠️  Já existe. Pulando...")
            # else:
            #     print("   📝 Adicionando...")
            #     db.session.execute(text(f"""
            #         ALTER TABLE {NOME_TABELA}
            #         ADD COLUMN xxx_cte_id INTEGER;
            #     """))
            #     db.session.execute(text(f"""
            #         ALTER TABLE {NOME_TABELA}
            #         ADD CONSTRAINT fk_{NOME_TABELA}_cte
            #         FOREIGN KEY (xxx_cte_id)
            #         REFERENCES conhecimento_transporte(id)
            #         ON DELETE SET NULL;
            #     """))
            #     db.session.execute(text(f"""
            #         CREATE INDEX idx_{NOME_TABELA}_cte_id
            #         ON {NOME_TABELA}(xxx_cte_id);
            #     """))
            #     print("   ✅ Adicionado com FK e índice!")
            # print()

            # ================================================================
            # MIGRAÇÃO DE DADOS (OPCIONAL)
            # ================================================================
            # Exemplo: Definir status inicial baseado em alguma condição
            #
            # print("📋 Migração de dados")
            # resultado = db.session.execute(text(f"""
            #     UPDATE {NOME_TABELA}
            #     SET status = 'LANCADO'
            #     WHERE alguma_coluna IS NOT NULL
            #     AND status = 'PENDENTE';
            # """))
            # print(f"   ✅ {resultado.rowcount} registros atualizados!")
            # print()

            # ================================================================
            # COMMIT FINAL
            # ================================================================
            db.session.commit()

            print("=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print()
            print(f"❌ ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    adicionar_campos_odoo()
