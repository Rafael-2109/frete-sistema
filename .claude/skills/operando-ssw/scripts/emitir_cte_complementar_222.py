"""
Emissao de CTe Complementar via SSW opcao 222.

Preenche a tela 222 (CTRC Servico Complementar) com:
- CTRC do CTe original (filial + numero + DV)
- Motivo (C=complementar, D=descarga, V=veiculo dedicado, E=estadia, R=reembolso)
- Valor no campo "Outros" (parcela)
- Submete ao SEFAZ

Uso standalone (teste):
    python emitir_cte_complementar_222.py --ctrc-pai CAR-113-9 --motivo D --valor-outros 150.00

Uso via RQ job:
    Chamado por ssw_cte_complementar_jobs.py via asyncio.run()
"""
import argparse
import asyncio
import json
import logging
import os
import re
import sys

# Setup path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from ssw_common import (  # noqa: E402
    verificar_credenciais,
    login_ssw,
    abrir_opcao_popup,
    interceptar_ajax_response,
    injetar_html_no_dom,
    preencher_campo_no_html,
    capturar_screenshot,
    gerar_saida,
    verificar_mensagem_ssw,
)

logger = logging.getLogger(__name__)

# Motivos validos para opcao 222
MOTIVOS_VALIDOS = {'C', 'D', 'V', 'E', 'R'}


def validar_args(args):
    """Valida argumentos antes de iniciar Playwright."""
    erros = []

    if not args.ctrc_pai:
        erros.append("ctrc_pai obrigatorio (ex: CAR-113-9)")

    if args.motivo not in MOTIVOS_VALIDOS:
        erros.append(f"motivo invalido: {args.motivo}. Validos: {MOTIVOS_VALIDOS}")

    if not args.valor_outros or args.valor_outros <= 0:
        erros.append(f"valor_outros deve ser > 0 (recebido: {args.valor_outros})")

    if erros:
        raise ValueError("; ".join(erros))


def parsear_ctrc(ctrc_pai):
    """Extrai filial, numero e digito verificador do CTRC.

    Formato esperado: CAR-113-9 → ('CAR', '113', '9')
    """
    partes = ctrc_pai.split('-')
    if len(partes) != 3:
        raise ValueError(
            f"CTRC formato invalido: {ctrc_pai}. Esperado: FILIAL-NUMERO-DV (ex: CAR-113-9)"
        )
    return partes[0], partes[1], partes[2]


