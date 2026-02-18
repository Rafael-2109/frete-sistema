#!/usr/bin/env python3
"""
cadastrar_transportadora_485.py — Cadastra transportadora no SSW (opcao 485).

Fluxo:
  1. Login SSW
  2. Abre opcao 485 (popup)
  3. Override createNewDoc para PES in-place (evita window.open)
  4. Preenche CNPJ e executa PES — pesquisa transportadora
  5. Checar campo `nome`: se preenchido → ja existe
  6. Preencher nome + ativo
  7. --dry-run: captura snapshot → retorna preview
  8. Sem flag: ajaxEnvia('INC', 0) ou ajaxEnvia('GRA', 0) → verifica
  9. Output JSON via gerar_saida()

IMPORTANTE:
  - 485 e mais simples que 478 — basta CNPJ + nome + ativo
  - NAO exige endereco, telefone ou especialidade para gravacao
  - Prerequisito: CNPJ deve estar cadastrado na 478 como fornecedor
  - Acao de salvar: ajaxEnvia('INC', 0) para novo, ajaxEnvia('GRA', 0) para atualizar

Uso:
    python cadastrar_transportadora_485.py \
      --cnpj 42769176000152 \
      --nome "UNI BRASIL TRANSPORTES" \
      [--ativo S] \
      [--dry-run]

Retorno: JSON {"sucesso": bool, "cnpj": "...", ...}

Mapeamento de campos (fonte: scripts ad-hoc POP-A10, 2026-02-17):
  2        → CNPJ (campo de busca PES)
  nome     → Razao Social
  fg_ativo → Ativo S/N
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
    preencher_campo_js,
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
)


# ──────────────────────────────────────────────
# Field mapping: parametro CLI → nome do campo SSW
# ──────────────────────────────────────────────
FIELD_MAP = {
    "cnpj": "2",          # Campo de busca PES
    "nome": "nome",       # Razao social
    "ativo": "fg_ativo",  # S/N
}

# ──────────────────────────────────────────────
# Field limits: maxlength de cada campo SSW
# ──────────────────────────────────────────────
FIELD_LIMITS = {
    "cnpj": 14,
    "nome": 45,
    "ativo": 1,
}

# Opcoes validas para campos com dominio restrito
VALID_OPTIONS = {
    "ativo": ["S", "N"],
}


def validar_campos(campos):
    """Valida campos contra FIELD_LIMITS e VALID_OPTIONS. Retorna lista de erros."""
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
        if options and value_str.upper() not in options:
            erros.append(
                f"{param}: valor '{value_str}' invalido. Opcoes: {', '.join(options)}"
            )

    # Validacao CNPJ
    cnpj = campos.get("cnpj", "")
    if cnpj and (not cnpj.isdigit() or len(cnpj) != 14):
        erros.append(f"cnpj: deve ter exatamente 14 digitos numericos (recebido: '{cnpj}')")

    return erros


def montar_campos(args):
    """Monta dict completo de campos a preencher."""
    campos = {}
    campos["cnpj"] = args.cnpj.replace(".", "").replace("/", "").replace("-", "")
    campos["nome"] = args.nome.upper()
    campos["ativo"] = args.ativo.upper()
    return campos


async def cadastrar_transportadora(args):
    """
    Fluxo principal de cadastro de transportadora no SSW 485.

    Usa createNewDoc override para manter PES in-place,
    preenche campos e submete com ajaxEnvia('INC', 0).
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()
    campos = montar_campos(args)
    cnpj = campos["cnpj"]
    nome = campos["nome"]

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

            # ── 2. Abrir opcao 485 (popup) ──
            popup = await abrir_opcao_popup(context, page.frames[0], 485)
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
                screenshot = await capturar_screenshot(popup, f"485_pes_timeout_{cnpj}")
                return gerar_saida(
                    False,
                    erro="Timeout aguardando form 485 apos PES",
                    cnpj=cnpj,
                    screenshot=screenshot,
                )

            await asyncio.sleep(1)  # DOM estabilizar

            # ── 5. Checar existencia ──
            # Se campo nome ja esta preenchido, transportadora ja existe
            nome_atual = await popup.evaluate("""() => {
                const el = document.querySelector('input[name="nome"]');
                return el ? el.value.trim() : '';
            }""")

            if nome_atual:
                screenshot = await capturar_screenshot(popup, f"485_ja_existe_{cnpj}")
                return gerar_saida(
                    True,
                    status="ja_existe",
                    cnpj=cnpj,
                    nome_existente=nome_atual,
                    screenshot=screenshot,
                    mensagem=f"Transportadora CNPJ {cnpj} ja existe no SSW (nome: {nome_atual[:40]})",
                )

            # ── 6. Preencher campos via FIELD_MAP loop ──
            campos_preenchidos = {"cnpj": cnpj}
            campos_readonly = []
            campos_nao_encontrados = []

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
                popup, f"485_{'dryrun' if args.dry_run else 'presubmit'}_{cnpj}"
            )

            if args.dry_run:
                snapshot = await capturar_campos(popup)
                return gerar_saida(
                    True,
                    modo="dry-run",
                    cnpj=cnpj,
                    nome=nome,
                    campos_preenchidos=campos_preenchidos,
                    campos_readonly=campos_readonly,
                    campos_nao_encontrados=campos_nao_encontrados,
                    formulario_snapshot=snapshot,
                    screenshot=screenshot_path,
                    mensagem=f"Preview do cadastro transportadora CNPJ {cnpj}. Nenhum dado foi submetido.",
                )

            # ── 8. Submeter formulario ──
            alert_msg = None
            inc_response = None

            async def on_dialog(dialog):
                nonlocal alert_msg
                alert_msg = dialog.message
                await dialog.accept()

            async def on_response(response):
                nonlocal inc_response
                if "/bin/ssw" in response.url and response.status == 200:
                    try:
                        inc_response = await response.text()
                    except Exception:
                        pass

            popup.on("dialog", on_dialog)
            popup.on("response", on_response)

            try:
                # INC — Incluir
                await popup.evaluate("ajaxEnvia('INC', 0)")
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
                        nome=nome,
                        campos_preenchidos=campos_preenchidos,
                        mensagem=f"Transportadora {nome} (CNPJ {cnpj}) cadastrada com sucesso.",
                    )

                # Popup NAO fechou — checar resultado
                # Verificar se nome agora esta preenchido (indicador de sucesso sem close)
                nome_pos = await popup.evaluate("""() => {
                    const el = document.querySelector('input[name="nome"]');
                    return el ? el.value.trim() : '';
                }""")

                erro = None
                if alert_msg:
                    erro = f"SSW alert: {alert_msg}"
                elif inc_response:
                    # Checar <foc> (mensagem de erro inline do SSW)
                    foc_match = re.search(
                        r'<foc[^>]*>(.*?)$', inc_response, re.DOTALL
                    )
                    if foc_match:
                        erro = html_module.unescape(foc_match.group(1).strip())
                    elif "GoBack" in inc_response:
                        msg_match = re.search(
                            r'(.*?)<!--GoBack-->', inc_response, re.DOTALL
                        )
                        if msg_match:
                            text = re.sub(r'<[^>]+>', ' ', msg_match.group(1)).strip()
                            text = re.sub(r'\s+', ' ', text)
                            erro = text[:300]

                screenshot_pos = await capturar_screenshot(popup, f"485_resultado_{cnpj}")

                if erro:
                    return gerar_saida(
                        False,
                        status="erro",
                        cnpj=cnpj,
                        erro=erro,
                        campos_preenchidos=campos_preenchidos,
                        screenshot=screenshot_pos,
                    )

                # Se nome_pos preenchido, possivelmente sucesso sem fechar
                if nome_pos:
                    return gerar_saida(
                        True,
                        status="cadastrado",
                        cnpj=cnpj,
                        nome=nome,
                        campos_preenchidos=campos_preenchidos,
                        screenshot=screenshot_pos,
                        mensagem=f"Transportadora {nome} (CNPJ {cnpj}) possivelmente cadastrada "
                                 f"(nome preenchido no DOM, popup nao fechou).",
                    )

                return gerar_saida(
                    False,
                    status="inconclusivo",
                    cnpj=cnpj,
                    erro="Resposta SSW inconclusiva (popup nao fechou, sem erro explicito)",
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
        description="Cadastrar transportadora no SSW (opcao 485)"
    )
    parser.add_argument(
        "--cnpj", required=True,
        help="CNPJ da transportadora (14 digitos numericos)"
    )
    parser.add_argument(
        "--nome", required=True,
        help="Razao social da transportadora (max 45 chars)"
    )
    parser.add_argument(
        "--ativo", default="S", choices=["S", "N"],
        help="Ativo S/N (default: S)"
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

    asyncio.run(cadastrar_transportadora(args))


if __name__ == "__main__":
    main()
