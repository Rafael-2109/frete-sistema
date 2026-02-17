#!/usr/bin/env python3
"""
cadastrar_unidade_401.py — Cadastra nova unidade operacional no SSW (opcao 401).

Fluxo:
  1. Login SSW
  2. Abre opcao 401 (popup)
  3. Verifica se sigla ja existe (PES)
  4. Executa INC (Incluir) para formulario vazio
  5. Preenche campos (defaults CarVia + parametros CLI)
  6. --dry-run: captura preview sem submeter
  7. Sem flag: submete (GRA) e verifica sucesso

Uso:
    python cadastrar_unidade_401.py \
      --sigla CGR --tipo T \
      --razao-social "ALEMAR - CAMPO GRANDE/MS" \
      --nome-fantasia "ALEMAR CGR" \
      --ie "ISENTO" \
      [--cnpj 62312605000175] \
      [--defaults-file ../ssw_defaults.json] \
      [--dry-run]

Retorno: JSON {"sucesso": bool, "sigla": "...", ...}

Mapeamento de campos (fonte: /tmp/ssw_401_completo/401_PES_CAR.html):
  sigla          → name="sigla" (READONLY em PES, editavel em INC)
  f1             → Ativa (S/N)
  f3             → Tipo da Unidade (T/F/M)
  f7             → Nome Fantasia (30 chars)
  f37            → Razao Social (45 chars)
  f38            → CNPJ (14 chars)
  f45            → Inscricao Estadual (20 chars)
  f44            → Regime PIS/COFINS (C/N)
  fld_aereo      → Aereo (S/N)
  fld_rodoviario → Rodoviario (S/N)
  f4             → Aquaviaria (S/N)
  f32/f33/f34/f35/f36 → Banco/Ag/DV/Conta/DV
  f29            → Seguro RCTRC apolice
  cnpj_seguradora → CNPJ seguradora
  f41            → RNTRC
  cod_emp_ctb    → Empresa contabil
  sigla_mtz_ctb  → Matriz contabil
  * NAO ha campo UF explicito — UF vem do CEP (f14) ou IE (f45)
"""
import argparse
import asyncio
import json
import os
import re
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
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
    verificar_mensagem_ssw,
)


# ──────────────────────────────────────────────
# Field mapping: parametro → nome do campo SSW
# ──────────────────────────────────────────────
FIELD_MAP = {
    # Dados Basicos
    "ativa": "f1",
    "tipo": "f3",
    "nome_fantasia": "f7",
    "razao_social": "f37",
    # Modalidades
    "aereo": "fld_aereo",
    "rodoviario": "fld_rodoviario",
    "aquaviaria": "f4",
    # Dados Fiscais
    "cnpj": "f38",
    "ie": "f45",
    "regime_pis_cofins": "f44",
    "rntrc": "f41",
    # Empresa contabil
    "cod_emp_ctb": "cod_emp_ctb",
    "sigla_mtz_ctb": "sigla_mtz_ctb",
    # Seguro
    "rctrc_apolice": "f29",
    "cnpj_seguradora": "cnpj_seguradora",
    # Dados Bancarios
    "banco": "f32",
    "agencia": "f33",
    "dv_agencia": "f34",
    "conta": "f35",
    "dv_conta": "f36",
    # Configuracoes operacionais (S/N)
    "imprime_fatura": "f18",
    "gera_fatura_bloqueto": "f19",
    "arquiva_comprovante": "f20",
    "imprime_subcontrato": "f21",
    "romaneio_gera_damdfe": "f22",
    "possui_almoxarifado": "f23",
    "cobra_frete_avista": "fld_cobra_ctrc_avista",
    "impedir_cfop_5932_6932": "troca_fil_orig",
    "debita_auto_frete_avista": "f24",
    "cobra_agencia_via_fat": "fg_cobra_agen_via_fat",
    "servico_logistica": "f25",
}

