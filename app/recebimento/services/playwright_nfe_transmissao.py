"""
Transmissao de NF-e via Playwright (UI Odoo)
=============================================

Resolve o problema de campos fiscais NF-e "stale" (nfe_infnfe_*) criados
pelo robo CIEL IT. As chains @api.depends/@api.compute do modulo l10n_br
NAO sao avaliadas na criacao via XML-RPC. Somente a interacao via UI
(renderizar form view + clicar "Pre Visualizar XML NF-e") forca a
recomputacao completa, corrigindo o Schema XML (erro SEFAZ 225).

Validado com NF-e 93549 (invoice 502614, cstat=100, autorizado) em 2026-02-21.
Padrao base: scripts/remediar_nfe_93549_playwright.py

Env vars necessarias (ja disponiveis no Render):
    ODOO_URL, ODOO_DATABASE, ODOO_USERNAME, ODOO_PASSWORD

Uso:
    from app.recebimento.services.playwright_nfe_transmissao import transmitir_nfe_via_playwright

    resultado = transmitir_nfe_via_playwright(
        invoice_id=502614,
        odoo=odoo_connection,
        logger=logger,
        redis_callback=lambda t, m, msg: ...,
    )
"""

import logging
import os
import time

logger = logging.getLogger(__name__)

# Configuracao Odoo (env vars)
ODOO_URL = os.environ.get('ODOO_URL', 'https://odoo.nacomgoya.com.br')
ODOO_DATABASE = os.environ.get('ODOO_DATABASE', 'odoo-17-ee-nacomgoya-prd')
ODOO_USERNAME = os.environ.get('ODOO_USERNAME', '')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', '')


