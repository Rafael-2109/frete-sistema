#!/usr/bin/env python3
"""
Script para corrigir problema de Playwright Sync/Async
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

async def garantir_sessao_valida_async(portal, cnpj_cliente=None):
    """
    Versão assíncrona para garantir sessão válida
    
    Args:
        portal: Nome do portal
        cnpj_cliente: CNPJ do cliente (opcional)
        
    Returns:
        bool: True se sessão válida ou re-login bem sucedido
    """
    import os
    
    try:
        # Verificar se arquivo de sessão existe
        if portal == 'atacadao':
            if os.path.exists("storage_state_atacadao.json"):
                # Usar versão assíncrona do Playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(
                        storage_state="storage_state_atacadao.json"
                    )
                    page = await context.new_page()
                    
                    # Verificar se está logado
                    try:
                        await page.goto('https://atacadao.hodiebooking.com.br/pedidos', 
                                       timeout=30000)
                        
                        # Verificar indicadores de login
                        login_elements = await page.query_selector_all('input[type="password"]')
                        
                        if not login_elements:
                            # Está logado
                            await browser.close()
                            return True
                    except Exception as e:
                        logger.warning(f"Erro ao verificar sessão: {e}")
                    
                    await browser.close()
                    
            logger.info("Sessão expirada ou não existe, re-login necessário")
            
            # Aqui poderia fazer re-login automático se tivesse credenciais
            # Por ora, retornar False para indicar que precisa configurar
            return False
            
    except Exception as e:
        logger.error(f"Erro ao garantir sessão válida: {e}")
        return False


# Para uso em contexto não assíncrono
def garantir_sessao_valida_sync(portal, cnpj_cliente=None):
    """
    Wrapper síncrono para garantir_sessao_valida_async
    """
    import nest_asyncio
    nest_asyncio.apply()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(
            garantir_sessao_valida_async(portal, cnpj_cliente)
        )
    finally:
        loop.close()


if __name__ == "__main__":
    # Teste
    print("Testando verificação de sessão...")
    resultado = garantir_sessao_valida_sync('atacadao')
    print(f"Sessão válida: {resultado}")