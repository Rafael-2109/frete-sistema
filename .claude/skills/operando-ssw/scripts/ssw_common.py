#!/usr/bin/env python3
"""
ssw_common.py — Funcoes reutilizaveis para scripts Playwright SSW.

Compartilhado entre cadastrar_unidade_401.py e cadastrar_cidades_402.py.
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
# Credenciais SSW (lidas do .env)
# ──────────────────────────────────────────────
SSW_URL = os.getenv("SSW_URL")
SSW_DOMINIO = os.getenv("SSW_DOMINIO")
SSW_CPF = os.getenv("SSW_CPF")
SSW_LOGIN = os.getenv("SSW_LOGIN")
SSW_SENHA = os.getenv("SSW_SENHA")

# Diretorio para screenshots/evidencias
EVIDENCE_DIR = "/tmp/ssw_operacoes"


def verificar_credenciais():
    """Verifica se todas as credenciais SSW estao configuradas."""
    missing = []
    for var in ["SSW_URL", "SSW_DOMINIO", "SSW_CPF", "SSW_LOGIN", "SSW_SENHA"]:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise EnvironmentError(
            f"Credenciais SSW faltando no .env: {', '.join(missing)}"
        )


def carregar_defaults(path=None):
    """Carrega ssw_defaults.json."""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "ssw_defaults.json")
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo de defaults nao encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def login_ssw(page, timeout_s=30):
    """
    Login no SSW. Reutiliza sessao ativa se detectada.

    Args:
        page: Playwright Page
        timeout_s: Timeout em segundos

    Returns:
        True se logado com sucesso
    """
    await page.goto(SSW_URL, wait_until="networkidle", timeout=timeout_s * 1000)
    await asyncio.sleep(2)

    # Sessao ativa = mais de 2 frames (frameset carregado)
    if len(page.frames) > 2:
        return True

    # Preencher campos de login
    for name, value in [
        ("f1", SSW_DOMINIO),
        ("f2", SSW_CPF),
        ("f3", SSW_LOGIN),
        ("f4", SSW_SENHA),
    ]:
        await page.fill(f'input[name="{name}"]', value)

    # Submeter login
    try:
        await page.get_by_text("►", exact=True).first.click()
    except Exception:
        await page.evaluate("ajaxEnvia('L', 0)")

    # Esperar frameset carregar
    for _ in range(timeout_s // 2):
        await asyncio.sleep(2)
        if len(page.frames) > 2:
            return True

    return False


async def abrir_opcao_popup(context, main_frame, opcao, timeout_s=15):
    """
    Navega para uma opcao SSW via popup.

    SSW abre opcoes em nova page via window.open (doOption).

    Args:
        context: Playwright BrowserContext
        main_frame: Frame principal (page.frames[0])
        opcao: Numero da opcao (int ou str)
        timeout_s: Timeout em segundos

    Returns:
        Playwright Page (popup)
    """
    option_str = str(opcao).zfill(3)

    async with context.expect_page(timeout=timeout_s * 1000) as new_page_info:
        await main_frame.evaluate(
            f"document.getElementById('3').value = '{option_str}'; doOption();"
        )

    popup = await new_page_info.value

    try:
        await popup.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        await asyncio.sleep(3)

    return popup


async def interceptar_ajax_response(popup, frame, action_code, timeout_s=15):
    """
    Executa uma acao ajaxEnvia e intercepta a response HTML.

    SSW substitui o conteudo inteiro da pagina via AJAX. O Playwright
    perde a referencia ao DOM apos substituicao. Por isso interceptamos
    o response body diretamente.

    Args:
        popup: Playwright Page do popup
        frame: Frame onde executar a acao
        action_code: JS a executar (ex: "ajaxEnvia('PES', 1)")
        timeout_s: Timeout em segundos

    Returns:
        str: HTML completo da response, ou None se falhou
    """
    response_body = None

    async def on_response(response):
        nonlocal response_body
        url = response.url
        # Capturar apenas responses da mesma opcao SSW
        if "/bin/ssw" in url and response.status == 200:
            try:
                body = await response.text()
                if len(body) > 500:  # Ignorar responses pequenos (erros, redirects)
                    response_body = body
            except Exception:
                pass

    popup.on("response", on_response)

    try:
        await frame.evaluate(action_code)
        # Esperar a response chegar
        for _ in range(timeout_s * 2):
            if response_body:
                break
            await asyncio.sleep(0.5)
    finally:
        popup.remove_listener("response", on_response)

    return response_body


async def injetar_html_no_dom(popup, html):
    """
    Injeta HTML interceptado no DOM do popup via document.write().

    SSW's ajaxEnvia() faz AJAX POST e recebe HTML completo como response,
    mas o mecanismo nativo de substituicao do DOM nao funciona em Playwright
    headless. Esta funcao faz a injecao manual, preservando:
    - Origin (https://sistema.ssw.inf.br) — necessario para submissoes
    - Cookies e sessao SSW
    - Funcoes JS do SSW (ajaxEnvia, etc.)
    - Hidden fields do formulario

    Args:
        popup: Playwright Page do popup
        html: HTML completo interceptado da response AJAX
    """
    # Escapar caracteres especiais para template literal JS
    escaped = html.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

    await popup.evaluate(f'''() => {{
        document.open();
        document.write(`{escaped}`);
        document.close();
    }}''')

    # Aguardar DOM estabilizar apos injecao
    await asyncio.sleep(1)


async def preencher_campo_no_html(popup, field_name, value, by="name"):
    """
    Preenche um campo em um formulario SSW que foi carregado via AJAX.

    Como o SSW substitui o HTML inteiro, precisamos re-encontrar o campo
    no DOM atualizado. Usa evaluate para setar valor diretamente.

    Args:
        popup: Playwright Page
        field_name: nome ou id do campo
        value: valor a preencher
        by: "name" ou "id"
    """
    if by == "name":
        selector = f'input[name="{field_name}"], select[name="{field_name}"], textarea[name="{field_name}"]'
    else:
        selector = f'#{field_name}'

    # Usar evaluate para maior confiabilidade com AJAX-replaced DOM
    success = await popup.evaluate(f"""() => {{
        const el = document.querySelector('{selector}');
        if (!el) return false;
        el.value = '{value}';
        // Disparar eventos para que SSW JS reconheca a mudanca
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        return true;
    }}""")

    if not success:
        raise ValueError(f"Campo nao encontrado: {field_name} (by={by})")


async def preencher_campo_inline(frame, field_id, value):
    """
    Preenche um campo inline (como na 402) pelo ID numerico.

    Args:
        frame: Frame onde o campo esta
        field_id: ID numerico do campo
        value: Valor a preencher
    """
    success = await frame.evaluate(f"""() => {{
        const el = document.getElementById('{field_id}');
        if (!el) return false;
        el.value = '{value}';
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        return true;
    }}""")

    if not success:
        raise ValueError(f"Campo inline #{field_id} nao encontrado")


async def capturar_campos(target):
    """
    Captura todos os campos visiveis de um target (page ou frame).

    Returns:
        dict com inputs, selects, checkboxes, radios, bodySnippet
    """
    return await target.evaluate("""() => {
        const r = {inputs: [], selects: [], checkboxes: [], bodySnippet: ''};
        r.bodySnippet = (document.body ? document.body.innerText : '').substring(0, 5000);

        function findLabel(el) {
            let lbl = '';
            if (el.id) { const l = document.querySelector('label[for="' + el.id + '"]'); if (l) lbl = l.textContent.trim(); }
            if (!lbl) { let prev = el.previousSibling; while (prev && prev.nodeType !== 1 && prev.nodeType !== 3) prev = prev.previousSibling; if (prev) { lbl = prev.nodeType === 3 ? prev.textContent.trim() : (prev.textContent || '').trim(); } }
            if (!lbl && el.closest('td')) { const prevTd = el.closest('td').previousElementSibling; if (prevTd) lbl = prevTd.textContent.trim(); }
            return lbl.substring(0, 200);
        }

        document.querySelectorAll('input:not([type="hidden"])').forEach(el => {
            if (el.offsetParent !== null) {
                r.inputs.push({name: el.name, id: el.id, value: (el.value || '').substring(0, 200), maxLength: el.maxLength > 0 && el.maxLength < 10000 ? el.maxLength : null, label: findLabel(el), readOnly: el.readOnly});
            }
        });

        document.querySelectorAll('select').forEach(el => {
            if (el.offsetParent !== null) {
                const opts = [];
                el.querySelectorAll('option').forEach(o => opts.push({value: o.value, text: o.textContent.trim()}));
                r.selects.push({name: el.name, id: el.id, label: findLabel(el), selectedValue: el.value, options: opts.slice(0, 30)});
            }
        });

        return r;
    }""")


async def capturar_screenshot(page_or_frame, nome, diretorio=None):
    """
    Captura screenshot como evidencia.

    Args:
        page_or_frame: Playwright Page
        nome: Nome base do arquivo (sem extensao)
        diretorio: Diretorio de destino (default: EVIDENCE_DIR)

    Returns:
        str: Caminho do arquivo salvo
    """
    diretorio = diretorio or EVIDENCE_DIR
    os.makedirs(diretorio, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(diretorio, f"{nome}_{timestamp}.png")
    await page_or_frame.screenshot(path=path, full_page=True)
    return path


def gerar_saida(sucesso, **kwargs):
    """
    Gera saida JSON padrao.

    Args:
        sucesso: bool
        **kwargs: campos adicionais

    Returns:
        dict (tambem imprime como JSON)
    """
    resultado = {"sucesso": sucesso, **kwargs}
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return resultado


async def verificar_mensagem_ssw(popup, timeout_s=5):
    """
    Verifica se SSW mostrou mensagem de erro ou sucesso apos uma operacao.

    SSW exibe mensagens via:
    - errorpanel/errormsg (div com visibility)
    - alert() nativo
    - Texto na pagina

    Returns:
        dict com {tipo: "erro"|"sucesso"|None, mensagem: str}
    """
    # Tentar capturar alert dialog
    # Nota: alerts precisam ser tratados ANTES da acao, nao depois
    # Aqui verificamos elementos de erro no DOM

    resultado = await popup.evaluate("""() => {
        // 1. Verificar errorpanel/errormsg
        const errMsg = document.getElementById('errormsg');
        if (errMsg && errMsg.style.visibility !== 'hidden') {
            const text = errMsg.innerText.trim();
            if (text && text !== '\\u00a0') return {tipo: 'erro', mensagem: text};
        }

        // 2. Verificar se tem texto de erro no body
        const body = document.body ? document.body.innerText : '';
        if (body.includes('ERRO') || body.includes('erro:')) {
            const match = body.match(/(?:ERRO|erro)[:!]?\\s*([^\\n]{5,200})/);
            if (match) return {tipo: 'erro', mensagem: match[1].trim()};
        }

        // 3. Verificar mensagem de sucesso
        if (body.includes('cadastrado com sucesso') || body.includes('incluído com sucesso')
            || body.includes('atualizado com sucesso') || body.includes('gravado')) {
            return {tipo: 'sucesso', mensagem: 'Operacao realizada com sucesso'};
        }

        return {tipo: null, mensagem: ''};
    }""")

    return resultado
