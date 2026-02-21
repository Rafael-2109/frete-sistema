#!/usr/bin/env python3
"""
investigar_903_certificado.py — Investiga configuracao de certificado digital e
busca de XMLs na opcao 903 do SSW.

SCRIPT DE LEITURA APENAS — nao modifica nada.

Objetivo: Entender por que CT-es de subcontratacao nao aparecem na 475/477/071.

Verifica:
1. Opcao 903 → Certificados Digitais (status, validade)
2. Opcao 903 → Emissao de CTRCs (horarios busca XMLs)
3. Opcao 475 → Aba "Disponiveis para programacao" (se existe e o que mostra)
"""
import asyncio
import json
import os
import sys

# Importar ssw_common
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


async def investigar_903(context, main_frame):
    """Investiga opcao 903 — Certificado Digital e Busca XMLs."""
    resultados = {}

    print(">>> Abrindo opcao 903...")
    popup = await abrir_opcao_popup(context, main_frame, 903)
    await asyncio.sleep(2)

    # Screenshot da tela inicial da 903
    path = await capturar_screenshot(popup, "903_tela_inicial")
    print(f"  Screenshot: {path}")

    # Capturar campos da tela inicial
    campos_inicial = await capturar_campos(popup)
    resultados["903_tela_inicial"] = {
        "body_snippet": campos_inicial.get("bodySnippet", "")[:3000],
        "inputs": campos_inicial.get("inputs", []),
        "selects": campos_inicial.get("selects", []),
    }

    # Tentar encontrar links/botoes para navegar nas secoes da 903
    secoes = await popup.evaluate("""() => {
        const links = [];
        // Buscar links clickaveis
        document.querySelectorAll('a, input[type="button"], button, input[type="submit"]').forEach(el => {
            const text = (el.textContent || el.value || '').trim();
            if (text.length > 1 && text.length < 100) {
                links.push({
                    tag: el.tagName,
                    text: text,
                    href: el.href || '',
                    onclick: (el.getAttribute('onclick') || '').substring(0, 200),
                    name: el.name || '',
                    id: el.id || '',
                    value: el.value || '',
                });
            }
        });
        return links;
    }""")
    resultados["903_secoes_disponiveis"] = secoes
    print(f"  Encontradas {len(secoes)} acoes/links na 903")

    # Buscar especificamente por "Certificado", "XML", "Busca", "Emissao"
    keywords = ["certificad", "xml", "busca", "emiss", "portal", "dfe", "ct-e", "cte"]
    secoes_relevantes = [
        s for s in secoes
        if any(kw in (s.get("text", "") + s.get("value", "")).lower() for kw in keywords)
    ]
    resultados["903_secoes_relevantes"] = secoes_relevantes
    print(f"  Secoes relevantes encontradas: {len(secoes_relevantes)}")
    for s in secoes_relevantes:
        print(f"    - [{s['tag']}] {s.get('text', '') or s.get('value', '')} | onclick={s.get('onclick', '')[:60]}")

    # Tentar navegar para secao de certificados se encontrar link
    for s in secoes_relevantes:
        if "certificad" in (s.get("text", "") + s.get("value", "")).lower():
            onclick = s.get("onclick", "")
            if onclick:
                print(f"  >>> Clicando em secao Certificados: {onclick[:80]}")
                try:
                    html = await interceptar_ajax_response(popup, popup, onclick)
                    if html:
                        await injetar_html_no_dom(popup, html)
                        await asyncio.sleep(1)
                        path = await capturar_screenshot(popup, "903_certificados")
                        print(f"  Screenshot certificados: {path}")
                        campos_cert = await capturar_campos(popup)
                        resultados["903_certificados"] = {
                            "body_snippet": campos_cert.get("bodySnippet", "")[:3000],
                            "inputs": campos_cert.get("inputs", []),
                            "selects": campos_cert.get("selects", []),
                        }
                except Exception as e:
                    print(f"  Erro ao navegar certificados: {e}")
                    # Tentar click direto
                    try:
                        await popup.click(f'text="{s.get("text", "")}"')
                        await asyncio.sleep(2)
                        path = await capturar_screenshot(popup, "903_certificados_click")
                        print(f"  Screenshot certificados (click): {path}")
                    except Exception as e2:
                        print(f"  Erro click direto: {e2}")
            break

    # Buscar texto completo da pagina para analise
    full_text = await popup.evaluate("() => document.body ? document.body.innerText : ''")
    resultados["903_full_text"] = full_text[:5000]

    await popup.close()
    return resultados