def transmitir_nfe_via_playwright(
    invoice_id: int,
    odoo,
    logger,
    redis_callback=None,
    max_tentativas: int = 15,
    intervalo_retry: int = 120,
) -> dict:
    """
    Transmite NF-e via interacao com UI Odoo (Playwright headless).

    Renderizar o form view + clicar "Pre Visualizar XML NF-e" forca a
    recomputacao completa dos campos nfe_infnfe_* do l10n_br, resolvendo
    o erro SEFAZ 225 ("Falha no Schema XML").

    Args:
        invoice_id: ID da invoice no Odoo (account.move)
        odoo: Conexao Odoo autenticada (para verificacao XML-RPC)
        logger: Logger para registrar progresso
        redis_callback: fn(tentativa, max, mensagem) para progresso UI
        max_tentativas: Maximo de tentativas (default 15 = 30 min)
        intervalo_retry: Segundos entre tentativas (default 120 = 2 min)

    Returns:
        {'sucesso': True, 'chave_nf': '...', 'situacao_nf': 'autorizado',
         'inv_name': '...', 'tentativa': N}
        ou
        {'sucesso': False, 'erro': '...', 'tentativas': N,
         'ultimo_estado': {...}}
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("[playwright] Playwright nao instalado")
        return {'sucesso': False, 'erro': 'playwright_indisponivel', 'tentativas': 0}

    if not ODOO_PASSWORD:
        logger.error("[playwright] ODOO_PASSWORD nao configurado")
        return {'sucesso': False, 'erro': 'odoo_password_ausente', 'tentativas': 0}

    if not ODOO_USERNAME:
        logger.error("[playwright] ODOO_USERNAME nao configurado")
        return {'sucesso': False, 'erro': 'odoo_username_ausente', 'tentativas': 0}

    browser = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
        )
        page = context.new_page()

        # Login
        if not _login_odoo(page, context, logger):
            # Retry login uma vez
            logger.warning("[playwright] Primeiro login falhou, tentando novamente...")
            page.close()
            context.close()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True,
            )
            page = context.new_page()
            if not _login_odoo(page, context, logger):
                return {'sucesso': False, 'erro': 'login_falhou', 'tentativas': 0}

        # Ler nome da invoice antes do loop (para verificar que a pagina certa carregou)
        inv_name_esperado = None
        try:
            inv_pre = odoo.execute_kw(
                'account.move', 'read',
                [[invoice_id]],
                {'fields': ['name']}
            )
            if inv_pre:
                inv_name_esperado = inv_pre[0].get('name')
                logger.info(f"  [playwright] Invoice alvo: {inv_name_esperado} (id={invoice_id})")
        except Exception as e:
            logger.warning(f"  [playwright] Nao conseguiu ler nome da invoice: {e}")

        ultimo_estado = {}
        for tentativa in range(1, max_tentativas + 1):
            inicio_tentativa = time.time()
            logger.info(
                f"  [playwright] Tentativa {tentativa}/{max_tentativas} "
                f"para invoice {invoice_id}"
            )

            if redis_callback:
                redis_callback(
                    tentativa, max_tentativas,
                    f'Abrindo invoice no Odoo (tentativa {tentativa})...'
                )

            try:
                # 1. Navegar para invoice (verifica que a correta carregou)
                _navegar_para_invoice(page, invoice_id, logger, inv_name_esperado)

                # 2. Clicar "Pre Visualizar XML NF-e" (forca recomputacao)
                if redis_callback:
                    redis_callback(
                        tentativa, max_tentativas,
                        'Pre-visualizando XML NF-e...'
                    )

                clicou_preview = _clicar_botao_preview_xml(page, logger)
                if clicou_preview:
                    logger.info("  [playwright] Aguardando 8s apos preview XML...")
                    page.wait_for_timeout(8000)

                    # Fechar abas extras (preview pode abrir nova aba)
                    pages = context.pages
                    if len(pages) > 1:
                        logger.info(
                            f"  [playwright] {len(pages)} abas abertas. "
                            f"Fechando extras..."
                        )
                        for extra_page in pages[1:]:
                            extra_page.close()

                    # Voltar ao form view (verifica que a correta carregou)
                    _navegar_para_invoice(page, invoice_id, logger, inv_name_esperado)
                else:
                    logger.warning(
                        "  [playwright] Botao preview XML nao encontrado. "
                        "Tentando transmitir direto..."
                    )

                # 3. Clicar "Transmitir NF-e"
                if redis_callback:
                    redis_callback(
                        tentativa, max_tentativas,
                        'Transmitindo NF-e para SEFAZ...'
                    )

                clicou_transmitir = _clicar_botao_transmitir(page, logger)
                if clicou_transmitir:
                    logger.info("  [playwright] Aguardando 25s para SEFAZ processar...")
                    page.wait_for_timeout(25000)
                else:
                    logger.warning(
                        "  [playwright] Botao transmitir nao encontrado. "
                        "Verificando estado via XML-RPC..."
                    )

            except Exception as e:
                logger.warning(
                    f"  [playwright] Erro na tentativa {tentativa}: {e}"
                )
                # Screenshot para diagnostico
                try:
                    page.screenshot(
                        path=f'/tmp/playwright_nfe_{invoice_id}_attempt{tentativa}.png'
                    )
                except Exception:
                    pass

                # Browser crash → re-inicializar
                if 'Target closed' in str(e) or 'Browser' in str(e):
                    logger.warning(
                        "  [playwright] Browser crash detectado. Re-inicializando..."
                    )
                    try:
                        browser.close()
                    except Exception:
                        pass
                    browser = pw.chromium.launch(headless=True)
                    context = browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        ignore_https_errors=True,
                    )
                    page = context.new_page()
                    if not _login_odoo(page, context, logger):
                        return {
                            'sucesso': False,
                            'erro': 'login_falhou_apos_crash',
                            'tentativas': tentativa,
                        }

            # 4. Verificar resultado via XML-RPC (mais confiavel que scraping)
            try:
                inv_check = odoo.execute_kw(
                    'account.move', 'read',
                    [[invoice_id]],
                    {'fields': [
                        'name', 'l10n_br_situacao_nf', 'l10n_br_chave_nf',
                        'l10n_br_cstat_nf', 'l10n_br_xmotivo_nf',
                    ]}
                )
                if not inv_check:
                    logger.error(
                        f"  [playwright] Invoice {invoice_id} nao encontrada no Odoo"
                    )
                    ultimo_estado = {'erro': 'invoice_nao_encontrada'}
                    continue

                check = inv_check[0]
                sit = check.get('l10n_br_situacao_nf')
                chave = check.get('l10n_br_chave_nf')
                cstat = check.get('l10n_br_cstat_nf')
                xmotivo = check.get('l10n_br_xmotivo_nf', '')
                inv_name = check.get('name', '')

                ultimo_estado = {
                    'situacao_nf': sit,
                    'chave_nf': chave,
                    'cstat': cstat,
                    'xmotivo': xmotivo,
                }

                chave_valida = chave and len(str(chave)) == 44

                # Sucesso: autorizado COM chave de 44 digitos
                if sit == 'autorizado' and chave_valida:
                    logger.info(
                        f"  [playwright] NF-e {inv_name} AUTORIZADA! "
                        f"(tentativa {tentativa}, chave={chave})"
                    )
                    return {
                        'sucesso': True,
                        'chave_nf': chave,
                        'situacao_nf': 'autorizado',
                        'inv_name': inv_name,
                        'tentativa': tentativa,
                    }

                # Sucesso com excecao mas COM chave → aceitar
                if sit == 'excecao_autorizado' and chave_valida:
                    logger.warning(
                        f"  [playwright] NF-e {inv_name} excecao_autorizado "
                        f"COM chave (tentativa {tentativa}, chave={chave}). "
                        f"Aceito com ressalva."
                    )
                    return {
                        'sucesso': True,
                        'chave_nf': chave,
                        'situacao_nf': 'excecao_autorizado',
                        'inv_name': inv_name,
                        'tentativa': tentativa,
                    }

                logger.warning(
                    f"  [playwright] NF-e {inv_name} nao autorizada "
                    f"(tentativa {tentativa}/{max_tentativas}, "
                    f"situacao={sit}, cstat={cstat}, xmotivo={xmotivo})"
                )

            except Exception as e:
                logger.warning(
                    f"  [playwright] Falha ao verificar via XML-RPC: {e}"
                )
                ultimo_estado = {'erro_xmlrpc': str(e)}

            # Aguardar ate completar intervalo de retry
            if tentativa < max_tentativas:
                elapsed = time.time() - inicio_tentativa
                wait_time = max(0, intervalo_retry - elapsed)
                if wait_time > 0:
                    if redis_callback:
                        redis_callback(
                            tentativa, max_tentativas,
                            f'Aguardando {int(wait_time)}s para proxima tentativa...'
                        )
                    logger.info(
                        f"  [playwright] Aguardando {int(wait_time)}s "
                        f"para proxima tentativa..."
                    )
                    time.sleep(wait_time)

        # Esgotou todas as tentativas
        return {
            'sucesso': False,
            'erro': f'nao_autorizada_apos_{max_tentativas}_tentativas',
            'tentativas': max_tentativas,
            'ultimo_estado': ultimo_estado,
        }

    except Exception as e:
        logger.error(f"[playwright] Erro fatal: {e}")
        return {
            'sucesso': False,
            'erro': f'erro_fatal: {e}',
            'tentativas': 0,
        }
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        try:
            pw.stop()
        except Exception:
            pass


# =====================================================================
# Funcoes internas
# =====================================================================

def _login_odoo(page, context, logger):
    """
    Faz login no Odoo via JSON-RPC (cookie de sessao automatico).
    Fallback: form login via UI.

    Usa ODOO_PASSWORD (senha web), NAO ODOO_API_KEY.
    """
    # Estrategia 1: JSON-RPC authenticate
    logger.info(f"  [playwright] Login JSON-RPC ({ODOO_URL})...")
    try:
        auth_response = context.request.post(
            f"{ODOO_URL}/web/session/authenticate",
            data={
                "jsonrpc": "2.0",
                "method": "call",
                "id": 1,
                "params": {
                    "db": ODOO_DATABASE,
                    "login": ODOO_USERNAME,
                    "password": ODOO_PASSWORD,
                },
            },
        )

        if auth_response.status == 200:
            auth_data = auth_response.json()
            if not auth_data.get('error'):
                uid = auth_data.get('result', {}).get('uid')
                if uid:
                    logger.info(f"  [playwright] JSON-RPC auth OK (uid={uid})")

                    # Navegar para /web (sessao ja ativa)
                    # NOTA: Odoo SPA mantem long-polling → networkidle NUNCA resolve
                    page.goto(
                        f"{ODOO_URL}/web",
                        wait_until='domcontentloaded',
                        timeout=60000,
                    )
                    page.wait_for_timeout(3000)

                    if '/web/login' not in page.url:
                        logger.info(f"  [playwright] Login OK! URL: {page.url}")
                        return True
                    else:
                        logger.warning(
                            "  [playwright] JSON-RPC retornou uid mas sessao "
                            "nao ativa. Tentando form..."
                        )
            else:
                msg = auth_data['error'].get('data', {}).get('message', 'unknown')
                logger.warning(f"  [playwright] JSON-RPC auth erro: {msg}")
    except Exception as e:
        logger.warning(f"  [playwright] JSON-RPC auth falhou: {e}")

    # Estrategia 2: Form login via UI
    logger.info("  [playwright] Tentando login via form UI...")
    page.goto(
        f"{ODOO_URL}/web/login",
        wait_until='domcontentloaded',
        timeout=60000,
    )

    # Ja logado?
    if '/web#' in page.url or (page.url.endswith('/web') and '/login' not in page.url):
        logger.info("  [playwright] Ja logado!")
        return True

    # Preencher form
    email_field = page.locator('input[name="login"]')
    pass_field = page.locator('input[name="password"]')

    if email_field.count() == 0 or pass_field.count() == 0:
        logger.error("  [playwright] Campos de login nao encontrados!")
        page.screenshot(path='/tmp/playwright_login_debug.png')
        return False

    email_field.fill(ODOO_USERNAME)
    pass_field.fill(ODOO_PASSWORD)

    # Selecionar database se necessario
    db_selector = page.locator('select[name="db"]')
    if db_selector.count() > 0:
        db_selector.select_option(ODOO_DATABASE)

    # Submeter form (Enter e mais confiavel que buscar botao)
    pass_field.press('Enter')

    # Aguardar redirect para /web# (nao apenas /web que casa com /web/login)
    try:
        page.wait_for_function(
            "() => !window.location.href.includes('/web/login')",
            timeout=20000,
        )
        page.wait_for_timeout(2000)
        logger.info(f"  [playwright] Login via form OK! URL: {page.url}")
        return True
    except Exception:
        page.screenshot(path='/tmp/playwright_login_debug.png')
        logger.error(f"  [playwright] Login falhou. URL: {page.url}")

        error = page.locator('.alert-danger')
        if error.count() > 0:
            logger.error(f"  [playwright] Erro: {error.text_content()}")

        return False


def _navegar_para_invoice(page, invoice_id, logger, inv_name_esperado=None):
    """
    Navega para o form view da invoice no Odoo.

    Estrategia de URL (em ordem):
      1. URL minima sem menu_id/action (nao depende de IDs que mudam)
      2. Fallback: URL completa com menu_id=124, action=243 (Faturamento)

    Apos carregar, verifica se a invoice correta foi aberta (pelo titulo).

    Args:
        page: Playwright page
        invoice_id: ID da invoice no Odoo
        logger: Logger
        inv_name_esperado: Nome da invoice para verificar (ex: "NACOM/2026/0001").
                           Se None, pula verificacao de conteudo.
    """
    # URL minima — Odoo 17 resolve model+view_type sem menu_id/action
    # cids=1-3-4 necessario para multi-company (FB=1, LF=3, CD=4)
    url_minima = (
        f"{ODOO_URL}/web#id={invoice_id}&cids=1-3-4"
        f"&model=account.move&view_type=form"
    )
    # Fallback: URL completa com IDs de menu/action do Faturamento
    # Estes IDs sao da instancia Nacom Goya (podem mudar se Odoo for reinstalado)
    url_completa = (
        f"{ODOO_URL}/web#id={invoice_id}&cids=1-3-4&menu_id=124"
        f"&action=243&model=account.move&view_type=form"
    )

    for tentativa_nav, url in enumerate([url_minima, url_completa], 1):
        logger.info(
            f"  [playwright] Navegando para invoice {invoice_id} "
            f"(estrategia {tentativa_nav}/2)..."
        )
        # NOTA: Odoo SPA mantem long-polling → networkidle NUNCA resolve
        page.goto(url, wait_until='domcontentloaded', timeout=60000)

        # Aguardar form carregar
        try:
            page.wait_for_selector('.o_form_view', timeout=30000)
        except Exception:
            logger.warning(
                f"  [playwright] Form view nao carregou com estrategia "
                f"{tentativa_nav}. {'Tentando fallback...' if tentativa_nav == 1 else 'Continuando mesmo assim...'}"
            )
            if tentativa_nav == 1:
                continue
            # Na segunda tentativa, continua mesmo sem .o_form_view
            page.wait_for_timeout(5000)
            return

        # Pausa para computed fields renderizarem
        page.wait_for_timeout(3000)

        # Verificar se a invoice certa carregou (se temos o nome esperado)
        if inv_name_esperado:
            try:
                # Odoo 17: titulo da invoice fica em .oe_title ou breadcrumb
                page_text = page.locator('.o_form_view').first.text_content()
                if inv_name_esperado in (page_text or ''):
                    logger.info(
                        f"  [playwright] Form view carregado — "
                        f"invoice {inv_name_esperado} confirmada."
                    )
                    return
                else:
                    logger.warning(
                        f"  [playwright] Form carregou mas '{inv_name_esperado}' "
                        f"nao encontrado no conteudo. "
                        f"{'Tentando fallback...' if tentativa_nav == 1 else 'Prosseguindo...'}"
                    )
                    if tentativa_nav == 1:
                        continue
            except Exception:
                pass  # Se nao conseguiu ler texto, prossegue

        logger.info("  [playwright] Form view carregado.")
        return


def _clicar_botao(page, texto_botao, logger):
    """Clica em botao pelo texto visivel. Tenta 3 estrategias."""
    # Estrategia 1: botao com texto exato
    btn = page.locator(f'button:has-text("{texto_botao}")')
    if btn.count() > 0:
        logger.info(f'  [playwright] Botao "{texto_botao}" encontrado. Clicando...')
        btn.first.click()
        return True

    # Estrategia 2: botao dentro de dropdown "..." (Odoo 17)
    dropdown = page.locator(
        '.o_statusbar_buttons .o_dropdown_more, '
        '.o_statusbar_buttons .dropdown-toggle'
    )
    if dropdown.count() > 0:
        logger.info("  [playwright] Abrindo dropdown de acoes...")
        dropdown.first.click()
        page.wait_for_timeout(1000)
        btn = page.locator(
            f'.dropdown-menu button:has-text("{texto_botao}"), '
            f'.dropdown-menu a:has-text("{texto_botao}")'
        )
        if btn.count() > 0:
            logger.info(
                f'  [playwright] Botao "{texto_botao}" no dropdown. Clicando...'
            )
            btn.first.click()
            return True

    # Estrategia 3: menu "Acao"
    action_menu = page.locator(
        '.o_cp_action_menus .dropdown-toggle:has-text("Ação"), '
        '.o_cp_action_menus button:has-text("Ação")'
    )
    if action_menu.count() > 0:
        logger.info('  [playwright] Abrindo menu "Ação"...')
        action_menu.first.click()
        page.wait_for_timeout(1000)
        btn = page.locator(
            f'.dropdown-menu span:has-text("{texto_botao}"), '
            f'.dropdown-menu a:has-text("{texto_botao}")'
        )
        if btn.count() > 0:
            logger.info(f'  [playwright] "{texto_botao}" no menu Ação. Clicando...')
            btn.first.click()
            return True

    logger.warning(f'  [playwright] Botao "{texto_botao}" NAO encontrado!')
    return False


def _clicar_botao_preview_xml(page, logger):
    """Clica no botao 'Pre Visualizar XML NF-e' (variantes de nome)."""
    for nome in [
        "Pré Visualizar XML NF-e",
        "Pré Visualizar XML",
        "Pré-visualizar XML NF-e",
        "Pre Visualizar XML NF-e",
        "Pre-visualizar XML",
        "Preview XML",
    ]:
        if _clicar_botao(page, nome, logger):
            return True

    # Ultima tentativa: qualquer botao com "XML" no texto
    logger.info("  [playwright] Buscando botao generico com 'XML'...")
    btn = page.locator('button:has-text("XML")')
    if btn.count() > 0:
        txt = btn.first.text_content()
        logger.info(f'  [playwright] Botao XML encontrado: "{txt}". Clicando...')
        btn.first.click()
        return True

    return False


def _clicar_botao_transmitir(page, logger):
    """Clica no botao 'Transmitir NF-e' (variantes de nome)."""
    for nome in [
        "Transmitir NF-e",
        "Transmitir",
        "Gerar NF-e",
        "Enviar NF-e",
    ]:
        if _clicar_botao(page, nome, logger):
            return True

    return False
