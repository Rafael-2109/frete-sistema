#!/usr/bin/env python3
"""
cancelar_cte_004.py — Cancela CT-e no SSW (opcao 004).

Fluxo:
  1. Login SSW
  2. Abre opcao 004 (popup)
  3. Override createNewDoc para manter DOM in-place
  4. Navega para funcao de cancelamento via link "Cancelar" no rodape
  5. Informa numero do CTRC
  6. Sistema carrega dados do CT-e (PES)
  7. --dry-run: captura snapshot + screenshot -> retorna preview
  8. Confirma cancelamento
  9. Se CT-e autorizado: sistema envia cancelamento ao SEFAZ
  10. Verifica resposta (cancelado/rejeitado)
  11. Output JSON via gerar_saida()

IMPORTANTE:
  - Operacao FISCAL IRREVERSIVEL — cancelamento no SEFAZ nao pode ser desfeito
  - Prazo SEFAZ: 7 dias da data de autorizacao
  - Se CT-e ja manifestado: cancelar Manifesto ANTES (opcao 024)
  - Se CT-e ja embarcado: NAO CANCELAR (risco de sinistro sem cobertura)
  - Efeitos colaterais: fatura, boleto, averbacao cancelados automaticamente

Fonte: POP-C06 (pops/POP-C06-cancelar-cte.md)

Uso:
    python cancelar_cte_004.py \\
      --ctrc 66 \\
      --serie "CAR 68-0" \\
      --motivo "NF vinculada incorretamente, reemissao necessaria" \\
      [--dry-run] [--discover]

Retorno: JSON {"sucesso": bool, "ctrc": "...", "status": "...", ...}

Mapeamento de campos (a confirmar via --discover na primeira execucao):
  Cancelar link  -> <a> no rodape com texto "Cancelar" ou onclick com 'CAN'
  Campo CTRC     -> campo para informar numero do CTRC a cancelar
  Motivo         -> campo texto livre para justificativa
"""
import argparse
import asyncio
import html as html_module
import json
import os
import re
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (
    verificar_credenciais,
    login_ssw,
    abrir_opcao_popup,
    interceptar_ajax_response,
    injetar_html_no_dom,
    preencher_campo_js,
    preencher_campo_no_html,
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
)


# ──────────────────────────────────────────────
# Override createNewDoc (padrao SSW scripts)
# ──────────────────────────────────────────────
CREATE_NEW_DOC_OVERRIDE = """() => {
    createNewDoc = function(pathname) {
        document.open("text/html", "replace");
        document.write(valSep.toString());
        document.close();
        if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
    };
}"""


def validar_campos(args):
    """Valida parametros de entrada. Retorna lista de erros."""
    erros = []

    if not args.ctrc:
        erros.append("ctrc: obrigatorio (numero do CT-e a cancelar)")

    if not args.serie:
        erros.append("serie: obrigatorio (serie do CT-e, ex: CAR 68-0)")

    if not args.motivo or len(args.motivo.strip()) < 5:
        erros.append("motivo: obrigatorio (minimo 5 caracteres, descricao do motivo)")

    if args.motivo and len(args.motivo) > 200:
        erros.append(f"motivo: maximo 200 caracteres (recebido: {len(args.motivo)})")

    return erros


