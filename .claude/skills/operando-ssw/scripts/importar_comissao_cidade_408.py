#!/usr/bin/env python3
"""
importar_comissao_cidade_408.py — Importa CSV de comissao por cidade na opcao 408 do SSW.

Fluxo por unidade:
  1. Login SSW (reutiliza sessao)
  2. Abre opcao 408 (popup)
  3. Preenche sigla da unidade no campo f2
  4. ajaxEnvia('CSV_CID', 1) → abre popup de importacao
  5. Upload do CSV via <input type="file">
  6. Submete importacao
  7. Coleta resultado (sucesso/insucesso/contagens)
  8. Fecha popup e repete para proxima unidade

Suporta importacao individual (--csv + --unidade) ou em lote (--csv-dir).

Uso:
    # Importar uma unidade:
    python importar_comissao_cidade_408.py \\
      --csv /tmp/ssw_408_csvs/BVH_comissao_408.csv \\
      --unidade BVH \\
      [--dry-run]

    # Importar todas (lote):
    python importar_comissao_cidade_408.py \\
      --csv-dir /tmp/ssw_408_csvs/ \\
      [--unidades BVH,CGR,SSA] \\
      [--dry-run]

Retorno: JSON {"sucesso": bool, "resultados": [...], ...}

Prerequisitos:
  - CSVs gerados por gerar_csv_comissao_408.py (238 colunas, ';', ISO-8859-1)
  - Comissao geral ja existente para cada unidade (criar_comissao_408.py)
  - Credenciais SSW no .env (SSW_URL, SSW_DOMINIO, SSW_CPF, SSW_LOGIN, SSW_SENHA)
"""
import argparse
import asyncio
import html as html_module
import os
import re
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (
    verificar_credenciais,
    login_ssw,
    abrir_opcao_popup,
    capturar_screenshot,
    gerar_saida,
)


# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

DEFAULT_CSV_DIR = "/tmp/ssw_408_csvs/"
CSV_SUFFIX = "_comissao_408.csv"

# AJAX actions descobertos via exploracao da interface 408
ACTION_IMPORT_CIDADE = "CSV_CID"  # Abre popup de importacao para cidade


# ──────────────────────────────────────────────
# Validacao
# ──────────────────────────────────────────────

def validar_csv_408(csv_path):
    """Valida CSV de comissao 408 antes de importar."""
    erros = []
    info = {"linhas_dados": 0, "unidades": set(), "cidades": []}

    if not os.path.exists(csv_path):
        return False, [f"Arquivo nao encontrado: {csv_path}"], info

    try:
        with open(csv_path, "r", encoding="iso-8859-1") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            return False, [f"Erro ao ler arquivo: {e}"], info

    if len(lines) < 3:
        return False, ["CSV deve ter metadata + header + pelo menos 1 linha de dados"], info

    # Linha 1: metadata, Linha 2: headers, Linhas 3+: dados
    header_line = lines[1].strip()
    headers = header_line.split(";")

    if len(headers) != 238:
        erros.append(f"Esperado 238 colunas no header, encontrado {len(headers)}")

    # Verificar headers chave
    expected_first = ["UNIDADE", "EXPEDICAO/RECEPCAO", "CIDADE/UF", "COD_MERCADORIA"]
    for i, exp in enumerate(expected_first):
        if i < len(headers) and headers[i] != exp:
            erros.append(f"Header col {i}: esperado '{exp}', encontrado '{headers[i]}'")

    # Validar linhas de dados
    for i, line in enumerate(lines[2:], start=3):
        line = line.strip()
        if not line:
            continue
        fields = line.split(";")
        if len(fields) != 238:
            erros.append(f"Linha {i}: {len(fields)} campos (esperado 238)")
            continue

        unidade = fields[0]
        tipo_er = fields[1]
        cidade_uf = fields[2]

        info["unidades"].add(unidade)
        info["linhas_dados"] += 1

        if tipo_er not in ("E", "R"):
            erros.append(f"Linha {i}: EXPEDICAO/RECEPCAO='{tipo_er}' (esperado E ou R)")

        if "/" not in cidade_uf:
            erros.append(f"Linha {i}: CIDADE/UF='{cidade_uf}' sem '/' (formato: CIDADE/UF)")

        if tipo_er == "E" and cidade_uf not in [c for c in info["cidades"]]:
            info["cidades"].append(cidade_uf)

    info["unidades"] = sorted(info["unidades"])
    info["total_cidades"] = len(info["cidades"])

    return len(erros) == 0, erros[:20], info


