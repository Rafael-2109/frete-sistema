#!/usr/bin/env python3
"""
Técnicas para debug de Playwright em produção (sem headless=False)
"""

# TÉCNICA 1: Screenshots em cada passo
def debug_com_screenshots():
    """Tirar screenshot após cada ação importante"""
    codigo = '''
    # Adicionar após cada ação importante:
    logger.info("Estado atual da página")
    self.page.screenshot(path=f"debug_{datetime.now().strftime('%H%M%S')}.png")
    
    # Salvar HTML também
    html = self.page.content()
    with open(f"debug_{datetime.now().strftime('%H%M%S')}.html", "w") as f:
        f.write(html)
    '''
    return codigo

# TÉCNICA 2: Logs detalhados com timing
def debug_com_timing():
    """Medir tempo de cada operação"""
    codigo = '''
    import time
    
    # Antes de cada operação
    inicio = time.time()
    logger.info(f"Iniciando operação X...")
    
    # Operação
    self.page.wait_for_load_state('networkidle')  # Exemplo problemático
    
    # Depois
    tempo = time.time() - inicio
    logger.info(f"Operação X levou {tempo:.2f}s")
    
    if tempo > 10:
        logger.warning(f"⚠️ Operação muito lenta: {tempo}s")
    '''
    return codigo

# TÉCNICA 3: Timeout com fallback
def debug_com_fallback():
    """Sempre ter fallback para timeouts"""
    codigo = '''
    try:
        # Tentar com timeout menor
        self.page.wait_for_load_state('networkidle', timeout=3000)
        logger.info("✅ Network idle OK")
    except:
        logger.warning("⚠️ Network idle timeout - continuando...")
        # Continuar com o fluxo
    '''
    return codigo

# TÉCNICA 4: Verificar recursos pendentes
def debug_recursos_pendentes():
    """Ver o que está impedindo networkidle"""
    codigo = '''
    # Executar JavaScript para ver requisições pendentes
    recursos = self.page.evaluate("""
        () => {
            const entries = performance.getEntriesByType('resource');
            return entries.filter(e => e.responseEnd === 0).map(e => ({
                name: e.name,
                type: e.initiatorType,
                duration: e.duration
            }));
        }
    """)
    
    if recursos:
        logger.warning(f"⚠️ Recursos pendentes: {len(recursos)}")
        for r in recursos[:5]:  # Primeiros 5
            logger.warning(f"  - {r['type']}: {r['name'][:50]}")
    '''
    return codigo

# TÉCNICA 5: Console do navegador
def debug_console():
    """Capturar logs do console do navegador"""
    codigo = '''
    # No início da sessão
    self.page.on("console", lambda msg: logger.info(f"CONSOLE: {msg.text}"))
    self.page.on("pageerror", lambda err: logger.error(f"PAGE ERROR: {err}"))
    
    # Agora todos os logs JS aparecem no log Python
    '''
    return codigo

# TÉCNICA 6: Trace para análise posterior
def debug_com_trace():
    """Gravar trace completo para análise"""
    codigo = '''
    # Iniciar trace
    await browser.start_tracing(page, screenshots=True)
    
    # ... executar ações ...
    
    # Salvar trace
    await browser.stop_tracing(path="trace.zip")
    
    # Baixar trace.zip e abrir em chrome://tracing
    '''
    return codigo

print("="*60)
print("TÉCNICAS DE DEBUG PLAYWRIGHT EM PRODUÇÃO")
print("="*60)
print("\n1. SCREENSHOTS A CADA PASSO:")
print(debug_com_screenshots())
print("\n2. TIMING DE OPERAÇÕES:")
print(debug_com_timing())
print("\n3. TIMEOUTS COM FALLBACK:")
print(debug_com_fallback())
print("\n4. VERIFICAR RECURSOS PENDENTES:")
print(debug_recursos_pendentes())
print("\n5. CAPTURAR CONSOLE DO NAVEGADOR:")
print(debug_console())
print("\n6. TRACE COMPLETO (para async):")
print(debug_com_trace())
print("\n" + "="*60)
print("RESUMO:")
print("- NÃO use headless=False em produção (não tem display)")
print("- NÃO use networkidle em produção (pode travar)")
print("- USE domcontentloaded ou timeout pequeno")
print("- USE screenshots para debug visual")
print("- USE logs detalhados com timing")
print("="*60)