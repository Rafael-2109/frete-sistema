#!/usr/bin/env python3
"""
emitir_cte_004.py — Emite CT-e no SSW (opcao 004) + envia SEFAZ (007) + consulta (101).

Fluxo completo:
  1. Login SSW
  2. Trocar filial para CAR (se necessario)
  3. Abrir opcao 004 (popup)
  4. Navegar para "Incluir" (novo CTE)
  5. Selecionar tipo CTE Normal
  6. Preencher: placa, chave NF-e, frete peso
  7. Gravar pre-CTRC (handle dialogs: confirmar emissao, email nao disponivel)
  8. [--enviar-sefaz] Enviar ao SEFAZ (opcao 007)
  9. [--consultar-101] Consultar resultado (opcao 101)
  10. [--baixar-dacte] Baixar DACTE PDF e XML

IMPORTANTE:
  - Filial DEVE ser CAR para emissao de CT-e (POP-C01)
  - Placa ARMAZEM = frete fracionado (cliente trouxe ao armazem)
  - Pre-CTRC so tem valor fiscal APOS autorizacao SEFAZ (opcao 007)
  - Chave NF-e de 44 digitos — sistema auto-preenche dados da NF

Fonte: POP-C01 (pops/POP-C01-emitir-cte-fracionado.md)

Uso:
    python emitir_cte_004.py \\
      --chave-nfe "33260309089839000112550000003571412198449​43" \\
      --placa ARMAZEM \\
      --frete-peso 600 \\
      [--filial CAR] \\
      [--enviar-sefaz] \\
      [--consultar-101] \\
      [--baixar-dacte] \\
      [--dry-run] [--discover]

Retorno: JSON {"sucesso": bool, "ctrc": "...", "status": "...", ...}
"""
import argparse
import asyncio
import html as html_module
import json
import os
import re
import sys
import traceback

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (
    verificar_credenciais,
    carregar_defaults,
    login_ssw,
    abrir_opcao_popup,
    interceptar_ajax_response,
    injetar_html_no_dom,
    preencher_campo_js,
    preencher_campo_no_html,
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
    verificar_mensagem_ssw,
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


EVIDENCE_DIR = "/tmp/ssw_operacoes/emitir_cte"


async def capturar_screenshot_local(page, nome):
    """Screenshot com diretorio especifico para emissao CTE."""
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    return await capturar_screenshot(page, nome, diretorio=EVIDENCE_DIR)


async def listar_links(popup):
    """Lista todos os links com onclick no DOM atual."""
    return await popup.evaluate("""() => {
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


async def listar_selects(popup):
    """Lista todos os selects com suas opcoes."""
    return await popup.evaluate("""() => {
        const r = [];
        document.querySelectorAll('select').forEach(el => {
            const opts = [];
            el.querySelectorAll('option').forEach(o => {
                opts.push({value: o.value, text: o.textContent.trim(), selected: o.selected});
            });
            r.push({
                name: el.name, id: el.id, visible: el.offsetParent !== null,
                selectedValue: el.value, options: opts.slice(0, 50)
            });
        });
        return r;
    }""")


async def trocar_filial(page, filial_alvo="CAR", timeout_s=30):
    """
    Troca a filial ativa no SSW.

    O SSW mostra a filial atual no frame principal. Para trocar:
    1. Localizar o seletor de filial no frame principal
    2. Selecionar a filial alvo
    3. Confirmar a troca

    Returns:
        dict com {trocou: bool, filial_atual: str, mensagem: str}
    """
    main_frame = page.frames[0]

    # Capturar filial atual do frame principal
    filial_info = await main_frame.evaluate("""() => {
        // Procurar elemento que mostra filial atual
        // Pode ser um select, span, ou campo de texto
        const body = document.body ? document.body.innerText : '';

        // Procurar select de filial
        const selects = document.querySelectorAll('select');
        for (const sel of selects) {
            for (const opt of sel.options) {
                if (opt.text.includes('CAR') || opt.text.includes('MTZ') ||
                    opt.value === 'CAR' || opt.value === 'MTZ') {
                    return {
                        tipo: 'select',
                        name: sel.name,
                        id: sel.id,
                        valorAtual: sel.value,
                        textoAtual: sel.options[sel.selectedIndex]?.text || '',
                        opcoes: Array.from(sel.options).map(o => ({
                            value: o.value, text: o.text.trim()
                        })).slice(0, 20)
                    };
                }
            }
        }

        // Procurar campo de texto com filial
        const inputs = document.querySelectorAll('input');
        for (const inp of inputs) {
            if (inp.value === 'CAR' || inp.value === 'MTZ' || inp.name === 'filial' ||
                inp.name === 'unidade' || inp.id === 'filial' || inp.id === 'unidade') {
                return {
                    tipo: 'input',
                    name: inp.name,
                    id: inp.id,
                    valorAtual: inp.value,
                    readOnly: inp.readOnly
                };
            }
        }

        // Procurar no texto da pagina
        const filMatch = body.match(/(?:Filial|Unidade|Fil)[:\\s]*([A-Z]{2,5})/i);
        return {
            tipo: 'texto',
            filialDetectada: filMatch ? filMatch[1] : null,
            bodySnippet: body.substring(0, 2000)
        };
    }""")

    if filial_info.get("tipo") == "select":
        # Encontrou select de filial
        sel_name = filial_info.get("name") or filial_info.get("id")
        if filial_info.get("valorAtual", "").upper() == filial_alvo.upper():
            return {"trocou": False, "filial_atual": filial_alvo,
                    "mensagem": f"Ja esta na filial {filial_alvo}"}

        # Tentar trocar via select
        for opt in filial_info.get("opcoes", []):
            if filial_alvo.upper() in opt.get("value", "").upper() or \
               filial_alvo.upper() in opt.get("text", "").upper():
                # Selecionar a opcao
                await main_frame.evaluate(f"""() => {{
                    const sel = document.querySelector('select[name="{sel_name}"]') ||
                                document.getElementById('{sel_name}');
                    if (sel) {{
                        sel.value = '{opt["value"]}';
                        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                    return false;
                }}""")
                await asyncio.sleep(3)
                return {"trocou": True, "filial_atual": filial_alvo,
                        "mensagem": f"Filial trocada para {filial_alvo}"}

    elif filial_info.get("tipo") == "input":
        if filial_info.get("valorAtual", "").upper() == filial_alvo.upper():
            return {"trocou": False, "filial_atual": filial_alvo,
                    "mensagem": f"Ja esta na filial {filial_alvo}"}

        if not filial_info.get("readOnly"):
            inp_name = filial_info.get("name") or filial_info.get("id")
            await main_frame.evaluate(f"""() => {{
                let el = document.querySelector('input[name="{inp_name}"]') ||
                         document.getElementById('{inp_name}');
                if (el) {{
                    el.value = '{filial_alvo}';
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            }}""")
            await asyncio.sleep(2)

            # Pode precisar de Enter ou Tab para confirmar
            await main_frame.evaluate(f"""() => {{
                let el = document.querySelector('input[name="{inp_name}"]') ||
                         document.getElementById('{inp_name}');
                if (el) {{
                    el.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Tab', bubbles: true }}));
                }}
            }}""")
            await asyncio.sleep(3)
            return {"trocou": True, "filial_atual": filial_alvo,
                    "mensagem": f"Filial trocada para {filial_alvo} via input"}

    # Fallback: tentar trocar via campo de opcao do SSW (campo '2' = filial em alguns layouts)
    try:
        await main_frame.evaluate(f"""() => {{
            // Tentar campo '2' que em alguns SSW e o seletor de filial
            const el = document.getElementById('2');
            if (el) {{
                el.value = '{filial_alvo}';
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }}""")
        await asyncio.sleep(2)
    except Exception:
        pass

    return {
        "trocou": False,
        "filial_atual": "desconhecida",
        "filial_info": filial_info,
        "mensagem": "Nao foi possivel identificar/trocar filial automaticamente"
    }


async def descobrir_campos(args):
    """
    Modo --discover: abre opcao 004, navega para emissao e mapeia todos os campos.
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        try:
            # 1. Login
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            # 1b. Capturar frame principal para entender filial
            main_frame = page.frames[0]
            screenshot_main = await capturar_screenshot_local(page, "004_main_frame")

            # Capturar info do frame principal (filial, campos, etc)
            main_info = await main_frame.evaluate("""() => {
                const r = {inputs: [], selects: [], bodySnippet: ''};
                r.bodySnippet = (document.body ? document.body.innerText : '').substring(0, 3000);
                document.querySelectorAll('input').forEach(el => {
                    r.inputs.push({name: el.name, id: el.id, value: (el.value||'').substring(0,100),
                                   type: el.type, visible: el.offsetParent !== null});
                });
                document.querySelectorAll('select').forEach(el => {
                    const opts = [];
                    el.querySelectorAll('option').forEach(o => opts.push({value: o.value, text: o.text.trim()}));
                    r.selects.push({name: el.name, id: el.id, selectedValue: el.value,
                                    options: opts.slice(0, 20)});
                });
                return r;
            }""")

            # 1c. Tentar trocar filial
            filial_result = await trocar_filial(page, args.filial or "CAR")

            # 2. Abrir opcao 004
            popup = await abrir_opcao_popup(context, main_frame, 4, timeout_s=30)
            await asyncio.sleep(2)
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            screenshot_004_inicial = await capturar_screenshot_local(popup, "004_tela_inicial")
            campos_004_inicial = await capturar_campos(popup)
            links_004_inicial = await listar_links(popup)
            selects_004_inicial = await listar_selects(popup)

            # 3. Clicar em "N Normal" (CTE Normal) — ajaxEnvia('NORMAL', 1)
            # A tela inicial da 004 e um MENU de tipos de documento.
            # Para emissao normal: ajaxEnvia('NORMAL', 1)
            incluir_found = False
            html_incluir = None

            try:
                html_incluir = await interceptar_ajax_response(
                    popup, popup, "ajaxEnvia('NORMAL', 1)", timeout_s=15
                )
                if html_incluir and len(html_incluir) > 1000:
                    incluir_found = True
            except Exception:
                pass

            screenshot_form = None
            campos_form = None
            selects_form = None
            links_form = None

            if html_incluir:
                await injetar_html_no_dom(popup, html_incluir)
                await asyncio.sleep(1)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

                screenshot_form = await capturar_screenshot_local(popup, "004_formulario_emissao")
                campos_form = await capturar_campos(popup)
                selects_form = await listar_selects(popup)
                links_form = await listar_links(popup)

                # Capturar hidden fields tambem (podem ter info importante)
                hidden_fields = await popup.evaluate("""() => {
                    const r = [];
                    document.querySelectorAll('input[type="hidden"]').forEach(el => {
                        r.push({name: el.name, id: el.id, value: (el.value||'').substring(0, 200)});
                    });
                    return r;
                }""")
            else:
                # Tentar capturar o que tem na tela atual (pode ter mudado sem AJAX)
                await asyncio.sleep(2)
                screenshot_form = await capturar_screenshot_local(popup, "004_apos_tentativas")
                campos_form = await capturar_campos(popup)
                selects_form = await listar_selects(popup)
                links_form = await listar_links(popup)
                hidden_fields = []

            return gerar_saida(
                True,
                modo="discover",
                filial=filial_result,
                main_frame_info=main_info,
                tela_inicial={
                    "campos": campos_004_inicial,
                    "links": links_004_inicial,
                    "selects": selects_004_inicial,
                    "screenshot": screenshot_004_inicial,
                },
                formulario_emissao={
                    "encontrado": incluir_found,
                    "html_carregado": html_incluir is not None,
                    "campos": campos_form,
                    "selects": selects_form,
                    "links": links_form,
                    "hidden_fields": hidden_fields if html_incluir else [],
                    "screenshot": screenshot_form,
                },
                screenshot_main=screenshot_main,
            )

        finally:
            await browser.close()


async def emitir_cte(args):
    """
    Fluxo de emissao de CT-e usando interacao NATIVA do Playwright (fill/click/press).

    O SSW depende dos eventos reais (blur, change, keydown) para disparar
    validacoes, lookups e preenchimentos automaticos. Por isso usamos
    popup.fill() / popup.click() / popup.press() em vez de evaluate().

    Campos (discover 2026-03-26):
      f13 (id=13)             -> Placa Coleta
      chaveAcesso             -> Chave NF-e (45 chars)
      id_frt_inf_frete_peso   -> Frete peso informado
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()

    chave_nfe = args.chave_nfe.replace(" ", "").strip()
    placa = args.placa.upper().strip()
    # Frete peso: formato BR (virgula decimal)
    frete_peso = str(args.frete_peso).replace(".", ",")
    if "," not in frete_peso:
        frete_peso += ",00"
    filial = (args.filial or "CAR").upper().strip()

    if len(chave_nfe) != 44 or not chave_nfe.isdigit():
        return gerar_saida(False, erro=f"Chave NF-e invalida: {len(chave_nfe)} chars")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        try:
            # ── 1. Login ──
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            main_frame = page.frames[0]

            # ── 2. Trocar filial para CAR ──
            # Usar evaluate (nao fill nativo) pois fill na filial causa page reload
            filial_result = await trocar_filial(page, filial)

            # ── 3. Abrir opcao 004 ──
            popup = await abrir_opcao_popup(context, main_frame, 4, timeout_s=30)
            await asyncio.sleep(2)

            # Override createNewDoc para manter DOM in-place
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
            await capturar_screenshot_local(popup, "01_menu_tipos")

            # ── 4. Clicar "N Normal" — deixar override fazer document.write(valSep) ──
            await popup.evaluate("ajaxEnvia('NORMAL', 1)")
            await asyncio.sleep(5)  # Esperar AJAX + document.write
            # Re-apply override
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            await capturar_screenshot_local(popup, "02_formulario_vazio")

            campos_ok = {}

            # ── 5a. Preencher Placa Coleta (NATIVO) ──
            try:
                campo_placa = popup.locator('input[name="f13"]')
                await campo_placa.click()
                await campo_placa.fill(placa)
                await campo_placa.press("Tab")
                await asyncio.sleep(3)  # SSW valida placa no blur
                campos_ok["placa"] = placa
            except Exception as e:
                return gerar_saida(False, erro=f"Falha ao preencher placa: {e}")

            await capturar_screenshot_local(popup, "03_placa_preenchida")

            # ── 5b. Preencher chave NF-e ──
            # Apos Tab na placa ARMAZEM, SSW abre popup nfepnl automaticamente
            # com campo chaveAcesso (name="chaveAcesso", id="-1", maxlength=45)
            # Handler inline: onchange="isSSW(this.value,1)" faz lookup NF-e
            try:
                campo_chave = popup.locator('input[name="chaveAcesso"]')
                await campo_chave.wait_for(state="attached", timeout=8000)
                await asyncio.sleep(0.5)

                # Preencher chave (fill nativo)
                await campo_chave.click(force=True)
                await campo_chave.fill(chave_nfe, force=True)
                await asyncio.sleep(1)

                # Clicar FORA do popup nfepnl para fechar + disparar onchange/isSSW
                await popup.mouse.click(10, 500)
                await asyncio.sleep(10)  # Esperar lookup NF-e (request ao servidor)

                campos_ok["chave_nfe"] = chave_nfe
                campos_ok["chave_metodo"] = "native_popup_nfepnl"
            except Exception as e:
                # Fallback: setar via evaluate e chamar isSSW
                try:
                    await popup.evaluate(f"""() => {{
                        const el = document.querySelector('input[name="chaveAcesso"]');
                        if (el) {{
                            el.value = '{chave_nfe}';
                            if (typeof isSSW === 'function') isSSW(el.value, 1);
                        }}
                    }}""")
                    await asyncio.sleep(8)
                    campos_ok["chave_nfe"] = chave_nfe
                    campos_ok["chave_metodo"] = "evaluate_isSSW"
                except Exception as e2:
                    return gerar_saida(False, erro=f"Falha chave: {e} / {e2}")

            await capturar_screenshot_local(popup, "04_chave_preenchida")

            # ── 5c. Abrir "Frete informado" e preencher frete peso ──
            # Painel "parc" eh colapsavel — abrir e preencher com force
            try:
                await popup.evaluate("showhide('parc')")
                await asyncio.sleep(1)
                campo_frete = popup.locator('input[name="id_frt_inf_frete_peso"]')
                await campo_frete.click(force=True)
                await campo_frete.fill(frete_peso, force=True)
                await asyncio.sleep(0.5)
                campos_ok["frete_peso"] = frete_peso
            except Exception as e:
                # Fallback evaluate
                await popup.evaluate(f"""() => {{
                    const el = document.getElementById('id_frt_inf_frete_peso');
                    if (el) {{ el.value = '{frete_peso}'; }}
                }}""")
                campos_ok["frete_peso"] = frete_peso
                campos_ok["frete_metodo"] = "evaluate"

            # Confirmar painel frete informado (► = fechafrtparc('C'))
            try:
                await popup.evaluate("fechafrtparc('C')")
            except Exception:
                # Clicar fora para fechar o painel
                await popup.mouse.click(10, 500)
            await asyncio.sleep(2)

            await capturar_screenshot_local(popup, "05_frete_preenchido")

            # ── 5d. Preencher dimensoes de moto (se fornecidas) ──
            # Painel "Volume (m3)" — abrir com showhide('volume')
            # Campos por linha: id_dim_{n}_altu, id_dim_{n}_larg,
            #   id_dim_{n}_comp, id_dim_{n}_vezes
            # Confirmar com acabadim('C')
            medidas_list = getattr(args, 'medidas', None)
            if medidas_list:
                if isinstance(medidas_list, str):
                    medidas_list = json.loads(medidas_list)

                try:
                    # Abrir painel Volume
                    await popup.evaluate("showhide('volume')")
                    await asyncio.sleep(1)

                    for i, med in enumerate(medidas_list, start=1):
                        # Formatar valores para BR (virgula decimal, 3 casas)
                        alt_br = f"{float(med['alt_m']):.3f}".replace('.', ',')
                        larg_br = f"{float(med['larg_m']):.3f}".replace('.', ',')
                        comp_br = f"{float(med['comp_m']):.3f}".replace('.', ',')
                        qtd_str = str(int(med['qtd']))

                        # Preencher campos de dimensao
                        campo_alt = popup.locator(f'input[name="id_dim_{i}_altu"]')
                        campo_larg = popup.locator(f'input[name="id_dim_{i}_larg"]')
                        campo_comp = popup.locator(f'input[name="id_dim_{i}_comp"]')
                        campo_vezes = popup.locator(f'input[name="id_dim_{i}_vezes"]')

                        await campo_alt.click(force=True)
                        await campo_alt.fill(alt_br, force=True)
                        await asyncio.sleep(0.3)

                        await campo_larg.click(force=True)
                        await campo_larg.fill(larg_br, force=True)
                        await asyncio.sleep(0.3)

                        await campo_comp.click(force=True)
                        await campo_comp.fill(comp_br, force=True)
                        await asyncio.sleep(0.3)

                        await campo_vezes.click(force=True)
                        await campo_vezes.fill(qtd_str, force=True)
                        # Tab dispara onblur=linhadim() que calcula cubagem
                        await campo_vezes.press("Tab")
                        await asyncio.sleep(1)

                    # Confirmar dimensoes (botao ► = acabadim('C'))
                    await popup.evaluate("acabadim('C')")
                    await asyncio.sleep(2)

                    campos_ok["medidas"] = medidas_list
                    campos_ok["medidas_linhas"] = len(medidas_list)
                except Exception as e:
                    campos_ok["medidas_erro"] = str(e)

                await capturar_screenshot_local(popup, "05b_medidas_preenchidas")

            # ── Dry-run: parar aqui ──
            if args.dry_run:
                campos_estado = await capturar_campos(popup)
                return gerar_saida(
                    True, modo="dry-run",
                    campos_preenchidos=campos_ok,
                    campos_formulario=campos_estado,
                    mensagem="Preview. Nenhuma acao executada.",
                )

            # ── 6. Clicar ► para simular/calcular frete ──
            # O botao ► principal chama calculafrete(this)
            dialogs = []
            ctrc_num = None

            async def on_dialog(dialog):
                nonlocal ctrc_num
                msg = dialog.message
                msg_lower = msg.lower()
                dialogs.append({"tipo": dialog.type, "msg": msg})

                if dialog.type == "confirm":
                    if "email" in msg_lower or "e-mail" in msg_lower or "disponivel" in msg_lower:
                        await dialog.dismiss()  # Email nao disponivel -> NAO
                    elif "confirma" in msg_lower or "gravar" in msg_lower or "emiss" in msg_lower:
                        await dialog.accept()   # Confirma -> SIM
                    else:
                        await dialog.accept()
                else:
                    # Alert — capturar numero CTRC
                    m = re.search(r'(\d{2,6})', msg)
                    if m and not ctrc_num:
                        ctrc_num = m.group(1)
                    await dialog.accept()

            popup.on("dialog", on_dialog)

            try:
                # ── 6. Clicar ► (calculafrete) = SIMULAR ──
                try:
                    await popup.evaluate("calculafrete(this)")
                except Exception:
                    pass

                await asyncio.sleep(8)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                await capturar_screenshot_local(popup, "06_pos_simular")

                # ── 7. Tratar "Email nao disponivel" (popup SSW customizado) ──
                # calculafrete pode disparar email dialog antes do resumo
                try:
                    await popup.evaluate("""() => {
                        const links = document.querySelectorAll('a');
                        for (const el of links) {
                            const t = el.textContent.toLowerCase();
                            if (t.includes('disponível') || t.includes('disponivel')) {
                                el.click(); return true;
                            }
                        }
                        return false;
                    }""")
                except Exception:
                    pass
                await asyncio.sleep(5)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                await capturar_screenshot_local(popup, "07_pos_email")

                # ── 8. GRAVAR no painel de resumo ──
                # O botao REAL eh "1. Gravar" com onclick concluindo('C')
                # NAO confundir com "1. Gravar CTRC/Subcontrato/NFPS" (ajaxEnvia #res_con#)
                try:
                    await popup.evaluate("concluindo('C')")
                except Exception:
                    # Fallback: clicar no link
                    await popup.evaluate("""() => {
                        const links = document.querySelectorAll('a[onclick]');
                        for (const el of links) {
                            if (el.getAttribute('onclick') && el.getAttribute('onclick').includes("concluindo('C')")) {
                                el.click(); return true;
                            }
                        }
                        return false;
                    }""")

                await asyncio.sleep(10)  # Esperar gravar + possiveis dialogs
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                await capturar_screenshot_local(popup, "08_pos_gravar")

                # ── 9. Extrair CTRC do formulario pos-gravar ──
                # Apos concluindo('C'), o SSW volta ao formulario vazio
                # com "CTRC anterior: 000094-9" mostrando o ultimo gravado
                page_closed = False
                try:
                    await popup.evaluate("1")
                except Exception:
                    page_closed = True

                if not ctrc_num and not page_closed:
                    body = await popup.evaluate(
                        "() => document.body ? document.body.innerText.substring(0,8000) : ''"
                    )
                    # Extrair de "CTRC anterior: 000094-9" → pegar 94
                    m = re.search(r'CTRC\s*anterior\s*:?\s*0*(\d+)', body, re.IGNORECASE)
                    if m:
                        ctrc_num = m.group(1)

                    # Fallback: campo hidden ou input com valor do CTRC
                    if not ctrc_num:
                        ctrc_num = await popup.evaluate("""() => {
                            // Tentar campo que mostra CTRC anterior
                            const el = document.querySelector('input[name="seq_ant"]');
                            if (el && el.value && el.value.trim()) return el.value.trim();
                            const el2 = document.getElementById('seq_ctrc');
                            if (el2 && el2.value && el2.value.trim()) return el2.value.trim();
                            return null;
                        }""")

                await capturar_screenshot_local(popup, "09_resultado")

                resultado = {
                    "ctrc": ctrc_num,
                    "dialogs": dialogs,
                    "popup_fechou": page_closed,
                }

            finally:
                try:
                    popup.remove_listener("dialog", on_dialog)
                except Exception:
                    pass

            # ── 11. Enviar ao SEFAZ (link na propria tela 004) ──
            # O link "Enviar meus CT-es ao SEFAZ" fica na barra inferior da 004
            # junto com ► × Impressão Etiquetas
            # onclick: ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024')
            sefaz_result = None
            if args.enviar_sefaz:
                try:
                    sefaz_dialogs = []

                    async def on_sefaz_dlg(dialog):
                        sefaz_dialogs.append({"tipo": dialog.type, "msg": dialog.message})
                        await dialog.accept()

                    popup.on("dialog", on_sefaz_dlg)

                    try:
                        # Clicar direto via evaluate (mais confiavel que locator)
                        await popup.evaluate(
                            "ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024')"
                        )
                        await asyncio.sleep(15)  # SEFAZ pode demorar
                        await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                        await capturar_screenshot_local(popup, "09_sefaz")

                        body_sefaz = await popup.evaluate(
                            "() => document.body ? document.body.innerText.substring(0,5000) : ''"
                        )

                        sefaz_result = {
                            "dialogs": sefaz_dialogs,
                            "body": body_sefaz[:2000],
                        }
                    finally:
                        try:
                            popup.remove_listener("dialog", on_sefaz_dlg)
                        except Exception:
                            pass

                except Exception as e:
                    sefaz_result = {"erro": str(e)}

            # ── 12. Consultar 101 + baixar DACTE/XML ──
            consulta_101 = None
            if args.consultar_101 and ctrc_num:
                try:
                    popup_101 = await abrir_opcao_popup(
                        context, main_frame, 101, timeout_s=30
                    )
                    await asyncio.sleep(2)
                    await popup_101.evaluate(CREATE_NEW_DOC_OVERRIDE)

                    # Preencher CTRC no campo t_nro_ctrc (sem DV)
                    await popup_101.evaluate(f"""() => {{
                        const el = document.getElementById('t_nro_ctrc');
                        if (el) el.value = '{ctrc_num}';
                    }}""")
                    await asyncio.sleep(1)

                    # Pesquisar: ajaxEnvia('P1', 1)
                    await popup_101.evaluate("ajaxEnvia('P1', 1)")
                    await asyncio.sleep(8)
                    await popup_101.evaluate(CREATE_NEW_DOC_OVERRIDE)
                    await capturar_screenshot_local(popup_101, f"10_101_{ctrc_num}")

                    body_101 = await popup_101.evaluate(
                        "() => document.body ? document.body.innerText.substring(0,5000) : ''"
                    )

                    # Capturar links DACTE e XML (se existirem)
                    dacte_info = await popup_101.evaluate("""() => {
                        const d = document.getElementById('link_imp_dacte');
                        const x = document.getElementById('link_imp_xml');
                        return {
                            dacte: d ? d.getAttribute('onclick') : null,
                            xml: x ? x.getAttribute('onclick') : null
                        };
                    }""")

                    consulta_101 = {
                        "body": body_101[:3000],
                        "dacte_onclick": dacte_info.get("dacte"),
                        "xml_onclick": dacte_info.get("xml"),
                    }

                    try:
                        await popup_101.close()
                    except Exception:
                        pass

                except Exception as e:
                    consulta_101 = {"erro": str(e)}

            # ── Resultado final ──
            sucesso = ctrc_num is not None
            return gerar_saida(
                sucesso,
                ctrc=ctrc_num,
                campos_preenchidos=campos_ok,
                resultado=resultado,
                sefaz=sefaz_result,
                consulta_101=consulta_101,
                mensagem=f"CT-e {ctrc_num or '?'} — "
                         f"{'Emitido' if sucesso else 'Inconclusivo'}. "
                         f"{'SEFAZ enviado.' if sefaz_result and not sefaz_result.get('erro') else ''}"
            )

        except Exception as e:
            return gerar_saida(False, erro=str(e), traceback=traceback.format_exc()[-1000:])

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Emitir CT-e no SSW (opcao 004). Fluxo completo: 004 → 007 → 101."
    )

    # Modo discover
    parser.add_argument(
        "--discover", action="store_true",
        help="Modo exploratorio: abre opcao 004 e lista campos da emissao"
    )

    # Parametros da emissao
    parser.add_argument(
        "--chave-nfe", default=None,
        help="Chave de acesso da NF-e (44 digitos)"
    )
    parser.add_argument(
        "--placa", default="ARMAZEM",
        help="Placa de coleta (default: ARMAZEM para fracionado)"
    )
    parser.add_argument(
        "--frete-peso", type=float, default=None,
        help="Valor do frete peso (informado manualmente)"
    )
    parser.add_argument(
        "--filial", default="CAR",
        help="Filial para emissao (default: CAR)"
    )

    # Dimensoes moto (novo)
    parser.add_argument(
        "--medidas", default=None,
        help='JSON com dimensoes moto: [{"comp_m":2.0,"larg_m":0.8,"alt_m":1.2,"qtd":3}]'
    )

    # Etapas opcionais
    parser.add_argument(
        "--enviar-sefaz", action="store_true",
        help="Enviar CT-e ao SEFAZ apos gravar (opcao 007)"
    )
    parser.add_argument(
        "--consultar-101", action="store_true",
        help="Consultar resultado na opcao 101 apos emissao"
    )
    parser.add_argument(
        "--baixar-dacte", action="store_true",
        help="Baixar DACTE PDF e XML (requer --consultar-101)"
    )
    parser.add_argument(
        "--baixar-xml", action="store_true",
        help="Baixar XML do CT-e (requer --consultar-101)"
    )

    # Config
    parser.add_argument(
        "--defaults-file",
        default=os.path.join(SCRIPT_DIR, "..", "ssw_defaults.json"),
        help="Caminho para ssw_defaults.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preenche formulario sem gravar. OBRIGATORIO na primeira execucao."
    )

    args = parser.parse_args()

    # Modo discover
    if args.discover:
        asyncio.run(descobrir_campos(args))
        return

    # Validar parametros obrigatorios
    faltando = []
    if not args.chave_nfe:
        faltando.append("--chave-nfe")
    if args.frete_peso is None:
        faltando.append("--frete-peso")

    if faltando:
        print(json.dumps({
            "sucesso": False,
            "erro": f"Parametros obrigatorios faltando: {', '.join(faltando)}",
            "uso": 'python emitir_cte_004.py --chave-nfe "332603..." --frete-peso 600 '
                   '--placa ARMAZEM --enviar-sefaz --consultar-101 --dry-run',
        }, ensure_ascii=False))
        sys.exit(1)

    asyncio.run(emitir_cte(args))


if __name__ == "__main__":
    main()
