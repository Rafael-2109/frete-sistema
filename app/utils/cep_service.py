"""Resolucao de CEP -> {cidade, uf, codigo_ibge} via ViaCEP.

ViaCEP (https://viacep.com.br/ws/{cep}/json/) devolve o campo `ibge` (codigo IBGE
do municipio, 7 digitos) — compativel diretamente com `Cidade.codigo_ibge`
(String). Sem dependencia nova: `requests` ja esta em requirements.

Uso tipico (Cotacao Rapida CarVia): CEP -> cidade/uf -> codigo_ibge ->
`CarviaCidadeAtendida` (uf_origem=SP).
"""

import logging
import re
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

VIACEP_URL = 'https://viacep.com.br/ws/{cep}/json/'
# Conservador: a chamada e sincrona dentro de uma rota interativa.
TIMEOUT_S = 5


def normalizar_cep(cep: str) -> Optional[str]:
    """Extrai os 8 digitos do CEP (aceita formatado/com hifen). None se invalido."""
    if not cep:
        return None
    digitos = re.sub(r'\D', '', str(cep))
    return digitos if len(digitos) == 8 else None


def resolver_cep(cep: str) -> Optional[Dict]:
    """Resolve um CEP para `{cep, cidade, uf, codigo_ibge}`.

    Retorna None (nunca levanta) se o CEP for invalido, nao encontrado, ou se a
    API externa falhar/expirar — o caller decide a UX (a tela cai no preenchimento
    manual de cidade/UF).
    """
    cep_limpo = normalizar_cep(cep)
    if not cep_limpo:
        return None

    try:
        resp = requests.get(VIACEP_URL.format(cep=cep_limpo), timeout=TIMEOUT_S)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning("Falha ao consultar CEP %s no ViaCEP: %s", cep_limpo, e)
        return None

    # ViaCEP devolve {"erro": true} para CEP inexistente.
    if not isinstance(data, dict) or data.get('erro'):
        return None

    cidade = (data.get('localidade') or '').strip()
    uf = (data.get('uf') or '').strip().upper()
    codigo_ibge = str(data.get('ibge') or '').strip()

    if not cidade or not uf:
        return None

    return {
        'cep': cep_limpo,
        'cidade': cidade,
        'uf': uf,
        'codigo_ibge': codigo_ibge or None,
    }
