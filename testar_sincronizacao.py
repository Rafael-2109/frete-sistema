#!/usr/bin/env python3
"""
Script para testar sincronização integrada
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Executa sincronização integrada completa"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*80)
        print("🚀 INICIANDO SINCRONIZAÇÃO INTEGRADA SEGURA")
        print("="*80)
        print("\nSequência de execução:")
        print("1. FATURAMENTO (importa NFs e processa movimentações)")
        print("2. CARTEIRA (sincroniza pedidos)")
        print("\nProcessamento de NFs:")
        print("- Lotes de 20 NFs com savepoints")
        print("- Retry automático para erros SSL")
        print("- Commit seguro a cada lote\n")
        
        service = SincronizacaoIntegradaService()
        
        # Executar sincronização completa
        resultado = service.executar_sincronizacao_completa_segura(
            usar_filtro_carteira=True  # Filtrar apenas pendentes
        )
        
        print("\n" + "="*80)
        print("📊 RESULTADO DA SINCRONIZAÇÃO")
        print("="*80)
        
        if resultado.get('sucesso'):
            print("✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO!")
        elif resultado.get('sucesso_parcial'):
            print("⚠️ SINCRONIZAÇÃO PARCIAL")
        else:
            print("❌ FALHA NA SINCRONIZAÇÃO")
            if resultado.get('erro'):
                print(f"Erro: {resultado['erro']}")
        
        # Estatísticas do faturamento
        fat = resultado.get('faturamento_resultado', {})
        if fat:
            print("\n📊 FATURAMENTO:")
            print(f"  - Registros importados: {fat.get('registros_importados', 0)}")
            print(f"  - Registros novos: {fat.get('registros_novos', 0)}")
            print(f"  - Registros atualizados: {fat.get('registros_atualizados', 0)}")
            
            # Detalhes do processamento de estoque
            estoque = fat.get('detalhes_estoque', {})
            if estoque:
                print(f"\n📦 MOVIMENTAÇÕES DE ESTOQUE:")
                print(f"  - NFs processadas: {estoque.get('processadas', 0)}")
                print(f"  - Já processadas: {estoque.get('ja_processadas', 0)}")
                print(f"  - Canceladas: {estoque.get('canceladas', 0)}")
                print(f"  - Com embarque: {estoque.get('com_embarque', 0)}")
                print(f"  - Sem separação: {estoque.get('sem_separacao', 0)}")
                print(f"  - Movimentações criadas: {estoque.get('movimentacoes_criadas', 0)}")
                
                erros = estoque.get('erros', [])
                if erros:
                    print(f"\n⚠️ Erros no processamento ({len(erros)} total):")
                    for erro in erros[:5]:  # Mostrar apenas 5 primeiros
                        print(f"    - {erro}")
        
        # Estatísticas da carteira
        cart = resultado.get('carteira_resultado', {})
        if cart and cart.get('sucesso'):
            stats = cart.get('estatisticas', {})
            print(f"\n🔄 CARTEIRA:")
            print(f"  - Registros inseridos: {stats.get('registros_inseridos', 0)}")
            print(f"  - Registros removidos: {stats.get('registros_removidos', 0)}")
            print(f"  - Pré-separações recompostas: {stats.get('recomposicao_sucesso', 0)}")
        
        # Tempo total
        tempo = resultado.get('tempo_total', 0)
        print(f"\n⏱️ Tempo total: {tempo:.1f} segundos")
        
        # Etapas executadas
        etapas = resultado.get('etapas_executadas', [])
        if etapas:
            print(f"\n📋 Etapas executadas: {' → '.join(etapas[-5:])}")
        
        # Alertas
        alertas = resultado.get('alertas', [])
        if alertas:
            print(f"\n⚠️ Alertas:")
            for alerta in alertas[:3]:
                print(f"  - {alerta}")
        
        print("\n" + "="*80)
        print("✅ PROCESSO FINALIZADO")
        print("="*80 + "\n")

if __name__ == "__main__":
    main()