# ──────────────────────────────────────────────
# Importacao individual
# ──────────────────────────────────────────────

async def importar_csv_cidade(context, page, unidade, csv_path, dry_run=False):
    """
    Importa CSV de comissao por cidade para uma unidade.

    Fluxo:
      1. Abre 408 popup
      2. Preenche unidade no campo f2
      3. ajaxEnvia('CSV_CID', 1) → abre popup de importacao
      4. Upload CSV + submete

    Args:
        context: BrowserContext (para capturar popups)
        page: Page principal (com SSW logado)
        unidade: Sigla IATA (3 chars)
        csv_path: Caminho absoluto do CSV
        dry_run: Se True, apenas navega sem submeter

    Returns:
        dict com resultado
    """
    result = {
        "unidade": unidade,
        "csv": csv_path,
        "sucesso": False,
    }

    # 1. Abrir 408 popup
    try:
        popup_408 = await abrir_opcao_popup(context, page.frames[0], 408)
        await asyncio.sleep(2)
    except Exception as e:
        result["erro"] = f"Falha ao abrir 408: {e}"
        return result

    try:
        # 2. Preencher unidade
        await popup_408.evaluate(f"""() => {{
            const f2 = document.getElementById('2');
            if (f2) f2.value = '{unidade}';
        }}""")
        await asyncio.sleep(0.5)

        # 3. Verificar se link CSV_CID existe
        has_csv_cid = await popup_408.evaluate("""() => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                const onclick = a.getAttribute('onclick') || '';
                if (onclick.includes('CSV_CID')) return true;
            }
            return false;
        }""")

        if not has_csv_cid:
            result["erro"] = "Link 'Importar' (CSV_CID) nao encontrado na tela inicial da 408"
            await capturar_screenshot(popup_408, f"408_no_csv_cid_{unidade}")
            return result

        if dry_run:
            # Em dry-run, capturar screenshot e retornar preview
            screenshot = await capturar_screenshot(popup_408, f"408_dryrun_{unidade}")
            result["sucesso"] = True
            result["modo"] = "dry-run"
            result["screenshot"] = screenshot
            result["mensagem"] = f"Preview: unidade {unidade} pronta para importacao CSV_CID"
            return result

        # 4. Clicar em Importar (CSV_CID) → abre popup de importacao
        import_page = None
        try:
            async with context.expect_page(timeout=15000) as new_page_info:
                await popup_408.evaluate(f"ajaxEnvia('{ACTION_IMPORT_CIDADE}', 1)")
            import_page = await new_page_info.value
            await import_page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
        except Exception as e:
            result["erro"] = f"Falha ao abrir popup de importacao: {e}"
            await capturar_screenshot(popup_408, f"408_import_fail_{unidade}")
            return result

        # 5. Localizar input file
        file_input = await import_page.query_selector('input[type="file"]')
        if not file_input:
            # Tentar outro seletor
            file_input = await import_page.query_selector('input[name="f1"]')
        if not file_input:
            # Capturar DOM para diagnostico
            body_text = await import_page.evaluate(
                "document.body ? document.body.innerText.substring(0, 2000) : ''"
            )
            screenshot = await capturar_screenshot(import_page, f"408_no_fileinput_{unidade}")
            result["erro"] = "Input file nao encontrado na tela de importacao"
            result["body_text"] = body_text[:500]
            result["screenshot"] = screenshot

            # Capturar botoes/links para diagnostico
            elementos = await import_page.evaluate("""() => {
                const r = {links: [], buttons: [], inputs: []};
                document.querySelectorAll('a').forEach(a => {
                    r.links.push({text: (a.textContent||'').trim().substring(0,60), onclick: (a.getAttribute('onclick')||'').substring(0,100)});
                });
                document.querySelectorAll('input').forEach(inp => {
                    r.inputs.push({name: inp.name||'', type: inp.type||'', id: inp.id||''});
                });
                return r;
            }""")
            result["elementos_importacao"] = elementos
            return result

        # 6. Upload do CSV
        await file_input.set_input_files(csv_path)
        await asyncio.sleep(1)

        # Screenshot pre-submit
        await capturar_screenshot(import_page, f"408_presubmit_{unidade}")

        # 7. Submeter importacao
        # Interceptar response para capturar resultado
        import_result_text = None

        async def on_response(response):
            nonlocal import_result_text
            if "/bin/ssw" in response.url and response.status == 200:
                try:
                    body = await response.text()
                    text = re.sub(r'<[^>]+>', ' ', body).strip()
                    text = html_module.unescape(text)  # Decodificar &iacute; etc.
                    text = re.sub(r'\s+', ' ', text)
                    if text and len(text) > 5:
                        import_result_text = text
                except Exception:
                    pass

        import_page.on("response", on_response)

        # Descobrir botao de submit na pagina de importacao
        submit_action = await import_page.evaluate("""() => {
            // Procurar links/botoes com onclick contendo 'ajaxEnvia'
            const actions = [];
            document.querySelectorAll('a[onclick], input[onclick]').forEach(el => {
                const onclick = el.getAttribute('onclick') || '';
                if (onclick.includes('ajaxEnvia') || onclick.includes('IMPORTA')) {
                    actions.push({
                        text: (el.value || el.textContent || '').trim().substring(0, 60),
                        onclick: onclick.substring(0, 150),
                        tag: el.tagName,
                    });
                }
            });
            return actions;
        }""")

        result["submit_actions_found"] = submit_action

        # Tentar submeter — procurar acao de importacao
        submitted = False
        for action in submit_action:
            onclick = action["onclick"]
            if "IMPORTA" in onclick.upper() or "ENV" in onclick.upper():
                try:
                    await import_page.evaluate(onclick.replace(";return false;", "").replace("return false;", ""))
                    submitted = True
                    break
                except Exception:
                    pass

        if not submitted:
            # Fallback: tentar ajaxEnvia('IMPORTA2', 0) diretamente
            try:
                await import_page.evaluate("ajaxEnvia('IMPORTA2', 0)")
                submitted = True
            except Exception as e:
                result["erro"] = f"Nenhum botao de submit encontrado e fallback falhou: {e}"
                return result

        # Esperar processamento
        await asyncio.sleep(10)

        import_page.remove_listener("response", on_response)

        # 8. Fallback: verificar iframe (SSW usa iframe hidden para upload)
        if not import_result_text:
            try:
                iframe_body = await import_page.evaluate("""() => {
                    const iframe = document.querySelector('#uploadframe');
                    if (iframe && iframe.contentDocument && iframe.contentDocument.body) {
                        return iframe.contentDocument.body.innerText;
                    }
                    return '';
                }""")
                if iframe_body:
                    import_result_text = iframe_body.strip()
            except Exception:
                pass

        # Fallback 2: body text da propria pagina
        if not import_result_text:
            try:
                import_result_text = await import_page.evaluate(
                    "document.body ? document.body.innerText.substring(0, 3000) : ''"
                )
            except Exception:
                pass

        # Screenshot pos-submit
        try:
            screenshot_pos = await capturar_screenshot(import_page, f"408_resultado_{unidade}")
            result["screenshot"] = screenshot_pos
        except Exception:
            pass

        # 9. Analisar resultado
        if import_result_text:
            result["resposta_ssw"] = import_result_text[:1000]

            # Detectar erro
            erro_detectado = any(
                kw in import_result_text.lower()
                for kw in ["erro", "error", "informe", "não encontrad", "inválid"]
            )

            # Extrair contagens — formato SSW real:
            # "Processamento concluído. Tabelas incluídas: 12 Alteradas: 2 Não inclusas: 0"
            match_inc = re.search(r'[Ii]nclu[ií]das?:\s*(\d+)', import_result_text)
            match_alt = re.search(r'[Aa]lteradas?:\s*(\d+)', import_result_text)
            match_nao = re.search(r'[Nn][ãa]o\s+inclusas?:\s*(\d+)', import_result_text)

            if match_inc:
                result["inclusoes"] = int(match_inc.group(1))
            if match_alt:
                result["alteracoes"] = int(match_alt.group(1))
            if match_nao:
                result["nao_inclusas"] = int(match_nao.group(1))

            if erro_detectado:
                result["sucesso"] = False
                result["erro"] = f"SSW reportou erro: {import_result_text[:300]}"
            else:
                result["sucesso"] = True
                result["mensagem"] = f"Importacao CSV cidade para {unidade} concluida"
        else:
            result["sucesso"] = False
            result["erro"] = "Nenhuma resposta do SSW apos submissao"

        # Fechar popup de importacao
        try:
            await import_page.close()
        except Exception:
            pass

    except Exception as e:
        result["erro"] = f"Erro inesperado: {e}"
        try:
            await capturar_screenshot(popup_408, f"408_erro_{unidade}")
        except Exception:
            pass

    finally:
        # Fechar popup 408
        try:
            await popup_408.close()
        except Exception:
            pass

    return result


