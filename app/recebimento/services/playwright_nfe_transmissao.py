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

        # Ler nome + company_id da invoice antes do loop (para verificar pagina e
        # resolver cids/menu_id por CNPJ — LF=5 usa cids=5,menu_id=217; NACOM 1-3-4,124)
        inv_name_esperado = None
        company_id_invoice = None
        try:
            inv_pre = odoo.execute_kw(
                'account.move', 'read',
                [[invoice_id]],
                {'fields': ['name', 'company_id']}
            )
            if inv_pre:
                inv_name_esperado = inv_pre[0].get('name')
                cid_raw = inv_pre[0].get('company_id')
                if isinstance(cid_raw, (list, tuple)) and cid_raw:
                    company_id_invoice = cid_raw[0]
                logger.info(
                    f"  [playwright] Invoice alvo: {inv_name_esperado} "
                    f"(id={invoice_id}, company_id={company_id_invoice})"
                )
        except Exception as e:
            logger.warning(f"  [playwright] Nao conseguiu ler nome da invoice: {e}")

        # Forcar mudanca de allowed_company_ids na sessao se a invoice eh de
        # outra empresa do grupo (ex: LF=5 quando user default e' FB=1).
        # Sem isso, a regra global "Account Entry" (ir.rule 71) filtra a
        # invoice e UI mostra "Erro de acesso a Faturas".
        if company_id_invoice:
            cids_alvo, _ = _resolver_cids_e_menu(company_id_invoice)
            try:
                logger.info(
                    f"  [playwright] Forcando allowed_company_ids=cids={cids_alvo} "
                    f"(invoice company_id={company_id_invoice})"
                )
                page.goto(
                    f"{ODOO_URL}/web?cids={cids_alvo}",
                    wait_until='domcontentloaded', timeout=60000,
                )
                page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"  [playwright] Falha ao forcar cids: {e}")

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
                _navegar_para_invoice(page, invoice_id, logger, inv_name_esperado, company_id=company_id_invoice)

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
                    _navegar_para_invoice(page, invoice_id, logger, inv_name_esperado, company_id=company_id_invoice)
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
                    # Screenshot logo apos click (pode aparecer wizard de confirmacao)
                    try:
                        _shot1 = f'/tmp/sefaz_debug/pos_click_transmitir_inv{invoice_id}_t{tentativa}.png'
                        page.screenshot(path=_shot1)
                        logger.info(f"  [playwright] Screenshot pos-click: {_shot1}")
                    except Exception:
                        pass
                    # Detectar e tratar wizard de confirmacao (se aparecer)
                    page.wait_for_timeout(2000)
                    _tratar_wizard_confirmacao(page, logger)
                    logger.info("  [playwright] Aguardando 25s para SEFAZ processar...")
                    page.wait_for_timeout(25000)
                    try:
                        _shot2 = f'/tmp/sefaz_debug/pos_sefaz_inv{invoice_id}_t{tentativa}.png'
                        page.screenshot(path=_shot2)
                        logger.info(f"  [playwright] Screenshot pos-SEFAZ: {_shot2}")
                    except Exception:
                        pass
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


def _resolver_cids_e_menu(company_id):
    """Resolve (cids, menu_id) por CNPJ do grupo.

    NACOM GOYA (CNPJ 61.724.241/000X-XX) — FB=1, SC=3, CD=4: mesmo CNPJ,
        compartilham menu_id=124. cids='1-3-4'.
    LA FAMIGLIA (CNPJ 18.467.441/0001-63) — LF=5: CNPJ separado,
        menu_id=217. cids='5'.

    Validado por URL real do usuario 2026-05-18:
        https://odoo.nacomgoya.com.br/web?debug=1#id=608607&cids=5&menu_id=217&model=account.move&view_type=form
    """
    if company_id == 5:
        return '5', 217
    return '1-3-4', 124


def _navegar_para_invoice(
    page, invoice_id, logger, inv_name_esperado=None,
    company_id=None,
):
    """
    Navega para o form view da invoice no Odoo.

    Estrategia de URL (em ordem):
      1. URL minima sem menu_id/action (nao depende de IDs que mudam)
      2. Fallback: URL completa com menu_id+action conforme empresa

    cids e menu_id sao resolvidos dinamicamente por company_id (G_LF/NACOM).

    Args:
        page: Playwright page
        invoice_id: ID da invoice no Odoo
        logger: Logger
        inv_name_esperado: Nome da invoice para verificar (ex: "NACOM/2026/0001").
                           Se None, pula verificacao de conteudo.
        company_id: company da invoice (1=FB, 3=SC, 4=CD, 5=LF).
            Se None, default NACOM (cids='1-3-4', menu_id=124).
    """
    cids, menu_id = _resolver_cids_e_menu(company_id)
    # NAO usar ?debug=1 — abre modal tecnico que bloqueia clicks no Playwright.
    # URL minima (sem menu_id) primeiro; fallback com menu_id por CNPJ.
    url_minima = (
        f"{ODOO_URL}/web#id={invoice_id}&cids={cids}"
        f"&model=account.move&view_type=form"
    )
    url_completa = (
        f"{ODOO_URL}/web#id={invoice_id}&cids={cids}&menu_id={menu_id}"
        f"&model=account.move&view_type=form"
    )

    for tentativa_nav, url in enumerate([url_minima, url_completa], 1):
        logger.info(
            f"  [playwright] Navegando para invoice {invoice_id} "
            f"(estrategia {tentativa_nav}/2): {url}"
        )
        # NOTA: Odoo SPA mantem long-polling → networkidle NUNCA resolve
        page.goto(url, wait_until='domcontentloaded', timeout=60000)

        # Aguardar form carregar
        try:
            page.wait_for_selector('.o_form_view', timeout=30000)
        except Exception:
            # Screenshot diagnostico
            try:
                _shot = f'/tmp/sefaz_debug/nav_falhou_inv{invoice_id}_est{tentativa_nav}.png'
                page.screenshot(path=_shot)
                logger.warning(f"  [playwright] Screenshot: {_shot}")
            except Exception:
                pass
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


