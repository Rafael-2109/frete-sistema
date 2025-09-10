#!/usr/bin/env python3
"""
Módulo para consumir agendas do Portal Sendas (Trizy)
Realiza download automático da planilha de agendamentos disponíveis
"""

import os
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

from playwright.async_api import TimeoutError as PWTimeout, Download
from app.portal.sendas.sendas_playwright import SendasPortal

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
            except:
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
            
            # Aguardar iframe carregar
            await self.portal.page.wait_for_timeout(2000)
            
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
            
            # Aguardar o iframe carregar
            await self.portal.page.wait_for_timeout(2000)
            
            # Verificar e fechar modal se aparecer
            if await self.fechar_modal_se_aparecer(timeout=2000):
                logger.info("✅ Modal de releases fechado antes do upload")
                await self.portal.page.wait_for_timeout(1000)
            
            # Trabalhar dentro do iframe
            iframe = self.portal.page.frame_locator("#iframe-servico")
            
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
                            # CORREÇÃO 1: Sempre usar o iframe para tudo que for modal de upload
                            logger.info("🔍 Procurando input de arquivo DENTRO DO MODAL (no iframe)...")
                            
                            # Input específico do modal com name="arquivoExcel"
                            file_input = modal.locator('input[name="arquivoExcel"]').first
                            
                            # Se não encontrar pelo name, tentar pelo type
                            if await file_input.count() == 0:
                                logger.info("⚠️ Input arquivoExcel não encontrado, tentando input[type=file]...")
                                file_input = modal.locator('input[type="file"]').first
                            
                            if await file_input.count() > 0:
                                logger.info("📁 Input file encontrado NO MODAL/IFRAME, enviando arquivo...")
                                await file_input.set_input_files(arquivo_planilha)
                                logger.info(f"📤 Arquivo setado no input do modal: {arquivo_planilha}")
                                
                                # COMPORTAMENTO CORRETO: Modal desaparece automaticamente após processar o arquivo
                                logger.info("⏳ Aguardando modal processar arquivo e desaparecer...")
                                
                                try:
                                    # Aguardar o modal desaparecer (isso indica que o upload foi processado)
                                    await modal.wait_for(state="hidden", timeout=30000)
                                    logger.info("✅ Modal desapareceu - upload foi processado!")
                                    
                                    # Aguardar um pouco para estabilizar
                                    await self.portal.page.wait_for_timeout(2000)
                                    
                                    # Verificar se apareceu erro após o modal fechar
                                    if await self._verificar_erro_servidor(iframe):
                                        logger.error("❌ Erro detectado após modal desaparecer")
                                        return False
                                    
                                    # Procurar mensagem de sucesso no iframe
                                    success_msg = iframe.locator(
                                        'text=/arquivo.*enviado|upload.*realizado|processado.*sucesso|demanda.*criada/i, '
                                        '.rs-notification-item-success, '
                                        '.rs-message-success, '
                                        '.alert-success'
                                    ).first
                                    
                                    if await success_msg.is_visible(timeout=3000):
                                        logger.info("✅ Mensagem de sucesso encontrada após upload!")
                                        
                                    # Tentar clicar em CONFIRMAR DEMANDA se existir
                                    await self.confirmar_demanda(iframe)
                                    
                                    logger.info("✅ Upload concluído com sucesso!")
                                    return True
                                    
                                except TimeoutError:
                                    logger.error("⏱️ Timeout: Modal não desapareceu após 30 segundos")
                                    
                                    # Verificar se há erro visível
                                    if await self._verificar_erro_servidor(iframe):
                                        logger.error("❌ Erro detectado no modal")
                                        return False
                                    
                                    # Tentar fechar o modal manualmente se ainda estiver aberto
                                    close_btn = modal.locator('.rs-modal-header-close, .rs-btn-close').first
                                    if await close_btn.is_visible(timeout=1000):
                                        logger.info("🔄 Tentando fechar modal manualmente...")
                                        await close_btn.click()
                                        await self.portal.page.wait_for_timeout(2000)
                                    
                                    return False
                            else:
                                # Se não encontrar input file, tentar clicar no dropzone
                                logger.info("⚠️ Input file não encontrado, tentando dropzone...")
                                
                                dropzone_selectors = [
                                    '#dropzone-external',
                                    '#dropzone',
                                    '.dropzone-container',
                                    'div:has-text("Faça upload do arquivo clicando aqui")'
                                ]
                                
                                for dz_selector in dropzone_selectors:
                                    # CORREÇÃO: Procurar dropzone no IFRAME, não no page!
                                    dropzone = iframe.locator(dz_selector)
                                    if await dropzone.is_visible(timeout=1000):
                                        logger.info(f"📦 Dropzone encontrado NO IFRAME: {dz_selector}")
                                        
                                        # Verificar se arquivo existe e é acessível
                                        if not os.path.exists(arquivo_planilha):
                                            logger.error(f"❌ Arquivo não existe: {arquivo_planilha}")
                                            return False
                                        
                                        if not os.access(arquivo_planilha, os.R_OK):
                                            logger.error(f"❌ Arquivo não é legível: {arquivo_planilha}")
                                            return False
                                        
                                        logger.info(f"📁 Arquivo confirmado: {arquivo_planilha}")
                                        logger.info(f"📁 Tamanho: {os.path.getsize(arquivo_planilha)} bytes")
                                        
                                        try:
                                            # Aguardar um pouco para garantir que a página está pronta
                                            logger.info("⏳ Aguardando página estabilizar...")
                                            await self.portal.page.wait_for_timeout(2000)
                                            
                                            # PRIMEIRO: Procurar o input específico do modal baseado na gravação
                                            logger.info("🔍 Procurando input file específico do modal...")
                                            
                                            # Seletores baseados na gravação do Chrome
                                            input_selectors = [
                                                'div.rs-modal-wrapper input[type="file"]',
                                                '#file-uploader input[type="file"]',
                                                'input[name="arquivoExcel"]',
                                                'input[type="file"]'
                                            ]
                                            
                                            for selector in input_selectors:
                                                try:
                                                    # CORREÇÃO CRÍTICA: Procurar input no IFRAME, não no page!
                                                    file_input = iframe.locator(selector).first
                                                    if await file_input.count() > 0:
                                                        logger.info(f"✅ Input encontrado NO IFRAME com seletor: {selector}")
                                                        
                                                        # REMOVIDO page.evaluate - set_input_files funciona com input invisível
                                                        # Fazer upload direto
                                                        await file_input.set_input_files(arquivo_planilha)
                                                        logger.info(f"📤 Arquivo enviado via {selector}, aguardando resposta...")
                                                        
                                                        # Aguardar processamento
                                                        await self.portal.page.wait_for_timeout(5000)
                                                        
                                                        # Verificar se deu erro ANTES de considerar sucesso (passando iframe!)
                                                        if await self._verificar_erro_servidor(iframe):
                                                            logger.error(f"❌ Internal Server Error detectado após envio via {selector}")
                                                            logger.error("❌ O upload FALHOU - servidor retornou erro")
                                                            # Não continuar tentando outros seletores
                                                            # Retornar falha imediatamente
                                                            return False
                                                        
                                                        # Sucesso! (só chega aqui se NÃO teve erro)
                                                        logger.info("✅ Upload processado sem erros pelo servidor")
                                                        await self.confirmar_demanda(iframe)
                                                        return True
                                                        
                                                except Exception as e:
                                                    logger.debug(f"Seletor {selector} não funcionou: {e}")
                                                    continue
                                            
                                            # Se nenhum seletor específico funcionou, tentar método genérico
                                            logger.info("🔍 Tentando método genérico de busca de inputs NO IFRAME...")
                                            file_inputs = await iframe.locator('input[type="file"]').all()
                                            
                                            if file_inputs:
                                                logger.info(f"📁 Encontrados {len(file_inputs)} inputs de arquivo")
                                                
                                                for i, file_input in enumerate(file_inputs):
                                                    try:
                                                        # REMOVIDO page.evaluate - set_input_files funciona com input invisível
                                                        # Fazer upload direto no input
                                                        await file_input.set_input_files(arquivo_planilha)
                                                        logger.info(f"📤 Arquivo enviado diretamente no input {i}, aguardando resposta...")
                                                        
                                                        # Aguardar processamento
                                                        await self.portal.page.wait_for_timeout(5000)
                                                        
                                                        # Verificar se deu erro ANTES de considerar sucesso (passando iframe!)
                                                        if await self._verificar_erro_servidor(iframe):
                                                            logger.error(f"❌ Internal Server Error detectado no input {i}")
                                                            logger.error("❌ O upload FALHOU - servidor retornou erro")
                                                            # Parar de tentar outros inputs
                                                            # Retornar falha imediatamente
                                                            return False
                                                        
                                                        # Se chegou aqui, upload foi bem-sucedido
                                                        logger.info("✅ Upload processado sem erros pelo servidor")
                                                        await self.confirmar_demanda(iframe)
                                                        return True
                                                        
                                                    except Exception as e:
                                                        logger.warning(f"⚠️ Input {i} não funcionou: {e}")
                                                        continue
                                            
                                            # SE NENHUM INPUT FUNCIONOU, tentar método antigo com file chooser
                                            logger.info("⚠️ Upload direto não funcionou, tentando com file chooser...")
                                            
                                            try:
                                                async with self.portal.page.expect_file_chooser(timeout=5000) as fc_info:
                                                    await dropzone.click()
                                                    logger.info("🖱️ Dropzone clicado")
                                                
                                                logger.info("📂 File chooser apareceu")
                                                file_chooser = await fc_info.value
                                            except TimeoutError:
                                                logger.error("⏱️ Timeout: File chooser não apareceu após clicar no dropzone")
                                                logger.error("💡 Isso indica que o dropzone não está abrindo o seletor de arquivo")
                                                logger.error("💡 Possível causa: Sessão expirada ou problema de autenticação")
                                                return False
                                            
                                            logger.info("📤 Setando arquivo no file chooser...")
                                            
                                            # Adicionar um pequeno delay antes de setar o arquivo
                                            await self.portal.page.wait_for_timeout(1000)
                                            
                                            # Verificar se o contexto ainda está correto
                                            current_url = self.portal.page.url
                                            logger.info(f"📍 URL atual antes do upload: {current_url}")
                                            
                                            await file_chooser.set_files(arquivo_planilha)
                                            logger.info(f"✅ Arquivo selecionado via dropzone: {arquivo_planilha}")
                                            
                                            # Aguardar processamento
                                            await self.portal.page.wait_for_timeout(5000)
                                            
                                            # Verificar se apareceu erro no servidor (passando iframe!)
                                            if await self._verificar_erro_servidor(iframe):
                                                logger.error("❌ ERRO DO SERVIDOR DETECTADO após file chooser")
                                                logger.error("❌ O portal Sendas retornou Internal Server Error")
                                                logger.error("💡 Possíveis causas:")
                                                logger.error("   1. Sessão expirada - tente fazer login novamente")
                                                logger.error("   2. Formato de dados incompatível")
                                                logger.error("   3. Problema temporário no servidor Sendas")
                                                
                                                # Capturar screenshot para debug
                                                try:
                                                    screenshot_path = f"/tmp/sendas_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                                    await self.portal.page.screenshot(path=screenshot_path)
                                                    logger.info(f"📸 Screenshot salvo em: {screenshot_path}")
                                                except:
                                                    pass
                                                
                                                return False
                                            
                                            # Confirmar demanda após upload
                                            logger.info("🔍 Procurando botão CONFIRMAR DEMANDA...")
                                            confirm_success = await self.confirmar_demanda(iframe)
                                            
                                            if confirm_success:
                                                logger.info("✅ Upload e confirmação concluídos com sucesso")
                                            else:
                                                logger.warning("⚠️ Upload realizado mas confirmação pode ter falhado")
                                            
                                            return True
                                            
                                        except TimeoutError as te:
                                            logger.error(f"⏱️ Timeout esperando file chooser: {te}")
                                            # Tentar método alternativo - input direto NO IFRAME
                                            logger.info("🔄 Tentando método alternativo no iframe...")
                                            try:
                                                file_input = iframe.locator('input[type="file"]')
                                                if await file_input.count() > 0:
                                                    await file_input.set_input_files(arquivo_planilha)
                                                    logger.info("✅ Arquivo enviado via input direto no iframe (fallback)")
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
                                        except Exception as e:
                                            logger.error(f"❌ Erro ao interagir com dropzone: {e}")
                                            logger.error(f"❌ Tipo do erro: {type(e).__name__}")
                                            logger.error(f"❌ Stack trace:\n{traceback.format_exc()}")
                                            return False
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
                    
                    return True
            else:
                logger.error("❌ Não foi possível encontrar área de upload")
                # Tentar capturar screenshot para debug
                await self.portal.page.screenshot(path='erro_upload_botao_nao_encontrado.png')
                return False
                    
        except PWTimeout as e:
            logger.error(f"⏱️ Timeout durante upload: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro durante upload: {e}")
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
                except:
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
            # Aguardar um pouco para o botão aparecer após o upload
            await self.portal.page.wait_for_timeout(2000)
            
            # Procurar o botão CONFIRMAR DEMANDA com diferentes seletores
            confirm_selectors = [
                'button:has-text("CONFIRMAR DEMANDA")',
                'button.rs-btn-primary:has-text("CONFIRMAR DEMANDA")',
                '.rs-btn.rs-btn-primary:has-text("CONFIRMAR DEMANDA")',
                'button[type="button"]:has-text("CONFIRMAR DEMANDA")'
            ]
            
            for selector in confirm_selectors:
                try:
                    btn_confirmar = iframe.locator(selector)
                    if await btn_confirmar.is_visible(timeout=2000):
                        logger.info(f"✅ Botão CONFIRMAR DEMANDA encontrado: {selector}")
                        
                        # Clicar no botão
                        await btn_confirmar.click()
                        logger.info("🖱️ Clicou em CONFIRMAR DEMANDA")
                        
                        # Aguardar processamento
                        await self.portal.page.wait_for_timeout(3000)
                        
                        # Verificar se apareceu alguma mensagem de sucesso ou erro
                        await self.verificar_resultado_confirmacao(iframe)
                        
                        return True
                except Exception as e:
                    logger.debug(f"Seletor {selector} não funcionou: {e}")
                    continue
            
            # Se não encontrou o botão, pode ser que a confirmação não seja necessária
            logger.warning("⚠️ Botão CONFIRMAR DEMANDA não encontrado - pode não ser necessário")
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
            
            # Verificar e fechar modal se aparecer ANTES de qualquer ação
            await self.portal.page.wait_for_timeout(1000)
            if await self.fechar_modal_se_aparecer(timeout=2000):
                logger.info("✅ Modal fechado antes de iniciar download")
                await self.portal.page.wait_for_timeout(1000)
            
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
                    async with self.portal.page.expect_download() as download_info:
                        item_todos = iframe.get_by_role("menuitem", name="TODOS ITENS")
                        await item_todos.wait_for(state="visible", timeout=5000)
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
    
    async def run_baixar_planilha(self) -> Optional[str]:
        """
        Executa o processo completo de download da planilha
        
        Returns:
            Caminho do arquivo baixado ou None se falhar
        """
        try:
            # Inicializar navegador
            await self.portal.iniciar_navegador()
            
            # Login
            if not await self.portal.fazer_login():
                logger.error("❌ Falha no login")
                return None
            
            # Navegar para gestão de pedidos
            if not await self.navegar_para_gestao_pedidos():
                logger.error("❌ Falha ao navegar para gestão de pedidos")
                return None
            
            # Baixar planilha
            arquivo = await self.baixar_planilha_agendamentos()
            
            # Fechar navegador
            await self.portal.fechar()
            
            return arquivo
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar download: {e}")
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
            # Inicializar navegador
            await self.portal.iniciar_navegador()
            
            # Login
            if not await self.portal.fazer_login():
                logger.error("❌ Falha no login")
                return False
            
            # Navegar para gestão de pedidos
            if not await self.navegar_para_gestao_pedidos():
                logger.error("❌ Falha ao navegar para gestão de pedidos")
                return False
            
            # Fazer upload
            resultado = await self.fazer_upload_planilha(arquivo_planilha)
            
            # Fechar navegador
            await self.portal.fechar()
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar upload: {e}")
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