async def investigar_475(context, main_frame):
    """Investiga opcao 475 — Contas a Pagar."""
    resultados = {}

    print("\n>>> Abrindo opcao 475...")
    popup = await abrir_opcao_popup(context, main_frame, 475)
    await asyncio.sleep(2)

    # Screenshot da tela inicial
    path = await capturar_screenshot(popup, "475_tela_inicial")
    print(f"  Screenshot: {path}")

    # Capturar campos
    campos = await capturar_campos(popup)
    resultados["475_tela_inicial"] = {
        "body_snippet": campos.get("bodySnippet", "")[:3000],
        "inputs": campos.get("inputs", []),
        "selects": campos.get("selects", []),
    }

    # Buscar abas, links ou botoes
    abas = await popup.evaluate("""() => {
        const items = [];
        document.querySelectorAll('a, input[type="button"], button, .tab, [role="tab"]').forEach(el => {
            const text = (el.textContent || el.value || '').trim();
            if (text.length > 1 && text.length < 100) {
                items.push({
                    tag: el.tagName,
                    text: text,
                    onclick: (el.getAttribute('onclick') || '').substring(0, 200),
                    href: el.href || '',
                    class: el.className || '',
                });
            }
        });
        return items;
    }""")
    resultados["475_abas_links"] = abas
    print(f"  Encontradas {len(abas)} acoes/links na 475")

    # Buscar por "disponiv", "xml", "ct-e", "dfe"
    keywords = ["disponiv", "xml", "ct-e", "cte", "dfe", "importa", "portal", "nf-e", "nfe"]
    relevantes = [
        a for a in abas
        if any(kw in (a.get("text", "")).lower() for kw in keywords)
    ]
    resultados["475_relevantes"] = relevantes
    print(f"  Links relevantes: {len(relevantes)}")
    for r in relevantes:
        print(f"    - [{r['tag']}] {r.get('text', '')} | onclick={r.get('onclick', '')[:60]}")

    # Capturar texto completo
    full_text = await popup.evaluate("() => document.body ? document.body.innerText : ''")
    resultados["475_full_text"] = full_text[:5000]

    await popup.close()
    return resultados


async def main():
    verificar_credenciais()

    from playwright.async_api import async_playwright

    resultados_completos = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        print(">>> Fazendo login no SSW...")
        logado = await login_ssw(page)
        if not logado:
            gerar_saida(False, erro="Falha no login SSW")
            await browser.close()
            return

        print("  Login OK")

        # Obter frame principal
        main_frame = page.frames[0]

        # Investigar 903
        try:
            r903 = await investigar_903(context, main_frame)
            resultados_completos["opcao_903"] = r903
        except Exception as e:
            print(f"  ERRO na 903: {e}")
            resultados_completos["opcao_903_erro"] = str(e)

        # Investigar 475
        try:
            r475 = await investigar_475(context, main_frame)
            resultados_completos["opcao_475"] = r475
        except Exception as e:
            print(f"  ERRO na 475: {e}")
            resultados_completos["opcao_475_erro"] = str(e)

        await browser.close()

    # Salvar resultados em JSON
    output_path = "/tmp/ssw_operacoes/investigacao_903_475.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados_completos, f, indent=2, ensure_ascii=False)

    print(f"\n>>> Resultados salvos em: {output_path}")

    # Resumo
    gerar_saida(
        True,
        screenshots="/tmp/ssw_operacoes/",
        resultados=output_path,
        resumo={
            "903_secoes_encontradas": len(resultados_completos.get("opcao_903", {}).get("903_secoes_disponiveis", [])),
            "903_secoes_relevantes": len(resultados_completos.get("opcao_903", {}).get("903_secoes_relevantes", [])),
            "475_links_encontrados": len(resultados_completos.get("opcao_475", {}).get("475_abas_links", [])),
            "475_links_relevantes": len(resultados_completos.get("opcao_475", {}).get("475_relevantes", [])),
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
