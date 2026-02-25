#!/usr/bin/env python3
"""
exportar_comissao_cidade_408.py — Exporta CSV de comissao por cidade da 408 por unidade.

Para cada unidade das 56 fornecidas, navega a opcao 408, preenche a unidade,
carrega o formulario (ENV), e clica "Baixar arquivo CSV" na secao
"Especifica para CIDADE" (acao LINK_DOWN_CID).

Reutiliza UMA sessao de browser para todas as unidades.

Uso:
    python exportar_comissao_cidade_408.py \\
      [--unidades MAO,CGR,CGB]  \\
      [--output-dir /tmp/408_export/] \\
      [--dry-run]

Retorno: JSON {"sucesso": bool, "total": N, "exportados": N, "falhas": N, "detalhes": [...]}
"""
import argparse
import asyncio
import os
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import verificar_credenciais, login_ssw, abrir_opcao_popup, gerar_saida, SSW_URL


# Todas as 56 unidades fornecidas pelo usuario (da 401)
TODAS_UNIDADES = [
    "MAO", "CGR", "CGB", "ALE", "CAR", "JPA", "MCZ", "NAT", "SSA", "VIX",
    "AJU", "CWB", "FLN", "DAG", "PAS", "POA", "FOR", "DJJ", "FEC", "FRT",
    "G10", "MTZ", "GRM", "PAU", "EUN", "FEI", "IOS", "BPS", "TXF", "VCQ",
    "VDC", "ZZ9", "Z02", "AUX", "BSS", "GYN", "GRP", "PMW", "PDT", "GIG",
    "LDB", "MGF", "OAL", "PVH", "RBR", "BVH", "GJM", "ARU", "AQM", "JPR",
    "BEL", "VEL", "MCP", "REC", "SLZ", "THE",
]

# Timeout para captura de CSV (segundos)
CSV_CAPTURE_TIMEOUT = 15

# Pausa entre unidades (segundos)
PAUSA_ENTRE_UNIDADES = 3


