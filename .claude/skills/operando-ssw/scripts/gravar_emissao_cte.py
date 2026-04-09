#!/usr/bin/env python3
"""
Gravador de percurso — Emissão CTe SSW (tela 004).

Faz login automatico, abre tela 004, seleciona "N Normal", e PAUSA
com o Playwright Inspector aberto para o usuario fazer o percurso manual.

O Inspector grava todas as acoes (cliques, preenchimentos, navegacao).
Ao final, copie o codigo gerado do painel lateral.

Uso:
    PWDEBUG=1 python .claude/skills/operando-ssw/scripts/gravar_emissao_cte.py [--filial CAR]

Nota: PWDEBUG=1 abre o Inspector automaticamente.
"""
import asyncio
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import verificar_credenciais, login_ssw, abrir_opcao_popup


CREATE_NEW_DOC_OVERRIDE = """() => {
    createNewDoc = function(pathname) {
        document.open("text/html", "replace");
        document.write(valSep.toString());
        document.close();
        if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
    };
}"""


async def main():
    from playwright.async_api import async_playwright

    ssw_url = os.environ.get("SSW_URL", "https://sistema.ssw.inf.br")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})

        # Tracing para gravar todo o percurso
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = await context.new_page()

        try:
            # Abrir SSW (sem wait_until rigoroso)
            await page.goto(ssw_url, wait_until="domcontentloaded", timeout=30000)

            print()
            print("=" * 60)
            print("  GRAVADOR SSW — Browser aberto")
            print()
            print("  1. Faca login no SSW")
            print("  2. Abra opcao 004 (Digitacao CT-e)")
            print("  3. Selecione 'N Normal'")
            print("  4. Preencha: placa, chave, peso, frete")
            print("  5. Simule e grave o CTe")
            print()
            print("  Dados NF 36673:")
            print("  Chave: 33260409089839000112550000000366731385587835")
            print("  Placa: ARMAZEM | Frete: 250,00 | Peso: 95,27")
            print()
            print("  Ao terminar: feche o browser ou Ctrl+C")
            print("  Trace salva em /tmp/ssw_trace.zip")
            print("=" * 60)
            print()

            # PAUSAR — usuario assume controle total
            await page.pause()

        except KeyboardInterrupt:
            print("\n>>> Interrompido pelo usuario")
        finally:
            trace_path = "/tmp/ssw_trace.zip"
            await context.tracing.stop(path=trace_path)
            print(f">>> Trace salvo em {trace_path}")
            print(">>> Visualizar: playwright show-trace /tmp/ssw_trace.zip")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
