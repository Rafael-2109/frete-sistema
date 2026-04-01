#!/usr/bin/env python3
"""
gerar_fatura_ssw_437.py — Gera fatura no SSW (opcao 437, filial MTZ).

Fluxo completo:
  1. Login SSW
  2. Trocar filial para MTZ (OBRIGATORIO — 437 so funciona em MTZ)
  3. Abrir opcao 437 (popup)
  4. Preencher CNPJ tomador → getcli() lookup
  5. Auto-preencher banco → findbco()
  6. Prosseguir → ajaxEnvia('ENV', 0)
  7. Preencher data vencimento (DDMMYY)
  8. Apontar documentos → ajaxEnvia('APO', 1)
  9. Selecionar CTe no grid (checkbox + confirmar)
  10. Capturar numero fatura
  11. [--baixar-pdf] Download PDF da fatura

IMPORTANTE:
  - Filial DEVE ser MTZ para faturamento (nao CAR)
  - CNPJ com 14 digitos (sem formatacao)
  - Data vencimento no formato DDMMYY (ex: 150426 = 15/04/2026)

Uso:
    python gerar_fatura_ssw_437.py \\
      --cnpj-tomador "12345678000199" \\
      --ctrc "94" \\
      --data-vencimento "150426" \\
      [--baixar-pdf] \\
      [--dry-run]

Retorno: JSON {"sucesso": bool, "fatura_numero": "...", "fatura_pdf": "...", ...}
"""
import argparse
import asyncio
import json
import os
import re
import sys
import traceback

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (
    verificar_credenciais,
    login_ssw,
    abrir_opcao_popup,
    interceptar_ajax_response,
    injetar_html_no_dom,
    capturar_campos,
    capturar_screenshot,
    gerar_saida,
)


# Override createNewDoc (padrao SSW scripts)
CREATE_NEW_DOC_OVERRIDE = """() => {
    createNewDoc = function(pathname) {
        document.open("text/html", "replace");
        document.write(valSep.toString());
        document.close();
        if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
    };
}"""

EVIDENCE_DIR = "/tmp/ssw_operacoes/fatura_437"


async def capturar_screenshot_local(page, nome):
    """Screenshot com diretorio especifico para fatura 437."""
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    return await capturar_screenshot(page, nome, diretorio=EVIDENCE_DIR)


async def trocar_filial_mtz(page):
    """Troca filial para MTZ (obrigatorio para tela 437)."""
    main_frame = page.frames[0]

    # Tentar trocar via campo '2' (seletor de filial no SSW)
    try:
        await main_frame.evaluate("""() => {
            const el = document.getElementById('2');
            if (el) {
                el.value = 'MTZ';
                el.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
            return false;
        }""")
        await asyncio.sleep(3)
    except Exception:
        pass

    # Tentar via select
    try:
        await main_frame.evaluate("""() => {
            const selects = document.querySelectorAll('select');
            for (const sel of selects) {
                for (const opt of sel.options) {
                    if (opt.value === 'MTZ' || opt.text.includes('MTZ')) {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
            }
            return false;
        }""")
        await asyncio.sleep(3)
    except Exception:
        pass


