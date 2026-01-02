"""
Script de Migracao - FASE 4: NFDevolucaoNFReferenciada
======================================================

Cria a tabela:
- nf_devolucao_nf_referenciada (NFs de venda referenciadas pela NFD)

Adiciona campo:
- nf_devolucao.origem_registro (MONITORAMENTO ou ODOO)

Migra dados existentes:
- numero_nf_venda -> nf_devolucao_nf_referenciada

Criado em: 30/12/2024
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela_nf_referenciada():
    """Cria tabela de NFs referenciadas e adiciona campo origem_registro"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("FASE 4: Criando tabela nf_devolucao_nf_referenciada")
            print("=" * 60)

            # =====================================================================
            # 1. Verificar se tabela ja existe
            # =====================================================================
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'nf_devolucao_nf_referenciada'
                )
            """))
            if result.scalar():
                print("Tabela nf_devolucao_nf_referenciada ja existe. Pulando criacao...")
            else:
                # =====================================================================
                # 2. Criar tabela nf_devolucao_nf_referenciada
                # =====================================================================
                print("\n1. Criando tabela nf_devolucao_nf_referenciada...")
                db.session.execute(text("""
                    CREATE TABLE nf_devolucao_nf_referenciada (
                        id SERIAL PRIMARY KEY,

                        -- Vinculo com NFDevolucao
                        nf_devolucao_id INTEGER NOT NULL REFERENCES nf_devolucao(id) ON DELETE CASCADE,

                        -- Dados da NF de venda referenciada
                        numero_nf VARCHAR(20) NOT NULL,
                        serie_nf VARCHAR(10),
                        chave_nf VARCHAR(44),
                        data_emissao_nf DATE,

                        -- Origem do dado
                        origem VARCHAR(20) DEFAULT 'MANUAL' NOT NULL,

                        -- Vinculo com entrega monitorada (se disponivel)
                        entrega_monitorada_id INTEGER REFERENCES entregas_monitoradas(id),

                        -- Auditoria
                        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        criado_por VARCHAR(100),

                        -- Constraint unica (NFD + numero + serie)
                        CONSTRAINT uq_nfd_nf_ref UNIQUE (nf_devolucao_id, numero_nf, serie_nf)
                    )
                """))
                print("   Tabela criada!")

                # Indices
                db.session.execute(text("""
                    CREATE INDEX idx_nf_ref_nfd ON nf_devolucao_nf_referenciada(nf_devolucao_id);
                    CREATE INDEX idx_nf_ref_numero ON nf_devolucao_nf_referenciada(numero_nf);
                    CREATE INDEX idx_nf_ref_chave ON nf_devolucao_nf_referenciada(chave_nf);
                    CREATE INDEX idx_nf_ref_entrega ON nf_devolucao_nf_referenciada(entrega_monitorada_id);
                """))
                print("   Indices criados!")

            # =====================================================================
            # 3. Adicionar coluna origem_registro em nf_devolucao
            # =====================================================================
            print("\n2. Adicionando coluna origem_registro em nf_devolucao...")
            try:
                db.session.execute(text("""
                    ALTER TABLE nf_devolucao
                    ADD COLUMN IF NOT EXISTS origem_registro VARCHAR(20) DEFAULT 'MONITORAMENTO' NOT NULL
                """))
                print("   Coluna origem_registro adicionada!")
            except Exception as e:
                print(f"   Aviso: {e}")

            # Criar indice para origem_registro
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_nfd_origem_registro ON nf_devolucao(origem_registro)
                """))
                print("   Indice criado para origem_registro!")
            except Exception as e:
                print(f"   Aviso: {e}")

            # =====================================================================
            # 4. Migrar dados existentes de numero_nf_venda
            # =====================================================================
            print("\n3. Migrando dados existentes de numero_nf_venda...")

            # Contar registros a migrar
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM nf_devolucao
                WHERE numero_nf_venda IS NOT NULL
                AND numero_nf_venda != ''
                AND NOT EXISTS (
                    SELECT 1 FROM nf_devolucao_nf_referenciada r
                    WHERE r.nf_devolucao_id = nf_devolucao.id
                    AND r.numero_nf = nf_devolucao.numero_nf_venda
                )
            """))
            count = result.scalar()
            print(f"   {count} registros para migrar")

            if count > 0:
                # Migrar dados
                db.session.execute(text("""
                    INSERT INTO nf_devolucao_nf_referenciada (
                        nf_devolucao_id,
                        numero_nf,
                        origem,
                        entrega_monitorada_id,
                        criado_em,
                        criado_por
                    )
                    SELECT
                        id,
                        numero_nf_venda,
                        'MONITORAMENTO',
                        entrega_monitorada_id,
                        criado_em,
                        criado_por
                    FROM nf_devolucao
                    WHERE numero_nf_venda IS NOT NULL
                    AND numero_nf_venda != ''
                    AND NOT EXISTS (
                        SELECT 1 FROM nf_devolucao_nf_referenciada r
                        WHERE r.nf_devolucao_id = nf_devolucao.id
                        AND r.numero_nf = nf_devolucao.numero_nf_venda
                    )
                """))
                print(f"   {count} registros migrados!")
            else:
                print("   Nenhum registro para migrar")

            # Commit final
            db.session.commit()
            print("\n" + "=" * 60)
            print("MIGRACAO FASE 4 CONCLUIDA COM SUCESSO!")
            print("=" * 60)
            print("\nAlteracoes realizadas:")
            print("  - Tabela nf_devolucao_nf_referenciada criada")
            print("  - Coluna nf_devolucao.origem_registro adicionada")
            print("  - Dados migrados de numero_nf_venda para tabela de relacionamento")
            print("\nNOTA: O campo numero_nf_venda foi mantido para compatibilidade.")
            print("      Em versoes futuras, ele sera removido.")

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO na migracao: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    criar_tabela_nf_referenciada()
