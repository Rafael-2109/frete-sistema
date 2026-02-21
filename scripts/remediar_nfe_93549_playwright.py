#!/usr/bin/env python3
"""
Remediar NF-e 93549 via Playwright — Interacao direta com UI Odoo
=================================================================

Os metodos via XML-RPC (onchange, preview, action_gerar_nfe) NAO conseguem
disparar a cadeia completa de _compute do l10n_br. Somente a renderizacao
do form view na UI forca a recomputacao dos campos nfe_infnfe_*.

Este script usa Playwright para:
1. Fazer login no Odoo
2. Abrir a invoice 502614 (NF 93549)
3. Clicar "Pre-visualizar XML NF-e" (forca recomputacao)
4. Voltar ao form e clicar "Transmitir" (action_gerar_nfe)
5. Aguardar e verificar resultado (autorizado + chave 44 digitos)

Execucao:
    source .venv/bin/activate
    python scripts/remediar_nfe_93549_playwright.py [--headless] [--diagnose-only]

Flags:
    --headless       Rodar sem abrir janela do browser (default: headed)
    --diagnose-only  Apenas abrir a invoice e ler estado, sem clicar botoes
"""

import argparse
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INVOICE_ID = 502614
ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo.nacomgoya.com.br')
ODOO_USERNAME = os.environ.get('ODOO_USERNAME', '')
ODOO_API_KEY = os.environ.get('ODOO_API_KEY', '')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', '')  # Senha web (diferente do API key)
ODOO_DATABASE = os.environ.get('ODOO_DATABASE', 'odoo-17-ee-nacomgoya-prd')


async def login_odoo(page, context):
    """
    Faz login no Odoo.

    Tenta 2 estrategias:
    1. JSON-RPC /web/session/authenticate (cookie de sessao automatico)
    2. Fallback: form login via UI

    Usa ODOO_PASSWORD (senha web), NAO ODOO_API_KEY.
    """
    password = ODOO_PASSWORD

    # Estrategia 1: JSON-RPC authenticate (seta cookie automaticamente)
    logger.info(f"Tentando login JSON-RPC ({ODOO_URL})...")
    try:
        auth_response = await context.request.post(
            f"{ODOO_URL}/web/session/authenticate",
            data={
                "jsonrpc": "2.0",
                "method": "call",
                "id": 1,
                "params": {
                    "db": ODOO_DATABASE,
                    "login": ODOO_USERNAME,
                    "password": password,
                }
            },
        )

        if auth_response.status == 200:
            auth_data = await auth_response.json()
            if not auth_data.get('error'):
                result = auth_data.get('result', {})
                uid = result.get('uid')
                if uid:
                    logger.info(f"JSON-RPC auth OK (uid={uid})")

                    # Navegar para /web (sessao ja ativa)
                    # NOTA: Odoo SPA mantem long-polling/WebSocket aberto → networkidle NUNCA resolve
                    await page.goto(f"{ODOO_URL}/web", wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(3)

                    if '/web/login' not in page.url:
                        logger.info(f"Login OK! URL: {page.url}")
                        return True
                    else:
                        logger.warning("JSON-RPC auth retornou uid mas sessao nao ativa. Tentando form...")
            else:
                logger.warning(f"JSON-RPC auth erro: {auth_data['error'].get('data', {}).get('message', 'unknown')}")
    except Exception as e:
        logger.warning(f"JSON-RPC auth falhou: {e}")

    # Estrategia 2: Form login via UI
    logger.info("Tentando login via form UI...")
    login_url = f"{ODOO_URL}/web/login"
    await page.goto(login_url, wait_until='domcontentloaded', timeout=60000)

    # Verificar se ja esta logado
    if '/web#' in page.url or (page.url.endswith('/web') and '/login' not in page.url):
        logger.info("Ja logado!")
        return True

    # Preencher form
    email_field = page.locator('input[name="login"]')
    pass_field = page.locator('input[name="password"]')

    if await email_field.count() == 0 or await pass_field.count() == 0:
        logger.error("Campos de login nao encontrados!")
        await page.screenshot(path='/tmp/odoo_login_debug.png')
        return False

    await email_field.fill(ODOO_USERNAME)
    await pass_field.fill(password)

    # Selecionar database se necessario
    db_selector = page.locator('select[name="db"]')
    if await db_selector.count() > 0:
        await db_selector.select_option(ODOO_DATABASE)

    # Submeter form (pressionar Enter e mais confiavel que buscar botao)
    await pass_field.press('Enter')

    # Aguardar redirect para /web# (nao apenas /web que casa com /web/login)
    try:
        await page.wait_for_function(
            "() => !window.location.href.includes('/web/login')",
            timeout=20000
        )
        await asyncio.sleep(2)
        logger.info(f"Login via form OK! URL: {page.url}")
        return True
    except Exception:
        await page.screenshot(path='/tmp/odoo_login_debug.png')
        logger.error(f"Login falhou. URL final: {page.url}")
        logger.info("Screenshot: /tmp/odoo_login_debug.png")

        # Verificar se houve mensagem de erro
        error = page.locator('.alert-danger')
        if await error.count() > 0:
            error_text = await error.text_content()
            logger.error(f"Mensagem de erro: {error_text}")

        return False


async def navegar_para_invoice(page, invoice_id):
    """Navega para o form view da invoice."""
    # URL completa com cids, menu_id e action — necessario para Odoo resolver view corretamente
    url = f"{ODOO_URL}/web#id={invoice_id}&cids=1-3-4&menu_id=124&action=243&model=account.move&view_type=form"
    logger.info(f"Navegando para invoice {invoice_id}...")
    # NOTA: Odoo SPA mantem long-polling/WebSocket aberto → networkidle NUNCA resolve
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)

    # Aguardar o form carregar (campo 'name' ou breadcrumb)
    try:
        await page.wait_for_selector('.o_form_view', timeout=30000)
        logger.info("Form view carregado.")
    except Exception:
        logger.warning("Timeout aguardando form view. Tentando continuar...")

    # Pausa para computed fields renderizarem
    await asyncio.sleep(3)


