#!/usr/bin/env python
"""
Script de debug para o portal Atacadão
"""

from playwright.sync_api import sync_playwright
import time
import json

# Carregar configuração
from app.portal.atacadao.config import ATACADAO_CONFIG

def testar_portal():
    """Testa o portal com debug detalhado"""
    
    with sync_playwright() as p:
        # Iniciar navegador em modo visível
        browser = p.chromium.launch(headless=False)
        
        # Criar contexto com sessão salva
        try:
            context = browser.new_context(storage_state="storage_state_atacadao.json")
            print("✅ Sessão carregada")
        except:
            context = browser.new_context()
            print("⚠️ Sem sessão salva")
        
        page = context.new_page()
        
        # 1. Ir para página de pedidos
        print("\n1. Abrindo página de pedidos...")
        page.goto(ATACADAO_CONFIG['urls']['pedidos'])
        page.wait_for_load_state('networkidle')
        
        # 2. Verificar se está logado
        print("2. Verificando login...")
        if "/login" in page.url or page.locator("input[type='password']").is_visible():
            print("❌ Não está logado!")
            browser.close()
            return
        
        print("✅ Logado")
        
        # 3. LIMPAR TODOS OS FILTROS
        print("\n3. Limpando filtros...")
        
        # Método 1: Clicar em todos os botões de limpar
        botoes_limpar = page.locator('button[data-action="remove"]').all()
        print(f"   Encontrados {len(botoes_limpar)} botões de limpar")
        for i, botao in enumerate(botoes_limpar):
            try:
                if botao.is_visible():
                    botao.click()
                    print(f"   ✅ Botão {i+1} clicado")
                    time.sleep(0.5)
            except:
                pass
        
        # Método 2: Limpar campos específicos
        campos_data = [
            '#dthr_elaboracao',
            '#dthr_elaboracao_inicio', 
            '#dthr_elaboracao_fim',
            '#data_inicio',
            '#data_fim',
            'input[name*="data"]',
            'input[name*="dthr"]'
        ]
        
        for campo in campos_data:
            try:
                elementos = page.locator(campo).all()
                for el in elementos:
                    if el.is_visible():
                        el.fill('')
                        print(f"   ✅ Campo {campo} limpo")
            except:
                pass
        
        # 4. Preencher número do pedido
        numero_pedido = input("\n4. Digite o número do pedido (ou ENTER para 892784): ").strip() or "892784"
        print(f"   Buscando pedido: {numero_pedido}")
        
        campo_pedido = ATACADAO_CONFIG['seletores']['campo_pedido']
        page.fill(campo_pedido, '')
        time.sleep(0.5)
        page.fill(campo_pedido, numero_pedido)
        
        # Screenshot antes de filtrar
        page.screenshot(path="antes_filtrar.png")
        print("   📸 Screenshot: antes_filtrar.png")
        
        # 5. Clicar em filtrar
        print("\n5. Filtrando...")
        botao_filtrar = ATACADAO_CONFIG['seletores']['botao_filtrar']
        page.click(botao_filtrar)
        
        # Aguardar resposta
        print("   Aguardando resultado...")
        page.wait_for_load_state('networkidle', timeout=30000)
        time.sleep(2)
        
        # Screenshot depois de filtrar
        page.screenshot(path="depois_filtrar.png")
        print("   📸 Screenshot: depois_filtrar.png")
        
        # 6. Verificar resultado
        print("\n6. Verificando resultado...")
        
        # Verificar se há tabela vazia
        content = page.content()
        if "Nenhum registro encontrado" in content or "Nenhum dado disponível" in content:
            print("   ❌ Nenhum registro encontrado!")
            
            # Verificar se há filtros ativos
            print("\n   Verificando filtros ativos:")
            
            # Pegar valores dos campos
            try:
                val_elaboracao = page.input_value('#dthr_elaboracao')
                if val_elaboracao:
                    print(f"   ⚠️ Data elaboração: {val_elaboracao}")
            except:
                pass
            
            # Sugestão
            print("\n   💡 SUGESTÕES:")
            print("   1. Verifique se o pedido existe no portal")
            print("   2. Tente buscar SEM nenhum filtro de data")
            print("   3. Verifique se o pedido não foi cancelado")
            
        else:
            # Verificar se tem link de exibir
            link_exibir = ATACADAO_CONFIG['seletores']['link_exibir_pedido']
            if page.locator(link_exibir).is_visible():
                print(f"   ✅ PEDIDO {numero_pedido} ENCONTRADO!")
                
                # Clicar para abrir
                page.click(link_exibir)
                time.sleep(2)
                
                # Screenshot do pedido
                page.screenshot(path=f"pedido_{numero_pedido}.png")
                print(f"   📸 Screenshot: pedido_{numero_pedido}.png")
            else:
                print("   ⚠️ Pedido na tabela mas sem link de exibir")
        
        # Manter navegador aberto para inspeção
        input("\n🔍 Navegador aberto para inspeção. Pressione ENTER para fechar...")
        
        browser.close()

if __name__ == "__main__":
    print("🔧 DEBUG DO PORTAL ATACADÃO")
    print("=" * 50)
    testar_portal()