async def descobrir_campos(_args=None):
    """
    Modo --discover: abre a opcao 004 e mapeia a interface de cancelamento.
    Lista links, campos e botoes disponiveis para cancelamento.
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        try:
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            popup = await abrir_opcao_popup(context, page.frames[0], 4, timeout_s=30)
            await asyncio.sleep(2)

            # Override createNewDoc
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            # Capturar tela inicial da 004
            screenshot_inicial = await capturar_screenshot(popup, "004_tela_inicial")
            campos_iniciais = await capturar_campos(popup)

            # Listar todos os links com onclick
            links = await popup.evaluate("""() => {
                const r = [];
                document.querySelectorAll('a[onclick], a[href]').forEach(el => {
                    r.push({
                        text: el.textContent.trim().substring(0, 100),
                        onclick: (el.getAttribute('onclick') || '').substring(0, 300),
                        href: (el.getAttribute('href') || '').substring(0, 200),
                        id: el.id || '',
                        visible: el.offsetParent !== null
                    });
                });
                return r;
            }""")

            # Filtrar links relevantes para cancelamento
            links_cancel = [
                l for l in links
                if any(k in (l.get("text", "") + l.get("onclick", "")).lower()
                       for k in ["cancel", "exclu", "canc"])
            ]

            # Tentar encontrar e clicar no link "Cancelar"
            cancelar_encontrado = False
            html_cancelar = None

            # Estrategia 1: Procurar link com texto "Cancelar"
            for link in links:
                text = link.get("text", "").strip().lower()
                onclick = link.get("onclick", "")
                if "cancelar" in text or "cancel" in text:
                    cancelar_encontrado = True
                    # Tentar interceptar a navegacao
                    try:
                        html_cancelar = await interceptar_ajax_response(
                            popup, popup, onclick, timeout_s=15
                        )
                    except Exception as e:
                        pass
                    break

            # Estrategia 2: Se nao encontrou, procurar via ajaxEnvia com CAN
            if not cancelar_encontrado:
                for link in links:
                    onclick = link.get("onclick", "")
                    if "'CAN'" in onclick or '"CAN"' in onclick:
                        cancelar_encontrado = True
                        try:
                            html_cancelar = await interceptar_ajax_response(
                                popup, popup, onclick, timeout_s=15
                            )
                        except Exception:
                            pass
                        break

            screenshot_cancelar = None
            campos_cancelar = None

            if html_cancelar:
                await injetar_html_no_dom(popup, html_cancelar)
                await asyncio.sleep(1)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                screenshot_cancelar = await capturar_screenshot(popup, "004_tela_cancelar")
                campos_cancelar = await capturar_campos(popup)

                # Listar links da tela de cancelamento
                links_cancelar_tela = await popup.evaluate("""() => {
                    const r = [];
                    document.querySelectorAll('a[onclick], a[href]').forEach(el => {
                        r.push({
                            text: el.textContent.trim().substring(0, 100),
                            onclick: (el.getAttribute('onclick') || '').substring(0, 300),
                            id: el.id || '',
                            visible: el.offsetParent !== null
                        });
                    });
                    return r;
                }""")
            else:
                links_cancelar_tela = []

            return gerar_saida(
                True,
                modo="discover",
                tela_inicial={
                    "campos": campos_iniciais,
                    "links_todos": links,
                    "links_cancelamento": links_cancel,
                    "screenshot": screenshot_inicial,
                },
                tela_cancelar={
                    "encontrada": cancelar_encontrado,
                    "html_carregado": html_cancelar is not None,
                    "campos": campos_cancelar,
                    "links": links_cancelar_tela,
                    "screenshot": screenshot_cancelar,
                },
            )

        finally:
            await browser.close()


async def cancelar_cte(args):
    """
    Fluxo principal de cancelamento de CT-e no SSW via opcao 004.

    1. Login
    2. Abrir opcao 004
    3. Navegar para "Cancelar"
    4. Informar CTRC
    5. PES (pesquisar CT-e)
    6. Verificar dados do CT-e
    7. [dry-run] Preview
    8. Confirmar cancelamento
    9. Capturar resposta SEFAZ
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()

    ctrc = str(args.ctrc).strip()
    serie = args.serie.strip()
    motivo = args.motivo.strip()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        try:
            # ── 1. Login ──
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            # ── 2. Abrir opcao 004 (popup) ──
            popup = await abrir_opcao_popup(context, page.frames[0], 4, timeout_s=30)
            await asyncio.sleep(2)

            # Override createNewDoc
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            # ── 3. Navegar para funcao "Cancelar" ──
            # Procurar link "Cancelar" no rodape da 004
            cancel_link = await popup.evaluate("""() => {
                const links = document.querySelectorAll('a[onclick], a[href]');
                for (const el of links) {
                    const text = el.textContent.trim().toLowerCase();
                    const onclick = (el.getAttribute('onclick') || '').toLowerCase();
                    if (text.includes('cancelar') || onclick.includes("'can'") || onclick.includes('"can"')) {
                        return {
                            found: true,
                            text: el.textContent.trim(),
                            onclick: el.getAttribute('onclick') || '',
                        };
                    }
                }
                return {found: false};
            }""")

            if not cancel_link.get("found"):
                screenshot = await capturar_screenshot(popup, "004_sem_link_cancelar")
                campos = await capturar_campos(popup)
                links_all = await popup.evaluate("""() => {
                    const r = [];
                    document.querySelectorAll('a').forEach(el => {
                        r.push({text: el.textContent.trim().substring(0, 80),
                                onclick: (el.getAttribute('onclick') || '').substring(0, 200)});
                    });
                    return r;
                }""")
                return gerar_saida(
                    False,
                    erro="Link 'Cancelar' nao encontrado na opcao 004",
                    links_disponiveis=links_all,
                    campos=campos,
                    screenshot=screenshot,
                    dica="Execute com --discover para mapear a interface",
                )

            # Clicar no link "Cancelar" via onclick
            onclick_js = cancel_link["onclick"]
            html_cancelar = await interceptar_ajax_response(
                popup, popup, onclick_js, timeout_s=15
            )

            if html_cancelar:
                await injetar_html_no_dom(popup, html_cancelar)
                await asyncio.sleep(1)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
            else:
                # Tentar clicar diretamente se interceptacao falhou
                try:
                    await popup.evaluate(f"""() => {{
                        const links = document.querySelectorAll('a');
                        for (const el of links) {{
                            if (el.textContent.trim().toLowerCase().includes('cancelar')) {{
                                el.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}""")
                    await asyncio.sleep(3)
                except Exception:
                    pass

            screenshot_cancel_tela = await capturar_screenshot(popup, "004_tela_cancelar")

            # ── 4. Preencher numero do CTRC ──
            # Tentar preencher campo CTRC (varios nomes possiveis)
            ctrc_preenchido = False
            campo_ctrc_usado = None

            # Estrategia: tentar campo '2' (padrao SSW para campo de busca)
            # e tambem tentar nomes comuns
            for campo_name in ["2", "ctrc", "numero", "num_ctrc", "nrctrc", "nr_ctrc"]:
                result = await preencher_campo_js(popup, campo_name, ctrc)
                if result.get("found") and not result.get("readonly"):
                    ctrc_preenchido = True
                    campo_ctrc_usado = campo_name
                    break

            if not ctrc_preenchido:
                # Tentar localizar qualquer input numerico visivel
                campo_detect = await popup.evaluate("""() => {
                    const inputs = document.querySelectorAll('input:not([type="hidden"])');
                    for (const el of inputs) {
                        if (el.offsetParent !== null && !el.readOnly &&
                            (el.maxLength <= 20 || !el.maxLength)) {
                            return {found: true, name: el.name, id: el.id, maxLength: el.maxLength};
                        }
                    }
                    return {found: false};
                }""")

                if campo_detect.get("found"):
                    campo_id = campo_detect.get("name") or campo_detect.get("id")
                    by = "name" if campo_detect.get("name") else "id"
                    await preencher_campo_no_html(popup, campo_id, ctrc, by=by)
                    ctrc_preenchido = True
                    campo_ctrc_usado = campo_id

            if not ctrc_preenchido:
                campos_form = await capturar_campos(popup)
                return gerar_saida(
                    False,
                    erro="Nao foi possivel preencher o campo do CTRC na tela de cancelamento",
                    campos_form=campos_form,
                    screenshot=screenshot_cancel_tela,
                    dica="Execute com --discover para mapear campos",
                )

            # ── 5. PES — pesquisar CT-e ──
            html_pes = await interceptar_ajax_response(
                popup, popup, "ajaxEnvia('PES', 0)", timeout_s=15
            )

            if html_pes:
                await injetar_html_no_dom(popup, html_pes)
                await asyncio.sleep(1)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            await asyncio.sleep(2)

            # ── 6. Verificar dados do CT-e carregado ──
            screenshot_dados = await capturar_screenshot(popup, f"004_dados_cte_{ctrc}")
            campos_cte = await capturar_campos(popup)

            # Extrair informacoes do CT-e
            body_text = await popup.evaluate(
                "() => document.body ? document.body.innerText.substring(0, 5000) : ''"
            )

            # Verificar se CT-e foi encontrado
            if any(msg in body_text.lower() for msg in [
                "nao encontrad", "não encontrad", "nao existe", "não existe",
                "invalido", "inválido"
            ]):
                return gerar_saida(
                    False,
                    erro=f"CT-e {ctrc} nao encontrado ou invalido",
                    ctrc=ctrc,
                    serie=serie,
                    body_text=body_text[:1000],
                    screenshot=screenshot_dados,
                )

            # Capturar dados do CT-e para preview
            dados_cte = {
                "ctrc": ctrc,
                "serie": serie,
                "motivo": motivo,
            }

            # Tentar extrair dados do formulario
            for campo_nome in ["nome_rem", "nome_dest", "vlr_merc", "peso",
                               "qtd_vol", "vlr_frete", "status", "situacao",
                               "dt_emissao", "chave_cte"]:
                val = await popup.evaluate(f"""() => {{
                    let el = document.querySelector('input[name="{campo_nome}"]');
                    if (!el) el = document.getElementById('{campo_nome}');
                    return el ? (el.value || el.textContent || '').trim() : '';
                }}""")
                if val:
                    dados_cte[campo_nome] = val

            # ── 7. Dry-run: apenas preview ──
            if args.dry_run:
                return gerar_saida(
                    True,
                    modo="dry-run",
                    dados_cte=dados_cte,
                    campo_ctrc_usado=campo_ctrc_usado,
                    campos_formulario=campos_cte,
                    body_text=body_text[:2000],
                    screenshot=screenshot_dados,
                    mensagem=f"Preview do cancelamento CT-e {ctrc} serie {serie}. "
                             f"Nenhuma acao foi executada.",
                )

            # ── 8. Preencher motivo (se campo existir) ──
            for campo_motivo in ["motivo", "obs", "observacao", "justificativa",
                                 "mot_cancel", "motivo_cancel"]:
                result = await preencher_campo_js(popup, campo_motivo, motivo)
                if result.get("found") and not result.get("readonly"):
                    dados_cte["campo_motivo_usado"] = campo_motivo
                    break

            # ── 9. Confirmar cancelamento ──
            screenshot_pre = await capturar_screenshot(popup, f"004_pre_cancelar_{ctrc}")

            alert_msg = None
            confirm_msg = None
            cancel_response = None

            async def on_dialog(dialog):
                nonlocal alert_msg, confirm_msg
                msg = dialog.message
                if dialog.type == "confirm":
                    confirm_msg = msg
                    await dialog.accept()  # Confirmar "Sim"
                else:
                    alert_msg = msg
                    await dialog.accept()

            async def on_response(response):
                nonlocal cancel_response
                if "/bin/ssw" in response.url and response.status == 200:
                    try:
                        cancel_response = await response.text()
                    except Exception:
                        pass

            popup.on("dialog", on_dialog)
            popup.on("response", on_response)

            try:
                # Tentar submeter cancelamento
                # Estrategia 1: ajaxEnvia com acao de cancelamento
                # Acoes possiveis: 'CAN', 'EXC', 'DEL', 'GRA'
                acao_executada = None

                for acao in ["CAN", "EXC"]:
                    try:
                        await popup.evaluate(f"ajaxEnvia('{acao}', 0)")
                        acao_executada = acao
                        break
                    except Exception:
                        continue

                if not acao_executada:
                    # Estrategia 2: Procurar e clicar botao de confirmar cancelamento
                    btn_clicked = await popup.evaluate("""() => {
                        const links = document.querySelectorAll('a[onclick]');
                        for (const el of links) {
                            const text = el.textContent.trim().toLowerCase();
                            const onclick = (el.getAttribute('onclick') || '').toLowerCase();
                            if (text.includes('confirma') || text.includes('cancelar') ||
                                onclick.includes("'can'") || onclick.includes("'exc'")) {
                                el.click();
                                return {clicked: true, text: el.textContent.trim(),
                                        onclick: el.getAttribute('onclick')};
                            }
                        }
                        return {clicked: false};
                    }""")
                    if btn_clicked.get("clicked"):
                        acao_executada = f"link: {btn_clicked.get('text', '?')}"

                # Aguardar resposta (SEFAZ pode demorar)
                await asyncio.sleep(5)

                # Detectar se popup fechou (= sucesso em alguns casos SSW)
                page_closed = False
                try:
                    await popup.evaluate("1")
                except Exception:
                    page_closed = True

                if page_closed:
                    return gerar_saida(
                        True,
                        status="cancelado",
                        ctrc=ctrc,
                        serie=serie,
                        motivo=motivo,
                        acao_executada=acao_executada,
                        confirm_dialog=confirm_msg,
                        alert_dialog=alert_msg,
                        mensagem=f"CT-e {ctrc} serie {serie} — cancelamento submetido com sucesso "
                                 f"(popup fechou, indicando sucesso SSW).",
                    )

                # Popup continua aberto — verificar resposta
                screenshot_resultado = await capturar_screenshot(
                    popup, f"004_resultado_cancelar_{ctrc}"
                )

                body_resultado = await popup.evaluate(
                    "() => document.body ? document.body.innerText.substring(0, 5000) : ''"
                )

                # Verificar sucesso
                indicadores_sucesso = [
                    "cancelado com sucesso", "cancelamento autorizado",
                    "cancelado", "protocolo de cancelamento",
                    "operacao realizada", "cancelamento efetuado",
                ]
                sucesso = any(
                    ind in body_resultado.lower() for ind in indicadores_sucesso
                )

                # Verificar erro
                indicadores_erro = [
                    "prazo vencido", "prazo expirado", "fora do prazo",
                    "ja manifestado", "já manifestado",
                    "nao permitido", "não permitido",
                    "rejeitado", "rejeicao", "rejeição",
                    "erro", "falha",
                ]
                tem_erro = any(
                    ind in body_resultado.lower() for ind in indicadores_erro
                )

                # Extrair mensagem de erro do response AJAX
                erro_detalhe = None
                if cancel_response:
                    # Checar <foc> (mensagem inline SSW)
                    foc_match = re.search(
                        r'<foc[^>]*>(.*?)$', cancel_response, re.DOTALL
                    )
                    if foc_match:
                        erro_detalhe = html_module.unescape(foc_match.group(1).strip())
                    # Checar <!--GoBack-->
                    elif "GoBack" in cancel_response:
                        msg_match = re.search(
                            r'(.*?)<!--GoBack-->', cancel_response, re.DOTALL
                        )
                        if msg_match:
                            text = re.sub(r'<[^>]+>', ' ', msg_match.group(1)).strip()
                            text = re.sub(r'\s+', ' ', text)
                            erro_detalhe = text[:300]
                    # Checar <!--CloseMe--> (sucesso)
                    elif "CloseMe" in cancel_response:
                        sucesso = True

                if sucesso:
                    return gerar_saida(
                        True,
                        status="cancelado",
                        ctrc=ctrc,
                        serie=serie,
                        motivo=motivo,
                        acao_executada=acao_executada,
                        confirm_dialog=confirm_msg,
                        alert_dialog=alert_msg,
                        body_resultado=body_resultado[:1000],
                        screenshot=screenshot_resultado,
                        mensagem=f"CT-e {ctrc} serie {serie} cancelado com sucesso.",
                    )

                if tem_erro or erro_detalhe:
                    return gerar_saida(
                        False,
                        status="erro",
                        ctrc=ctrc,
                        serie=serie,
                        erro=erro_detalhe or "Erro detectado no cancelamento",
                        alert_dialog=alert_msg,
                        body_resultado=body_resultado[:1000],
                        screenshot=screenshot_resultado,
                    )

                # Resultado inconclusivo
                return gerar_saida(
                    False,
                    status="inconclusivo",
                    ctrc=ctrc,
                    serie=serie,
                    acao_executada=acao_executada,
                    confirm_dialog=confirm_msg,
                    alert_dialog=alert_msg,
                    body_resultado=body_resultado[:2000],
                    screenshot=screenshot_resultado,
                    mensagem="Resposta SSW inconclusiva. Verificar manualmente na opcao 101.",
                    dica="Execute com --discover para investigar a interface",
                )

            finally:
                try:
                    popup.remove_listener("dialog", on_dialog)
                    popup.remove_listener("response", on_response)
                except Exception:
                    pass

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Cancelar CT-e no SSW (opcao 004). OPERACAO FISCAL IRREVERSIVEL."
    )

    # Modo discover (exclusivo)
    parser.add_argument(
        "--discover", action="store_true",
        help="Modo exploratorio: abre tela de cancelamento e lista campos/links"
    )

    # Parametros do cancelamento
    parser.add_argument(
        "--ctrc", default=None,
        help="Numero do CT-e a cancelar (ex: 66)"
    )
    parser.add_argument(
        "--serie", default=None,
        help="Serie do CT-e (ex: 'CAR 68-0')"
    )
    parser.add_argument(
        "--motivo", default=None,
        help="Motivo do cancelamento (obrigatorio, min 5 chars, max 200)"
    )

    # Config
    parser.add_argument(
        "--defaults-file",
        default=os.path.join(SCRIPT_DIR, "..", "ssw_defaults.json"),
        help="Caminho para ssw_defaults.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview do cancelamento, sem executar. OBRIGATORIO na primeira execucao."
    )

    args = parser.parse_args()

    # Modo discover
    if args.discover:
        asyncio.run(descobrir_campos())
        return

    # Validar parametros obrigatorios
    if not args.ctrc or not args.serie or not args.motivo:
        faltando = []
        if not args.ctrc:
            faltando.append("--ctrc")
        if not args.serie:
            faltando.append("--serie")
        if not args.motivo:
            faltando.append("--motivo")
        print(json.dumps({
            "sucesso": False,
            "erro": f"Parametros obrigatorios faltando: {', '.join(faltando)}",
            "uso": 'python cancelar_cte_004.py --ctrc 66 --serie "CAR 68-0" '
                   '--motivo "NF vinculada incorretamente" --dry-run',
        }, ensure_ascii=False))
        sys.exit(1)

    # Validar campos
    erros = validar_campos(args)
    if erros:
        print(json.dumps({
            "sucesso": False,
            "erro": "Parametros invalidos",
            "erros_validacao": erros,
        }, ensure_ascii=False))
        sys.exit(1)

    asyncio.run(cancelar_cte(args))


if __name__ == "__main__":
    main()
