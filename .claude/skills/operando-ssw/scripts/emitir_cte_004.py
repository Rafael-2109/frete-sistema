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
  - Filial depende da UF de origem: SP=CAR, RJ=GIG (ver UF_FILIAL_MAP no service)
  - Placa ARMAZEM = frete fracionado (cliente trouxe ao armazem)
  - Pre-CTRC so tem valor fiscal APOS autorizacao SEFAZ (opcao 007)
  - Chave NF-e de 44 digitos — sistema auto-preenche dados da NF
  - Pos-simular: SSW usa paineis HTML "Aviso" (nao JS dialogs) para:
    * Email pagador → clicar "E-mail nao disponivel"
    * Cliente bloqueado → desbloqueio automatico (ssw1105, f2=S)
    * GNRE/Guia recolhimento → clicar "Continuar" (CFOP 5932, RJ→RJ)
    * Resumo → "1. Gravar" (concluindo('C'))

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
    login_ssw,
    abrir_opcao_popup,
    interceptar_ajax_response,
    injetar_html_no_dom,
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


EVIDENCE_DIR = "/tmp/ssw_operacoes/emitir_cte"


async def capturar_screenshot_local(page, nome):
    """Screenshot com diretorio especifico para emissao CTE."""
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    return await capturar_screenshot(page, nome, diretorio=EVIDENCE_DIR)


async def _clicar_simular(popup, timeout_ms=5000):
    """Click no ► (#lnk_env → calculafrete) com fallback JS.

    O SSW mantem um <div id="errorpanel"> como overlay invisivel (sem
    pointer-events: none) que intercepta cliques do Playwright. O click
    nativo timeouta em 30s tentando reagir ao elemento coberto.

    Estrategia:
      1) Tentar click nativo (rapido, 5s timeout)
      2) Se falhar: click via JS (document.getElementById('lnk_env').click())
         — isso bypassa a checagem de "element covered" do Playwright.

    Mesmo padrao usado no emitir_cte_complementar_222.py para o mesmo
    problema do errorpanel.

    Returns:
        str: 'native' | 'lnk_env' | 'onclick_calculafrete'

    Raises:
        RuntimeError: Se nenhum dos metodos encontrou/conseguiu clicar.
    """
    # 1) Tentativa nativa rapida
    try:
        await popup.get_by_role("link", name="►").first.click(
            timeout=timeout_ms
        )
        return 'native'
    except Exception:
        pass

    # 2) Fallback: click via JS direto no DOM (bypassa overlay errorpanel)
    metodo = await popup.evaluate("""() => {
        // Tenta pelo id explicito primeiro
        const link = document.getElementById('lnk_env');
        if (link) {
            link.click();
            return 'lnk_env';
        }
        // Fallback: buscar link com onclick contendo calculafrete
        for (const l of document.querySelectorAll('a')) {
            const oc = l.getAttribute('onclick') || '';
            if (oc.includes('calculafrete')) {
                l.click();
                return 'onclick_calculafrete';
            }
        }
        return null;
    }""")

    if not metodo:
        raise RuntimeError(
            "Nao encontrou o link ► (calculafrete/#lnk_env) no DOM"
        )
    return metodo


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


