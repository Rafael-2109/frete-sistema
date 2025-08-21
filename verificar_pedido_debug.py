#!/usr/bin/env python
"""
Verificar o que está acontecendo com a busca do pedido
"""

from playwright.sync_api import sync_playwright
import time

def debug_busca():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="storage_state_atacadao.json")
        page = context.new_page()
        
        print("1. Abrindo página de pedidos...")
        page.goto("https://atacadao.hodiebooking.com.br/pedidos")
        page.wait_for_load_state('networkidle')
        
        print("\n2. Estado inicial dos filtros:")
        
        # Verificar se filtros estão visíveis
        if page.locator('#nr_pedido').is_visible():
            print("   ✅ Filtros já estão abertos")
        else:
            print("   ⚠️ Filtros estão fechados, abrindo...")
            page.locator('a[data-toggle="collapse"][data-target="#filtros-collapse"]').click()
            time.sleep(2)
        
        # Verificar campo de data
        data_elaboracao = page.locator('#dthr_elaboracao')
        if data_elaboracao.is_visible():
            valor = data_elaboracao.input_value()
            print(f"   📅 Data elaboração atual: '{valor}'")
            
            if valor:
                print("   🧹 Limpando data...")
                # Clicar no botão X da data
                page.locator('button[data-target_daterangepicker="dthr_elaboracao"][data-action="remove"]').click()
                time.sleep(1)
                novo_valor = data_elaboracao.input_value()
                print(f"   📅 Data após limpar: '{novo_valor}'")
        
        print("\n3. Buscando pedido 606833...")
        page.fill('#nr_pedido', '606833')
        
        print("4. Clicando em filtrar...")
        page.click('#enviarFiltros')
        
        print("5. Aguardando resultado (10 segundos)...")
        time.sleep(10)
        
        print("\n6. Analisando resultado:")
        
        # Verificar se há resultados na tabela
        linhas = page.locator('table tbody tr').count()
        print(f"   📊 Linhas na tabela: {linhas}")
        
        if linhas > 0:
            print("   ✅ HÁ RESULTADOS!")
            
            # Pegar dados da primeira linha
            primeira_linha = page.locator('table tbody tr').first
            colunas = primeira_linha.locator('td').all()
            
            if len(colunas) > 1:
                pedido = colunas[0].text_content()
                pedido_original = colunas[1].text_content()
                print(f"   Pedido: {pedido}")
                print(f"   Pedido Original: {pedido_original}")
                
                # Verificar link
                link = primeira_linha.locator('a[title="Exibir"]')
                if link.is_visible():
                    href = link.get_attribute('href')
                    print(f"   ✅ Link encontrado: {href}")
                else:
                    print("   ❌ Link não encontrado")
        else:
            print("   ❌ TABELA VAZIA!")
            
            # Verificar mensagem de erro
            if "Nenhum registro encontrado" in page.content():
                print("   Mensagem: 'Nenhum registro encontrado'")
            
            # Verificar se a data voltou
            valor_data = page.locator('#dthr_elaboracao').input_value()
            if valor_data:
                print(f"   ⚠️ ATENÇÃO: Data preenchida novamente: '{valor_data}'")
                print("   Isso pode estar filtrando os resultados!")
        
        # Screenshot
        page.screenshot(path="debug_busca_606833.png")
        print("\n📸 Screenshot: debug_busca_606833.png")
        
        print("\n7. Testando busca direta por URL...")
        page.goto("https://atacadao.hodiebooking.com.br/pedidos/912933499")
        time.sleep(3)
        
        if "/pedidos/912933499" in page.url:
            print("   ✅ Pedido aberto diretamente pela URL!")
            page.screenshot(path="debug_pedido_direto.png")
            print("   📸 Screenshot: debug_pedido_direto.png")
        else:
            print(f"   ❌ Redirecionado para: {page.url}")
        
        input("\n🔍 Pressione ENTER para fechar...")
        browser.close()

if __name__ == "__main__":
    print("🔍 DEBUG DE BUSCA DE PEDIDO")
    print("=" * 50)
    debug_busca()