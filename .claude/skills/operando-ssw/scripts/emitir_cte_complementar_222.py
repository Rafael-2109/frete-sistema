"""
Emissao de CTe Complementar via SSW opcao 222 (+ envio SEFAZ opcao 007 + baixar XML via 101).

Fluxo completo (11 fases) baseado em Playwright codegen capturado do usuario.

SEGUIR EXATAMENTE o codegen — nao adicionar logica defensiva que nao esteja no codegen.

Uso:
    python emitir_cte_complementar_222.py --ctrc-pai CAR-59-1 --motivo D \\
        --valor-outros 227.90 [--tp-doc C] [--unid-emit D] [--enviar-sefaz]
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
    capturar_screenshot,
    gerar_saida,
)

logger = logging.getLogger(__name__)

# Motivos validos
MOTIVOS_VALIDOS = {'C', 'D', 'V', 'E', 'R'}
TP_DOC_VALIDOS = {'C'}
UNID_EMIT_VALIDOS = {'D', 'O'}


def validar_args(args):
    erros = []
    if not args.ctrc_pai:
        erros.append("ctrc_pai obrigatorio (ex: CAR-59-1)")
    if args.motivo not in MOTIVOS_VALIDOS:
        erros.append(f"motivo invalido: {args.motivo}. Validos: {MOTIVOS_VALIDOS}")
    # --valor-outros OU --valor-base (um dos dois obrigatorio)
    has_outros = args.valor_outros is not None and args.valor_outros > 0
    has_base = args.valor_base is not None and args.valor_base > 0
    if not has_outros and not has_base:
        erros.append(
            "Passar --valor-outros (valor final, pos-grossing up) "
            "OU --valor-base (valor bruto, script calcula automatic)"
        )
    if args.tp_doc not in TP_DOC_VALIDOS:
        erros.append(f"tp_doc invalido: {args.tp_doc}. Validos: {TP_DOC_VALIDOS}")
    if args.unid_emit not in UNID_EMIT_VALIDOS:
        erros.append(
            f"unid_emit invalido: {args.unid_emit}. Validos: {UNID_EMIT_VALIDOS}"
        )
    if erros:
        raise ValueError("; ".join(erros))


def parsear_ctrc(ctrc_pai):
    partes = ctrc_pai.split('-')
    if len(partes) != 3:
        raise ValueError(
            f"CTRC formato invalido: {ctrc_pai}. Esperado: FILIAL-NUMERO-DV"
        )
    return partes[0], partes[1], partes[2]


def _parse_valor_brasileiro(s):
    """Converte '1.863,72' → 1863.72"""
    if not s:
        return 0.0
    s = s.strip().replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


async def consultar_icms_pai(ctrc_num, filial):
    """Consulta opcao 101 do CTRC pai e extrai frete/ICMS/aliquota.

    Usado para calcular o grossing up correto do CTe complementar baseado no
    ICMS real da prestacao original (e nao uma estimativa fixa).

    Returns:
        dict com {valor_frete, valor_icms, aliquota_icms, ...} ou None se erro
    """
    try:
        from consultar_ctrc_101 import consultar_ctrc as _consultar
        args_101 = argparse.Namespace(
            ctrc=ctrc_num,
            nf=None,
            filial=filial,
            baixar_xml=False,
            baixar_dacte=False,
            output_dir='/tmp/ssw_operacoes/consulta_icms_pai',
        )
        res = await _consultar(args_101)
        if not res.get('sucesso'):
            logger.warning("Consulta 101 do pai %s-%s falhou", filial, ctrc_num)
            return None

        body = res.get('dados', {}).get('body_raw', '')
        # Regex para ICMS/ISS no body da tela 101
        m_icms = re.search(r"ICMS/ISS\s*\(R\$\):\s*([\d.,]+)", body)
        m_frete = re.search(r"Valor\s*frete\s*\(R\$\):\s*([\d.,]+)", body)

        valor_icms = _parse_valor_brasileiro(m_icms.group(1)) if m_icms else 0.0
        valor_frete = _parse_valor_brasileiro(m_frete.group(1)) if m_frete else 0.0

        aliquota = None
        if valor_frete > 0 and valor_icms > 0:
            aliquota = round((valor_icms / valor_frete) * 100, 2)

        dados = res.get('dados', {})
        return {
            'valor_frete': valor_frete,
            'valor_icms': valor_icms,
            'aliquota_icms': aliquota,
            'ctrc_completo': dados.get('ctrc_completo'),
            'cte': dados.get('cte'),
            'destino': dados.get('destino'),
            'remetente_cnpj': dados.get('remetente_cnpj'),
            'destinatario_cnpj': dados.get('destinatario_cnpj'),
            'nf': dados.get('nf'),
        }
    except Exception as e:
        logger.warning("Erro ao consultar ICMS do pai: %s", e)
        return None


# Divisor PIS/COFINS fixo 9,25% (mesma regra do custo_entrega_routes.py)
PISCOFINS_DIVISOR = 0.9075


def calcular_valor_cte_complementar(valor_base, aliquota_icms):
    """Grossing up: valor_base / 0,9075 / (1 - icms/100).

    Identico ao calculo da rota custo_entrega_routes.py.
    Para liquido=valor_base apos PIS/COFINS+ICMS.
    """
    icms_divisor = 1.0 - (aliquota_icms / 100.0)
    if icms_divisor <= 0:
        raise ValueError(f"Aliquota ICMS invalida: {aliquota_icms}")
    return round(valor_base / PISCOFINS_DIVISOR / icms_divisor, 2)


async def emitir_cte_complementar(args):
    """Fluxo completo baseado em codegen. NAO adicionar logica extra."""
    from playwright.async_api import async_playwright

    try:
        validar_args(args)
    except ValueError as e:
        return gerar_saida(False, erro=str(e))

    filial_pai, ctrc_num, ctrc_dv = parsear_ctrc(args.ctrc_pai)
    verificar_credenciais()

    # ── Auto-calculo do valor_outros via ICMS do CTe pai ──
    icms_pai_info = None
    if args.valor_base and not args.valor_outros:
        logger.info(
            "Auto-calculo: consultando ICMS do CTe pai %s-%s via opcao 101",
            filial_pai, ctrc_num
        )
        icms_pai_info = await consultar_icms_pai(ctrc_num, filial_pai)
        if not icms_pai_info:
            return gerar_saida(
                False,
                erro=(
                    f"Nao conseguiu consultar ICMS do CTe pai {args.ctrc_pai}. "
                    f"Passe --valor-outros manualmente."
                ),
            )
        aliquota = icms_pai_info.get('aliquota_icms')
        if not aliquota or aliquota <= 0:
            return gerar_saida(
                False,
                erro=(
                    f"ICMS do pai invalido: frete={icms_pai_info.get('valor_frete')} "
                    f"icms={icms_pai_info.get('valor_icms')} aliq={aliquota}. "
                    f"Passe --valor-outros manualmente."
                ),
                icms_pai=icms_pai_info,
            )
        try:
            valor_calculado = calcular_valor_cte_complementar(
                args.valor_base, aliquota
            )
        except ValueError as e:
            return gerar_saida(False, erro=str(e))
        logger.info(
            "ICMS pai: %s%% (frete=%s, icms=%s) → valor_outros=%s (base=%s)",
            aliquota, icms_pai_info['valor_frete'], icms_pai_info['valor_icms'],
            valor_calculado, args.valor_base
        )
        args.valor_outros = valor_calculado

    resultado = {
        'sucesso': False,
        'ctrc_pai': args.ctrc_pai,
        'motivo': args.motivo,
        'valor_outros': args.valor_outros,
        'valor_base': args.valor_base,
        'icms_pai': icms_pai_info,
        'tp_doc': args.tp_doc,
        'unid_emit': args.unid_emit,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        # Playwright async AUTO-DISMISSA dialogs por default (alert/confirm/prompt).
        # SSW usa alert() nativo para "Novo CTRC: XXX-YYY-Z" — precisamos
        # registrar handler em TODAS as pages do context para capturar a mensagem.
        dialog_messages = []
        ctrc_from_dialog = {'value': None}

        async def _capture_dialog(dialog):
            try:
                msg = dialog.message
                dialog_messages.append({'type': dialog.type, 'msg': msg})
                logger.info("DIALOG %s capturado: %s", dialog.type, msg[:300])
                # Extrair padrao "Novo CTRC: XXX000YYY-Z"
                m = re.search(r'Novo CTRC:\s*([A-Z]+)0*(\d+)-(\d)', msg)
                if m and not ctrc_from_dialog['value']:
                    ctrc_from_dialog['value'] = (
                        m.group(1), m.group(2), m.group(3)
                    )
                    logger.info(
                        "CTRC extraido do dialog: %s-%s-%s",
                        m.group(1), m.group(2), m.group(3)
                    )
                await dialog.accept()
            except Exception as e:
                logger.warning("on_dialog erro: %s", e)

        def _attach_dialog_handler(p_obj):
            """Registra handler em uma page para capturar dialogs nativos."""
            p_obj.on("dialog", lambda d: asyncio.create_task(_capture_dialog(d)))

        # Registrar em TODA nova page criada no context (popup 222, etc.)
        context.on("page", _attach_dialog_handler)
        _attach_dialog_handler(page)

        try:
            # ── FASE 1: Login (reutilizar login_ssw) ──
            logger.info("Fase 1: Login SSW")
            await login_ssw(page)
            main_frame = page.frames[0]
            await asyncio.sleep(1)

            # ── FASE 2: Abrir opcao 222 → popup page1 ──
            # Usar abrir_opcao_popup (doOption via main_frame) — testado OK
            logger.info("Fase 2: Abrir opcao 222")
            page1 = await abrir_opcao_popup(context, main_frame, 222)
            await asyncio.sleep(2)
            await capturar_screenshot(page1, "222_tela_inicial")

            # ── FASE 3: Preencher tela inicial (page1) ──
            # Codegen: #motivo.fill + [id="1"].fill(filial) + [id="2"].fill(ctrc_concat)
            ctrc_concatenado = f"{ctrc_num}{ctrc_dv}"
            logger.info(
                "Fase 3: motivo=%s filial=%s ctrc=%s",
                args.motivo, filial_pai, ctrc_concatenado
            )

            await page1.locator("#motivo").fill(args.motivo)
            await page1.locator('[id="1"]').fill(filial_pai)
            await page1.locator('[id="2"]').fill(ctrc_concatenado)
            await asyncio.sleep(0.5)
            await capturar_screenshot(page1, "222_preenchido_inicial")

            if args.dry_run:
                resultado['sucesso'] = True
                resultado['dry_run'] = True
                resultado['mensagem'] = 'Dry run: tela inicial preenchida'
                return resultado

            # ── FASE 4: Click [id="3"] → abre popup page2 ──
            logger.info("Fase 4: Click ► → abre popup page2")
            async with page1.expect_popup(timeout=20000) as page2_info:
                await page1.locator('[id="3"]').click()
            page2 = await page2_info.value
            try:
                await page2.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await asyncio.sleep(1)
            await capturar_screenshot(page2, "222_tela_principal")

            # ── FASE 5: Preencher tela principal (page2) ──
            # Codegen EXATO:
            #   #vlr_outros.click() + .fill(valor)
            #   #tp_doc.click() + .fill("C")
            #   #unid_emit.dblclick() + .fill("D")   <-- DBLCLICK antes de fill!
            valor_formatado = f"{args.valor_outros:.2f}".replace('.', ',')
            logger.info(
                "Fase 5: vlr_outros=%s tp_doc=%s unid_emit=%s",
                valor_formatado, args.tp_doc, args.unid_emit
            )

            await page2.locator("#vlr_outros").click()
            await page2.locator("#vlr_outros").fill(valor_formatado)

            await page2.locator("#tp_doc").click()
            await page2.locator("#tp_doc").fill(args.tp_doc)

            # unid_emit: SSW pode vir readonly com valor fixo (SSW decide
            # a filial do complementar baseado na carga). Nesse caso, respeitar.
            unid_info = await page2.locator("#unid_emit").evaluate(
                "(el) => ({"
                "readonly: el.readOnly || el.hasAttribute('readonly'),"
                "value: el.value || ''"
                "})"
            )
            logger.info("unid_emit: readonly=%s value=%s",
                        unid_info['readonly'], unid_info['value'])
            if not unid_info['readonly']:
                # Editavel — dblclick + fill conforme codegen
                await page2.locator("#unid_emit").dblclick()
                await page2.locator("#unid_emit").fill(args.unid_emit)
                resultado['unid_emit_usado'] = args.unid_emit
            else:
                # SSW forcou — respeitar
                resultado['unid_emit_usado'] = unid_info['value']
                resultado['unid_emit_readonly'] = True
                logger.info(
                    "SSW forcou unid_emit=%s — nao pode alterar "
                    "(SSW decide filial do complementar baseado na carga)",
                    unid_info['value']
                )

            await asyncio.sleep(0.5)
            await capturar_screenshot(page2, "222_valor_preenchido")

            # ── FASE 6: Click ► + Continuar (page2) ──
            logger.info("Fase 6: Gravar — click ► + Continuar")

            # Salvar HTML ANTES do click ►
            try:
                html_antes = await page2.content()
                with open('/tmp/ssw_operacoes/222_debug_page2_antes_submit.html', 'w') as f:
                    f.write(html_antes)
                logger.info("HTML page2 antes submit: %d chars", len(html_antes))
            except Exception:
                pass

            # Diagnostico: o ► existe?
            try:
                count_submit = await page2.get_by_role("link", name="►").count()
                logger.info("Links ► em page2: %d", count_submit)
            except Exception:
                count_submit = 0

            # Click no ► — timeout curto evita 30s aguardando errorpanel
            # (Sentry PYTHON-FLASK-DE/DF: <div id="errorpanel"> intercepta
            # pointer events; fallback evaluate JS abaixo bypassa o overlay).
            try:
                await page2.get_by_role("link", name="►").first.click(timeout=3000)
                logger.info("Click ► via get_by_role ok")
            except Exception as e:
                logger.warning("Click ► falhou: %s — tentando via evaluate", e)
                # Fallback: encontrar o <a> com onclick que contem ENV2
                try:
                    await page2.evaluate("""() => {
                        const links = document.querySelectorAll('a');
                        for (const l of links) {
                            const oc = l.getAttribute('onclick') || '';
                            if (oc.includes("ajaxEnvia('ENV2'")) {
                                l.click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    logger.info("Click ► via evaluate ok")
                except Exception as e2:
                    logger.error("Click ► evaluate tambem falhou: %s", e2)

            await asyncio.sleep(3)

            # Salvar HTML APOS click ►
            try:
                html_pos = await page2.content()
                with open('/tmp/ssw_operacoes/222_debug_page2_pos_submit.html', 'w') as f:
                    f.write(html_pos)
                logger.info("HTML page2 pos submit: %d chars", len(html_pos))
            except Exception:
                pass

            # Diagnostico: Continuar existe agora?
            try:
                count_continuar = await page2.get_by_role(
                    "link", name=re.compile(r"Continuar")
                ).count()
                logger.info("Links Continuar em page2: %d", count_continuar)
            except Exception:
                count_continuar = 0

            # Click Continuar — tentar por id="0", depois por role
            continuar_clicked = False
            try:
                # Link id="0" tem onclick com ajaxEnviah ENV2 btn_200='S'
                el_count = await page2.locator('[id="0"]').count()
                logger.info("Elementos [id='0'] em page2: %d", el_count)
                if el_count > 0:
                    await page2.locator('[id="0"]').click()
                    continuar_clicked = True
                    logger.info("Click Continuar via [id='0'] ok")
            except Exception as e:
                logger.warning("Click Continuar via id falhou: %s", e)

            if not continuar_clicked and count_continuar > 0:
                try:
                    await page2.get_by_role(
                        "link", name=re.compile(r"Continuar")
                    ).first.click()
                    continuar_clicked = True
                    logger.info("Click Continuar via get_by_role ok")
                except Exception as e:
                    logger.warning("Click Continuar via role falhou: %s", e)

            if not continuar_clicked:
                # Fallback: clicar via evaluate no link que contem 'ENV2'
                try:
                    clicked = await page2.evaluate("""() => {
                        const links = document.querySelectorAll('a');
                        for (const l of links) {
                            const oc = l.getAttribute('onclick') || '';
                            if (oc.includes("ajaxEnviah('ENV2'") ||
                                (oc.includes("btn_200") && oc.includes("'S'"))) {
                                l.click();
                                return l.innerText || l.textContent || '';
                            }
                        }
                        return null;
                    }""")
                    if clicked is not None:
                        continuar_clicked = True
                        logger.info("Click Continuar via evaluate: %s", clicked)
                except Exception as e:
                    logger.error("Click Continuar evaluate falhou: %s", e)

            if not continuar_clicked:
                logger.warning("Continuar NAO foi clicado em nenhuma tentativa")

            await asyncio.sleep(3)

            # SSW pode ter MULTIPLOS avisos em sequencia (ex: aviso CFOP+ICMS,
            # depois outro aviso, depois o CTRC). Loop: enquanto aparecer
            # "Continuar" ou "2. Continuar", clicar.
            for loop_idx in range(5):
                try:
                    # Salvar HTML atual para debug
                    html_loop = await page2.content()
                    with open(
                        f'/tmp/ssw_operacoes/222_debug_page2_loop{loop_idx}.html',
                        'w'
                    ) as f:
                        f.write(html_loop)

                    # Ha botao Continuar visivel?
                    has_continuar = 'Continuar' in html_loop and (
                        '2. Continuar' in html_loop or
                        "'S'" in html_loop and 'btn_' in html_loop
                    )
                    logger.info(
                        "Loop %d: Continuar presente=%s (html=%d chars)",
                        loop_idx, has_continuar, len(html_loop)
                    )

                    if not has_continuar:
                        logger.info("Sem mais Continuar — saindo do loop")
                        break

                    # Click via evaluate (mais robusto)
                    clicked_info = await page2.evaluate("""() => {
                        const links = document.querySelectorAll('a.dialog');
                        for (const l of links) {
                            const txt = (l.innerText || '').trim();
                            const oc = l.getAttribute('onclick') || '';
                            if ((txt.includes('Continuar') || txt.includes('2.')) &&
                                oc.includes('ajaxEnvia')) {
                                l.click();
                                return {text: txt, onclick: oc.substring(0, 200)};
                            }
                        }
                        return null;
                    }""")
                    logger.info("Loop %d click: %s", loop_idx, clicked_info)
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning("Loop %d erro: %s", loop_idx, e)
                    break

            await asyncio.sleep(3)

            # Debug: salvar HTML de page1 e page2 apos gravar
            try:
                html_page1 = await page1.content()
                with open('/tmp/ssw_operacoes/222_debug_page1_pos_gravar.html', 'w') as f:
                    f.write(html_page1)
                logger.info("HTML page1 salvo (%d chars)", len(html_page1))
            except Exception as e:
                logger.warning("Falha ao salvar HTML page1: %s", e)

            try:
                html_page2 = await page2.content()
                with open('/tmp/ssw_operacoes/222_debug_page2_pos_gravar.html', 'w') as f:
                    f.write(html_page2)
                logger.info("HTML page2 salvo (%d chars)", len(html_page2))
            except Exception as e:
                logger.warning("page2 ja fechada ou sem HTML: %s", e)

            await capturar_screenshot(page1, "222_pos_gravar_page1")

            # ── FASE 7: Capturar aviso "Novo CTRC: XXX000YYY-Z" ──
            logger.info("Fase 7: Capturar aviso do CTRC")

            ctrc_complementar = None
            filial_complementar = None
            num_complementar = None
            dv_complementar = None
            aviso_texto = None

            # FONTE 1: Dialog nativo capturado pelo handler (prioridade)
            if ctrc_from_dialog['value']:
                filial_complementar, num_complementar, dv_complementar = (
                    ctrc_from_dialog['value']
                )
                ctrc_complementar = (
                    f"{filial_complementar}-{num_complementar}-{dv_complementar}"
                )
                logger.info("CTRC via dialog: %s", ctrc_complementar)
                aviso_texto = '\n'.join(
                    d['msg'] for d in dialog_messages
                )[:2000]

            # FONTE 2: Fallback — buscar texto "Novo CTRC" em todos os frames/pages
            if not ctrc_complementar:
                all_pages = context.pages
                logger.info(
                    "Fallback HTML — pages abertas: %d",
                    len(all_pages)
                )
                for idx, p_search in enumerate(all_pages):
                    try:
                        if p_search.is_closed():
                            continue
                        for frame_idx, frame in enumerate(p_search.frames):
                            try:
                                text = await frame.evaluate(
                                    "() => document.body "
                                    "? document.body.innerText : ''"
                                )
                                if text and 'Novo CTRC' in text:
                                    logger.info(
                                        "Achou aviso em page %d frame %d",
                                        idx, frame_idx
                                    )
                                    aviso_texto = text
                                    break
                            except Exception:
                                pass
                        if aviso_texto:
                            break
                    except Exception:
                        pass

                if aviso_texto:
                    m = re.search(
                        r'Novo CTRC:\s*([A-Z]+)0*(\d+)-(\d)',
                        aviso_texto
                    )
                    if m:
                        filial_complementar = m.group(1)
                        num_complementar = m.group(2)
                        dv_complementar = m.group(3)
                        ctrc_complementar = (
                            f"{filial_complementar}-{num_complementar}"
                            f"-{dv_complementar}"
                        )

            resultado['dialog_messages'] = dialog_messages

            if aviso_texto:
                logger.info("Body (primeiros 500 chars): %s", aviso_texto[:500])
                m = re.search(
                    r'Novo CTRC:\s*([A-Z]+)0*(\d+)-(\d)',
                    aviso_texto
                )
                if m:
                    filial_complementar = m.group(1)
                    num_complementar = m.group(2)
                    dv_complementar = m.group(3)
                    ctrc_complementar = (
                        f"{filial_complementar}-{num_complementar}-{dv_complementar}"
                    )
                    logger.info("CTRC Complementar: %s", ctrc_complementar)
                    resultado['ctrc_complementar'] = ctrc_complementar
                    resultado['filial_complementar'] = filial_complementar
                    resultado['numero_complementar'] = num_complementar
                    resultado['dv_complementar'] = dv_complementar

            await capturar_screenshot(page1, "222_aviso_ctrc")

            # Click OK para fechar aviso
            try:
                await page1.get_by_role("link", name="OK").click(timeout=5000)
                await asyncio.sleep(1)
            except Exception as e:
                logger.debug("Link OK nao encontrado: %s", e)

            if not ctrc_complementar:
                resultado['erro'] = 'Nao capturou CTRC Complementar da page1'
                resultado['aviso_bruto'] = (aviso_texto or '')[:2000]
                return resultado

            # Nao fechar popups — precisamos da page principal para 007
            # Mas o SSW provavelmente ja fechou page2 apos gravar

            # Se nao pediu SEFAZ, retorna aqui
            if not args.enviar_sefaz:
                resultado['sucesso'] = True
                resultado['sefaz_enviado'] = False
                resultado['mensagem'] = (
                    f'Pre-CTRC {ctrc_complementar} criado. SEFAZ nao enviado.'
                )
                return resultado

            # ── FASE 8: Trocar filial no menu principal ──
            # Via main_frame.evaluate (page.locator nao funciona em async quando
            # o elemento esta dentro de um frame do frameset SSW)
            logger.info(
                "Fase 8: Trocar filial menu para %s (filial do novo CTRC)",
                filial_complementar
            )
            try:
                await main_frame.evaluate(f"""() => {{
                    var el = document.getElementById('2');
                    if (el) {{
                        el.value = '{filial_complementar}';
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        el.dispatchEvent(new Event('blur', {{bubbles: true}}));
                    }}
                }}""")
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning("Trocar filial falhou: %s", e)

            # ── FASE 9: Abrir opcao 007 → popup page3 ──
            logger.info("Fase 9: Abrir opcao 007 (Envio SEFAZ)")
            try:
                page3 = await abrir_opcao_popup(context, main_frame, 7)
                await asyncio.sleep(2)
                await capturar_screenshot(page3, "007_inicial")

                # Click "Enviar à SEFAZ"
                await page3.get_by_role(
                    "link", name="Enviar à SEFAZ"
                ).click(timeout=15000)
                await asyncio.sleep(5)
                await capturar_screenshot(page3, "007_pos_enviar")
                resultado['sefaz_enviado'] = True
            except Exception as e:
                logger.error("Erro na opcao 007 (SEFAZ): %s", e)
                resultado['sefaz_erro'] = str(e)

            # Dismiss DCe dialog — aguardar SSW processar
            await asyncio.sleep(3)

            # ── FASE 10: Abrir opcao 101 → popup page4 ──
            logger.info("Fase 10: Abrir opcao 101 para consulta")
            try:
                page4 = await abrir_opcao_popup(context, main_frame, 101)
                try:
                    await page4.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(2)

                # Preencher numero do CTRC
                await page4.locator("#t_nro_ctrc").click()
                await page4.locator("#t_nro_ctrc").fill(num_complementar)

                # Press Enter → novo popup page5
                async with page4.expect_popup(timeout=20000) as page5_info:
                    await page4.locator("#t_nro_ctrc").press("Enter")
                page5 = await page5_info.value
                try:
                    await page5.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(3)
                await capturar_screenshot(page5, "101_consulta")

                # Download DACTE
                try:
                    async with page5.expect_download(timeout=30000) as dacte_info:
                        await page5.get_by_role("link", name="DACTE").click()
                    dacte_download = await dacte_info.value
                    dacte_path = f"/tmp/ssw_operacoes/cte_complementar/{filial_complementar}-{num_complementar}-{dv_complementar}.pdf"
                    os.makedirs(os.path.dirname(dacte_path), exist_ok=True)
                    await dacte_download.save_as(dacte_path)
                    resultado['dacte'] = dacte_path
                    logger.info("DACTE baixado: %s", dacte_path)
                except Exception as e:
                    logger.warning("Download DACTE falhou: %s", e)
                    resultado['dacte_erro'] = str(e)

                # Download XML
                try:
                    async with page5.expect_download(timeout=30000) as xml_info:
                        await page5.get_by_role("link", name="XML").click()
                    xml_download = await xml_info.value
                    xml_path = f"/tmp/ssw_operacoes/cte_complementar/{filial_complementar}-{num_complementar}-{dv_complementar}.xml"
                    os.makedirs(os.path.dirname(xml_path), exist_ok=True)
                    await xml_download.save_as(xml_path)
                    resultado['xml'] = xml_path
                    logger.info("XML baixado: %s", xml_path)
                except Exception as e:
                    logger.warning("Download XML falhou: %s", e)
                    resultado['xml_erro'] = str(e)

            except Exception as e:
                logger.warning("Consulta 101 falhou: %s", e)
                resultado['consulta_101_erro'] = str(e)

            # Sucesso
            resultado['sucesso'] = True
            resultado['mensagem'] = (
                f"CTe Complementar {ctrc_complementar} emitido" +
                (
                    f" — XML: {resultado.get('xml')}"
                    if resultado.get('xml') else " — XML nao baixado"
                )
            )
            return resultado

        except Exception as e:
            logger.exception("Erro na emissao 222: %s", e)
            try:
                await capturar_screenshot(page, "222_erro_geral")
            except Exception:
                pass
            resultado['erro'] = str(e)
            return resultado

        finally:
            try:
                await browser.close()
            except Exception:
                pass


def main():
    # Configurar logging para ver logs INFO no stderr
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(
        description="Emitir CTe Complementar via SSW opcao 222 + SEFAZ 007 + 101"
    )
    parser.add_argument('--ctrc-pai', required=True)
    parser.add_argument('--motivo', required=True, choices=list(MOTIVOS_VALIDOS))
    parser.add_argument(
        '--valor-outros', type=float, default=None,
        help='Valor final ja com grossing up (R$). Alternativa: --valor-base'
    )
    parser.add_argument(
        '--valor-base', type=float, default=None,
        help='Valor bruto do custo entrega (R$). Script calcula grossing '
             'up automaticamente consultando ICMS do CTe pai via opcao 101.'
    )
    parser.add_argument('--tp-doc', default='C', choices=list(TP_DOC_VALIDOS))
    parser.add_argument('--unid-emit', default='D', choices=list(UNID_EMIT_VALIDOS))
    parser.add_argument('--enviar-sefaz', action='store_true', default=False)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--filial', default=None, help='(ignorado)')

    args = parser.parse_args()
    resultado = asyncio.run(emitir_cte_complementar(args))
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