# ──────────────────────────────────────────────
# Field limits: maxlength real de cada campo SSW
# Fonte: /tmp/ssw_401_completo/401_PES_CAR.html
# ──────────────────────────────────────────────
FIELD_LIMITS = {
    # Dados basicos
    "tipo": 1,               # f3: T/F/M
    "nome_fantasia": 30,     # f7
    "razao_social": 45,      # f37
    # Fiscais
    "cnpj": 14,              # f38
    "ie": 20,                # f45
    "regime_pis_cofins": 1,  # f44: N/C
    "rntrc": 14,             # f41
    # Empresa contabil
    "cod_emp_ctb": 2,        # cod_emp_ctb
    "sigla_mtz_ctb": 3,      # sigla_mtz_ctb
    # Modalidades
    "aereo": 1,              # fld_aereo: S/N
    "rodoviario": 1,         # fld_rodoviario: S/N
    "aquaviaria": 1,         # f4: S/N
    # Seguro
    "rctrc_apolice": 30,     # f29
    "cnpj_seguradora": 14,   # cnpj_seguradora
    # Banco
    "banco": 3,              # f32
    "agencia": 5,            # f33
    "dv_agencia": 1,         # f34
    "conta": 10,             # f35
    "dv_conta": 2,           # f36
    # Flags operacionais (todos 1 char: S/N)
    "ativa": 1,
    "imprime_fatura": 1,
    "gera_fatura_bloqueto": 1,
    "arquiva_comprovante": 1,
    "imprime_subcontrato": 1,
    "romaneio_gera_damdfe": 1,
    "possui_almoxarifado": 1,
    "cobra_frete_avista": 1,
    "impedir_cfop_5932_6932": 1,
    "debita_auto_frete_avista": 1,
    "cobra_agencia_via_fat": 1,
    "servico_logistica": 1,
}

# Opcoes validas para campos com dominio restrito
VALID_OPTIONS = {
    "tipo": ["T", "F", "M"],
    "ativa": ["S", "N"],
    "aereo": ["S", "N"],
    "rodoviario": ["S", "N"],
    "aquaviaria": ["S", "N"],
    "regime_pis_cofins": ["N", "C"],  # N=Nao cumulativo, C=Cumulativo
    "imprime_fatura": ["S", "N"],
    "gera_fatura_bloqueto": ["S", "N"],
    "arquiva_comprovante": ["S", "N"],
    "imprime_subcontrato": ["S", "N"],
    "romaneio_gera_damdfe": ["S", "N"],
    "possui_almoxarifado": ["S", "N"],
    "cobra_frete_avista": ["S", "N"],
    "impedir_cfop_5932_6932": ["S", "N"],
    "debita_auto_frete_avista": ["S", "N"],
    "cobra_agencia_via_fat": ["S", "N"],
    "servico_logistica": ["S", "N"],
}


def validar_campos(campos):
    """Valida campos contra FIELD_LIMITS e VALID_OPTIONS. Retorna lista de erros."""
    erros = []
    for param, value in campos.items():
        # Checar maxlength
        limit = FIELD_LIMITS.get(param)
        if limit and len(str(value)) > limit:
            erros.append(
                f"{param}: valor '{value}' excede limite de {limit} chars "
                f"(tem {len(str(value))})"
            )
        # Checar opcoes validas
        options = VALID_OPTIONS.get(param)
        if options and str(value).upper() not in options:
            erros.append(
                f"{param}: valor '{value}' invalido. Opcoes: {', '.join(options)}"
            )
    return erros