async def exportar_csv_unidade(context, page, unidade, output_path):
    """
    Exporta CSV de comissao por cidade da 408 para uma unidade.

    Fluxo:
      1. Abre 408 (popup)
      2. Override createNewDoc para manter DOM in-place
      3. Preenche unidade no campo id="2"
      4. ajaxEnvia('ENV', 1) — carrega form da comissao
      5. Aguarda link id="10" (confirma que tela carregou)
      6. Registra handlers download + response interceptor
      7. ajaxEnvia('LINK_DOWN_CID', 0) — dispara download CSV
      8. Captura CSV via 3 estrategias
      9. Salva arquivo

    Retorna dict com resultado (sem imprimir JSON).
    """
    popup = None
    try:
        # 1. Abrir popup 408
        popup = await abrir_opcao_popup(context, page.frames[0], 408, timeout_s=30)
        await asyncio.sleep(1)

        # 2. Override createNewDoc para manter DOM in-place apos ENV
        await popup.evaluate("""() => {
            createNewDoc = function(pathname) {
                document.open("text/html", "replace");
                document.write(valSep.toString());
                document.close();
                if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
            };
        }""")

        # 3. Preencher unidade no campo id="2"
        await popup.evaluate(f"""() => {{
            const f2 = document.getElementById('2');
            if (f2) f2.value = '{unidade}';
        }}""")

        # 4. ajaxEnvia('ENV', 1) — carrega dados da comissao
        await popup.evaluate("ajaxEnvia('ENV', 1)")

        # 5. Aguardar form carregar — verificar presenca do link id="10"
        form_loaded = False
        for _ in range(30):
            has_link = await popup.evaluate("""() => {
                const el = document.getElementById('10');
                if (el) return true;
                // Fallback: procurar link com LINK_DOWN_CID no onclick
                const links = document.querySelectorAll('a');
                for (const a of links) {
                    const onclick = a.getAttribute('onclick') || '';
                    if (onclick.includes('LINK_DOWN_CID')) return true;
                }
                return false;
            }""")
            if has_link:
                form_loaded = True
                break
            await asyncio.sleep(0.5)

        if not form_loaded:
            # Verificar se comissao existe para esta unidade
            body_text = await popup.evaluate(
                "() => document.body ? document.body.innerText.substring(0, 2000) : ''"
            )
            if "nao encontrad" in body_text.lower() or "não encontrad" in body_text.lower():
                return {
                    "unidade": unidade,
                    "sucesso": False,
                    "erro": f"Comissao nao encontrada para unidade {unidade}",
                }
            return {
                "unidade": unidade,
                "sucesso": False,
                "erro": f"Timeout aguardando form 408 (link LINK_DOWN_CID nao encontrado) para {unidade}",
            }

        await asyncio.sleep(1)  # DOM estabilizar

        csv_content = None

        # ── Estrategia 1: Download handler ──
        async def on_download(download):
            nonlocal csv_content
            tmp_path = output_path + ".download"
            await download.save_as(tmp_path)
            with open(tmp_path, "rb") as f:
                csv_content = f.read().decode("iso-8859-1", errors="replace")
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        popup.on("download", on_download)

        # ── Estrategia 2: Response interceptor ──
        async def on_response(response):
            nonlocal csv_content
            if csv_content:
                return
            url = response.url
            ct = response.headers.get("content-type", "")
            disp = response.headers.get("content-disposition", "")
            try:
                body = await response.body()
                text = body.decode("iso-8859-1", errors="replace")
                if (";" in text and len(text) > 200
                        and ("csv" in ct.lower() or "csv" in disp.lower()
                             or "ssw0424" in url or "octet" in ct.lower()
                             or "ssw04" in url)):
                    csv_content = text
            except Exception:
                pass

        popup.on("response", on_response)

        # ── Estrategia 3: Override createNewDoc para capturar valSep no JS ──
        # Re-override para capturar a response do LINK_DOWN_CID
        await popup.evaluate("""() => {
            window._origCreateNewDoc2 = window.createNewDoc;
            createNewDoc = function(pathname) {
                window._csvResult = valSep ? valSep.toString() : null;
                try { window._origCreateNewDoc2(pathname); } catch(e) {}
            };
        }""")

        # 6. ajaxEnvia('LINK_DOWN_CID', 0) — dispara download CSV
        await popup.evaluate("ajaxEnvia('LINK_DOWN_CID', 0)")

        # Aguardar captura do CSV
        for _ in range(CSV_CAPTURE_TIMEOUT * 2):
            if csv_content:
                break
            await asyncio.sleep(0.5)

        popup.remove_listener("download", on_download)
        popup.remove_listener("response", on_response)

        # Fallback: JS variable
        if not csv_content:
            csv_result = await popup.evaluate("() => window._csvResult || ''")
            if csv_result and ";" in csv_result and len(csv_result) > 200:
                csv_content = csv_result

        # Fallback: nova pagina aberta pelo SSW
        if not csv_content:
            for pg in context.pages:
                if pg != page and pg != popup:
                    try:
                        text = await pg.evaluate(
                            "() => document.body?.innerText || ''"
                        )
                        if ";" in text and len(text) > 200:
                            csv_content = text
                            await pg.close()
                            break
                    except Exception:
                        pass

        if not csv_content:
            return {
                "unidade": unidade,
                "sucesso": False,
                "erro": f"CSV nao capturado para unidade={unidade}",
            }

        # Salvar
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="iso-8859-1") as f:
            f.write(csv_content)

        # Analisar
        lines = csv_content.strip().split("\n")
        total_linhas = len(lines) - 1  # Descontar header (pelo menos 1)
        if total_linhas < 0:
            total_linhas = 0

        return {
            "unidade": unidade,
            "sucesso": True,
            "linhas": total_linhas,
            "arquivo": output_path,
        }

    except Exception as e:
        return {"unidade": unidade, "sucesso": False, "erro": str(e)}

    finally:
        # Fechar popup e quaisquer paginas extras
        if popup:
            try:
                await popup.close()
            except Exception:
                pass
        for pg in context.pages:
            if pg != page:
                try:
                    await pg.close()
                except Exception:
                    pass


