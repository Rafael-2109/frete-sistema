"""
Autenticação OAuth2 com TagPlus
"""
import requests
import logging
from datetime import datetime, timedelta
from flask import current_app
import os

logger = logging.getLogger(__name__)

class TagPlusAuth:
    """Gerenciador de autenticação OAuth2 para TagPlus"""
    
    def __init__(self):
        self.base_url = "https://api.tagplus.com.br"
        self.client_id = os.getenv('TAGPLUS_CLIENT_ID')
        self.client_secret = os.getenv('TAGPLUS_CLIENT_SECRET')
        self.callback_url = os.getenv('TAGPLUS_CALLBACK_URL')
        
        # Cache de tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def get_auth_url(self, scopes=None):
        """Gera URL para autorização OAuth2"""
        if not scopes:
            scopes = [
                'read:clientes',
                'write:clientes',
                'read:nfes',
                'read:nfces',
                'read:notas_fiscais_entrada',
                'read:financeiros'
            ]
        
        scope_string = ' '.join(scopes)
        
        auth_url = (
            f"{self.base_url}/oauth/authorize?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.callback_url}&"
            f"response_type=code&"
            f"scope={scope_string}"
        )
        
        return auth_url
    
    def exchange_code_for_token(self, code):
        """Troca código de autorização por tokens"""
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'redirect_uri': self.callback_url
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self._store_tokens(data)
                return True
            else:
                logger.error(f"Erro ao trocar código por token: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro na autenticação TagPlus: {e}")
            return False
    
    def refresh_access_token(self):
        """Atualiza o access token usando o refresh token"""
        if not self.refresh_token:
            logger.error("Refresh token não disponível")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self._store_tokens(data)
                return True
            else:
                logger.error(f"Erro ao renovar token: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False
    
    def _store_tokens(self, token_data):
        """Armazena tokens e calcula expiração"""
        self.access_token = token_data.get('access_token')
        self.refresh_token = token_data.get('refresh_token')
        
        # Calcula quando o token expira (24 horas - 1 hora de margem)
        expires_in = token_data.get('expires_in', 86400)  # 24 horas em segundos
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 3600)
        
        logger.info("Tokens TagPlus armazenados com sucesso")
    
    def get_headers(self):
        """Retorna headers com token de autenticação"""
        if not self.access_token:
            raise Exception("Token de acesso não disponível")
        
        # Verifica se precisa renovar o token
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            logger.info("Token expirado, renovando...")
            if not self.refresh_access_token():
                raise Exception("Falha ao renovar token")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def is_authenticated(self):
        """Verifica se está autenticado"""
        return self.access_token is not None