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

            # Preencher CTRC — numero com DV (ex: 113-9)
            ctrc_com_dv = f"{ctrc_num}-{ctrc_dv}"
            await preencher_campo_no_html(popup, 'f2', ctrc_com_dv, by='name')
            await asyncio.sleep(0.3)

            await capturar_screenshot(popup, "222_preenchido_inicial")

            if args.dry_run:
                resultado['sucesso'] = True
                resultado['dry_run'] = True
                resultado['mensagem'] = 'Dry run: tela inicial preenchida, nao submetido'
                return resultado

            # Submeter tela inicial (OK/Prosseguir)
            logger.info("Fase 3b: Submeter tela inicial")
            html_tela2 = await interceptar_ajax_response(
                popup, frame, "ajaxEnvia('OK', 0)", timeout_s=15
            )

            if html_tela2:
                await injetar_html_no_dom(popup, html_tela2)
                await asyncio.sleep(1)
            else:
                # Tentar detectar erro
                msg = await verificar_mensagem_ssw(popup)
                if msg:
                    resultado['erro'] = f"SSW retornou: {msg}"
                    return resultado
                resultado['erro'] = "Sem resposta ao submeter tela inicial"
                return resultado

            await capturar_screenshot(popup, "222_tela_principal")

            # ── Fase 4: Tela Principal — preencher valor em "Outros" ──
            logger.info("Fase 4: Preencher valor em 'Outros'")

            # O valor vai no campo "outros" (parcela genérica)
            valor_formatado = f"{args.valor_outros:.2f}".replace('.', ',')
            await preencher_campo_no_html(popup, 'outros', valor_formatado, by='name')
            await asyncio.sleep(0.5)

            await capturar_screenshot(popup, "222_valor_preenchido")

            # ── Fase 5: Submeter ao SEFAZ ──
            logger.info("Fase 5: Submeter CTe Complementar")
            html_resultado = await interceptar_ajax_response(
                popup, frame, "ajaxEnvia('GRV', 0)", timeout_s=30
            )

            if html_resultado:
                await injetar_html_no_dom(popup, html_resultado)
                await asyncio.sleep(2)

            await capturar_screenshot(popup, "222_resultado_final")

            # Verificar resultado
            msg_ssw = await verificar_mensagem_ssw(popup)
            if msg_ssw:
                msg_lower = msg_ssw.lower()
                if 'erro' in msg_lower or 'rejeit' in msg_lower:
                    resultado['erro'] = msg_ssw
                    return resultado
                elif 'sucesso' in msg_lower or 'autorizado' in msg_lower:
                    resultado['sucesso'] = True
                    resultado['mensagem_ssw'] = msg_ssw
                else:
                    # Nao eh claro se deu certo — log e retornar com sucesso parcial
                    resultado['sucesso'] = True
                    resultado['mensagem_ssw'] = msg_ssw
                    resultado['aviso'] = 'Verificar manualmente no SSW'
            else:
                # Sem mensagem — pode ter dado certo
                resultado['sucesso'] = True
                resultado['aviso'] = 'Sem mensagem de retorno — verificar no SSW'

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
