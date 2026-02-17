"""
Custom Tool MCP: Browser (navegacao web via Playwright headless)

Permite ao agente web e bot Teams navegar em sites externos,
ler paginas HTML, preencher formularios e clicar em elementos.
Projetado para acessar o sistema SSW e manuais HTML.

Persistencia de sessao: cookies e localStorage salvos em /tmp/
para manter login entre mensagens do mesmo processo.

Suporte SSW:
    - Frameset: browser_switch_frame permite trocar entre frames
    - JavaScript: browser_evaluate_js executa JS (menus, subMenu01Click)
    - Login: browser_ssw_login faz login automatico via .env
    - Navegacao: browser_ssw_navigate_option vai direto a uma opcao

Tools expostas (12):
    - browser_navigate: abre URL e retorna snapshot
    - browser_snapshot: captura snapshot da pagina atual
    - browser_screenshot: captura screenshot visual (PNG) da pagina
    - browser_click: clica em elemento por texto/selector/role
    - browser_type: preenche campo por label/selector
    - browser_select_option: seleciona opcao em dropdown
    - browser_read_content: le texto limpo da pagina
    - browser_close: fecha browser e limpa recursos
    - browser_evaluate_js: executa JavaScript na pagina/frame (C1)
    - browser_switch_frame: troca frame ativo para interacoes (C2)
    - browser_ssw_login: login automatico SSW via .env (C3)
    - browser_ssw_navigate_option: navega para opcao SSW por numero (C4)

Referencia SDK:
    https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools
"""

import atexit
import asyncio
import base64
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# =====================================================================
# ESTADO DO BROWSER (module-level, persiste no processo)
# =====================================================================

_playwright = None
_browser = None
_context = None
_page = None

NAVIGATION_TIMEOUT = 60000  # 60 segundos
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}
_frame_local = threading.local()  # Frame ativo por thread (isolamento entre requests)


def _get_current_frame():
    """Retorna frame ativo da thread atual (None = page principal)."""
    return getattr(_frame_local, 'frame', None)


def _set_current_frame(frame):
    """Define frame ativo da thread atual."""
    _frame_local.frame = frame


def _get_storage_path() -> str:
    """Retorna path de storage state baseado na sessao atual.

    Cada sessao de usuario tem seu proprio arquivo de cookies/localStorage,
    evitando que credenciais SSW vazem entre usuarios diferentes.
    """
    try:
        from app.agente.config.permissions import get_current_session_id
        session_id = get_current_session_id()
        if session_id:
            return f"/tmp/playwright-session-{session_id}.json"
    except (ImportError, RuntimeError):
        pass
    return "/tmp/playwright-session.json"  # fallback


# =====================================================================
# HELPERS
# =====================================================================

async def _ensure_browser():
    """
    Lazy init: cria browser + context + page no primeiro uso.

    Restaura storage_state (cookies/localStorage) se existir de sessao anterior.
    Configura viewport padrao e timeout de navegacao.

    Returns:
        Page instance do Playwright
    """
    global _playwright, _browser, _context, _page
    if _page is not None:
        return _page

    from playwright.async_api import async_playwright

    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=True)

    context_opts: Dict[str, Any] = {"viewport": DEFAULT_VIEWPORT}

    # Restaurar cookies/localStorage de sessao anterior (isolado por sessao)
    storage_path = _get_storage_path()
    if os.path.exists(storage_path):
        try:
            context_opts["storage_state"] = storage_path
            logger.info(f"[BROWSER] Restaurando storage_state de {storage_path}")
        except Exception as e:
            logger.warning(f"[BROWSER] Falha ao restaurar storage_state (ignorado): {e}")

    _context = await _browser.new_context(**context_opts)
    _page = await _context.new_page()
    _page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)

    logger.info("[BROWSER] Browser inicializado (headless Chromium)")
    return _page


async def _save_storage_state():
    """Salva cookies/localStorage para persistencia entre sessoes (isolado por sessao)."""
    global _context
    if _context is not None:
        try:
            storage_path = _get_storage_path()
            await _context.storage_state(path=storage_path)
        except Exception as e:
            logger.warning(f"[BROWSER] Falha ao salvar storage_state: {e}")


def _get_active_target():
    """
    Retorna frame ativo ou page para interacoes com elementos.

    Quando browser_switch_frame seleciona um frame, todas as interacoes
    (click, type, select, read) operam dentro desse frame.
    """
    global _page
    current_frame = _get_current_frame()
    return current_frame if current_frame is not None else _page