def montar_campos(args, defaults):
    """Monta dict completo de campos a preencher, mesclando CLI + defaults."""
    d401 = defaults.get("opcao_401", {})
    empresa = defaults.get("empresa", {})
    seguro = defaults.get("seguro", {})
    banco = defaults.get("banco", {})

    campos = {}

    # 1. Dados Basicos (CLI tem prioridade)
    campos["tipo"] = args.tipo
    campos["razao_social"] = args.razao_social
    campos["nome_fantasia"] = args.nome_fantasia or args.razao_social[:30]
    campos["cnpj"] = args.cnpj or empresa.get("cnpj", "")
    campos["ie"] = args.ie or empresa.get("ie", "")

    # 2. Defaults da opcao 401
    campos["ativa"] = d401.get("ativa", "S")
    campos["aereo"] = d401.get("aereo", "N")
    campos["rodoviario"] = d401.get("rodoviario", "S")
    campos["aquaviaria"] = d401.get("aquaviaria", "N")
    campos["regime_pis_cofins"] = d401.get("regime_pis_cofins", "N")
    campos["imprime_fatura"] = d401.get("imprime_fatura", "N")
    campos["gera_fatura_bloqueto"] = d401.get("gera_fatura_bloqueto", "N")
    campos["arquiva_comprovante"] = d401.get("arquiva_comprovante", "N")
    campos["imprime_subcontrato"] = d401.get("imprime_subcontrato", "S")
    campos["romaneio_gera_damdfe"] = d401.get("romaneio_gera_damdfe", "N")
    campos["possui_almoxarifado"] = d401.get("possui_almoxarifado", "N")
    campos["cobra_frete_avista"] = d401.get("cobra_frete_avista", "S")
    campos["impedir_cfop_5932_6932"] = d401.get("impedir_cfop_5932_6932", "N")
    campos["debita_auto_frete_avista"] = d401.get("debita_auto_frete_avista", "N")
    campos["cobra_agencia_via_fat"] = d401.get("cobra_agencia_via_fat", "N")
    campos["servico_logistica"] = d401.get("servico_logistica", "N")

    # 3. Empresa
    campos["cod_emp_ctb"] = empresa.get("codigo_empresa_ctb", "")
    campos["sigla_mtz_ctb"] = empresa.get("sigla_mtz_ctb", "")
    campos["rntrc"] = empresa.get("rntrc", "")

    # 4. Seguro
    campos["rctrc_apolice"] = seguro.get("rctrc_apolice") or ""
    campos["cnpj_seguradora"] = seguro.get("cnpj_seguradora") or ""

    # 5. Banco
    campos["banco"] = banco.get("codigo") or ""
    campos["agencia"] = banco.get("agencia") or ""
    campos["dv_agencia"] = banco.get("dv_agencia") or ""
    campos["conta"] = banco.get("conta") or ""
    campos["dv_conta"] = banco.get("dv_conta") or ""

    # Remover campos vazios (nao preencher o que nao tem valor)
    return {k: v for k, v in campos.items() if v}


async def preencher_campo_js(popup, field_name, value):
    """
    Preenche campo via JS direto no DOM atualizado pelo AJAX.

    Tenta por name primeiro, depois por id. Respeita campos readonly.

    Returns:
        dict com {found: bool, readonly: bool, current: str, set: str}
    """
    escaped_value = str(value).replace("\\", "\\\\").replace("'", "\\'")
    result = await popup.evaluate(f"""() => {{
        let el = document.querySelector('input[name="{field_name}"], select[name="{field_name}"]');
        if (!el) el = document.getElementById('{field_name}');
        if (!el) return {{found: false}};
        if (el.readOnly || el.className === 'nodata') return {{found: true, readonly: true, current: el.value}};
        el.value = '{escaped_value}';
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        return {{found: true, readonly: false, set: '{escaped_value}'}};
    }}""")
    return result


