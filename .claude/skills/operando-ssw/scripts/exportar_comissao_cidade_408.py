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


async def _find_page_with_link(context, main_page, link_text):
    """Procura em todas as paginas do contexto a que contem o link especificado."""
    for pg in context.pages:
        if pg == main_page:
            continue
        try:
            has = await pg.evaluate(f"""() => {{
                const links = document.querySelectorAll('a[onclick]');
                for (const a of links) {{
                    if ((a.getAttribute('onclick') || '').includes('{link_text}')) return true;
                }}
                return false;
            }}""")
            if has:
                return pg
        except Exception:
            pass
    return None


async def exportar_csv_unidade(context, page, unidade, output_path):
    """
    Exporta CSV de comissao por cidade da 408 para uma unidade.

    Mecanismo descoberto via diagnostico:
    - NÃO usar createNewDoc override (quebra ajaxEnvia subsequente)
    - Deixar SSW navegar nativamente (ENV abre nova pagina)
    - LINK_DOWN_CID dispara cadeia AJAX que gera download real do browser
    - Capturar via Playwright download handler

    Fluxo:
      1. Abre 408 (popup)
      2. Preenche unidade no campo id="2"
      3. ajaxEnvia('ENV', 1) — SSW nativo abre nova pagina
      4. Encontra pagina com link LINK_DOWN_CID
      5. Registra download handler
      6. ajaxEnvia('LINK_DOWN_CID', 0) — dispara cadeia AJAX → download
      7. Captura CSV via download handler
      8. Salva arquivo

    Retorna dict com resultado (sem imprimir JSON).
    """
    popup = None
    try:
        # 1. Abrir popup 408
        popup = await abrir_opcao_popup(context, page.frames[0], 408, timeout_s=30)
        await asyncio.sleep(1)

        # 2. Preencher unidade no campo id="2" (SEM override de createNewDoc)
        await popup.evaluate(f"""() => {{
            const f2 = document.getElementById('2');
            if (f2) f2.value = '{unidade}';
        }}""")

        # 3. ajaxEnvia('ENV', 1) — SSW nativo navega (pode abrir nova pagina)
        await popup.evaluate("ajaxEnvia('ENV', 1)")
        await asyncio.sleep(5)

        # 4. Encontrar a pagina com LINK_DOWN_CID (busca em todas)
        target_page = await _find_page_with_link(context, page, "LINK_DOWN_CID")

        if not target_page:
            # Esperar mais e tentar novamente
            await asyncio.sleep(5)
            target_page = await _find_page_with_link(context, page, "LINK_DOWN_CID")

        if not target_page:
            # Verificar se alguma pagina mostra erro
            for pg in context.pages:
                if pg == page:
                    continue
                try:
                    body_text = await pg.evaluate(
                        "() => document.body ? document.body.innerText.substring(0, 2000) : ''"
                    )
                    if "nao encontrad" in body_text.lower() or "não encontrad" in body_text.lower():
                        return {
                            "unidade": unidade,
                            "sucesso": False,
                            "erro": f"Comissao nao encontrada para unidade {unidade}",
                        }
                except Exception:
                    pass
            return {
                "unidade": unidade,
                "sucesso": False,
                "erro": f"Timeout: link LINK_DOWN_CID nao encontrado em nenhuma pagina para {unidade}",
            }

        # 5. Registrar download handler na pagina-alvo
        csv_content = None
        download_done = asyncio.Event()

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
            download_done.set()

        target_page.on("download", on_download)

        # Tambem monitorar downloads em novas paginas (SSW pode abrir popup para download)
        def on_page(new_page):
            new_page.on("download", on_download)

        context.on("page", on_page)

        # 6. ajaxEnvia('LINK_DOWN_CID', 0) — dispara cadeia AJAX → download
        await target_page.evaluate("ajaxEnvia('LINK_DOWN_CID', 0)")

        # 7. Aguardar download (timeout 30s — cadeia AJAX tem 3 etapas)
        try:
            await asyncio.wait_for(download_done.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass

        target_page.remove_listener("download", on_download)
        context.remove_listener("page", on_page)

        if not csv_content:
            return {
                "unidade": unidade,
                "sucesso": False,
                "erro": f"CSV nao capturado (download nao disparou) para unidade={unidade}",
            }

        # 8. Salvar
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="iso-8859-1") as f:
            f.write(csv_content)

        # Analisar
        lines = csv_content.strip().split("\n")
        total_linhas = len(lines) - 1  # Descontar header
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
        # Fechar TODAS as paginas extras (popup, nova pagina do ENV, etc.)
        for pg in list(context.pages):
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