async def _get_snapshot() -> str:
    """
    Captura accessibility snapshot da pagina atual.

    Returns:
        Texto formatado com titulo, URL e arvore de acessibilidade
    """
    global _page
    if _page is None:
        return "Nenhuma pagina aberta. Use browser_navigate primeiro."

    try:
        snapshot = await _page.accessibility.snapshot()
        if not snapshot:
            title = await _page.title()
            return f"Pagina: {title} ({_page.url})\n(sem conteudo acessivel)"

        title = await _page.title()
        lines = [f"Pagina: {title} ({_page.url})\n"]
        _format_accessibility_tree(snapshot, lines)

        result = "\n".join(lines)
        # Limitar tamanho para evitar estourar contexto
        if len(result) > 50000:
            result = result[:50000] + "\n\n... (snapshot truncado, use browser_read_content para texto completo)"
        return result
    except Exception as e:
        return f"Erro ao capturar snapshot: {e}"


def _format_accessibility_tree(
    node: Dict[str, Any],
    lines: List[str],
    indent: int = 0,
):
    """
    Formata accessibility tree como texto indentado.

    Cada no mostra: role "name" value="value"
    Filhos sao indentados com 2 espacos por nivel.
    """
    prefix = "  " * indent
    role = node.get("role", "")
    name = node.get("name", "")
    value = node.get("value", "")

    # Skip nos sem conteudo util
    if not role and not name:
        for child in node.get("children", []):
            _format_accessibility_tree(child, lines, indent)
        return

    parts = [role]
    if name:
        # Truncar nomes muito longos
        display_name = name[:100] + "..." if len(name) > 100 else name
        parts.append(f'"{display_name}"')
    if value:
        display_value = value[:100] + "..." if len(value) > 100 else value
        parts.append(f'value="{display_value}"')

    lines.append(f"{prefix}{' '.join(parts)}")

    for child in node.get("children", []):
        _format_accessibility_tree(child, lines, indent + 1)


async def _close_browser():
    """Fecha browser e limpa recursos."""
    global _playwright, _browser, _context, _page

    if _context is not None:
        try:
            await _context.close()
        except Exception:
            pass

    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass

    if _playwright is not None:
        try:
            await _playwright.stop()
        except Exception:
            pass

    _playwright = None
    _browser = None
    _context = None
    _page = None
    _set_current_frame(None)
    logger.info("[BROWSER] Browser fechado e recursos liberados")


def _cleanup_browser_sync():
    """Cleanup sincrono para atexit — garante que browser nao fica orfao."""
    global _playwright, _browser, _context, _page
    if _browser is not None:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_close_browser())
            loop.close()
        except Exception:
            pass
        finally:
            _playwright = None
            _browser = None
            _context = None
            _page = None
            _set_current_frame(None)


atexit.register(_cleanup_browser_sync)


