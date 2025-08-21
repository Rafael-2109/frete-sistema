"""
Base Client
Classe base para todos os clientes de portal
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

class BasePortalClient(ABC):
    """Classe base abstrata para clientes de portal"""
    
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.driver = browser_manager.get_driver()
        self.portal_name = self.__class__.__name__.replace('Client', '').lower()
        
    @abstractmethod
    def fazer_login(self, usuario, senha) -> bool:
        """Realiza login no portal"""
        pass
    
    @abstractmethod
    def criar_agendamento(self, dados) -> dict:
        """Cria um novo agendamento"""
        pass
    
    @abstractmethod
    def consultar_status(self, protocolo) -> dict:
        """Consulta status de um agendamento"""
        pass
    
    @abstractmethod
    def obter_comprovante(self, protocolo) -> dict:
        """Obtém comprovante de agendamento"""
        pass
    
    def validar_login(self):
        """Verifica se está logado no portal"""
        try:
            # Verificar se está na página correta
            current_url = self.driver.current_url if hasattr(self.driver, 'current_url') else self.driver.url
            
            # Se estiver em página de login, retornar False
            if 'login' in current_url.lower() or 'signin' in current_url.lower():
                logger.info(f"Detectada página de login em {self.portal_name}")
                return False
            
            # Verificar elementos que indicam login bem-sucedido
            # Cada portal implementará seus próprios indicadores
            return self._verificar_indicadores_login()
            
        except Exception as e:
            logger.error(f"Erro ao validar login em {self.portal_name}: {e}")
            return False
    
    @abstractmethod
    def _verificar_indicadores_login(self) -> bool:
        """Verifica indicadores específicos de login do portal"""
        pass
    
    def extrair_protocolo(self, resposta_html=None):
        """Extrai protocolo da resposta do portal"""
        try:
            if resposta_html:
                # Implementação específica de cada portal
                return self._extrair_protocolo_html(resposta_html)
            else:
                # Tentar extrair da página atual
                return self._extrair_protocolo_pagina()
        except Exception as e:
            logger.error(f"Erro ao extrair protocolo: {e}")
            return None
    
    @abstractmethod
    def _extrair_protocolo_html(self, html) -> str:
        """Extrai protocolo do HTML"""
        pass
    
    @abstractmethod
    def _extrair_protocolo_pagina(self) -> str:
        """Extrai protocolo da página atual"""
        pass
    
    def capturar_screenshot(self, nome_arquivo=None):
        """Captura screenshot para debug"""
        if not nome_arquivo:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{self.portal_name}_{timestamp}.png"
        
        return self.browser_manager.take_screenshot(nome_arquivo)
    
    def aguardar_elemento(self, selector, timeout=10):
        """Aguarda elemento aparecer na página"""
        return self.browser_manager.wait_for_element(selector, timeout)
    
    def preencher_campo(self, selector, valor):
        """Preenche campo no formulário"""
        return self.browser_manager.fill_field(selector, valor)
    
    def clicar_elemento(self, selector):
        """Clica em elemento"""
        return self.browser_manager.click_element(selector)
    
    def obter_texto(self, selector):
        """Obtém texto de elemento"""
        return self.browser_manager.get_text(selector)
    
    def navegar_para(self, url):
        """Navega para URL"""
        return self.browser_manager.navigate_to(url)
    
    def salvar_sessao(self):
        """Salva sessão atual para reutilização"""
        self.browser_manager.save_storage_state(self.portal_name)
    
    def formatar_data(self, data, formato='%d/%m/%Y'):
        """Formata data para o formato esperado pelo portal"""
        if isinstance(data, str):
            # Tentar converter string para date
            try:
                data = datetime.strptime(data, '%Y-%m-%d').date()
            except Exception as e:
                logger.error(f"Erro ao formatar data: {e}")
                return data
        
        if hasattr(data, 'strftime'):
            return data.strftime(formato)
        
        return str(data)
    
    def validar_dados_agendamento(self, dados):
        """Valida dados necessários para agendamento"""
        campos_obrigatorios = [
            'cnpj_cliente',
            'nota_fiscal',
            'data_agendamento',
            'volumes',
            'peso',
            'valor'
        ]
        
        faltando = []
        for campo in campos_obrigatorios:
            if campo not in dados or not dados[campo]:
                faltando.append(campo)
        
        if faltando:
            raise ValueError(f"Campos obrigatórios faltando: {', '.join(faltando)}")
        
        return True