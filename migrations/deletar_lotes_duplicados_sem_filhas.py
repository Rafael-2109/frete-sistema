"""
Script para Deletar Lotes Duplicados SEM Filhas

Problema:
- Importação rodou 3 vezes
- Criou 3 cópias de cada lote
- Apenas 1 cópia tem filhas vinculadas (correta)
- 2 cópias são órfãs (sem filhas) - devem ser deletadas

Solução:
- Identificar lotes ÓRFÃOS (sem filhas vinculadas)
- Deletar apenas os lotes órfãos
- Manter os lotes que têm filhas

USO:
    python migrations/deletar_lotes_duplicados_sem_filhas.py
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
        print("🧹 DELETAR LOTES DUPLICADOS SEM FILHAS")
        print("=" * 120)

        # 1. IDENTIFICAR LOTES ÓRFÃOS (SEM FILHAS)
        print("\n1️⃣  IDENTIFICANDO LOTES SEM FILHAS (ÓRFÃOS)...")
        print("=" * 120)

        lotes_orfaos = db.session.execute(text("""
            SELECT
                l.id as lote_id,
                l.valor,
                l.data_movimentacao,
                l.descricao,
                COUNT(f.id) as qtd_filhas
            FROM movimentacao_financeira l
            LEFT JOIN movimentacao_financeira f ON f.movimentacao_origem_id = l.id
            WHERE l.categoria = 'Lote Comissão'
              AND l.tipo = 'PAGAMENTO'
              AND l.movimentacao_origem_id IS NULL
            GROUP BY l.id, l.valor, l.data_movimentacao, l.descricao
            HAVING COUNT(f.id) = 0
            ORDER BY l.id
        """)).fetchall()

        if not lotes_orfaos:
            print("\n✅ Não há lotes órfãos para deletar!")

            # Verificar se todos os lotes têm filhas
            total_lotes = db.session.execute(text("""
                SELECT COUNT(*)
                FROM movimentacao_financeira
                WHERE categoria = 'Lote Comissão'
                  AND tipo = 'PAGAMENTO'
                  AND movimentacao_origem_id IS NULL
            """)).scalar()

            print(f"   Total de lotes: {total_lotes}")
            print(f"   Todos os lotes têm filhas vinculadas ✅")
            return

        print(f"\n⚠️  Encontrados {len(lotes_orfaos)} lotes ÓRFÃOS (sem filhas)\n")

        valor_total_orfaos = Decimal('0')

        print("   EXEMPLOS (primeiros 20):")
        for i, lote in enumerate(lotes_orfaos[:20], 1):
            valor = Decimal(str(lote[1]))
            valor_total_orfaos += valor
            print(f"   {i:3}. Lote ID={lote[0]:5} | Valor: R$ {float(valor):12,.2f} | "
                  f"Data: {lote[2]} | {lote[3][:50]}")

        # Somar todos
        for lote in lotes_orfaos[20:]:
            valor_total_orfaos += Decimal(str(lote[1]))

        print(f"\n📊 RESUMO:")
        print(f"   Lotes órfãos a deletar: {len(lotes_orfaos)}")
        print(f"   Valor total a remover: R$ {float(valor_total_orfaos):,.2f}")

        # 2. VERIFICAR LOTES COM FILHAS (QUE SERÃO MANTIDOS)
        print("\n2️⃣  VERIFICANDO LOTES COM FILHAS (SERÃO MANTIDOS)...")
        print("=" * 120)

        lotes_com_filhas = db.session.execute(text("""
            SELECT
                COUNT(*) as qtd_lotes,
                SUM(l.valor) as valor_lotes,
                SUM(filhas.qtd) as total_filhas,
                SUM(filhas.soma_valor) as valor_filhas
            FROM movimentacao_financeira l
            INNER JOIN (
                SELECT
                    movimentacao_origem_id,
                    COUNT(*) as qtd,
                    SUM(valor) as soma_valor
                FROM movimentacao_financeira
                WHERE categoria = 'Comissão'
                  AND movimentacao_origem_id IS NOT NULL
                GROUP BY movimentacao_origem_id
            ) filhas ON filhas.movimentacao_origem_id = l.id
            WHERE l.categoria = 'Lote Comissão'
              AND l.tipo = 'PAGAMENTO'
        """)).fetchone()

        qtd_lotes_corretos = lotes_com_filhas[0]
        valor_lotes_corretos = Decimal(str(lotes_com_filhas[1] or 0))
        total_filhas = lotes_com_filhas[2]
        valor_filhas = Decimal(str(lotes_com_filhas[3] or 0))

        print(f"\n   Lotes COM filhas (corretos): {qtd_lotes_corretos}")
        print(f"   Valor dos lotes corretos:    R$ {float(valor_lotes_corretos):,.2f}")
        print(f"   Total de comissões filhas:   {total_filhas}")
        print(f"   Valor das filhas:            R$ {float(valor_filhas):,.2f}")

        # 3. IMPACTO NO EXTRATO
        print("\n3️⃣  IMPACTO NO EXTRATO:")
        print("=" * 120)

        extrato_antes = db.session.execute(text("""
            SELECT SUM(valor)
            FROM movimentacao_financeira
            WHERE tipo = 'PAGAMENTO'
              AND movimentacao_origem_id IS NULL
        """)).scalar()

        extrato_depois = extrato_antes - valor_total_orfaos

        print(f"   Extrato ANTES:  R$ {float(extrato_antes or 0):,.2f}")
        print(f"   Valor removido: R$ {float(valor_total_orfaos):,.2f}")
        print(f"   Extrato DEPOIS: R$ {float(extrato_depois):,.2f}")

        # 4. CONFIRMAR
        print("\n" + "=" * 120)
        print("📋 OPERAÇÃO QUE SERÁ REALIZADA:")
        print("=" * 120)
        print(f"   Deletar {len(lotes_orfaos)} lotes ÓRFÃOS (sem filhas)")
        print(f"   Manter {qtd_lotes_corretos} lotes COM filhas")
        print(f"   Redução no extrato: R$ {float(valor_total_orfaos):,.2f}")
        print(f"\n   ✅ Mantém todos os lotes corretos")
        print(f"   ✅ Mantém todas as {total_filhas} comissões filhas")
        print(f"   ✅ Remove apenas duplicatas órfãs")

        print("\n⚠️  VOCÊ DESEJA PROSSEGUIR?")
        confirmacao = input("Digite 'SIM' para confirmar: ").strip().upper()

        if confirmacao != 'SIM':
            print("\n❌ Operação cancelada.")
            return

        # 5. DELETAR LOTES ÓRFÃOS
        print("\n4️⃣  DELETANDO LOTES ÓRFÃOS...")
        print("=" * 120)

        try:
            # Pegar IDs dos lotes órfãos
            ids_deletar = [lote[0] for lote in lotes_orfaos]

            deletados = 0
            for lote_id in ids_deletar:
                db.session.execute(text("""
                    DELETE FROM movimentacao_financeira
                    WHERE id = :lote_id
                """), {'lote_id': lote_id})
                deletados += 1

            # COMMIT
            db.session.commit()

            print(f"\n✅ {deletados} lotes órfãos deletados com sucesso!")

            # 6. VERIFICAR RESULTADO
            print("\n5️⃣  VERIFICANDO RESULTADO...")
            print("=" * 120)

            # Verificar se ainda há lotes órfãos
            ainda_orfaos = db.session.execute(text("""
                SELECT COUNT(*)
                FROM movimentacao_financeira l
                LEFT JOIN movimentacao_financeira f ON f.movimentacao_origem_id = l.id
                WHERE l.categoria = 'Lote Comissão'
                  AND l.tipo = 'PAGAMENTO'
                  AND l.movimentacao_origem_id IS NULL
                GROUP BY l.id
                HAVING COUNT(f.id) = 0
            """)).scalar()

            if ainda_orfaos is None or ainda_orfaos == 0:
                print("\n   ✅ Nenhum lote órfão restante!")
            else:
                print(f"\n   ⚠️  Ainda existem {ainda_orfaos} lotes órfãos")

            # Novo valor do extrato
            novo_extrato = db.session.execute(text("""
                SELECT SUM(valor)
                FROM movimentacao_financeira
                WHERE tipo = 'PAGAMENTO'
                  AND movimentacao_origem_id IS NULL
            """)).scalar()

            print(f"\n   Novo valor do extrato: R$ {float(novo_extrato or 0):,.2f}")

            # Verificar estrutura final
            estrutura_final = db.session.execute(text("""
                SELECT
                    COUNT(DISTINCT l.id) as qtd_lotes,
                    SUM(l.valor) as valor_lotes,
                    COUNT(f.id) as qtd_filhas,
                    SUM(f.valor) as valor_filhas
                FROM movimentacao_financeira l
                INNER JOIN movimentacao_financeira f ON f.movimentacao_origem_id = l.id
                WHERE l.categoria = 'Lote Comissão'
                  AND f.categoria = 'Comissão'
            """)).fetchone()

            print(f"\n📊 ESTRUTURA FINAL:")
            print(f"   Lotes (PAI):        {estrutura_final[0]} lotes  | R$ {float(estrutura_final[1] or 0):,.2f}")
            print(f"   Comissões (FILHAS): {estrutura_final[2]} comissões | R$ {float(estrutura_final[3] or 0):,.2f}")

            dif = abs(float(estrutura_final[1] or 0) - float(estrutura_final[3] or 0))
            if dif < 1.0:
                print(f"   ✅ Lotes = Filhas (diferença: R$ {dif:.2f})")
            else:
                print(f"   ⚠️  Diferença: R$ {dif:.2f}")

            print("\n" + "=" * 120)
            print("✅✅✅ LIMPEZA CONCLUÍDA COM SUCESSO! ✅✅✅")
            print("=" * 120)
            print(f"\n📊 RESULTADO:")
            print(f"   - Lotes órfãos deletados: {deletados}")
            print(f"   - Valor removido do extrato: R$ {float(valor_total_orfaos):,.2f}")
            print(f"   - Novo valor do extrato: R$ {float(novo_extrato or 0):,.2f}")
            print(f"\n✅ Atualize a página do extrato para ver o valor correto!")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            print(traceback.format_exc())


if __name__ == '__main__':
    main()