async def tentar_relogin(page):
    """
    Tenta re-login quando sessao SSW expira.

    Navega de volta para a URL de login e refaz o processo.
    """
    try:
        await page.goto(SSW_URL, wait_until="networkidle", timeout=30000)
    except Exception:
        pass
    await asyncio.sleep(2)
    return await login_ssw(page)


async def exportar_todas(args):
    """Exporta CSV de comissao por cidade da 408 para todas as unidades."""
    from playwright.async_api import async_playwright

    verificar_credenciais()

    # Resolver lista de unidades
    if args.unidades:
        unidades = [u.strip().upper() for u in args.unidades.split(",")]
    else:
        unidades = TODAS_UNIDADES[:]

    output_dir = args.output_dir

    if args.dry_run:
        return gerar_saida(
            True,
            modo="dry-run",
            total=len(unidades),
            unidades=unidades,
            output_dir=output_dir,
            mensagem=f"Exportaria CSV da 408 para {len(unidades)} unidades em {output_dir}. "
                      "Nenhuma acao executada.",
        )

    # Criar diretorio de saida
    os.makedirs(output_dir, exist_ok=True)

    print(f">>> Exportando 408 (comissao por cidade) para {len(unidades)} unidades...")

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
            await browser.close()
            return gerar_saida(False, erro="Login SSW falhou")
        print(">>> Login OK")
        await asyncio.sleep(2)

        detalhes = []
        exportados = 0
        falhas = 0

        for i, unidade in enumerate(unidades, 1):
            output_path = os.path.join(output_dir, f"{unidade}_408_export.csv")
            print(f"\n>>> [{i}/{len(unidades)}] Exportando unidade={unidade}...")

            resultado = await exportar_csv_unidade(context, page, unidade, output_path)

            if resultado.get("sucesso"):
                exportados += 1
                print(f"    OK: {resultado.get('linhas', '?')} linhas → {output_path}")
            else:
                erro = resultado.get("erro", "desconhecido")
                print(f"    ERRO: {erro}")

                # Tentar re-login se parece ser sessao expirada
                if "timeout" in erro.lower() or "closed" in erro.lower() or "target" in erro.lower():
                    print(f"    >>> Tentando re-login...")
                    if await tentar_relogin(page):
                        print(f"    >>> Re-login OK, retentando unidade={unidade}...")
                        resultado = await exportar_csv_unidade(context, page, unidade, output_path)
                        if resultado.get("sucesso"):
                            exportados += 1
                            print(f"    OK (retentativa): {resultado.get('linhas', '?')} linhas")
                        else:
                            falhas += 1
                            print(f"    ERRO (retentativa): {resultado.get('erro', 'desconhecido')}")
                    else:
                        falhas += 1
                        print(f"    >>> Re-login FALHOU")
                else:
                    falhas += 1

            detalhes.append(resultado)

            # Pausa entre unidades
            if i < len(unidades):
                await asyncio.sleep(PAUSA_ENTRE_UNIDADES)

        await browser.close()

    return gerar_saida(
        falhas == 0,
        total=len(unidades),
        exportados=exportados,
        falhas=falhas,
        detalhes=detalhes,
        output_dir=output_dir,
        mensagem=f"Exportacao 408: {exportados}/{len(unidades)} unidades OK, {falhas} falhas",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Exporta CSV de comissao por cidade da 408 por unidade."
    )
    parser.add_argument(
        "--unidades",
        default=None,
        help="Filtro de unidades (virgula-sep, ex: MAO,CGR,BVH). Default: todas 56.",
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/408_export/",
        help="Diretorio de saida para os CSVs (default: /tmp/408_export/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra o que seria exportado, sem executar.",
    )

    args = parser.parse_args()

    asyncio.run(exportar_todas(args))


if __name__ == "__main__":
    main()
