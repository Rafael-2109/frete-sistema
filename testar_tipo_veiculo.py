#!/usr/bin/env python3
"""
Script para testar a determinação automática do tipo de veículo
baseado no peso total da separação
"""

import sys
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient

def main():
    print("\n" + "🚚"*30)
    print("TESTE DE SELEÇÃO AUTOMÁTICA DE VEÍCULO")
    print("🚚"*30)
    
    print("\n📋 REGRAS DE SELEÇÃO:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Até 2.000 kg  → F4000-3/4 (ID: 5)")
    print("  Até 4.000 kg  → Toco-Baú (ID: 11)")
    print("  Até 7.000 kg  → Truck-Baú (ID: 8)")
    print("  Acima 7.000 kg → Carreta-Baú (ID: 2)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Criar cliente para testar
    client = AtacadaoPlaywrightClient(headless=True)
    
    # Casos de teste
    casos_teste = [
        (500, "F4000-3/4", "5"),
        (1500, "F4000-3/4", "5"),
        (2000, "F4000-3/4", "5"),
        (2001, "Toco-Baú", "11"),
        (3500, "Toco-Baú", "11"),
        (4000, "Toco-Baú", "11"),
        (4001, "Truck-Baú", "8"),
        (5500, "Truck-Baú", "8"),
        (7000, "Truck-Baú", "8"),
        (7001, "Carreta-Baú", "2"),
        (10000, "Carreta-Baú", "2"),
        (15000, "Carreta-Baú", "2"),
    ]
    
    print("\n🧪 EXECUTANDO TESTES:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    todos_passaram = True
    
    for peso, veiculo_esperado, id_esperado in casos_teste:
        # Testar determinação
        id_resultado = client.determinar_tipo_veiculo_por_peso(peso)
        
        # Verificar resultado
        if id_resultado == id_esperado:
            status = "✅ PASSOU"
        else:
            status = "❌ FALHOU"
            todos_passaram = False
        
        print(f"  {peso:,} kg → ID: {id_resultado} {status}")
        
        if id_resultado != id_esperado:
            print(f"      Esperado: {id_esperado} ({veiculo_esperado})")
            print(f"      Recebido: {id_resultado}")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if todos_passaram:
        print("\n✅ TODOS OS TESTES PASSARAM!")
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
    
    # Teste interativo
    print("\n" + "="*50)
    continuar = input("\nDeseja testar com um valor específico? (s/n): ")
    
    if continuar.lower() == 's':
        while True:
            try:
                peso_str = input("\nDigite o peso em kg (ou 'sair'): ")
                
                if peso_str.lower() == 'sair':
                    break
                
                peso = float(peso_str.replace(',', '.'))
                
                # Determinar tipo
                tipo_id = client.determinar_tipo_veiculo_por_peso(peso)
                
                # Mapear ID para nome
                mapa_veiculos = {
                    '5': 'F4000-3/4 (até 2.000 kg)',
                    '11': 'Toco-Baú (até 4.000 kg)',
                    '8': 'Truck-Baú (até 7.000 kg)',
                    '2': 'Carreta-Baú (acima de 7.000 kg)'
                }
                
                veiculo_nome = mapa_veiculos.get(tipo_id, 'Desconhecido')
                
                print(f"\n📦 Peso: {peso:,.2f} kg")
                print(f"🚚 Veículo selecionado: {veiculo_nome}")
                print(f"🔢 ID no portal: {tipo_id}")
                
            except ValueError:
                print("❌ Valor inválido. Digite apenas números.")
            except Exception as e:
                print(f"❌ Erro: {e}")
    
    # Limpar recursos
    client.fechar()
    print("\n👋 Teste finalizado!")

if __name__ == "__main__":
    main()