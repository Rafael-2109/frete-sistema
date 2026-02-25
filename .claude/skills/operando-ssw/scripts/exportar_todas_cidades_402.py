#!/usr/bin/env python3
"""
exportar_todas_cidades_402.py — Exporta CSV de cidades atendidas da 402 para TODAS as 27 UFs.

Reutiliza UMA sessao de browser para exportar o CSV de cada UF, evitando
27 ciclos de login separados. Baseado em exportar_cidades_402.py (UF unica).

IMPORTANTE: Chama _MOD_CSV na tela INICIAL (ANTES de VIS_UF).
Apos VIS_UF o botao CSV desaparece.

Uso:
    python exportar_todas_cidades_402.py [--output-dir /tmp/402_export_all/] [--ufs AC,AL,BA] [--dry-run]

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


# Todas as 27 UFs brasileiras em ordem alfabetica
TODAS_UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

# Timeout para captura de CSV (segundos)
CSV_CAPTURE_TIMEOUT = 15

# Pausa entre UFs (segundos)
PAUSA_ENTRE_UFS = 3


async def exportar_csv_uf(context, page, uf, output_path):
    """
    Exporta CSV da 402 para uma UF, reutilizando sessao existente.

    Retorna dict com resultado (sem imprimir JSON).
    """
    popup = None
    try:
        # 1. Abrir popup 402
        popup = await abrir_opcao_popup(context, page.frames[0], 402, timeout_s=30)
        await asyncio.sleep(2)

        # 2. Preencher UF no campo id="2"
        await popup.evaluate(f"""() => {{
            const el = document.getElementById('2');
            if (el) el.value = '{uf}';
        }}""")

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
                if (";" in text and len(text) > 500
                        and ("csv" in ct.lower() or "csv" in disp.lower()
                             or "ssw0424" in url or "octet" in ct.lower())):
                    csv_content = text
            except Exception:
                pass

        popup.on("response", on_response)

        # ── Estrategia 3: createNewDoc override (captura valSep no JS) ──
        await popup.evaluate("""() => {
            window._origCreateNewDoc = window.createNewDoc;
            createNewDoc = function(pathname) {
                window._csvResult = valSep ? valSep.toString() : null;
                try { window._origCreateNewDoc(pathname); } catch(e) {}
            };
        }""")

        # ── Chamar _MOD_CSV (ANTES de VIS_UF!) ──
        await popup.evaluate("ajaxEnvia('_MOD_CSV', 0)")

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
            if csv_result and ";" in csv_result and len(csv_result) > 500:
                csv_content = csv_result

        # Fallback: nova pagina aberta pelo SSW
        if not csv_content:
            for pg in context.pages:
                if pg != page and pg != popup:
                    try:
                        text = await pg.evaluate(
                            "() => document.body?.innerText || ''"
                        )
                        if ";" in text and len(text) > 500:
                            csv_content = text
                            # Fechar pagina extra
                            await pg.close()
                            break
                    except Exception:
                        pass

        if not csv_content:
            return {"uf": uf, "sucesso": False, "erro": f"CSV nao capturado para UF={uf}"}

        # Salvar
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="iso-8859-1") as f:
            f.write(csv_content)

        # Analisar
        lines = csv_content.strip().split("\n")
        total_linhas = len(lines) - 1  # Descontar header
        header = lines[0]
        cols = [c.strip() for c in header.split(";") if c.strip()]

        return {
            "uf": uf,
            "sucesso": True,
            "linhas": total_linhas,
            "colunas": len(cols),
            "arquivo": output_path,
        }

    except Exception as e:
        return {"uf": uf, "sucesso": False, "erro": str(e)}

    finally:
        # Fechar popup (e quaisquer paginas extras)
        if popup:
            try:
                await popup.close()
            except Exception:
                pass
        # Limpar paginas extras que possam ter sido abertas
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
    """Exporta CSV da 402 para todas as UFs."""
    from playwright.async_api import async_playwright

    verificar_credenciais()

    # Resolver lista de UFs
    if args.ufs:
        ufs = [u.strip().upper() for u in args.ufs.split(",")]
        invalidas = [u for u in ufs if u not in TODAS_UFS]
        if invalidas:
            return gerar_saida(False, erro=f"UFs invalidas: {invalidas}. Validas: {TODAS_UFS}")
    else:
        ufs = TODAS_UFS[:]

    output_dir = args.output_dir

    if args.dry_run:
        return gerar_saida(
            True,
            modo="dry-run",
            total=len(ufs),
            ufs=ufs,
            output_dir=output_dir,
            mensagem=f"Exportaria CSV da 402 para {len(ufs)} UFs em {output_dir}. "
                      "Nenhuma acao executada.",
        )

    # Criar diretorio de saida
    os.makedirs(output_dir, exist_ok=True)

    print(f">>> Exportando 402 para {len(ufs)} UFs...")

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

        for i, uf in enumerate(ufs, 1):
            output_path = os.path.join(output_dir, f"{uf.lower()}_402_export.csv")
            print(f"\n>>> [{i}/{len(ufs)}] Exportando UF={uf}...")

            resultado = await exportar_csv_uf(context, page, uf, output_path)

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
                        print(f"    >>> Re-login OK, retentando UF={uf}...")
                        resultado = await exportar_csv_uf(context, page, uf, output_path)
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

            # Pausa entre UFs
            if i < len(ufs):
                await asyncio.sleep(PAUSA_ENTRE_UFS)

        await browser.close()

    return gerar_saida(
        falhas == 0,
        total=len(ufs),
        exportados=exportados,
        falhas=falhas,
        detalhes=detalhes,
        output_dir=output_dir,
        mensagem=f"Exportacao 402: {exportados}/{len(ufs)} UFs OK, {falhas} falhas",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Exporta CSV de cidades atendidas da 402 para todas as 27 UFs."
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/402_export_all/",
        help="Diretorio de saida para os CSVs (default: /tmp/402_export_all/)",
    )
    parser.add_argument(
        "--ufs",
        default=None,
        help="Filtro de UFs (virgula-sep, ex: AC,BA,SP). Default: todas 27 UFs.",
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
