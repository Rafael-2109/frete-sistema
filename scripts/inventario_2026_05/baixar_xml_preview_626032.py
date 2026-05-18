"""Baixa XML de pré-visualizacao da invoice 626032 e insere como anexo no Odoo.

Caso de uso: NF 626032 em `excecao_autorizado` com `l10n_br_xml_aut_nfe`
vazio (G008). Sem o XML, Odoo nao permite cancelar. Solucao: baixar via
botao "Pre Visualizar XML NF-e" + inserir manualmente no campo.

Uso:
    python scripts/inventario_2026_05/baixar_xml_preview_626032.py
"""
import base64
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.recebimento.services.playwright_nfe_transmissao import (
    _resolver_cids_e_menu,
    _fechar_modais_tecnicos,
    _clicar_botao_preview_xml,
    _login_odoo,
    ODOO_URL,
)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


INVOICE_ID = 626032


def main():
    from playwright.sync_api import sync_playwright

    odoo_url = os.getenv('ODOO_URL', 'https://odoo.nacomgoya.com.br')
    odoo_user = os.getenv('ODOO_USERNAME')
    odoo_pass = os.getenv('ODOO_PASSWORD')
    if not odoo_user or not odoo_pass:
        raise RuntimeError('ODOO_USERNAME e ODOO_PASSWORD obrigatorios no .env')

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        # Ler company_id da invoice para resolver cids
        inv = odoo.read('account.move', [INVOICE_ID],
                        ['name', 'company_id', 'l10n_br_xml_aut_nfe'])
        company_id = inv[0]['company_id'][0]
        logger.info(f'Invoice {INVOICE_ID} ({inv[0]["name"]}) company={company_id}')

        cids, menu_id = _resolver_cids_e_menu(company_id)
        logger.info(f'cids={cids} menu_id={menu_id}')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1. Login (helper JSON-RPC + fallback UI)
        logger.info('[1] Login Odoo via _login_odoo...')
        if not _login_odoo(page, context, logger):
            logger.error('Login falhou!')
            browser.close()
            return

        # 2. Setar allowed_company_ids correto via /web?cids=...
        logger.info(f'[2] Forcando cids={cids}...')
        page.goto(f'{ODOO_URL}/web?cids={cids}', timeout=30000)
        page.wait_for_load_state('domcontentloaded', timeout=30000)
        time.sleep(2)

        # 3. Navegar para invoice
        url = (f'{ODOO_URL}/web#id={INVOICE_ID}&cids={cids}'
               f'&model=account.move&view_type=form')
        logger.info(f'[3] Navegando: {url}')
        page.goto(url, timeout=30000)
        page.wait_for_load_state('domcontentloaded', timeout=30000)
        time.sleep(5)

        _fechar_modais_tecnicos(page, logger)

        # 4. Clicar "Pre Visualizar XML NF-e" — tenta DOWNLOAD primeiro
        logger.info('[4] Clicando "Pre Visualizar XML NF-e" (esperando download)...')
        xml_content = None
        try:
            with page.expect_download(timeout=12000) as dl_info:
                clicou = _clicar_botao_preview_xml(page, logger)
                if not clicou:
                    logger.error('Botao "Pre Visualizar XML" NAO encontrado!')
                    browser.close()
                    return
            download = dl_info.value
            dl_path = f'/tmp/sefaz_debug/download_{INVOICE_ID}_{download.suggested_filename}'
            download.save_as(dl_path)
            logger.info(f'[5] DOWNLOAD capturado: {dl_path} (sugestao={download.suggested_filename})')
            with open(dl_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except Exception as e_dl:
            logger.warning(f'expect_download timeout: {e_dl}. Tentando expect_page...')
            try:
                with context.expect_page(timeout=8000) as np_info:
                    _clicar_botao_preview_xml(page, logger)
                new_page = np_info.value
                time.sleep(3)
                content = new_page.content()
                body_text = new_page.locator('body').inner_text()
                if '<?xml' in body_text:
                    xml_content = body_text
                elif '<?xml' in content:
                    xs = content.index('<?xml')
                    xml_content = content[xs:]
                logger.info(f'[5] XML via NEW PAGE: {len(xml_content) if xml_content else 0} chars')
            except Exception as e_np:
                logger.warning(f'expect_page tambem timeout: {e_np}')
                # Ultima tentativa: ver se XML apareceu na pagina principal
                time.sleep(3)
                page.screenshot(path=f'/tmp/sefaz_debug/preview_xml_main_{INVOICE_ID}.png')
                body_text = page.locator('body').inner_text()
                if '<?xml' in body_text:
                    xml_content = body_text
                    logger.info(f'[5] XML via MAIN PAGE body: {len(xml_content)} chars')

        if not xml_content:
            logger.error('XML NAO foi capturado por nenhuma estrategia. Aborting.')
            browser.close()
            return

        content = xml_content
        logger.info(f'[6] Content size: {len(content)} chars')

        # xml_content ja foi setado acima (download ou body)
        if '<?xml' in xml_content:
            # Limpar wrapper se vier de body de pagina HTML
            xs = xml_content.find('<?xml')
            xe = xml_content.rfind('</nfeProc>')
            if xe < 0:
                xe = xml_content.rfind('</NFe>')
            if xe > 0:
                xe += len('</nfeProc>') if '</nfeProc>' in xml_content[xs:] else len('</NFe>')
                xml_content = xml_content[xs:xe]
            else:
                xml_content = xml_content[xs:]
            logger.info(f'XML limpo: {len(xml_content)} chars')

        logger.info(f'XML final size: {len(xml_content)} chars')

        # 6. Salvar local + Inserir no Odoo
        out_path = f'/tmp/sefaz_debug/preview_xml_inv{INVOICE_ID}.xml'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        logger.info(f'XML salvo em {out_path}')

        browser.close()

        # 7. Re-conectar Odoo e inserir XML
        with app.app_context():
            odoo = get_odoo_connection()
            # base64
            xml_bytes = xml_content.encode('utf-8')
            xml_b64 = base64.b64encode(xml_bytes).decode('utf-8')
            try:
                odoo.write('account.move', [INVOICE_ID], {
                    'l10n_br_xml_aut_nfe': xml_b64,
                })
                logger.info(f'XML inserido em l10n_br_xml_aut_nfe ({len(xml_b64)} chars b64)')
            except Exception as e:
                logger.error(f'Falha ao escrever l10n_br_xml_aut_nfe: {e}')
                # Try alternativo: l10n_br_xml_nfe
                try:
                    odoo.write('account.move', [INVOICE_ID], {
                        'l10n_br_xml_nfe': xml_b64,
                    })
                    logger.info(f'XML inserido em l10n_br_xml_nfe (campo alternativo)')
                except Exception as e2:
                    logger.error(f'Falha tambem em l10n_br_xml_nfe: {e2}')


if __name__ == '__main__':
    main()
