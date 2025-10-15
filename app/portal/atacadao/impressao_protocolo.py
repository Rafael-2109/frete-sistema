"""
Serviço para geração de PDF de protocolos do Atacadão

ESTRATÉGIA: Capturar HTML do modal e criar página limpa para PDF
"""

import logging
import os
import base64
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class GeradorPDFProtocoloAtacadao:
    """Classe para gerar PDF de protocolos do Atacadão"""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Diretório temporário
        self.pdf_dir = Path("/tmp/protocolos_atacadao")
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        # Storage state
        root_storage = Path.cwd() / "storage_state_atacadao.json"
        self.storage_file = str(root_storage) if root_storage.exists() else None

    def iniciar_navegador(self):
        """Inicia navegador"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)

        if self.storage_file and os.path.exists(self.storage_file):
            logger.info(f"Carregando sessão de {self.storage_file}")
            self.context = self.browser.new_context(storage_state=self.storage_file)
        else:
            logger.warning("Sessão não encontrada")
            self.context = self.browser.new_context()

        self.page = self.context.new_page()

    def fechar_navegador(self):
        """Fecha navegador"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("🔒 Navegador fechado")
        except Exception as e:
            logger.warning(f"Erro ao fechar: {e}")

    def verificar_login(self):
        """Verifica login"""
        try:
            url_atual = self.page.url
            if "login" in url_atual.lower():
                return False
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar login: {e}")
            return False

    def gerar_pdf_protocolo(self, protocolo):
        """
        Gera PDF capturando HTML do modal e criando página limpa

        Args:
            protocolo: Número do protocolo

        Returns:
            dict com resultado
        """
        try:
            # 1. Iniciar navegador
            logger.info(f"📄 Iniciando captura do protocolo {protocolo}")
            self.iniciar_navegador()

            # 2. Verificar login
            self.page.goto("https://atacadao.hodiebooking.com.br/", timeout=15000)

            if not self.verificar_login():
                logger.error("❌ Sessão expirada")
                return {
                    'success': False,
                    'message': 'Sessão expirada. Faça login novamente.',
                    'requer_login': True
                }

            # 3. Navegar para protocolo
            url_protocolo = f"https://atacadao.hodiebooking.com.br/agendamentos/{protocolo}"
            logger.info(f"🌐 Abrindo: {url_protocolo}")

            self.page.goto(url_protocolo, timeout=30000, wait_until='networkidle')
            self.page.wait_for_timeout(2000)

            if "agendamentos" not in self.page.url:
                logger.warning(f"⚠️ Redirecionado para: {self.page.url}")
                return {
                    'success': False,
                    'message': 'Protocolo não encontrado'
                }

            # 4. Clicar em "Imprimir Senha"
            logger.info("🖱️ Clicando em 'Imprimir Senha'...")

            btn_imprimir_senha = self.page.locator('.btn_imprimir_senha').first

            if btn_imprimir_senha.count() == 0:
                logger.error("❌ Botão 'Imprimir Senha' não encontrado")
                return {
                    'success': False,
                    'message': 'Botão não encontrado'
                }

            btn_imprimir_senha.click()
            logger.info("✅ Modal aberto")

            # 5. Aguardar modal carregar COMPLETAMENTE
            logger.info("⏳ Aguardando modal...")
            self.page.wait_for_selector('#modal-imprimir-senha', state='visible', timeout=10000)
            self.page.wait_for_timeout(3000)  # Aguardar imagens, QR code, tabelas
            logger.info("✅ Modal carregado")

            # 6. CAPTURAR HTML COMPLETO do modal-body
            logger.info("📋 Capturando HTML do modal...")

            html_modal = self.page.evaluate("""
                () => {
                    const modalBody = document.querySelector('#modal-imprimir-senha .modal-body');
                    if (!modalBody) return null;

                    // Pegar HTML do modal-body
                    const modalHTML = modalBody.innerHTML;

                    // Pegar estilos inline de todos os elementos
                    const allElements = modalBody.querySelectorAll('*');
                    allElements.forEach(el => {
                        const computedStyle = window.getComputedStyle(el);
                        // Aplicar estilos computados como inline
                        el.setAttribute('style', computedStyle.cssText || '');
                    });

                    // Coletar todos os CSS externos e inline
                    const styles = Array.from(document.styleSheets)
                        .map(sheet => {
                            try {
                                return Array.from(sheet.cssRules || sheet.rules)
                                    .map(rule => rule.cssText)
                                    .join('\\n');
                            } catch (e) {
                                return '';
                            }
                        })
                        .join('\\n');

                    // Retornar HTML limpo com estilos
                    return `
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <style>
                                ${styles}

                                /* Reset para impressão limpa */
                                * {
                                    box-sizing: border-box;
                                }
                                body {
                                    margin: 0;
                                    padding: 20px;
                                    background: white;
                                    font-family: Arial, sans-serif;
                                }
                                @media print {
                                    body {
                                        margin: 0;
                                        padding: 10mm;
                                    }
                                }
                            </style>
                        </head>
                        <body>
                            ${modalBody.outerHTML}
                        </body>
                        </html>
                    `;
                }
            """)

            if not html_modal:
                logger.error("❌ Não foi possível capturar HTML do modal")
                return {
                    'success': False,
                    'message': 'Erro ao capturar conteúdo'
                }

            logger.info("✅ HTML capturado")

            # 7. Criar nova página limpa com o HTML capturado
            logger.info("📄 Criando página limpa...")
            nova_pagina = self.context.new_page()
            nova_pagina.set_content(html_modal, wait_until='networkidle')
            nova_pagina.wait_for_timeout(2000)  # Aguardar renderização completa

            # 8. Gerar PDF da página limpa
            logger.info("📸 Gerando PDF...")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"protocolo_{protocolo}_{timestamp}.pdf"
            pdf_path = self.pdf_dir / pdf_filename

            nova_pagina.pdf(
                path=str(pdf_path),
                format='A4',
                print_background=True,
                margin={
                    'top': '10mm',
                    'right': '10mm',
                    'bottom': '10mm',
                    'left': '10mm'
                }
            )

            # Fechar página temporária
            nova_pagina.close()

            logger.info(f"✅ PDF gerado: {pdf_path}")

            # Verificar
            if not pdf_path.exists():
                logger.error("❌ PDF não foi criado")
                return {
                    'success': False,
                    'message': 'Erro ao salvar PDF'
                }

            tamanho_kb = pdf_path.stat().st_size / 1024
            logger.info(f"📊 Tamanho: {tamanho_kb:.2f} KB")

            return {
                'success': True,
                'message': 'PDF gerado com sucesso!',
                'protocolo': protocolo,
                'pdf_path': str(pdf_path),
                'pdf_filename': pdf_filename,
                'pdf_size_kb': round(tamanho_kb, 2)
            }

        except PlaywrightTimeout as e:
            logger.error(f"⏱️ Timeout: {e}")
            return {
                'success': False,
                'message': 'Timeout ao processar PDF'
            }

        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'Erro: {str(e)}'
            }

        finally:
            self.fechar_navegador()

    def limpar_pdfs_antigos(self, dias=1):
        """Remove PDFs antigos"""
        try:
            import time
            agora = time.time()
            dias_em_segundos = dias * 86400

            for pdf_file in self.pdf_dir.glob("protocolo_*.pdf"):
                idade = agora - pdf_file.stat().st_mtime
                if idade > dias_em_segundos:
                    pdf_file.unlink()
                    logger.info(f"🗑️ Removido: {pdf_file.name}")

        except Exception as e:
            logger.warning(f"Erro ao limpar PDFs: {e}")


def gerar_pdf_protocolo_atacadao(protocolo):
    """Helper para geração de PDF"""
    gerador = GeradorPDFProtocoloAtacadao()
    gerador.limpar_pdfs_antigos(dias=1)
    return gerador.gerar_pdf_protocolo(protocolo)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        protocolo = sys.argv[1]
    else:
        protocolo = input("Digite o protocolo: ").strip()

    print(f"\n📄 Gerando PDF do protocolo {protocolo}...\n")

    resultado = gerar_pdf_protocolo_atacadao(protocolo)

    if resultado['success']:
        print(f"\n✅ {resultado['message']}")
        print(f"📋 Protocolo: {resultado['protocolo']}")
        print(f"📁 Arquivo: {resultado['pdf_filename']}")
        print(f"📊 Tamanho: {resultado['pdf_size_kb']} KB")
        print(f"💾 Local: {resultado['pdf_path']}\n")
    else:
        print(f"\n❌ {resultado['message']}\n")
