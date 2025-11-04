"""
Teste simplificado para validar busca upstream de programações
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app
from app.manufatura.services.projecao_estoque_service import ServicoProjecaoEstoque

def testar_busca_upstream():
    """Testa se a busca upstream encontra programações corretamente"""
    app = create_app()
    with app.app_context():
        service = ServicoProjecaoEstoque()

        data_inicio = date.today()
        data_fim = date.today() + timedelta(days=30)

        print("\n" + "="*80)
        print("🧪 TESTE: Busca upstream de programações")
        print("="*80)

        # Teste 1: Produto intermediário (SALMOURA)
        print("\n📦 Teste 1: SALMOURA (301000001) - Intermediário SEM programação")
        print("   Esperado: Encontrar programações de produtos que consomem SALMOURA")

        progs_salmoura = service._buscar_programacoes_upstream(
            '301000001',
            data_inicio,
            data_fim
        )

        print(f"   Resultado: {len(progs_salmoura)} programação(ões) encontrada(s)")
        for prog, fator in progs_salmoura:
            print(f"      ✅ {prog.cod_produto}: {prog.qtd_programada} un × {fator:.4f} = {prog.qtd_programada * fator:.2f}")

        # Teste 2: Componente indireto (ACIDO CITRICO)
        print("\n📦 Teste 2: Cálculo de saídas para ACIDO CITRICO (104000002)")
        print("   Esperado: Encontrar consumo via SALMOURA → AZEITONA")

        saidas_acido = service._calcular_saidas_por_bom('104000002', data_inicio, data_fim)

        print(f"   Resultado: {len(saidas_acido)} saída(s) encontrada(s)")
        total_consumo = 0
        for saida in saidas_acido:
            print(f"      ✅ {saida['tipo']}: {saida['quantidade']:.2f} em {saida['data']}")
            print(f"         Produto: {saida.get('produto_produzido', 'N/A')}")
            if saida['tipo'] == 'CONSUMO_INDIRETO':
                print(f"         Via: {saida.get('via_intermediario', 'N/A')}")
            total_consumo += saida['quantidade']

        print(f"\n   📊 TOTAL consumido: {total_consumo:.2f}")

        # Teste 3: Componente direto (para comparação)
        print("\n📦 Teste 3: AZEITONA VERDE RECHEADA (102030601) - Componente direto")

        saidas_azeitona = service._calcular_saidas_por_bom('102030601', data_inicio, data_fim)

        print(f"   Resultado: {len(saidas_azeitona)} saída(s) encontrada(s)")
        for saida in saidas_azeitona:
            print(f"      ✅ {saida['tipo']}: {saida['quantidade']:.2f} em {saida['data']}")

if __name__ == '__main__':
    print("🚀 Iniciando teste de busca upstream...")
    testar_busca_upstream()
    print("\n" + "="*80)
    print("✅ Teste concluído!")
    print("="*80)
