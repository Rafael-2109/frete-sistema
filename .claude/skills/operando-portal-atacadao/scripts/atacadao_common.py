#!/usr/bin/env python3
"""
atacadao_common.py — Funcoes reutilizaveis para scripts Playwright do Atacadao.

Compartilhado entre imprimir_pedidos.py, consultar_agendamentos.py,
consultar_saldo.py e agendar_lote.py.

Funcoes exportadas:
  - verificar_credenciais_atacadao()
  - carregar_defaults(path)
  - criar_client_com_sessao(headless)
  - criar_sessao_download(headless)
  - verificar_sessao(page)
  - capturar_screenshot(page, nome, diretorio)
  - gerar_saida(sucesso, **kwargs)
  - extrair_tabela(page, table_selector)
"""
import asyncio
import json
import os
import sys
from datetime import datetime

# Adicionar raiz do projeto ao path para imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

ATACADAO_BASE_URL = "https://atacadao.hodiebooking.com.br"

ATACADAO_URLS = {
    "base": ATACADAO_BASE_URL,
    "login": f"{ATACADAO_BASE_URL}/",
    "pedidos": f"{ATACADAO_BASE_URL}/pedidos",
    "pedido_detalhe": f"{ATACADAO_BASE_URL}/pedidos/{{pedido_id}}",
    "criar_carga": f"{ATACADAO_BASE_URL}/cargas/create?id_pedido={{pedido_id}}",
    "carga_detalhe": f"{ATACADAO_BASE_URL}/cargas/{{carga_id}}",
    "agendamento_status": f"{ATACADAO_BASE_URL}/agendamentos/{{protocolo}}",
    "relatorio_itens": f"{ATACADAO_BASE_URL}/relatorio/itens",
    "planilha_pedidos": f"{ATACADAO_BASE_URL}/relatorio/planilhaPedidos",
    "cargas_planilha": f"{ATACADAO_BASE_URL}/cargas-planilha",
}

# Credenciais (lidas do .env)
ATACADAO_USUARIO = os.getenv("ATACADAO_USUARIO")
ATACADAO_SENHA = os.getenv("ATACADAO_SENHA")

# Diretorio para screenshots/evidencias
EVIDENCE_DIR = "/tmp/atacadao_operacoes"

# Storage state paths (ordem de preferencia)
STORAGE_STATE_PATHS = [
    os.path.join(PROJECT_ROOT, "storage_state_atacadao.json"),
    os.path.join(PROJECT_ROOT, "app", "portal", "atacadao", "storage_state_atacadao.json"),
]

# Timeouts (em ms para Playwright)
TIMEOUTS = {
    "page_load": 30000,
    "element_wait": 10000,
    "form_submit": 20000,
    "modal_wait": 5000,
    "session_check": 15000,
}


# ──────────────────────────────────────────────
# Credenciais e configuracao
# ──────────────────────────────────────────────

def verificar_credenciais_atacadao():
    """Verifica se as credenciais do Atacadao estao configuradas no .env."""
    missing = []
    for var in ["ATACADAO_USUARIO", "ATACADAO_SENHA"]:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise EnvironmentError(
            f"Credenciais Atacadao faltando no .env: {', '.join(missing)}"
        )


def carregar_defaults(path=None):
    """Carrega atacadao_defaults.json."""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "atacadao_defaults.json")
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo de defaults nao encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _encontrar_storage_state():
    """Encontra o arquivo storage_state_atacadao.json mais recente.

    Returns:
        str: Caminho do arquivo encontrado, ou None se nenhum existir.
    """
    for path in STORAGE_STATE_PATHS:
        if os.path.exists(path):
            return path
    return None


# ──────────────────────────────────────────────
# Sessao Playwright (sync — usada pelos scripts)
# ──────────────────────────────────────────────