async def ler_estado_invoice(page):
    """Le o estado da invoice diretamente da UI."""
    estado = {}

    # Tentar ler o titulo/nome da invoice
    try:
        name_el = page.locator('.o_form_view .oe_title span[name="name"]')
        if await name_el.count() > 0:
            estado['name'] = await name_el.text_content()
    except Exception:
        pass

    # Tentar ler situacao_nf via widget ou campo
    try:
        # Odoo 17 usa widget de status bar ou campo selection
        sit_el = page.locator('[name="l10n_br_situacao_nf"] .o_field_widget, [name="l10n_br_situacao_nf"]')
        if await sit_el.count() > 0:
            estado['situacao_nf'] = await sit_el.text_content()
    except Exception:
        pass

    # Tentar ler chave_nf
    try:
        chave_el = page.locator('[name="l10n_br_chave_nf"] .o_field_widget, [name="l10n_br_chave_nf"]')
        if await chave_el.count() > 0:
            estado['chave_nf'] = await chave_el.text_content()
    except Exception:
        pass

    return estado


async def clicar_botao(page, texto_botao, timeout=10000):
    """Clica em um botao pelo texto visivel."""
    logger.info(f'Procurando botao "{texto_botao}"...')

    # Estrategia 1: botao com texto exato
    btn = page.locator(f'button:has-text("{texto_botao}")')
    if await btn.count() > 0:
        logger.info(f'Botao "{texto_botao}" encontrado. Clicando...')
        await btn.first.click()
        return True

    # Estrategia 2: botao dentro de dropdown/menu
    # Em Odoo 17, botoes secundarios ficam no dropdown "..." (o_dropdown_more)
    dropdown = page.locator('.o_statusbar_buttons .o_dropdown_more, .o_statusbar_buttons .dropdown-toggle')
    if await dropdown.count() > 0:
        logger.info("Abrindo dropdown de acoes...")
        await dropdown.first.click()
        await asyncio.sleep(1)
        btn = page.locator(f'.dropdown-menu button:has-text("{texto_botao}"), .dropdown-menu a:has-text("{texto_botao}")')
        if await btn.count() > 0:
            logger.info(f'Botao "{texto_botao}" encontrado no dropdown. Clicando...')
            await btn.first.click()
            return True

    # Estrategia 3: Dentro do menu "Ação" ou "Imprimir"
    action_menu = page.locator('.o_cp_action_menus .dropdown-toggle:has-text("Ação"), .o_cp_action_menus button:has-text("Ação")')
    if await action_menu.count() > 0:
        logger.info('Abrindo menu "Ação"...')
        await action_menu.first.click()
        await asyncio.sleep(1)
        btn = page.locator(f'.dropdown-menu span:has-text("{texto_botao}"), .dropdown-menu a:has-text("{texto_botao}")')
        if await btn.count() > 0:
            logger.info(f'"{texto_botao}" encontrado no menu Ação. Clicando...')
            await btn.first.click()
            return True

    logger.warning(f'Botao "{texto_botao}" NAO encontrado!')
    return False