async def trocar_filial(page, filial_alvo="CAR"):
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
            await trocar_filial(page, filial)

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

                # Clicar "OK" para confirmar chave (fecha popup nfepnl + lookup)
                # Tambem trata aviso "carta de correcao" se exibido
                ok_link = popup.get_by_role("link", name="OK")
                try:
                    await ok_link.click(timeout=5000)
                except Exception:
                    # Fallback: clicar fora
                    await popup.mouse.click(10, 500)
                await asyncio.sleep(10)  # Esperar lookup NF-e

                # Se aviso carta de correcao apareceu, clicar OK novamente
                try:
                    body_chk = await popup.evaluate(
                        "() => (document.body?.innerText || '').substring(0,2000).toLowerCase()"
                    )
                    if 'carta' in body_chk and 'corre' in body_chk:
                        await ok_link.click(timeout=3000)
                        await asyncio.sleep(3)
                        campos_ok["carta_correcao"] = True
                except Exception:
                    pass

                campos_ok["chave_nfe"] = chave_nfe
                campos_ok["chave_metodo"] = "native_ok"
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

            # ── 5c. Dimensoes de moto (se fornecidas) ──
            # Ordem da gravacao: Volume → peso → frete → simular
            medidas_list = getattr(args, 'medidas', None)
            if medidas_list:
                if isinstance(medidas_list, str):
                    medidas_list = json.loads(medidas_list)

                try:
                    # Abrir painel Volume (clicar link "Volume (m3):")
                    await popup.get_by_role("link", name="Volume (m3):").click()
                    await asyncio.sleep(1)

                    for i, med in enumerate(medidas_list, start=1):
                        alt_br = f"{float(med['alt_m']):.2f}".replace('.', ',')
                        larg_br = f"{float(med['larg_m']):.2f}".replace('.', ',')
                        comp_br = f"{float(med['comp_m']):.2f}".replace('.', ',')
                        qtd_str = str(int(med['qtd']))

                        await popup.locator(f'#id_dim_{i}_altu').click()
                        await popup.locator(f'#id_dim_{i}_altu').fill(alt_br)
                        await popup.locator(f'#id_dim_{i}_altu').press("Tab")

                        await popup.locator(f'#id_dim_{i}_larg').fill(larg_br)
                        await popup.locator(f'#id_dim_{i}_larg').press("Tab")

                        await popup.locator(f'#id_dim_{i}_comp').fill(comp_br)
                        await popup.locator(f'#id_dim_{i}_comp').press("Tab")

                        await popup.locator(f'#id_dim_{i}_vezes').fill(qtd_str)
                        await asyncio.sleep(0.5)

                    # Confirmar dimensoes: #id_dim_env (botao enviar/fechar)
                    await popup.locator('#id_dim_env').click()
                    await asyncio.sleep(2)

                    campos_ok["medidas"] = medidas_list
                    campos_ok["medidas_linhas"] = len(medidas_list)
                except Exception as e:
                    campos_ok["medidas_erro"] = str(e)

                await capturar_screenshot_local(popup, "05b_medidas_preenchidas")

            # ── 5d. Preencher peso real se zero (50% do cubado) ──
            # Gravacao: fill() nativo funciona no campo id_peso_real
            try:
                peso_cv = await popup.evaluate(
                    "() => +(document.getElementById('id_peso_real')"
                    "?.getAttribute('currencyvalue') || 0)"
                )
                if peso_cv == 0 and medidas_list:
                    meds = (medidas_list if isinstance(medidas_list, list)
                            else json.loads(medidas_list))
                    cubado_total = sum(
                        float(m['comp_m']) * float(m['larg_m']) * float(m['alt_m'])
                        * 300 * int(m.get('qtd', 1))
                        for m in meds
                    )
                    peso_50 = round(cubado_total * 0.5, 2)
                    peso_br = f"{peso_50:.2f}".replace('.', ',')

                    await popup.locator('#id_peso_real').click()
                    await popup.locator('#id_peso_real').fill(peso_br)
                    await asyncio.sleep(1)

                    campos_ok["peso_real"] = peso_br
                    campos_ok["peso_real_motivo"] = "50pct_cubado"
                    campos_ok["peso_cubado_calc"] = round(cubado_total, 2)
                elif peso_cv > 0:
                    campos_ok["peso_real_motivo"] = "ja_preenchido"
            except Exception as e:
                campos_ok["peso_real_erro"] = str(e)

            # ── 5e. Frete informado (OVERRIDE manual sobre tabela) ──
            # Fluxo validado via Playwright codegen manual:
            #   1. Click "Frete informado:" — abre painel parc
            #   2. fill em #id_frt_inf_frete_peso — valor em R$
            #   3. Click em #lnk_frt_inf_env — CONFIRMA o valor informado
            #
            # Nota historica: SCRIPTS.md antigo sugeria fechafrtparc('C'),
            # mas o codegen manual (que funciona e gera CTe com valor
            # override) usa #lnk_frt_inf_env — essa e a fonte de verdade.
            try:
                await popup.get_by_role("link", name="Frete informado:").click()
                await asyncio.sleep(0.5)

                await popup.locator('#id_frt_inf_frete_peso').fill(frete_peso)
                await asyncio.sleep(0.3)

                # CONFIRMAR via #lnk_frt_inf_env (mesmo que o usuario clica)
                await popup.locator('#lnk_frt_inf_env').click()
                await asyncio.sleep(2)
                campos_ok["frete_peso"] = frete_peso
                campos_ok["frete_metodo"] = "lnk_frt_inf_env"
            except Exception as e:
                campos_ok["frete_erro"] = str(e)

            await capturar_screenshot_local(popup, "05_campos_preenchidos")

            # ── Dry-run: parar aqui ──
            if args.dry_run:
                campos_estado = await capturar_campos(popup)
                return gerar_saida(
                    True, modo="dry-run",
                    campos_preenchidos=campos_ok,
                    campos_formulario=campos_estado,
                    mensagem="Preview. Nenhuma acao executada.",
                )

            # ── 6. SIMULAR + tratar Avisos HTML + GRAVAR ──
            #
            # Apos calculafrete(), o SSW exibe uma SEQUENCIA de paineis HTML
            # "Aviso" (nao JS dialogs). A ordem tipica:
            #   1. Email: "Informe e-mail do cliente pagador"
            #      → clicar "E-mail não está disponível"
            #   2. (Opcional) Bloqueio: "Cliente pagador bloqueado para transporte"
            #      → abrir ssw1105, mudar f2=S, confirmar, voltar e re-simular
            #   3. (Opcional) GNRE/ICMS: "ICMS deve ser recolhido antecipadamente"
            #      → clicar "Continuar"
            #   4. Resumo: mostra valores calculados
            #      → clicar "1. Gravar" (concluindo('C'))
            #
            # JS dialogs sao raros mas mantemos handler como fallback.

            dialogs = []
            ctrc_num = None
            avisos_tratados = []

            async def on_dialog(dialog):
                nonlocal ctrc_num
                msg = dialog.message
                dialogs.append({"tipo": dialog.type, "msg": msg})
                if dialog.type == "confirm":
                    if "email" in msg.lower() or "disponivel" in msg.lower():
                        await dialog.dismiss()
                    else:
                        await dialog.accept()
                else:
                    m = re.search(r'(\d{2,6})', msg)
                    if m and not ctrc_num:
                        ctrc_num = m.group(1)
                    await dialog.accept()

            popup.on("dialog", on_dialog)

            try:
                # ── 6a. Simular (clicar ► via helper com fallback JS) ──
                # Helper lida com <div id="errorpanel"> que intercepta
                # pointer events no SSW — fallback via evaluate.
                metodo_simular = await _clicar_simular(popup)
                avisos_tratados.append(f"SIMULAR_CLICK:{metodo_simular}")
                await asyncio.sleep(8)
                await capturar_screenshot_local(popup, "06_pos_simular")

                # ── 6b. Tratar paineis Aviso em sequencia ──
                MAX_AVISOS = 6  # Seguranca contra loop infinito
                for aviso_idx in range(MAX_AVISOS):
                    body = await popup.evaluate(
                        "() => document.body ? document.body.innerText.substring(0,5000) : ''"
                    )
                    body_lower = body.lower()

                    # --- Aviso: Email ---
                    if 'disponível' in body_lower and 'e-mail' in body_lower:
                        await popup.evaluate("""() => {
                            const links = document.querySelectorAll('a');
                            for (const el of links) {
                                if (el.textContent.toLowerCase().includes('disponível')) {
                                    el.click(); return true;
                                }
                            }
                            return false;
                        }""")
                        avisos_tratados.append("EMAIL_DISPENSADO")
                        await asyncio.sleep(5)
                        await capturar_screenshot_local(popup, f"07_aviso_{aviso_idx}_email")
                        continue

                    # --- Aviso: Peso real inválido ---
                    if 'peso real' in body_lower and 'inválido' in body_lower:
                        avisos_tratados.append("PESO_INVALIDO_OK")
                        await capturar_screenshot_local(popup, f"07_aviso_{aviso_idx}_peso")
                        # Clicar "7. OK" para fechar aviso
                        await popup.evaluate("""() => {
                            const links = document.querySelectorAll('a');
                            for (const el of links) {
                                const t = el.textContent.trim();
                                if (t.includes('OK') || t === '7. OK') {
                                    el.click(); return true;
                                }
                            }
                            return false;
                        }""")
                        await asyncio.sleep(3)

                        # Re-preencher peso via evaluate (currencyedit)
                        peso_50 = campos_ok.get("peso_cubado_calc", 100) * 0.5
                        peso_br = f"{peso_50:.3f}".replace('.', ',')
                        await popup.evaluate(f"""() => {{
                            const el = document.getElementById('id_peso_real');
                            if (el) {{
                                el.value = '{peso_br}';
                                el.setAttribute('currencyvalue', '{peso_50}');
                                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                                el.dispatchEvent(new Event('blur', {{bubbles: true}}));
                            }}
                        }}""")
                        await asyncio.sleep(1)

                        # Re-simular apos ajuste de peso (com fallback JS)
                        try:
                            await _clicar_simular(popup)
                        except Exception as e_resim:
                            avisos_tratados.append(
                                f"RESIMULAR_PESO_ERRO: {e_resim}"
                            )
                        await asyncio.sleep(8)
                        continue

                    # --- Aviso: Cliente bloqueado (desbloquear, 2 fluxos SSW) ---
                    #
                    # Ao clicar "Desbloquear cliente pagador" o SSW carrega a
                    # tela 389/ssw1105 (Credito/Transportar). Testado com
                    # MGS ELETRO (2026-04-23, emissoes id=11 e id=12):
                    # o SSW abriu ssw1105 na MESMA popup, nao em nova page.
                    # Por isso usamos expect_page com timeout curto e fazemos
                    # fallback para detectar navegacao in-place via URL/body.
                    # Em ambos casos: fill f2="S" + click "►" para gravar +
                    # aguardar SSW voltar a tela 004 de emissao CTe.
                    if ('bloqueado' in body_lower or 'desbloquear' in body_lower) \
                            and 'transporte' in body_lower:
                        avisos_tratados.append("CLIENTE_BLOQUEADO")
                        await capturar_screenshot_local(popup, f"07_aviso_{aviso_idx}_bloqueio")

                        # Alvo do fill: desbloq_page se SSW abriu em nova janela,
                        # ou o proprio popup se o SSW navegou in-place.
                        desbloq_target = None
                        desbloq_origem = None
                        try:
                            async with context.expect_page(timeout=4000) as desbloq_info:
                                await popup.get_by_role(
                                    "link", name="Desbloquear cliente pagador"
                                ).click()
                            desbloq_target = await desbloq_info.value
                            desbloq_origem = "nova_page"
                            await asyncio.sleep(2)
                        except Exception:
                            # Timeout curto: SSW provavelmente navegou a mesma popup
                            # para ssw1105. Aguardar e verificar se o body mudou.
                            await asyncio.sleep(3)
                            try:
                                body_check = await popup.evaluate(
                                    "() => (document.body?.innerText || '').substring(0,3000).toLowerCase()"
                                )
                            except Exception:
                                body_check = ''
                            # Tela 389/ssw1105 tem "limites de credito" e "transportar:"
                            if ('limites de cr' in body_check
                                    and 'transportar' in body_check):
                                desbloq_target = popup
                                desbloq_origem = "inline_popup"
                            else:
                                avisos_tratados.append(
                                    "DESBLOQUEIO_SEM_TARGET: body nao parece ssw1105"
                                )

                        if desbloq_target is not None:
                            avisos_tratados.append(
                                f"DESBLOQUEIO_TARGET:{desbloq_origem}"
                            )
                            try:
                                # Seletor robusto: HTML real do ssw1105 tem
                                # <input name="f2" id="2" value="N" ...>.
                                # Tentamos id="2" primeiro, depois name="f2".
                                campo_f2 = desbloq_target.locator(
                                    'input[id="2"], input[name="f2"]'
                                ).first
                                await campo_f2.wait_for(state="visible", timeout=5000)
                                await campo_f2.fill("S")
                                # Blur para disparar validacao SSW
                                await campo_f2.press("Tab")
                                await asyncio.sleep(0.5)

                                # Gravar (SALVAR): clicar "►" que dispara o
                                # submit via concluir/ajaxEnvia e persiste.
                                # Seletor robusto: a tela 389 pode ter outros
                                # "►" (Consulta Serasa, paginacao). Priorizamos
                                # o link com onclick contendo 'concluir' ou
                                # 'ajaxEnvia' SEM parametros ('INA','SERASA')
                                # que sinalizam ACOES auxiliares. Fallback para
                                # get_by_role se nao achar via JS.
                                clicou_gravar = await desbloq_target.evaluate(
                                    """() => {
                                        const links = document.querySelectorAll('a');
                                        for (const el of links) {
                                            const t = (el.textContent || '').trim();
                                            if (t !== '►') continue;
                                            const oc = el.getAttribute('onclick') || '';
                                            // Links auxiliares (INA, SERASA)
                                            // nao sao de gravar:
                                            if (oc.includes("'INA'") ||
                                                oc.includes("'SERASA'") ||
                                                oc.includes("'INFO'")) continue;
                                            el.click();
                                            return oc.substring(0, 150);
                                        }
                                        return null;
                                    }"""
                                )
                                if not clicou_gravar:
                                    # Fallback: primeiro ► da DOM (codigo antigo)
                                    await desbloq_target.get_by_role(
                                        "link", name="►"
                                    ).first.click(timeout=5000)
                                    avisos_tratados.append(
                                        "GRAVAR_F2_FALLBACK:first"
                                    )
                                else:
                                    avisos_tratados.append(
                                        f"GRAVAR_F2_ONCLICK:{clicou_gravar[:80]}"
                                    )
                                # Aguardar SSW processar gravacao + voltar
                                # para tela 004 (ou fechar popup de desbloqueio).
                                await asyncio.sleep(5)
                                await capturar_screenshot_local(
                                    desbloq_target, f"07_aviso_{aviso_idx}_f2_gravado"
                                )

                                # Se foi nova page, FECHAR (cliente pagador
                                # gravou e o SSW espera fechamento manual).
                                if desbloq_origem == "nova_page":
                                    try:
                                        await desbloq_target.close()
                                    except Exception:
                                        pass

                                avisos_tratados.append("CLIENTE_DESBLOQUEADO")
                                desbloqueio_ok = True
                            except Exception as e:
                                avisos_tratados.append(f"DESBLOQUEIO_ERRO: {e}")
                                desbloqueio_ok = False
                        else:
                            desbloqueio_ok = False

                        if not desbloqueio_ok:
                            # Desbloqueio falhou (nova page nao abriu E navegacao
                            # in-place nao foi detectada, OU o fill/click falhou).
                            # Interromper loop: sem desbloqueio o proximo ciclo
                            # veria o mesmo painel, gastando ate MAX_AVISOS=6
                            # iteracoes (~84s) antes de falhar.
                            avisos_tratados.append("CLIENTE_BLOQUEADO_ABORT")
                            break

                        # Re-simular na MESMA popup apos desbloqueio. Se o SSW
                        # navegou in-place, pode ser necessario aguardar mais
                        # tempo para ele retornar da tela 389 para a 004.
                        await asyncio.sleep(3)
                        try:
                            await _clicar_simular(popup)
                        except Exception as e_resim:
                            avisos_tratados.append(
                                f"RESIMULAR_DESBLOQ_ERRO: {e_resim}"
                            )
                        await asyncio.sleep(8)
                        continue

                    # --- Aviso: GNRE/Guia de Recolhimento ---
                    if ('guia de recolhimento' in body_lower or
                            'gnre' in body_lower or
                            'recolhido antecipadamente' in body_lower):
                        avisos_tratados.append("GNRE_CONTINUAR")
                        await capturar_screenshot_local(popup, f"07_aviso_{aviso_idx}_gnre")
                        await popup.evaluate("""() => {
                            const links = document.querySelectorAll('a');
                            for (const el of links) {
                                if (el.textContent.trim().toLowerCase().includes('continuar')) {
                                    el.click(); return true;
                                }
                            }
                            return false;
                        }""")
                        await asyncio.sleep(3)
                        continue

                    # --- Resumo com "Gravar" (match flexivel via regex) ---
                    # SSW pode renderizar como "1. Gravar", "Gravar", "1.Gravar"
                    # etc. Regex case-insensitive cobre todas variacoes.
                    try:
                        gravar_link = popup.get_by_role(
                            "link", name=re.compile(r"Gravar", re.IGNORECASE)
                        )
                        if await gravar_link.count() > 0:
                            avisos_tratados.append("RESUMO_GRAVAR")
                            await capturar_screenshot_local(
                                popup, f"07_aviso_{aviso_idx}_resumo"
                            )
                            break  # Sair do loop para gravar
                    except Exception:
                        pass

                    # --- Fallback: link com onclick=concluindo('C') ---
                    # Caso o texto do link nao contenha "Gravar" mas o
                    # comportamento seja o mesmo (SSW pode ter variacoes).
                    try:
                        achou_concluindo = await popup.evaluate("""() => {
                            for (const l of document.querySelectorAll('a')) {
                                const oc = l.getAttribute('onclick') || '';
                                if (oc.includes("concluindo('C')") ||
                                    oc.includes('concluindo("C")') ||
                                    oc.includes('concluindo(\\'C\\')')) {
                                    return {
                                        found: true,
                                        text: (l.textContent || '').trim().substring(0, 100),
                                        onclick: oc.substring(0, 200)
                                    };
                                }
                            }
                            return {found: false};
                        }""")
                        if achou_concluindo.get('found'):
                            avisos_tratados.append(
                                f"RESUMO_CONCLUINDO:{achou_concluindo.get('text')}"
                            )
                            await capturar_screenshot_local(
                                popup, f"07_aviso_{aviso_idx}_concluindo"
                            )
                            break
                    except Exception:
                        pass

                    # --- Fallback: painel com "Continuar" (GNRE, info, etc) ---
                    continuar_link = popup.get_by_role("link", name="Continuar")
                    try:
                        if await continuar_link.count() > 0:
                            avisos_tratados.append(f"CONTINUAR_GENERICO_{aviso_idx}")
                            await capturar_screenshot_local(
                                popup, f"07_aviso_{aviso_idx}_continuar"
                            )
                            await continuar_link.first.click()
                            await asyncio.sleep(5)
                            continue
                    except Exception:
                        pass

                    # Nenhum aviso reconhecido — dump body + HTML para debug
                    # Aumentado de 500 → 3000 chars para capturar mais contexto.
                    # Tambem salva HTML outerHTML truncado para proximos testes.
                    try:
                        html_atual = await popup.evaluate(
                            "() => document.documentElement.outerHTML.substring(0, 8000)"
                        )
                    except Exception:
                        html_atual = ''
                    avisos_tratados.append(
                        f"NAO_RECONHECIDO: body={body[:3000]}"
                    )
                    avisos_tratados.append(
                        f"NAO_RECONHECIDO_HTML: {html_atual[:3000]}"
                    )
                    await capturar_screenshot_local(
                        popup, f"07_aviso_{aviso_idx}_nao_reconhecido"
                    )
                    break

                # ── 6d. RE-CONFIRMAR Frete informado ANTES de Gravar ──
                #
                # SOMENTE executa se houve re-simulacao durante os avisos
                # (peso_real_invalido, GNRE, cliente_desbloqueado). Essas
                # re-simulacoes silenciosamente sobrescrevem o valor digitado
                # em "Frete informado" com o valor da tabela interna —
                # apenas nesses casos o re-confirm e necessario.
                #
                # IMPORTANTE: no fluxo simples (EMAIL_DISPENSADO → RESUMO),
                # executar o re-confirm QUEBRA o fluxo porque:
                #   - click nativo falha (link "Frete informado:" nao esta
                #     mais visivel no resumo) → cai no fallback JS
                #   - fallback JS encontra #id_frt_inf_frete_peso no DOM
                #     (oculto) e clica em #lnk_frt_inf_env — isso muda o
                #     state do SSW para pos-frete, nao-resumo
                #   - ao clicar "Gravar" depois, o SSW nao retorna CTRC
                #     (emissao fica "Inconclusiva. SEFAZ enviado")
                #
                # Bug historico: commit 7e7ceee7 (2026-04-22) introduziu este
                # bloco SEM condicional — todas emissoes seguintes (NF 221,
                # NF 240) falharam com CTRC=null. Fix: condicional + fallback
                # JS so atua se campo estiver VISIVEL.
                _precisa_reconfirmar = any(
                    a in avisos_tratados for a in (
                        "PESO_INVALIDO_OK",
                        "GNRE_CONTINUAR",
                        "CLIENTE_DESBLOQUEADO",
                    )
                ) or any(
                    isinstance(a, str) and a.startswith("RESIMULAR_")
                    for a in avisos_tratados
                )

                if _precisa_reconfirmar:
                    try:
                        await popup.get_by_role(
                            "link", name="Frete informado:"
                        ).click(timeout=5000)
                        # Aguarda o painel AJAX renderizar (SSW pode levar
                        # 2-3s em carga alta — 0.5s era insuficiente).
                        await popup.locator('#id_frt_inf_frete_peso').wait_for(
                            state='visible', timeout=8000
                        )
                        await popup.locator('#id_frt_inf_frete_peso').fill(frete_peso)
                        await asyncio.sleep(0.3)
                        await popup.locator('#lnk_frt_inf_env').click()
                        await asyncio.sleep(2)
                        avisos_tratados.append(
                            f"FRETE_REINFORMADO_PRE_GRAVAR:{frete_peso}"
                        )
                        await capturar_screenshot_local(
                            popup, "07b_frete_reinformado"
                        )
                    except Exception as e_reinf:
                        # Fallback via JS — SOMENTE se painel esta visivel.
                        # `frete_peso` e passado como ARGUMENTO ao evaluate
                        # (nao interpolado em f-string) para evitar injection.
                        try:
                            reaplicou = await popup.evaluate(
                                """(val) => {
                                    const el = document.getElementById('id_frt_inf_frete_peso');
                                    if (!el) return 'sem_campo';
                                    // Guard: so prossegue se campo REALMENTE visivel
                                    // (rect nao-zero + nao oculto via CSS). Sem
                                    // esse guard, o click em lnk_frt_inf_env com
                                    // painel oculto muda o state do SSW e
                                    // quebra o fluxo do resumo.
                                    const rect = el.getBoundingClientRect();
                                    const style = window.getComputedStyle(el);
                                    const visible = rect.width > 0 && rect.height > 0
                                        && style.display !== 'none'
                                        && style.visibility !== 'hidden';
                                    if (!visible) return 'oculto';
                                    el.value = val;
                                    el.dispatchEvent(new Event('change', {bubbles: true}));
                                    el.dispatchEvent(new Event('blur', {bubbles: true}));
                                    const lnk = document.getElementById('lnk_frt_inf_env');
                                    if (lnk) { lnk.click(); return 'ok_js'; }
                                    return 'sem_lnk';
                                }""",
                                frete_peso,
                            )
                            await asyncio.sleep(2)
                            avisos_tratados.append(
                                f"FRETE_REINFORMADO_JS:{reaplicou}:{frete_peso}"
                            )
                        except Exception as e_js:
                            avisos_tratados.append(
                                f"FRETE_REINFORMADO_ERRO: native={e_reinf}, js={e_js}"
                            )
                else:
                    avisos_tratados.append(
                        "FRETE_REINFORMADO_SKIPPED:sem_resimulacao"
                    )

                # ── 7. GRAVAR pre-CTRC (match flexivel + fallback JS) ──
                await capturar_screenshot_local(popup, "08_pre_gravar")
                gravar_clicked = False
                # Tentativa 1: regex em get_by_role
                try:
                    await popup.get_by_role(
                        "link", name=re.compile(r"Gravar", re.IGNORECASE)
                    ).first.click(timeout=5000)
                    gravar_clicked = True
                    avisos_tratados.append("GRAVAR_CLICK:regex")
                except Exception:
                    pass

                # Tentativa 2: click via JS no link com onclick=concluindo
                if not gravar_clicked:
                    try:
                        metodo_js = await popup.evaluate("""() => {
                            for (const l of document.querySelectorAll('a')) {
                                const oc = l.getAttribute('onclick') || '';
                                if (oc.includes("concluindo('C')") ||
                                    oc.includes('concluindo("C")')) {
                                    l.click();
                                    return 'onclick_concluindo';
                                }
                            }
                            return null;
                        }""")
                        if metodo_js:
                            gravar_clicked = True
                            avisos_tratados.append(f"GRAVAR_CLICK:{metodo_js}")
                    except Exception:
                        pass

                # Tentativa 3: fallback final — chamar concluindo diretamente
                if not gravar_clicked:
                    try:
                        await popup.evaluate("concluindo('C')")
                        avisos_tratados.append("GRAVAR_CLICK:evaluate_concluindo")
                    except Exception as e:
                        avisos_tratados.append(f"GRAVAR_CLICK_ERRO: {e}")

                await asyncio.sleep(12)
                await capturar_screenshot_local(popup, "08_pos_gravar")

                # ── 8. Extrair CTRC ──
                page_closed = False
                try:
                    await popup.evaluate("1")
                except Exception:
                    page_closed = True

                if not ctrc_num and not page_closed:
                    body = await popup.evaluate(
                        "() => document.body ? document.body.innerText.substring(0,8000) : ''"
                    )
                    m = re.search(r'CTRC\s*anterior\s*:?\s*0*(\d+)', body, re.IGNORECASE)
                    if m:
                        ctrc_num = m.group(1)
                    if not ctrc_num:
                        ctrc_num = await popup.evaluate("""() => {
                            const el = document.querySelector('input[name="seq_ant"]');
                            if (el && el.value && el.value.trim()) return el.value.trim();
                            return null;
                        }""")

                await capturar_screenshot_local(popup, "09_resultado")

                resultado = {
                    "ctrc": ctrc_num,
                    "dialogs": dialogs,
                    "avisos_tratados": avisos_tratados,
                    "popup_fechou": page_closed,
                }

            finally:
                try:
                    popup.remove_listener("dialog", on_dialog)
                except Exception:
                    pass

            # ── 11. Enviar ao SEFAZ ──
            # O envio NAO e automatico — precisa ser disparado explicitamente.
            # Estrategia: chamar ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024')
            # via evaluate (bypass do div#errorpanel que bloqueia clicks nativos).
            # A action `REM` (Remeter) e que efetivamente envia os CT-es digitados.
            # Depois abrimos opcao 007 para capturar status da fila como evidencia.
            sefaz_result = None
            if args.enviar_sefaz:
                try:
                    # Tentar no popup atual primeiro (post-gravar), se ainda aberto
                    try:
                        await popup.evaluate(
                            "ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024')"
                        )
                        await asyncio.sleep(20)
                        sefaz_result = {"metodo": "ajaxEnvia_REM_popup004"}
                    except Exception as e_popup:
                        # Popup pode ter fechado — abrir 007 e chamar REM la
                        sefaz_result = {"popup004_erro": str(e_popup)}

                    # Abrir 007 para ler status da fila e confirmar envio
                    popup_007 = await abrir_opcao_popup(
                        context, main_frame, 7, timeout_s=30
                    )
                    await asyncio.sleep(3)
                    await popup_007.evaluate(CREATE_NEW_DOC_OVERRIDE)

                    # Se nao conseguiu chamar REM no popup 004, chamar aqui
                    if sefaz_result.get("popup004_erro"):
                        try:
                            await popup_007.evaluate(
                                "ajaxEnvia('', 1, 'ssw0767?act=REM&chamador=ssw0024')"
                            )
                            await asyncio.sleep(20)
                            sefaz_result["metodo"] = "ajaxEnvia_REM_popup007"
                        except Exception as e_007:
                            sefaz_result["popup007_erro"] = str(e_007)

                    # Forcar refresh da fila
                    try:
                        await popup_007.evaluate("ajaxEnvia('ATU', 0)")
                        await asyncio.sleep(5)
                        await popup_007.evaluate(CREATE_NEW_DOC_OVERRIDE)
                    except Exception:
                        pass

                    await capturar_screenshot_local(popup_007, "09_sefaz_007")

                    # Capturar status da fila
                    status = await popup_007.evaluate("""() => {
                        const campo = document.getElementById('sefaz');
                        const body = (document.body?.innerText || '').substring(0, 4000);
                        const extrair = (label) => {
                            const re = new RegExp(label + '[:\\\\s]*(\\\\d+)', 'i');
                            const m = body.match(re);
                            return m ? parseInt(m[1]) : null;
                        };
                        return {
                            servico: campo ? campo.value : null,
                            digitados: extrair('Digitados'),
                            enviados: extrair('Enviados à SEFAZ'),
                            autorizados: extrair('Autorizados'),
                            denegados: extrair('Denegados'),
                            rejeitados: extrair('Rejeitados'),
                        };
                    }""")
                    sefaz_result["status_fila"] = status

                    try:
                        await popup_007.close()
                    except Exception:
                        pass

                except Exception as e:
                    if sefaz_result is None:
                        sefaz_result = {}
                    sefaz_result["erro"] = str(e)

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
