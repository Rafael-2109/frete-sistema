#!/usr/bin/env python3
"""
consultar_ctrc_101.py — Consulta CTRC no SSW (opcao 101) + baixa DACTE/XML.

Pesquisa por CTRC (--ctrc), numero da NF (--nf) ou numero do CTe (--cte).
Obrigatorio um dos tres.

Fluxo:
  1. Login SSW
  2. Trocar filial (default: CAR)
  3. Abrir opcao 101
  4. Preencher campo de pesquisa (t_nro_ctrc, t_nro_nf ou t_nro_cte)
  5. Pesquisar via ajaxEnvia('P1', 1) / ('P2', 1) / ('P3', 1)
  6. Capturar dados do CTRC (CT-e, status, remetente, destinatario, etc.)
  7. [--baixar-xml] Baixar XML do CT-e (ZIP → extrai XML)
  8. [--baixar-dacte] Baixar DACTE em PDF

Campos mapeados (2026-04-14):
  t_nro_ctrc          -> Numero do CTRC sem DV (ex: 94)
  t_nro_nf            -> Numero da NF (ex: 35714, maxlength=10)
  t_nro_cte           -> Numero do CTe/nCT SEFAZ (ex: 161, maxlength=10)
  ajaxEnvia('P1', 1)  -> Pesquisar por CTRC
  ajaxEnvia('P2', 1)  -> Pesquisar por NF
  ajaxEnvia('P3', 1)  -> Pesquisar por NR (nao usado aqui)
  ajaxEnvia('P4', 1)  -> Pesquisar por CT-e/NFS-e (t_nro_cte)
  ajaxEnvia('XML', 0) -> Baixar XML (retorna form com abrir() para ZIP)
  link_imp_dacte      -> Baixar DACTE (retorna form com abrir() para PDF)

Uso:
    python consultar_ctrc_101.py --ctrc 94 --baixar-xml --baixar-dacte
    python consultar_ctrc_101.py --nf 35714 --baixar-xml --baixar-dacte
    python consultar_ctrc_101.py --cte 161 --baixar-xml --baixar-dacte
    python consultar_ctrc_101.py --ctrc 94 --filial CAR --output-dir /tmp/cte

Retorno: JSON {"sucesso": bool, "ctrc": "...", "cte": "...", "dados": {...}, ...}
"""
import argparse
import asyncio
import os
import re
import sys
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (
    verificar_credenciais,
    login_ssw,
    abrir_opcao_popup,
    capturar_screenshot,
    gerar_saida,
)

CREATE_NEW_DOC_OVERRIDE = """() => {
    createNewDoc = function(pathname) {
        document.open("text/html", "replace");
        document.write(valSep.toString());
        document.close();
        if (pathname) try { history.pushState({}, "", pathname); } catch(e) {}
    };
}"""


