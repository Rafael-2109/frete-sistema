"""
Script para Limpar Movimentações de Montagem Duplicadas

Problema identificado:
- Há 3.378 MovimentacaoFinanceira de pagamento de montagem
- Mas apenas 1.779 TituloAPagar de montagem (correto)
- Cada pedido+chassi tem 2 movimentações idênticas
- Valor duplicado: R$ 115.782,44

Solução:
- Identifica movimentações duplicadas (mesmo pedido+chassi)
- Mantém apenas a PRIMEIRA (menor ID)
- Deleta as duplicadas
- Ajusta o saldo da Sogima (+R$ 115.782,44)

USO:
    python migrations/limpar_movimentacoes_montagem_duplicadas.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text
from decimal import Decimal

def main():
    app = create_app()

    with app.app_context():
        print("\n" + "=" * 120)
        print("🧹 LIMPEZA DE MOVIMENTAÇÕES DE MONTAGEM DUPLICADAS")
        print("=" * 120)

        # 1. IDENTIFICAR DUPLICATAS
        print("\n1️⃣  IDENTIFICANDO MOVIMENTAÇÕES DUPLICADAS...")
        print("=" * 120)

        resultado = db.session.execute(text("""
            SELECT
                pedido_id,
                UPPER(numero_chassi) as chassi_upper,
                COUNT(*) as qtd,
                ARRAY_AGG(id ORDER BY id) as ids,
                ARRAY_AGG(valor ORDER BY id) as valores
            FROM movimentacao_financeira
            WHERE categoria = 'Montagem'
              AND tipo = 'PAGAMENTO'
              AND empresa_origem_id = (SELECT id FROM empresa_venda_moto WHERE empresa = 'SOGIMA')
            GROUP BY pedido_id, UPPER(numero_chassi)
            HAVING COUNT(*) > 1
        """)).fetchall()

        if not resultado:
            print("\n✅ Nenhuma duplicata encontrada!")
            return

        print(f"\n⚠️  Encontradas {len(resultado)} grupos com movimentações duplicadas\n")

        total_a_deletar = 0
        valor_a_devolver = Decimal('0')
        ids_deletar = []

        for row in resultado:
            qtd_duplicadas = row[2] - 1  # Mantém a primeira, deleta o resto
            ids_duplicados = row[3][1:]  # Pega todos exceto o primeiro
            valores_duplicados = row[4][1:]

            total_a_deletar += qtd_duplicadas
            for v in valores_duplicados:
                valor_a_devolver += Decimal(str(v))

            ids_deletar.extend(ids_duplicados)

            print(f"   Pedido: {row[0]:6} | Chassi: {row[1]:20} | "
                  f"Total: {row[2]} | MANTER: ID={row[3][0]} | "
                  f"DELETAR: {list(ids_duplicados)}")

        print(f"\n📊 RESUMO:")
        print(f"   Movimentações a deletar: {total_a_deletar}")
        print(f"   Valor a devolver ao saldo Sogima: R$ {float(valor_a_devolver):,.2f}")

        # 2. CONFIRMAR
        print("\n" + "=" * 120)
        print("⚠️  VOCÊ DESEJA PROSSEGUIR COM A LIMPEZA?")
        confirmacao = input("Digite 'SIM' para confirmar: ").strip().upper()

        if confirmacao != 'SIM':
            print("\n❌ Operação cancelada.")
            return

        # 3. DELETAR MOVIMENTAÇÕES DUPLICADAS
        print("\n2️⃣  DELETANDO MOVIMENTAÇÕES DUPLICADAS...")
        print("=" * 120)

        try:
            deletados = 0
            for mov_id in ids_deletar:
                db.session.execute(text("""
                    DELETE FROM movimentacao_financeira WHERE id = :id
                """), {'id': mov_id})
                deletados += 1

            print(f"\n✅ {deletados} movimentações deletadas")

            # 4. AJUSTAR SALDO DA SOGIMA
            print("\n3️⃣  AJUSTANDO SALDO DA SOGIMA...")
            print("=" * 120)

            # Buscar saldo atual
            sogima = db.session.execute(text("""
                SELECT id, saldo, empresa
                FROM empresa_venda_moto
                WHERE empresa = 'SOGIMA'
            """)).fetchone()

            saldo_anterior = Decimal(str(sogima[1]))
            saldo_novo = saldo_anterior + valor_a_devolver  # SOMA porque estava subtraindo indevidamente

            print(f"\n   Empresa: {sogima[2]}")
            print(f"   Saldo Anterior: R$ {float(saldo_anterior):15,.2f}")
            print(f"   Ajuste:         R$ {float(valor_a_devolver):+15,.2f}")
            print(f"   Saldo Novo:     R$ {float(saldo_novo):15,.2f}")

            # Atualizar saldo
            db.session.execute(text("""
                UPDATE empresa_venda_moto
                SET saldo = :saldo_novo,
                    atualizado_em = NOW()
                WHERE id = :id
            """), {'saldo_novo': float(saldo_novo), 'id': sogima[0]})

            # COMMIT
            db.session.commit()

            print("\n" + "=" * 120)
            print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
            print("=" * 120)
            print(f"\n📊 RESULTADO:")
            print(f"   Movimentações deletadas: {deletados}")
            print(f"   Saldo ajustado: R$ {float(valor_a_devolver):+,.2f}")
            print(f"   Novo saldo Sogima: R$ {float(saldo_novo):,.2f}")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            print(traceback.format_exc())


if __name__ == '__main__':
    main()
