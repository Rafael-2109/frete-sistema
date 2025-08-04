"""
Autenticação TagPlus usando API Key
"""
import requests
import logging
import os

logger = logging.getLogger(__name__)

class TagPlusAuthAPIKey:
    """Autenticação usando API Key do TagPlus"""
    
    def __init__(self, api_key=None):
        # Permite modo de teste local
        if os.environ.get('TAGPLUS_TEST_MODE') == 'local':
            self.base_url = os.environ.get('TAGPLUS_TEST_URL', 'http://localhost:8080/api/v1')
            self.api_key = 'test-key'
            logger.info(f"Modo de teste local ativado: {self.base_url}")
        else:
            self.base_url = "https://api.tagplus.com.br/api/v1"
            # API Key pode vir do parâmetro ou variável de ambiente
            self.api_key = api_key or os.environ.get('TAGPLUS_API_KEY', 'seu-api-key-aqui')
        
        logger.info(f"TagPlus configurado para: {self.base_url}")
    
    def get_headers(self):
        """Retorna headers com API Key"""
        return {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def testar_conexao(self):
        """Testa se a conexão está funcionando"""
        try:
            # Tenta endpoint simples para validar API Key
            response = requests.get(
                f"{self.base_url}/ping",  # ou /health, /status
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Conexão com TagPlus OK")
                return True, "Conexão estabelecida com sucesso"
            elif response.status_code == 401:
                logger.error("API Key inválida ou não autorizada")
                return False, "API Key inválida. Verifique suas credenciais."
            elif response.status_code == 404:
                # Se ping não existe, tenta outro endpoint
                return self._testar_endpoint_alternativo()
            else:
                logger.error(f"Erro ao testar conexão: {response.status_code}")
                return False, f"Erro HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.Timeout:
            logger.error("Timeout ao conectar com TagPlus")
            return False, "Timeout ao conectar com TagPlus. Verifique sua conexão."
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False, f"Erro de conexão: {str(e)}"
    
    def _testar_endpoint_alternativo(self):
        """Tenta endpoint alternativo se o principal não existir"""
        try:
            # Tenta listar empresas ou outro recurso básico
            response = requests.get(
                f"{self.base_url}/empresas",
                headers=self.get_headers(),
                params={'limit': 1},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Conexão com TagPlus OK (endpoint alternativo)")
                return True, "Conexão estabelecida com sucesso"
            else:
                return False, f"Erro HTTP {response.status_code}"
                
        except Exception as e:
            logger.error(f"Erro no endpoint alternativo: {e}")
            return False, str(e)