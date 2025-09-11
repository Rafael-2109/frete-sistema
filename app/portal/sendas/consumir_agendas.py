#!/usr/bin/env python3
"""
Módulo para consumir agendas do Portal Sendas (Trizy)
Realiza download automático da planilha de agendamentos disponíveis
"""

import os
import re
import sys
import asyncio
import logging
import subprocess
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from playwright.async_api import TimeoutError as PWTimeout, Download # noqa: E402
from app.portal.sendas.sendas_playwright import SendasPortal # noqa: E402
from app.portal.sendas.normalizar_com_libreoffice import normalizar_planilha_sendas # noqa: E402
from app.portal.sendas.fechar_modal_releases import aguardar_e_fechar_modal_releases # noqa: E402

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConsumirAgendasSendas:
    """Classe para consumir agendas do Portal Sendas"""
    
    def __init__(self, download_dir: str = None):
        """
        Inicializa o consumidor de agendas
        
        Args:
            download_dir: Diretório para salvar os downloads
        """
        # Detectar ambiente de produção (Render ou outras plataformas)
        # IMPORTANTE: os.getenv retorna string ou None, não boolean
        # No Render, a variável RENDER existe e tem valor "true"
        is_render = os.getenv('RENDER') is not None
        is_production_env = os.getenv('IS_PRODUCTION', '').lower() in ['true', '1', 'yes']
        
        # Detectar se está rodando em /opt/render (caminho específico do Render)
        is_render_path = '/opt/render' in os.getcwd()
        
        # Em produção SEMPRE usar headless=True (sem interface gráfica)
        is_production = is_render or is_production_env or is_render_path
        headless_mode = True if is_production else False
        
        if is_production:
            logger.info(f"🚀 Ambiente de PRODUÇÃO detectado - Forçando headless=True")
            logger.info(f"   RENDER={is_render}, IS_PRODUCTION={is_production_env}, PATH={is_render_path}")
            logger.info(f"   CWD={os.getcwd()}")
        else:
            logger.info(f"💻 Ambiente de desenvolvimento - headless={headless_mode}")
        
        # Inicializar portal com modo apropriado
        self.portal = SendasPortal(headless=headless_mode)
        
        # Validar credenciais ANTES de tentar qualquer operação
        if not self.portal.usuario or not self.portal.senha:
            logger.error("❌ CREDENCIAIS SENDAS NÃO CONFIGURADAS!")
            logger.error("Configure as variáveis de ambiente: SENDAS_USUARIO e SENDAS_SENHA")
            raise ValueError("Credenciais Sendas não configuradas. Configure SENDAS_USUARIO e SENDAS_SENHA.")
        
        # Configurar diretório de downloads
        if download_dir:
            self.download_dir = download_dir
        else:
            self.download_dir = os.path.join(
                os.path.dirname(__file__), 
                'downloads',
                datetime.now().strftime('%Y%m%d')
            )
        
        # Criar diretório se não existir
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Diretório de downloads: {self.download_dir}")
    
    async def click_seguro(self, elemento_ou_seletor, nome_acao: str = "clique", 
                          timeout: int = 5000, dentro_iframe: bool = False,
                          iframe_locator: str = None) -> bool:
        """
        Realiza um clique seguro, tratando automaticamente o releases-panel se aparecer
        
        Args:
            elemento_ou_seletor: Elemento Locator ou string seletor para clicar
            nome_acao: Descrição da ação para log
            timeout: Timeout em ms para aguardar elemento
            dentro_iframe: Se True, o elemento está dentro de um iframe
            iframe_locator: Seletor do iframe (se dentro_iframe=True)
            
        Returns:
            True se conseguiu clicar, False caso contrário
        """
        tentativas = 0
        max_tentativas = 3
        
        while tentativas < max_tentativas:
            try:
                tentativas += 1
                logger.debug(f"🔄 Tentativa {tentativas}/{max_tentativas} para {nome_acao}")
                
                # Determinar o elemento a clicar
                if isinstance(elemento_ou_seletor, str):
                    if dentro_iframe and iframe_locator:
                        # Elemento dentro de iframe
                        iframe = self.portal.page.frame_locator(iframe_locator)
                        elemento = iframe.locator(elemento_ou_seletor)
                    else:
                        # Elemento normal
                        elemento = self.portal.page.locator(elemento_ou_seletor)
                else:
                    # Já é um Locator
                    elemento = elemento_ou_seletor
                
                # Tentar aguardar o elemento ficar visível
                await elemento.wait_for(state="visible", timeout=timeout)
                
                # Tentar clicar
                await elemento.click()
                logger.info(f"✅ {nome_acao} realizado com sucesso")
                return True
                
            except PWTimeout as e:
                logger.warning(f"⏱️ Timeout ao tentar {nome_acao} (tentativa {tentativas}/{max_tentativas})")
                
                # Se deu timeout, verificar se há modal bloqueando
                if await self.fechar_modal_se_aparecer(timeout=2000):
                    logger.info(f"🔄 Modal fechado, tentando {nome_acao} novamente...")
                    continue  # Tentar novamente
                    
                if tentativas >= max_tentativas:
                    logger.error(f"❌ Falha ao realizar {nome_acao} após {max_tentativas} tentativas")
                    return False
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao tentar {nome_acao}: {str(e)[:100]}")
                
                # Qualquer erro, verificar se há modal bloqueando
                if await self.fechar_modal_se_aparecer(timeout=2000):
                    logger.info(f"🔄 Modal fechado, tentando {nome_acao} novamente...")
                    continue  # Tentar novamente
                    
                if tentativas >= max_tentativas:
                    logger.error(f"❌ Falha ao realizar {nome_acao}: {e}")
                    return False
                    
                # Aguardar um pouco antes de tentar novamente
                await self.portal.page.wait_for_timeout(1000)
        
        return False
    
    async def fechar_modal_se_aparecer(self, timeout: int = 3000) -> bool:
        """
        Verifica e fecha modal/pop-up se aparecer (incluindo releases-panel e widget de chat)
        
        Args:
            timeout: Tempo máximo de espera em ms
            
        Returns:
            True se modal foi fechado, False se não apareceu
        """
        try:
            logger.debug("🔍 Verificando presença de modal ou painel de releases...")
            
            # CORREÇÃO 3: Não fechar o modal de upload sem querer
            try:
                iframe_modal_count = await self.portal.page.frame_locator("#iframe-servico").locator(".rs-modal, .rs-modal-wrapper").count()
                if iframe_modal_count > 0:
                    logger.debug("📋 Modal de upload detectado no iframe - NÃO será fechado")
                    return False  # há um modal válido do fluxo aberto; não feche nada
            except Exception:
                pass
            
            # 1. Primeiro, verificar o releases-panel (notas de lançamento Trizy)
            releases_panel = self.portal.page.locator('releases-panel[opened]')
            if await releases_panel.count() > 0:
                logger.info("📋 Painel de releases/novidades detectado")
                
                try:
                    # Tentar clicar no botão de fechar dentro do Shadow DOM
                    # Usar JavaScript para acessar o shadow root e clicar no botão
                    await self.portal.page.evaluate("""
                        () => {
                            const panel = document.querySelector('releases-panel');
                            if (panel && panel.shadowRoot) {
                                const closeBtn = panel.shadowRoot.querySelector('.close-btn');
                                if (closeBtn) {
                                    closeBtn.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    logger.info("✅ Painel de releases fechado via Shadow DOM")
                    await self.portal.page.wait_for_timeout(500)
                    return True
                except Exception as e:
                    logger.debug(f"Tentando remover releases-panel diretamente: {e}")
                    # Se falhar, tentar remover o elemento completamente
                    await self.portal.page.evaluate("""
                        () => {
                            const panel = document.querySelector('releases-panel');
                            if (panel) {
                                panel.remove();
                            }
                        }
                    """)
                    return True
            
            # 2. Verificar o widget de chat Movidesk/Trizy
            widget_chat = self.portal.page.locator('#md-app-widget')
            if await widget_chat.count() > 0:
                logger.info("💬 Widget de chat Movidesk/Trizy detectado")
                
                # Tentar clicar no botão de fechar do widget
                btn_close_widget = self.portal.page.locator('.md-chat-widget-btn-close-icon')
                if await btn_close_widget.count() > 0 and await btn_close_widget.is_visible():
                    logger.info("🔘 Fechando widget de chat...")
                    await btn_close_widget.click()
                    await self.portal.page.wait_for_timeout(500)
                    return True
                
                # Se não tem botão de fechar visível, ocultar via JavaScript
                logger.info("🔧 Ocultando widget de chat via JavaScript...")
                await self.portal.page.evaluate("""
                    () => {
                        const widget = document.getElementById('md-app-widget');
                        if (widget) {
                            widget.style.display = 'none';
                            widget.style.visibility = 'hidden';
                        }
                        const wrapper = document.querySelector('.md-chat-widget-wrapper');
                        if (wrapper) {
                            wrapper.remove();
                        }
                    }
                """)
                await self.portal.page.wait_for_timeout(500)
                return True
            
            # 3. Lista de seletores possíveis para outros tipos de modal
            seletores_fechar = [
                'button[aria-label="Close"]',  # Botão com aria-label
                'button:has-text("×")',  # Botão com X
                'button:has-text("X")',  # Botão com X maiúsculo
                '.close-button',  # Classe comum
                '[class*="close"]:not(.md-chat-widget-btn-close-icon)',  # Qualquer classe com "close"
                '[class*="modal"] button[class*="close"]',  # Botão close dentro de modal
            ]
            
            # Tentar cada seletor
            for seletor in seletores_fechar:
                try:
                    elemento = self.portal.page.locator(seletor).first
                    
                    if await elemento.is_visible(timeout=1000):  # Timeout menor para cada tentativa
                        logger.info(f"✅ Modal detectado! Fechando com seletor: {seletor}")
                        await elemento.click()
                        await self.portal.page.wait_for_timeout(500)
                        return True
                        
                except Exception:
                    continue  # Tentar próximo seletor
            
            logger.debug("ℹ️ Nenhum modal detectado")
            return False
            
        except Exception as e:
            logger.debug(f"ℹ️ Erro ao verificar modal: {e}")
            return False
    
    async def navegar_para_gestao_pedidos(self) -> bool:
        """
        Navega até a área de Gestão de Pedidos
        
        Returns:
            True se navegação bem-sucedida
        """
        try:
            logger.info("🔄 Navegando para Gestão de Pedidos...")
            
            # Ir para o painel principal
            await self.portal.page.goto("https://plataforma.trizy.com.br/#/terminal/painel")
            await self.portal.page.wait_for_timeout(2000)
            
            # Clicar no Menu usando click_seguro
            logger.info("📋 Clicando em Menu...")
            menu_elemento = self.portal.page.get_by_label("Menu")
            if not await self.click_seguro(menu_elemento, "Clique em Menu"):
                logger.error("❌ Não foi possível clicar em Menu")
                return False
            
            await self.portal.page.wait_for_timeout(3000)
            
            # Clicar em Gestão de Pedidos usando click_seguro
            logger.info("📦 Acessando Gestão de Pedidos...")
            btn_gestao = self.portal.page.get_by_role("button", name="Gestão de Pedidos")
            if not await self.click_seguro(btn_gestao, "Clique em Gestão de Pedidos"):
                logger.error("❌ Não foi possível acessar Gestão de Pedidos")
                return False
            
            # Usar estratégia otimizada para fechar modal de releases
            await aguardar_e_fechar_modal_releases(self.portal.page, "após Gestão de Pedidos")
            
            # Aguardar iframe estabilizar (tempo reduzido pois modal já foi tratado)
            await self.portal.page.wait_for_timeout(500)
            
            # Verificar se iframe existe
            iframe = self.portal.page.frame_locator("#iframe-servico")
            if not iframe:
                logger.error("❌ iFrame de serviço não encontrado")
                return False
            
            logger.info("✅ Navegação para Gestão de Pedidos concluída")
            return True
            
        except PWTimeout as e:
            logger.error(f"⏱️ Timeout ao navegar: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao navegar: {e}")
            return False
    
    async def fazer_upload_planilha(self, arquivo_planilha: str) -> bool:
        """
        Faz upload da planilha preenchida no portal Sendas
        
        Args:
            arquivo_planilha: Caminho completo do arquivo Excel a ser enviado
            
        Returns:
            True se upload bem-sucedido, False caso contrário
        """
        try:
            logger.info(f"📤 Iniciando upload da planilha: {arquivo_planilha}")
            
            # Verificar se o arquivo existe
            if not os.path.exists(arquivo_planilha):
                logger.error(f"❌ Arquivo não encontrado: {arquivo_planilha}")
                return False
            
            # VALIDAÇÃO 1: Verificar extensão do arquivo
            if not arquivo_planilha.lower().endswith('.xlsx'):
                logger.error(f"❌ Arquivo deve ser .xlsx, encontrado: {arquivo_planilha}")
                return False
            
            # VALIDAÇÃO 2: Verificar tamanho do arquivo (máx 10MB)
            file_size = os.path.getsize(arquivo_planilha)
            max_size = 10 * 1024 * 1024  # 10MB em bytes
            if file_size > max_size:
                logger.error(f"❌ Arquivo muito grande: {file_size/1024/1024:.2f}MB (máximo: 10MB)")
                return False
            
            logger.info(f"✅ Arquivo válido: .xlsx, {file_size/1024/1024:.2f}MB")
            
            # NORMALIZAÇÃO: Corrigir formato Excel para evitar erro 500
            logger.info("🔧 Normalizando arquivo Excel para compatibilidade com o portal...")
            logger.info("   (Isso evita o erro 500 causado por formatação incompatível)")
            
            # LOG DETALHADO DO ARQUIVO ORIGINAL
            logger.info(f"🔍 Análise do arquivo original:")
            logger.info(f"   Nome: {os.path.basename(arquivo_planilha)}")
            logger.info(f"   Tamanho: {file_size/1024:.1f} KB")
            logger.info(f"   Caminho: {arquivo_planilha}")
            
            # Criar arquivo temporário para a versão normalizada
            import tempfile
            fd, arquivo_normalizado = tempfile.mkstemp(suffix='_normalizado.xlsx', dir='/tmp')
            os.close(fd)
            
            # SOLUÇÃO DEFINITIVA: Abrir e salvar com LibreOffice (converte para sharedStrings)
            logger.info("🎯 SOLUÇÃO DEFINITIVA: Normalizando com LibreOffice")
            logger.info("   (Simula abrir/salvar do Excel - converte para sharedStrings!)")
            sucesso_norm, arquivo_para_upload = normalizar_planilha_sendas(
                arquivo_planilha, 
                arquivo_normalizado
            )
            
            if sucesso_norm:
                logger.info("✅ Arquivo normalizado com sucesso")
                logger.info(f"   Arquivo normalizado: {os.path.basename(arquivo_para_upload)}")
                logger.info(f"   Caminho completo: {arquivo_para_upload}")
                
                # Comparar tamanhos
                novo_tamanho = os.path.getsize(arquivo_para_upload)
                logger.info(f"   Tamanho após normalização: {novo_tamanho/1024:.1f} KB")
                logger.info(f"   Diferença: {(novo_tamanho - file_size)/1024:.1f} KB")
                
                # Log de sucesso da normalização
                logger.info("✅ Arquivo preparado com estrutura compatível com Sendas")
                
                # Usar arquivo normalizado para upload
                logger.info("🔄 USANDO ARQUIVO NORMALIZADO PARA UPLOAD")
                arquivo_planilha = arquivo_para_upload
            else:
                logger.error("❌ Normalização falhou!")
                logger.warning("🔴 USANDO ARQUIVO ORIGINAL (pode dar erro 500)")
                logger.warning("   SUGESTÃO: Abra e salve o arquivo no Excel antes do upload")
                logger.warning(f"   Arquivo problemático: {arquivo_planilha}")
            
            # Usar estratégia otimizada para fechar modal antes do upload
            await aguardar_e_fechar_modal_releases(self.portal.page, "antes do upload")
            
            # Aguardar estabilização mínima
            await self.portal.page.wait_for_timeout(500)
            
            # CRÍTICO: Obter token JWT e enviar via postMessage para o iframe
            logger.info("🔑 Obtendo token JWT para autenticação...")
            jwt_token = None
            
            try:
                # Primeiro tentar obter de cookies (mais confiável)
                cookies = await self.portal.page.context.cookies()
                for cookie in cookies:
                    if cookie.get("name") == "trizy_access_token":
                        jwt_token = cookie.get("value")
                        logger.info("✅ Token JWT obtido do cookie trizy_access_token")
                        break
                
                # Se não achou em cookies, tentar storage
                if not jwt_token:
                    jwt_token = await self.portal.page.evaluate("""
                        () => {
                            return localStorage.getItem('trizy_access_token') || 
                                   sessionStorage.getItem('trizy_access_token') ||
                                   localStorage.getItem('access_token') ||
                                   sessionStorage.getItem('access_token');
                        }
                    """)
                    if jwt_token:
                        logger.info("✅ Token JWT obtido do storage")
                
                if not jwt_token:
                    logger.warning("⚠️ Token JWT não encontrado - upload pode falhar")
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao obter token: {e}")
            
            # Enviar token via postMessage para o iframe (CRÍTICO!)
            # Enviar 2x com delay para garantir que o iframe receba
            if jwt_token:
                logger.info("📨 Enviando token JWT via postMessage para o iframe...")
                for i in range(2):
                    await self.portal.page.evaluate("""
                        (tok) => {
                            const iframe = document.querySelector('#iframe-servico');
                            if (iframe && iframe.contentWindow) {
                                iframe.contentWindow.postMessage(
                                    { token: tok, modulo_gped: 1 }, 
                                    '*'
                                );
                                console.log('Token enviado para iframe via postMessage');
                            }
                        }
                    """, jwt_token)
                    await self.portal.page.wait_for_timeout(400)
                logger.info("✅ Token enviado 2x para garantir recebimento")
            
            # (Modal já foi tratado acima com estratégia otimizada)
            
            # Trabalhar dentro do iframe
            iframe = self.portal.page.frame_locator("#iframe-servico")
            
            # IMPORTANTE: Preparar captura assíncrona da resposta ANTES de qualquer interação
            logger.info("🎯 Preparando interceptação de resposta do upload...")
            upload_response = {"hit": False, "status": None, "body": None, "ok": False}
            
            async def _capture_body(resp):
                """Captura o corpo da resposta de forma segura"""
                try:
                    return await resp.json()
                except Exception:
                    try:
                        return await resp.text()
                    except Exception:
                        return None
            
            async def on_response_async(response):
                """Processa respostas de forma assíncrona"""
                if "/empresa/demanda/consumoExcelUpload" in response.url:
                    logger.info(f"🎯 Capturado upload para: {response.url}")
                    upload_response["hit"] = True
                    upload_response["status"] = response.status
                    upload_response["body"] = await _capture_body(response)
                    
                    # Considerar sucesso apenas se JSON tiver statusCode 200
                    try:
                        if isinstance(upload_response["body"], dict) and upload_response["body"].get("statusCode") == 200:
                            upload_response["ok"] = True
                            logger.info("✅ Upload confirmado pela API (statusCode: 200)")
                    except Exception:
                        pass
                    
                    # Log detalhado da resposta
                    logger.info(f"🛰️ Upload HTTP status: {upload_response['status']}")
                    logger.info(f"🧾 Corpo da resposta: {str(upload_response['body'])[:500]}")
            
            # Função wrapper para o listener
            def response_handler(r):
                asyncio.create_task(on_response_async(r))
            
            # Adicionar listener assíncrono ANTES de abrir o menu
            self.portal.page.on("response", response_handler)
            
            # Primeiro precisamos acessar o menu AÇÕES novamente
            logger.info("🔘 Clicando em AÇÕES para acessar opções de upload...")
            btn_acoes = iframe.get_by_role("button", name="AÇÕES")
            if await self.click_seguro(btn_acoes, "Clique em AÇÕES"):
                await self.portal.page.wait_for_timeout(1000)
                
                # Agora procurar por CONSUMIR ITENS
                logger.info("📋 Selecionando CONSUMIR ITENS...")
                item_consumir = iframe.get_by_role("menuitem", name="CONSUMIR ITENS")
                if await self.click_seguro(item_consumir, "Clique em CONSUMIR ITENS"):
                    await self.portal.page.wait_for_timeout(1500)
                    
                    # Agora sim procurar o botão de upload
                    logger.info("🔍 Procurando botão de Upload da planilha...")
                    
                    # Lista de seletores possíveis para o botão de upload
                    upload_selectors = [
                        'button:has-text("Upload da planilha")',
                        'button:has-text("UPLOAD PLANILHA")',
                        'button:has-text("Upload")',
                        'button:has-text("Enviar planilha")',
                        'button:has-text("Carregar planilha")',
                        '.upload-button',
                        'button[title*="upload" i]',
                        'button:has(svg[width="16"][height="16"])',
                        'button:has([data-icon="upload"])'
                    ]
                    
                    botao_upload = None
                    for selector in upload_selectors:
                        temp_button = iframe.locator(selector).first
                        if await temp_button.is_visible(timeout=1000):
                            botao_upload = temp_button
                            logger.info(f"✅ Botão encontrado com seletor: {selector}")
                            break
            
                    if botao_upload:
                        logger.info("✅ Botão de upload encontrado")
                        
                        # Clicar no botão para abrir o modal
                        await botao_upload.click()
                        logger.info("🖱️ Botão de upload clicado, aguardando modal...")
                        
                        # Aguardar o modal aparecer
                        await self.portal.page.wait_for_timeout(2000)
                        
                        # CORREÇÃO CRÍTICA: Procurar o modal DENTRO DO IFRAME, não no page!
                        logger.info("🔍 Procurando modal de upload DENTRO DO IFRAME...")
                        
                        # O modal está no iframe, não no page principal
                        modal_selectors = [
                            '[role="dialog"].rs-modal',
                            '.rs-modal-wrapper',
                            '.rs-modal'
                        ]
                        
                        modal = None
                        for selector in modal_selectors:
                            temp_modal = iframe.locator(selector).first
                            if await temp_modal.is_visible(timeout=1000):
                                logger.info(f"🎆 Modal de upload encontrado no IFRAME: {selector}")
                                modal = temp_modal
                                break
                        
                        if modal:
                            logger.info("🔍 Localizando o DevExtreme FileUploader DENTRO do modal...")
                            
                            # IMPORTANTE: Capturar a resposta do endpoint de upload
                            logger.info("🎯 Preparando para interceptar resposta do endpoint de upload...")
                            
                            # Helpers
                            async def esta_visivel(loc, timeout=1200) -> bool:
                                try:
                                    await loc.wait_for(state="visible", timeout=timeout)
                                    return True
                                except Exception:
                                    return False

                            async def aguardar_devextreme_reconhecer(uploader_root, timeout_ms=8000) -> bool:
                                """Espera o DevExtreme remover 'dx-fileuploader-empty' e/ou mostrar item na lista."""
                                loop = asyncio.get_running_loop()
                                deadline = loop.time() + (timeout_ms / 1000.0)
                                files_item = modal.locator('.dx-fileuploader-files-container .dx-fileuploader-file').first
                                while loop.time() < deadline:
                                    try:
                                        classes = await uploader_root.get_attribute("class")
                                        if classes and "dx-fileuploader-empty" not in classes:
                                            # se houver card de arquivo melhor ainda
                                            if await esta_visivel(files_item, 300):
                                                return True
                                            return True
                                    except Exception:
                                        pass
                                    await self.portal.page.wait_for_timeout(200)
                                return False

                            # ESCOPAR NO MODAL: pega o root do uploader DENTRO do modal
                            uploader_root = modal.locator('#file-uploader, [id^="file-uploader"]').first
                            if await uploader_root.count() == 0 or not await esta_visivel(uploader_root, 1500):
                                logger.warning("⚠️ Root do FileUploader não encontrado no modal. Tentando só pelos inputs.")
                                uploader_root = modal  # degrade: vamos validar por toasts/erros

                            # IMPORTANTE: Verificar se o input tem o nome correto "arquivoExcel"
                            # Pegue TODOS os inputs file DENTRO do modal
                            inputs = await modal.locator('input[type="file"]').all()
                            if not inputs:
                                logger.error("❌ Nenhum input[type=file] encontrado DENTRO do modal.")
                                try:
                                    html_dump = await modal.inner_html()
                                    dump_path = f"/tmp/sendas_modal_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                                    with open(dump_path, "w", encoding="utf-8") as f:
                                        f.write(html_dump or "")
                                    logger.info(f"📝 Dump do HTML do modal salvo em: {dump_path}")
                                except Exception:
                                    pass
                                return False

                            logger.info(f"📁 {len(inputs)} input(s) de arquivo encontrados no modal.")
                            
                            # Verificar e setar o atributo name para "arquivoExcel" se necessário
                            for idx, file_input in enumerate(inputs):
                                try:
                                    # Obter o nome atual do campo
                                    current_name = await file_input.get_attribute("name")
                                    logger.info(f"📝 Input[{idx}] tem name='{current_name}'")
                                    
                                    # Se não for "arquivoExcel", precisamos setar
                                    if current_name != "arquivoExcel":
                                        logger.warning(f"⚠️ Nome do campo incorreto: '{current_name}'. Corrigindo para 'arquivoExcel'...")
                                        await file_input.evaluate("""
                                            (el) => {
                                                el.setAttribute('name', 'arquivoExcel');
                                                console.log('Campo name alterado para arquivoExcel');
                                            }
                                        """)
                                except Exception as e:
                                    logger.debug(f"Erro ao verificar/setar name do input[{idx}]: {e}")

                            # O listener já foi adicionado antes de abrir o menu AÇÕES
                            # Agora apenas referenciamos a variável upload_response que já existe
                            
                            reconhecido = False
                            for idx, file_input in enumerate(inputs):
                                try:
                                    # set_input_files funciona mesmo com input invisível
                                    logger.info(f"📤 Tentando set_input_files no input[{idx}] com campo name='arquivoExcel'...")
                                    await file_input.set_input_files(arquivo_planilha)
                                    # Força o 'change' a borbulhar
                                    try:
                                        await file_input.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                                    except Exception:
                                        pass

                                    # Valida se o FileUploader saiu de 'empty' (se temos uploader_root)
                                    if await aguardar_devextreme_reconhecer(uploader_root, timeout_ms=9000):
                                        reconhecido = True
                                        logger.info("✅ DevExtreme reconheceu o arquivo (saiu de 'dx-fileuploader-empty').")
                                        break
                                    else:
                                        logger.warning(f"⚠️ Input[{idx}] não populou o uploader.")
                                except Exception as e:
                                    logger.warning(f"⚠️ Falha ao usar input[{idx}]: {e}")

                            # Fallback: usar botão "Selecionar arquivo" do DevExtreme, ainda escopado ao modal
                            if not reconhecido:
                                select_btn = modal.locator('.dx-fileuploader-button[role="button"]').first
                                if await select_btn.count() > 0 and await esta_visivel(select_btn, 1500):
                                    logger.info("🔄 Fallback: acionando file chooser do DevExtreme (no modal)...")
                                    try:
                                        async with self.portal.page.expect_file_chooser(timeout=6000) as fc_info:
                                            await select_btn.click()
                                        fc = await fc_info.value
                                        await fc.set_files(arquivo_planilha)
                                        if not await aguardar_devextreme_reconhecer(uploader_root, timeout_ms=9000):
                                            logger.error("❌ Mesmo com file chooser, o DevExtreme não populou (no modal).")
                                            return False
                                        reconhecido = True
                                    except PWTimeout:
                                        logger.error("⏱️ Timeout ao abrir file chooser do DevExtreme (no modal).")
                                        return False
                                    except Exception as e:
                                        logger.error(f"❌ Erro no fallback de file chooser (no modal): {e}")
                                        return False

                            if not reconhecido:
                                logger.error("❌ Nenhuma tentativa populou o uploader no modal.")
                                return False

                            # Se existir botão de upload, clique; caso contrário, ele é instant-upload
                            upload_btn = modal.locator('.dx-fileuploader-upload-button').first
                            if await upload_btn.count() > 0 and await esta_visivel(upload_btn, 1500):
                                logger.info("🖱️ Clicando no botão de upload do DevExtreme (no modal)…")
                                await upload_btn.click()
                            else:
                                logger.info("ℹ️ Sem botão de upload — assumindo 'instant upload'.")

                            # Aguardar resposta do servidor (máximo 30 segundos)
                            logger.info("⏳ Aguardando resposta do servidor após upload...")
                            for _ in range(60):  # 30 segundos (60 x 500ms)
                                if upload_response["hit"]:
                                    break
                                await self.portal.page.wait_for_timeout(500)
                            
                            # Remover listener após upload
                            self.portal.page.remove_listener("response", response_handler)
                            
                            # Verificar resposta do servidor
                            if upload_response["hit"]:
                                if upload_response["ok"]:
                                    logger.info("✅ Upload confirmado pela API com sucesso")
                                    logger.info(f"   📊 Status HTTP: {upload_response['status']}")
                                    if isinstance(upload_response["body"], dict):
                                        if 'demandaId' in upload_response["body"]:
                                            logger.info(f"   🆔 ID da Demanda: {upload_response['body']['demandaId']}")
                                        if 'quantidade' in upload_response["body"]:
                                            logger.info(f"   📦 Quantidade processada: {upload_response['body']['quantidade']}")
                                else:
                                    logger.error("❌ Upload rejeitado pela API")
                                    logger.error(f"   📊 Status HTTP: {upload_response['status']}")
                                    # Tentar obter mensagem de erro
                                    if upload_response["body"]:
                                        if isinstance(upload_response["body"], dict):
                                            logger.error(f"   📨 Mensagem: {upload_response['body'].get('message', 'Sem mensagem')}")
                                            logger.error(f"   🔢 StatusCode: {upload_response['body'].get('statusCode', 'N/A')}")
                                            if 'errors' in upload_response["body"]:
                                                logger.error(f"   ⛔ Erros: {upload_response['body']['errors']}")
                                        else:
                                            logger.error(f"   📄 Resposta: {upload_response['body'][:500]}")
                                    # Tentar capturar screenshot do erro
                                    try:
                                        error_path = f"/tmp/sendas_erro_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                        await self.portal.page.screenshot(path=error_path)
                                        logger.info(f"   📸 Screenshot do erro salvo em: {error_path}")
                                    except Exception:
                                        pass
                                    return False
                            else:
                                logger.warning("⚠️ Nenhuma resposta do endpoint de upload foi capturada")
                                logger.warning("   Possíveis causas:")
                                logger.warning("   - O endpoint pode estar em outro domínio")
                                logger.warning("   - O upload pode não ter sido disparado") 
                                logger.warning("   - Token JWT pode estar inválido")
                                logger.warning("   - Arquivo pode estar no formato incorreto")
                                
                                # Fallback: verificar toasts de erro na interface
                                erro = False
                                for _ in range(10):  # 5s
                                    # Erro explícito em toasts/alertas
                                    for sel_err in ['.rs-notification-item-error', '.rs-message-error', '.alert-danger', '.error-message']:
                                        loc_err = modal.locator(sel_err).first
                                        if await esta_visivel(loc_err, 300):
                                            erro = True
                                            break
                                    if not erro:
                                        try:
                                            loc_err_text = modal.get_by_text(re.compile(r'erro|falha|inválid|tamanho|formato', re.I))
                                            if await esta_visivel(loc_err_text, 300):
                                                erro = True
                                        except Exception:
                                            pass
                                    if erro:
                                        break
                                    await self.portal.page.wait_for_timeout(500)

                                if erro:
                                    logger.error("❌ Portal exibiu erro após upload (no modal).")
                                    return False

                            # Não espere o modal sumir sozinho; feche pela cruz
                            close_btn = modal.locator('.rs-modal-header .rs-modal-header-close.rs-btn-close').first
                            if await close_btn.count() > 0 and await esta_visivel(close_btn, 1500):
                                logger.info("🧹 Fechando modal pelo botão de fechar…")
                                await close_btn.click()
                                await self.portal.page.wait_for_timeout(600)
                            else:
                                logger.info("ℹ️ Botão de fechar do modal não visível; seguindo.")

                            # Segurança extra: verificador de erro geral
                            if await self._verificar_erro_servidor(iframe):
                                logger.error("❌ Erro detectado após upload.")
                                return False

                            # Confirmar demanda (se existir)
                            logger.info("🔍 Procurando botão CONFIRMAR DEMANDA…")
                            confirm_success = await self.confirmar_demanda(iframe)
                            if confirm_success:
                                logger.info("✅ Upload + confirmação concluídos.")
                                return True
                            else:
                                logger.warning("⚠️ Upload OK, mas sem confirmação. Considerando sucesso do upload.")
                                return True


                        else:
                            logger.warning("⚠️ Modal de upload não apareceu após clicar no botão")
                
                        # Já retornou True no bloco acima se conseguiu fazer upload
                        logger.warning("⚠️ Não conseguiu fazer upload pelo modal")
                    
                    else:
                        logger.warning("⚠️ Botão de upload não encontrado após abrir menu AÇÕES")
                else:
                    logger.warning("⚠️ Não foi possível clicar em CONSUMIR ITENS")
                
            # Se não conseguiu pelo menu, tentar método alternativo
            logger.info("⚠️ Tentando método alternativo de upload...")
            
            # IMPORTANTE: Injetar token no iframe antes de qualquer upload
            if jwt_token:
                logger.info("🔑 Reinjetando token no contexto do iframe...")
                try:
                    await iframe.evaluate(f"""
                        () => {{
                            // Setar token no localStorage e sessionStorage do iframe
                            localStorage.setItem('trizy_access_token', '{jwt_token}');
                            sessionStorage.setItem('trizy_access_token', '{jwt_token}');
                            
                            // Também setar em window para garantir
                            window.trizy_token = '{jwt_token}';
                            
                            console.log('Token injetado no iframe');
                        }}
                    """)
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao injetar token no iframe: {e}")
            
            # Procurar área de dropzone
            dropzone = iframe.locator('#dropzone-external')
            if not await dropzone.is_visible(timeout=3000):
                dropzone = iframe.locator('[id*="dropzone"]')
            
            if await dropzone.is_visible():
                logger.info("📦 Área de dropzone encontrada")
                
                # Usar o input file diretamente se existir
                file_input = iframe.locator('input[type="file"]')
                if await file_input.count() > 0:
                    # Verificar se o arquivo existe antes de enviar
                    if not os.path.exists(arquivo_planilha):
                        logger.error(f"❌ Arquivo não encontrado: {arquivo_planilha}")
                        return False
                    
                    logger.info(f"📁 Enviando arquivo: {arquivo_planilha}")
                    logger.info(f"📁 Tamanho do arquivo: {os.path.getsize(arquivo_planilha)} bytes")
                    
                    try:
                        await file_input.set_input_files(arquivo_planilha)
                        logger.info("✅ Arquivo enviado via input direto")
                    except Exception as upload_error:
                        logger.error(f"❌ Erro ao enviar arquivo: {upload_error}")
                        return False
                    
                    # Aguardar processamento
                    await self.portal.page.wait_for_timeout(3000)
                    
                    # Confirmar demanda após upload
                    logger.info("🔍 Procurando botão CONFIRMAR DEMANDA...")
                    confirm_success = await self.confirmar_demanda(iframe)
                    
                    if confirm_success:
                        logger.info("✅ Upload e confirmação concluídos com sucesso")
                    else:
                        logger.warning("⚠️ Upload realizado mas confirmação pode ter falhado")
                    
                    return True
                else:
                    # Verificar arquivo antes de tentar dropzone
                    if not os.path.exists(arquivo_planilha):
                        logger.error(f"❌ Arquivo não encontrado para dropzone: {arquivo_planilha}")
                        return False
                    
                    logger.info(f"📁 Tentando enviar via dropzone: {arquivo_planilha}")
                    
                    # Clicar na área de dropzone para abrir seletor
                    try:
                        logger.info("⏳ Preparando para clicar no dropzone...")
                        async with self.portal.page.expect_file_chooser(timeout=10000) as fc_info:
                            await dropzone.click()
                            logger.info("🖱️ Dropzone clicado, aguardando file chooser...")
                        
                        logger.info("📂 File chooser apareceu")
                        file_chooser = await fc_info.value
                        
                        logger.info(f"📤 Enviando arquivo: {arquivo_planilha}")
                        await file_chooser.set_files(arquivo_planilha)
                        logger.info("✅ Arquivo enviado via dropzone")
                        
                    except TimeoutError as te:
                        logger.error(f"⏱️ Timeout esperando file chooser: {te}")
                        # Tentar clicar diretamente no input se existir
                        logger.info("🔄 Tentando input direto como fallback...")
                        try:
                            file_input = iframe.locator('input[type="file"]')
                            if await file_input.count() > 0:
                                await file_input.set_input_files(arquivo_planilha)
                                logger.info("✅ Arquivo enviado via input direto (fallback)")
                                await self.portal.page.wait_for_timeout(3000)
                                
                                # Confirmar demanda após upload
                                logger.info("🔍 Procurando botão CONFIRMAR DEMANDA...")
                                confirm_success = await self.confirmar_demanda(iframe)
                                
                                if confirm_success:
                                    logger.info("✅ Upload e confirmação concluídos com sucesso")
                                else:
                                    logger.warning("⚠️ Upload realizado mas confirmação pode ter falhado")
                                
                                return True
                        except Exception as fallback_error:
                            logger.error(f"❌ Fallback também falhou: {fallback_error}")
                        return False
                    except Exception as dropzone_error:
                        logger.error(f"❌ Erro ao enviar via dropzone: {dropzone_error}")
                        logger.error(f"❌ Tipo do erro: {type(dropzone_error).__name__}")
                        logger.error(f"❌ Stack trace:\n{traceback.format_exc()}")
                        return False
                    
                    # Aguardar processamento
                    await self.portal.page.wait_for_timeout(3000)
                    
                    # Confirmar demanda após upload
                    logger.info("🔍 Procurando botão CONFIRMAR DEMANDA...")
                    confirm_success = await self.confirmar_demanda(iframe)
                    
                    if confirm_success:
                        logger.info("✅ Upload e confirmação concluídos com sucesso")
                    else:
                        logger.warning("⚠️ Upload realizado mas confirmação pode ter falhado")
                    
                    logger.info("="*60)
                    logger.info("✅ UPLOAD CONCLUÍDO COM SUCESSO!")
                    logger.info(f"📁 Arquivo: {os.path.basename(arquivo_planilha)}")
                    logger.info("="*60)
                    return True
            else:
                logger.error("❌ Não foi possível encontrar área de upload")
                # Tentar capturar screenshot para debug
                screenshot_path = f"/tmp/sendas_erro_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.portal.page.screenshot(path=screenshot_path)
                logger.info(f"📸 Screenshot salvo em: {screenshot_path}")
                return False
                    
        except PWTimeout as e:
            logger.error(f"⏱️ Timeout durante upload: {e}")
            logger.error("   Tente aumentar o timeout ou verificar a conexão")
            return False
        except Exception as e:
            logger.error(f"❌ Erro durante upload: {e}")
            logger.error("   Verifique se o arquivo está no formato correto")
            logger.error("   Certifique-se que o portal está acessível")
            traceback.print_exc()
            return False
    
    async def _verificar_erro_servidor(self, iframe=None) -> bool:
        """
        Verifica se apareceu erro do servidor na página ou iframe
        
        Args:
            iframe: Frame locator opcional. Se fornecido, prioriza busca no iframe
        
        Returns:
            True se detectou erro, False caso contrário
        """
        # CORREÇÃO 2: Verificador de erro ciente do iframe
        seletores = [
            'text="Internal Server Error"',
            'text="500"', 
            'text=/Erro (no servidor|interno)/i',
            '.alert-danger',
            '.error-message',
            '.rs-message-error',
            '.rs-notification-item-error'
        ]
        
        contexts = []
        if iframe:
            contexts.append(iframe)
        contexts.append(self.portal.page)
        
        for ctx in contexts:
            for s in seletores:
                try:
                    if await ctx.locator(s).is_visible(timeout=1000):
                        context_name = "iframe" if ctx != self.portal.page else "page"
                        logger.error(f"❌ ERRO DO SERVIDOR DETECTADO no {context_name}: {s}")
                        logger.error(f"❌ Portal Sendas retornou erro ao processar o upload (contexto: {context_name})")
                        
                        # Capturar screenshot para debug
                        try:
                            screenshot_path = f"/tmp/sendas_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            await self.portal.page.screenshot(path=screenshot_path, full_page=True)
                            logger.info(f"📸 Screenshot do erro salvo em: {screenshot_path}")
                            
                            # Capturar URL atual para debug
                            current_url = self.portal.page.url
                            logger.info(f"📍 URL quando erro ocorreu: {current_url}")
                            
                            # Informação adicional sobre o contexto
                            logger.error(f"💡 Erro encontrado no contexto: {context_name}")
                            if context_name == "iframe":
                                logger.error("💡 Isso confirma que o modal/erro está no iframe, não no page principal")
                            
                        except Exception as e:
                            logger.debug(f"Erro ao capturar detalhes: {e}")
                        
                        return True
                except Exception:
                    pass
        
        return False
    
    async def confirmar_demanda(self, iframe) -> bool:
        """
        Clica no botão CONFIRMAR DEMANDA após o upload da planilha
        
        Args:
            iframe: Frame locator do iframe onde está o botão
            
        Returns:
            True se conseguiu confirmar, False caso contrário
        """
        try:
            logger.info("🔍 Procurando botão CONFIRMAR DEMANDA...")
            
            # Aguardar um pouco para o botão aparecer após o upload
            await self.portal.page.wait_for_timeout(2000)
            
            # Fechar modal se ainda estiver aberto
            close_btn = iframe.locator('.rs-modal-header-close').first
            if await close_btn.is_visible(timeout=1000):
                logger.info("🔒 Fechando modal antes de confirmar...")
                await close_btn.click()
                await self.portal.page.wait_for_timeout(1000)
            
            # Procurar o botão CONFIRMAR DEMANDA com diferentes seletores
            confirm_selectors = [
                'button:has-text("CONFIRMAR DEMANDA")',
                'button.rs-btn-primary:has-text("CONFIRMAR DEMANDA")',
                '.rs-btn.rs-btn-primary:has-text("CONFIRMAR DEMANDA")',
                'button[type="button"]:has-text("CONFIRMAR DEMANDA")'
            ]
            
            confirmado = False
            for selector in confirm_selectors:
                btn_confirmar = iframe.locator(selector).first
                if await btn_confirmar.is_visible(timeout=2000):
                    logger.info(f"✅ Botão CONFIRMAR DEMANDA encontrado")
                    
                    # Aguardar 500ms antes de clicar (estabilização da interface)
                    await self.portal.page.wait_for_timeout(500)
                    
                    # Clicar no botão
                    await btn_confirmar.click()
                    logger.info("🖱️ Clicou em CONFIRMAR DEMANDA")
                    
                    # Aguardar processamento
                    await self.portal.page.wait_for_timeout(3000)
                    
                    # Verificar se apareceu mensagem de sucesso
                    success_msgs = [
                        '.alert-success',
                        '.rs-notification-item-success',
                        'text=/.*confirmad.*/i',
                        'text=/.*sucesso.*/i'
                    ]
                    
                    for msg_selector in success_msgs:
                        if await iframe.locator(msg_selector).is_visible(timeout=1000):
                            logger.info("✅ Confirmação realizada com sucesso!")
                            confirmado = True
                            break
                    
                    # Verificar se há mensagem de erro
                    if not confirmado:
                        error_msgs = ['.alert-danger', '.rs-notification-item-error']
                        for err_selector in error_msgs:
                            if await iframe.locator(err_selector).is_visible(timeout=1000):
                                try:
                                    msg = await iframe.locator(err_selector).text_content()
                                    logger.error(f"❌ Erro na confirmação: {msg}")
                                except Exception:
                                    logger.error("❌ Erro na confirmação detectado")
                    
                    break  # Sai do loop após processar (IGUAL ao upload_simples.py linha 248)
            
            # Verificação FORA do loop (IGUAL ao upload_simples.py linhas 250-254)
            if confirmado:
                logger.info("✅ DEMANDA CONFIRMADA COM SUCESSO!")
                return True
            else:
                # Se não encontrou o botão, pode ser que a confirmação não seja necessária
                logger.warning("⚠️ Botão CONFIRMAR DEMANDA não encontrado ou confirmação não necessária")
                logger.info("   (Upload já foi realizado com sucesso)")
                return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao confirmar demanda: {e}")
            return False
    
    async def verificar_resultado_confirmacao(self, iframe) -> None:
        """
        Verifica se apareceu alguma mensagem após confirmar a demanda
        
        Args:
            iframe: Frame locator do iframe
        """
        try:
            # Procurar por mensagens de sucesso ou erro
            success_selectors = [
                'text=/.*sucesso.*/i',
                'text=/.*confirmad.*/i',
                'text=/.*concluíd.*/i',
                '.alert-success',
                '.success-message'
            ]
            
            error_selectors = [
                'text=/.*erro.*/i',
                'text=/.*falha.*/i',
                '.alert-danger',
                '.error-message'
            ]
            
            # Verificar mensagens de sucesso
            for selector in success_selectors:
                try:
                    msg = iframe.locator(selector)
                    if await msg.is_visible(timeout=1000):
                        text = await msg.text_content()
                        logger.info(f"✅ Mensagem de sucesso: {text}")
                        return
                except Exception as e:
                    logger.debug(f"Erro ao verificar mensagem de sucesso: {e}")
                    continue
            
            # Verificar mensagens de erro
            for selector in error_selectors:
                try:
                    msg = iframe.locator(selector)
                    if await msg.is_visible(timeout=1000):
                        text = await msg.text_content()
                        logger.warning(f"⚠️ Mensagem de erro: {text}")
                        return
                except Exception as e:
                    logger.debug(f"Erro ao verificar mensagem de erro: {e}")
                    continue
                    
            logger.info("ℹ️ Nenhuma mensagem específica detectada após confirmação")
            
        except Exception as e:
            logger.debug(f"Erro ao verificar resultado: {e}")
    
    async def baixar_planilha_agendamentos(self) -> Optional[str]:
        """
        Realiza o download da planilha de agendamentos
        
        Returns:
            Caminho do arquivo baixado ou None se falhar
        """
        try:
            logger.info("📥 Iniciando download da planilha...")
            
            # Usar estratégia otimizada para fechar modal antes do download
            await aguardar_e_fechar_modal_releases(self.portal.page, "antes do download")
            
            # Acessar o iframe
            iframe = self.portal.page.frame_locator("#iframe-servico")
            
            # Clicar em AÇÕES usando click_seguro
            logger.info("🔘 Clicando em AÇÕES...")
            btn_acoes = iframe.get_by_role("button", name="AÇÕES")
            if not await self.click_seguro(btn_acoes, "Clique em AÇÕES"):
                logger.error("❌ Não foi possível clicar em AÇÕES")
                return None
            await self.portal.page.wait_for_timeout(1000)
            
            # Clicar em CONSUMIR ITENS usando click_seguro
            logger.info("📋 Selecionando CONSUMIR ITENS...")
            item_consumir = iframe.get_by_role("menuitem", name="CONSUMIR ITENS")
            if not await self.click_seguro(item_consumir, "Clique em CONSUMIR ITENS"):
                logger.error("❌ Não foi possível clicar em CONSUMIR ITENS")
                return None
            await self.portal.page.wait_for_timeout(1000)
            
            # Clicar em DOWNLOAD PLANILHA usando click_seguro
            logger.info("💾 Clicando em DOWNLOAD PLANILHA...")
            btn_download = iframe.get_by_role("button", name="DOWNLOAD PLANILHA")
            if not await self.click_seguro(btn_download, "Clique em DOWNLOAD PLANILHA"):
                logger.error("❌ Não foi possível clicar em DOWNLOAD PLANILHA")
                return None
            await self.portal.page.wait_for_timeout(1000)
            
            # Preparar para capturar o download
            logger.info("⏳ Aguardando download...")
            
            # Clicar em TODOS ITENS e capturar download
            # Este é especial pois dispara download, então fazemos manualmente
            tentativas = 0
            while tentativas < 3:
                try:
                    tentativas += 1
                    logger.info(f"📥 Tentativa {tentativas}/3 de download...")
                    
                    # Aumentar timeout em produção
                    timeout_download = 60000 if os.getenv('RENDER') else 30000
                    timeout_visibility = 10000 if os.getenv('RENDER') else 5000
                    
                    async with self.portal.page.expect_download(timeout=timeout_download) as download_info:
                        item_todos = iframe.get_by_role("menuitem", name="TODOS ITENS")
                        await item_todos.wait_for(state="visible", timeout=timeout_visibility)
                        await item_todos.click()
                    break  # Sucesso, sair do loop
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao clicar em TODOS ITENS (tentativa {tentativas}/3): {e}")
                    # Tentar fechar modal e tentar novamente
                    if await self.fechar_modal_se_aparecer(timeout=2000):
                        logger.info("🔄 Modal fechado, tentando novamente...")
                        continue
                    if tentativas >= 3:
                        logger.error("❌ Falha ao clicar em TODOS ITENS após 3 tentativas")
                        return None
            
            # Obter informações do download
            download: Download = await download_info.value
            
            # Nome do arquivo original
            nome_original = download.suggested_filename
            logger.info(f"📄 Arquivo original: {nome_original}")
            
            # Gerar nome único com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"sendas_agendamentos_{timestamp}_{nome_original}"
            caminho_completo = os.path.join(self.download_dir, nome_arquivo)
            
            # Salvar arquivo
            await download.save_as(caminho_completo)
            logger.info(f"✅ Arquivo salvo: {caminho_completo}")
            
            return caminho_completo
            
        except PWTimeout as e:
            logger.error(f"⏱️ Timeout ao baixar planilha: {e}")
            await self.portal.page.screenshot(path='erro_download_timeout.png')
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao baixar planilha: {e}")
            await self.portal.page.screenshot(path='erro_download.png')
            return None
    
    async def executar_fluxo_completo(self) -> Dict[str, Any]:
        """
        Executa o fluxo completo de download de agendamentos
        
        Returns:
            Dicionário com resultado da operação
        """
        resultado = {
            'sucesso': False,
            'arquivo': None,
            'mensagem': '',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            logger.info("=" * 60)
            logger.info("INICIANDO CONSUMO DE AGENDAS - PORTAL SENDAS")
            logger.info("=" * 60)
            
            # Iniciar navegador
            logger.info("🌐 Iniciando navegador...")
            if not await self.portal.iniciar_navegador():
                resultado['mensagem'] = "Falha ao iniciar navegador"
                return resultado
            
            # Fazer login
            logger.info("🔐 Realizando login...")
            if not await self.portal.fazer_login():
                resultado['mensagem'] = "Falha no login"
                return resultado
            
            logger.info("✅ Login realizado com sucesso!")
            
            # Script preventivo para remover releases-panel e widget de chat automaticamente
            await self.portal.page.add_init_script("""
                // Observador para remover releases-panel e widget de chat assim que aparecerem
                const observer = new MutationObserver((mutations) => {
                    // Remover releases-panel
                    const releasesPanel = document.querySelector('releases-panel');
                    if (releasesPanel) {
                        console.log('Releases panel detectado e será removido');
                        // Tentar clicar no botão de fechar primeiro
                        if (releasesPanel.shadowRoot) {
                            const closeBtn = releasesPanel.shadowRoot.querySelector('.close-btn');
                            if (closeBtn) {
                                closeBtn.click();
                                return;
                            }
                        }
                        // Se não conseguir clicar, remover o elemento
                        releasesPanel.remove();
                    }
                    
                    // Remover widget de chat Movidesk
                    const widget = document.getElementById('md-app-widget');
                    if (widget) {
                        console.log('Widget de chat detectado e será removido');
                        widget.remove();
                    }
                    const wrapper = document.querySelector('.md-chat-widget-wrapper');
                    if (wrapper) {
                        wrapper.remove();
                    }
                });
                
                // Observar mudanças no DOM
                observer.observe(document.body, { childList: true, subtree: true });
                
                // Tentar remover elementos existentes imediatamente
                setTimeout(() => {
                    const panel = document.querySelector('releases-panel');
                    if (panel && panel.shadowRoot) {
                        const closeBtn = panel.shadowRoot.querySelector('.close-btn');
                        if (closeBtn) closeBtn.click();
                    }
                }, 1000);
            """)
            
            # Navegar para Gestão de Pedidos
            if not await self.navegar_para_gestao_pedidos():
                resultado['mensagem'] = "Falha ao navegar para Gestão de Pedidos"
                return resultado
            
            # Baixar planilha
            arquivo_baixado = await self.baixar_planilha_agendamentos()
            
            if arquivo_baixado:
                resultado['sucesso'] = True
                resultado['arquivo'] = arquivo_baixado
                resultado['mensagem'] = "Download realizado com sucesso"
                
                logger.info("\n" + "=" * 60)
                logger.info("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
                logger.info(f"📁 Arquivo: {arquivo_baixado}")
                logger.info("=" * 60)
            else:
                resultado['mensagem'] = "Falha no download da planilha"
                logger.error("❌ Não foi possível baixar a planilha")
            
            return resultado
            
        except Exception as e:
            resultado['mensagem'] = f"Erro inesperado: {str(e)}"
            logger.error(f"❌ Erro no fluxo: {e}")
            return resultado
            
        finally:
            # Sempre fechar o navegador
            await self.portal.fechar()
            logger.info("🔒 Navegador fechado")
    
    async def executar_com_retry(self, max_tentativas: int = 3) -> Dict[str, Any]:
        """
        Executa o fluxo com retry em caso de falha
        
        Args:
            max_tentativas: Número máximo de tentativas
            
        Returns:
            Dicionário com resultado da operação
        """
        for tentativa in range(1, max_tentativas + 1):
            logger.info(f"\n🔄 Tentativa {tentativa} de {max_tentativas}")
            
            resultado = await self.executar_fluxo_completo()
            
            if resultado['sucesso']:
                return resultado
            
            if tentativa < max_tentativas:
                logger.warning(f"⚠️ Tentativa {tentativa} falhou. Aguardando 5 segundos...")
                await asyncio.sleep(5)
        
        logger.error(f"❌ Todas as {max_tentativas} tentativas falharam")
        return resultado
    
    def baixar_planilha_modelo(self) -> Optional[str]:
        """
        Versão síncrona para baixar a planilha modelo do portal
        Usa subprocess para isolar completamente do contexto Flask
        
        Returns:
            Caminho do arquivo baixado ou None se falhar
        """
        
        try:
            # Caminho do script subprocess
            script_path = os.path.join(
                os.path.dirname(__file__), 
                'baixar_planilha_subprocess.py'
            )
            
            # Executar em processo separado
            logger.info("🚀 Executando download em processo separado...")
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=120  # Timeout de 2 minutos
            )
            
            # Parse do resultado JSON (pegar última linha com JSON)
            if result.stdout:
                try:
                    # Procurar por JSON na saída (pode haver logs antes)
                    lines = result.stdout.strip().split('\n')
                    json_line = None
                    
                    # Procurar linha que começa com { e termina com }
                    for line in reversed(lines):
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            json_line = line
                            break
                    
                    if json_line:
                        response = json.loads(json_line)
                        if response.get('success'):
                            logger.info(f"✅ Download concluído: {response.get('arquivo')}")
                            return response.get('arquivo')
                        else:
                            logger.error(f"❌ Erro no download: {response.get('error')}")
                            return None
                    else:
                        logger.error(f"❌ Nenhum JSON encontrado na resposta do subprocess")
                        logger.debug(f"Stdout completo: {result.stdout}")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Erro ao decodificar JSON: {e}")
                    logger.debug(f"Linha JSON tentada: {json_line}")
                    return None
            else:
                logger.error(f"❌ Subprocess retornou vazio. Stderr: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout no download da planilha (120s)")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao executar subprocess: {e}")
            return None
    
    async def run_baixar_planilha(self, manter_aberto: bool = False) -> Optional[str]:
        """
        Executa o processo completo de download da planilha
        
        Args:
            manter_aberto: Se True, mantém o navegador aberto após download para reutilização
        
        Returns:
            Caminho do arquivo baixado ou None se falhar
        """
        try:
            logger.info("🚀 Iniciando run_baixar_planilha...")
            
            # Inicializar navegador
            logger.info("🌐 Etapa 1/4: Inicializando navegador...")
            sucesso_init = await self.portal.iniciar_navegador()
            if not sucesso_init:
                logger.error("❌ ERRO CRÍTICO: Falha ao inicializar navegador")
                logger.error("   Possíveis causas:")
                logger.error("   - Playwright não instalado corretamente")
                logger.error("   - Falta de recursos no servidor")
                logger.error("   - Problema com modo headless em produção")
                await self.portal.fechar()
                return None
            logger.info("✅ Navegador inicializado")
            
            # Login
            logger.info("🔐 Etapa 2/4: Realizando login...")
            if not await self.portal.fazer_login():
                logger.error("❌ ERRO CRÍTICO: Falha no login")
                logger.error("   Possíveis causas:")
                logger.error("   - Credenciais incorretas")
                logger.error("   - Portal Sendas fora do ar")
                logger.error("   - Mudança na interface do portal")
                await self.portal.fechar()
                return None
            logger.info("✅ Login realizado")
            
            # Navegar para gestão de pedidos
            logger.info("📦 Etapa 3/4: Navegando para Gestão de Pedidos...")
            if not await self.navegar_para_gestao_pedidos():
                logger.error("❌ ERRO CRÍTICO: Falha ao navegar para gestão de pedidos")
                logger.error("   Possíveis causas:")
                logger.error("   - Mudança no menu do portal")
                logger.error("   - Modal bloqueando navegação")
                logger.error("   - Timeout na navegação")
                await self.portal.fechar()
                return None
            logger.info("✅ Navegação concluída")
            
            # Baixar planilha
            logger.info("📥 Etapa 4/4: Baixando planilha...")
            arquivo = await self.baixar_planilha_agendamentos()
            
            if arquivo:
                logger.info(f"✅ Download concluído com sucesso: {arquivo}")
            else:
                logger.error("❌ ERRO: baixar_planilha_agendamentos retornou None")
                logger.error("   Possíveis causas:")
                logger.error("   - Botões do menu mudaram")
                logger.error("   - Download não foi disparado")
                logger.error("   - Timeout esperando download")
            
            # Fechar navegador apenas se não for manter aberto
            if not manter_aberto:
                await self.portal.fechar()
                logger.info("🔒 Navegador fechado")
            else:
                logger.info("🔓 Navegador mantido aberto para reutilização")
            
            return arquivo
            
        except Exception as e:
            logger.error(f"❌ ERRO EXCEÇÃO em run_baixar_planilha: {e}")
            logger.error(f"   Tipo: {type(e).__name__}")
            logger.error(f"   Stack trace:\n{traceback.format_exc()}")
            
            # Tentar fechar navegador se ainda estiver aberto (apenas se não for manter aberto)
            if not manter_aberto:
                try:
                    await self.portal.fechar()
                except:
                    pass
                
            return None
    
    def fazer_upload_planilha_sync(self, arquivo_planilha: str) -> bool:
        """
        Versão síncrona do fazer_upload_planilha para uso em endpoints Flask
        Usa subprocess para isolar completamente do contexto Flask
        
        Args:
            arquivo_planilha: Caminho completo do arquivo Excel
            
        Returns:
            True se upload bem-sucedido
        """
        
        try:
            # Caminho do script subprocess
            script_path = os.path.join(
                os.path.dirname(__file__), 
                'upload_planilha_subprocess.py'
            )
            
            # Executar em processo separado
            logger.info(f"🚀 Executando upload em processo separado: {arquivo_planilha}")
            result = subprocess.run(
                [sys.executable, script_path, arquivo_planilha],
                capture_output=True,
                text=True,
                timeout=120  # Timeout de 2 minutos
            )
            
            # Parse do resultado JSON (pegar última linha com JSON)
            if result.stdout:
                try:
                    # Procurar por JSON na saída (pode haver logs antes)
                    lines = result.stdout.strip().split('\n')
                    json_line = None
                    
                    # Procurar linha que começa com { e termina com }
                    for line in reversed(lines):
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            json_line = line
                            break
                    
                    if json_line:
                        response = json.loads(json_line)
                        if response.get('success'):
                            logger.info("✅ Upload concluído com sucesso")
                            return True
                        else:
                            logger.error(f"❌ Erro no upload: {response.get('error')}")
                            return False
                    else:
                        logger.error(f"❌ Nenhum JSON encontrado na resposta do subprocess")
                        logger.debug(f"Stdout completo: {result.stdout}")
                        if result.stderr:
                            logger.error(f"Stderr: {result.stderr}")
                        return False
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Erro ao decodificar JSON: {e}")
                    logger.debug(f"Linha JSON tentada: {json_line}")
                    if result.stderr:
                        logger.error(f"Stderr: {result.stderr}")
                    return False
            else:
                logger.error(f"❌ Subprocess retornou vazio. Stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout no upload da planilha (120s)")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao executar subprocess: {e}")
            logger.error(f"❌ Tipo do erro: {type(e).__name__}")
            logger.error(f"❌ Stack trace: {traceback.format_exc()}")
            return False
    
    async def run_upload_planilha(self, arquivo_planilha: str) -> bool:
        """
        Executa o processo completo de upload da planilha
        
        Returns:
            True se upload bem-sucedido
        """
        try:
            logger.info("=" * 60)
            logger.info("🚀 INICIANDO PROCESSO DE UPLOAD PARA SENDAS")
            logger.info("=" * 60)
            
            # Inicializar navegador
            logger.info("🌐 Etapa 1/4: Inicializando navegador...")
            if not await self.portal.iniciar_navegador():
                logger.error("❌ ERRO CRÍTICO: Falha ao inicializar navegador")
                return False
            logger.info("✅ Navegador inicializado com sucesso")
            
            # Login
            logger.info("🔐 Etapa 2/4: Realizando login...")
            if not await self.portal.fazer_login():
                logger.error("❌ ERRO CRÍTICO: Falha no login")
                await self.portal.fechar()
                return False
            logger.info("✅ Login realizado com sucesso")
            
            # Navegar para gestão de pedidos
            logger.info("📦 Etapa 3/4: Navegando para Gestão de Pedidos...")
            if not await self.navegar_para_gestao_pedidos():
                logger.error("❌ ERRO CRÍTICO: Falha ao navegar para gestão de pedidos")
                await self.portal.fechar()
                return False
            logger.info("✅ Navegação concluída com sucesso")
            
            # Fazer upload
            logger.info("📤 Etapa 4/4: Realizando upload da planilha...")
            resultado = await self.fazer_upload_planilha(arquivo_planilha)
            
            if resultado:
                logger.info("=" * 60)
                logger.info("✅ UPLOAD CONCLUÍDO COM SUCESSO!")
                logger.info("=" * 60)
            else:
                logger.error("=" * 60)
                logger.error("❌ UPLOAD FALHOU - Verifique os logs acima")
                logger.error("=" * 60)
            
            # Fechar navegador
            await self.portal.fechar()
            logger.info("🔒 Navegador fechado")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ ERRO FATAL ao executar upload: {e}")
            logger.error(f"❌ Tipo: {type(e).__name__}")
            logger.error(f"❌ Stack trace:\n{traceback.format_exc()}")
            
            # Tentar fechar navegador se ainda estiver aberto
            try:
                await self.portal.fechar()
            except Exception:
                pass
                
            return False


def testar_upload_com_curl(arquivo_xlsx: str, jwt_token: str = None):
    """
    Testa o upload direto via curl para validar o endpoint
    
    Args:
        arquivo_xlsx: Caminho do arquivo Excel para upload
        jwt_token: Token JWT (se não fornecido, tentará obter das variáveis de ambiente)
    
    Returns:
        True se upload bem-sucedido
    """
    import subprocess
    
    logger.info("🔧 Testando upload via curl...")
    
    # Obter token se não fornecido
    if not jwt_token:
        jwt_token = os.getenv('TRIZY_ACCESS_TOKEN', '')
        if not jwt_token:
            logger.error("❌ Token JWT não fornecido e não encontrado em TRIZY_ACCESS_TOKEN")
            return False
    
    # Verificar arquivo
    if not os.path.exists(arquivo_xlsx):
        logger.error(f"❌ Arquivo não encontrado: {arquivo_xlsx}")
        return False
    
    # URL base CORRETA - MRO domain!
    base_url = os.getenv('TRIZY_API_URL', 'https://mro.trizy.com.br')
    upload_url = f"{base_url}/api/empresa/demanda/consumoExcelUpload"
    
    # Comando curl
    cmd = [
        'curl', '-X', 'POST', upload_url,
        '-H', f'Authorization: Bearer {jwt_token}',
        '-H', 'Accept: application/json',
        '-F', f'arquivoExcel=@{arquivo_xlsx};type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '-v'  # Verbose para debug
    ]
    
    logger.info(f"📡 Executando: {' '.join(cmd[:5])}...")  # Log sem o token completo
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        logger.info(f"📨 Status code: {result.returncode}")
        logger.info(f"📦 Resposta: {result.stdout[:500]}")
        
        if result.stderr:
            logger.debug(f"📝 Debug info: {result.stderr[:500]}")
        
        # Verificar sucesso
        if result.returncode == 0 and '"statusCode":200' in result.stdout:
            logger.info("✅ Upload via curl bem-sucedido!")
            return True
        else:
            logger.error("❌ Upload via curl falhou")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("⏱️ Timeout no teste com curl")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao executar curl: {e}")
        return False


async def main():
    """Função principal para teste"""
    
    # Criar consumidor
    consumidor = ConsumirAgendasSendas()
    
    # Executar com retry
    resultado = await consumidor.executar_com_retry(max_tentativas=2)
    
    # Mostrar resultado
    print("\n" + "=" * 60)
    print("RESULTADO FINAL:")
    print("=" * 60)
    print(f"Sucesso: {resultado['sucesso']}")
    print(f"Mensagem: {resultado['mensagem']}")
    if resultado['arquivo']:
        print(f"Arquivo baixado: {resultado['arquivo']}")
    print(f"Timestamp: {resultado['timestamp']}")
    print("=" * 60)
    
    return resultado


if __name__ == "__main__":
    # Executar
    asyncio.run(main())