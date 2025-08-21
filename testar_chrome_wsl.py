#!/usr/bin/env python3
"""
Script de teste para validar conexão com Chrome do Windows via WSL
Executa passo a passo com logs detalhados
"""

import sys
import os
import requests
import time

# Adicionar o diretório do projeto ao path
sys.path.insert(0, '/home/rafaelnascimento/projetos/frete_sistema')

def teste_1_verificar_porta():
    """Testa se a porta 9222 está acessível"""
    print("\n" + "="*60)
    print("TESTE 1: Verificar se Chrome está rodando na porta 9222")
    print("="*60)
    
    # Detectar IP do Windows
    import subprocess
    chrome_host = os.environ.get('CHROME_DEBUG_HOST')
    
    if not chrome_host:
        try:
            result = subprocess.run(
                ["awk", "/nameserver/ {print $2}", "/etc/resolv.conf"],
                capture_output=True, text=True
            )
            chrome_host = result.stdout.strip()
        except:
            chrome_host = "localhost"
    
    if not chrome_host:
        chrome_host = "localhost"
    
    print(f"Testando Chrome em: {chrome_host}:9222")
    
    try:
        response = requests.get(f'http://{chrome_host}:9222/json/version', timeout=2)
        if response.status_code == 200:
            info = response.json()
            print("✅ Chrome detectado!")
            print(f"   Navegador: {info.get('Browser', 'N/A')}")
            print(f"   Versão: {info.get('Protocol-Version', 'N/A')}")
            print(f"   WebSocket: {info.get('webSocketDebuggerUrl', 'N/A')}")
            return True
        else:
            print(f"❌ Porta responde mas com erro: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Não conseguiu conectar na porta 9222")
        print("\n🔧 SOLUÇÃO:")
        print("1. No Windows, execute o arquivo: iniciar_chrome_windows.bat")
        print("2. Ou execute manualmente:")
        print('   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222')
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def teste_2_selenium_basico():
    """Testa conexão básica do Selenium"""
    print("\n" + "="*60)
    print("TESTE 2: Conectar Selenium ao Chrome")
    print("="*60)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        print("📦 Selenium importado com sucesso")
        
        options = Options()
        options.add_experimental_option("debuggerAddress", "localhost:9222")
        
        print("🔧 Tentando conectar ao Chrome...")
        driver = webdriver.Chrome(options=options)
        
        print("✅ Conectado com sucesso!")
        print(f"   Título da página: {driver.title}")
        print(f"   URL atual: {driver.current_url}")
        
        driver.quit()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        
        # Tentar diagnosticar o problema
        if "chromedriver" in str(e).lower():
            print("\n🔧 PROBLEMA: ChromeDriver não encontrado")
            print("SOLUÇÕES:")
            print("1. Instalar ChromeDriver no WSL:")
            print("   sudo apt update && sudo apt install chromium-chromedriver")
            print("2. Ou baixar manualmente de:")
            print("   https://chromedriver.chromium.org/")
        
        return False

def teste_3_browser_manager():
    """Testa o BrowserManagerSimples"""
    print("\n" + "="*60)
    print("TESTE 3: Testar BrowserManagerSimples")
    print("="*60)
    
    try:
        from app.portal.browser_manager_simples import BrowserManagerSimples
        
        print("📦 BrowserManagerSimples importado")
        
        manager = BrowserManagerSimples()
        print("🔧 Conectando ao Chrome...")
        
        if manager.conectar_chrome_windows():
            print("✅ BrowserManagerSimples conectado!")
            
            # Testar navegação
            print("\n🌐 Testando navegação...")
            if manager.navegar("https://www.google.com"):
                print("✅ Navegou para Google")
                
                # Testar busca de elemento
                print("\n🔍 Testando busca de elemento...")
                elemento = manager.buscar_elemento('input[name="q"]')
                if elemento:
                    print("✅ Encontrou campo de busca")
                else:
                    print("⚠️ Não encontrou campo de busca")
            
            manager.fechar()
            return True
        else:
            print("❌ Falha ao conectar BrowserManagerSimples")
            return False
            
    except ImportError as e:
        print(f"❌ Erro ao importar: {e}")
        print("Certifique-se de estar no diretório correto do projeto")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def teste_4_portal_atacadao():
    """Testa acesso ao portal Atacadão"""
    print("\n" + "="*60)
    print("TESTE 4: Acessar Portal Atacadão")
    print("="*60)
    
    try:
        from app.portal.browser_manager_simples import BrowserManagerSimples
        
        manager = BrowserManagerSimples()
        
        if not manager.conectar_chrome_windows():
            print("❌ Não conseguiu conectar ao Chrome")
            return False
        
        print("🌐 Navegando para portal Atacadão...")
        url_atacadao = "https://www.atacadao.com.br/portal-vendas"
        
        if manager.navegar(url_atacadao):
            print("✅ Acessou portal Atacadão")
            time.sleep(2)  # Aguardar página carregar
            
            # Verificar se está na página de login
            print("\n🔍 Verificando página...")
            
            # Tentar encontrar campo de login
            campo_login = manager.buscar_elemento('input[type="text"], input[name="username"], input[id="username"]')
            
            if campo_login:
                print("✅ Página de login detectada")
                print("   Portal está acessível e pronto para automação!")
            else:
                print("⚠️ Não detectou campos de login")
                print("   Pode estar em outra página ou já logado")
            
            manager.fechar()
            return True
        else:
            print("❌ Falha ao navegar")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "🚀"*30)
    print("TESTE DE INTEGRAÇÃO CHROME WSL")
    print("🚀"*30)
    
    resultados = []
    
    # Teste 1: Verificar porta
    if teste_1_verificar_porta():
        resultados.append("✅ Porta 9222")
        
        # Teste 2: Selenium básico
        if teste_2_selenium_basico():
            resultados.append("✅ Selenium")
            
            # Teste 3: BrowserManager
            if teste_3_browser_manager():
                resultados.append("✅ BrowserManager")
                
                # Teste 4: Portal
                if teste_4_portal_atacadao():
                    resultados.append("✅ Portal Atacadão")
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    for resultado in resultados:
        print(resultado)
    
    if len(resultados) == 4:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("O sistema está pronto para uso!")
    else:
        print(f"\n⚠️ {len(resultados)}/4 testes passaram")
        print("Verifique os erros acima e tente novamente")
    
    return len(resultados) == 4

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)