#!/usr/bin/env python3
"""
cotar_frete_ssw_002.py — Cotacao de frete no SSW (opcao 002).

Fluxo:
  1. Login SSW
  2. Abre opcao 002 (popup)
  3. Override createNewDoc para manter DOM in-place
  4. ajaxEnvia('NEW', 1) para abrir formulario de nova cotacao
  5. Preencher campos: cgc_pag, tp_frete, cep_origem, cep_destino,
     coletar, entregar, vlr_merc, peso, cubagem, contribuinte
  6. calcula('S') para simular
  7. Capturar resultado agrupado (transporte, seguros, taxas, impostos)
  8. Screenshot como evidencia
  9. Output JSON via gerar_saida()

MAPEAMENTO DE CAMPOS (fonte: --discover 2026-02-19):
  cgc_pag      -> CNPJ pagador (14 dig)
  tp_frete     -> 1=CIF, 2=FOB
  cep_origem   -> CEP origem (8 dig)
  cep_destino  -> CEP destino (8 dig)
  coletar      -> S/N
  entregar     -> S/N
  contribuinte -> S/N (OBRIGATORIO para simulacao)
  vlr_merc     -> Valor NF (R$ formato brasileiro, maxLen=15)
  peso         -> Peso kg (formato brasileiro, maxLen=12)
  cubagem      -> Cubagem m3 (formato brasileiro, maxLen=12)

CEP ORIGEM — REGRA CRITICA:
  coletar=S -> CEP origem = endereco do CLIENTE (CarVia coleta la)
  coletar=N -> CEP origem = CEP da CARVIA (cliente entrega na CarVia)
  O CEP da CarVia esta em ssw_defaults.json -> endereco_fiscal.cep

RESULTADOS (readOnly, preenchidos apos calcula('S')):
  fretepeso, fretevalor(=Ad Valorem/seguro), despacho, gris,
  coleta, ent_geral, pedagio, tas, tdc, entrega(=TDE), tar, trt,
  adic_local(=TDA), pos, cat, itr, dev_canh, co2, rdc, agend_ent,
  veic_dedic, separacao, paletizacao, capatazia, adic_frete, suframa,
  seguro_fluvial, redesp_fluvial, reembolso, impostos,
  vlr_frete (total proposta)

Uso:
    python cotar_frete_ssw_002.py \\
      --cnpj-pagador 33119545000251 \\
      --cep-origem 06530581 --cep-destino 26020157 \\
      --peso 1894.405 --valor 14649.73 \\
      [--frete CIF] [--coletar N] [--entregar S] \\
      [--contribuinte S] [--cubagem 0] [--dry-run] [--discover]

Retorno: JSON {"sucesso": bool, "cotacao": {...}, "proposta": {...},
               "indicadores": {...}, "parametros_assumidos": {...}, ...}
"""
import argparse
import asyncio
import json
import os
import sys

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
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
)


# ──────────────────────────────────────────────
# Field mapping: parametro CLI -> nome do campo SSW
# (descoberto via --discover em 2026-02-19)
# ──────────────────────────────────────────────
FIELD_MAP = {
    "cnpj_pagador": "cgc_pag",        # CNPJ pagador, maxLen=14
    "tipo_frete": "tp_frete",          # 1=CIF, 2=FOB, maxLen=1
    "cep_origem": "cep_origem",        # CEP origem, maxLen=8
    "cep_destino": "cep_destino",      # CEP destino, maxLen=8
    "coletar": "coletar",              # S/N, maxLen=1
    "entregar": "entregar",            # S/N, maxLen=1
    "valor_mercadoria": "vlr_merc",    # R$ formato BR, maxLen=15
    "peso": "peso",                    # kg formato BR, maxLen=12
    "cubagem": "cubagem",              # m3 formato BR, maxLen=12
    "contribuinte": "contribuinte",    # S/N, maxLen=1
}

