#!/usr/bin/env python3
"""
criar_comissao_408.py — Cria comissao de unidade no SSW (opcao 408).

Fluxo:
  1. Login SSW
  2. Abre opcao 408 (popup)
  3. Override createNewDoc para manter DOM in-place
  4. Preenche sigla da unidade → ajaxEnvia('ENV', 1) → interceptar
  5. Checar campo `acao`:
     - 'A' → comissao ja existe → retornar `ja_existe`
     - Outro → inclusao (nao existe ainda)
  6. Preencher CNPJ, data, despachos
  7. --dry-run: captura snapshot → retorna preview
  8. Sem flag: ajaxEnvia('ENV2', 0)
  9. Sucesso: popup fecha (TargetClosedError). Erro: popup aberto.
  10. Output JSON via gerar_saida()

IMPORTANTE:
  - Acao de salvar: ajaxEnvia('ENV2', 0)
  - Sucesso = popup fecha automaticamente (SSW envia <!--CloseMe-->)
  - Popup aberto apos ENV2 = ERRO
  - Prerequisitos: 478 finalizado (inclusao != 'S') + 485 cadastrado + 401 unidade existente

Uso:
    python criar_comissao_408.py \
      --unidade VIX \
      --cnpj 42769176000152 \
      [--data-inicio 180226] \
      [--despacho-exp "1,00"] \
      [--despacho-rec "1,00"] \
      [--defaults-file ../ssw_defaults.json] \
      [--dry-run]

Retorno: JSON {"sucesso": bool, "unidade": "...", "cnpj": "...", ...}

Mapeamento de campos (fonte: scripts ad-hoc POP-A10, 2026-02-17):
  2                      → Sigla da unidade (3 chars)
  3                      → CNPJ do subcontratado
  data_ini               → Data inicio (DDMMAA)
  exp_emit_despacho_pol  → Despacho expedidor R$ com virgula
  rec_dest_despacho_pol  → Despacho recebedor R$ com virgula
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
    preencher_campo_js,
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
)


# ──────────────────────────────────────────────
# Field mapping: parametro CLI → nome do campo SSW
# ──────────────────────────────────────────────
FIELD_MAP = {
    "unidade": "2",                             # Sigla 3 chars
    "cnpj": "3",                                # CNPJ subcontratado
    "data_inicio": "data_ini",                  # DDMMAA
    "despacho_exp": "exp_emit_despacho_pol",    # R$ com virgula
    "despacho_rec": "rec_dest_despacho_pol",    # R$ com virgula
}

# ──────────────────────────────────────────────
# Field limits
# ──────────────────────────────────────────────
FIELD_LIMITS = {
    "unidade": 3,
    "cnpj": 14,
    "data_inicio": 6,       # DDMMAA
    "despacho_exp": 10,      # ex: "1.234,56"
    "despacho_rec": 10,
}

# Opcoes validas (nenhum campo de dominio restrito alem dos limites)
VALID_OPTIONS = {}


def validar_campos(campos):
    """Valida campos contra FIELD_LIMITS e regras especiais. Retorna lista de erros."""
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

    # Validacao CNPJ
    cnpj = campos.get("cnpj", "")
    if cnpj and (not cnpj.isdigit() or len(cnpj) != 14):
        erros.append(f"cnpj: deve ter exatamente 14 digitos numericos (recebido: '{cnpj}')")

    # Validacao unidade
    unidade = campos.get("unidade", "")
    if unidade and len(unidade) != 3:
        erros.append(f"unidade: deve ter exatamente 3 caracteres (recebido: '{unidade}')")

    # Validacao data_inicio (DDMMAA)
    data = campos.get("data_inicio", "")
    if data and (len(data) != 6 or not data.isdigit()):
        erros.append(f"data_inicio: deve ter formato DDMMAA com 6 digitos (recebido: '{data}')")

    return erros


def montar_campos(args, defaults):
    """Monta dict completo de campos a preencher, mesclando CLI + defaults."""
    d408 = defaults.get("opcao_408", {})

    campos = {}

    # Dados obrigatorios (CLI)
    campos["unidade"] = args.unidade.upper()
    campos["cnpj"] = args.cnpj.replace(".", "").replace("/", "").replace("-", "")

    # Dados com defaults
    campos["data_inicio"] = args.data_inicio or d408.get("data_ini", "180226")
    campos["despacho_exp"] = args.despacho_exp or d408.get("exp_emit_despacho_pol", "1,00")
    campos["despacho_rec"] = args.despacho_rec or d408.get("rec_dest_despacho_pol", "1,00")

    return campos


async def criar_comissao(args):
    """
    Fluxo principal de criacao de comissao no SSW 408.

    Usa createNewDoc override para manter DOM in-place.
    Preenche unidade → ENV → CNPJ + campos → ENV2.
    Sucesso = popup fecha (TargetClosedError).
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()
    defaults = carregar_defaults(args.defaults_file)
    campos = montar_campos(args, defaults)
    unidade = campos["unidade"]
    cnpj = campos["cnpj"]

    # Validar campos antes de tentar preencher
    erros_validacao = validar_campos(campos)
    if erros_validacao:
        return gerar_saida(
            False,
            erro="Campos invalidos",
            unidade=unidade,
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

            # ── 2. Abrir opcao 408 (popup) ──
            popup = await abrir_opcao_popup(context, page.frames[0], 408)
            await asyncio.sleep(1)

            # ── 3. Override createNewDoc para manter DOM in-place ──
            await popup.evaluate("""() => {
                createNewDoc = function(pathname) {
                    document.open("text/html", "replace");
                    document.write(valSep.toString());
                    document.close();
                    if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
                };
            }""")

            # ── 4. Preencher unidade e executar ENV ──
            await popup.evaluate(f"""() => {{
                const f2 = document.getElementById('2');
                if (f2) f2.value = '{unidade}';
            }}""")
            await popup.evaluate("ajaxEnvia('ENV', 1)")

            # Esperar DOM atualizar (campo CNPJ '3' aparece apos ENV)
            form_loaded = False
            for _ in range(30):
                has_cnpj = await popup.evaluate(
                    '!!document.getElementById("3")'
                )
                if has_cnpj:
                    form_loaded = True
                    break
                await asyncio.sleep(0.5)

            if not form_loaded:
                screenshot = await capturar_screenshot(popup, f"408_env_timeout_{unidade}")
                return gerar_saida(
                    False,
                    erro=f"Timeout aguardando form 408 apos ENV para unidade {unidade}",
                    unidade=unidade,
                    screenshot=screenshot,
                )

            await asyncio.sleep(1)  # DOM estabilizar

            # ── 5. Checar existencia via campo `acao` ──
            # acao='A' → comissao ja existe (modo alteracao)
            # acao='I' ou outro → inclusao
            acao_status = await popup.evaluate("""() => {
                const el = document.getElementById('acao');
                if (!el) return {exists: false, value: ''};
                return {exists: true, value: el.value};
            }""")

            if acao_status.get("exists") and acao_status.get("value") == "A":
                # Comissao ja existe
                screenshot = await capturar_screenshot(popup, f"408_ja_existe_{unidade}")
                return gerar_saida(
                    True,
                    status="ja_existe",
                    unidade=unidade,
                    cnpj=cnpj,
                    screenshot=screenshot,
                    mensagem=f"Comissao para unidade {unidade} ja existe no SSW.",
                )

            # ── 6. Preencher campos via FIELD_MAP loop ──
            campos_preenchidos = {"unidade": unidade}
            campos_readonly = []
            campos_nao_encontrados = []

            for param, value in campos.items():
                if param == "unidade":
                    continue  # Ja preenchido pelo ENV
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
                popup, f"408_{'dryrun' if args.dry_run else 'presubmit'}_{unidade}_{cnpj}"
            )

            if args.dry_run:
                snapshot = await capturar_campos(popup)
                return gerar_saida(
                    True,
                    modo="dry-run",
                    unidade=unidade,
                    cnpj=cnpj,
                    campos_preenchidos=campos_preenchidos,
                    campos_readonly=campos_readonly,
                    campos_nao_encontrados=campos_nao_encontrados,
                    formulario_snapshot=snapshot,
                    screenshot=screenshot_path,
                    mensagem=f"Preview da comissao {unidade}/{cnpj}. Nenhum dado foi submetido.",
                )

            # ── 8. Submeter formulario ──
            alert_msg = None

            async def on_dialog(dialog):
                nonlocal alert_msg
                alert_msg = dialog.message
                await dialog.accept()

            popup.on("dialog", on_dialog)

            try:
                # ENV2 — Enviar etapa 2 (gravar comissao)
                await popup.evaluate("ajaxEnvia('ENV2', 0)")
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
                        status="criado",
                        unidade=unidade,
                        cnpj=cnpj,
                        campos_preenchidos=campos_preenchidos,
                        mensagem=f"Comissao {unidade} ← CNPJ {cnpj} criada com sucesso.",
                    )

                # Popup NAO fechou — houve ERRO
                erro = None
                if alert_msg:
                    erro = f"SSW alert: {alert_msg}"
                else:
                    # Tentar ler erro do DOM
                    body_text = await popup.evaluate("""() => {
                        return document.body ? document.body.innerText.substring(0, 2000) : '';
                    }""")
                    if body_text:
                        # Buscar padrao de erro SSW
                        for pattern in [
                            r'CNPJ n[aã]o cadastrado como fornecedor',
                            r'n[aã]o cadastrado como transportadora',
                            r'Unidade n[aã]o encontrada',
                            r'ERRO[:\s]+(.*)',
                            r'erro[:\s]+(.*)',
                        ]:
                            match = re.search(pattern, body_text, re.IGNORECASE)
                            if match:
                                erro = match.group(0).strip()[:300]
                                break

                screenshot_pos = await capturar_screenshot(
                    popup, f"408_resultado_{unidade}_{cnpj}"
                )

                if erro:
                    return gerar_saida(
                        False,
                        status="erro",
                        unidade=unidade,
                        cnpj=cnpj,
                        erro=erro,
                        campos_preenchidos=campos_preenchidos,
                        screenshot=screenshot_pos,
                    )

                return gerar_saida(
                    False,
                    status="inconclusivo",
                    unidade=unidade,
                    cnpj=cnpj,
                    erro="Popup nao fechou apos ENV2 (erro provavel, sem mensagem explicita)",
                    campos_preenchidos=campos_preenchidos,
                    screenshot=screenshot_pos,
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
        description="Criar comissao de unidade no SSW (opcao 408)"
    )
    parser.add_argument(
        "--unidade", required=True,
        help="Sigla da unidade (3 chars, ex: VIX, CGR, SSA)"
    )
    parser.add_argument(
        "--cnpj", required=True,
        help="CNPJ do subcontratado (14 digitos numericos)"
    )
    parser.add_argument(
        "--data-inicio", default=None,
        help="Data inicio formato DDMMAA (default: 180226 do ssw_defaults.json)"
    )
    parser.add_argument(
        "--despacho-exp", default=None,
        help='Despacho expedidor em R$ com virgula (default: "1,00" do ssw_defaults.json)'
    )
    parser.add_argument(
        "--despacho-rec", default=None,
        help='Despacho recebedor em R$ com virgula (default: "1,00" do ssw_defaults.json)'
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

    # Validacoes de entrada
    if len(args.unidade) != 3:
        print(json.dumps({
            "sucesso": False,
            "erro": f"Unidade deve ter 3 caracteres (recebido: '{args.unidade}')"
        }))
        sys.exit(1)

    cnpj_clean = args.cnpj.replace(".", "").replace("/", "").replace("-", "")
    if not cnpj_clean.isdigit() or len(cnpj_clean) != 14:
        print(json.dumps({
            "sucesso": False,
            "erro": f"CNPJ deve ter 14 digitos numericos (recebido: '{args.cnpj}')"
        }))
        sys.exit(1)

    asyncio.run(criar_comissao(args))


if __name__ == "__main__":
    main()
