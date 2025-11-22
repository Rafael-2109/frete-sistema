"""
SCRIPT 06: Adicionar campos para integração Odoo em DespesaExtra
================================================================

OBJETIVO:
    Adicionar os campos necessários para:
    1. Vínculo com CTe Complementar
    2. Integração com Odoo (DFe, PO, Invoice)
    3. Status da despesa
    4. Comprovante para NFS/Recibo

CAMPOS ADICIONADOS:
    - status (String 20) - PENDENTE, VINCULADO_CTE, LANCADO_ODOO, LANCADO, CANCELADO
    - despesa_cte_id (FK conhecimento_transporte)
    - chave_cte (String 44)
    - odoo_dfe_id (Integer)
    - odoo_purchase_order_id (Integer)
    - odoo_invoice_id (Integer)
    - lancado_odoo_em (DateTime)
    - lancado_odoo_por (String 100)
    - comprovante_path (String 500)
    - comprovante_nome_arquivo (String 255)

MIGRAÇÃO DE DADOS:
    - Despesas com fatura_frete_id preenchido → status = 'LANCADO'
    - Despesas sem fatura_frete_id → status = 'PENDENTE'

Executar: LOCALMENTE primeiro, depois criar SQL para Render
Data: 2025-01-22
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(nome_coluna):
    """Verifica se uma coluna já existe na tabela despesas_extras"""
    resultado = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'despesas_extras'
        AND column_name = :nome_coluna;
    """), {'nome_coluna': nome_coluna})
    return resultado.fetchone() is not None


