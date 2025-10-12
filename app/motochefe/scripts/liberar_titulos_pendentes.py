"""
Script de Migração: Liberar TituloAPagar PENDENTES cujo TituloFinanceiro está PAGO

Execução LOCAL:
    python3 app/motochefe/scripts/liberar_titulos_pendentes.py

Execução RENDER (SQL):
    -- Ver script SQL no final deste arquivo
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from app.motochefe.models.financeiro import TituloAPagar, TituloFinanceiro
from datetime import date

def liberar_titulos_pendentes():
    """
    Libera títulos a pagar que estão PENDENTES mas cujo título origem está PAGO

    LÓGICA:
    - TituloFinanceiro.status = 'PAGO' → Cliente já pagou
    - TituloAPagar.status = 'PENDENTE' → Empresa ainda não pode pagar
    - CORRIGIR: TituloAPagar.status → 'ABERTO' (permitir pagamento)
    """
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("🔓 LIBERAÇÃO DE TÍTULOS A PAGAR PENDENTES")
        print("=" * 80)

        # Buscar todos os títulos a pagar PENDENTES
        titulos_pendentes = TituloAPagar.query.filter_by(status='PENDENTE').all()

        print(f"\n📊 Total de títulos PENDENTES: {len(titulos_pendentes)}")

        liberados = 0
        ja_liberados = 0
        sem_titulo_origem = 0

        for titulo_pagar in titulos_pendentes:
            # Buscar título financeiro origem
            titulo_origem = titulo_pagar.titulo_origem

            if not titulo_origem:
                sem_titulo_origem += 1
                print(f"   ⚠️ TituloAPagar #{titulo_pagar.id} sem título origem")
                continue

            # Verificar se título origem está PAGO
            if titulo_origem.status == 'PAGO':
                # LIBERAR!
                print(f"\n   🔓 Liberando TituloAPagar #{titulo_pagar.id}:")
                print(f"      Tipo: {titulo_pagar.tipo}")
                print(f"      Pedido: {titulo_pagar.pedido_id}")
                print(f"      Chassi: {titulo_pagar.numero_chassi[:15] if titulo_pagar.numero_chassi else 'N/A'}")
                print(f"      Valor: R$ {float(titulo_pagar.valor_saldo):.2f}")
                print(f"      TituloFinanceiro #{titulo_origem.id}: {titulo_origem.status}")

                # Atualizar status
                titulo_pagar.status = 'ABERTO'
                titulo_pagar.data_liberacao = date.today()

                liberados += 1
            else:
                ja_liberados += 1
                # print(f"   ℹ️ TituloAPagar #{titulo_pagar.id} aguardando pagamento do cliente (TF #{titulo_origem.id}: {titulo_origem.status})")

        # Commit
        db.session.commit()

        print("\n" + "=" * 80)
        print("📊 RESULTADO:")
        print(f"   Total processados: {len(titulos_pendentes)}")
        print(f"   Liberados agora: {liberados}")
        print(f"   Aguardando cliente: {ja_liberados}")
        print(f"   Sem título origem: {sem_titulo_origem}")
        print("=" * 80)

        if liberados > 0:
            print(f"\n✅ {liberados} título(s) liberado(s) com sucesso!")
            print("   Agora você pode pagar esses títulos em Contas a Pagar ou Títulos a Pagar")
        else:
            print("\n✅ Nenhum título precisou ser liberado (todos já estão corretos)")


if __name__ == '__main__':
    liberar_titulos_pendentes()


"""
================================================================================
SCRIPT SQL PARA RENDER (executar no Shell do Render)
================================================================================

-- 1. Verificar títulos pendentes com origem paga
SELECT
    tap.id,
    tap.tipo,
    tap.pedido_id,
    tap.numero_chassi,
    tap.status AS status_titulo_pagar,
    tf.id AS titulo_financeiro_id,
    tf.status AS status_titulo_financeiro
FROM titulo_a_pagar tap
INNER JOIN titulo_financeiro tf ON tap.titulo_financeiro_id = tf.id
WHERE tap.status = 'PENDENTE'
  AND tf.status = 'PAGO';

-- 2. Liberar títulos pendentes cujo título origem está pago
UPDATE titulo_a_pagar
SET
    status = 'ABERTO',
    data_liberacao = CURRENT_DATE
WHERE status = 'PENDENTE'
  AND titulo_financeiro_id IN (
      SELECT id
      FROM titulo_financeiro
      WHERE status = 'PAGO'
  );

-- 3. Verificar resultado
SELECT status, COUNT(*)
FROM titulo_a_pagar
WHERE tipo IN ('MOVIMENTACAO', 'MONTAGEM')
GROUP BY status;

================================================================================
"""