# Campos de resultado (readOnly, preenchidos apos calcula('S'))
# Agrupados por categoria para facilitar apresentacao
RESULT_FIELDS_TRANSPORTE = {
    "frete_peso": "fretepeso",         # Frete por peso (principal)
    "despacho": "despacho",            # Taxa despacho/CTE
}

RESULT_FIELDS_SEGUROS = {
    "ad_valorem": "fretevalor",        # Ad Valorem = seguro sobre valor NF
    "gris": "gris",                    # Gerenciamento de Risco
    "seguro_fluvial": "seguro_fluvial",
}

RESULT_FIELDS_TAXAS = {
    "coleta": "coleta",
    "entrega_geral": "ent_geral",
    "pedagio": "pedagio",
    "tas": "tas",                      # Taxa de Administracao de Seguro
    "tdc": "tdc",                      # Taxa de Dificuldade de Coleta
    "tde": "entrega",                  # Taxa de Dificuldade de Entrega
    "tar": "tar",                      # Taxa de Armazenagem
    "trt": "trt",                      # Taxa de Reentrega/Retorno
    "tda": "adic_local",               # Taxa de Dificuldade de Acesso
    "pos": "pos",
    "cat": "cat",                      # Capatazia (porto)
    "itr": "itr",                      # ITR
    "devol_canhoto": "dev_canh",
    "co2": "co2",
    "rdc": "rdc",
    "agendamento": "agend_ent",
    "veic_dedicado": "veic_dedic",
    "separacao": "separacao",
    "paletizacao": "paletizacao",
    "capatazia": "capatazia",
    "adic_frete": "adic_frete",
    "suframa": "suframa",
    "redesp_fluvial": "redesp_fluvial",
    "reembolso": "reembolso",
}

RESULT_FIELDS_IMPOSTOS = {
    "impostos": "impostos",            # Imposto repassado
}

RESULT_FIELDS_TOTAIS = {
    "total_frete": "vlr_frete",        # Total da proposta
    "tabela_ntc": "ntc",               # Valor NTC (referencia)
    "tributacao": "tributacao",         # Tributacao da proposta
    "base_calculo": "base_tribut",     # Base de calculo
}

RESULT_FIELDS_INDICADORES = {
    "frete_por_kg": "percfretepeso",
    "frete_sobre_merc_pct": "percfretemerc",
    "desc_ntc_pct": "descatual",
    "rc_pct": "rcatual",
    "rota": "rota",
}

# Todos combinados (para captura)
ALL_RESULT_FIELDS = {}
ALL_RESULT_FIELDS.update(RESULT_FIELDS_TRANSPORTE)
ALL_RESULT_FIELDS.update(RESULT_FIELDS_SEGUROS)
ALL_RESULT_FIELDS.update(RESULT_FIELDS_TAXAS)
ALL_RESULT_FIELDS.update(RESULT_FIELDS_IMPOSTOS)
ALL_RESULT_FIELDS.update(RESULT_FIELDS_TOTAIS)
ALL_RESULT_FIELDS.update(RESULT_FIELDS_INDICADORES)

# Campos informativos (readOnly, preenchidos apos CEP lookup)
INFO_FIELDS = {
    "cidade_origem": "cidadeori",
    "cidade_destino": "cidadedest",
    "unid_coleta": "unid_col",
    "unid_entrega": "unid_ent",
    "dias_entrega": "dias_entrega",
    "prev_entrega": "prev_ent",
    "peso_calculo": "pesocalculo",
}