async def emitir_cte_complementar(args):
    """Fluxo principal: login → opcao 222 → preencher → submeter.

    Args:
        args: argparse.Namespace com ctrc_pai, motivo, valor_outros, filial, dry_run

    Returns:
        dict com {sucesso, ctrc_complementar, erro, ...}
    """
    from playwright.async_api import async_playwright

    try:
        validar_args(args)
    except ValueError as e:
        return gerar_saida(False, erro=str(e))

    filial, ctrc_num, ctrc_dv = parsear_ctrc(args.ctrc_pai)

    verificar_credenciais()

    resultado = {
        'sucesso': False,
        'ctrc_pai': args.ctrc_pai,
        'motivo': args.motivo,
        'valor_outros': args.valor_outros,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # ── Fase 1: Login ──
            logger.info("Fase 1: Login SSW")
            await login_ssw(page)

            main_frame = page.frames[0]

            # ── Fase 1b: Trocar filial para a correta (ex: CAR) ──
            logger.info("Fase 1b: Trocar filial para %s", filial)
            await main_frame.evaluate(f"""() => {{
                var el = document.getElementById('2');
                if (el) el.value = '{filial}';
            }}""")
            await asyncio.sleep(2)

            # ── Fase 2: Abrir opcao 222 ──
            logger.info("Fase 2: Abrir opcao 222")
            popup = await abrir_opcao_popup(context, main_frame, 222)
            await asyncio.sleep(2)

            # Frame do popup
            frames = popup.frames
            frame = frames[0] if len(frames) == 1 else frames[-1]

            # ── Fase 3: Tela Inicial — preencher motivo + CTRC ──
            logger.info("Fase 3: Preencher tela inicial 222")

            # Capturar screenshot da tela inicial
            await capturar_screenshot(popup, "222_tela_inicial")

            # Campos reais da tela 222 (descobertos via DOM inspect):
            #   motivo (name=motivo, maxLen=1): C/D/V/E/R
            #   nro_desp (name=nro_desp): num lancamento despesa (so motivo R)
            #   f1 (name=f1, maxLen=3): filial (ex: CAR)
            #   f2 (name=f2, maxLen=7): CTRC com DV (ex: 113-9)
            #   cod_bar (name=cod_bar, maxLen=44): chave acesso (alternativa)

            # Preencher Motivo do complemento
            await preencher_campo_no_html(popup, 'motivo', args.motivo, by='name')
            await asyncio.sleep(0.5)

            # Preencher CTRC — filial
            await preencher_campo_no_html(popup, 'f1', filial, by='name')
            await asyncio.sleep(0.3)

            # Preencher CTRC — numero + DV colado sem hifen (ex: 1139)
            ctrc_com_dv = f"{ctrc_num}{ctrc_dv}"
            await preencher_campo_no_html(popup, 'f2', ctrc_com_dv, by='name')
            await asyncio.sleep(0.3)

            await capturar_screenshot(popup, "222_preenchido_inicial")

            if args.dry_run:
                resultado['sucesso'] = True
                resultado['dry_run'] = True
                resultado['mensagem'] = 'Dry run: tela inicial preenchida, nao submetido'
                return resultado

            # ── Fase 3b: Submeter tela inicial — ajaxEnvia('ENV', 1) ──
            logger.info("Fase 3b: Submeter tela inicial via ajaxEnvia('ENV', 1)")

            # Dismiss dialogs automaticamente
            dialogs = []
            ctrc_complementar_num = None

            async def on_dialog(dialog):
                nonlocal ctrc_complementar_num
                msg = dialog.message
                dialogs.append({"tipo": dialog.type, "msg": msg})
                m = re.search(r'(\d{2,6})', msg)
                if m and not ctrc_complementar_num:
                    ctrc_complementar_num = m.group(1)
                if dialog.type == "confirm":
                    await dialog.accept()
                else:
                    await dialog.accept()

            popup.on("dialog", on_dialog)

            # SSW usa AJAX que substitui DOM — interceptar response
            html_tela2 = await interceptar_ajax_response(
                popup, popup, "ajaxEnvia('ENV', 1)", timeout_s=15
            )

            if html_tela2:
                await injetar_html_no_dom(popup, html_tela2)
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(5)

            await capturar_screenshot(popup, "222_pos_submit_inicial")

            body = await popup.evaluate(
                "() => document.body ? document.body.innerText.substring(0,5000) : ''"
            )

            # Checar se houve erro
            body_lower = body.lower()
            if 'erro' in body_lower or 'não encontrad' in body_lower or 'nao encontrad' in body_lower:
                await capturar_screenshot(popup, "222_erro_tela2")
                resultado['erro'] = f"SSW: {body[:500]}"
                resultado['dialogs'] = dialogs
                return resultado

            # Descobrir campos da tela principal
            logger.info("Fase 4: Descobrir e preencher campos da tela principal")
            inputs_tela2 = await popup.evaluate("""() => {
                const els = document.querySelectorAll('input, select, textarea');
                return Array.from(els).map(el => ({
                    tag: el.tagName, type: el.type || '', name: el.name || '',
                    id: el.id || '', maxLength: el.maxLength || 0
                }));
            }""")

            for inp in inputs_tela2:
                logger.info("  Campo: name=%s id=%s type=%s", inp['name'], inp['id'], inp['type'])

            await capturar_screenshot(popup, "222_tela_principal")

            # ── Fase 4b: Preencher valor ──
            # Tentar campo "outros" primeiro, senao tentar "frete"
            valor_formatado = f"{args.valor_outros:.2f}".replace('.', ',')
            campo_valor = None
            for nome_campo in ['outros', 'frete', 'vlr_outros', 'vlr_frete', 'valor']:
                try:
                    await preencher_campo_no_html(popup, nome_campo, valor_formatado, by='name')
                    campo_valor = nome_campo
                    logger.info("Valor %s preenchido no campo '%s'", valor_formatado, nome_campo)
                    break
                except ValueError:
                    continue

            if not campo_valor:
                await capturar_screenshot(popup, "222_sem_campo_valor")
                resultado['erro'] = f"Campo de valor nao encontrado. Campos disponiveis: {[i['name'] for i in inputs_tela2]}"
                resultado['dialogs'] = dialogs
                return resultado

            await asyncio.sleep(0.5)
            await capturar_screenshot(popup, "222_valor_preenchido")

            # ── Fase 5: Gravar via ajaxEnvia ──
            logger.info("Fase 5: Gravar CTe Complementar")

            # Descobrir qual acao de gravar existe
            grv_action = await popup.evaluate("""() => {
                const links = document.querySelectorAll('a');
                for (const l of links) {
                    const oc = l.getAttribute('onclick') || '';
                    if (oc.includes('ajaxEnvia') && oc.includes('GRV'))
                        return oc.replace(';return false;', '');
                    if (oc.includes('ajaxEnvia') && l.innerText.includes('Gravar'))
                        return oc.replace(';return false;', '');
                }
                // Fallback: tentar ENV que e o padrao para submeter
                return null;
            }""")

            logger.info("Acao gravar: %s", grv_action)

            if grv_action:
                html_grv = await interceptar_ajax_response(
                    popup, popup, grv_action, timeout_s=30
                )
            else:
                # Fallback: click no primeiro ► da tela
                html_grv = await interceptar_ajax_response(
                    popup, popup, "ajaxEnvia('GRV', 0)", timeout_s=30
                )

            if html_grv:
                await injetar_html_no_dom(popup, html_grv)
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(5)

            await capturar_screenshot(popup, "222_pos_gravar")

            # Extrair CTRC do resultado
            body_final = await popup.evaluate(
                "() => document.body ? document.body.innerText.substring(0,5000) : ''"
            )

            # Tentar extrair numero do CTRC complementar gerado
            if not ctrc_complementar_num:
                m = re.search(r'CTRC\s*(?:anterior|complementar|gerado)\s*:?\s*0*(\d+)', body_final, re.IGNORECASE)
                if m:
                    ctrc_complementar_num = m.group(1)
                if not ctrc_complementar_num:
                    m = re.search(r'pre-?CTRC\s*:?\s*0*(\d+)', body_final, re.IGNORECASE)
                    if m:
                        ctrc_complementar_num = m.group(1)

            await capturar_screenshot(popup, "222_resultado_final")

            resultado['ctrc_complementar'] = ctrc_complementar_num
            resultado['dialogs'] = dialogs
            resultado['body_final'] = body_final[:2000]

            # ── Fase 6: Consultar 101 para baixar XML ──
            if ctrc_complementar_num:
                logger.info("Fase 6: Consultar CTRC %s via 101 para XML", ctrc_complementar_num)
                try:
                    from consultar_ctrc_101 import consultar_ctrc as _consultar
                    args_101 = argparse.Namespace(
                        ctrc=ctrc_complementar_num,
                        nf=None,
                        filial=filial,
                        baixar_xml=True,
                        baixar_dacte=True,
                        output_dir='/tmp/ssw_operacoes/cte_complementar',
                    )
                    res_101 = await _consultar(args_101)
                    if res_101.get('sucesso'):
                        resultado['xml'] = res_101.get('xml')
                        resultado['dacte'] = res_101.get('dacte')
                        resultado['dados_101'] = {
                            k: v for k, v in res_101.get('dados', {}).items()
                            if k != 'body_raw'
                        }
                        logger.info("XML baixado: %s", resultado.get('xml'))
                except Exception as e:
                    logger.warning("Consulta 101 falhou: %s", e)

            # Determinar sucesso
            if ctrc_complementar_num:
                resultado['sucesso'] = True
                resultado['mensagem'] = f"CTe Complementar {ctrc_complementar_num} gerado"
            else:
                # Sem CTRC mas pode ter dado certo — verificar body
                msg_ssw = await verificar_mensagem_ssw(popup)
                msg_str = str(msg_ssw) if msg_ssw else ''
                if msg_str and ('sucesso' in msg_str.lower() or 'autorizado' in msg_str.lower()):
                    resultado['sucesso'] = True
                    resultado['mensagem_ssw'] = msg_str
                    resultado['aviso'] = 'CTRC nao capturado — verificar no SSW'
                elif msg_str and ('erro' in msg_str.lower() or 'rejeit' in msg_str.lower()):
                    resultado['erro'] = msg_str
                else:
                    resultado['sucesso'] = True
                    resultado['aviso'] = 'Verificar manualmente no SSW'

            return resultado

        except Exception as e:
            logger.exception("Erro na emissao CTe Complementar 222: %s", e)
            await capturar_screenshot(popup if 'popup' in dir() else page, "222_erro")
            resultado['erro'] = str(e)
            return resultado

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Emitir CTe Complementar via SSW opcao 222"
    )
    parser.add_argument('--ctrc-pai', required=True, help='CTRC do CTe original (ex: CAR-113-9)')
    parser.add_argument('--motivo', required=True, choices=list(MOTIVOS_VALIDOS),
                        help='Motivo: C=complementar, D=descarga, E=estadia, R=reembolso')
    parser.add_argument('--valor-outros', type=float, required=True,
                        help='Valor a cobrar no campo Outros (R$)')
    parser.add_argument('--filial', default='CAR', help='Filial SSW (default: CAR)')
    parser.add_argument('--dry-run', action='store_true', help='Apenas preencher, nao submeter')

    args = parser.parse_args()
    resultado = asyncio.run(emitir_cte_complementar(args))
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