def criar_client_com_sessao(headless=True):
    """
    Cria um AtacadaoPlaywrightClient com sessao salva.

    Reutiliza storage_state_atacadao.json se existir.
    Verifica se a sessao esta valida (nao redireciona para login).

    Args:
        headless: Se True, executa sem janela visivel

    Returns:
        AtacadaoPlaywrightClient com sessao ativa

    Raises:
        RuntimeError: Se sessao expirada ou storage_state nao encontrado
    """
    from app.portal.atacadao.playwright_client import AtacadaoPlaywrightClient

    storage_path = _encontrar_storage_state()
    if not storage_path:
        raise RuntimeError(
            "storage_state_atacadao.json nao encontrado. "
            "Faca login interativo primeiro: "
            "python -m app.portal.atacadao.login_interativo"
        )

    client = AtacadaoPlaywrightClient(headless=headless)
    client.storage_file = storage_path
    client.iniciar_sessao()

    # Verificar sessao navegando para /pedidos
    if not verificar_sessao_sync(client.page):
        client.fechar()
        raise RuntimeError(
            "Sessao do Atacadao expirada. "
            "Faca re-login interativo: "
            "python -m app.portal.atacadao.login_interativo"
        )

    return client


def criar_sessao_download(headless=True):
    """
    Cria sessao sync Playwright com accept_downloads=True e storage_state.

    AtacadaoPlaywrightClient.iniciar_sessao() NAO suporta accept_downloads.
    Esta funcao cria sessao manualmente para interceptar downloads (CSV export).

    Reutilizada por consultar_agendamentos.py, consultar_saldo.py, agendar_lote.py.

    Args:
        headless: Se True, executa sem janela visivel

    Returns:
        tuple: (playwright, browser, context, page)

    Raises:
        RuntimeError: Se storage_state nao encontrado
    """
    from playwright.sync_api import sync_playwright

    storage_path = _encontrar_storage_state()
    if not storage_path:
        raise RuntimeError(
            "storage_state_atacadao.json nao encontrado. "
            "Faca login interativo primeiro: "
            "python -m app.portal.atacadao.login_interativo"
        )

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context(
        storage_state=storage_path,
        accept_downloads=True,
    )
    page = context.new_page()

    return pw, browser, context, page


def verificar_sessao_sync(page):
    """
    Verifica se a sessao do Atacadao esta valida (sync API).

    Navega para /pedidos e verifica se nao foi redirecionado para login.

    Args:
        page: Playwright Page (sync)

    Returns:
        bool: True se sessao valida
    """
    try:
        page.goto(
            ATACADAO_URLS["pedidos"],
            wait_until="domcontentloaded",
            timeout=TIMEOUTS["session_check"],
        )
        page.wait_for_timeout(2000)

        url_atual = page.url.lower()

        # Se redirecionou para login, sessao expirada
        if "login" in url_atual or "signin" in url_atual:
            return False

        # Se ficou em /pedidos, sessao valida
        if "/pedidos" in url_atual:
            return True

        # Verificar indicadores de login
        indicadores = [
            'a[href*="logout"]',
            ".user-menu",
            "#usuario-logado",
            ".navbar-user",
        ]
        for selector in indicadores:
            if page.locator(selector).count() > 0:
                return True

        # Estado indeterminado — assumir invalido
        return False

    except Exception:
        return False


# ──────────────────────────────────────────────
# Sessao Playwright (async — usada pelo MCP tool)
# ──────────────────────────────────────────────

async def verificar_sessao_async(page):
    """
    Verifica se a sessao do Atacadao esta valida (async API).

    Navega para /pedidos e verifica se nao foi redirecionado para login.

    Args:
        page: Playwright Page (async)

    Returns:
        bool: True se sessao valida
    """
    try:
        await page.goto(
            ATACADAO_URLS["pedidos"],
            wait_until="domcontentloaded",
            timeout=TIMEOUTS["session_check"],
        )
        await asyncio.sleep(2)

        url_atual = page.url.lower()

        # Se redirecionou para login, sessao expirada
        if "login" in url_atual or "signin" in url_atual:
            return False

        # Se ficou em /pedidos, sessao valida
        if "/pedidos" in url_atual:
            return True

        # Verificar indicadores de login
        indicadores = [
            'a[href*="logout"]',
            ".user-menu",
            "#usuario-logado",
            ".navbar-user",
        ]
        for selector in indicadores:
            count = await page.locator(selector).count()
            if count > 0:
                return True

        return False

    except Exception:
        return False


