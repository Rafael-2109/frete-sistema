"""
ANÁLISE: Solução Híbrida API + Playwright
Comparação de performance e viabilidade
"""

print("=" * 80)
print("ANÁLISE DE VIABILIDADE: PLAYWRIGHT + API")
print("=" * 80)

print("""
CONCEITO DA SOLUÇÃO HÍBRIDA:
-----------------------------
1. API cria o pedido com dados básicos (rápido)
2. Playwright abre o pedido no navegador
3. Playwright adiciona produtos (dispara onchange)
4. API lê os dados calculados

ANÁLISE DE PERFORMANCE:
-----------------------

API PURA:
- Criar pedido: ~0.5 segundos
- Adicionar 10 itens: ~2 segundos
- TOTAL: ~2.5 segundos
- ❌ Problema: CFOP não preenchido

PLAYWRIGHT PURO:
- Abrir navegador: ~3 segundos
- Login: ~2 segundos
- Navegar até pedidos: ~2 segundos
- Criar pedido: ~3 segundos
- Adicionar 10 itens: ~20 segundos (2s por item)
- TOTAL: ~30 segundos
- ✅ Vantagem: CFOP preenchido corretamente

HÍBRIDO (API + Playwright):
- API cria pedido: ~0.5 segundos
- Playwright abre pedido existente: ~5 segundos
- Playwright adiciona produtos: ~15 segundos
- TOTAL: ~20 segundos
- ✅ Vantagem: CFOP preenchido
- ✅ 33% mais rápido que Playwright puro

COMPARAÇÃO:
-----------
Método          | Tempo    | CFOP | Confiável
----------------|----------|------|----------
API Pura        | 2.5s     | ❌   | ✅
Playwright Puro | 30s      | ✅   | ⚠️
Híbrido         | 20s      | ✅   | ✅

RISCOS DO PLAYWRIGHT:
--------------------
⚠️ Mudanças na interface quebram o script
⚠️ Mais lento que API pura (8x mais lento)
⚠️ Consome mais recursos (navegador)
⚠️ Pode ter problemas de timeout

BENEFÍCIOS DO PLAYWRIGHT:
-------------------------
✅ Garante comportamento idêntico ao usuário
✅ CFOP preenchido corretamente
✅ Todos os cálculos executados
✅ Validações de frontend aplicadas
""")

# Exemplo de implementação híbrida
codigo_hibrido = '''
# EXEMPLO: Implementação Híbrida (NÃO EXECUTAR - APENAS CONCEITO)

import xmlrpc.client
from playwright.sync_api import sync_playwright
import time

class PedidoHibrido:
    def __init__(self, odoo_url, odoo_db, odoo_user, odoo_pass):
        # Configurar API
        self.common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
        self.uid = self.common.authenticate(odoo_db, odoo_user, odoo_pass, {})
        self.models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')
        
        # Guardar credenciais para Playwright
        self.url = odoo_url
        self.user = odoo_user
        self.password = odoo_pass
    
    def criar_pedido_base_api(self, cliente_id, empresa_id):
        """Passo 1: API cria estrutura básica"""
        pedido_id = self.executar_api('sale.order', 'create', [{
            'partner_id': cliente_id,
            'company_id': empresa_id,
            'warehouse_id': 3,
            'payment_provider_id': 30,
            'incoterm_id': 6
        }])
        return pedido_id
    
    def adicionar_produtos_playwright(self, pedido_id, produtos):
        """Passo 2: Playwright adiciona produtos para acionar onchange"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(f"{self.url}/web/login")
            page.fill('input[name="login"]', self.user)
            page.fill('input[name="password"]', self.password)
            page.click('button[type="submit"]')
            
            # Abrir pedido específico
            page.goto(f"{self.url}/web#id={pedido_id}&model=sale.order&view_type=form")
            time.sleep(2)
            
            # Para cada produto
            for produto in produtos:
                # Clicar em adicionar linha
                page.click('a:has-text("Add a product")')
                time.sleep(1)
                
                # Preencher produto (dispara onchange)
                page.fill('input[name="product_id"]', produto['codigo'])
                page.press('input[name="product_id"]', 'Enter')
                time.sleep(1)
                
                # Preencher quantidade
                page.fill('input[name="product_uom_qty"]', str(produto['qty']))
                page.press('input[name="product_uom_qty"]', 'Tab')
                time.sleep(1)
            
            # Salvar
            page.click('button:has-text("Save")')
            time.sleep(2)
            
            browser.close()
    
    def verificar_resultado_api(self, pedido_id):
        """Passo 3: API lê os dados calculados"""
        linhas = self.executar_api('sale.order.line', 'search_read', [
            ['order_id', '=', pedido_id]
        ], {
            'fields': ['product_id', 'l10n_br_cfop_codigo', 'tax_id']
        })
        
        return linhas

# USO:
# hibrido = PedidoHibrido(url, db, user, pass)
# pedido_id = hibrido.criar_pedido_base_api(cliente_id, empresa_id)
# hibrido.adicionar_produtos_playwright(pedido_id, produtos)
# resultado = hibrido.verificar_resultado_api(pedido_id)
'''

print("\nCÓDIGO CONCEITUAL (NÃO TESTADO):")
print(codigo_hibrido)

print("\n" + "=" * 80)
print("RECOMENDAÇÃO FINAL")
print("=" * 80)
print("""
SUGESTÃO DE ABORDAGEM SEGURA:

1. PRIMEIRO: Execute a Server Action de descoberta (segura)
   - Apenas lista métodos disponíveis
   - Não executa nada
   - Permite identificar métodos seguros

2. SEGUNDO: Com a lista de métodos, pergunte:
   - Quais métodos são seguros de chamar?
   - Qual a ordem correta?
   - Existem pré-requisitos?

3. TERCEIRO: Escolha a estratégia:
   
   A) Se encontrarmos métodos seguros:
      - Criar Server Action específica
      - Testar em ambiente de desenvolvimento
   
   B) Se não houver métodos seguros:
      - Considerar Playwright híbrido
      - Aceitar o trade-off de performance

PERGUNTA CRÍTICA:
Você tem ambiente de teste/desenvolvimento para validar?
Ou precisamos garantir 100% de segurança em produção?
""")