# ──────────────────────────────────────────────
# Validacoes
# ──────────────────────────────────────────────
def validar_campos(args):
    """Valida parametros de entrada. Retorna lista de erros.
    Campos opcionais (None) sao ignorados — serao resolvidos por montar_parametros."""
    erros = []

    # CNPJ
    if args.cnpj_pagador:
        cnpj = args.cnpj_pagador.replace(".", "").replace("/", "").replace("-", "")
        if not cnpj.isdigit() or len(cnpj) != 14:
            erros.append(f"cnpj-pagador: deve ter 14 digitos (recebido: '{args.cnpj_pagador}')")

    # CEPs (cep_origem pode ser None — sera resolvido pelo defaults quando coletar=N)
    if args.cep_origem:
        cep = args.cep_origem.replace("-", "")
        if not cep.isdigit() or len(cep) != 8:
            erros.append(f"cep-origem: deve ter 8 digitos (recebido: '{args.cep_origem}')")
    if args.cep_destino:
        cep = args.cep_destino.replace("-", "")
        if not cep.isdigit() or len(cep) != 8:
            erros.append(f"cep-destino: deve ter 8 digitos (recebido: '{args.cep_destino}')")

    # Peso
    if args.peso is not None and args.peso <= 0:
        erros.append(f"peso: deve ser positivo (recebido: {args.peso})")

    # Valor
    if args.valor is not None and args.valor <= 0:
        erros.append(f"valor: deve ser positivo (recebido: {args.valor})")

    # Frete (pode ser None — sera resolvido pelo defaults)
    if args.frete and args.frete.upper() not in ("CIF", "FOB"):
        erros.append(f"frete: deve ser CIF ou FOB (recebido: '{args.frete}')")

    # Coletar/Entregar/Contribuinte (podem ser None — serao resolvidos pelo defaults)
    for nome, valor in [
        ("coletar", args.coletar),
        ("entregar", args.entregar),
        ("contribuinte", args.contribuinte),
    ]:
        if valor is not None and valor.upper() not in ("S", "N"):
            erros.append(f"{nome}: deve ser S ou N (recebido: '{valor}')")

    # Cubagem
    if args.cubagem is not None and args.cubagem < 0:
        erros.append(f"cubagem: deve ser >= 0 (recebido: {args.cubagem})")

    return erros