def adicionar_campos_despesa_extra_odoo():
    """Adiciona campos para integração Odoo em DespesaExtra"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("MIGRAÇÃO: Adicionar campos Odoo em DespesaExtra")
            print("=" * 80)
            print()

            # ================================================================
            # ETAPA 1: Adicionar campo STATUS
            # ================================================================
            print("📋 ETAPA 1: Campo status")
            print("-" * 40)

            if verificar_coluna_existe('status'):
                print("   ⚠️  Coluna 'status' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'status'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';
                """))
                print("   ✅ Coluna 'status' adicionada!")

                # Criar índice
                print("   📝 Criando índice para 'status'...")
                db.session.execute(text("""
                    CREATE INDEX idx_despesas_extras_status
                    ON despesas_extras(status);
                """))
                print("   ✅ Índice criado!")
            print()

            # ================================================================
            # ETAPA 2: Adicionar campo despesa_cte_id (FK)
            # ================================================================
            print("📋 ETAPA 2: Campo despesa_cte_id (FK)")
            print("-" * 40)

            if verificar_coluna_existe('despesa_cte_id'):
                print("   ⚠️  Coluna 'despesa_cte_id' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'despesa_cte_id'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN despesa_cte_id INTEGER;
                """))
                print("   ✅ Coluna 'despesa_cte_id' adicionada!")

                # Adicionar FK
                print("   📝 Adicionando FOREIGN KEY constraint...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD CONSTRAINT fk_despesa_extra_cte
                    FOREIGN KEY (despesa_cte_id)
                    REFERENCES conhecimento_transporte(id)
                    ON DELETE SET NULL;
                """))
                print("   ✅ Foreign Key constraint adicionada!")

                # Criar índice
                print("   📝 Criando índice para 'despesa_cte_id'...")
                db.session.execute(text("""
                    CREATE INDEX idx_despesas_extras_cte_id
                    ON despesas_extras(despesa_cte_id);
                """))
                print("   ✅ Índice criado!")
            print()

            # ================================================================
            # ETAPA 3: Adicionar campo chave_cte
            # ================================================================
            print("📋 ETAPA 3: Campo chave_cte")
            print("-" * 40)

            if verificar_coluna_existe('chave_cte'):
                print("   ⚠️  Coluna 'chave_cte' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'chave_cte'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN chave_cte VARCHAR(44);
                """))
                print("   ✅ Coluna 'chave_cte' adicionada!")

                # Criar índice
                print("   📝 Criando índice para 'chave_cte'...")
                db.session.execute(text("""
                    CREATE INDEX idx_despesas_extras_chave_cte
                    ON despesas_extras(chave_cte);
                """))
                print("   ✅ Índice criado!")
            print()

            # ================================================================
            # ETAPA 4: Adicionar campos Odoo (dfe_id, po_id, invoice_id)
            # ================================================================
            print("📋 ETAPA 4: Campos de integração Odoo")
            print("-" * 40)

            # odoo_dfe_id
            if verificar_coluna_existe('odoo_dfe_id'):
                print("   ⚠️  Coluna 'odoo_dfe_id' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'odoo_dfe_id'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN odoo_dfe_id INTEGER;
                """))
                db.session.execute(text("""
                    CREATE INDEX idx_despesas_extras_odoo_dfe_id
                    ON despesas_extras(odoo_dfe_id);
                """))
                print("   ✅ Coluna 'odoo_dfe_id' adicionada com índice!")

            # odoo_purchase_order_id
            if verificar_coluna_existe('odoo_purchase_order_id'):
                print("   ⚠️  Coluna 'odoo_purchase_order_id' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'odoo_purchase_order_id'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN odoo_purchase_order_id INTEGER;
                """))
                print("   ✅ Coluna 'odoo_purchase_order_id' adicionada!")

            # odoo_invoice_id
            if verificar_coluna_existe('odoo_invoice_id'):
                print("   ⚠️  Coluna 'odoo_invoice_id' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'odoo_invoice_id'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN odoo_invoice_id INTEGER;
                """))
                print("   ✅ Coluna 'odoo_invoice_id' adicionada!")
            print()

            # ================================================================
            # ETAPA 5: Adicionar campos de auditoria Odoo
            # ================================================================
            print("📋 ETAPA 5: Campos de auditoria Odoo")
            print("-" * 40)

            # lancado_odoo_em
            if verificar_coluna_existe('lancado_odoo_em'):
                print("   ⚠️  Coluna 'lancado_odoo_em' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'lancado_odoo_em'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN lancado_odoo_em TIMESTAMP;
                """))
                print("   ✅ Coluna 'lancado_odoo_em' adicionada!")

            # lancado_odoo_por
            if verificar_coluna_existe('lancado_odoo_por'):
                print("   ⚠️  Coluna 'lancado_odoo_por' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'lancado_odoo_por'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN lancado_odoo_por VARCHAR(100);
                """))
                print("   ✅ Coluna 'lancado_odoo_por' adicionada!")
            print()

            # ================================================================
            # ETAPA 6: Adicionar campos de comprovante
            # ================================================================
            print("📋 ETAPA 6: Campos de comprovante (NFS/Recibo)")
            print("-" * 40)

            # comprovante_path
            if verificar_coluna_existe('comprovante_path'):
                print("   ⚠️  Coluna 'comprovante_path' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'comprovante_path'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN comprovante_path VARCHAR(500);
                """))
                print("   ✅ Coluna 'comprovante_path' adicionada!")

            # comprovante_nome_arquivo
            if verificar_coluna_existe('comprovante_nome_arquivo'):
                print("   ⚠️  Coluna 'comprovante_nome_arquivo' já existe. Pulando...")
            else:
                print("   📝 Adicionando coluna 'comprovante_nome_arquivo'...")
                db.session.execute(text("""
                    ALTER TABLE despesas_extras
                    ADD COLUMN comprovante_nome_arquivo VARCHAR(255);
                """))
                print("   ✅ Coluna 'comprovante_nome_arquivo' adicionada!")
            print()

            # ================================================================
            # ETAPA 7: Adicionar campo despesa_extra_id na auditoria
            # ================================================================
            print("📋 ETAPA 7: Campo despesa_extra_id na tabela de auditoria")
            print("-" * 40)

            # Verificar se coluna existe na auditoria
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'lancamento_frete_odoo_auditoria'
                AND column_name = 'despesa_extra_id';
            """))

            if resultado.fetchone():
                print("   ⚠️  Coluna 'despesa_extra_id' já existe na auditoria. Pulando...")
            else:
                print("   📝 Adicionando coluna 'despesa_extra_id' na auditoria...")
                db.session.execute(text("""
                    ALTER TABLE lancamento_frete_odoo_auditoria
                    ADD COLUMN despesa_extra_id INTEGER;
                """))

                # Adicionar FK
                print("   📝 Adicionando FOREIGN KEY constraint...")
                db.session.execute(text("""
                    ALTER TABLE lancamento_frete_odoo_auditoria
                    ADD CONSTRAINT fk_auditoria_despesa_extra
                    FOREIGN KEY (despesa_extra_id)
                    REFERENCES despesas_extras(id)
                    ON DELETE SET NULL;
                """))

                # Criar índice
                print("   📝 Criando índice...")
                db.session.execute(text("""
                    CREATE INDEX idx_auditoria_despesa_extra_id
                    ON lancamento_frete_odoo_auditoria(despesa_extra_id);
                """))
                print("   ✅ Campo 'despesa_extra_id' adicionado na auditoria!")
            print()

            # ================================================================
            # ETAPA 8: Migrar dados - Definir status inicial
            # ================================================================
            print("📋 ETAPA 8: Migrar dados - Definir status inicial")
            print("-" * 40)

            # Contar despesas antes
            resultado = db.session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(fatura_frete_id) as com_fatura,
                    COUNT(*) - COUNT(fatura_frete_id) as sem_fatura
                FROM despesas_extras;
            """))
            row = resultado.fetchone()
            total = row[0]
            com_fatura = row[1]
            sem_fatura = row[2]

            print(f"   📊 Total de despesas: {total}")
            print(f"   📊 Com fatura_frete_id: {com_fatura} → status = 'LANCADO'")
            print(f"   📊 Sem fatura_frete_id: {sem_fatura} → status = 'PENDENTE'")
            print()

            # Atualizar despesas COM fatura_frete_id para LANCADO
            print("   📝 Atualizando despesas com fatura para 'LANCADO'...")
            resultado_lancado = db.session.execute(text("""
                UPDATE despesas_extras
                SET status = 'LANCADO'
                WHERE fatura_frete_id IS NOT NULL
                AND status = 'PENDENTE';
            """))
            print(f"   ✅ {resultado_lancado.rowcount} despesas atualizadas para 'LANCADO'!")

            # Despesas SEM fatura_frete_id já estão como PENDENTE (default)
            print("   ✅ Despesas sem fatura permanecem como 'PENDENTE' (default)")
            print()

            # ================================================================
            # COMMIT FINAL
            # ================================================================
            db.session.commit()

            print("=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print()
            print("RESUMO DOS CAMPOS ADICIONADOS:")
            print("   1. status (VARCHAR 20) - com índice")
            print("   2. despesa_cte_id (INTEGER FK) - com índice e constraint")
            print("   3. chave_cte (VARCHAR 44) - com índice")
            print("   4. odoo_dfe_id (INTEGER) - com índice")
            print("   5. odoo_purchase_order_id (INTEGER)")
            print("   6. odoo_invoice_id (INTEGER)")
            print("   7. lancado_odoo_em (TIMESTAMP)")
            print("   8. lancado_odoo_por (VARCHAR 100)")
            print("   9. comprovante_path (VARCHAR 500)")
            print("  10. comprovante_nome_arquivo (VARCHAR 255)")
            print()
            print("MIGRAÇÃO DE DADOS:")
            print(f"   - {com_fatura} despesas → status = 'LANCADO'")
            print(f"   - {sem_fatura} despesas → status = 'PENDENTE'")
            print()
            print("PRÓXIMOS PASSOS:")
            print("1. Executar script SQL equivalente no Render")
            print("2. Atualizar modelo DespesaExtra em models.py")
            print("3. Implementar service de lançamento Odoo para despesas")
            print()

        except Exception as e:
            db.session.rollback()
            print()
            print("❌ ERRO durante migração:")
            print(f"   {str(e)}")
            print()
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    adicionar_campos_despesa_extra_odoo()
