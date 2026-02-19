#!/usr/bin/env python3
"""
exportar_cidades_402.py — Exporta CSV de cidades atendidas da opcao 402 do SSW.

Exporta o CSV completo de uma UF, preservando todos os 45 campos exatamente
como o SSW espera. Este CSV pode ser modificado em Python e reimportado
com importar_cidades_402.py.

IMPORTANTE: Chama _MOD_CSV na tela INICIAL (ANTES de VIS_UF).
Apos VIS_UF o botao CSV desaparece.

Uso:
    python exportar_cidades_402.py --uf BA [--output /tmp/ba_402_export.csv] [--dry-run]

Retorno: JSON {"sucesso": bool, "arquivo": "...", "total_linhas": N, ...}
"""
import argparse
import asyncio
import json
import os
import sys

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import verificar_credenciais, login_ssw, abrir_opcao_popup, gerar_saida


async def exportar_csv(uf, output_path):
    """
    Exporta CSV da 402 para a UF especificada.

    Mecanismo:
    1. Abre 402 (popup)
    2. Preenche UF no campo id="2"
    3. Override createNewDoc para capturar valSep (resultado AJAX)
    4. Chama _MOD_CSV (ANTES de VIS_UF — botao so existe na tela inicial)
    5. Captura CSV via 3 estrategias: download handler, response interceptor, JS variable
    6. Salva no output_path
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 1000},
            accept_downloads=True,
        )
        page = await context.new_page()

        if not await login_ssw(page):
            await browser.close()
            return gerar_saida(False, erro="Login SSW falhou")

        popup = await abrir_opcao_popup(context, page.frames[0], 402, timeout_s=30)
        await asyncio.sleep(2)

        # Preencher UF
        await popup.evaluate(f"""() => {{
            const el = document.getElementById('2');
            if (el) el.value = '{uf.upper()}';
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
        await asyncio.sleep(10)

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
                            break
                    except Exception:
                        pass

        await browser.close()

        if not csv_content:
            return gerar_saida(False, erro=f"CSV nao capturado para UF={uf}")

        # Salvar
        with open(output_path, "w", encoding="iso-8859-1") as f:
            f.write(csv_content)

        # Analisar
        lines = csv_content.strip().split("\n")
        header = lines[0]
        cols = [c.strip() for c in header.split(";") if c.strip()]

        # Contar cidades com/sem unidade
        cidades_com_unidade = 0
        cidades_sem_unidade = 0
        unidades = set()
        for line in lines[1:]:
            fields = line.split(";")
            if len(fields) > 2:
                unidade = fields[2].strip()
                if unidade:
                    cidades_com_unidade += 1
                    unidades.add(unidade)
                else:
                    cidades_sem_unidade += 1

        return gerar_saida(
            True,
            arquivo=output_path,
            uf=uf.upper(),
            total_linhas=len(lines) - 1,
            total_colunas=len(cols),
            cidades_com_unidade=cidades_com_unidade,
            cidades_sem_unidade=cidades_sem_unidade,
            unidades_encontradas=sorted(unidades),
            amostra=lines[1][:300] if len(lines) > 1 else None,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Exporta CSV de cidades atendidas da opcao 402 do SSW."
    )
    parser.add_argument(
        "--uf", required=True,
        help="UF para exportar (ex: BA, SP, MS)",
    )
    parser.add_argument(
        "--output",
        help="Caminho do CSV de saida (default: /tmp/{uf}_402_export.csv)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Apenas mostra o que seria exportado (verifica login e tela)",
    )
    args = parser.parse_args()

    uf = args.uf.upper()
    if len(uf) != 2:
        print(json.dumps({"sucesso": False, "erro": "UF deve ter 2 caracteres"}))
        sys.exit(1)

    output_path = args.output or f"/tmp/{uf.lower()}_402_export.csv"

    if args.dry_run:
        print(json.dumps({
            "sucesso": True,
            "modo": "dry-run",
            "uf": uf,
            "output": output_path,
            "mensagem": f"Exportaria CSV da UF={uf} para {output_path}. "
                        "Nenhuma acao executada.",
        }, indent=2, ensure_ascii=False))
        return

    asyncio.run(exportar_csv(uf, output_path))


if __name__ == "__main__":
    main()