async def verificar_resultado_via_xmlrpc():
    """Verifica o resultado final via XML-RPC (mais confiavel que scraping)."""
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()
        odoo.authenticate()

        inv = odoo.execute_kw(
            'account.move', 'read',
            [[INVOICE_ID]],
            {'fields': [
                'name', 'state', 'l10n_br_situacao_nf', 'l10n_br_chave_nf',
                'l10n_br_cstat_nf', 'l10n_br_xmotivo_nf',
                'amount_tax', 'amount_total',
            ]}
        )
        if not inv:
            logger.error("Invoice nao encontrada!")
            return False

        inv = inv[0]
        chave = inv.get('l10n_br_chave_nf', '')
        chave_ok = chave and len(str(chave)) == 44

        logger.info("=" * 60)
        logger.info("VERIFICACAO FINAL (via XML-RPC)")
        logger.info("=" * 60)
        logger.info(f"  name: {inv['name']}")
        logger.info(f"  state: {inv['state']}")
        logger.info(f"  situacao_nf: {inv['l10n_br_situacao_nf']}")
        logger.info(f"  chave_nf: {chave} (valida={chave_ok})")
        logger.info(f"  cstat: {inv['l10n_br_cstat_nf']}")
        logger.info(f"  xmotivo: {inv['l10n_br_xmotivo_nf']}")
        logger.info(f"  amount_tax: {inv['amount_tax']}")
        logger.info(f"  amount_total: {inv['amount_total']}")

        if inv['l10n_br_situacao_nf'] == 'autorizado' and chave_ok:
            logger.info("*** SUCESSO: NF-e AUTORIZADA! ***")
            return True
        elif inv['l10n_br_situacao_nf'] == 'excecao_autorizado' and chave_ok:
            logger.info("*** SUCESSO PARCIAL: excecao_autorizado COM chave ***")
            return True
        else:
            logger.warning("NF-e ainda NAO autorizada.")
            return False


