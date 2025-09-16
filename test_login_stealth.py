#!/usr/bin/env python3
"""
Teste de Login Direto com Stealth Mode
Testa se consegue fazer login no Portal Sendas com todas as melhorias
"""

import asyncio
import logging
import os
import sys

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.portal.sendas.sendas_playwright import SendasPortal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def testar_login_direto():
    """
    Testa login direto sem usar cookies salvos
    """
    logger.info("=" * 60)
    logger.info("🚀 TESTE DE LOGIN DIRETO COM STEALTH MODE")
    logger.info("=" * 60)

    # Primeiro limpar arquivos de sessão ANTES de criar o portal
    logger.info("\n0️⃣ Limpando arquivos de sessão antiga...")
    import os
    from pathlib import Path

    session_files = [
        Path(__file__).parent / "app/portal/sendas/sendas_state.json",
        Path(__file__).parent / "app/portal/sendas/sessions/sendas_session.json",
        Path(__file__).parent / "app/portal/sendas/sessions/sendas_cookies.json"
    ]

    for file in session_files:
        if file.exists():
            file.unlink()
            logger.info(f"  🗑️ Removido: {file.name}")

    # Agora criar o portal sem sessão
    portal = SendasPortal(headless=True)

    try:
        # Iniciar navegador
        logger.info("\n1️⃣ Iniciando navegador em modo HEADLESS...")
        if not await portal.iniciar_navegador():
            logger.error("❌ Falha ao iniciar navegador")
            return False

        # Navegar direto para login
        logger.info("\n3️⃣ Navegando para página de login...")
        await portal.page.goto('https://login.trizy.com.br/access/auth/login/', wait_until='networkidle')

        # Aguardar página carregar
        await portal.page.wait_for_timeout(3000)

        # Verificar se tem Turnstile
        logger.info("\n4️⃣ Verificando presença do Turnstile...")
        has_turnstile = await portal.page.locator('#cf-turnstile').count() > 0

        if has_turnstile:
            logger.info("⚠️ Turnstile detectado - tentando preencher credenciais...")
        else:
            logger.info("✅ Sem Turnstile visível")

        # Preencher credenciais
        logger.info("\n5️⃣ Preenchendo credenciais...")

        # Verificar se campos existem
        email_field = await portal.page.locator('input[name="email_or_telephone"]').count()
        password_field = await portal.page.locator('input[name="password"]').count()

        if email_field == 0 or password_field == 0:
            logger.error("❌ Campos de login não encontrados!")

            # Capturar screenshot para debug
            await portal.page.screenshot(path='login_page_debug.png')
            logger.info("📸 Screenshot salvo: login_page_debug.png")

            # Verificar URL atual
            current_url = portal.page.url
            logger.info(f"📍 URL atual: {current_url}")

            # Talvez já esteja logado?
            if 'plataforma' in current_url and 'login' not in current_url:
                logger.info("🤔 Parece que já está na plataforma!")
                return True

            return False

        # Preencher campos
        await portal.page.fill('input[name="email_or_telephone"]', portal.usuario)
        await portal.page.fill('input[name="password"]', portal.senha)
        logger.info(f"✅ Credenciais preenchidas para: {portal.usuario}")

        # Procurar botão de submit
        logger.info("\n6️⃣ Procurando botão de login...")
        submit_button = portal.page.locator('button[type="submit"]')

        if await submit_button.count() == 0:
            submit_button = portal.page.get_by_role("button", name="Entrar")

        if await submit_button.count() > 0:
            logger.info("✅ Botão encontrado - clicando...")
            await submit_button.click()
        else:
            logger.error("❌ Botão de submit não encontrado")
            return False

        # Aguardar resultado
        logger.info("\n7️⃣ Aguardando resposta do login...")

        # Aguardar até 30 segundos para sair da página de login
        for i in range(30):
            await portal.page.wait_for_timeout(1000)
            current_url = portal.page.url

            # Se saiu da página de login, sucesso!
            if 'login' not in current_url.lower() and 'auth' not in current_url.lower():
                logger.info("=" * 60)
                logger.info("✅✅✅ LOGIN FUNCIONOU COM STEALTH MODE!")
                logger.info(f"📍 URL atual: {current_url}")
                logger.info("=" * 60)

                # Salvar cookies para uso futuro
                await portal.salvar_storage_state()
                logger.info("💾 Sessão salva para uso futuro")

                return True

            # Verificar se tem erro
            if i > 5:
                error_element = portal.page.locator('.error-message, .alert-danger, .toast-error')
                if await error_element.count() > 0:
                    error_text = await error_element.first.text_content()
                    logger.error(f"❌ Erro detectado: {error_text}")
                    break

            # Feedback a cada 5 segundos
            if i % 5 == 0 and i > 0:
                logger.info(f"⏳ Ainda aguardando... {30-i}s restantes")

        # Se chegou aqui, falhou
        logger.error("=" * 60)
        logger.error("❌ LOGIN FALHOU - Ainda na página de login")
        logger.error(f"📍 URL final: {portal.page.url}")
        logger.error("=" * 60)

        # Screenshot para debug
        await portal.page.screenshot(path='login_failed.png')
        logger.info("📸 Screenshot do erro: login_failed.png")

        return False

    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Fechar navegador
        await portal.fechar()
        logger.info("\n🔚 Navegador fechado")


async def main():
    """Função principal"""

    # Verificar se tem credenciais
    usuario = os.getenv('SENDAS_USUARIO')
    senha = os.getenv('SENDAS_SENHA')

    if not usuario or not senha:
        logger.error("❌ Configure as variáveis SENDAS_USUARIO e SENDAS_SENHA")
        return

    logger.info(f"👤 Usuário configurado: {usuario}")
    logger.info(f"🔑 Senha configurada: {'*' * len(senha)}")

    # Executar teste
    sucesso = await testar_login_direto()

    if sucesso:
        print("\n" + "🎉" * 20)
        print("SUCESSO! O STEALTH MODE FUNCIONOU!")
        print("O login passou mesmo em modo HEADLESS")
        print("🎉" * 20)
    else:
        print("\n" + "😔" * 20)
        print("LOGIN FALHOU - Cloudflare ainda está bloqueando")
        print("Pode ser necessário:")
        print("1. Capturar cookies manualmente")
        print("2. Usar proxy residencial")
        print("3. Aguardar alguns minutos e tentar novamente")
        print("😔" * 20)


if __name__ == "__main__":
    asyncio.run(main())