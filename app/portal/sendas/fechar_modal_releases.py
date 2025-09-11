#!/usr/bin/env python3
"""
Estratégia otimizada para fechar modal de releases rapidamente
sem causar falsos negativos
"""

import logging

logger = logging.getLogger(__name__)


async def fechar_modal_releases_rapido(page, max_tentativas=10, intervalo_ms=200):
    """
    Estratégia otimizada para fechar o modal de releases:
    - Polling rápido em intervalos curtos
    - Detecta e fecha assim que aparece
    - Não bloqueia se não aparecer
    
    Args:
        page: Página do Playwright
        max_tentativas: Número máximo de tentativas (default: 10)
        intervalo_ms: Intervalo entre tentativas em ms (default: 200ms)
    
    Returns:
        True se fechou o modal, False se não apareceu
    """
    
    # Seletores específicos para o modal de releases
    seletores_modal_releases = [
        # Modal de releases geralmente tem um título específico
        'div:has-text("Release Notes")',
        'div:has-text("Novidades")',
        'div:has-text("Atualizações")',
        '[class*="release"]',
        '[class*="announcement"]',
        '[class*="modal"]:has-text("versão")',
        '[class*="modal"]:has-text("nova")',
    ]
    
    # Seletores para o botão de fechar
    seletores_fechar = [
        # Botões específicos do modal de releases
        '[class*="modal"] button:has-text("×")',
        '[class*="modal"] button:has-text("X")',
        '[class*="modal"] button[aria-label*="lose"]',
        '[class*="modal"] button[aria-label*="echar"]',
        '[class*="modal"] .close',
        '[class*="modal"] [class*="close"]',
        'button:has-text("Fechar")',
        'button:has-text("OK")',
        'button:has-text("Entendi")',
    ]
    
    logger.debug(f"🔍 Iniciando detecção rápida de modal (máx {max_tentativas} tentativas, {intervalo_ms}ms cada)")
    
    for tentativa in range(max_tentativas):
        try:
            # Verificar se algum modal de releases está visível
            modal_detectado = False
            
            for seletor_modal in seletores_modal_releases:
                try:
                    # Verificação super rápida (sem wait)
                    elemento_modal = page.locator(seletor_modal).first
                    if await elemento_modal.count() > 0:
                        # Modal detectado, tentar fechar imediatamente
                        logger.info(f"⚡ Modal de releases detectado na tentativa {tentativa + 1}")
                        modal_detectado = True
                        
                        # Tentar fechar com diferentes seletores
                        for seletor_fechar in seletores_fechar:
                            try:
                                btn_fechar = page.locator(seletor_fechar).first
                                if await btn_fechar.is_visible(timeout=100):  # Timeout mínimo
                                    logger.info(f"🎯 Fechando modal com: {seletor_fechar}")
                                    await btn_fechar.click()
                                    await page.wait_for_timeout(200)  # Pausa mínima
                                    
                                    # Verificar se modal sumiu
                                    if await elemento_modal.count() == 0:
                                        logger.info(f"✅ Modal fechado com sucesso em {(tentativa + 1) * intervalo_ms}ms")
                                        return True
                            except Exception:
                                continue
                        
                        # Se detectou mas não conseguiu fechar, tentar método alternativo
                        if modal_detectado:
                            logger.debug("⚡ Tentando ESC para fechar modal")
                            await page.keyboard.press("Escape")
                            await page.wait_for_timeout(100)
                            
                            if await elemento_modal.count() == 0:
                                logger.info(f"✅ Modal fechado com ESC em {(tentativa + 1) * intervalo_ms}ms")
                                return True
                        
                        break  # Sair do loop de seletores de modal se encontrou
                except Exception:
                    continue
            
            # Se não detectou modal nesta tentativa, aguardar intervalo curto
            if not modal_detectado:
                await page.wait_for_timeout(intervalo_ms)
        
        except Exception as e:
            logger.debug(f"Tentativa {tentativa + 1} erro: {e}")
            await page.wait_for_timeout(intervalo_ms)
    
    # Após todas as tentativas
    total_ms = max_tentativas * intervalo_ms
    logger.debug(f"ℹ️ Nenhum modal de releases em {total_ms}ms - continuando")
    return False


async def fechar_modal_releases_com_fallback(page):
    """
    Estratégia em duas fases:
    1. Tentativa rápida (1 segundo total)
    2. Fallback para método tradicional se necessário
    
    Args:
        page: Página do Playwright
    
    Returns:
        True se fechou o modal, False se não apareceu
    """
    
    # Fase 1: Detecção rápida (5 tentativas de 200ms = 1 segundo)
    logger.info("⚡ Fase 1: Detecção rápida de modal...")
    fechou = await fechar_modal_releases_rapido(page, max_tentativas=5, intervalo_ms=200)
    
    if fechou:
        return True
    
    # Fase 2: Uma tentativa mais robusta se suspeitar que pode aparecer
    # Útil em conexões lentas onde o modal demora mais
    logger.debug("🔍 Fase 2: Verificação adicional...")
    
    # Verificar se há algum indicador de loading que sugere que modal vai aparecer
    loading_indicators = [
        '.loading',
        '.spinner',
        '[class*="load"]',
        '[class*="spin"]'
    ]
    
    for indicator in loading_indicators:
        try:
            if await page.locator(indicator).is_visible(timeout=100):
                logger.info("⏳ Indicador de loading detectado, aguardando mais...")
                # Dar mais tempo se há loading
                fechou = await fechar_modal_releases_rapido(page, max_tentativas=5, intervalo_ms=300)
                if fechou:
                    return True
                break
        except Exception:
            continue
    
    logger.debug("ℹ️ Modal de releases não apareceu")
    return False


# Função helper para integrar no código existente
async def aguardar_e_fechar_modal_releases(page, contexto=""):
    """
    Função wrapper para usar no consumir_agendas.py
    
    Args:
        page: Página do Playwright
        contexto: Descrição do contexto (ex: "após Gestão de Pedidos")
    
    Returns:
        True se fechou modal, False caso contrário
    """
    if contexto:
        logger.info(f"🔍 Verificando modal de releases {contexto}...")
    
    resultado = await fechar_modal_releases_com_fallback(page)
    
    if resultado:
        logger.info(f"✅ Modal de releases fechado rapidamente {contexto}")
    else:
        logger.debug(f"ℹ️ Sem modal de releases {contexto}")
    
    return resultado