async def main():
    parser = argparse.ArgumentParser(description='Remediar NF-e 93549 via Playwright')
    parser.add_argument('--headless', action='store_true', help='Rodar sem janela')
    parser.add_argument('--diagnose-only', action='store_true', help='Apenas ler estado, sem acoes')
    args = parser.parse_args()

    if not ODOO_USERNAME:
        logger.error("ODOO_USERNAME nao configurado no .env")
        sys.exit(1)
    if not ODOO_PASSWORD:
        logger.error("ODOO_PASSWORD nao configurado no .env (senha web, diferente do API key)")
        sys.exit(1)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        try:
            # 1. Login via JSON-RPC (API key funciona, web login nao)
            if not await login_odoo(page, context):
                logger.error("Falha no login. Abortando.")
                return

            # 2. Navegar para invoice
            await navegar_para_invoice(page, INVOICE_ID)

            # Screenshot para diagnostico
            screenshot_path = '/tmp/odoo_nfe_93549_form.png'
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot salvo: {screenshot_path}")

            if args.diagnose_only:
                logger.info("MODO DIAGNOSTICO — apenas leitura.")
                estado = await ler_estado_invoice(page)
                logger.info(f"Estado UI: {estado}")
                return

            # 3. Clicar "Pré-visualizar XML NF-e"
            logger.info("")
            logger.info("=" * 60)
            logger.info("PASSO 1: Clicar 'Pré-visualizar XML NF-e'")
            logger.info("=" * 60)

            # Tentar variantes do nome do botao
            clicou_preview = False
            for nome in [
                "Pré Visualizar XML NF-e",
                "Pré Visualizar XML",
                "Pré-visualizar XML NF-e",
                "Pre Visualizar XML NF-e",
                "Pre-visualizar XML",
                "Preview XML",
            ]:
                if await clicar_botao(page, nome):
                    clicou_preview = True
                    break

            if not clicou_preview:
                # Ultima tentativa: buscar qualquer botao com "xml" no texto
                logger.info("Tentando busca generica por botao com 'XML'...")
                btn = page.locator('button:has-text("XML")')
                count = await btn.count()
                if count > 0:
                    for i in range(count):
                        txt = await btn.nth(i).text_content()
                        logger.info(f"  Botao encontrado: '{txt}'")
                    await btn.first.click()
                    clicou_preview = True
                    logger.info(f"Clicou no primeiro botao com 'XML'")

            if not clicou_preview:
                # Listar TODOS os botoes visiveis para debug
                logger.warning("Nenhum botao XML encontrado. Listando botoes visiveis...")
                all_btns = page.locator('button:visible')
                count = await all_btns.count()
                for i in range(min(count, 20)):
                    txt = await all_btns.nth(i).text_content()
                    txt = txt.strip().replace('\n', ' ')[:60] if txt else '(vazio)'
                    logger.info(f"  Botao [{i}]: '{txt}'")

            if clicou_preview:
                # Aguardar: pode abrir nova aba/dialog ou redirecionar
                logger.info("Aguardando 8s apos preview XML...")
                await asyncio.sleep(8)

                # Se abriu nova aba, fechar e voltar
                pages = context.pages
                if len(pages) > 1:
                    logger.info(f"Nova aba aberta ({len(pages)} abas). Fechando aba extra...")
                    for extra_page in pages[1:]:
                        await extra_page.close()

                # Voltar para o form da invoice
                await navegar_para_invoice(page, INVOICE_ID)
                await asyncio.sleep(3)

            # 4. Clicar "Transmitir" (action_gerar_nfe)
            logger.info("")
            logger.info("=" * 60)
            logger.info("PASSO 2: Clicar 'Transmitir' (action_gerar_nfe)")
            logger.info("=" * 60)

            clicou_transmitir = False
            for nome in [
                "Transmitir NF-e",
                "Transmitir",
                "Gerar NF-e",
                "Enviar NF-e",
            ]:
                if await clicar_botao(page, nome):
                    clicou_transmitir = True
                    break

            if not clicou_transmitir:
                logger.warning("Botao Transmitir nao encontrado. Listando botoes...")
                all_btns = page.locator('button:visible')
                count = await all_btns.count()
                for i in range(min(count, 20)):
                    txt = await all_btns.nth(i).text_content()
                    txt = txt.strip().replace('\n', ' ')[:60] if txt else '(vazio)'
                    logger.info(f"  Botao [{i}]: '{txt}'")

            if clicou_transmitir:
                logger.info("Aguardando 25s para SEFAZ processar...")
                await asyncio.sleep(25)

                # Screenshot do resultado
                await page.screenshot(path='/tmp/odoo_nfe_93549_resultado.png')
                logger.info("Screenshot resultado: /tmp/odoo_nfe_93549_resultado.png")

            # 5. Verificar resultado via XML-RPC (mais confiavel)
            logger.info("")

        except Exception as e:
            logger.error(f"Erro durante execucao: {e}")
            await page.screenshot(path='/tmp/odoo_nfe_93549_erro.png')
            logger.info("Screenshot erro: /tmp/odoo_nfe_93549_erro.png")
            raise
        finally:
            await browser.close()

    # Verificar resultado final via XML-RPC
    await verificar_resultado_via_xmlrpc()


if __name__ == '__main__':
    asyncio.run(main())
