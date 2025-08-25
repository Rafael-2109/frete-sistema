#!/usr/bin/env python3
"""
Correção para erro "Execution context was destroyed" no Playwright
"""

# O problema ocorre quando tentamos interagir com elementos após navegação/reload

# PADRÃO INCORRETO (causa o erro):
"""
page.click("#salvar")  # Faz submit e navega
page.wait_for_timeout(500)  # Context já foi destruído!
# Qualquer ação aqui falha com "Execution context was destroyed"
"""

# PADRÃO CORRETO 1 - Aguardar navegação:
"""
# Usar wait_for_url ou wait_for_load_state
with page.expect_navigation():
    page.click("#salvar")
# Agora é seguro interagir com a nova página
"""

# PADRÃO CORRETO 2 - Verificar se ainda está na mesma página:
"""
url_before = page.url
page.click("#salvar")

# Aguardar mudança de URL ou timeout
try:
    page.wait_for_url(lambda url: url != url_before, timeout=5000)
    print("Navegou para nova página")
except:
    print("Ainda na mesma página")
"""

# PADRÃO CORRETO 3 - Para elementos que recarregam:
"""
# Aguardar elemento desaparecer e reaparecer
page.click("#botao")
page.wait_for_selector("#resultado", state="detached")  # Espera sair do DOM
page.wait_for_selector("#resultado", state="visible")   # Espera voltar
"""

# CORREÇÕES ESPECÍFICAS PARA O ATACADÃO:

def correcao_salvar_agendamento():
    """
    Correção para o botão salvar que causa navegação
    """
    codigo_corrigido = '''
    def _clicar_salvar(self):
        """Clicar no botão salvar com tratamento de navegação"""
        logger.info("🎯 Clicando em salvar...")
        
        try:
            botao_salvar = self.page.locator('#salvar')
            
            if botao_salvar.is_visible():
                # Capturar URL antes do clique
                url_before = self.page.url
                
                # Clicar e aguardar navegação
                with self.page.expect_navigation(wait_until="networkidle", timeout=10000):
                    botao_salvar.click()
                    logger.info("✅ Clique executado, aguardando navegação...")
                
                # Verificar nova URL
                url_after = self.page.url
                logger.info(f"Navegou de: {url_before}")
                logger.info(f"Para: {url_after}")
                
                if "/cargas/" in url_after or "/agendamentos/" in url_after:
                    logger.info("✅ Agendamento salvo com sucesso!")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
            # Se o contexto foi destruído, a página já navegou
            if "context was destroyed" in str(e).lower():
                logger.info("Página navegou - verificando resultado...")
                if "/cargas/" in self.page.url or "/agendamentos/" in self.page.url:
                    return True
            return False
    '''
    return codigo_corrigido

def correcao_buscar_pedido():
    """
    Correção para busca de pedido que recarrega a tabela
    """
    codigo_corrigido = '''
    def buscar_pedido(self, numero_pedido):
        """Buscar pedido com tratamento de recarregamento"""
        try:
            # Preencher campo
            self.page.fill('#nr_pedido', numero_pedido)
            
            # Clicar em filtrar e aguardar resposta
            # Aguardar a tabela recarregar (desaparecer e reaparecer)
            with self.page.expect_response("**/api/pedidos**", timeout=5000):
                self.page.click('#enviarFiltros')
            
            # Aguardar tabela estabilizar
            self.page.wait_for_selector('table tbody tr', state="visible")
            
            # Agora é seguro interagir com os resultados
            
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
    '''
    return codigo_corrigido

def correcao_preencher_data():
    """
    Correção para preenchimento de data que dispara eventos
    """
    codigo_corrigido = '''
    def preencher_data(self, campo_selector, data):
        """Preencher data com tratamento de eventos"""
        try:
            campo = self.page.locator(campo_selector)
            
            # Clicar e limpar
            campo.click()
            self.page.keyboard.press('Control+A')
            self.page.keyboard.press('Delete')
            
            # Digitar data
            self.page.keyboard.type(data)
            
            # Aguardar processamento do campo
            # NÃO usar wait_for_timeout aqui!
            # Usar wait_for_function para garantir que o valor foi aceito
            self.page.wait_for_function(
                f"document.querySelector('{campo_selector}').value === '{data}'",
                timeout=2000
            )
            
            # Agora é seguro continuar
            self.page.keyboard.press('Tab')
            
        except Exception as e:
            logger.error(f"Erro ao preencher data: {e}")
    '''
    return codigo_corrigido

print("="*60)
print("CORREÇÕES PARA 'Execution context was destroyed'")
print("="*60)
print("\n1. PROBLEMA PRINCIPAL:")
print("   - Tentar interagir com página após navegação/reload")
print("   - Usar wait_for_timeout após ações que mudam o DOM")
print("\n2. SOLUÇÕES:")
print("\n   a) Para botões que navegam (como Salvar):")
print("      - Use: with page.expect_navigation()")
print("      - OU: wait_for_url() para detectar mudança")
print("\n   b) Para elementos que recarregam:")
print("      - Use: wait_for_selector com state='detached' e depois 'visible'")
print("      - OU: expect_response() para aguardar resposta da API")
print("\n   c) Para campos que disparam eventos:")
print("      - Use: wait_for_function() para verificar se valor foi aceito")
print("      - EVITE: wait_for_timeout() fixo")
print("\n3. IMPLEMENTAR CORREÇÕES:")
print("\nCORREÇÃO 1 - Botão Salvar:")
print(correcao_salvar_agendamento())
print("\nCORREÇÃO 2 - Buscar Pedido:")
print(correcao_buscar_pedido())
print("\nCORREÇÃO 3 - Preencher Data:")
print(correcao_preencher_data())
print("\n" + "="*60)