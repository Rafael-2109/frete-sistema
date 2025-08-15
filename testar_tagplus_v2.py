#!/usr/bin/env python3
"""
Script de Teste do TagPlus API v2 com OAuth2
"""

from datetime import datetime, timedelta
from app import create_app
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("TESTE DO TAGPLUS API V2")
        print("=" * 70)
        
        print("\n⚠️  IMPORTANTE:")
        print("Este teste requer que você já tenha autorizado as APIs.")
        print("Se ainda não autorizou, acesse:")
        print("https://sistema-fretes.onrender.com/tagplus/oauth/")
        print("ou execute: python autorizar_tagplus.py")
        print("=" * 70)
        
        # Opção de configurar tokens manualmente para teste
        print("\n📝 Configuração de Tokens")
        print("1. Usar tokens da sessão (se já autorizou via web)")
        print("2. Inserir tokens manualmente")
        print("3. Pular e tentar com tokens existentes")
        
        opcao = input("\nOpção [3]: ").strip() or "3"
        
        if opcao == "2":
            print("\n📝 Configuração Manual de Tokens")
            print("-" * 40)
            
            # Tokens para API de Clientes
            print("\nAPI de CLIENTES:")
            token_clientes = input("Access Token (deixe vazio para pular): ").strip()
            if token_clientes:
                oauth_clientes = TagPlusOAuth2V2(api_type='clientes')
                oauth_clientes.set_tokens(token_clientes)
                print("✅ Token de clientes configurado")
            
            # Tokens para API de Notas
            print("\nAPI de NOTAS:")
            token_notas = input("Access Token (deixe vazio para pular): ").strip()
            if token_notas:
                oauth_notas = TagPlusOAuth2V2(api_type='notas')
                oauth_notas.set_tokens(token_notas)
                print("✅ Token de notas configurado")
        
        # Cria importador
        print("\n🚀 Criando importador...")
        importador = ImportadorTagPlusV2()
        
        # Testa conexões
        print("\n🔍 Testando conexões...")
        resultado_teste = importador.testar_conexoes()
        
        print("\n📊 Status das APIs:")
        print(f"   Clientes: {'✅ OK' if resultado_teste['clientes']['sucesso'] else '❌ FALHOU'}")
        if not resultado_teste['clientes']['sucesso']:
            print(f"      Erro: {resultado_teste['clientes']['info']}")
        
        print(f"   Notas: {'✅ OK' if resultado_teste['notas']['sucesso'] else '❌ FALHOU'}")
        if not resultado_teste['notas']['sucesso']:
            print(f"      Erro: {resultado_teste['notas']['info']}")
        
        # Se ambas falharam
        if not resultado_teste['clientes']['sucesso'] and not resultado_teste['notas']['sucesso']:
            print("\n❌ Ambas as APIs falharam.")
            print("\n💡 Solução:")
            print("1. Acesse https://sistema-fretes.onrender.com/tagplus/oauth/")
            print("2. Faça login no sistema")
            print("3. Clique em 'Autorizar API de Clientes'")
            print("4. Clique em 'Autorizar API de Notas'")
            print("5. Execute este script novamente")
            return
        
        # Menu de teste
        print("\n" + "=" * 70)
        print("O que deseja testar?")
        print("1. Importar clientes")
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
            print("📥 IMPORTANDO CLIENTES")
            print("=" * 70)
            
            limite = input("Quantos clientes? [10]: ").strip()
            limite = int(limite) if limite else 10
            
            resultado = importador.importar_clientes(limite=limite)
            
            print(f"\n✅ Resultado:")
            print(f"   Importados: {resultado['importados']}")
            print(f"   Atualizados: {resultado['atualizados']}")
            if resultado['erros']:
                print(f"   ⚠️  Erros: {len(resultado['erros'])}")
                for erro in resultado['erros'][:3]:
                    print(f"      - {erro}")
        
        # Importar NFs
        if opcao in ["2", "3"] and resultado_teste['notas']['sucesso']:
            print("\n" + "=" * 70)
            print("📥 IMPORTANDO NOTAS FISCAIS")
            print("=" * 70)
            
            dias = input("NFs dos últimos quantos dias? [7]: ").strip()
            dias = int(dias) if dias else 7
            
            limite = input("Limite de NFs? [10]: ").strip()
            limite = int(limite) if limite else 10
            
            data_fim = datetime.now().date()
            data_inicio = data_fim - timedelta(days=dias)
            
            print(f"\nImportando de {data_inicio} até {data_fim}...")
            
            resultado = importador.importar_nfs(
                data_inicio=data_inicio,
                data_fim=data_fim,
                limite=limite
            )
            
            print(f"\n✅ Resultado:")
            print(f"   NFs importadas: {resultado['nfs']['importadas']}")
            print(f"   Itens importados: {resultado['nfs']['itens']}")
            
            if resultado['nfs']['erros']:
                print(f"   ⚠️  Erros: {len(resultado['nfs']['erros'])}")
                for erro in resultado['nfs']['erros'][:3]:
                    print(f"      - {erro}")
            
            if resultado.get('processamento'):
                proc = resultado['processamento']
                print(f"\n📊 Processamento:")
                if proc.get('success'):
                    print(f"   NFs processadas: {proc.get('nfs_processadas', 0)}")
                    print(f"   Movimentações: {proc.get('movimentacoes_criadas', 0)}")
                else:
                    print(f"   ❌ Erro: {proc.get('erro')}")
        
        print("\n" + "=" * 70)
        print("✅ TESTE CONCLUÍDO!")
        print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelado.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()