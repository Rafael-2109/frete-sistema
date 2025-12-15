# -*- coding: utf-8 -*-
"""
Migração: Separar FKs de títulos no ExtratoItem
===============================================

PROBLEMA:
O modelo ExtratoItem tinha apenas um campo titulo_id com FK para contas_a_receber,
mas era usado tanto para recebimentos (clientes) quanto pagamentos (fornecedores).
Isso causava o bug de mostrar nome de cliente quando deveria mostrar fornecedor.

SOLUÇÃO:
- titulo_receber_id -> FK para contas_a_receber (clientes)
- titulo_pagar_id -> FK para contas_a_pagar (fornecedores)
- titulo_cnpj -> Campo cache para CNPJ
- titulo_id -> Mantido sem FK (deprecado) para compatibilidade

Data: 2025-12-15
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    """Executa a migração para separar as FKs."""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRAÇÃO: Separar FKs de títulos no ExtratoItem")
            print("=" * 60)

            # 1. Verificar se os campos já existem
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'extrato_item'
                AND column_name IN ('titulo_receber_id', 'titulo_pagar_id', 'titulo_cnpj')
            """))
            colunas_existentes = [row[0] for row in result.fetchall()]

            print(f"Colunas já existentes: {colunas_existentes}")

            # 2. Adicionar campo titulo_receber_id (se não existir)
            if 'titulo_receber_id' not in colunas_existentes:
                print("\n[1/5] Adicionando campo titulo_receber_id...")
                db.session.execute(text("""
                    ALTER TABLE extrato_item
                    ADD COLUMN titulo_receber_id INTEGER REFERENCES contas_a_receber(id)
                """))
                print("  ✓ Campo titulo_receber_id adicionado")
            else:
                print("\n[1/5] Campo titulo_receber_id já existe")

            # 3. Adicionar campo titulo_pagar_id (se não existir)
            if 'titulo_pagar_id' not in colunas_existentes:
                print("\n[2/5] Adicionando campo titulo_pagar_id...")
                db.session.execute(text("""
                    ALTER TABLE extrato_item
                    ADD COLUMN titulo_pagar_id INTEGER REFERENCES contas_a_pagar(id)
                """))
                print("  ✓ Campo titulo_pagar_id adicionado")
            else:
                print("\n[2/5] Campo titulo_pagar_id já existe")

            # 4. Adicionar campo titulo_cnpj (se não existir)
            if 'titulo_cnpj' not in colunas_existentes:
                print("\n[3/5] Adicionando campo titulo_cnpj...")
                db.session.execute(text("""
                    ALTER TABLE extrato_item
                    ADD COLUMN titulo_cnpj VARCHAR(20)
                """))
                print("  ✓ Campo titulo_cnpj adicionado")
            else:
                print("\n[3/5] Campo titulo_cnpj já existe")

            # 5. Migrar dados existentes do titulo_id para titulo_receber_id
            # (para lotes de recebimento - tipo_transacao = 'entrada' ou NULL)
            print("\n[4/5] Migrando dados de titulo_id para titulo_receber_id (lotes de recebimento)...")
            result = db.session.execute(text("""
                UPDATE extrato_item ei
                SET titulo_receber_id = titulo_id
                FROM extrato_lote el
                WHERE ei.lote_id = el.id
                AND ei.titulo_id IS NOT NULL
                AND ei.titulo_receber_id IS NULL
                AND (el.tipo_transacao = 'entrada' OR el.tipo_transacao IS NULL)
            """))
            print(f"  ✓ {result.rowcount} registros migrados para titulo_receber_id")

            # 6. Para lotes de pagamento, NÃO migrar automaticamente
            # porque o titulo_id pode estar errado (era FK para contas_a_receber)
            print("\n[5/5] Verificando lotes de pagamento...")
            result = db.session.execute(text("""
                SELECT COUNT(*)
                FROM extrato_item ei
                JOIN extrato_lote el ON ei.lote_id = el.id
                WHERE el.tipo_transacao = 'saida'
                AND ei.titulo_id IS NOT NULL
            """))
            pagamentos_com_titulo = result.scalar()
            if pagamentos_com_titulo > 0:
                print(f"  ⚠ {pagamentos_com_titulo} itens de pagamento com titulo_id preenchido")
                print("    Esses itens precisarão ser reprocessados manualmente")
                print("    (titulo_id apontava para ContasAReceber, não ContasAPagar)")
            else:
                print("  ✓ Nenhum item de pagamento com titulo_id antigo")

            # 7. Criar índices
            print("\n[6/6] Criando índices...")
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_extrato_item_titulo_receber_id
                    ON extrato_item(titulo_receber_id)
                """))
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_extrato_item_titulo_pagar_id
                    ON extrato_item(titulo_pagar_id)
                """))
                print("  ✓ Índices criados")
            except Exception as e:
                print(f"  ⚠ Índices podem já existir: {e}")

            db.session.commit()

            print("\n" + "=" * 60)
            print("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)

            # Resumo
            print("\nRESUMO:")
            print("- titulo_receber_id: FK para contas_a_receber (clientes)")
            print("- titulo_pagar_id: FK para contas_a_pagar (fornecedores)")
            print("- titulo_cnpj: Campo cache para CNPJ")
            print("- titulo_id: Mantido (deprecado) para compatibilidade")

            return True

        except Exception as e:
            print(f"\n❌ ERRO na migração: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    executar_migracao()
