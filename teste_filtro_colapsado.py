#!/usr/bin/env python
"""
Teste para abrir filtros colapsados e buscar pedido
"""

from playwright.sync_api import sync_playwright
import time

def teste_filtro():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="storage_state_atacadao.json")
        page = context.new_page()
        
        print("1. Abrindo página de pedidos...")
        page.goto("https://atacadao.hodiebooking.com.br/pedidos")
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        print("2. Procurando e abrindo filtros...")
        
        # Tentar várias formas de abrir os filtros
        abriu = False
        
        # Método 1: Clicar no h4 com "Filtros"
        try:
            filtro_h4 = page.locator('h4:has-text("Filtros")')
            if filtro_h4.is_visible():
                print("   Encontrado: h4 com 'Filtros'")
                filtro_h4.click()
                abriu = True
                time.sleep(1)
        except:
            pass
        
        # Método 2: Clicar em elemento com data-toggle
        if not abriu:
            try:
                toggle = page.locator('[data-toggle="collapse"]').first
                if toggle.is_visible():
                    print("   Encontrado: elemento com data-toggle")
                    toggle.click()
                    abriu = True
                    time.sleep(1)
            except:
                pass
        
        # Método 3: Clicar no painel colapsável
        if not abriu:
            try:
                panel = page.locator('.panel-heading, .card-header').first
                if panel.is_visible():
                    print("   Encontrado: panel-heading")
                    panel.click()
                    abriu = True
                    time.sleep(1)
            except:
                pass
        
        if abriu:
            print("   ✅ Filtros abertos!")
        else:
            print("   ⚠️ Não conseguiu abrir filtros automaticamente")
        
        # Verificar se o campo de pedido está visível agora
        print("\n3. Verificando visibilidade do campo de pedido...")
        campo_pedido = page.locator('#nr_pedido')
        if campo_pedido.is_visible():
            print("   ✅ Campo #nr_pedido está visível!")
            
            # Tentar preencher
            numero = input("\n4. Digite o número do pedido: ").strip()
            campo_pedido.fill(numero)
            print(f"   Preenchido com: {numero}")
            
            # Procurar botão de filtrar
            print("\n5. Procurando botão de filtrar...")
            botao = page.locator('#enviarFiltros')
            if botao.is_visible():
                print("   ✅ Botão #enviarFiltros encontrado!")
                botao.click()
                print("   Filtro enviado!")
            else:
                print("   ❌ Botão não encontrado")
                
                # Tentar alternativas
                alternativas = [
                    'button:has-text("Filtrar")',
                    'button:has-text("Buscar")',
                    'button[type="submit"]',
                    '.btn-primary:has-text("Filtrar")'
                ]
                
                for alt in alternativas:
                    try:
                        if page.locator(alt).first.is_visible():
                            print(f"   ✅ Encontrado alternativa: {alt}")
                            page.locator(alt).first.click()
                            break
                    except:
                        continue
            
            # Aguardar resultado
            print("\n6. Aguardando resultado...")
            time.sleep(5)
            
            # Verificar se encontrou
            if page.locator('a[title="Exibir"]').is_visible():
                print("   ✅ PEDIDO ENCONTRADO!")
                href = page.locator('a[title="Exibir"]').first.get_attribute('href')
                print(f"   URL: {href}")
            else:
                print("   ❌ Pedido não encontrado ou link não visível")
                
        else:
            print("   ❌ Campo #nr_pedido NÃO está visível!")
            print("   Os filtros podem não ter aberto corretamente")
        
        # Screenshot
        page.screenshot(path="teste_filtro_resultado.png")
        print("\n📸 Screenshot: teste_filtro_resultado.png")
        
        input("\n🔍 Pressione ENTER para fechar...")
        browser.close()

if __name__ == "__main__":
    print("🧪 TESTE DE FILTRO COLAPSADO")
    print("=" * 40)
    teste_filtro()