"""
Session Manager
Gerencia sessões e cookies dos portais com criptografia
"""

import os
import json
import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

class SessionManager:
    """Gerencia sessões e cookies dos portais com criptografia"""
    
    def __init__(self):
        # Gerar ou carregar chave de criptografia
        self.cipher_key = self._get_or_create_key()
        self.cipher = Fernet(self.cipher_key)
    
    def _get_or_create_key(self):
        """Obtém ou cria chave de criptografia"""
        key_file = 'app/portal/portal_sessions/.encryption_key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            os.makedirs('app/portal/portal_sessions', exist_ok=True)
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def save_cookies(self, driver, portal_name, usuario=None):
        """Salva cookies criptografados no banco"""
        try:
            from .models import PortalSessao
            
            # Obter cookies do driver
            if hasattr(driver, 'get_cookies'):
                cookies = driver.get_cookies()
            else:
                # Para Playwright
                cookies = driver.context.cookies()
            
            # Criptografar
            cookies_json = json.dumps(cookies)
            encrypted = self.cipher.encrypt(cookies_json.encode())
            
            # Salvar no banco
            sessao = PortalSessao.query.filter_by(
                portal=portal_name,
                usuario=usuario
            ).first()
            
            if not sessao:
                sessao = PortalSessao(
                    portal=portal_name,
                    usuario=usuario
                )
                db.session.add(sessao)
            
            sessao.cookies_criptografados = encrypted.decode()
            sessao.valido_ate = agora_utc_naive() + timedelta(hours=8)
            sessao.ultima_utilizacao = agora_utc_naive()
            
            # Salvar storage state se for Playwright
            if hasattr(driver, 'context'):
                storage = driver.context.storage_state()
                sessao.storage_state = storage
            
            db.session.commit()
            logger.info(f"Cookies salvos para {portal_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar cookies: {e}")
            return False
    
    def load_cookies(self, driver, portal_name, usuario=None):
        """Carrega cookies salvos do banco"""
        try:
            from .models import PortalSessao
            
            # Buscar sessão válida
            sessao = PortalSessao.query.filter(
                PortalSessao.portal == portal_name,
                PortalSessao.valido_ate > agora_utc_naive()
            ).order_by(PortalSessao.ultima_utilizacao.desc()).first()
            
            if not sessao:
                logger.info(f"Nenhuma sessão válida para {portal_name}")
                return False
            
            # Descriptografar
            cookies_json = self.cipher.decrypt(
                sessao.cookies_criptografados.encode()
            )
            cookies = json.loads(cookies_json)
            
            # Aplicar cookies
            if hasattr(driver, 'add_cookie'):
                # Selenium
                for cookie in cookies:
                    # Limpar campos que podem causar erro
                    if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                        cookie['sameSite'] = 'None'
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        logger.warning(f"Cookie não aplicado: {e}")
            else:
                # Playwright
                driver.context.add_cookies(cookies)
            
            # Atualizar última utilização
            sessao.ultima_utilizacao = agora_utc_naive()
            db.session.commit()
            
            logger.info(f"Cookies carregados para {portal_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar cookies: {e}")
            return False
    
    def detect_login_page(self, driver, portal_config):
        """Detecta se está na página de login"""
        login_indicators = portal_config.get('login_indicators', [])
        
        for selector in login_indicators:
            try:
                if hasattr(driver, 'find_element'):
                    # Selenium
                    from selenium.webdriver.common.by import By
                    driver.find_element(By.CSS_SELECTOR, selector)
                else:
                    # Playwright
                    driver.locator(selector).first
                
                logger.info(f"Página de login detectada (selector: {selector})")
                return True
            except Exception as e:
                logger.error(f"Erro ao verificar indicador: {e}")
                continue
        
        return False
    
    def is_session_valid(self, driver, portal_config):
        """Verifica se a sessão atual é válida"""
        # Primeiro verificar se não está na página de login
        if self.detect_login_page(driver, portal_config):
            return False
        
        # Verificar indicadores de sessão válida
        valid_indicators = portal_config.get('session_valid_indicators', [])
        for selector in valid_indicators:
            try:
                if hasattr(driver, 'find_element'):
                    from selenium.webdriver.common.by import By
                    driver.find_element(By.CSS_SELECTOR, selector)
                else:
                    driver.locator(selector).first
                return True
            except Exception as e:
                logger.error(f"Erro ao verificar indicador: {e}")
                continue
        
        # Se não encontrou indicadores, assumir que sessão é válida
        # (melhor tentar do que falhar prematuramente)
        return True
    
    def handle_session_expired(self, portal_name, integracao_id=None, user_email=None):
        """Trata sessão expirada"""
        from .models import PortalIntegracao, PortalLog
        
        # Atualizar status da integração se ID fornecido
        if integracao_id:
            integracao = db.session.get(PortalIntegracao,integracao_id) if integracao_id else None
            if integracao:
                integracao.status = 'sessao_expirada'
                integracao.ultimo_erro = 'Sessão expirada no portal'
                
                # Log
                log = PortalLog(
                    integracao_id=integracao_id,
                    acao='sessao_expirada',
                    sucesso=False,
                    mensagem='Sessão expirada, reautenticação necessária'
                )
                db.session.add(log)
                db.session.commit()
        
        # Notificar usuário se email disponível
        if user_email:
            self._send_notification(
                user_email,
                f"Sessão expirada no portal {portal_name}",
                "Por favor, faça login novamente para continuar."
            )
        
        return {
            'success': False,
            'error': 'Sessão expirada',
            'action_required': 'login',
            'portal': portal_name
        }
    
    def _send_notification(self, email, subject, message):
        """Envia notificação por email"""
        # TODO: Implementar envio de email
        # Por enquanto, apenas log
        logger.info(f"Notificação: {subject} - {message}")