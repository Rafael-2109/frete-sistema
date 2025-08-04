"""
Autenticação simplificada com TagPlus usando usuário/senha
"""
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TagPlusAuthSimplificado:
    """Autenticação direta com usuário/senha TagPlus"""
    
    def __init__(self, usuario='rayssa', senha='A12345'):
        self.base_url = "https://api.tagplus.com.br"
        self.usuario = usuario
        self.senha = senha
        
        # Cache de tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Tenta autenticar automaticamente
        self.autenticar()
    
    def autenticar(self):
        """Realiza autenticação com usuário e senha"""
        try:
            # Endpoint de login direto (se disponível)
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={
                    'usuario': self.usuario,
                    'senha': self.senha
                },
                headers={
                    'Content-Type': 'application/json'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token', data.get('token'))
                self.refresh_token = data.get('refresh_token')
                
                # Define expiração (24 horas padrão)
                expires_in = data.get('expires_in', 86400)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 3600)
                
                logger.info("Autenticação TagPlus realizada com sucesso")
                return True
            else:
                logger.error(f"Erro na autenticação: {response.status_code} - {response.text}")
                
                # Tenta método alternativo (OAuth2 Resource Owner Password)
                return self._autenticar_oauth2_password()
                
        except Exception as e:
            logger.error(f"Erro ao autenticar no TagPlus: {e}")
            return False
    
    def _autenticar_oauth2_password(self):
        """Tenta autenticação OAuth2 com Resource Owner Password Grant"""
        try:
            # Este é um método OAuth2 que permite usar usuário/senha diretamente
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    'grant_type': 'password',
                    'username': self.usuario,
                    'password': self.senha,
                    'scope': 'read:clientes write:clientes read:nfes read:financeiros'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                
                expires_in = data.get('expires_in', 86400)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 3600)
                
                logger.info("Autenticação OAuth2 realizada com sucesso")
                return True
            else:
                logger.error(f"Erro OAuth2: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro OAuth2: {e}")
            return False
    
    def get_headers(self):
        """Retorna headers com token de autenticação"""
        if not self.access_token:
            # Tenta autenticar novamente
            if not self.autenticar():
                raise Exception("Não foi possível autenticar no TagPlus")
        
        # Verifica se token expirou
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            logger.info("Token expirado, renovando...")
            if not self.renovar_token():
                # Tenta autenticar novamente
                if not self.autenticar():
                    raise Exception("Não foi possível renovar autenticação")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def renovar_token(self):
        """Renova o token usando refresh token"""
        if not self.refresh_token:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                
                expires_in = data.get('expires_in', 86400)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 3600)
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return False
    
    def testar_conexao(self):
        """Testa se a conexão está funcionando"""
        try:
            headers = self.get_headers()
            
            # Tenta buscar informações básicas
            response = requests.get(
                f"{self.base_url}/v1/empresa",  # ou outro endpoint simples
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info("Conexão com TagPlus OK")
                return True, response.json()
            else:
                logger.error(f"Erro ao testar conexão: {response.status_code}")
                return False, response.text
                
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False, str(e)