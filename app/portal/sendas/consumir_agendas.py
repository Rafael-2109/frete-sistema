#!/usr/bin/env python3
"""
Módulo para consumir agendas do Portal Sendas (Trizy)
Realiza download automático da planilha de agendamentos disponíveis
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from playwright.async_api import TimeoutError as PWTimeout, Download
from sendas_playwright import SendasPortal

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
        self.portal = SendasPortal(headless=False)  # Pode mudar para True em produção
        
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
            
            await self.portal.page.wait_for_timeout(1000)
            
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
    
    async def baixar_planilha_agendamentos(self) -> Optional[str]:
        """
        Realiza o download da planilha de agendamentos
        
        Returns:
            Caminho do arquivo baixado ou None se falhar
        """
        try:
            logger.info("📥 Iniciando download da planilha...")
            
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


if __name__ == "__main__":
    # Executar
    asyncio.run(main())