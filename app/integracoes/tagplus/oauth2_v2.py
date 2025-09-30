"""
OAuth2 para TagPlus API v2 - Fluxo Authorization Code
"""

import os
import time
import requests
import logging
from urllib.parse import urlencode
from flask import session

logger = logging.getLogger(__name__)

class TagPlusOAuth2V2:
    """Gerenciador OAuth2 para TagPlus API v2"""
    
    # URLs do TagPlus (CORRIGIDAS conforme documentação)
    AUTH_URL = "https://developers.tagplus.com.br/authorize"
    TOKEN_URL = "https://api.tagplus.com.br/oauth2/token"
    API_BASE = "https://api.tagplus.com.br"
    
    def __init__(self, api_type='clientes'):
        """
        Inicializa OAuth2 para API específica
        
        Args:
            api_type: 'clientes' ou 'notas'
        """
        self.api_type = api_type
        
        if api_type == 'clientes':
            self.client_id = os.environ.get('TAGPLUS_CLIENTES_CLIENT_ID', 'FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD')
            self.client_secret = os.environ.get('TAGPLUS_CLIENTES_CLIENT_SECRET', 'uNWYSWyOHGFJvJoEdw1H5xgZnCM92Ey7')
            self.redirect_uri = 'https://sistema-fretes.onrender.com/tagplus/oauth/callback/cliente'
            self.scopes = 'read:clientes write:clientes'
        else:  # notas
            self.client_id = os.environ.get('TAGPLUS_NOTAS_CLIENT_ID', '8YZNqaklKj3CfIkOtkoV9ILpCllAtalT')
            self.client_secret = os.environ.get('TAGPLUS_NOTAS_CLIENT_SECRET', 'MJHfk8hr3022Y1ETTwqSf0Qsb5Lj6HZe')
            self.redirect_uri = 'https://sistema-fretes.onrender.com/tagplus/oauth/callback/nfe'
            self.scopes = 'read:nfes read:clientes read:produtos'
        
        # Tokens (armazenados em sessão ou memória)
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Tenta carregar tokens da sessão se disponível
        self._load_tokens_from_session()
    
    def get_authorization_url(self, state=None):
        """
        Gera URL para autorização do usuário
        
        Returns:
            URL para redirecionar o usuário
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scopes
        }
        
        if state:
            params['state'] = state
        
        url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info(f"URL de autorização gerada para {self.api_type}: {url}")
        return url
    
    def exchange_code_for_tokens(self, code):
        """
        Troca código de autorização por tokens

        Args:
            code: Código recebido após autorização

        Returns:
            dict com tokens ou None se falhar
        """
        try:
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri
            }

            logger.info(f"[{self.api_type}] Enviando requisição para: {self.TOKEN_URL}")
            logger.info(f"[{self.api_type}] Client ID: {self.client_id[:10]}...")
            logger.info(f"[{self.api_type}] Redirect URI: {self.redirect_uri}")
            logger.info(f"[{self.api_type}] Code: {code[:20]}...")

            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )

            logger.info(f"[{self.api_type}] Status Code: {response.status_code}")

            if response.status_code == 200:
                tokens = response.json()
                self._save_tokens(tokens)
                logger.info(f"Tokens obtidos com sucesso para {self.api_type}")
                logger.info(f"Access Token: {tokens.get('access_token', '')[:30]}...")
                return tokens
            else:
                logger.error(f"[{self.api_type}] Erro ao trocar código: {response.status_code}")
                logger.error(f"[{self.api_type}] Resposta: {response.text}")
                # Log detalhado do erro
                try:
                    error_json = response.json()
                    logger.error(f"[{self.api_type}] Erro JSON: {error_json}")
                except:
                    pass
                return None

        except Exception as e:
            logger.error(f"[{self.api_type}] Erro ao trocar código por tokens: {e}")
            return None
    
    def refresh_access_token(self):
        """
        Renova access token usando refresh token
        
        Returns:
            bool indicando sucesso
        """
        if not self.refresh_token:
            logger.warning(f"Sem refresh token para {self.api_type}")
            return False
        
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self._save_tokens(tokens)
                logger.info(f"Token renovado para {self.api_type}")
                return True
            else:
                logger.error(f"Erro ao renovar token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False
    
    def _save_tokens(self, token_data):
        """Salva tokens na memória e sessão"""
        self.access_token = token_data.get('access_token')
        self.refresh_token = token_data.get('refresh_token', self.refresh_token)
        
        # Calcula expiração (com margem de 5 minutos)
        expires_in = token_data.get('expires_in', 86400)
        self.token_expires_at = time.time() + expires_in - 300
        
        # Salva na sessão se disponível
        try:
            if session:
                session[f'tagplus_{self.api_type}_access_token'] = self.access_token
                session[f'tagplus_{self.api_type}_refresh_token'] = self.refresh_token
                session[f'tagplus_{self.api_type}_expires_at'] = self.token_expires_at
        except Exception as e:
            logger.error(f"Erro ao salvar tokens na sessão: {e}")
            pass  # Sessão não disponível (ex: script CLI)
    
    def _load_tokens_from_session(self):
        """Carrega tokens da sessão Flask se disponível"""
        try:
            if session:
                self.access_token = session.get(f'tagplus_{self.api_type}_access_token')
                self.refresh_token = session.get(f'tagplus_{self.api_type}_refresh_token')
                self.token_expires_at = session.get(f'tagplus_{self.api_type}_expires_at')
        except Exception as e:
            logger.error(f"Erro ao carregar tokens da sessão: {e}")
            pass  # Sessão não disponível
    
    def get_headers(self):
        """
        Retorna headers para requisições autenticadas
        Renova token automaticamente se necessário
        """
        # Verifica se token expirou ou não existe
        if not self.access_token or (self.token_expires_at and time.time() >= self.token_expires_at):
            if self.refresh_token:
                logger.info(f"Token expirado para {self.api_type}, renovando...")
                if not self.refresh_access_token():
                    raise Exception(f"Não foi possível renovar token para {self.api_type}")
            else:
                raise Exception(f"Sem token válido para {self.api_type}. É necessário autorizar primeiro.")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'X-Api-Version': '2.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def make_request(self, method, endpoint, **kwargs):
        """
        Faz requisição autenticada para API v2

        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Caminho da API (ex: '/clientes')
            **kwargs: Parâmetros adicionais para requests

        Returns:
            Response object ou None se falhar
        """
        try:
            headers = self.get_headers()

            # Remove Content-Type para requisições GET
            if method.upper() == 'GET':
                headers.pop('Content-Type', None)

            url = f"{self.API_BASE}{endpoint}"

            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=kwargs.pop('timeout', 300),  # 5 minutos de timeout padrão
                **kwargs
            )

            logger.debug(f"{method} {url} - Status: {response.status_code}")

            return response

        except Exception as e:
            logger.error(f"Erro na requisição {method} {endpoint}: {e}")
            return None
    
    def test_connection(self):
        """Testa a conexão com a API"""
        try:
            # Endpoint de teste depende da API
            if self.api_type == 'clientes':
                endpoint = '/clientes'
            else:
                endpoint = '/nfes'
            
            response = self.make_request(
                'GET', 
                endpoint,
                params={'pagina': 1, 'limite': 1}
            )
            
            if response and response.status_code == 200:
                logger.info(f"Conexão OK com API {self.api_type}")
                return True, response.json()
            else:
                error_msg = response.text if response else "Sem resposta"
                logger.error(f"Erro na conexão: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False, str(e)
    
    def set_tokens(self, access_token, refresh_token=None):
        """
        Define tokens manualmente (útil para testes ou tokens salvos)
        
        Args:
            access_token: Token de acesso
            refresh_token: Token de renovação (opcional)
        """
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        self.token_expires_at = time.time() + 86400 - 300  # 24h menos 5 min
        self._save_tokens({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': 86400
        })