async def cadastrar_unidade(args):
    from playwright.async_api import async_playwright

    verificar_credenciais()
    defaults = carregar_defaults(args.defaults_file)
    campos = montar_campos(args, defaults)
    sigla = args.sigla.upper()

    # Validar campos antes de tentar preencher
    erros_validacao = validar_campos(campos)
    if erros_validacao:
        return gerar_saida(
            False,
            erro="Campos invalidos",
            erros_validacao=erros_validacao,
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        try:
            # ── 1. Login ──
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            # ── 2. Abrir opcao 401 (popup) ──
            popup = await abrir_opcao_popup(context, page.frames[0], 401)
            frame = popup.frames[0]

            # ── 3. Pesquisar sigla (PES) ──
            await frame.fill('input[name="f2"]', sigla)
            pes_html = await interceptar_ajax_response(
                popup, frame, "ajaxEnvia('PES', 1)", timeout_s=15
            )

            if not pes_html:
                screenshot = await capturar_screenshot(popup, f"401_pes_falhou_{sigla}")
                return gerar_saida(
                    False,
                    erro="Nao recebeu resposta PES da opcao 401",
                    sigla=sigla,
                    screenshot=screenshot,
                )

            # Detectar existencia: se f37 (razao_social) tem valor nao-vazio,
            # o registro existe. O campo de busca sempre contem a sigla digitada,
            # entao checar pela sigla no HTML causa falso positivo.
            sigla_existe = False
            f37_match = re.search(
                r'name="f37"[^>]*value="([^"]*)"', pes_html
            )
            if f37_match and f37_match.group(1).strip():
                sigla_existe = True

            if sigla_existe:
                await injetar_html_no_dom(popup, pes_html)
                screenshot = await capturar_screenshot(popup, f"401_ja_existe_{sigla}")
                return gerar_saida(
                    False,
                    erro=f"Sigla {sigla} ja existe no SSW. Escolha outra sigla.",
                    sigla=sigla,
                    screenshot=screenshot,
                )

            # ── 4. Injetar HTML no DOM ──
            # SSW's ajaxEnvia faz AJAX POST e recebe HTML completo, mas o mecanismo
            # nativo de substituicao do DOM nao funciona em Playwright headless.
            # Injetamos o HTML interceptado manualmente via document.write().
            await injetar_html_no_dom(popup, pes_html)

            # Verificar modo do formulario injetado
            form_info = await popup.evaluate("""() => {
                const tipo = document.querySelector('input[name="tipo"]');
                const inputCount = document.querySelectorAll('input:not([type="hidden"])').length;
                return {
                    tipo: tipo ? tipo.value : null,
                    inputCount: inputCount,
                };
            }""")

            # PES para sigla inexistente retorna formulario em modo inclusao
            # (tipo=inclusao, acao=I). Se nao, chamar INC explicitamente.
            if form_info.get("tipo") != "inclusao" or form_info.get("inputCount", 0) < 20:
                inc_html = await interceptar_ajax_response(
                    popup, popup.main_frame, "ajaxEnvia('INC', 1)", timeout_s=15
                )
                if inc_html:
                    await injetar_html_no_dom(popup, inc_html)
                else:
                    screenshot = await capturar_screenshot(popup, f"401_inc_falhou_{sigla}")
                    return gerar_saida(
                        False,
                        erro="Nao foi possivel carregar formulario de inclusao 401",
                        sigla=sigla,
                        screenshot=screenshot,
                    )

            # ── 5. Forcar sigla no campo ──
            # Apos PES, sigla pode ser readonly. Remover readonly e setar valor.
            await popup.evaluate(f"""() => {{
                const el = document.querySelector('input[name="sigla"]');
                if (el) {{
                    el.readOnly = false;
                    el.className = el.className.replace('nodata', '');
                    el.value = '{sigla}';
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""")

            # ── 6. Preencher todos os campos ──
            campos_preenchidos = {"sigla": sigla}
            campos_readonly = []
            campos_nao_encontrados = []

            for param, value in campos.items():
                ssw_field = FIELD_MAP.get(param)
                if not ssw_field:
                    continue

                result = await preencher_campo_js(popup, ssw_field, value)

                if not result.get("found"):
                    campos_nao_encontrados.append(f"{param} ({ssw_field})")
                elif result.get("readonly"):
                    campos_readonly.append(
                        f"{param} ({ssw_field}): readonly, atual={result.get('current', '?')}"
                    )
                else:
                    campos_preenchidos[param] = str(value)

            # ── 7. Capturar estado do formulario ──
            screenshot_path = await capturar_screenshot(
                popup, f"401_{'dryrun' if args.dry_run else 'presubmit'}_{sigla}"
            )

            if args.dry_run:
                snapshot = await capturar_campos(popup)
                return gerar_saida(
                    True,
                    modo="dry-run",
                    sigla=sigla,
                    campos_preenchidos=campos_preenchidos,
                    campos_readonly=campos_readonly,
                    campos_nao_encontrados=campos_nao_encontrados,
                    formulario_snapshot=snapshot,
                    screenshot=screenshot_path,
                    mensagem=f"Preview do cadastro {sigla}. Nenhum dado foi submetido.",
                )

            # ── 8. Submeter formulario (GRA = Gravar) ──
            alert_msg = None

            async def on_dialog(dialog):
                nonlocal alert_msg
                alert_msg = dialog.message
                await dialog.accept()

            popup.on("dialog", on_dialog)

            try:
                gra_html = await interceptar_ajax_response(
                    popup, popup.main_frame, "ajaxEnvia('GRA', 1)", timeout_s=20
                )

                # Injetar response do GRA para ler mensagens de sucesso/erro
                if gra_html:
                    await injetar_html_no_dom(popup, gra_html)

                await asyncio.sleep(2)

                # Verificar mensagem de sucesso/erro do SSW
                msg_ssw = await verificar_mensagem_ssw(popup)
                screenshot_pos = await capturar_screenshot(popup, f"401_resultado_{sigla}")

                # Avaliar resultado
                erro = None
                if alert_msg and any(
                    e in alert_msg.lower() for e in ["erro", "invalido", "obrigat", "existente"]
                ):
                    erro = f"SSW alert: {alert_msg}"
                elif msg_ssw and msg_ssw.get("tipo") == "erro":
                    erro = msg_ssw["mensagem"]

                if erro:
                    return gerar_saida(
                        False,
                        sigla=sigla,
                        erro=erro,
                        campos_preenchidos=campos_preenchidos,
                        screenshot=screenshot_pos,
                    )

                return gerar_saida(
                    True,
                    sigla=sigla,
                    campos_preenchidos=campos_preenchidos,
                    campos_readonly=campos_readonly,
                    campos_nao_encontrados=campos_nao_encontrados,
                    resposta_ssw=msg_ssw,
                    alert=alert_msg,
                    screenshot=screenshot_pos,
                    mensagem=f"Unidade {sigla} cadastrada com sucesso.",
                )

            finally:
                popup.remove_listener("dialog", on_dialog)

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Cadastrar unidade no SSW (opcao 401)"
    )
    parser.add_argument(
        "--sigla", required=True,
        help="Sigla IATA 3 chars (ex: CGR, CWB, POA)"
    )
    parser.add_argument(
        "--tipo", default="T", choices=["T", "F", "M"],
        help="T=Terceiro/parceira, F=Filial, M=Matriz (default: T)"
    )
    parser.add_argument(
        "--razao-social", required=True,
        help="Razao Social, max 45 chars (ex: ALEMAR - CAMPO GRANDE/MS)"
    )
    parser.add_argument(
        "--nome-fantasia", default="",
        help="Nome Fantasia, max 30 chars (default: razao social truncada)"
    )
    parser.add_argument(
        "--cnpj", default="",
        help="CNPJ 14 digitos (default: usa CNPJ do ssw_defaults.json)"
    )
    parser.add_argument(
        "--ie", default="",
        help="Inscricao Estadual (vazio se isento naquela UF)"
    )
    parser.add_argument(
        "--defaults-file",
        default=os.path.join(SCRIPT_DIR, "..", "ssw_defaults.json"),
        help="Caminho para ssw_defaults.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview do formulario preenchido, sem submeter"
    )

    args = parser.parse_args()

    # Validacoes
    if len(args.sigla) != 3:
        print(json.dumps({"sucesso": False, "erro": "Sigla deve ter exatamente 3 caracteres"}))
        sys.exit(1)

    if len(args.razao_social) > 45:
        print(json.dumps({
            "sucesso": False,
            "erro": f"Razao Social max 45 chars (recebido {len(args.razao_social)})"
        }))
        sys.exit(1)

    if args.nome_fantasia and len(args.nome_fantasia) > 30:
        print(json.dumps({
            "sucesso": False,
            "erro": f"Nome Fantasia max 30 chars (recebido {len(args.nome_fantasia)})"
        }))
        sys.exit(1)

    asyncio.run(cadastrar_unidade(args))


if __name__ == "__main__":
    main()