def formatar_br(valor, casas=2):
    """Formata numero para formato brasileiro (virgula decimal, ponto milhar)."""
    formatted = f"{valor:,.{casas}f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def parse_br(valor_str):
    """Converte string formato brasileiro para float. Retorna 0.0 se invalido."""
    if not valor_str or not valor_str.strip():
        return 0.0
    try:
        return float(valor_str.strip().replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return 0.0


def agrupar_proposta(all_values):
    """
    Agrupa campos de resultado em categorias para apresentacao clara.
    Retorna dict com transporte, seguros, taxas, impostos, totais, indicadores.
    Campos com valor 0,00 sao incluidos mas marcados.
    """
    def extrair(mapping):
        result = {}
        for nome in mapping:
            val_str = all_values.get(nome, "0,00")
            result[nome] = val_str
        return result

    return {
        "transporte": extrair(RESULT_FIELDS_TRANSPORTE),
        "seguros": extrair(RESULT_FIELDS_SEGUROS),
        "taxas": extrair(RESULT_FIELDS_TAXAS),
        "impostos": extrair(RESULT_FIELDS_IMPOSTOS),
        "totais": extrair(RESULT_FIELDS_TOTAIS),
        "indicadores": extrair(RESULT_FIELDS_INDICADORES),
    }


def calcular_indicadores_extras(proposta_flat, valor_nf):
    """Calcula indicadores adicionais a partir da proposta."""
    total = parse_br(proposta_flat.get("total_frete", "0"))
    ad_valorem = parse_br(proposta_flat.get("ad_valorem", "0"))
    gris = parse_br(proposta_flat.get("gris", "0"))

    indicadores = {}
    if valor_nf > 0 and ad_valorem > 0:
        indicadores["ad_valorem_pct"] = f"{(ad_valorem / valor_nf) * 100:.2f}%"
    if valor_nf > 0 and gris > 0:
        indicadores["gris_pct"] = f"{(gris / valor_nf) * 100:.2f}%"
    if valor_nf > 0 and total > 0:
        indicadores["seguro_total"] = formatar_br(ad_valorem + gris, 2)
        indicadores["seguro_total_pct"] = f"{((ad_valorem + gris) / valor_nf) * 100:.2f}%"

    return indicadores


# ──────────────────────────────────────────────
# Funcoes auxiliares
# ──────────────────────────────────────────────
CREATE_NEW_DOC_OVERRIDE = """() => {
    createNewDoc = function(pathname) {
        document.open("text/html", "replace");
        document.write(valSep.toString());
        document.close();
        if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
    };
}"""


def montar_parametros(args, defaults):
    """
    Monta parametros completos mesclando CLI + defaults.
    Retorna (campos, parametros_assumidos).
    parametros_assumidos lista o que foi assumido sem o usuario informar.
    """
    d002 = defaults.get("opcao_002", {})
    cep_carvia = defaults.get("endereco_fiscal", {}).get("cep", "")

    campos = {}
    assumidos = {}

    # ── Obrigatorios (sempre do CLI) ──
    campos["cnpj_pagador"] = args.cnpj_pagador.replace(".", "").replace("/", "").replace("-", "")
    campos["cep_destino"] = args.cep_destino.replace("-", "")
    campos["peso"] = args.peso
    campos["valor"] = args.valor

    # ── CEP Origem: logica especial baseada em coletar ──
    coletar = (args.coletar or d002.get("coletar", "S")).upper()
    if args.cep_origem:
        campos["cep_origem"] = args.cep_origem.replace("-", "")
    elif coletar == "N" and cep_carvia:
        # Cliente entrega na CarVia -> origem = CEP CarVia
        campos["cep_origem"] = cep_carvia.replace("-", "")
        assumidos["cep_origem"] = f"{cep_carvia} (CEP CarVia — coletar=N, cliente entrega na CarVia)"
    else:
        campos["cep_origem"] = ""  # Ficara faltando, validacao vai pegar

    # ── Opcionais com defaults ──
    frete = (args.frete or d002.get("frete", "CIF")).upper()
    campos["frete"] = frete
    if not args.frete or args.frete == "CIF":
        assumidos["frete"] = f"{frete} (emitente paga o frete)"

    campos["coletar"] = coletar
    if not args.coletar or args.coletar == d002.get("coletar", "S"):
        desc_col = "CarVia coleta no cliente" if coletar == "S" else "Cliente entrega na CarVia"
        assumidos["coletar"] = f"{coletar} ({desc_col})"

    entregar = (args.entregar or d002.get("entregar", "S")).upper()
    campos["entregar"] = entregar
    if not args.entregar or args.entregar == d002.get("entregar", "S"):
        desc_ent = "CarVia entrega no destino" if entregar == "S" else "Destino retira"
        assumidos["entregar"] = f"{entregar} ({desc_ent})"

    contribuinte = (args.contribuinte or d002.get("contribuinte", "S")).upper()
    campos["contribuinte"] = contribuinte
    if not args.contribuinte or args.contribuinte == d002.get("contribuinte", "S"):
        desc_cont = "Destinatario contribuinte ICMS" if contribuinte == "S" else "Destinatario NAO contribuinte"
        assumidos["contribuinte"] = f"{contribuinte} ({desc_cont})"

    campos["cubagem"] = args.cubagem  # None = SSW calcula automatico
    if args.cubagem is None:
        assumidos["cubagem"] = "automatico (SSW calcula pelo peso)"

    return campos, assumidos


async def descobrir_campos(_args=None):
    """
    Modo --discover: abre a opcao 002, clica NEW e lista todos os campos.
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

            popup = await abrir_opcao_popup(context, page.frames[0], 2)
            await asyncio.sleep(2)

            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            screenshot_inicial = await capturar_screenshot(popup, "002_tela_inicial")

            html_new = await interceptar_ajax_response(
                popup, popup, "ajaxEnvia('NEW', 1)", timeout_s=15
            )

            if not html_new:
                return gerar_saida(
                    False,
                    erro="Timeout ao abrir formulario NEW na 002",
                    screenshot=screenshot_inicial,
                )

            await injetar_html_no_dom(popup, html_new)
            await asyncio.sleep(1)
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            screenshot_form = await capturar_screenshot(popup, "002_formulario_inclusao")
            campos_form = await capturar_campos(popup)

            botoes = await popup.evaluate("""() => {
                const r = [];
                document.querySelectorAll('a[onclick]').forEach(el => {
                    r.push({
                        text: el.textContent.trim().substring(0, 100),
                        onclick: el.getAttribute('onclick').substring(0, 200),
                        id: el.id || ''
                    });
                });
                return r;
            }""")

            return gerar_saida(
                True,
                modo="discover",
                formulario=campos_form,
                botoes=botoes,
                screenshot_inicial=screenshot_inicial,
                screenshot_formulario=screenshot_form,
            )

        finally:
            await browser.close()


async def cotar_frete(args):
    """
    Fluxo principal de cotacao de frete no SSW 002.

    1. Login -> 2. Abrir 002 -> 3. NEW -> 4. Preencher -> 5. Simular -> 6. Capturar
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()
    defaults = carregar_defaults(args.defaults_file)
    campos, parametros_assumidos = montar_parametros(args, defaults)

    cnpj = campos["cnpj_pagador"]
    cep_ori = campos["cep_origem"]
    cep_dest = campos["cep_destino"]
    frete = campos["frete"]
    tp_frete = "1" if frete == "CIF" else "2"
    coletar = campos["coletar"]
    entregar = campos["entregar"]
    contribuinte = campos["contribuinte"]

    # Formatar valores para formato brasileiro
    peso_str = formatar_br(campos["peso"], 3)
    valor_str = formatar_br(campos["valor"], 2)
    cubagem_str = formatar_br(campos["cubagem"], 4) if campos["cubagem"] is not None else None

    # Validar
    erros = validar_campos(args)
    if not cep_ori:
        erros.append("cep-origem: obrigatorio (informar --cep-origem ou usar coletar=N para CEP CarVia)")
    if erros:
        return gerar_saida(
            False,
            erro="Parametros invalidos",
            erros_validacao=erros,
            parametros_assumidos=parametros_assumidos,
        )

    cotacao_input = {
        "cnpj_pagador": cnpj,
        "cep_origem": cep_ori,
        "cep_destino": cep_dest,
        "peso_kg": campos["peso"],
        "valor_nf": campos["valor"],
        "frete": frete,
        "coletar": coletar,
        "entregar": entregar,
        "contribuinte": contribuinte,
        "cubagem": campos["cubagem"],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        try:
            # ── 1. Login ──
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            # ── 2. Abrir opcao 002 (popup) ──
            popup = await abrir_opcao_popup(context, page.frames[0], 2)
            await asyncio.sleep(2)

            # ── 3. Override createNewDoc ──
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            # ── 4. Abrir formulario de nova cotacao ──
            html_new = await interceptar_ajax_response(
                popup, popup, "ajaxEnvia('NEW', 1)", timeout_s=15
            )

            if not html_new:
                screenshot = await capturar_screenshot(popup, "002_new_falhou")
                return gerar_saida(
                    False,
                    erro="Timeout ao abrir formulario de nova cotacao (NEW) na 002",
                    screenshot=screenshot,
                )

            await injetar_html_no_dom(popup, html_new)
            await asyncio.sleep(1)
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            # ── 5. Preencher campos ──
            campos_preenchidos = {}
            campos_erros = []

            async def preencher(nome_cli, campo_ssw, valor):
                result = await preencher_campo_js(popup, campo_ssw, valor)
                if not result.get("found"):
                    campos_erros.append(f"{nome_cli} ({campo_ssw}): campo nao encontrado")
                elif result.get("readonly"):
                    campos_erros.append(
                        f"{nome_cli} ({campo_ssw}): readonly, atual='{result.get('current', '')}'"
                    )
                else:
                    campos_preenchidos[nome_cli] = valor

            await preencher("cnpj_pagador", "cgc_pag", cnpj)
            await preencher("tipo_frete", "tp_frete", tp_frete)
            await preencher("coletar", "coletar", coletar)
            await preencher("entregar", "entregar", entregar)
            await preencher("cep_origem", "cep_origem", cep_ori)
            await preencher("cep_destino", "cep_destino", cep_dest)
            await preencher("valor_mercadoria", "vlr_merc", valor_str)
            await preencher("peso", "peso", peso_str)
            await preencher("contribuinte", "contribuinte", contribuinte)

            if cubagem_str:
                await preencher("cubagem", "cubagem", cubagem_str)

            # ── 6. Screenshot pre-simulacao ──
            screenshot_pre = await capturar_screenshot(
                popup, f"002_{'dryrun' if args.dry_run else 'presim'}_{cnpj}"
            )

            if args.dry_run:
                return gerar_saida(
                    True,
                    modo="dry-run",
                    cotacao=cotacao_input,
                    parametros_assumidos=parametros_assumidos,
                    campos_preenchidos=campos_preenchidos,
                    campos_erros=campos_erros,
                    screenshot=screenshot_pre,
                    mensagem="Preview da cotacao. Nenhuma simulacao foi executada.",
                )

            # ── 7. Simular via calcula('S') ──
            alert_msg = None

            async def on_dialog(dialog):
                nonlocal alert_msg
                alert_msg = dialog.message
                await dialog.accept()

            popup.on("dialog", on_dialog)

            try:
                await popup.evaluate("calcula('S')")

                resultado_ok = False
                for _ in range(40):  # 20 segundos
                    await asyncio.sleep(0.5)
                    if alert_msg:
                        break
                    check = await popup.evaluate("""() => {
                        const fp = document.getElementById('fretepeso');
                        const vf = document.getElementById('vlr_frete');
                        const fpVal = fp ? fp.value : '';
                        const vfVal = vf ? vf.value : '';
                        return {
                            fretepeso: fpVal,
                            vlr_frete: vfVal,
                            has_result: (fpVal && fpVal !== '0,00') || (vfVal && vfVal !== '')
                        };
                    }""")
                    if check.get("has_result"):
                        resultado_ok = True
                        break

                # ── 8. Capturar resultado ──
                screenshot_resultado = await capturar_screenshot(
                    popup, f"002_resultado_{cnpj}"
                )

                if alert_msg:
                    return gerar_saida(
                        False,
                        erro=f"SSW alert: {alert_msg}",
                        cotacao=cotacao_input,
                        parametros_assumidos=parametros_assumidos,
                        campos_preenchidos=campos_preenchidos,
                        campos_erros=campos_erros,
                        screenshot=screenshot_resultado,
                    )

                # Capturar todos os campos de resultado
                proposta_flat = {}
                for nome_result, campo_ssw in ALL_RESULT_FIELDS.items():
                    val = await popup.evaluate(f"""() => {{
                        const el = document.getElementById('{campo_ssw}');
                        return el ? el.value || el.textContent || '' : '';
                    }}""")
                    if val and val.strip():
                        proposta_flat[nome_result] = val.strip()

                # Capturar campos informativos
                info = {}
                for nome_info, campo_ssw in INFO_FIELDS.items():
                    val = await popup.evaluate(f"""() => {{
                        const el = document.getElementById('{campo_ssw}');
                        return el ? el.value || el.textContent || '' : '';
                    }}""")
                    if val and val.strip():
                        info[nome_info] = val.strip()

                if not resultado_ok and not proposta_flat:
                    body_text = await popup.evaluate(
                        "() => document.body ? document.body.innerText.substring(0, 2000) : ''"
                    )
                    return gerar_saida(
                        False,
                        erro="Simulacao nao retornou resultado em 20 segundos",
                        body_text=body_text,
                        cotacao=cotacao_input,
                        parametros_assumidos=parametros_assumidos,
                        campos_preenchidos=campos_preenchidos,
                        campos_erros=campos_erros,
                        screenshot=screenshot_resultado,
                    )

                # Agrupar proposta por categoria
                proposta_agrupada = agrupar_proposta(proposta_flat)

                # Indicadores extras calculados
                indicadores_extras = calcular_indicadores_extras(
                    proposta_flat, campos["valor"]
                )

                # Enriquecer cotacao_input com info de cidades
                cotacao_input["origem"] = info.get("cidade_origem", f"CEP {cep_ori}")
                cotacao_input["destino"] = info.get("cidade_destino", f"CEP {cep_dest}")

                return gerar_saida(
                    True,
                    cotacao=cotacao_input,
                    proposta=proposta_agrupada,
                    proposta_flat=proposta_flat,
                    indicadores=indicadores_extras,
                    info=info,
                    parametros_assumidos=parametros_assumidos,
                    campos_preenchidos=campos_preenchidos,
                    campos_erros=campos_erros,
                    screenshot=screenshot_resultado,
                )

            finally:
                try:
                    popup.remove_listener("dialog", on_dialog)
                except Exception:
                    pass

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Cotacao de frete no SSW (opcao 002)"
    )

    # Modo discover (exclusivo)
    parser.add_argument(
        "--discover", action="store_true",
        help="Modo exploratorio: abre formulario e lista campos"
    )

    # Parametros obrigatorios (exceto em modo discover)
    parser.add_argument(
        "--cnpj-pagador", default=None,
        help="CNPJ do cliente pagador (14 digitos)"
    )
    parser.add_argument(
        "--cep-origem", default=None,
        help="CEP origem. REGRA: coletar=S -> CEP cliente. coletar=N -> CEP CarVia (auto do defaults)"
    )
    parser.add_argument(
        "--cep-destino", default=None,
        help="CEP de entrega/destino (8 digitos)"
    )
    parser.add_argument(
        "--peso", type=float, default=None,
        help="Peso em kg"
    )
    parser.add_argument(
        "--valor", type=float, default=None,
        help="Valor da mercadoria em R$"
    )

    # Parametros opcionais (com defaults do ssw_defaults.json)
    parser.add_argument(
        "--frete", default=None,
        help="CIF ou FOB (default: CIF do ssw_defaults.json)"
    )
    parser.add_argument(
        "--coletar", default=None,
        help="S=CarVia coleta, N=cliente entrega na CarVia (default: S)"
    )
    parser.add_argument(
        "--entregar", default=None,
        help="S=CarVia entrega, N=destino retira (default: S)"
    )
    parser.add_argument(
        "--contribuinte", default=None,
        help="S/N destinatario contribuinte ICMS (default: S)"
    )
    parser.add_argument(
        "--cubagem", type=float, default=None,
        help="Cubagem em m3 (SSW calcula automatico se omitido)"
    )
    parser.add_argument(
        "--defaults-file",
        default=os.path.join(SCRIPT_DIR, "..", "ssw_defaults.json"),
        help="Caminho para ssw_defaults.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preenche formulario sem simular"
    )

    args = parser.parse_args()

    # Modo discover
    if args.discover:
        asyncio.run(descobrir_campos())
        return

    # Validar parametros obrigatorios
    faltando = []
    if not args.cnpj_pagador:
        faltando.append("--cnpj-pagador")
    if not args.cep_destino:
        faltando.append("--cep-destino")
    if args.peso is None:
        faltando.append("--peso")
    if args.valor is None:
        faltando.append("--valor")
    # CEP origem NAO e obrigatorio se coletar=N (usa CEP CarVia do defaults)

    if faltando:
        print(json.dumps({
            "sucesso": False,
            "erro": f"Parametros obrigatorios faltando: {', '.join(faltando)}"
        }, ensure_ascii=False))
        sys.exit(1)

    # Validar valores
    erros = validar_campos(args)
    if erros:
        print(json.dumps({
            "sucesso": False,
            "erro": "Parametros invalidos",
            "erros_validacao": erros
        }, ensure_ascii=False))
        sys.exit(1)

    asyncio.run(cotar_frete(args))


if __name__ == "__main__":
    main()