# =====================================================================
# CUSTOM TOOLS — @tool decorator
# =====================================================================

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server, ToolAnnotations

    # -----------------------------------------------------------------
    # Tool 1: browser_navigate
    # -----------------------------------------------------------------
    @tool(
        "browser_navigate",
        (
            "Navega para URL e retorna snapshot da pagina. "
            "Use para acessar sites externos, manuais HTML ou sistemas web. "
            "A sessao persiste cookies entre chamadas (login mantido). "
            "Exemplos: 'acesse https://example.com', 'abra o SSW'."
        ),
        {
            "url": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def browser_navigate(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navega para URL e retorna accessibility snapshot.

        Args:
            args: {"url": str} — URL completa (com https://)

        Returns:
            MCP tool response com titulo e snapshot da pagina.
        """
        url = (args.get("url") or "").strip()
        if not url:
            return {
                "content": [{"type": "text", "text": "Erro: URL obrigatoria."}],
                "is_error": True,
            }

        # Adicionar protocolo se ausente
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            page = await _ensure_browser()
            response = await page.goto(url, wait_until="domcontentloaded")

            status = response.status if response else "?"
            await _save_storage_state()

            snapshot = await _get_snapshot()

            return {
                "content": [{"type": "text", "text": f"Status: {status}\n\n{snapshot}"}],
            }

        except Exception as e:
            error_msg = f"Erro ao navegar para {url}: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 2: browser_snapshot
    # -----------------------------------------------------------------
    @tool(
        "browser_snapshot",
        (
            "Captura snapshot da pagina atual (arvore de acessibilidade). "
            "Use para ver o estado atual da pagina apos navegacao ou interacao. "
            "Retorna elementos com role, nome e valor."
        ),
        {},
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def browser_snapshot(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Captura accessibility snapshot da pagina atual.

        Returns:
            MCP tool response com arvore de acessibilidade formatada.
        """
        try:
            snapshot = await _get_snapshot()
            return {
                "content": [{"type": "text", "text": snapshot}],
            }
        except Exception as e:
            error_msg = f"Erro ao capturar snapshot: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 3: browser_screenshot (screenshot visual PNG)
    # -----------------------------------------------------------------

    SCREENSHOTS_DIR = os.path.join("/tmp", "agente_files", "screenshots")

    def _cleanup_old_screenshots(max_age_seconds: int = 3600) -> int:
        """
        Remove screenshots com mais de max_age_seconds.

        Lazy cleanup — chamado no inicio de cada captura.
        Limpa PNGs antigos em /tmp/agente_files/screenshots/.

        Returns:
            Numero de arquivos removidos.
        """
        removed = 0
        try:
            if not os.path.exists(SCREENSHOTS_DIR):
                return 0
            now = time.time()
            for fname in os.listdir(SCREENSHOTS_DIR):
                if not fname.endswith(".png"):
                    continue
                fpath = os.path.join(SCREENSHOTS_DIR, fname)
                try:
                    if now - os.path.getmtime(fpath) > max_age_seconds:
                        os.remove(fpath)
                        removed += 1
                except OSError:
                    pass
        except Exception as e:
            logger.warning(f"[BROWSER] Erro no cleanup de screenshots: {e}")
        return removed

    def _save_screenshot(png_bytes: bytes, prefix: str = "screenshot") -> str:
        """
        Salva PNG em /tmp/agente_files/screenshots/ com nome unico.

        Args:
            png_bytes: Bytes da imagem PNG.
            prefix: Prefixo do nome do arquivo.

        Returns:
            Nome do arquivo salvo (ex: screenshot_abc12345.png).
        """
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        short_id = uuid.uuid4().hex[:8]
        filename = f"{prefix}_{short_id}.png"
        filepath = os.path.join(SCREENSHOTS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(png_bytes)
        return filename

    @tool(
        "browser_screenshot",
        (
            "Captura screenshot VISUAL (imagem PNG) da pagina ou elemento. "
            "Retorna a imagem para analise visual + URL para exibir ao usuario. "
            "Diferente de browser_snapshot que retorna apenas texto (acessibilidade). "
            "Use para: evidencia visual, verificar layout, graficos, tabelas, aparencia. "
            "Parametros: full_page (bool, default false), selector (string CSS, opcional). "
            "Exemplos: {} (viewport), {\"full_page\": true} (pagina inteira), "
            "{\"selector\": \"#tabela\"} (elemento especifico)."
        ),
        {
            "full_page": bool,
            "selector": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def browser_screenshot(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Captura screenshot visual (PNG) da pagina ou elemento.

        Retorna dual content:
        1. ImageContent (base64 PNG) — Claude ve a pagina via Vision
        2. TextContent com URL — agente inclui ![Screenshot](url) no markdown

        Args:
            args: {
                "full_page": bool (default False — viewport only),
                "selector": str (CSS selector para capturar elemento especifico, opcional),
            }

        Returns:
            MCP tool response com [ImageContent, TextContent].
        """
        global _page
        if _page is None:
            return {
                "content": [{"type": "text", "text": "Nenhuma pagina aberta. Use browser_navigate primeiro."}],
                "is_error": True,
            }

        full_page = args.get("full_page", False)
        selector = (args.get("selector") or "").strip()

        try:
            # Lazy cleanup de screenshots antigos (> 1 hora)
            removed = _cleanup_old_screenshots(max_age_seconds=3600)
            if removed > 0:
                logger.info(f"[BROWSER] Cleanup: {removed} screenshots antigos removidos")

            target = _get_active_target()

            # Capturar PNG bytes
            if selector:
                # Screenshot de elemento especifico
                try:
                    element = target.locator(selector)
                    png_bytes = await element.screenshot(type="png")
                    capture_desc = f"elemento '{selector}'"
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Erro: selector '{selector}' nao encontrado ou nao visivel: {str(e)[:200]}"}],
                        "is_error": True,
                    }
            else:
                # Screenshot da pagina (viewport ou full_page)
                png_bytes = await _page.screenshot(type="png", full_page=full_page)
                capture_desc = "pagina inteira" if full_page else "viewport"

            # Salvar arquivo e gerar URL
            filename = _save_screenshot(png_bytes)
            url = f"/agente/api/files/screenshots/{filename}"

            # Codificar em base64 para ImageContent
            b64_data = base64.b64encode(png_bytes).decode("utf-8")

            # Log de tamanho
            size_kb = len(png_bytes) / 1024
            size_mb = size_kb / 1024
            if size_mb > 5:
                logger.warning(f"[BROWSER] Screenshot grande: {size_mb:.1f}MB ({capture_desc})")
            else:
                logger.info(f"[BROWSER] Screenshot capturado: {size_kb:.0f}KB ({capture_desc}) → {filename}")

            title = await _page.title()
            page_url = _page.url

            return {
                "content": [
                    {
                        "type": "image",
                        "data": b64_data,
                        "mimeType": "image/png",
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Screenshot capturado ({capture_desc}): {size_kb:.0f}KB\n"
                            f"Pagina: {title} ({page_url})\n"
                            f"URL da imagem: {url}\n\n"
                            f"Para exibir ao usuario, inclua no markdown:\n"
                            f"![Screenshot]({url})"
                        ),
                    },
                ],
            }

        except Exception as e:
            error_msg = f"Erro ao capturar screenshot: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 4: browser_click
    # -----------------------------------------------------------------
    @tool(
        "browser_click",
        (
            "Clica em elemento da pagina. "
            "Pode usar texto visivel (text), role+name semantico, ou seletor CSS. "
            "Prioridade: text > role+name > selector. "
            "Use 'text' para links e botoes com texto visivel. "
            "Use 'selector' para elementos sem texto claro (CSS selector). "
            "Exemplos: text='Entrar', text='Manual', selector='#btn-login'."
        ),
        {
            "text": str,
            "selector": str,
            "role": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def browser_click(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clica em elemento por texto, role ou selector CSS.

        Args:
            args: {
                "text": str (texto visivel do elemento, opcional),
                "selector": str (CSS selector, opcional),
                "role": str (ARIA role, opcional — combinado com text como name),
            }

        Returns:
            MCP tool response com snapshot apos o click.
        """
        global _page
        if _page is None:
            return {
                "content": [{"type": "text", "text": "Nenhuma pagina aberta. Use browser_navigate primeiro."}],
                "is_error": True,
            }

        text = (args.get("text") or "").strip()
        selector = (args.get("selector") or "").strip()
        role = (args.get("role") or "").strip()

        if not text and not selector and not role:
            return {
                "content": [{"type": "text", "text": "Erro: forneça 'text', 'selector' ou 'role' para identificar o elemento."}],
                "is_error": True,
            }

        try:
            target = _get_active_target()
            # Prioridade: text > role+name > selector
            if text and role:
                await target.get_by_role(role, name=text).click()
                action = f"Clicou em {role} '{text}'"
            elif text:
                await target.get_by_text(text, exact=False).first.click()
                action = f"Clicou em '{text}'"
            elif role:
                await target.get_by_role(role).first.click()
                action = f"Clicou em {role}"
            elif selector:
                await target.click(selector)
                action = f"Clicou em '{selector}'"

            # Aguardar estabilizacao da pagina
            try:
                await _page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass  # Timeout ok — pagina pode nao navegar

            await _save_storage_state()
            snapshot = await _get_snapshot()

            return {
                "content": [{"type": "text", "text": f"{action}\n\n{snapshot}"}],
            }

        except Exception as e:
            error_msg = f"Erro ao clicar: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 4: browser_type
    # -----------------------------------------------------------------
    @tool(
        "browser_type",
        (
            "Preenche campo de texto na pagina. "
            "Pode identificar o campo por label (texto do rotulo) ou seletor CSS. "
            "Prioridade: label > selector. "
            "Usa fill() que substitui o conteudo existente. "
            "Exemplos: label='Usuário' text='admin', selector='#email' text='user@test.com'."
        ),
        {
            "text": str,
            "label": str,
            "selector": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def browser_type(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preenche campo de texto por label ou selector.

        Args:
            args: {
                "text": str (texto a digitar, obrigatorio),
                "label": str (label do campo, opcional),
                "selector": str (CSS selector, opcional),
            }

        Returns:
            MCP tool response com confirmacao.
        """
        global _page
        if _page is None:
            return {
                "content": [{"type": "text", "text": "Nenhuma pagina aberta. Use browser_navigate primeiro."}],
                "is_error": True,
            }

        text = args.get("text", "")
        label = (args.get("label") or "").strip()
        selector = (args.get("selector") or "").strip()

        if text is None or text == "":
            return {
                "content": [{"type": "text", "text": "Erro: 'text' obrigatorio (texto a digitar)."}],
                "is_error": True,
            }

        if not label and not selector:
            return {
                "content": [{"type": "text", "text": "Erro: forneça 'label' ou 'selector' para identificar o campo."}],
                "is_error": True,
            }

        try:
            target = _get_active_target()
            if label:
                await target.get_by_label(label).fill(str(text))
                action = f"Preencheu campo '{label}'"
            elif selector:
                await target.fill(selector, str(text))
                action = f"Preencheu campo '{selector}'"

            return {
                "content": [{"type": "text", "text": f"{action} com '{text}'"}],
            }

        except Exception as e:
            error_msg = f"Erro ao preencher campo: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 5: browser_select_option
    # -----------------------------------------------------------------
    @tool(
        "browser_select_option",
        (
            "Seleciona opcao em dropdown/select. "
            "Identifica o dropdown por seletor CSS e a opcao por valor ou label. "
            "Exemplos: selector='#uf' value='SP', selector='select[name=estado]' value='RJ'."
        ),
        {
            "selector": str,
            "value": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def browser_select_option(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seleciona opcao em dropdown.

        Args:
            args: {
                "selector": str (CSS selector do <select>, obrigatorio),
                "value": str (valor ou label da opcao, obrigatorio),
            }

        Returns:
            MCP tool response com confirmacao.
        """
        global _page
        if _page is None:
            return {
                "content": [{"type": "text", "text": "Nenhuma pagina aberta. Use browser_navigate primeiro."}],
                "is_error": True,
            }

        selector = (args.get("selector") or "").strip()
        value = (args.get("value") or "").strip()

        if not selector or not value:
            return {
                "content": [{"type": "text", "text": "Erro: 'selector' e 'value' sao obrigatorios."}],
                "is_error": True,
            }

        try:
            target = _get_active_target()
            # Tentar por value primeiro, depois por label
            try:
                await target.select_option(selector, value=value)
            except Exception:
                await target.select_option(selector, label=value)

            return {
                "content": [{"type": "text", "text": f"Selecionou '{value}' em '{selector}'"}],
            }

        except Exception as e:
            error_msg = f"Erro ao selecionar opcao: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 6: browser_read_content
    # -----------------------------------------------------------------
    @tool(
        "browser_read_content",
        (
            "Le conteudo da pagina como texto limpo (sem HTML). "
            "Util para ler paginas de manual inteiras ou extrair texto de secoes. "
            "Pode especificar seletor CSS para ler apenas parte da pagina. "
            "Default: le o <body> inteiro. "
            "Exemplos: selector='body', selector='.manual-content', selector='#main'."
        ),
        {
            "selector": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def browser_read_content(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Le conteudo como texto limpo (inner_text).

        Args:
            args: {
                "selector": str (CSS selector, default "body"),
            }

        Returns:
            MCP tool response com texto limpo da pagina/secao.
        """
        global _page
        if _page is None:
            return {
                "content": [{"type": "text", "text": "Nenhuma pagina aberta. Use browser_navigate primeiro."}],
                "is_error": True,
            }

        selector = (args.get("selector") or "body").strip()

        try:
            target = _get_active_target()
            text_content = await target.inner_text(selector)
            title = await _page.title()

            # Limitar tamanho para evitar estourar contexto
            if len(text_content) > 100000:
                text_content = text_content[:100000] + "\n\n... (conteudo truncado — 100K chars)"

            header = f"Pagina: {title} ({_page.url})\nSeletor: {selector}\n\n"
            return {
                "content": [{"type": "text", "text": header + text_content}],
            }

        except Exception as e:
            error_msg = f"Erro ao ler conteudo (selector='{selector}'): {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 7: browser_close
    # -----------------------------------------------------------------
    @tool(
        "browser_close",
        (
            "Fecha o browser e limpa recursos. "
            "Use quando terminar de navegar para liberar memoria. "
            "O browser sera reiniciado automaticamente na proxima navegacao."
        ),
        {},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def browser_close(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fecha browser e limpa todos os recursos.

        Returns:
            MCP tool response com confirmacao.
        """
        try:
            await _close_browser()
            return {
                "content": [{"type": "text", "text": "Browser fechado com sucesso. Sera reiniciado automaticamente na proxima navegacao."}],
            }

        except Exception as e:
            error_msg = f"Erro ao fechar browser: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 8: browser_evaluate_js (C1)
    # -----------------------------------------------------------------
    @tool(
        "browser_evaluate_js",
        (
            "Executa JavaScript na pagina ou frame ativo. "
            "OBRIGATORIO para SSW: menu usa subMenu01Click(), popups e funcoes internas. "
            "Retorna resultado da expressao + snapshot apos execucao. "
            "Se um frame estiver selecionado (via browser_switch_frame), executa NO frame. "
            "Exemplos: script='subMenu01Click(this, 6)', script='document.title', "
            "script='document.querySelectorAll(\"input\").length'."
        ),
        {
            "script": str,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def browser_evaluate_js(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa JavaScript arbitrario na pagina ou frame ativo.

        Args:
            args: {"script": str} — codigo JavaScript a executar

        Returns:
            MCP tool response com resultado JS + snapshot.
        """
        script = (args.get("script") or "").strip()
        if not script:
            return {
                "content": [{"type": "text", "text": "Erro: 'script' obrigatorio (codigo JavaScript)."}],
                "is_error": True,
            }

        try:
            page = await _ensure_browser()
            target = _get_active_target()

            result = await target.evaluate(script)

            # Aguardar estabilizacao (JS pode causar navegacao)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass

            await _save_storage_state()
            snapshot = await _get_snapshot()

            result_str = str(result) if result is not None else "(void)"
            # Truncar resultado muito longo
            if len(result_str) > 5000:
                result_str = result_str[:5000] + "... (truncado)"

            _active_frame = _get_current_frame()
            frame_info = f" [frame: {_active_frame.name}]" if _active_frame else ""
            return {
                "content": [{"type": "text", "text": f"JS resultado{frame_info}: {result_str}\n\n{snapshot}"}],
            }

        except Exception as e:
            error_msg = f"Erro ao executar JS: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 9: browser_switch_frame (C2)
    # -----------------------------------------------------------------
    @tool(
        "browser_switch_frame",
        (
            "Troca o frame ativo para interacoes. SSW usa frameset com multiplos frames. "
            "Apos trocar, browser_click/type/read_content/evaluate_js operam DENTRO do frame. "
            "Use name='main' para voltar ao frame principal (page). "
            "Omita name (ou list_frames=true) para listar frames disponiveis. "
            "Exemplos: name='mainFrame', name='menuFrame', name='main' (voltar)."
        ),
        {
            "name": str,
            "list_frames": bool,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    async def browser_switch_frame(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lista frames ou troca para um frame especifico.

        Args:
            args: {
                "name": str (nome do frame, ou "main" para page, opcional),
                "list_frames": bool (True para listar sem trocar, opcional),
            }

        Returns:
            MCP tool response com lista de frames ou confirmacao de troca.
        """
        name = (args.get("name") or "").strip()
        list_frames = args.get("list_frames", False)

        try:
            page = await _ensure_browser()
            _active_frame = _get_current_frame()

            # Modo listagem: retorna frames disponiveis
            if list_frames or not name:
                frames = page.frames
                frame_lines = []
                for i, f in enumerate(frames):
                    marker = " ← ATIVO" if f == _active_frame else ""
                    frame_lines.append(f"  [{i}] name='{f.name}' url='{f.url}'{marker}")

                current = f"Frame ativo: {_active_frame.name}" if _active_frame else "Frame ativo: page (principal)"
                return {
                    "content": [{"type": "text", "text": f"Frames disponiveis ({len(frames)}):\n" + "\n".join(frame_lines) + f"\n\n{current}"}],
                }

            # Voltar ao frame principal
            if name.lower() in ("main", "page", "top", "principal"):
                _set_current_frame(None)
                snapshot = await _get_snapshot()
                return {
                    "content": [{"type": "text", "text": f"Voltou ao frame principal (page).\n\n{snapshot}"}],
                }

            # Buscar frame por nome
            frame = page.frame(name=name)

            # Fallback: buscar por URL fragment ou indice
            if not frame:
                for f in page.frames:
                    if name.lower() in (f.url or "").lower():
                        frame = f
                        break

            if not frame:
                # Tentar por indice numerico
                try:
                    idx = int(name)
                    frames = page.frames
                    if 0 <= idx < len(frames):
                        frame = frames[idx]
                except (ValueError, IndexError):
                    pass

            if not frame:
                available = ", ".join(f"'{f.name}'" for f in page.frames if f.name)
                return {
                    "content": [{"type": "text", "text": f"Frame '{name}' nao encontrado. Disponiveis: {available or '(nenhum nomeado)'}"}],
                    "is_error": True,
                }

            _set_current_frame(frame)

            # Capturar conteudo do frame selecionado
            try:
                frame_text = await frame.inner_text("body")
                if len(frame_text) > 30000:
                    frame_text = frame_text[:30000] + "\n... (truncado)"
                content_preview = f"\n\nConteudo do frame:\n{frame_text}"
            except Exception:
                content_preview = "\n\n(nao foi possivel ler conteudo do frame)"

            return {
                "content": [{"type": "text", "text": f"Trocou para frame '{frame.name}' (url: {frame.url}){content_preview}"}],
            }

        except Exception as e:
            error_msg = f"Erro ao trocar frame: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 10: browser_ssw_login (C3)
    # -----------------------------------------------------------------
    @tool(
        "browser_ssw_login",
        (
            "Login automatico no SSW usando credenciais do .env. "
            "Navega para SSW_URL, preenche dominio/CPF/login/senha e submete. "
            "Credenciais lidas de: SSW_URL, SSW_DOMINIO, SSW_CPF, SSW_LOGIN, SSW_SENHA. "
            "Se ja estiver logado (sessao persistida), detecta e pula login. "
            "Use ANTES de browser_ssw_navigate_option ou qualquer interacao SSW."
        ),
        {},
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def browser_ssw_login(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Login automatico no SSW.

        Credenciais lidas das variaveis de ambiente:
            SSW_URL, SSW_DOMINIO, SSW_CPF, SSW_LOGIN, SSW_SENHA

        Returns:
            MCP tool response com snapshot apos login.
        """
        ssw_url = os.getenv("SSW_URL", "").strip()
        dominio = os.getenv("SSW_DOMINIO", "").strip()
        cpf = os.getenv("SSW_CPF", "").strip()
        login = os.getenv("SSW_LOGIN", "").strip()
        senha = os.getenv("SSW_SENHA", "").strip()

        if not all([ssw_url, dominio, login, senha]):
            missing = []
            if not ssw_url: missing.append("SSW_URL")
            if not dominio: missing.append("SSW_DOMINIO")
            if not login: missing.append("SSW_LOGIN")
            if not senha: missing.append("SSW_SENHA")
            return {
                "content": [{"type": "text", "text": f"Erro: variaveis de ambiente faltando: {', '.join(missing)}. Configure no .env."}],
                "is_error": True,
            }

        try:
            page = await _ensure_browser()
            _set_current_frame(None)  # Reset frame ao fazer login

            # Navegar para SSW
            response = await page.goto(ssw_url, wait_until="domcontentloaded")
            status = response.status if response else "?"

            # Aguardar carregamento completo
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            # Detectar se ja esta logado (presenca de 3+ frames = menu ativo)
            if len(page.frames) > 2:
                await _save_storage_state()
                snapshot = await _get_snapshot()
                return {
                    "content": [{"type": "text", "text": f"SSW ja logado (sessao ativa, {len(page.frames)} frames detectados).\n\n{snapshot}"}],
                }

            # SSW login page: campos f1 (dominio), f2 (CPF), f3 (usuario), f4 (senha)
            # HTML usa <input name="fN"> sem labels semanticos
            ssw_fields = [
                ("f1", dominio, "dominio"),
                ("f2", cpf, "cpf"),
                ("f3", login, "usuario"),
                ("f4", senha, "senha"),
            ]

            filled_fields = []
            for field_name, value, label in ssw_fields:
                try:
                    await page.fill(f'input[name="{field_name}"]', value)
                    filled_fields.append(label)
                except Exception:
                    logger.warning(f"[BROWSER] SSW login: campo {field_name} ({label}) nao encontrado")

            # Submit: <a> com onclick="ajaxEnvia('L', 0)" (texto "►")
            submitted = False
            try:
                locator = page.get_by_text("►", exact=True)
                if await locator.count() > 0:
                    await locator.first.click()
                    submitted = True
            except Exception:
                pass

            if not submitted:
                try:
                    await page.evaluate("ajaxEnvia('L', 0)")
                    submitted = True
                except Exception:
                    await page.keyboard.press("Enter")

            # Aguardar redirect pos-login (SSW usa AJAX → redirect para menu01)
            # Polling: verificar se frames > 2 (menu carregado)
            login_ok = False
            for _ in range(15):
                await asyncio.sleep(2)
                if len(page.frames) > 2:
                    login_ok = True
                    break

            await _save_storage_state()
            snapshot = await _get_snapshot()

            if login_ok:
                return {
                    "content": [{"type": "text", "text": (
                        f"Login SSW OK (status HTTP: {status})\n"
                        f"  Dominio: {dominio} | Usuario: {login}\n"
                        f"  Campos: {', '.join(filled_fields)}\n"
                        f"  Frames: {len(page.frames)}\n\n{snapshot}"
                    )}],
                }
            else:
                body_text = ""
                try:
                    body_text = await page.inner_text("body")
                    body_text = body_text[:300]
                except Exception:
                    pass
                return {
                    "content": [{"type": "text", "text": (
                        f"Login SSW falhou (permaneceu em {page.url})\n"
                        f"  Campos preenchidos: {', '.join(filled_fields) or 'nenhum'}\n"
                        f"  Frames: {len(page.frames)} (esperado > 2)\n"
                        f"  Pagina: {body_text}\n\n"
                        f"Verifique as credenciais SSW_DOMINIO/SSW_CPF/SSW_LOGIN/SSW_SENHA no .env."
                    )}],
                    "is_error": True,
                }

        except Exception as e:
            error_msg = f"Erro no login SSW: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # -----------------------------------------------------------------
    # Tool 11: browser_ssw_navigate_option (C4)
    # -----------------------------------------------------------------
    @tool(
        "browser_ssw_navigate_option",
        (
            "Navega diretamente para uma opcao SSW por numero. "
            "REQUER login previo (use browser_ssw_login antes). "
            "Usa campo Opcao (f3) do menu + doOption() para navegar via AJAX. "
            "Conteudo carrega no frame principal via AJAX (URL nao muda). "
            "Exemplos: option_number=4 (emissao CTRCs), option_number=436 (faturamento)."
        ),
        {
            "option_number": int,
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def browser_ssw_navigate_option(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navega para opcao SSW por numero.

        SSW menu: campo f3 (id=3, maxlength=3) = "Opcao:", onchange=doOption().
        doOption() chama findme(f3.value) que faz:
        ajaxEnvia("", 0, "menu01?act=TRO&f2=UNIT&f3=SEQ")

        Conteudo carrega via AJAX no frame principal (URL permanece menu01).

        Args:
            args: {"option_number": int} — numero da opcao SSW (ex: 4, 7, 436)

        Returns:
            MCP tool response com snapshot da tela da opcao.
        """
        option_number = args.get("option_number", 0)
        if not option_number or not isinstance(option_number, (int, float)):
            return {
                "content": [{"type": "text", "text": "Erro: 'option_number' obrigatorio (numero inteiro da opcao SSW)."}],
                "is_error": True,
            }

        option_number = int(option_number)
        option_str = str(option_number).zfill(3)

        try:
            page = await _ensure_browser()

            # Verificar se estamos logados (3+ frames = menu ativo)
            if len(page.frames) < 3:
                return {
                    "content": [{"type": "text", "text": "Erro: SSW nao parece estar logado (< 3 frames). Use browser_ssw_login primeiro."}],
                    "is_error": True,
                }

            main_frame = page.main_frame
            method_used = ""

            # Estrategia 1 (validada): Setar campo f3 (Opcao) no DOM + doOption()
            # doOption() le $(3).value e chama findme() → ajaxEnvia com act=TRO
            try:
                await main_frame.evaluate(
                    f"document.getElementById('3').value = '{option_str}'; doOption();"
                )
                method_used = f"f3='{option_str}' + doOption()"
            except Exception as e1:
                # Estrategia 2: findme() direto (precisa setar f3 antes)
                try:
                    await main_frame.evaluate(
                        f"document.getElementById('3').value = '{option_str}'; findme('{option_str}');"
                    )
                    method_used = f"f3='{option_str}' + findme()"
                except Exception as e2:
                    # Estrategia 3: ajaxEnvia direto com parametros de navegacao
                    try:
                        unidade = await main_frame.evaluate("document.getElementById('2').value || 'MTZ'")
                        await main_frame.evaluate(
                            f"ajaxEnvia('', 0, 'menu01?act=TRO&f2={unidade}&f3={option_str}');"
                        )
                        method_used = f"ajaxEnvia(act=TRO, f3={option_str})"
                    except Exception as e3:
                        snapshot = await _get_snapshot()
                        return {
                            "content": [{"type": "text", "text": (
                                f"Nao conseguiu navegar para opcao {option_str}.\n"
                                f"Tentativa 1 (doOption): {str(e1)[:100]}\n"
                                f"Tentativa 2 (findme): {str(e2)[:100]}\n"
                                f"Tentativa 3 (ajaxEnvia): {str(e3)[:100]}\n\n"
                                f"Sugestao: use browser_evaluate_js para depurar.\n\n{snapshot}"
                            )}],
                            "is_error": True,
                        }

            # Aguardar AJAX (conteudo carrega via AJAX, URL nao muda)
            await asyncio.sleep(3)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            await _save_storage_state()
            snapshot = await _get_snapshot()

            return {
                "content": [{"type": "text", "text": (
                    f"Navegou para opcao {option_str} via {method_used}\n"
                    f"Frames: {len(page.frames)}\n\n{snapshot}"
                )}],
            }

        except Exception as e:
            error_msg = f"Erro ao navegar para opcao {option_str}: {str(e)[:300]}"
            logger.error(f"[BROWSER] {error_msg}", exc_info=True)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "is_error": True,
            }

    # =====================================================================
    # MCP SERVER REGISTRATION
    # =====================================================================
    browser_server = create_sdk_mcp_server(
        name="browser",
        version="2.1.0",
        tools=[
            browser_navigate,
            browser_snapshot,
            browser_screenshot,
            browser_click,
            browser_type,
            browser_select_option,
            browser_read_content,
            browser_close,
            browser_evaluate_js,
            browser_switch_frame,
            browser_ssw_login,
            browser_ssw_navigate_option,
        ],
    )

    logger.info("[BROWSER] Custom Tool MCP 'browser' registrado com sucesso (12 tools)")

except ImportError as e:
    browser_server = None
    logger.debug(f"[BROWSER] claude_agent_sdk nao disponivel: {e}")
