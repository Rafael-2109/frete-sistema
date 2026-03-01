"""
HaveIBeenPwned Service
======================

Integra com API HaveIBeenPwned:
- Email breaches: GET /breachedaccount/{email} (requer API key)
- Password check (GRATIS): GET api.pwnedpasswords.com/range/{5chars} (k-anonymity)

SEGURANCA:
- Password check usa k-anonymity — NUNCA envia hash completo
- Senhas NUNCA sao armazenadas ou logadas
"""

import hashlib
import time
import requests
from typing import Optional, Dict, Any, List

from app.utils.logging_config import logger


# Rate limiting: 1.6s entre requests (free tier HIBP)
_RATE_LIMIT_SECONDS = 1.6
_REQUEST_TIMEOUT = 10
_MAX_RETRIES = 3
_HIBP_API_BASE = 'https://haveibeenpwned.com/api/v3'
_HIBP_PASSWORD_API = 'https://api.pwnedpasswords.com/range'
_USER_AGENT = 'NacomGoya-FreteSeguranca'

# Controle de rate limiting
_last_request_time = 0.0


def _rate_limit():
    """Aguarda rate limit entre requests"""
    global _last_request_time
    agora = time.monotonic()
    elapsed = agora - _last_request_time
    if elapsed < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - elapsed)
    _last_request_time = time.monotonic()


def verificar_email_breaches(
    email: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifica se email apareceu em vazamentos conhecidos.

    Requer API key HIBP. Sem key, retorna aviso de degradacao.

    Args:
        email: Email para verificar
        api_key: API key HIBP (opcional)

    Returns:
        dict com 'sucesso', 'breaches' (lista), 'total', 'sem_api_key'
    """
    if not api_key:
        return {
            'sucesso': True,
            'breaches': [],
            'total': 0,
            'sem_api_key': True,
            'mensagem': (
                'API Key HIBP nao configurada. '
                'Verificacao de breaches de email desabilitada. '
                'Configure em Seguranca > Configuracao.'
            )
        }

    _rate_limit()

    headers = {
        'hibp-api-key': api_key,
        'user-agent': _USER_AGENT,
    }

    for tentativa in range(_MAX_RETRIES):
        try:
            resp = requests.get(
                f'{_HIBP_API_BASE}/breachedaccount/{email}',
                headers=headers,
                params={'truncateResponse': 'false'},
                timeout=_REQUEST_TIMEOUT,
            )

            if resp.status_code == 200:
                breaches = resp.json()
                return {
                    'sucesso': True,
                    'breaches': breaches,
                    'total': len(breaches),
                    'sem_api_key': False,
                }
            elif resp.status_code == 404:
                # Nenhum breach encontrado
                return {
                    'sucesso': True,
                    'breaches': [],
                    'total': 0,
                    'sem_api_key': False,
                }
            elif resp.status_code == 401:
                return {
                    'sucesso': False,
                    'erro': 'API Key HIBP invalida',
                    'breaches': [],
                    'total': 0,
                    'sem_api_key': False,
                }
            elif resp.status_code == 429:
                # Rate limited — aguardar e tentar novamente
                retry_after = int(resp.headers.get('Retry-After', 2))
                logger.warning(
                    f"HIBP rate limit para {email}, retry em {retry_after}s"
                )
                time.sleep(retry_after)
                continue
            else:
                logger.error(
                    f"HIBP erro inesperado: status={resp.status_code} "
                    f"email={email}"
                )
                return {
                    'sucesso': False,
                    'erro': f'Erro HTTP {resp.status_code}',
                    'breaches': [],
                    'total': 0,
                    'sem_api_key': False,
                }

        except requests.Timeout:
            logger.warning(
                f"HIBP timeout para {email}, tentativa {tentativa + 1}"
            )
            if tentativa < _MAX_RETRIES - 1:
                time.sleep(2 ** tentativa)
                continue
            return {
                'sucesso': False,
                'erro': 'Timeout na API HIBP',
                'breaches': [],
                'total': 0,
                'sem_api_key': False,
            }
        except requests.RequestException as e:
            logger.error(f"HIBP erro de request para {email}: {e}")
            if tentativa < _MAX_RETRIES - 1:
                time.sleep(2 ** tentativa)
                continue
            return {
                'sucesso': False,
                'erro': str(e),
                'breaches': [],
                'total': 0,
                'sem_api_key': False,
            }

    return {
        'sucesso': False,
        'erro': 'Max retries atingido',
        'breaches': [],
        'total': 0,
        'sem_api_key': False,
    }


def verificar_senha_vazada(senha: str) -> Dict[str, Any]:
    """
    Verifica se senha apareceu em vazamentos via k-anonymity.

    SEGURANCA: Apenas os primeiros 5 caracteres do SHA-1 sao enviados.
    A senha NUNCA e transmitida ou armazenada.

    Args:
        senha: Senha para verificar (nao sera armazenada/logada)

    Returns:
        dict com 'vazada' (bool), 'ocorrencias' (int), 'erro' (str|None)
    """
    # Gerar SHA-1 da senha
    sha1_hash = hashlib.sha1(senha.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    _rate_limit()

    for tentativa in range(_MAX_RETRIES):
        try:
            resp = requests.get(
                f'{_HIBP_PASSWORD_API}/{prefix}',
                headers={'user-agent': _USER_AGENT},
                timeout=_REQUEST_TIMEOUT,
            )

            if resp.status_code == 200:
                # Buscar o suffix na resposta
                for linha in resp.text.splitlines():
                    partes = linha.strip().split(':')
                    if len(partes) == 2 and partes[0] == suffix:
                        return {
                            'vazada': True,
                            'ocorrencias': int(partes[1]),
                            'erro': None,
                        }
                return {
                    'vazada': False,
                    'ocorrencias': 0,
                    'erro': None,
                }
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 2))
                time.sleep(retry_after)
                continue
            else:
                return {
                    'vazada': False,
                    'ocorrencias': 0,
                    'erro': f'Erro HTTP {resp.status_code}',
                }

        except requests.Timeout:
            if tentativa < _MAX_RETRIES - 1:
                time.sleep(2 ** tentativa)
                continue
            return {
                'vazada': False,
                'ocorrencias': 0,
                'erro': 'Timeout na API HIBP',
            }
        except requests.RequestException as e:
            if tentativa < _MAX_RETRIES - 1:
                time.sleep(2 ** tentativa)
                continue
            return {
                'vazada': False,
                'ocorrencias': 0,
                'erro': str(e),
            }

    return {
        'vazada': False,
        'ocorrencias': 0,
        'erro': 'Max retries atingido',
    }


def obter_breaches_resumo(breaches: List[Dict]) -> List[Dict[str, Any]]:
    """
    Resume lista de breaches para exibicao.

    Args:
        breaches: Lista de breaches da API HIBP

    Returns:
        Lista simplificada com nome, data, dados comprometidos
    """
    resumos = []
    for b in breaches:
        resumos.append({
            'nome': b.get('Name', 'Desconhecido'),
            'dominio': b.get('Domain', ''),
            'data_breach': b.get('BreachDate', ''),
            'dados_comprometidos': b.get('DataClasses', []),
            'verificado': b.get('IsVerified', False),
            'descricao': b.get('Description', ''),
        })
    return resumos
