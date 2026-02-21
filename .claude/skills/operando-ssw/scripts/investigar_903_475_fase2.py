#!/usr/bin/env python3
"""
investigar_903_475_fase2.py — Fase 2: Navegar nas secoes internas da 903 e 475.

SCRIPT DE LEITURA APENAS — nao modifica nada.

Verifica:
1. 903 → Certificados Digitais (status, validade, CNPJ)
2. 903 → Emissao de CTRCs (horarios busca XMLs, modo)
3. 475 → "Disponiveis para programacao" (o que mostra)
"""
import asyncio
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (
    verificar_credenciais,
    login_ssw,
    abrir_opcao_popup,
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
    interceptar_ajax_response,
    injetar_html_no_dom,
)


async def navegar_secao_903(context, main_frame, secao_id, secao_nome, js_code):
    """Abre 903 e navega para uma secao especifica via AJAX."""
    popup = await abrir_opcao_popup(context, main_frame, 903)
    await asyncio.sleep(2)

    print(f"  >>> Navegando para secao: {secao_nome}")

    # Executar AJAX para ir na secao
    html = await interceptar_ajax_response(popup, popup, js_code)
    if html:
        await injetar_html_no_dom(popup, html)
        await asyncio.sleep(1)

        path = await capturar_screenshot(popup, f"903_{secao_id}")
        print(f"  Screenshot: {path}")

        campos = await capturar_campos(popup)
        full_text = await popup.evaluate("() => document.body ? document.body.innerText : ''")

        await popup.close()
        return {
            "body_snippet": campos.get("bodySnippet", "")[:5000],
            "inputs": campos.get("inputs", []),
            "selects": campos.get("selects", []),
            "full_text": full_text[:5000],
            "screenshot": path,
        }
    else:
        # Tentar click direto no link
        try:
            await popup.click(f"#{secao_id}")
            await asyncio.sleep(3)
            path = await capturar_screenshot(popup, f"903_{secao_id}_click")
            print(f"  Screenshot (click): {path}")
            campos = await capturar_campos(popup)
            full_text = await popup.evaluate("() => document.body ? document.body.innerText : ''")
            await popup.close()
            return {
                "body_snippet": campos.get("bodySnippet", "")[:5000],
                "inputs": campos.get("inputs", []),
                "selects": campos.get("selects", []),
                "full_text": full_text[:5000],
                "screenshot": path,
            }
        except Exception as e:
            print(f"  Erro: {e}")
            await popup.close()
            return {"erro": str(e)}


async def investigar_475_disponiveis(context, main_frame):
    """Clica em 'Disponiveis para programacao' na 475."""
    popup = await abrir_opcao_popup(context, main_frame, 475)
    await asyncio.sleep(2)

    print("  >>> Clicando em 'Disponiveis para programacao'")

    html = await interceptar_ajax_response(popup, popup, "ajaxEnvia('DISP', 1)")
    if html:
        await injetar_html_no_dom(popup, html)
        await asyncio.sleep(1)

        path = await capturar_screenshot(popup, "475_disponiveis")
        print(f"  Screenshot: {path}")

        campos = await capturar_campos(popup)
        full_text = await popup.evaluate("() => document.body ? document.body.innerText : ''")

        await popup.close()
        return {
            "body_snippet": campos.get("bodySnippet", "")[:5000],
            "inputs": campos.get("inputs", []),
            "selects": campos.get("selects", []),
            "full_text": full_text[:5000],
            "screenshot": path,
        }
    else:
        # Tentar click direto
        try:
            await popup.click('text="Disponíveis para programação"')
            await asyncio.sleep(3)
            path = await capturar_screenshot(popup, "475_disponiveis_click")
            print(f"  Screenshot (click): {path}")
            campos = await capturar_campos(popup)
            full_text = await popup.evaluate("() => document.body ? document.body.innerText : ''")
            await popup.close()
            return {
                "body_snippet": campos.get("bodySnippet", "")[:5000],
                "inputs": campos.get("inputs", []),
                "selects": campos.get("selects", []),
                "full_text": full_text[:5000],
                "screenshot": path,
            }
        except Exception as e:
            print(f"  Erro: {e}")
            await popup.close()
            return {"erro": str(e)}


async def main():
    verificar_credenciais()

    from playwright.async_api import async_playwright

    resultados = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        print(">>> Login SSW...")
        logado = await login_ssw(page)
        if not logado:
            gerar_saida(False, erro="Falha no login SSW")
            await browser.close()
            return
        print("  Login OK")

        main_frame = page.frames[0]

        # 1. 903 → Certificados Digitais
        print("\n>>> [1/3] 903 - Certificados Digitais")
        try:
            r = await navegar_secao_903(
                context, main_frame,
                "link_certif",
                "Certificados digitais",
                "ajaxEnvia('', 1, 'ssw1970')"
            )
            resultados["903_certificados"] = r
        except Exception as e:
            print(f"  ERRO: {e}")
            resultados["903_certificados_erro"] = str(e)

        # 2. 903 → Emissao de CTRCs
        print("\n>>> [2/3] 903 - Emissao de CTRCs")
        try:
            r = await navegar_secao_903(
                context, main_frame,
                "link_emissao_ctrc",
                "Emissao de CTRCs",
                "ajaxEnvia('', 1, 'ssw2688')"
            )
            resultados["903_emissao_ctrcs"] = r
        except Exception as e:
            print(f"  ERRO: {e}")
            resultados["903_emissao_ctrcs_erro"] = str(e)

        # 3. 475 → Disponiveis para programacao
        print("\n>>> [3/3] 475 - Disponiveis para programacao")
        try:
            r = await investigar_475_disponiveis(context, main_frame)
            resultados["475_disponiveis"] = r
        except Exception as e:
            print(f"  ERRO: {e}")
            resultados["475_disponiveis_erro"] = str(e)

        await browser.close()

    # Salvar resultados
    output_path = "/tmp/ssw_operacoes/investigacao_fase2.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n>>> Resultados: {output_path}")

    # Resumo
    for secao, dados in resultados.items():
        if isinstance(dados, dict) and "full_text" in dados:
            print(f"\n--- {secao} ---")
            print(dados["full_text"][:500])

    gerar_saida(True, resultados=output_path)


if __name__ == "__main__":
    asyncio.run(main())
