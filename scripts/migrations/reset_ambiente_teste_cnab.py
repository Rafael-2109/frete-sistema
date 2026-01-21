"""
Script para RESETAR o ambiente de teste CNAB + Extrato.

ESCOPO ESPECÍFICO:
- Exclui TODOS os lotes e itens CNAB
- Reseta extratos do lote 14 para PENDENTE
- Reseta APENAS os 4 títulos vinculados: 111, 1650, 3185, 3381

Uso:
    source .venv/bin/activate
    python scripts/migrations/reset_ambiente_teste_cnab.py

Data: 2026-01-21
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

# IDs específicos dos títulos vinculados ao Extrato Lote 14 e CNABs
TITULOS_A_RESETAR = [111, 1650, 3185, 3381]


def main():
    app = create_app()
    with app.app_context():
        print("\n" + "="*70)
        print("🔄 RESET DO AMBIENTE DE TESTE - CNAB + EXTRATO (LOTE 14)")
        print("="*70)

        try:
            # =========================================================
            # PASSO 1: Estado ANTES do reset
            # =========================================================
            print("\n📊 PASSO 1: Estado ANTES do reset...")

            result = db.session.execute(text("SELECT COUNT(*) FROM cnab_retorno_lote"))
            total_lotes = result.scalar()
            print(f"   Lotes CNAB: {total_lotes}")

            result = db.session.execute(text("SELECT COUNT(*) FROM cnab_retorno_item"))
            total_itens = result.scalar()
            print(f"   Itens CNAB: {total_itens}")

            result = db.session.execute(text("""
                SELECT COUNT(*) FROM extrato_item
                WHERE lote_id = 14 AND status = 'CONCILIADO'
            """))
            extratos_conciliados = result.scalar()
            print(f"   Extratos CONCILIADO (Lote 14): {extratos_conciliados}")

            result = db.session.execute(text("""
                SELECT COUNT(*) FROM contas_a_receber
                WHERE id = ANY(:ids) AND parcela_paga = TRUE
            """), {'ids': TITULOS_A_RESETAR})
            titulos_pagos = result.scalar()
            print(f"   Títulos pagos (a resetar): {titulos_pagos}")

            # =========================================================
            # PASSO 2: Excluir itens CNAB
            # =========================================================
            print("\n🗑️  PASSO 2: Excluindo itens CNAB...")

            result = db.session.execute(text("DELETE FROM cnab_retorno_item"))
            print(f"   ✓ {result.rowcount} itens CNAB excluídos")

            # =========================================================
            # PASSO 3: Excluir lotes CNAB
            # =========================================================
            print("\n🗑️  PASSO 3: Excluindo lotes CNAB...")

            result = db.session.execute(text("DELETE FROM cnab_retorno_lote"))
            print(f"   ✓ {result.rowcount} lotes CNAB excluídos")

            # =========================================================
            # PASSO 4: Resetar extratos do lote 14
            # =========================================================
            print("\n🔄 PASSO 4: Resetando extratos do lote 14...")

            result = db.session.execute(text("""
                UPDATE extrato_item
                SET
                    status = 'PENDENTE',
                    status_match = 'PENDENTE',
                    titulo_receber_id = NULL,
                    titulo_nf = NULL,
                    titulo_parcela = NULL,
                    titulo_valor = NULL,
                    titulo_cliente = NULL,
                    titulo_cnpj = NULL,
                    match_score = NULL,
                    match_criterio = NULL,
                    aprovado = FALSE,
                    aprovado_por = NULL,
                    aprovado_em = NULL,
                    processado_em = NULL,
                    mensagem = NULL
                WHERE lote_id = 14
            """))
            print(f"   ✓ {result.rowcount} extratos resetados para PENDENTE")

            # =========================================================
            # PASSO 5: Resetar APENAS os 4 títulos específicos
            # =========================================================
            print("\n🔄 PASSO 5: Resetando títulos específicos...")
            print(f"   IDs: {TITULOS_A_RESETAR}")

            result = db.session.execute(text("""
                UPDATE contas_a_receber
                SET
                    parcela_paga = FALSE,
                    status_pagamento_odoo = NULL
                WHERE id = ANY(:ids)
            """), {'ids': TITULOS_A_RESETAR})
            print(f"   ✓ {result.rowcount} títulos resetados (parcela_paga = FALSE)")

            # =========================================================
            # PASSO 6: Commit
            # =========================================================
            db.session.commit()

            # =========================================================
            # PASSO 7: Verificação pós-reset
            # =========================================================
            print("\n✅ PASSO 6: Verificação pós-reset...")

            result = db.session.execute(text("SELECT COUNT(*) FROM cnab_retorno_lote"))
            print(f"   Lotes CNAB: {result.scalar()} (esperado: 0)")

            result = db.session.execute(text("SELECT COUNT(*) FROM cnab_retorno_item"))
            print(f"   Itens CNAB: {result.scalar()} (esperado: 0)")

            result = db.session.execute(text("""
                SELECT COUNT(*) FROM extrato_item
                WHERE lote_id = 14 AND status = 'PENDENTE'
            """))
            print(f"   Extratos PENDENTE (Lote 14): {result.scalar()}")

            result = db.session.execute(text("""
                SELECT id, titulo_nf, parcela, parcela_paga
                FROM contas_a_receber
                WHERE id = ANY(:ids)
                ORDER BY id
            """), {'ids': TITULOS_A_RESETAR})
            print("\n   Títulos resetados:")
            for r in result.fetchall():
                status = "✓ OK" if not r[3] else "✗ AINDA PAGO"
                print(f"      ID {r[0]}: NF {r[1]}/{r[2]} - {status}")

            print("\n" + "="*70)
            print("✅ RESET CONCLUÍDO COM SUCESSO!")
            print("="*70)
            print("\n📌 PRÓXIMOS PASSOS:")
            print("   1. Importar arquivo CNAB novamente")
            print("   2. Verificar matching automático com título E extrato")
            print("   3. Executar baixas")
            print("   4. Verificar conciliação no Odoo")
            print()

            return 0

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())
