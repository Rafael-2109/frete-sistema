#!/usr/bin/env python3
"""
cadastrar_unidade_401.py — Cadastra nova unidade operacional no SSW (opcao 401).

Fluxo:
  1. Login SSW
  2. Abre opcao 401 (popup)
  3. Override createNewDoc para PES in-place (evita window.open)
  4. Pesquisa sigla (PES) — se f37 vazio, sigla nao existe
  5. Preenche campos (defaults CarVia + parametros CLI)
  6. --dry-run: captura preview sem submeter
  7. Sem flag: submete (ENV) e verifica sucesso (popup fecha = sucesso)

IMPORTANTE:
  - Acao de salvar: ajaxEnvia('ENV', 0) — NAO 'GRA'!
  - Campos f44, simp_nac, cod_fil, sigla_mtz_ctb sao gerenciados pelo servidor.
    NAO devem ser preenchidos pela automacao.
  - Sucesso = popup fecha automaticamente (SSW envia <!--CloseMe-->)

Uso:
    python cadastrar_unidade_401.py \
      --sigla GIG --tipo T \
      --nome-fantasia "TRANSMENEZES - RIO DE JANEIRO/RJ" \
      --logradouro "Rua Ricardo Machado" --numero 159 \
      --bairro "Vasco da Gama" --cep 20921270 \
      --ddd 21 --telefone 33617700 \
      [--defaults-file ../ssw_defaults.json] \
      [--dry-run]

Retorno: JSON {"sucesso": bool, "sigla": "...", ...}

Mapeamento de campos (fonte: /tmp/ssw_401_pes_completo.html, 2026-02-17):
  sigla          → name="sigla" (READONLY — forcamos apenas este)
  f1             → Ativa (S/N)
  f3             → Tipo da Unidade (T/F/M)
  f7             → Nome Fantasia (30 chars)
  f37            → Razao Social (45 chars) — SEMPRE CarVia (do defaults)
  f38            → CNPJ (editavel em novo registro)
  f45            → IE (editavel em novo registro)
  f9/f10/f11     → Endereco: logradouro / numero / complemento
  f12            → Bairro
  f14            → CEP (8 digitos, sem traco)
  f15/f16        → DDD / Telefone
  fld_aereo      → Aereo (S/N)
  fld_rodoviario → Rodoviario (S/N)
  f4             → Aquaviaria (S/N)
  f32/f33/f34/f35/f36 → Banco/Ag/DV/Conta/DV
  f29            → Seguro RCTRC apolice
  cnpj_seguradora → CNPJ seguradora
  f41            → RNTRC
  f48-f54        → Endereco fiscal (sede CarVia)
  * f44, simp_nac, cod_fil, sigla_mtz_ctb — SERVIDOR GERENCIA, NAO PREENCHER
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
    carregar_defaults,
    login_ssw,
    abrir_opcao_popup,
    preencher_campo_js,
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
)


# ──────────────────────────────────────────────
# Field mapping: parametro → nome do campo SSW
# NOTA: f44, simp_nac, cod_fil, sigla_mtz_ctb sao EXCLUIDOS
#       pois o servidor SSW os gerencia automaticamente.
# ──────────────────────────────────────────────
FIELD_MAP = {
    # Dados Basicos
    "ativa": "f1",
    "tipo": "f3",
    "nome_fantasia": "f7",
    "razao_social": "f37",
    # Endereco operacional
    "logradouro": "f9",
    "numero": "f10",
    "complemento": "f11",
    "bairro": "f12",
    "cep": "f14",
    # Telefone
    "ddd": "f15",
    "telefone": "f16",
    # Modalidades
    "aereo": "fld_aereo",
    "rodoviario": "fld_rodoviario",
    "aquaviaria": "f4",
    # Dados Fiscais (editaveis em registro novo)
    "cnpj": "f38",
    "ie": "f45",
    "rntrc": "f41",
    # Seguro
    "rctrc_apolice": "f29",
    "cnpj_seguradora": "cnpj_seguradora",
    # Dados Bancarios
    "banco": "f32",
    "agencia": "f33",
    "dv_agencia": "f34",
    "conta": "f35",
    "dv_conta": "f36",
    # Endereco fiscal (sede CarVia — igual para todas as unidades)
    "fiscal_logradouro": "f48",
    "fiscal_numero": "f49",
    "fiscal_complemento": "comple_fiscal",
    "fiscal_bairro": "f50",
    "fiscal_cep": "f52",
    "fiscal_ddd": "f53",
    "fiscal_telefone": "f54",
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
# Fonte: /tmp/ssw_401_pes_completo.html
# ──────────────────────────────────────────────
FIELD_LIMITS = {
    # Dados basicos
    "tipo": 1,               # f3: T/F/M
    "nome_fantasia": 30,     # f7
    "razao_social": 45,      # f37
    # Endereco
    "logradouro": 40,        # f9
    "numero": 6,             # f10
    "complemento": 20,       # f11
    "bairro": 30,            # f12
    "cep": 8,                # f14
    # Telefone
    "ddd": 4,                # f15
    "telefone": 15,          # f16
    # Fiscais
    "rntrc": 14,             # f41
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
    # Endereco fiscal
    "fiscal_logradouro": 30,  # f48
    "fiscal_numero": 10,      # f49
    "fiscal_complemento": 10, # comple_fiscal
    "fiscal_bairro": 30,      # f50
    "fiscal_cep": 8,          # f52
    "fiscal_ddd": 2,          # f53
    "fiscal_telefone": 9,     # f54
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

    # 1. Dados Basicos
    campos["tipo"] = args.tipo
    # f37 = SEMPRE razao social da CarVia (do defaults)
    campos["razao_social"] = empresa.get("razao_social", "CARVIA LOGISTICA E TRANSPORTE LTDA")
    # f7 = nome fantasia: padrao "PARCEIRO - CIDADE/UF"
    campos["nome_fantasia"] = args.nome_fantasia
    # CNPJ (f38) e IE (f45): editaveis em registro novo
    campos["cnpj"] = empresa.get("cnpj", "")
    campos["ie"] = empresa.get("ie", "")

    # 1b. Endereco operacional (do CLI)
    if hasattr(args, "logradouro") and args.logradouro:
        campos["logradouro"] = args.logradouro
    if hasattr(args, "numero") and args.numero:
        campos["numero"] = args.numero
    if hasattr(args, "complemento") and args.complemento:
        campos["complemento"] = args.complemento
    if hasattr(args, "bairro") and args.bairro:
        campos["bairro"] = args.bairro
    if hasattr(args, "cep") and args.cep:
        campos["cep"] = args.cep.replace("-", "").replace(".", "")
    if hasattr(args, "ddd") and args.ddd:
        campos["ddd"] = args.ddd
    if hasattr(args, "telefone") and args.telefone:
        campos["telefone"] = args.telefone

    # 2. Defaults da opcao 401 (flags S/N)
    campos["ativa"] = d401.get("ativa", "S")
    campos["aereo"] = d401.get("aereo", "N")
    campos["rodoviario"] = d401.get("rodoviario", "S")
    campos["aquaviaria"] = d401.get("aquaviaria", "N")
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

    # 3. Dados da empresa
    campos["rntrc"] = empresa.get("rntrc", "")

    # 3b. Endereco fiscal (sede CarVia — igual para todas as unidades)
    fiscal = defaults.get("endereco_fiscal", {})
    if fiscal:
        campos["fiscal_logradouro"] = fiscal.get("logradouro", "")
        campos["fiscal_numero"] = fiscal.get("numero", "")
        if fiscal.get("complemento"):
            campos["fiscal_complemento"] = fiscal["complemento"]
        campos["fiscal_bairro"] = fiscal.get("bairro", "")
        campos["fiscal_cep"] = fiscal.get("cep", "").replace("-", "")
        campos["fiscal_ddd"] = fiscal.get("ddd", "")
        campos["fiscal_telefone"] = fiscal.get("telefone", "")

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


async def cadastrar_unidade(args):
    """
    Fluxo principal de cadastro de unidade no SSW 401.

    Usa createNewDoc override para manter PES in-place (evita window.open),
    preenche campos e submete com ajaxEnvia('ENV', 0). Sucesso = popup fecha.
    """
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
            await asyncio.sleep(1)

            # ── 3. Override createNewDoc para PES in-place ──
            # SSW's createNewDoc com newPage=1 abre nova janela via window.open.
            # Substituimos para fazer document.write in-place no popup,
            # preservando a referencia Playwright ao popup.
            await popup.evaluate("""() => {
                createNewDoc = function(pathname) {
                    document.open("text/html", "replace");
                    document.write(valSep.toString());
                    document.close();
                    if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
                };
            }""")

            # ── 4. PES — pesquisar sigla ──
            await popup.evaluate(f"""() => {{
                const f2 = document.querySelector('input[name="f2"]');
                if (f2) f2.value = '{sigla}';
            }}""")
            await popup.evaluate("ajaxEnvia('PES', 1)")

            # Esperar DOM atualizar (f37 aparece apos PES in-place)
            form_loaded = False
            for _ in range(30):
                has_f37 = await popup.evaluate(
                    '!!document.querySelector(\'input[name="f37"]\')'
                )
                if has_f37:
                    form_loaded = True
                    break
                await asyncio.sleep(0.5)

            if not form_loaded:
                screenshot = await capturar_screenshot(popup, f"401_pes_timeout_{sigla}")
                return gerar_saida(
                    False,
                    erro="Timeout aguardando form 401 apos PES",
                    sigla=sigla,
                    screenshot=screenshot,
                )

            await asyncio.sleep(1)  # DOM estabilizar

            # Verificar se form carregou completamente
            input_count = await popup.evaluate(
                "document.querySelectorAll('input:not([type=\"hidden\"])').length"
            )
            if input_count < 20:
                screenshot = await capturar_screenshot(popup, f"401_form_incompleto_{sigla}")
                return gerar_saida(
                    False,
                    erro=f"Form 401 incompleto ({input_count} inputs, esperado 60+)",
                    sigla=sigla,
                    screenshot=screenshot,
                )

            # ── 5. Checar existencia ──
            # Se f37 (razao_social) tem valor, sigla ja existe no SSW
            f37_val = await popup.evaluate("""() => {
                const el = document.querySelector('input[name="f37"]');
                return el ? el.value : '';
            }""")
            if f37_val.strip():
                screenshot = await capturar_screenshot(popup, f"401_ja_existe_{sigla}")
                return gerar_saida(
                    False,
                    erro=f"Sigla {sigla} ja existe no SSW (razao: {f37_val.strip()[:40]})",
                    sigla=sigla,
                    screenshot=screenshot,
                )

            # ── 6. Forcar sigla no campo ──
            # Unico campo readonly que precisamos setar.
            await popup.evaluate(f"""() => {{
                const el = document.querySelector('input[name="sigla"]');
                if (el) {{
                    el.readOnly = false;
                    el.className = el.className.replace('nodata', '');
                    el.value = '{sigla}';
                }}
            }}""")

            # ── 7. Preencher todos os campos ──
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

            # ── 8. Screenshot pre-submit ──
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

            # ── 9. Submeter formulario ──
            # Acao: ajaxEnvia('ENV', 0) — 'ENV' = Enviar (acao do botao ►)
            # newPage=0 — nao abre nova janela
            # Em sucesso, SSW envia <!--CloseMe--> que fecha o popup

            # Abortar qualquer request AJAX pendente (ex: geocoding do CEP)
            await popup.evaluate("""() => {
                if (typeof ajaxGeral !== 'undefined' &&
                    ajaxGeral.readyState !== 0 && ajaxGeral.readyState !== 4) {
                    ajaxGeral.abort();
                }
            }""")
            await asyncio.sleep(2)

            alert_msg = None
            env_response = None

            async def on_dialog(dialog):
                nonlocal alert_msg
                alert_msg = dialog.message
                await dialog.accept()

            async def on_response(response):
                nonlocal env_response
                if "/bin/ssw" in response.url and response.status == 200:
                    try:
                        env_response = await response.text()
                    except Exception:
                        pass

            popup.on("dialog", on_dialog)
            popup.on("response", on_response)

            try:
                # ENV — acao do botao ► (Enviar)
                await popup.evaluate("ajaxEnvia('ENV', 0)")
                await asyncio.sleep(5)

                # Detectar se popup fechou (= sucesso)
                # SSW envia <!--CloseMe--> na response, que fecha a janela
                page_closed = False
                try:
                    await popup.evaluate("1")
                except Exception:
                    page_closed = True

                if page_closed:
                    return gerar_saida(
                        True,
                        sigla=sigla,
                        campos_preenchidos=campos_preenchidos,
                        campos_readonly=campos_readonly,
                        campos_nao_encontrados=campos_nao_encontrados,
                        mensagem=f"Unidade {sigla} cadastrada com sucesso.",
                    )

                # Popup NAO fechou — checar erro na response
                erro = None
                if alert_msg:
                    erro = f"SSW alert: {alert_msg}"
                elif env_response:
                    # Checar <foc> (mensagem de erro inline do SSW)
                    foc_match = re.search(
                        r'<foc[^>]*>(.*?)$', env_response, re.DOTALL
                    )
                    if foc_match:
                        erro = html_module.unescape(foc_match.group(1).strip())
                    # Checar <!--GoBack--> (mensagem de erro com botao voltar)
                    elif "GoBack" in env_response:
                        msg_match = re.search(
                            r'(.*?)<!--GoBack-->', env_response, re.DOTALL
                        )
                        if msg_match:
                            text = re.sub(r'<[^>]+>', ' ', msg_match.group(1)).strip()
                            text = re.sub(r'\s+', ' ', text)
                            erro = text[:300]

                screenshot_pos = await capturar_screenshot(
                    popup, f"401_resultado_{sigla}"
                )

                if erro:
                    return gerar_saida(
                        False,
                        sigla=sigla,
                        erro=erro,
                        campos_preenchidos=campos_preenchidos,
                        screenshot=screenshot_pos,
                    )

                # Sem erro explicito mas popup nao fechou — inconclusivo
                return gerar_saida(
                    False,
                    sigla=sigla,
                    erro="Resposta SSW inconclusiva (popup nao fechou mas sem erro explicito)",
                    campos_preenchidos=campos_preenchidos,
                    screenshot=screenshot_pos,
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
        "--nome-fantasia", required=True,
        help="Nome Fantasia, max 30 chars. Padrao: 'PARCEIRO - CIDADE/UF'"
    )
    # Endereco operacional
    parser.add_argument("--logradouro", default="", help="Logradouro (max 40 chars)")
    parser.add_argument("--numero", default="", help="Numero (max 6 chars)")
    parser.add_argument("--complemento", default="", help="Complemento (max 20 chars)")
    parser.add_argument("--bairro", default="", help="Bairro (max 30 chars)")
    parser.add_argument("--cep", default="", help="CEP 8 digitos sem traco")
    # Telefone
    parser.add_argument("--ddd", default="", help="DDD (max 4 chars)")
    parser.add_argument("--telefone", default="", help="Telefone sem DDD (max 15 chars)")
    # Config
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

    if len(args.nome_fantasia) > 30:
        print(json.dumps({
            "sucesso": False,
            "erro": f"Nome Fantasia max 30 chars (recebido {len(args.nome_fantasia)})"
        }))
        sys.exit(1)

    asyncio.run(cadastrar_unidade(args))


if __name__ == "__main__":
    main()
