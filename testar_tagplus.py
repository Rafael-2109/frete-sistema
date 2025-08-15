#!/usr/bin/env python3
"""
Script de Teste do TagPlus com APIs Duais
Testa a conexão e importação usando as duas APIs separadas
"""

from datetime import datetime, timedelta
from app import create_app
from app.integracoes.tagplus.importador_dual import ImportadorTagPlusDual
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Função principal de teste"""
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("TESTE DO TAGPLUS - APIs DUAIS")
        print("=" * 70)
        print("\nUsando credenciais:")
        print("- API Clientes: FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD")
        print("- API Notas: 8YZNqaklKj3CfIkOtkoV9ILpCllAtalT")
        print("=" * 70)
        
        # Cria importador
        print("\n1️⃣ Criando importador dual...")
        importador = ImportadorTagPlusDual()
        
        # Testa conexões
        print("\n2️⃣ Testando conexões com as APIs...")
        resultado_teste = importador.testar_conexoes()
        
        print("\n📊 Resultado dos testes:")
        print(f"   API Clientes: {'✅ OK' if resultado_teste['clientes']['sucesso'] else '❌ FALHOU'}")
        if not resultado_teste['clientes']['sucesso']:
            print(f"      Erro: {resultado_teste['clientes']['info']}")
        
        print(f"   API Notas: {'✅ OK' if resultado_teste['notas']['sucesso'] else '❌ FALHOU'}")
        if not resultado_teste['notas']['sucesso']:
            print(f"      Erro: {resultado_teste['notas']['info']}")
        
        # Se ambas falharam, para aqui
        if not resultado_teste['clientes']['sucesso'] and not resultado_teste['notas']['sucesso']:
            print("\n❌ Ambas as APIs falharam. Verifique as credenciais.")
            return
        
        # Menu de opções
        print("\n" + "=" * 70)
        print("O que deseja testar?")
        print("1. Importar alguns clientes")
        print("2. Importar NFs recentes")
        print("3. Importar ambos")
        print("0. Sair")
        
        opcao = input("\nOpção: ").strip()
        
        if opcao == "0":
            print("Saindo...")
            return
        
        # Importar clientes
        if opcao in ["1", "3"] and resultado_teste['clientes']['sucesso']:
            print("\n" + "=" * 70)
            print("3️⃣ IMPORTANDO CLIENTES")
            print("=" * 70)
            
            limite = input("Quantos clientes importar? [10]: ").strip()
            limite = int(limite) if limite else 10
            
            resultado_clientes = importador.importar_clientes(limite=limite)
            
            print(f"\n📊 Resultado:")
            print(f"   ✅ Importados: {resultado_clientes['importados']}")
            print(f"   📝 Atualizados: {resultado_clientes['atualizados']}")
            if resultado_clientes['erros']:
                print(f"   ⚠️  Erros: {len(resultado_clientes['erros'])}")
                for erro in resultado_clientes['erros'][:3]:
                    print(f"      - {erro}")
        
        # Importar NFs
        if opcao in ["2", "3"] and resultado_teste['notas']['sucesso']:
            print("\n" + "=" * 70)
            print("4️⃣ IMPORTANDO NOTAS FISCAIS")
            print("=" * 70)
            
            dias = input("Importar NFs dos últimos quantos dias? [7]: ").strip()
            dias = int(dias) if dias else 7
            
            limite = input("Limite de NFs? [10]: ").strip()
            limite = int(limite) if limite else 10
            
            data_fim = datetime.now().date()
            data_inicio = data_fim - timedelta(days=dias)
            
            print(f"\nImportando NFs de {data_inicio} até {data_fim} (limite: {limite})...")
            
            resultado_nfs = importador.importar_nfs(
                data_inicio=data_inicio,
                data_fim=data_fim,
                limite=limite
            )
            
            print(f"\n📊 Resultado:")
            print(f"   ✅ NFs importadas: {resultado_nfs['nfs']['importadas']}")
            print(f"   📦 Itens importados: {resultado_nfs['nfs']['itens']}")
            
            if resultado_nfs['nfs']['erros']:
                print(f"   ⚠️  Erros: {len(resultado_nfs['nfs']['erros'])}")
                for erro in resultado_nfs['nfs']['erros'][:3]:
                    print(f"      - {erro}")
            
            # Mostra processamento
            if resultado_nfs.get('processamento'):
                proc = resultado_nfs['processamento']
                print(f"\n📊 Processamento do faturamento:")
                if proc.get('success'):
                    print(f"   ✅ NFs processadas: {proc.get('nfs_processadas', 0)}")
                    print(f"   🏭 Movimentações criadas: {proc.get('movimentacoes_criadas', 0)}")
                else:
                    print(f"   ❌ Erro: {proc.get('erro')}")
        
        print("\n" + "=" * 70)
        print("✅ TESTE CONCLUÍDO!")
        print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperação cancelada.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()