async def consultar_ctrc(args):
    """Consulta CTRC na opcao 101 e opcionalmente baixa XML e DACTE."""
    from playwright.async_api import async_playwright

    verificar_credenciais()

    ctrc = str(args.ctrc).strip() if args.ctrc else None
    nf = str(args.nf).strip() if args.nf else None
    cte = str(args.cte).strip() if getattr(args, "cte", None) else None

    if not ctrc and not nf and not cte:
        return gerar_saida(False, erro="Informe --ctrc, --nf ou --cte")

    # Label para screenshots e mensagens
    if ctrc:
        search_label = f"ctrc_{ctrc}"
    elif nf:
        search_label = f"nf_{nf}"
    else:
        search_label = f"cte_{cte}"
    filial = (args.filial or "CAR").upper().strip()
    output_dir = args.output_dir or "/tmp/ssw_operacoes/consulta_101"
    os.makedirs(output_dir, exist_ok=True)

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

            # ── 2. Frame principal (com campo de opcao #3) ──
            main_frame = None
            for frame in page.frames:
                try:
                    has_option = await frame.evaluate(
                        "() => !!document.getElementById('3')"
                    )
                    if has_option:
                        main_frame = frame
                        break
                except Exception:
                    continue

            if not main_frame:
                return gerar_saida(
                    False, erro="Frame principal nao encontrado apos login"
                )

            # ── 3. Filial ──
            await main_frame.evaluate(f"""() => {{
                var el = document.getElementById('2');
                if (el) el.value = '{filial}';
            }}""")
            await asyncio.sleep(2)

            # ── 4. Abrir 101 ──
            popup = await abrir_opcao_popup(context, main_frame, 101, timeout_s=30)
            await asyncio.sleep(3)
            # NÃO aplicar override antes — campos existem no HTML original

            # ── 5. Preencher campo de pesquisa ──
            if ctrc:
                field_id, field_value = "t_nro_ctrc", ctrc
            elif nf:
                field_id, field_value = "t_nro_nf", nf
            else:
                field_id, field_value = "t_nro_cte", cte

            fill_result = await popup.evaluate(f"""() => {{
                const el = document.getElementById('{field_id}');
                if (!el) return {{ok: false, erro: 'campo {field_id} nao existe'}};
                el.value = '{field_value}';
                return {{ok: true, value: el.value}};
            }}""")
            if not fill_result.get("ok"):
                return gerar_saida(False, erro=fill_result.get("erro"))

            await asyncio.sleep(1)

            # ── 6. Pesquisar ──
            # Mapa de acoes por campo (descoberto via inspect tela 101)
            # Nao e sequencial: ordem DOM 1-13 mapeia para
            # P1, P2, P3, P8, P4, P9, P10, P5, P6, VLR_FRT, PROT, P, BAR.
            # Portanto CTRC=P1, NF=P2, NR=P3, CT-e=P4 (nao P3!).
            field_actions = {
                "t_nro_ctrc": "ajaxEnvia('P1', 1)",
                "t_nro_nf": "ajaxEnvia('P2', 1)",
                "t_nro_cte": "ajaxEnvia('P4', 1)",
            }
            action = field_actions.get(field_id, "ajaxEnvia('P1', 1)")

            # Tratar dialogs nativos do SSW
            popup.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

            if ctrc:
                # CTRC: override antes (padrao que funciona)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                await popup.evaluate(action)
                await asyncio.sleep(8)
            else:
                # NF/CTe: chamar sem override (override interfere na validacao)
                # Aplicar override APOS o ajaxEnvia disparar (antes da response)
                await popup.evaluate(action)
                await asyncio.sleep(0.5)
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                await asyncio.sleep(8)
            try:
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
            except Exception:
                pass

            screenshot_path = await capturar_screenshot(
                popup, f"101_{search_label}", output_dir
            )

            # ── 7. Extrair dados ──
            body = await popup.evaluate(
                "() => document.body ? document.body.innerText.substring(0,8000) : ''"
            )

            dados = {"body_raw": body[:3000]}

            # Extrair campos estruturados
            patterns = {
                "ctrc_completo": r"CTRC\s*/Subc\./RPS:\s*(.+?)(?:\n|DACTE)",
                "cte": r"CT-e:\s*(\d+\s+\d+)",
                "status": r"(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2})\s+(AUTORIZADO|REJEITADO|DENEGADO|CANCELADO)",
                "destino": r"Destino:\s*(.+?)(?:\n|Inclusão)",
                "nf": r"N°\s*da\s*Nota\s*Fiscal:\s*(.+?)(?:\n|N°)",
                "volumes": r"Qtde\.\s*de\s*vol\./pares:\s*(.+?)(?:\n|Conferente)",
                "peso": r"Peso\s*(?:cálculo|real)\s*\(Kg\):\s*([\d.,]+)",
                "valor_nf": r"Valor\s*da\s*Nota\s*Fiscal:\s*([\d.,]+)",
                "frete": r"Valor\s*frete\s*\(R\$\):\s*([\d.,]+)",
                "remetente": r"Remetente:.*?Nome:\s*(.+?)(?:\n|CNPJ)",
                "remetente_cnpj": r"Remetente:.*?CNPJ:\s*(\d+)",
                "destinatario": r"Destinatário:.*?Nome:\s*(.+?)(?:\n|CNPJ)",
                "destinatario_cnpj": r"Destinatário:.*?CNPJ:\s*(\d+)",
                "situacao": r"Situação\s*de\s*liquidação:\s*(.+?)(?:\n|NFS)",
                "cobranca": r"Tipo\s*de\s*cobrança:\s*(.+?)(?:\n|Remetente)",
            }

            for key, pattern in patterns.items():
                m = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
                if m:
                    dados[key] = m.group(1).strip()

            # Capturar seq_ctrc e FAMILIA para downloads
            download_info = await popup.evaluate("""() => {
                const dacte = document.getElementById('link_imp_dacte');
                const xml = document.getElementById('link_imp_xml');
                return {
                    dacte_onclick: dacte ? dacte.getAttribute('onclick') : null,
                    xml_onclick: xml ? xml.getAttribute('onclick') : null,
                };
            }""")

            # Extrair seq_ctrc do onclick do DACTE
            seq_ctrc = None
            familia = None
            if download_info.get("dacte_onclick"):
                m = re.search(r"seq_ctrc=(\d+)", download_info["dacte_onclick"])
                if m:
                    seq_ctrc = m.group(1)
                m2 = re.search(r"FAMILIA=(\w+)", download_info["dacte_onclick"])
                if m2:
                    familia = m2.group(1)

            dados["seq_ctrc"] = seq_ctrc
            dados["familia"] = familia

            # ── 8. Baixar XML ──
            xml_path = None
            xml_cte = None
            xml_chave = None

            if args.baixar_xml:
                # Interceptar response do ajaxEnvia('XML', 0)
                xml_response = None

                async def on_xml(response):
                    nonlocal xml_response
                    if "/bin/ssw" in response.url and response.status == 200:
                        try:
                            body = await response.text()
                            if body and len(body) > 50:
                                xml_response = body
                        except Exception:
                            pass

                popup.on("response", on_xml)
                try:
                    await popup.evaluate("ajaxEnvia('XML', 0)")
                    for _ in range(20):
                        if xml_response:
                            break
                        await asyncio.sleep(0.5)
                finally:
                    popup.remove_listener("response", on_xml)

                if xml_response:
                    # Extrair nome do arquivo ZIP do web_body
                    from urllib.parse import unquote
                    wb_match = re.search(
                        r'web_body.*?value="(.+?)"', xml_response
                    )
                    if wb_match:
                        web_body = unquote(wb_match.group(1))
                        # Extrair: abrir("CTe_xxx.zip", ...)
                        file_match = re.search(
                            r'abrir\(["\'](.+?\.zip)["\']', web_body
                        )
                        if file_match:
                            zip_name = file_match.group(1)

                            # Chamar abrir() para triggerar download
                            try:
                                async with popup.expect_download(
                                    timeout=20000
                                ) as dl:
                                    await popup.evaluate(
                                        f'abrir("{zip_name}", "{zip_name}", 1, 1, "binary", 3)'
                                    )
                                download = await dl.value
                                zip_path = os.path.join(
                                    output_dir,
                                    download.suggested_filename or zip_name,
                                )
                                await download.save_as(zip_path)

                                # Extrair XML do ZIP
                                with zipfile.ZipFile(zip_path, "r") as z:
                                    for name in z.namelist():
                                        if name.endswith(".xml"):
                                            z.extract(name, output_dir)
                                            xml_path = os.path.join(
                                                output_dir, name
                                            )
                                            with open(
                                                xml_path, "r", encoding="utf-8"
                                            ) as f:
                                                xml_content = f.read()

                                            # Extrair CT-e e chave
                                            m = re.search(
                                                r"<nCT>(\d+)</nCT>", xml_content
                                            )
                                            if m:
                                                xml_cte = m.group(1)
                                            m = re.search(
                                                r"<chCTe>(\d+)</chCTe>",
                                                xml_content,
                                            )
                                            if m:
                                                xml_chave = m.group(1)
                                            break
                            except Exception as e:
                                dados["xml_erro"] = str(e)

                    # Re-pesquisar (DOM foi substituido pelo ajaxEnvia XML)
                    await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                    # Aguardar campo de pesquisa existir apos override
                    for _ in range(10):
                        has_field = await popup.evaluate(
                            f"() => !!document.getElementById('{field_id}')"
                        )
                        if has_field:
                            break
                        await asyncio.sleep(1)

                    await popup.evaluate(f"""() => {{
                        var el = document.getElementById('{field_id}');
                        if (el) el.value = '{field_value}';
                    }}""")
                    await popup.evaluate(action)
                    await asyncio.sleep(8)
                    try:
                        await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                    except Exception:
                        pass

            # ── 9. Baixar DACTE ──
            dacte_path = None

            if args.baixar_dacte and download_info.get("dacte_onclick"):
                dacte_response = None

                async def on_dacte(response):
                    nonlocal dacte_response
                    if "/bin/ssw" in response.url and response.status == 200:
                        try:
                            body = await response.text()
                            if body and len(body) > 50:
                                dacte_response = body
                        except Exception:
                            pass

                popup.on("response", on_dacte)
                try:
                    # Extrair e executar onclick do DACTE (sem return false)
                    onclick = download_info["dacte_onclick"].replace(
                        ";return false;", ""
                    ).replace("return false;", "")
                    await popup.evaluate(onclick)
                    for _ in range(20):
                        if dacte_response:
                            break
                        await asyncio.sleep(0.5)
                finally:
                    popup.remove_listener("response", on_dacte)

                if dacte_response:
                    from urllib.parse import unquote
                    wb_match = re.search(
                        r'web_body.*?value="(.+?)"', dacte_response
                    )
                    if wb_match:
                        web_body = unquote(wb_match.group(1))
                        file_match = re.search(
                            r"abrir\(['\"](.+?\.pdf)['\"].*?['\"](.+?\.pdf)['\"]",
                            web_body,
                        )
                        if file_match:
                            server_name = file_match.group(1)
                            display_name = file_match.group(2)

                            try:
                                async with popup.expect_download(
                                    timeout=20000
                                ) as dl:
                                    await popup.evaluate(
                                        f"abrir('{server_name}','{display_name}',1,1,'binary',5)"
                                    )
                                download = await dl.value
                                dacte_path = os.path.join(
                                    output_dir,
                                    download.suggested_filename
                                    or display_name,
                                )
                                await download.save_as(dacte_path)
                            except Exception as e:
                                dados["dacte_erro"] = str(e)

            # ── Resultado ──
            # Extrair CTRC do resultado (util quando pesquisa por NF ou CTe).
            # Ao pesquisar por CTRC, `ctrc_completo` e o retorno autoritativo
            # do SSW — preferir sobre o parametro passado.
            ctrc_completo_ssw = dados.get("ctrc_completo", "") or ""
            if nf or cte:
                ctrc_encontrado = ctrc_completo_ssw
            else:
                ctrc_encontrado = ctrc_completo_ssw or ctrc or ""
            cte_numero = xml_cte or (
                dados.get("cte", "").split()[-1] if dados.get("cte") else None
            )

            if ctrc:
                entrada_label = f"CTRC {ctrc}"
            elif nf:
                entrada_label = f"NF {nf}"
            else:
                entrada_label = f"CT-e {cte}"

            return gerar_saida(
                True,
                ctrc=ctrc_encontrado,
                ctrc_parametro=ctrc,
                nf_pesquisada=nf,
                cte_pesquisado=cte,
                cte=cte_numero,
                chave_cte=xml_chave,
                dados=dados,
                xml=xml_path,
                dacte=dacte_path,
                screenshot=screenshot_path,
                mensagem=f"{entrada_label} consultado. "
                + (
                    f"CTRC: {ctrc_encontrado}. "
                    if (nf or cte) and ctrc_encontrado
                    else ""
                )
                + (f"XML: {xml_path}. " if xml_path else "")
                + (f"DACTE: {dacte_path}." if dacte_path else ""),
            )

        except Exception as e:
            import traceback
            return gerar_saida(
                False, erro=str(e), traceback=traceback.format_exc()[-1000:]
            )

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Consulta CTRC no SSW (opcao 101) + baixa DACTE/XML."
    )

    search = parser.add_mutually_exclusive_group(required=True)
    search.add_argument(
        "--ctrc",
        help="Numero do CTRC sem DV (ex: 94)",
    )
    search.add_argument(
        "--nf",
        help="Numero da NF (ex: 35714, max 10 digitos)",
    )
    search.add_argument(
        "--cte",
        help="Numero do CTe/nCT SEFAZ (ex: 161, max 10 digitos)",
    )
    parser.add_argument(
        "--filial",
        default="CAR",
        help="Filial (default: CAR)",
    )
    parser.add_argument(
        "--baixar-xml",
        action="store_true",
        help="Baixar XML do CT-e (ZIP → extrai XML)",
    )
    parser.add_argument(
        "--baixar-dacte",
        action="store_true",
        help="Baixar DACTE em PDF",
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/ssw_operacoes/consulta_101",
        help="Diretorio para salvar arquivos",
    )

    args = parser.parse_args()
    asyncio.run(consultar_ctrc(args))


if __name__ == "__main__":
    main()
