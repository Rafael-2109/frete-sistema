"""
Autenticação TagPlus usando Bearer Token
"""
import requests
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TagPlusAuthBearer:
    """Autenticação usando Bearer Token do TagPlus"""
    
    def __init__(self, client_id=None, client_secret=None, access_token=None, refresh_token=None):
        # URLs da API
        self.base_url = "https://api.tagplus.com.br"
        self.auth_url = "https://developers.tagplus.com.br/oauth/token"
        self.authorize_url = "https://developers.tagplus.com.br/oauth/authorize"
        
        # Credenciais
        self.client_id = client_id or os.environ.get('TAGPLUS_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('TAGPLUS_CLIENT_SECRET')
        
        # Token cache
        self.access_token = access_token or os.environ.get('TAGPLUS_ACCESS_TOKEN')
        self.refresh_token = refresh_token or os.environ.get('TAGPLUS_REFRESH_TOKEN')
        self.token_expires_at = None
        
        # Se estiver em modo de teste
        if os.environ.get('TAGPLUS_TEST_MODE') == 'local':
            self.base_url = os.environ.get('TAGPLUS_TEST_URL', 'http://localhost:8080')
            self.auth_url = f"{self.base_url}/oauth/token"
            logger.info(f"Modo de teste local ativado: {self.base_url}")
    
    def obter_token(self):
        """Obtém um novo access token usando refresh token"""
        try:
            # Se não temos refresh token, não podemos obter novo access token
            if not self.refresh_token:
                logger.error("Refresh token não disponível. É necessário autorizar a aplicação primeiro.")
                return False
            
            if not self.client_id or not self.client_secret:
                raise Exception("Client ID e Client Secret são obrigatórios")
            
            # Requisição OAuth2 Refresh Token
            response = requests.post(
                self.auth_url,
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                # Atualiza refresh token se um novo foi fornecido
                if data.get('refresh_token'):
                    self.refresh_token = data.get('refresh_token')
                
                # Calcula expiração (24 horas segundo a documentação)
                expires_in = data.get('expires_in', 86400)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min antes
                
                logger.info("Token renovado com sucesso")
                return True
            else:
                logger.error(f"Erro ao renovar token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False
    
    def get_authorization_url(self, redirect_uri):
        """Retorna a URL para autorizar a aplicação"""
        if not self.client_id:
            raise Exception("Client ID é obrigatório")
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': 'read write'
        }
        
        from urllib.parse import urlencode
        return f"{self.authorize_url}?{urlencode(params)}"
    
    def trocar_codigo_por_token(self, code, redirect_uri):
        """Troca código de autorização por access token"""
        try:
            response = requests.post(
                self.auth_url,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                
                # Calcula expiração
                expires_in = data.get('expires_in', 86400)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                
                logger.info("Tokens obtidos com sucesso")
                return True, data
            else:
                logger.error(f"Erro ao trocar código: {response.status_code} - {response.text}")
                return False, response.text
                
        except Exception as e:
            logger.error(f"Erro ao trocar código por token: {e}")
            return False, str(e)
    
    def get_headers(self):
        """Retorna headers com Bearer Token"""
        # Se não temos access token, não podemos fazer requisições
        if not self.access_token:
            raise Exception("Access token não disponível. É necessário autorizar a aplicação primeiro.")
        
        # Verifica se precisa renovar o token
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            if not self.obter_token():
                raise Exception("Não foi possível renovar token de acesso")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def testar_conexao(self):
        """Testa se a conexão está funcionando"""
        try:
            headers = self.get_headers()
            
            # Tenta endpoint de teste
            response = requests.get(
                f"{self.base_url}/v1/ping",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Conexão com TagPlus OK")
                return True, "Conexão estabelecida com sucesso"
            elif response.status_code == 404:
                # Tenta endpoint alternativo
                return self._testar_endpoint_alternativo(headers)
            else:
                logger.error(f"Erro ao testar conexão: {response.status_code}")
                return False, f"Erro HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False, str(e)
    
    def _testar_endpoint_alternativo(self, headers):
        """Tenta endpoint alternativo"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/empresas",
                headers=headers,
                params={'limit': 1},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Conexão OK (endpoint alternativo)")
                return True, "Conexão estabelecida"
            else:
                return False, f"Erro HTTP {response.status_code}"
                
        except Exception as e:
            return False, str(e)