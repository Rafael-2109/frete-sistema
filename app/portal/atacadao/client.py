"""
Cliente para automação do Portal Atacadão
Implementação baseada no fluxo real do portal
"""

import re
import time
import logging
from datetime import datetime
from ..base_client import BasePortalClient
from .config import ATACADAO_CONFIG

logger = logging.getLogger(__name__)

class AtacadaoClient(BasePortalClient):
    """Cliente específico para o portal Atacadão (Hodie Booking)"""
    
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        self.config = ATACADAO_CONFIG
        self.portal_name = 'atacadao'
    
    def fazer_login(self, usuario, senha):
        """Realiza login no portal Atacadão"""
        try:
            logger.info(f"Iniciando login no Atacadão para usuário: {usuario}")
            
            # Navegar para página de login
            self.navegar_para(self.config['urls']['login'])
            time.sleep(2)
            
            # TODO: Implementar login quando tivermos os seletores corretos
            # Por enquanto, assumir que usuário já está logado (sessão do Chrome)
            
            # Verificar se login foi bem-sucedido
            if self.validar_login():
                logger.info("Sessão válida no Atacadão")
                self.salvar_sessao()
                return True
            else:
                logger.warning("Sessão não válida no Atacadão - login manual necessário")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao fazer login no Atacadão: {e}")
            self.capturar_screenshot('atacadao_login_exception')
            return False
    
    def criar_agendamento(self, dados):
        """
        Cria um novo agendamento no Atacadão
        
        Fluxo:
        1. Buscar pedido
        2. Abrir detalhes do pedido
        3. Solicitar agendamento
        4. Preencher formulário de carga
        5. Salvar e obter protocolo
        """
        try:
            # Obter pedido_cliente do dados
            pedido_cliente = dados.get('pedido_cliente')
            if not pedido_cliente:
                raise ValueError("Campo 'pedido_cliente' é obrigatório para Atacadão")
            
            logger.info(f"Criando agendamento no Atacadão para pedido: {pedido_cliente}")
            
            # Etapa 1: Buscar pedido
            pedido_id = self._buscar_pedido(pedido_cliente)
            if not pedido_id:
                raise Exception(f"Pedido {pedido_cliente} não encontrado")
            
            # Etapa 2: Solicitar agendamento no pedido
            self._abrir_solicitacao_agendamento(pedido_id)
            
            # Etapa 3: Preencher formulário de carga
            self._preencher_formulario_carga(dados)
            
            # Etapa 4: Salvar e obter protocolo
            resultado = self._salvar_e_obter_protocolo()
            
            if resultado['sucesso']:
                logger.info(f"Agendamento criado com sucesso. Protocolo: {resultado.get('protocolo')}")
                self.salvar_sessao()
            else:
                logger.error(f"Erro ao criar agendamento: {resultado.get('erro')}")
                self.capturar_screenshot('atacadao_agendamento_erro')
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao criar agendamento no Atacadão: {e}")
            self.capturar_screenshot('atacadao_agendamento_exception')
            return {
                'sucesso': False,
                'erro': str(e),
                'screenshot': self.capturar_screenshot()
            }
    
    def _buscar_pedido(self, pedido_cliente):
        """Busca o pedido na lista e retorna o ID interno do Atacadão"""
        try:
            logger.info(f"Buscando pedido {pedido_cliente}")
            
            # Navegar para página de pedidos
            self.navegar_para(self.config['urls']['pedidos'])
            time.sleep(2)
            
            # Preencher campo de busca
            self.preencher_campo(self.config['seletores']['campo_pedido'], pedido_cliente)
            
            # Clicar em filtrar
            self.clicar_elemento(self.config['seletores']['botao_filtrar'])
            time.sleep(3)
            
            # Procurar link "Exibir" do pedido
            # O link contém o ID do pedido na URL
            link_exibir = self.aguardar_elemento(self.config['seletores']['link_exibir_pedido'])
            
            if link_exibir:
                # Extrair href do link
                if hasattr(self.driver, 'get_attribute'):
                    href = link_exibir.get_attribute('href')
                else:
                    href = link_exibir.get_attribute('href')
                
                # Extrair ID do pedido da URL (pedidos/912933499)
                match = re.search(r'pedidos/(\d+)', href)
                if match:
                    pedido_id = match.group(1)
                    logger.info(f"Pedido encontrado com ID: {pedido_id}")
                    
                    # Clicar no link para abrir o pedido
                    self.clicar_elemento(self.config['seletores']['link_exibir_pedido'])
                    time.sleep(2)
                    
                    return pedido_id
            
            logger.error(f"Pedido {pedido_cliente} não encontrado na lista")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar pedido: {e}")
            return None
    
    def _abrir_solicitacao_agendamento(self, pedido_id):
        """Abre a tela de solicitação de agendamento para o pedido"""
        try:
            logger.info(f"Abrindo solicitação de agendamento para pedido {pedido_id}")
            
            # Verificar se estamos na página do pedido
            current_url = self.driver.current_url if hasattr(self.driver, 'current_url') else self.driver.url
            if pedido_id not in current_url:
                # Navegar para o pedido se necessário
                url_pedido = self.config['urls']['pedido_detalhe'].format(pedido_id=pedido_id)
                self.navegar_para(url_pedido)
                time.sleep(2)
            
            # Clicar no botão "Solicitar agendamento"
            self.clicar_elemento(self.config['seletores']['botao_solicitar_agendamento'])
            time.sleep(3)
            
            logger.info("Tela de criação de carga aberta")
            
        except Exception as e:
            logger.error(f"Erro ao abrir solicitação de agendamento: {e}")
            raise
    
    def _preencher_formulario_carga(self, dados):
        """Preenche o formulário de criação de carga/agendamento"""
        try:
            logger.info("Preenchendo formulário de carga")
            
            # Data de agendamento (leadtime e data desejada)
            data_formatada = self.formatar_data(dados['data_agendamento'])
            self.preencher_campo(self.config['seletores']['campo_data_leadtime'], data_formatada)
            self.preencher_campo(self.config['seletores']['campo_data_desejada'], data_formatada)
            
            # Selecionar transportadora (Agregado)
            self._selecionar_transportadora()
            
            # Selecionar tipo de carga (Paletizada)
            self._selecionar_opcao(
                self.config['seletores']['select_carga_especie'],
                self.config['valores_padrao']['carga_especie']
            )
            
            # Selecionar tipo de veículo
            tipo_veiculo = dados.get('tipo_veiculo')
            if tipo_veiculo:
                self._selecionar_opcao(
                    self.config['seletores']['select_tipo_veiculo'],
                    tipo_veiculo
                )
            else:
                # Se não especificado, pedir ao usuário ou usar padrão
                logger.warning("Tipo de veículo não especificado, usando Truck-Baú")
                self._selecionar_opcao(
                    self.config['seletores']['select_tipo_veiculo'],
                    '8'  # Truck-Baú
                )
            
            # Preencher quantidades dos produtos
            self._preencher_quantidades_produtos(dados)
            
            logger.info("Formulário de carga preenchido")
            
        except Exception as e:
            logger.error(f"Erro ao preencher formulário: {e}")
            raise
    
    def _selecionar_transportadora(self):
        """Seleciona a transportadora Agregado"""
        try:
            # Abrir modal de transportadoras
            self.clicar_elemento(self.config['seletores']['botao_buscar_transportadora'])
            time.sleep(2)
            
            # Selecionar radio button "Agregado"
            self.clicar_elemento(self.config['seletores']['radio_transportadora_agregado'])
            
            # Confirmar seleção
            self.clicar_elemento(self.config['seletores']['botao_selecionar_transportadora'])
            time.sleep(1)
            
            logger.info("Transportadora Agregado selecionada")
            
        except Exception as e:
            logger.error(f"Erro ao selecionar transportadora: {e}")
            raise
    
    def _selecionar_opcao(self, selector, value):
        """Seleciona uma opção em um select"""
        try:
            if hasattr(self.driver, 'find_element'):
                # Selenium
                try:
                    from selenium.webdriver.support.ui import Select
                    from selenium.webdriver.common.by import By
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    select = Select(element)
                    select.select_by_value(str(value))
                except ImportError:
                    logger.error("Selenium não instalado. Execute: pip install selenium")
                    raise
            else:
                # Playwright
                self.driver.select_option(selector, value=str(value))
            
        except Exception as e:
            logger.error(f"Erro ao selecionar opção {value} em {selector}: {e}")
            raise
    
    def _preencher_quantidades_produtos(self, dados):
        """Preenche as quantidades dos produtos"""
        try:
            # Por enquanto, preencher todas as quantidades disponíveis
            # TODO: Implementar lógica de DE-PARA de códigos de produtos
            
            # Tentar obter campos de quantidade
            if hasattr(self.driver, 'find_elements'):
                try:
                    from selenium.webdriver.common.by import By
                    campos_qtd = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        self.config['seletores']['campo_qtd_produto']
                    )
                    logger.info(f"Encontrados {len(campos_qtd)} campos de quantidade")
                except Exception as e:
                    logger.error(f"Erro ao encontrar campos de quantidade: {e}")
                    raise
            else:
                # Playwright
                campos_qtd = self.driver.locator(self.config['seletores']['campo_qtd_produto']).all()
                logger.info(f"Encontrados {campos_qtd.count()} campos de quantidade")
            
            # Por enquanto, preencher com as quantidades totais se disponível
            # Idealmente, deve-se fazer o match por código de produto
            
        except Exception as e:
            logger.warning(f"Erro ao preencher quantidades: {e}")
            # Continuar mesmo com erro, pois pode ser opcional
    
    def _salvar_e_obter_protocolo(self):
        """Salva a carga e obtém o protocolo de agendamento"""
        try:
            logger.info("Salvando carga")
            
            # Clicar em salvar
            self.clicar_elemento(self.config['seletores']['botao_salvar'])
            time.sleep(3)
            
            # Aguardar modal de sucesso
            sucesso = self.aguardar_elemento(self.config['seletores']['modal_sucesso'], timeout=10)
            
            if sucesso:
                logger.info("Carga salva com sucesso")
                
                # Clicar em "Não" para não incluir NF agora
                self.clicar_elemento(self.config['seletores']['botao_nao_incluir_nf'])
                time.sleep(3)
                
                # Obter ID da carga da URL atual
                current_url = self.driver.current_url if hasattr(self.driver, 'current_url') else self.driver.url
                match_carga = re.search(r'cargas/(\d+)', current_url)
                
                if match_carga:
                    carga_id = match_carga.group(1)
                    logger.info(f"Carga criada com ID: {carga_id}")
                    
                    # Clicar em "Acompanhe Agendamento"
                    self.clicar_elemento(self.config['seletores']['link_acompanhe_agendamento'])
                    time.sleep(3)
                    
                    # Obter protocolo da URL final
                    current_url = self.driver.current_url if hasattr(self.driver, 'current_url') else self.driver.url
                    match_protocolo = re.search(r'agendamentos/(\d+)', current_url)
                    
                    if match_protocolo:
                        protocolo = match_protocolo.group(1)
                        
                        # Obter status
                        status_texto = self.obter_texto(self.config['seletores']['status_agendamento'])
                        
                        return {
                            'sucesso': True,
                            'protocolo': protocolo,
                            'carga_id': carga_id,
                            'status': status_texto,
                            'data_solicitacao': datetime.now(),
                            'url_acompanhamento': current_url
                        }
            
            return {
                'sucesso': False,
                'erro': 'Não foi possível obter protocolo',
                'screenshot': self.capturar_screenshot()
            }
            
        except Exception as e:
            logger.error(f"Erro ao salvar e obter protocolo: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'screenshot': self.capturar_screenshot()
            }
    
    def consultar_status(self, protocolo):
        """Consulta status de um agendamento pelo protocolo"""
        try:
            logger.info(f"Consultando status do protocolo: {protocolo}")
            
            # Navegar direto para URL do agendamento
            url_agendamento = self.config['urls']['agendamento_status'].format(protocolo=protocolo)
            self.navegar_para(url_agendamento)
            time.sleep(2)
            
            # Verificar se protocolo existe
            numero_protocolo = self.obter_texto(self.config['seletores']['numero_protocolo'])
            
            if numero_protocolo and protocolo in numero_protocolo:
                # Obter status
                status = self.obter_texto(self.config['seletores']['status_agendamento'])
                
                resultado = {
                    'sucesso': True,
                    'status': {
                        'protocolo': protocolo,
                        'status': status or 'Não encontrado',
                        'status_normalizado': self._normalizar_status(status)
                    }
                }
                
                logger.info(f"Status obtido: {resultado['status']}")
                return resultado
            else:
                return {
                    'sucesso': False,
                    'erro': f'Protocolo {protocolo} não encontrado'
                }
            
        except Exception as e:
            logger.error(f"Erro ao consultar status: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def _normalizar_status(self, status_texto):
        """Normaliza o status do portal para o sistema"""
        if not status_texto:
            return 'desconhecido'
        
        status_lower = status_texto.lower()
        
        if 'aguardando' in status_lower:
            return 'aguardando'
        elif 'aprovado' in status_lower or 'confirmado' in status_lower:
            return 'confirmado'
        elif 'cancelado' in status_lower:
            return 'cancelado'
        elif 'rejeitado' in status_lower or 'recusado' in status_lower:
            return 'rejeitado'
        else:
            return 'aguardando'
    
    def obter_comprovante(self, protocolo):
        """Obtém comprovante de agendamento"""
        try:
            logger.info(f"Obtendo comprovante do protocolo: {protocolo}")
            
            # Primeiro consultar o status
            resultado_consulta = self.consultar_status(protocolo)
            
            if not resultado_consulta['sucesso']:
                return resultado_consulta
            
            # Capturar screenshot da página como comprovante
            screenshot = self.capturar_screenshot(f'comprovante_{protocolo}')
            
            return {
                'sucesso': True,
                'protocolo': protocolo,
                'comprovante': screenshot,
                'status': resultado_consulta['status']
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter comprovante: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def _verificar_indicadores_login(self):
        """Verifica indicadores específicos de login do Atacadão"""
        try:
            # Verificar se há menu principal
            menu = self.aguardar_elemento(
                self.config['seletores']['menu_principal'], 
                timeout=5
            )
            
            if menu:
                logger.info("Menu principal encontrado - sessão válida")
                return True
            
            # Verificar link de logout
            logout = self.aguardar_elemento(
                self.config['seletores']['link_logout'], 
                timeout=5
            )
            
            if logout:
                logger.info("Link de logout encontrado - sessão válida")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar indicadores de login: {e}")
            return False
    
    def _extrair_protocolo_html(self, html) -> str:
        """Extrai protocolo do HTML"""
        try:
            # Procurar protocolo na URL ou no conteúdo
            match = re.search(r'agendamentos/(\d+)', html)
            if match:
                return match.group(1)
            
            # Procurar no texto
            match = re.search(r'protocolo[:\s]+(\d+)', html, re.IGNORECASE)
            if match:
                return match.group(1)
            
            return ""
            
        except Exception as e:
            logger.error(f"Erro ao extrair protocolo do HTML: {e}")
            return ""
    
    def _extrair_protocolo_pagina(self) -> str:
        """Extrai protocolo da página atual"""
        try:
            # Primeiro tentar extrair da URL
            current_url = self.driver.current_url if hasattr(self.driver, 'current_url') else self.driver.url
            match = re.search(r'agendamentos/(\d+)', current_url)
            if match:
                return match.group(1)
            
            # Tentar obter pelo seletor
            protocolo = self.obter_texto(self.config['seletores']['numero_protocolo'])
            if protocolo:
                # Limpar e retornar apenas números
                return re.sub(r'\D', '', protocolo)
            
            return ""
            
        except Exception as e:
            logger.error(f"Erro ao extrair protocolo da página: {e}")
            return ""