"""
Backfill CTRC: varredura batch em 1 sessao SSW.

Abre 1 browser, loga 1 vez, e consulta todos os CTRCs
sequencialmente na mesma sessao (~5s por CTRC).

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_ctrc_ssw_batch.py [--max-ctrc 140]
"""
import asyncio
import json
import logging
import os
import re
import sys

SCRIPT_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '.claude', 'skills', 'operando-ssw', 'scripts'
)
if os.path.abspath(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, os.path.abspath(SCRIPT_DIR))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def formatar_ctrc(ctrc_completo):
    """CAR000113-9 → CAR-113-9"""
    m = re.match(r'^([A-Z]{2,4})0*(\d+)-(\d)$', ctrc_completo)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return ctrc_completo


def extrair_nct(cte_field):
    """'001 000000110' → 110"""
    if not cte_field:
        return None
    m = re.search(r'0*(\d+)$', cte_field.strip())
    return int(m.group(1)) if m else None


async def varrer_batch(max_ctrc=140, filial='CAR'):
    """Varre CTRCs 1..max_ctrc em 1 sessao SSW."""
    from playwright.async_api import async_playwright
    from ssw_common import verificar_credenciais, login_ssw, abrir_opcao_popup

    verificar_credenciais()
    nct_map = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 1000},
            accept_downloads=True,
        )
        page = await context.new_page()

        # Login 1 vez
        logger.info("Login SSW...")
        await login_ssw(page)

        main_frame = None
        for frame in page.frames:
            try:
                has_option = await frame.evaluate("() => !!document.getElementById('3')")
                if has_option:
                    main_frame = frame
                    break
            except Exception:
                continue

        if not main_frame:
            logger.error("Frame principal nao encontrado")
            await browser.close()
            return nct_map

        # Setar filial
        await main_frame.evaluate(f"""() => {{
            var el = document.getElementById('2');
            if (el) el.value = '{filial}';
        }}""")
        await asyncio.sleep(2)

        # Override para evitar abrir documento novo
        CREATE_NEW_DOC_OVERRIDE = """
        window.openNewDocument = function() {};
        window.abrirNovoDocumento = function() {};
        if (typeof createNewDoc !== 'undefined') createNewDoc = function() {};
        """

        for ctrc_num in range(1, max_ctrc + 1):
            try:
                # Abrir opcao 101 fresh a cada consulta (SSW muda DOM apos pesquisa)
                popup = await abrir_opcao_popup(context, main_frame, 101, timeout_s=20)
                await asyncio.sleep(2)

                # Dismiss dialogs automaticamente
                popup.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

                # Preencher campo CTRC
                fill_ok = await popup.evaluate(f"""() => {{
                    const el = document.getElementById('t_nro_ctrc');
                    if (!el) return false;
                    el.value = '{ctrc_num}';
                    return true;
                }}""")

                if not fill_ok:
                    logger.warning("  CTRC %d: campo t_nro_ctrc nao encontrado", ctrc_num)
                    try:
                        await popup.close()
                    except Exception:
                        pass
                    continue

                # Override + Pesquisar
                await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                await popup.evaluate("ajaxEnvia('P1', 1)")
                await asyncio.sleep(6)

                try:
                    await popup.evaluate(CREATE_NEW_DOC_OVERRIDE)
                except Exception:
                    pass

                # Extrair dados
                body = await popup.evaluate(
                    "() => document.body ? document.body.innerText.substring(0,8000) : ''"
                )

                # Extrair CTRC completo
                m_ctrc = re.search(
                    r'CTRC\s*/Subc\./RPS:\s*(.+?)(?:\n|DACTE)', body, re.IGNORECASE
                )
                ctrc_completo = m_ctrc.group(1).strip() if m_ctrc else None

                # Extrair CT-e
                m_cte = re.search(r'CT-e:\s*(\d+\s+\d+)', body, re.IGNORECASE)
                cte_field = m_cte.group(1).strip() if m_cte else None
                nct = extrair_nct(cte_field)

                if nct is not None and ctrc_completo:
                    ctrc_fmt = formatar_ctrc(ctrc_completo)
                    nct_map[nct] = ctrc_fmt
                    logger.info("  CTRC %d → CT-e %d → %s", ctrc_num, nct, ctrc_fmt)
                elif 'não encontrad' in body.lower() or 'nao encontrad' in body.lower():
                    logger.debug("  CTRC %d: nao encontrado", ctrc_num)
                else:
                    logger.debug("  CTRC %d: sem dados extraidos", ctrc_num)

                # Fechar popup para limpar
                try:
                    await popup.close()
                except Exception:
                    pass

            except Exception as e:
                logger.warning("  CTRC %d: erro — %s", ctrc_num, str(e)[:100])
                try:
                    await popup.close()
                except Exception:
                    pass

        await browser.close()

    logger.info("Varredura concluida: %d entradas nCT→CTRC", len(nct_map))
    return nct_map


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-ctrc', type=int, default=140)
    parser.add_argument('--filial', default='CAR')
    parser.add_argument('--output', default=os.path.join(
        os.path.dirname(__file__), 'nct_ctrc_map.json'
    ))
    args = parser.parse_args()

    nct_map = asyncio.run(varrer_batch(args.max_ctrc, args.filial))

    # Salvar mapa
    with open(args.output, 'w') as f:
        json.dump({str(k): v for k, v in sorted(nct_map.items())}, f, indent=2)
    logger.info("Mapa salvo em %s (%d entradas)", args.output, len(nct_map))


if __name__ == '__main__':
    main()