# ──────────────────────────────────────────────
# Utilitarios de captura e saida
# ──────────────────────────────────────────────

def capturar_screenshot(page, nome, diretorio=None):
    """
    Captura screenshot como evidencia (sync API).

    Args:
        page: Playwright Page (sync)
        nome: Nome base do arquivo (sem extensao)
        diretorio: Diretorio de destino (default: EVIDENCE_DIR)

    Returns:
        str: Caminho do arquivo salvo
    """
    diretorio = diretorio or EVIDENCE_DIR
    os.makedirs(diretorio, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(diretorio, f"{nome}_{timestamp}.png")
    page.screenshot(path=path, full_page=True)
    return path


async def capturar_screenshot_async(page, nome, diretorio=None):
    """
    Captura screenshot como evidencia (async API).

    Args:
        page: Playwright Page (async)
        nome: Nome base do arquivo (sem extensao)
        diretorio: Diretorio de destino (default: EVIDENCE_DIR)

    Returns:
        str: Caminho do arquivo salvo
    """
    diretorio = diretorio or EVIDENCE_DIR
    os.makedirs(diretorio, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(diretorio, f"{nome}_{timestamp}.png")
    await page.screenshot(path=path, full_page=True)
    return path


def gerar_saida(sucesso, **kwargs):
    """
    Gera saida JSON padrao para stdout.

    Args:
        sucesso: bool
        **kwargs: campos adicionais

    Returns:
        dict (tambem imprime como JSON)
    """
    resultado = {"sucesso": sucesso, **kwargs}
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return resultado


def extrair_tabela(page, table_selector=".VueTables__table"):
    """
    Extrai dados de uma tabela Vue do portal Atacadao (sync API).

    Captura headers e todas as linhas de dados.

    Args:
        page: Playwright Page (sync)
        table_selector: Seletor CSS da tabela

    Returns:
        list[dict]: Lista de dicionarios com dados por coluna
    """
    try:
        page.wait_for_selector(table_selector, timeout=TIMEOUTS["element_wait"])
    except Exception:
        return []

    return page.evaluate(f"""() => {{
        const table = document.querySelector('{table_selector}');
        if (!table) return [];

        // Capturar headers
        const headers = [];
        table.querySelectorAll('thead th').forEach(th => {{
            headers.push(th.textContent.trim());
        }});

        // Capturar linhas
        const rows = [];
        table.querySelectorAll('tbody tr:not(.VueTables__no-results)').forEach(tr => {{
            const cells = tr.querySelectorAll('td');
            if (cells.length === 0) return;

            const row = {{}};
            cells.forEach((td, i) => {{
                const key = headers[i] || ('col_' + i);
                row[key] = td.textContent.trim();
            }});
            rows.push(row);
        }});

        return rows;
    }}""")


def extrair_tabela_com_paginacao(page, table_selector=".VueTables__table", max_paginas=10):
    """
    Extrai dados de tabela com suporte a paginacao Vue (sync API).

    Detecta botao "proximo" e navega ate o final ou max_paginas.

    Args:
        page: Playwright Page (sync)
        table_selector: Seletor CSS da tabela
        max_paginas: Limite de paginas a processar

    Returns:
        list[dict]: Todos os registros de todas as paginas
    """
    todos = []

    for _ in range(1, max_paginas + 1):
        registros = extrair_tabela(page, table_selector)
        if not registros:
            break

        todos.extend(registros)

        # Tentar ir para proxima pagina
        try:
            # VueTables usa <a> ou <li> com class "page-link" e aria-label "Next"
            next_btn = page.locator(
                'a.page-link[aria-label="Next"], '
                'li.VuePagination__pagination-item-next-page:not(.disabled) a'
            )
            if next_btn.count() == 0:
                break

            # Verificar se botao nao esta desabilitado
            parent_li = next_btn.first.locator("..")
            parent_class = parent_li.get_attribute("class") or ""
            if "disabled" in parent_class:
                break

            next_btn.first.click()
            page.wait_for_timeout(1000)  # Aguardar AJAX da tabela

        except Exception:
            break

    return todos