# ──────────────────────────────────────────────
# Importacao em lote
# ──────────────────────────────────────────────

async def importar_lote(args):
    """Importa CSVs para multiplas unidades."""
    from playwright.async_api import async_playwright

    verificar_credenciais()

    # Resolver lista de CSVs a importar
    csvs = []

    if args.csv:
        # Modo individual
        csv_path = os.path.abspath(args.csv)
        if not args.unidade:
            # Tentar extrair unidade do nome do arquivo
            basename = os.path.basename(csv_path)
            if CSV_SUFFIX in basename:
                args.unidade = basename.replace(CSV_SUFFIX, "")
            else:
                return gerar_saida(False, erro="--unidade obrigatorio quando --csv nao segue padrao IATA_comissao_408.csv")

        csvs.append({"unidade": args.unidade.upper(), "csv": csv_path})

    elif args.csv_dir:
        # Modo lote
        csv_dir = os.path.abspath(args.csv_dir)
        if not os.path.isdir(csv_dir):
            return gerar_saida(False, erro=f"Diretorio nao encontrado: {csv_dir}")

        # Listar CSVs no diretorio
        for fname in sorted(os.listdir(csv_dir)):
            if fname.endswith(CSV_SUFFIX):
                iata = fname.replace(CSV_SUFFIX, "")
                csvs.append({"unidade": iata, "csv": os.path.join(csv_dir, fname)})

        if not csvs:
            return gerar_saida(False, erro=f"Nenhum CSV *{CSV_SUFFIX} encontrado em {csv_dir}")

        # Filtrar por unidades especificas
        if args.unidades:
            filtro = [u.strip().upper() for u in args.unidades.split(",")]
            csvs = [c for c in csvs if c["unidade"] in filtro]
            if not csvs:
                return gerar_saida(False, erro=f"Nenhuma unidade do filtro encontrada: {filtro}")

    else:
        return gerar_saida(False, erro="Especifique --csv FILE ou --csv-dir DIR")

    # Validar todos os CSVs antes de importar
    print(f">>> Validando {len(csvs)} CSVs...")
    validacoes = []
    todos_validos = True

    for item in csvs:
        valido, erros, info = validar_csv_408(item["csv"])
        item["valido"] = valido
        item["erros_validacao"] = erros
        item["info"] = info
        if not valido:
            todos_validos = False
        validacoes.append({
            "unidade": item["unidade"],
            "csv": item["csv"],
            "valido": valido,
            "erros": erros[:5],
            "linhas": info["linhas_dados"],
            "cidades": info["total_cidades"],
        })

    if args.dry_run:
        return gerar_saida(
            todos_validos,
            modo="dry-run",
            total_unidades=len(csvs),
            validacoes=validacoes,
            mensagem=f"Preview: {len(csvs)} unidades, {'todos validos' if todos_validos else 'ERROS encontrados'}",
        )

    if not todos_validos:
        invalidos = [v for v in validacoes if not v["valido"]]
        return gerar_saida(
            False,
            erro=f"{len(invalidos)} CSVs invalidos — corrigir antes de importar",
            invalidos=invalidos,
        )

    # Importar
    print(f">>> Importando {len(csvs)} CSVs no SSW...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 1000},
            accept_downloads=True,
        )
        page = await context.new_page()

        # Login
        print(">>> Login SSW...")
        if not await login_ssw(page):
            return gerar_saida(False, erro="Falha no login SSW")
        print(">>> Login OK")
        await asyncio.sleep(2)

        resultados = []
        sucessos = 0
        falhas = 0

        for i, item in enumerate(csvs, 1):
            unidade = item["unidade"]
            csv_path = item["csv"]
            print(f"\n>>> [{i}/{len(csvs)}] Importando {unidade}...")

            resultado = await importar_csv_cidade(
                context, page, unidade, csv_path, dry_run=False
            )
            resultados.append(resultado)

            if resultado.get("sucesso"):
                sucessos += 1
                inc = resultado.get("inclusoes", "?")
                alt = resultado.get("alteracoes", "?")
                nao = resultado.get("nao_inclusas", "?")
                print(f"    OK: incluidas={inc}, alteradas={alt}, nao_inclusas={nao}")
            else:
                falhas += 1
                print(f"    ERRO: {resultado.get('erro', 'desconhecido')}")

            # Pausa entre importacoes para nao sobrecarregar SSW
            if i < len(csvs):
                await asyncio.sleep(3)

        await browser.close()

    return gerar_saida(
        falhas == 0,
        modo="importacao",
        total=len(csvs),
        sucessos=sucessos,
        falhas=falhas,
        resultados=resultados,
        mensagem=f"Importacao: {sucessos}/{len(csvs)} unidades OK, {falhas} falhas",
    )


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Importa CSV de comissao por cidade na opcao 408 do SSW"
    )

    # Modo individual
    parser.add_argument(
        "--csv",
        default=None,
        help="Caminho do CSV a importar (modo individual)",
    )
    parser.add_argument(
        "--unidade",
        default=None,
        help="Sigla IATA da unidade (modo individual). Auto-detectado do nome do arquivo se omitido.",
    )

    # Modo lote
    parser.add_argument(
        "--csv-dir",
        default=None,
        help=f"Diretorio com CSVs *{CSV_SUFFIX} (modo lote, default: {DEFAULT_CSV_DIR})",
    )
    parser.add_argument(
        "--unidades",
        default=None,
        help="Filtrar por unidades IATA (virgula-sep, ex: BVH,CGR). Sem = todas",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida CSVs e navega sem submeter importacao",
    )

    args = parser.parse_args()

    if not args.csv and not args.csv_dir:
        # Default: usar csv-dir padrao
        if os.path.isdir(DEFAULT_CSV_DIR):
            args.csv_dir = DEFAULT_CSV_DIR
        else:
            parser.error("Especifique --csv FILE ou --csv-dir DIR")

    asyncio.run(importar_lote(args))


if __name__ == "__main__":
    main()
