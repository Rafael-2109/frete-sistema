#!/usr/bin/env python3
"""
Diagnóstico profundo do botão Salvar no portal Atacadão
"""

import json
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

def diagnosticar_botao_salvar():
    """Analisa profundamente todos os elementos de salvamento na página"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        
        # Carregar sessão salva
        with open('storage_state_atacadao.json', 'r') as f:
            storage_state = json.load(f)
        
        context = browser.new_context(
            storage_state=storage_state,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        print("\n" + "="*80)
        print("DIAGNÓSTICO DO BOTÃO SALVAR - PORTAL ATACADÃO")
        print("="*80)
        
        # Navegar direto para um formulário de agendamento
        print("\n1. Navegando para formulário de agendamento...")
        # Usar um pedido conhecido
        page.goto("https://atacadao.hodiebooking.com.br/pedidos")
        page.wait_for_load_state('networkidle')
        
        # Buscar pedido 932955
        print("2. Buscando pedido 932955...")
        
        # Abrir filtros
        page.locator('#btn-filtro').click()
        page.wait_for_timeout(1000)
        
        # Limpar data
        page.locator('#dthr_elaboracao').clear()
        
        # Buscar pedido
        page.locator('#nr_pedido').fill('932955')
        page.locator('#enviarFiltros').click()
        page.wait_for_timeout(3000)
        
        # Abrir pedido
        page.locator('a[title="Exibir"]').first.click()
        page.wait_for_load_state('networkidle')
        
        # Clicar em Solicitar Agendamento
        print("3. Abrindo formulário de agendamento...")
        page.locator('a:has-text("Solicitar Agendamento")').click()
        page.wait_for_load_state('networkidle')
        
        print("\n4. ANÁLISE DO FORMULÁRIO:")
        print("-" * 40)
        
        # Verificar URL
        url_atual = page.url
        print(f"URL do formulário: {url_atual}")
        
        # Extrair ID do pedido da URL
        if "id_pedido=" in url_atual:
            id_pedido_url = url_atual.split("id_pedido=")[1].split("&")[0]
            print(f"⚠️ ID do pedido na URL: {id_pedido_url}")
        
        # Analisar TODOS os elementos com ID 'salvar'
        print("\n5. ANÁLISE DOS BOTÕES SALVAR:")
        print("-" * 40)
        
        elementos_salvar = page.locator('#salvar').all()
        print(f"Total de elementos com ID 'salvar': {len(elementos_salvar)}")
        
        for i, elem in enumerate(elementos_salvar, 1):
            print(f"\n  Elemento #{i}:")
            # Verificar visibilidade
            is_visible = elem.is_visible()
            print(f"    - Visível: {is_visible}")
            
            # Classes
            classes = elem.get_attribute('class')
            print(f"    - Classes: {classes}")
            
            # Texto
            texto = elem.text_content()
            print(f"    - Texto: '{texto}'")
            
            # HTML
            outer_html = elem.evaluate('el => el.outerHTML')
            if len(outer_html) > 200:
                outer_html = outer_html[:200] + "..."
            print(f"    - HTML: {outer_html}")
            
            # Verificar se tem onclick
            onclick = elem.get_attribute('onclick')
            if onclick:
                print(f"    - onclick: {onclick}")
            
            # Verificar labels dentro
            labels = elem.locator('label').all()
            if labels:
                print(f"    - Labels encontrados: {len(labels)}")
                for label in labels:
                    print(f"      • {label.text_content()}")
        
        # Verificar formulários na página
        print("\n6. ANÁLISE DOS FORMULÁRIOS:")
        print("-" * 40)
        
        forms = page.locator('form').all()
        print(f"Total de formulários: {len(forms)}")
        
        for i, form in enumerate(forms, 1):
            print(f"\n  Formulário #{i}:")
            action = form.get_attribute('action')
            method = form.get_attribute('method')
            form_id = form.get_attribute('id')
            print(f"    - ID: {form_id}")
            print(f"    - Action: {action}")
            print(f"    - Method: {method}")
            
            # Verificar campos hidden
            hidden_inputs = form.locator('input[type="hidden"]').all()
            if hidden_inputs:
                print(f"    - Campos hidden: {len(hidden_inputs)}")
                for hidden in hidden_inputs[:5]:  # Mostrar apenas os 5 primeiros
                    name = hidden.get_attribute('name')
                    value = hidden.get_attribute('value')
                    if value and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"      • {name} = {value}")
        
        # Analisar JavaScript do botão
        print("\n7. ANÁLISE DO JAVASCRIPT:")
        print("-" * 40)
        
        # Verificar se há event listeners
        result = page.evaluate("""
            () => {
                const salvar = document.querySelector('#salvar');
                if (!salvar) return 'Elemento #salvar não encontrado';
                
                // Verificar event listeners (Chrome DevTools API)
                const listeners = getEventListeners ? getEventListeners(salvar) : null;
                
                // Verificar atributos data-*
                const dataAttrs = {};
                for (let attr of salvar.attributes) {
                    if (attr.name.startsWith('data-')) {
                        dataAttrs[attr.name] = attr.value;
                    }
                }
                
                return {
                    id: salvar.id,
                    className: salvar.className,
                    tagName: salvar.tagName,
                    onclick: salvar.onclick ? salvar.onclick.toString() : null,
                    dataAttributes: dataAttrs,
                    parentForm: salvar.closest('form') ? {
                        id: salvar.closest('form').id,
                        action: salvar.closest('form').action
                    } : null
                };
            }
        """)
        
        print(f"Resultado JavaScript: {json.dumps(result, indent=2)}")
        
        # Capturar screenshot para análise
        screenshot_path = f"diagnostico_salvar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n✅ Screenshot salvo: {screenshot_path}")
        
        input("\n⏸️ Pressione ENTER para fechar o navegador...")
        browser.close()

if __name__ == "__main__":
    diagnosticar_botao_salvar()