"""
Serviço para buscar dados de CNPJ na API da Receita Federal

API Utilizada: ReceitaWS (gratuita)
https://receitaws.com.br/api

⚠️ LIMITES:
- 3 requisições por minuto (free)
- 429 Too Many Requests se exceder
"""

import requests
import logging
import time
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class APIReceita:
    """Cliente para API da Receita Federal (ReceitaWS)"""

    BASE_URL = "https://receitaws.com.br/v1/cnpj"
    TIMEOUT = 10  # segundos
    RETRY_DELAY = 20  # segundos (espera se der 429)

    @staticmethod
    def limpar_cnpj(cnpj: str) -> str:
        """Remove formatação do CNPJ"""
        import re
        return re.sub(r'\D', '', str(cnpj))

    @classmethod
    def buscar_cnpj(cls, cnpj: str, retry: bool = True) -> Optional[Dict]:
        """
        Busca dados de um CNPJ na API da Receita

        Args:
            cnpj: CNPJ com ou sem formatação
            retry: Se True, tenta novamente em caso de erro 429

        Returns:
            Dicionário com dados do CNPJ ou None se não encontrar/erro

        Exemplo de resposta:
        {
            "atividade_principal": [{"code": "...", "text": "..."}],
            "data_situacao": "03/11/2005",
            "complemento": "",
            "nome": "EMPRESA EXEMPLO LTDA",
            "uf": "SP",
            "telefone": "(11) 1234-5678",
            "email": "exemplo@empresa.com",
            "qsa": [{"nome": "FULANO", "qual": "49-Sócio-Administrador"}],
            "situacao": "ATIVA",
            "bairro": "CENTRO",
            "logradouro": "RUA EXEMPLO",
            "numero": "123",
            "cep": "01234-567",
            "municipio": "SAO PAULO",
            "abertura": "10/10/2000",
            "natureza_juridica": "206-2 - Sociedade Empresária Limitada",
            "fantasia": "EMPRESA EXEMPLO",
            "cnpj": "12.345.678/0001-99",
            "ultima_atualizacao": "2024-01-15T10:30:00.000Z",
            "status": "OK",
            "complemento": "",
            "efr": "",
            "motivo_situacao": "",
            "situacao_especial": "",
            "data_situacao_especial": "",
            "capital_social": "100000.00"
        }
        """
        cnpj_limpo = cls.limpar_cnpj(cnpj)

        if not cnpj_limpo or len(cnpj_limpo) != 14:
            logger.error(f"CNPJ inválido: {cnpj}")
            return None

        url = f"{cls.BASE_URL}/{cnpj_limpo}"

        try:
            logger.info(f"🔍 Buscando CNPJ {cnpj_limpo} na API Receita...")

            response = requests.get(url, timeout=cls.TIMEOUT)

            # Sucesso
            if response.status_code == 200:
                data = response.json()

                # Verifica se o status é OK
                if data.get('status') == 'OK':
                    logger.info(f"✅ CNPJ {cnpj_limpo} encontrado: {data.get('nome', 'N/A')}")
                    return data
                elif data.get('status') == 'ERROR':
                    logger.error(f"❌ Erro da API: {data.get('message', 'Erro desconhecido')}")
                    return None
                else:
                    logger.warning(f"⚠️ Resposta inesperada: {data}")
                    return data

            # Limite de requisições excedido
            elif response.status_code == 429:
                logger.warning(f"⚠️ Limite de requisições excedido (429)")

                if retry:
                    logger.info(f"⏳ Aguardando {cls.RETRY_DELAY}s para tentar novamente...")
                    time.sleep(cls.RETRY_DELAY)
                    return cls.buscar_cnpj(cnpj, retry=False)  # Tenta apenas 1x
                else:
                    logger.error("❌ Limite excedido e retry desabilitado")
                    return None

            # CNPJ não encontrado
            elif response.status_code == 404:
                logger.error(f"❌ CNPJ {cnpj_limpo} não encontrado na Receita")
                return None

            # Outro erro
            else:
                logger.error(f"❌ Erro HTTP {response.status_code}: {response.text}")
                return None

        except requests.Timeout:
            logger.error(f"⏱️ Timeout ao buscar CNPJ {cnpj_limpo}")
            return None
        except requests.RequestException as e:
            logger.error(f"❌ Erro na requisição: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            return None

    @classmethod
    def extrair_dados_para_cliente(cls, dados_receita: Dict) -> Dict:
        """
        Extrai dados relevantes da API Receita para criar CadastroCliente

        Args:
            dados_receita: Resposta completa da API Receita

        Returns:
            Dicionário com campos mapeados para CadastroCliente
        """
        if not dados_receita or dados_receita.get('status') != 'OK':
            return {}

        return {
            'cnpj_cpf': cls.limpar_cnpj(dados_receita.get('cnpj', '')),
            'raz_social': dados_receita.get('nome', '')[:255],  # Limita a 255 chars
            'raz_social_red': dados_receita.get('fantasia', dados_receita.get('nome', ''))[:100],
            'municipio': dados_receita.get('municipio', '')[:100],
            'estado': dados_receita.get('uf', '')[:2],

            # Endereço completo
            'cep_endereco_ent': dados_receita.get('cep', '').replace('-', ''),
            'rua_endereco_ent': dados_receita.get('logradouro', '')[:255],
            'endereco_ent': dados_receita.get('numero', '')[:20],
            'bairro_endereco_ent': dados_receita.get('bairro', '')[:100],
            'telefone_endereco_ent': dados_receita.get('telefone', '')[:50],
            'nome_cidade': dados_receita.get('municipio', '')[:100],
            'cod_uf': dados_receita.get('uf', '')[:2],

            # Dados adicionais
            'email': dados_receita.get('email', '')[:100] if dados_receita.get('email') else None,
            'situacao': dados_receita.get('situacao', ''),  # ATIVA, BAIXADA, etc
            'data_abertura': dados_receita.get('abertura', '')
        }


def buscar_dados_cnpj(cnpj: str) -> Optional[Dict]:
    """
    Função helper para buscar CNPJ

    Args:
        cnpj: CNPJ com ou sem formatação

    Returns:
        Dicionário com dados do cliente ou None
    """
    api = APIReceita()
    dados = api.buscar_cnpj(cnpj)

    if dados:
        return api.extrair_dados_para_cliente(dados)

    return None