def _tratar_wizard_confirmacao(page, logger):
    """Se aparecer wizard/dialog de confirmacao apos clicar 'Transmitir NF-e',
    clica no botao de OK/Confirm/Sim para prosseguir.

    Odoo l10n_br pode mostrar wizard 'Confirmar transmissao para SEFAZ?'
    com botoes 'Confirmar' / 'Cancelar'.
    """
    # Procurar wizards comuns (NAO sao os o_technical_modal — sao .modal padrao)
    dialog = page.locator('.modal.show:not(.o_technical_modal), .o_dialog:visible')
    if dialog.count() == 0:
        return False
    logger.info(f"  [playwright] Wizard de confirmacao detectado ({dialog.count()})")
    # Capturar texto para diagnostico
    try:
        texto = dialog.first.text_content() or ''
        logger.info(f"  [playwright] Texto wizard: {texto[:200]}")
    except Exception:
        pass
    for seletor in [
        '.modal.show button.btn-primary:has-text("Confirmar")',
        '.modal.show button.btn-primary:has-text("Confirm")',
        '.modal.show button.btn-primary:has-text("Sim")',
        '.modal.show button.btn-primary:has-text("Yes")',
        '.modal.show button.btn-primary:has-text("OK")',
        '.modal.show button.btn-primary:has-text("Ok")',
        '.modal.show .modal-footer button.btn-primary',
        '.o_dialog button.btn-primary',
    ]:
        btn = page.locator(seletor)
        if btn.count() > 0:
            try:
                btn.first.click(timeout=5000)
                page.wait_for_timeout(1000)
                logger.info(f"  [playwright] Wizard confirmado via '{seletor}'")
                return True
            except Exception:
                continue
    logger.warning("  [playwright] Wizard detectado mas botao confirmar nao achado")
    return False


def _fechar_modais_tecnicos(page, logger):
    """Fecha modais .o_technical_modal que interceptam clicks.

    Em Odoo 17, modais tecnicos (avisos sistema, alertas) podem aparecer
    sobre o form view e bloquear clicks em botoes. Tenta fechar via:
    1. Botao com text 'Fechar'/'Close'/'Ok' dentro do modal
    2. Botao close (.btn-close ou .o_form_button_cancel)
    3. Pressionar Escape
    """
    modal = page.locator('.o_technical_modal:visible')
    if modal.count() == 0:
        return False
    logger.info(f"  [playwright] Modal tecnico detectado ({modal.count()}). Fechando...")
    for seletor in [
        '.o_technical_modal button.btn-close',
        '.o_technical_modal .btn-close',
        '.o_technical_modal button:has-text("Fechar")',
        '.o_technical_modal button:has-text("Close")',
        '.o_technical_modal button:has-text("Ok")',
        '.o_technical_modal button:has-text("OK")',
        '.o_technical_modal .modal-header button',
    ]:
        btn_close = page.locator(seletor)
        if btn_close.count() > 0:
            try:
                btn_close.first.click(timeout=5000)
                page.wait_for_timeout(500)
                logger.info(f"  [playwright] Modal fechado via '{seletor}'")
                return True
            except Exception:
                continue
    # Fallback: Escape
    try:
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
        if page.locator('.o_technical_modal:visible').count() == 0:
            logger.info("  [playwright] Modal fechado via Escape")
            return True
    except Exception:
        pass
    logger.warning("  [playwright] Nao consegui fechar modal tecnico!")
    return False


def _clicar_botao(page, texto_botao, logger):
    """Clica em botao pelo texto visivel. Tenta 3 estrategias."""
    # Fechar modais tecnicos que possam estar bloqueando clicks
    _fechar_modais_tecnicos(page, logger)
    # Estrategia 1: botao com texto exato
    btn = page.locator(f'button:has-text("{texto_botao}")')
    if btn.count() > 0:
        logger.info(f'  [playwright] Botao "{texto_botao}" encontrado. Clicando...')
        try:
            btn.first.click(timeout=10000)
        except Exception as e:
            # Modal pode ter reaparecido — tentar fechar e re-clicar com force
            logger.warning(f"  [playwright] Click bloqueado ({e}). Tentando force=True...")
            _fechar_modais_tecnicos(page, logger)
            try:
                btn.first.click(force=True, timeout=10000)
            except Exception as e2:
                logger.error(f"  [playwright] Click force tambem falhou: {e2}")
                return False
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
