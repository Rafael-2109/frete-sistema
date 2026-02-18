#!/usr/bin/env python3
"""
cadastrar_fornecedor_478.py — Cadastra fornecedor no SSW (opcao 478).

Fluxo:
  1. Login SSW
  2. Abre opcao 478 (popup)
  3. Override createNewDoc para PES in-place (evita window.open)
  4. Preenche CNPJ e executa PES — pesquisa fornecedor
  5. Checar campo `inclusao`:
     - Ausente do DOM → registro ja finalizado → retornar `ja_existe`
     - 'S' → registro precisa ser completado (campos obrigatorios faltando)
  6. Preenche campos do FIELD_MAP
  7. --dry-run: captura snapshot + screenshot → retorna preview
  8. Sem flag: ajaxEnvia('GRA', 0) → captura resposta
  9. Verificacao: reabrir 478, PES, confirmar `inclusao` ausente
  10. Output JSON via gerar_saida()

IMPORTANTE:
  - Acao de salvar: ajaxEnvia('GRA', 0)
  - Sucesso = popup fecha (SSW envia <!--CloseMe-->) OU `inclusao` desaparece
  - GOTCHA CRITICO: `inclusao=S` = registro nao finalizado → 408 rejeita CNPJ
  - Campos obrigatorios: nome, inscr_estadual, especialidade, ddd_principal (real),
    fone_principal (valido), endereco (cep, logradouro, numero, bairro)

Uso:
    python cadastrar_fornecedor_478.py \
      --cnpj 42769176000152 \
      --nome "UNI BRASIL TRANSPORTES" \
      --especialidade TRANSPORTADORA \
      [--ie ISENTO] [--contribuinte N] \
      [--ddd 11] [--telefone 30001234] \
      [--cep 06460040] [--logradouro "RUA JOSE SOARES"] \
      [--numero 100] [--bairro JAGUARE] \
      [--fg-cc N] \
      [--defaults-file ../ssw_defaults.json] \
      [--dry-run]

Retorno: JSON {"sucesso": bool, "cnpj": "...", ...}

Mapeamento de campos (fonte: scripts ad-hoc POP-A10, 2026-02-17):
  2               → CNPJ (campo de busca PES)
  nome            → Razao Social (max 45 chars)
  inscr_estadual  → IE ou ISENTO
  contribuinte    → S/N
  especialidade   → TRANSPORTADORA / PARCEIRO TRANSPORTADOR / PARCEIRO / FORNECEDOR
  ddd_principal   → DDD telefone (2 chars, NAO aceita '00' ou '01')
  fone_principal  → Telefone fixo (8 digitos, NAO aceita '00000000' ou '99999999')
  cep_end         → CEP (8 digitos sem hifen)
  logradouro      → Logradouro (max 40 chars)
  numero_end      → Numero (max 10 chars)
  bairro_end      → Bairro (max 30 chars)
  fg_cc           → Conta Corrente Fornecedor S/N (N = padrao seguro)
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
# Field mapping: parametro CLI → nome do campo SSW
# ──────────────────────────────────────────────
FIELD_MAP = {
    "cnpj": "2",                     # CNPJ (campo de busca PES)
    "nome": "nome",                  # Razao social
    "inscr_estadual": "inscr_estadual",  # IE ou ISENTO
    "contribuinte": "contribuinte",  # S/N
    "especialidade": "especialidade",  # TRANSPORTADORA, PARCEIRO, etc.
    "ddd": "ddd_principal",          # DDD telefone
    "telefone": "fone_principal",    # Telefone fixo
    "cep": "cep_end",               # CEP
    "logradouro": "logradouro",      # Logradouro
    "numero": "numero_end",          # Numero
    "bairro": "bairro_end",          # Bairro
    "fg_cc": "fg_cc",               # Conta corrente N/S
}

# ──────────────────────────────────────────────
# Field limits: maxlength de cada campo SSW
# Fonte: scripts ad-hoc POP-A10
# ──────────────────────────────────────────────
FIELD_LIMITS = {
    "cnpj": 14,
    "nome": 45,
    "inscr_estadual": 20,
    "ddd": 2,
    "telefone": 8,
    "cep": 8,
    "logradouro": 40,
    "numero": 10,
    "bairro": 30,
}

# Opcoes validas para campos com dominio restrito
VALID_OPTIONS = {
    "contribuinte": ["S", "N"],
    "especialidade": [
        "TRANSPORTADORA",
        "PARCEIRO TRANSPORTADOR",
        "PARCEIRO",
        "FORNECEDOR",
    ],
    "fg_cc": ["S", "N"],
}

# DDD invalidos (nao existem no Brasil)
INVALID_DDD = {"00", "01"}

# Telefones invalidos (genericos rejeitados pelo SSW)
INVALID_TELEFONE = {"00000000", "99999999"}


def validar_campos(campos):
    """Valida campos contra FIELD_LIMITS, VALID_OPTIONS e regras especiais. Retorna lista de erros."""
    erros = []
    for param, value in campos.items():
        value_str = str(value)

        # Checar maxlength
        limit = FIELD_LIMITS.get(param)
        if limit and len(value_str) > limit:
            erros.append(
                f"{param}: valor '{value_str}' excede limite de {limit} chars "
                f"(tem {len(value_str)})"
            )

        # Checar opcoes validas
        options = VALID_OPTIONS.get(param)
        if options and value_str.upper() not in [o.upper() for o in options]:
            erros.append(
                f"{param}: valor '{value_str}' invalido. Opcoes: {', '.join(options)}"
            )

    # Validacoes especiais
    cnpj = campos.get("cnpj", "")
    if cnpj and (not cnpj.isdigit() or len(cnpj) != 14):
        erros.append(f"cnpj: deve ter exatamente 14 digitos numericos (recebido: '{cnpj}')")

    ddd = campos.get("ddd", "")
    if ddd and ddd in INVALID_DDD:
        erros.append(f"ddd: '{ddd}' e invalido. Usar DDD real da cidade sede (ex: 11, 21, 92)")

    telefone = campos.get("telefone", "")
    if telefone:
        if telefone in INVALID_TELEFONE:
            erros.append(f"telefone: '{telefone}' e rejeitado pelo SSW. Usar numero valido (ex: 30001234)")
        if len(telefone) < 8:
            erros.append(f"telefone: minimo 8 digitos (recebido: '{telefone}', {len(telefone)} digitos)")

    return erros


def montar_campos(args, defaults):
    """Monta dict completo de campos a preencher, mesclando CLI + defaults."""
    d478 = defaults.get("opcao_478", {})

    campos = {}

    # Dados obrigatorios (CLI)
    campos["cnpj"] = args.cnpj.replace(".", "").replace("/", "").replace("-", "")
    campos["nome"] = args.nome.upper()

    # Dados com defaults
    campos["inscr_estadual"] = args.ie or d478.get("inscr_estadual", "ISENTO")
    campos["contribuinte"] = args.contribuinte or d478.get("contribuinte", "N")
    campos["especialidade"] = args.especialidade or d478.get("especialidade", "TRANSPORTADORA")
    campos["fg_cc"] = args.fg_cc or d478.get("fg_cc", "N")

    # Endereco e telefone (opcionais no CLI, mas obrigatorios no SSW)
    if args.ddd:
        campos["ddd"] = args.ddd
    if args.telefone:
        campos["telefone"] = args.telefone
    if args.cep:
        campos["cep"] = args.cep.replace("-", "").replace(".", "")
    if args.logradouro:
        campos["logradouro"] = args.logradouro.upper()
    if args.numero:
        campos["numero"] = args.numero
    if args.bairro:
        campos["bairro"] = args.bairro.upper()

    return campos


async def cadastrar_fornecedor(args):
    """
    Fluxo principal de cadastro de fornecedor no SSW 478.

    Usa createNewDoc override para manter PES in-place,
    preenche campos e submete com ajaxEnvia('GRA', 0).
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()
    defaults = carregar_defaults(args.defaults_file)
    campos = montar_campos(args, defaults)
    cnpj = campos["cnpj"]

    # Validar campos antes de tentar preencher
    erros_validacao = validar_campos(campos)
    if erros_validacao:
        return gerar_saida(
            False,
            erro="Campos invalidos",
            cnpj=cnpj,
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

            # ── 2. Abrir opcao 478 (popup) ──
            popup = await abrir_opcao_popup(context, page.frames[0], 478)
            await asyncio.sleep(1)

            # ── 3. Override createNewDoc para PES in-place ──
            await popup.evaluate("""() => {
                createNewDoc = function(pathname) {
                    document.open("text/html", "replace");
                    document.write(valSep.toString());
                    document.close();
                    if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
                };
            }""")

            # ── 4. PES — pesquisar CNPJ ──
            await popup.evaluate(f"""() => {{
                const f2 = document.getElementById('2');
                if (f2) f2.value = '{cnpj}';
            }}""")
            await popup.evaluate("ajaxEnvia('PES', 0)")

            # Esperar DOM atualizar (campo 'nome' aparece apos PES)
            form_loaded = False
            for _ in range(30):
                has_nome = await popup.evaluate(
                    '!!document.querySelector(\'input[name="nome"]\')'
                )
                if has_nome:
                    form_loaded = True
                    break
                await asyncio.sleep(0.5)

            if not form_loaded:
                screenshot = await capturar_screenshot(popup, f"478_pes_timeout_{cnpj}")
                return gerar_saida(
                    False,
                    erro="Timeout aguardando form 478 apos PES",
                    cnpj=cnpj,
                    screenshot=screenshot,
                )

            await asyncio.sleep(1)  # DOM estabilizar

            # ── 5. Checar existencia via campo `inclusao` ──
            # inclusao ausente do DOM = registro ja finalizado
            # inclusao = 'S' = registro em modo inclusao (precisa completar)
            inclusao_status = await popup.evaluate("""() => {
                const el = document.querySelector('input[name="inclusao"]');
                if (!el) return {exists: false};
                return {exists: true, value: el.value};
            }""")

            nome_atual = await popup.evaluate("""() => {
                const el = document.querySelector('input[name="nome"]');
                return el ? el.value.trim() : '';
            }""")

            if not inclusao_status["exists"]:
                # Registro ja finalizado — ja existe
                screenshot = await capturar_screenshot(popup, f"478_ja_existe_{cnpj}")
                return gerar_saida(
                    True,
                    status="ja_existe",
                    cnpj=cnpj,
                    nome_existente=nome_atual,
                    screenshot=screenshot,
                    mensagem=f"Fornecedor CNPJ {cnpj} ja existe no SSW (nome: {nome_atual[:40]})",
                )

            # inclusao='S' — registro em modo inclusao, precisa preencher
            # ── 6. Preencher campos ──
            campos_preenchidos = {"cnpj": cnpj}
            campos_readonly = []
            campos_nao_encontrados = []

            # Preencher todos os campos exceto CNPJ (ja preenchido pelo PES)
            for param, value in campos.items():
                if param == "cnpj":
                    continue  # Ja preenchido pelo PES
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

            # ── 7. Screenshot pre-submit ──
            screenshot_path = await capturar_screenshot(
                popup, f"478_{'dryrun' if args.dry_run else 'presubmit'}_{cnpj}"
            )

            if args.dry_run:
                snapshot = await capturar_campos(popup)
                return gerar_saida(
                    True,
                    modo="dry-run",
                    cnpj=cnpj,
                    nome=campos.get("nome", ""),
                    campos_preenchidos=campos_preenchidos,
                    campos_readonly=campos_readonly,
                    campos_nao_encontrados=campos_nao_encontrados,
                    formulario_snapshot=snapshot,
                    screenshot=screenshot_path,
                    mensagem=f"Preview do cadastro fornecedor CNPJ {cnpj}. Nenhum dado foi submetido.",
                )

            # ── 8. Submeter formulario ──
            # Abortar AJAX pendente (ex: geocoding do CEP)
            await popup.evaluate("""() => {
                if (typeof ajaxGeral !== 'undefined' &&
                    ajaxGeral.readyState !== 0 && ajaxGeral.readyState !== 4) {
                    ajaxGeral.abort();
                }
            }""")
            await asyncio.sleep(2)

            alert_msg = None
            gra_response = None

            async def on_dialog(dialog):
                nonlocal alert_msg
                alert_msg = dialog.message
                await dialog.accept()

            async def on_response(response):
                nonlocal gra_response
                if "/bin/ssw" in response.url and response.status == 200:
                    try:
                        gra_response = await response.text()
                    except Exception:
                        pass

            popup.on("dialog", on_dialog)
            popup.on("response", on_response)

            try:
                # GRA — Gravar
                await popup.evaluate("ajaxEnvia('GRA', 0)")
                await asyncio.sleep(5)

                # Detectar se popup fechou (= sucesso)
                page_closed = False
                try:
                    await popup.evaluate("1")
                except Exception:
                    page_closed = True

                if page_closed:
                    return gerar_saida(
                        True,
                        status="cadastrado",
                        cnpj=cnpj,
                        nome=campos.get("nome", ""),
                        campos_preenchidos=campos_preenchidos,
                        mensagem=f"Fornecedor {campos.get('nome', '')} (CNPJ {cnpj}) cadastrado com sucesso.",
                    )

                # Popup NAO fechou — checar se registro foi finalizado
                # Re-checar campo inclusao
                inclusao_pos = await popup.evaluate("""() => {
                    const el = document.querySelector('input[name="inclusao"]');
                    if (!el) return {exists: false};
                    return {exists: true, value: el.value};
                }""")

                if not inclusao_pos["exists"]:
                    # inclusao desapareceu = registro finalizado com sucesso
                    screenshot_pos = await capturar_screenshot(popup, f"478_sucesso_{cnpj}")
                    return gerar_saida(
                        True,
                        status="cadastrado",
                        cnpj=cnpj,
                        nome=campos.get("nome", ""),
                        campos_preenchidos=campos_preenchidos,
                        screenshot=screenshot_pos,
                        mensagem=f"Fornecedor {campos.get('nome', '')} (CNPJ {cnpj}) cadastrado com sucesso.",
                    )

                # Houve erro — tentar identificar
                erro = None
                if alert_msg:
                    erro = f"SSW alert: {alert_msg}"
                elif gra_response:
                    # Checar <foc> (mensagem de erro inline do SSW)
                    foc_match = re.search(
                        r'<foc[^>]*>(.*?)$', gra_response, re.DOTALL
                    )
                    if foc_match:
                        erro = html_module.unescape(foc_match.group(1).strip())
                    # Checar <!--GoBack--> (mensagem de erro com botao voltar)
                    elif "GoBack" in gra_response:
                        msg_match = re.search(
                            r'(.*?)<!--GoBack-->', gra_response, re.DOTALL
                        )
                        if msg_match:
                            text = re.sub(r'<[^>]+>', ' ', msg_match.group(1)).strip()
                            text = re.sub(r'\s+', ' ', text)
                            erro = text[:300]

                screenshot_pos = await capturar_screenshot(popup, f"478_resultado_{cnpj}")

                if erro:
                    return gerar_saida(
                        False,
                        status="erro",
                        cnpj=cnpj,
                        erro=erro,
                        campos_preenchidos=campos_preenchidos,
                        screenshot=screenshot_pos,
                    )

                # Sem erro explicito mas inclusao ainda S — inconclusivo
                return gerar_saida(
                    False,
                    status="inconclusivo",
                    cnpj=cnpj,
                    erro="Resposta SSW inconclusiva (inclusao ainda 'S', mas sem erro explicito)",
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
        description="Cadastrar fornecedor no SSW (opcao 478)"
    )
    parser.add_argument(
        "--cnpj", required=True,
        help="CNPJ do fornecedor (14 digitos numericos)"
    )
    parser.add_argument(
        "--nome", required=True,
        help="Razao social do fornecedor (max 45 chars)"
    )
    parser.add_argument(
        "--especialidade", default=None,
        choices=["TRANSPORTADORA", "PARCEIRO TRANSPORTADOR", "PARCEIRO", "FORNECEDOR"],
        help="Tipo de fornecedor (default: TRANSPORTADORA do ssw_defaults.json)"
    )
    parser.add_argument(
        "--ie", default=None,
        help="Inscricao Estadual (default: ISENTO do ssw_defaults.json)"
    )
    parser.add_argument(
        "--contribuinte", default=None, choices=["S", "N"],
        help="Contribuinte ICMS S/N (default: N do ssw_defaults.json)"
    )
    # Telefone
    parser.add_argument("--ddd", default=None, help="DDD telefone (2 digitos, ex: 11)")
    parser.add_argument("--telefone", default=None, help="Telefone fixo (8 digitos, ex: 30001234)")
    # Endereco
    parser.add_argument("--cep", default=None, help="CEP 8 digitos sem traco")
    parser.add_argument("--logradouro", default=None, help="Logradouro (max 40 chars)")
    parser.add_argument("--numero", default=None, help="Numero (max 10 chars)")
    parser.add_argument("--bairro", default=None, help="Bairro (max 30 chars)")
    # Conta corrente
    parser.add_argument(
        "--fg-cc", default=None, choices=["S", "N"],
        help="Conta Corrente Fornecedor S/N (default: N). Se S, campo 'evento' e obrigatorio"
    )
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

    # Validacoes de entrada
    cnpj_clean = args.cnpj.replace(".", "").replace("/", "").replace("-", "")
    if not cnpj_clean.isdigit() or len(cnpj_clean) != 14:
        print(json.dumps({
            "sucesso": False,
            "erro": f"CNPJ deve ter 14 digitos numericos (recebido: '{args.cnpj}')"
        }))
        sys.exit(1)

    if len(args.nome) > 45:
        print(json.dumps({
            "sucesso": False,
            "erro": f"Nome max 45 chars (recebido {len(args.nome)})"
        }))
        sys.exit(1)

    asyncio.run(cadastrar_fornecedor(args))


if __name__ == "__main__":
    main()