async def gerar_fatura(args):
    """
    Fluxo de geracao de fatura na tela 437 do SSW.

    Campos confirmados (HTML real):
      cgc_cliente (id=cgc_cliente)   -> CNPJ tomador (14 digitos)
      f2 (id=2)                      -> Data vencimento (DDMMYY)
      nro_fatura (readonly)          -> Numero da fatura gerada
    """
    from playwright.async_api import async_playwright

    verificar_credenciais()

    cnpj = args.cnpj_tomador.replace(".", "").replace("/", "").replace("-", "").strip()
    if len(cnpj) != 14 or not cnpj.isdigit():
        return gerar_saida(False, erro=f"CNPJ invalido: {cnpj} ({len(cnpj)} digitos)")

    ctrc = str(args.ctrc).strip()
    data_venc = args.data_vencimento.strip() if args.data_vencimento else None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 1000},
            accept_downloads=True,
        )
        page = await context.new_page()

        try:
            # ── 1. Login ──
            if not await login_ssw(page):
                return gerar_saida(False, erro="Login SSW falhou")

            main_frame = page.frames[0]

            # ── 2. Trocar filial para MTZ (OBRIGATORIO) ──
            await trocar_filial_mtz(page)

            # ── 3. Abrir opcao 437 ──
            popup = await abrir_opcao_popup(context, main_frame, 437, timeout_s=30)
            await asyncio.sleep(2)
            await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)

            await capturar_screenshot_local(popup, "01_437_inicial")

            campos_ok = {}

            # ── 4. Preencher CNPJ tomador ──
            try:
                campo_cnpj = popup.locator('input[name="cgc_cliente"]')
                await campo_cnpj.click()
                await campo_cnpj.fill(cnpj)
                # Disparar getcli() via blur/change
                await popup.mouse.click(10, 500)
                await asyncio.sleep(5)  # Esperar lookup cliente
                campos_ok["cnpj_tomador"] = cnpj
            except Exception as e:
                # Fallback evaluate
                try:
                    await popup.evaluate(f"""() => {{
                        const el = document.getElementById('cgc_cliente');
                        if (el) {{
                            el.value = '{cnpj}';
                            if (typeof getcli === 'function') getcli(el.value);
                        }}
                    }}""")
                    await asyncio.sleep(5)
                    campos_ok["cnpj_tomador"] = cnpj
                    campos_ok["cnpj_metodo"] = "evaluate"
                except Exception as e2:
                    return gerar_saida(False, erro=f"Falha CNPJ: {e} / {e2}")

            await capturar_screenshot_local(popup, "02_cnpj_preenchido")

            # Verificar se cliente foi encontrado (mensagens de erro no DOM)
            body_text = await popup.evaluate(
                "() => document.body ? document.body.innerText.substring(0, 3000) : ''"
            )
            if "não encontrado" in body_text.lower() or "nao encontrado" in body_text.lower():
                return gerar_saida(
                    False,
                    erro=f"Cliente CNPJ {cnpj} nao encontrado no SSW",
                    screenshot=await capturar_screenshot_local(popup, "02b_cliente_nao_encontrado"),
                )

            # ── 5. Auto-preencher banco ──
            try:
                await popup.evaluate("findbco('nro_banco','S','S','')")
                await asyncio.sleep(3)
                campos_ok["banco"] = "auto-preenchido"
            except Exception as e:
                campos_ok["banco_erro"] = str(e)

            await capturar_screenshot_local(popup, "03_banco_preenchido")

            # ── 6. Prosseguir (botao ►) ──
            try:
                await popup.evaluate("ajaxEnvia('ENV', 0)")
                await asyncio.sleep(8)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
            except Exception as e:
                return gerar_saida(False, erro=f"Falha ao prosseguir (ENV): {e}")

            await capturar_screenshot_local(popup, "04_pos_env")

            # ── 7. Preencher data vencimento ──
            if data_venc:
                try:
                    campo_venc = popup.locator('input[name="f2"]')
                    await campo_venc.click(force=True)
                    await campo_venc.fill(data_venc, force=True)
                    await campo_venc.press("Tab")
                    await asyncio.sleep(1)
                    campos_ok["data_vencimento"] = data_venc
                except Exception as e:
                    # Fallback: tentar por id
                    try:
                        await popup.evaluate(f"""() => {{
                            const el = document.getElementById('2');
                            if (el) {{ el.value = '{data_venc}'; }}
                        }}""")
                        campos_ok["data_vencimento"] = data_venc
                        campos_ok["vencimento_metodo"] = "evaluate"
                    except Exception as e2:
                        campos_ok["vencimento_erro"] = str(e2)

            # ── Dry-run: parar aqui ──
            if args.dry_run:
                campos_estado = await capturar_campos(popup)
                return gerar_saida(
                    True, modo="dry-run",
                    campos_preenchidos=campos_ok,
                    campos_formulario=campos_estado,
                    mensagem="Preview fatura 437. Nenhuma acao executada.",
                )

            # ── 8. Apontar documentos ──
            try:
                await popup.evaluate("ajaxEnvia('APO', 1)")
                await asyncio.sleep(8)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
            except Exception as e:
                return gerar_saida(False, erro=f"Falha ao apontar documentos (APO): {e}")

            await capturar_screenshot_local(popup, "05_grid_ctes")

            # ── 9. Selecionar CTe no grid ──
            # O grid mostra CTes com formato CAR000094-9
            # Precisamos encontrar o CTe pelo numero (ex: "94" → "CAR000094")
            ctrc_padded = ctrc.zfill(6)  # 94 → 000094
            ctrc_pattern = f"CAR{ctrc_padded}"

            # Encontrar e selecionar o CTe no grid
            selecao = await popup.evaluate(f"""() => {{
                const rows = document.querySelectorAll('tr');
                let found = false;
                let ctrc_text = '';
                for (const row of rows) {{
                    const text = row.textContent;
                    if (text.includes('{ctrc_pattern}') || text.includes('CAR{ctrc_padded}')) {{
                        // Encontrar checkbox na mesma row
                        const cb = row.querySelector('input[type="checkbox"]');
                        if (cb) {{
                            cb.checked = true;
                            cb.click();
                            found = true;
                            ctrc_text = text.substring(0, 200);
                        }}
                        break;
                    }}
                }}
                return {{found: found, ctrc_text: ctrc_text, pattern: '{ctrc_pattern}'}};
            }}""")

            if not selecao.get("found"):
                # Tentar match mais flexivel (sem padding)
                selecao = await popup.evaluate(f"""() => {{
                    const rows = document.querySelectorAll('tr');
                    let found = false;
                    let ctrc_text = '';
                    for (const row of rows) {{
                        const links = row.querySelectorAll('a');
                        for (const link of links) {{
                            const t = link.textContent.trim();
                            // Extrair numero puro (ex: CAR000094-0 → 94)
                            const m = t.match(/CAR0*(\\d+)/);
                            if (m && m[1] === '{ctrc}') {{
                                const cb = row.querySelector('input[type="checkbox"]');
                                if (cb) {{
                                    cb.checked = true;
                                    cb.click();
                                    found = true;
                                    ctrc_text = t;
                                }}
                                break;
                            }}
                        }}
                        if (found) break;
                    }}
                    return {{found: found, ctrc_text: ctrc_text}};
                }}""")

            if not selecao.get("found"):
                return gerar_saida(
                    False,
                    erro=f"CTe {ctrc_pattern} nao encontrado no grid de documentos",
                    screenshot=await capturar_screenshot_local(popup, "05b_cte_nao_encontrado"),
                )

            campos_ok["ctrc_selecionado"] = selecao.get("ctrc_text", ctrc_pattern)

            await capturar_screenshot_local(popup, "06_cte_selecionado")

            # ── 10. Confirmar selecao (botao ►) ──
            # O botao ► no grid e um <a class="srimglnk">
            dialogs = []

            async def on_dialog(dialog):
                dialogs.append({"tipo": dialog.type, "msg": dialog.message})
                await dialog.accept()

            popup.on("dialog", on_dialog)

            try:
                # Clicar no ► do grid (confirmar apontamento)
                await popup.evaluate("""() => {
                    const btns = document.querySelectorAll('a.srimglnk');
                    for (const btn of btns) {
                        if (btn.textContent.trim().includes('►') ||
                            btn.textContent.trim().includes('\\u25ba')) {
                            btn.click();
                            return true;
                        }
                    }
                    // Fallback: clicar no primeiro srimglnk
                    if (btns.length > 0) {
                        btns[0].click();
                        return true;
                    }
                    return false;
                }""")
                await asyncio.sleep(10)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
            except Exception:
                pass
            finally:
                try:
                    popup.remove_listener("dialog", on_dialog)
                except Exception:
                    pass

            await capturar_screenshot_local(popup, "07_pos_apontar")

            # ── 11. Capturar numero da fatura ──
            fatura_num = await popup.evaluate("""() => {
                const el = document.querySelector('input[name="nro_fatura"]');
                if (el && el.value && el.value.trim()) return el.value.trim();
                return null;
            }""")

            if not fatura_num:
                # Tentar extrair do body
                body_fatura = await popup.evaluate(
                    "() => document.body ? document.body.innerText.substring(0, 5000) : ''"
                )
                m = re.search(r'(?:fatura|nro|numero)\s*:?\s*(\d{3,})', body_fatura, re.IGNORECASE)
                if m:
                    fatura_num = m.group(1)

            campos_ok["fatura_numero"] = fatura_num

            # ── 12. Download PDF da fatura ──
            fatura_pdf_path = None
            if args.baixar_pdf and fatura_num:
                try:
                    os.makedirs(EVIDENCE_DIR, exist_ok=True)

                    # Configurar download handler
                    async with popup.expect_download(timeout=30000) as download_info:
                        # Disparar impressao/download
                        await popup.evaluate(f"""() => {{
                            const nro = '{fatura_num}';
                            ajaxEnvia('', 1,
                                'ssw2701?act=IMP&ler_morto=N&chamador=ssw0114' +
                                '&nro_fat_fin=' + nro + '&nro_fat_ini=' + nro
                            );
                        }}""")

                    download = await download_info.value
                    fatura_pdf_path = os.path.join(EVIDENCE_DIR, f"fatura_{fatura_num}.pdf")
                    await download.save_as(fatura_pdf_path)
                    campos_ok["fatura_pdf"] = fatura_pdf_path

                except Exception as e:
                    campos_ok["download_erro"] = str(e)
                    # Fallback: tentar via expect_download com timeout menor
                    try:
                        await popup.evaluate(f"""() => {{
                            const nro = '{fatura_num}';
                            ajaxEnvia('', 1,
                                'ssw2701?act=IMP&ler_morto=N&chamador=ssw0114' +
                                '&nro_fat_fin=' + nro + '&nro_fat_ini=' + nro
                            );
                        }}""")
                        await asyncio.sleep(10)
                    except Exception:
                        pass

            await capturar_screenshot_local(popup, "08_resultado_final")

            # ── Resultado final ──
            sucesso = fatura_num is not None
            return gerar_saida(
                sucesso,
                fatura_numero=fatura_num,
                fatura_pdf=fatura_pdf_path,
                ctrc_selecionado=campos_ok.get("ctrc_selecionado"),
                campos_preenchidos=campos_ok,
                dialogs=dialogs,
                mensagem=f"Fatura {fatura_num or '?'} — "
                         f"{'Gerada' if sucesso else 'Inconclusivo'}.",
            )

        except Exception as e:
            return gerar_saida(
                False, erro=str(e),
                traceback=traceback.format_exc()[-1000:]
            )

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Gerar fatura no SSW (opcao 437, filial MTZ). "
                    "Seleciona CTe e gera fatura com download PDF."
    )

    parser.add_argument(
        "--cnpj-tomador", required=True,
        help="CNPJ do tomador/cliente (14 digitos, sem formatacao)"
    )
    parser.add_argument(
        "--ctrc", required=True,
        help="Numero do CTRC a incluir na fatura (ex: 94)"
    )
    parser.add_argument(
        "--data-vencimento", default=None,
        help="Data de vencimento no formato DDMMYY (ex: 150426 = 15/04/2026)"
    )
    parser.add_argument(
        "--baixar-pdf", action="store_true",
        help="Baixar PDF da fatura gerada"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preenche CNPJ e banco sem gerar fatura. OBRIGATORIO na primeira execucao."
    )

    args = parser.parse_args()
    asyncio.run(gerar_fatura(args))


if __name__ == "__main__":
    main()
