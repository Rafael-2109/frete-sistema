#!/usr/bin/env python
"""
Teste simples e direto de busca no portal
"""

from playwright.sync_api import sync_playwright
import time

def teste_simples():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        # Carregar sessão
        context = browser.new_context(storage_state="storage_state_atacadao.json")
        page = context.new_page()
        
        # Ir para pedidos
        print("1. Abrindo página de pedidos...")
        page.goto("https://atacadao.hodiebooking.com.br/pedidos")
        page.wait_for_load_state('networkidle')
        
        # Limpar filtros de data
        print("2. Limpando filtros...")
        botoes_x = page.locator('button[data-action="remove"]').all()
        for botao in botoes_x:
            if botao.is_visible():
                botao.click()
                time.sleep(0.5)
        
        # Buscar pedido
        numero = input("3. Digite o número do pedido: ").strip()
        
        print(f"4. Buscando {numero}...")
        page.fill("#nr_pedido", numero)
        page.click("#enviarFiltros")
        
        print("5. Aguardando resultado...")
        time.sleep(5)  # Espera simples
        
        # Verificar resultado
        print("\n6. Verificando resultado...")
        
        # Tentar encontrar link de exibir de várias formas
        seletores = [
            'a[title="Exibir"]',
            'a[title="exibir"]',
            'a:has-text("Exibir")',
            'a.btn-primary',
            'a.btn[href*="/pedidos/"]',
            'table a[href*="/pedidos/"]'
        ]
        
        encontrado = False
        for seletor in seletores:
            try:
                if page.locator(seletor).first.is_visible():
                    print(f"   ✅ Link encontrado com seletor: {seletor}")
                    encontrado = True
                    
                    # Pegar href
                    href = page.locator(seletor).first.get_attribute('href')
                    print(f"   URL do pedido: {href}")
                    
                    # Clicar
                    page.locator(seletor).first.click()
                    break
            except:
                continue
        
        if not encontrado:
            print("   ❌ Nenhum link de exibir encontrado")
            
            # Verificar se tem tabela com dados
            if page.locator('table tbody tr').count() > 0:
                print("   ⚠️ Mas há linhas na tabela!")
                
                # Pegar HTML da primeira linha
                primeira_linha = page.locator('table tbody tr').first.inner_html()
                print(f"\n   HTML da primeira linha:\n   {primeira_linha[:500]}")
        
        # Screenshot
        page.screenshot(path="teste_busca_resultado.png")
        print("\n📸 Screenshot: teste_busca_resultado.png")
        
        input("\n🔍 Pressione ENTER para fechar...")
        browser.close()

if __name__ == "__main__":
    print("🧪 TESTE SIMPLES DE BUSCA")
    print("=" * 40)
    teste_simples()