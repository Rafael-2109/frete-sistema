"""
Helper para simular fluxo do Postman para TagPlus
"""
import requests
import logging
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger(__name__)

class PostmanHelper:
    """Simula o fluxo do Postman para obter tokens TagPlus"""
    
    def __init__(self):
        self.auth_url = "https://developers.tagplus.com.br/oauth/authorize"
        self.token_url = "https://developers.tagplus.com.br/oauth/token"
        
    def get_authorization_url_postman_style(self, client_id):
        """
        Gera URL de autorização no estilo Postman
        """
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': 'https://www.postman.com/oauth2/callback',
            'scope': 'read write',
            'state': 'tagplus_auth'
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    def extract_code_from_callback(self, callback_url):
        """
        Extrai código da URL de callback do Postman
        Exemplo: https://www.postman.com/oauth2/callback?code=ABC123&state=tagplus_auth
        """
        try:
            parsed = urlparse(callback_url)
            params = parse_qs(parsed.query)
            
            if 'code' in params:
                return params['code'][0]
            else:
                return None
        except Exception as e:
            logger.error(f"Erro ao extrair código: {e}")
            return None
    
    def exchange_code_for_tokens(self, code, client_id, client_secret):
        """
        Troca código por tokens (igual ao Postman)
        """
        try:
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': 'https://www.postman.com/oauth2/callback',
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            response = requests.post(
                self.token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.text
                
        except Exception as e:
            logger.error(f"Erro ao trocar código: {e}")
            return False, str(e)
    
    def refresh_access_token(self, refresh_token, client_id, client_secret):
        """
        Renova Access Token usando Refresh Token
        """
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            response = requests.post(
                self.token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.text
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False, str(e)
    
    def test_api_with_token(self, access_token):
        """
        Testa API com token obtido
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Tenta endpoint de clientes
            response = requests.get(
                'https://api.tagplus.com.br/v1/clientes',
                headers=headers,
                params={'limit': 1}
            )
            
            if response.status_code == 200:
                return True, "Token válido - API funcionando!"
            else:
                return False, f"Erro {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)