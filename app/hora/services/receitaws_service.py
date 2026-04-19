"""Integração com ReceitaWS para autopreencher cadastro de loja.

Endpoint público: https://receitaws.com.br/v1/cnpj/{cnpj}
Rate limit no plano gratuito: ~3 req/min. Timeout conservador (10s).

Retorna payload normalizado com chaves correspondentes aos campos de HoraLoja.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

RECEITAWS_URL = 'https://receitaws.com.br/v1/cnpj/{cnpj}'
TIMEOUT_S = 10


class ReceitaWSError(Exception):
    """Falha ao consultar ReceitaWS (rede, rate limit, CNPJ inválido)."""


def _sanitizar_cnpj(cnpj: str) -> str:
    return ''.join(c for c in (cnpj or '') if c.isdigit())


def _parse_data_br(s: Optional[str]) -> Optional[date]:
    """Parseia 'DD/MM/YYYY' → date."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None


def consultar_cnpj(cnpj: str) -> Dict:
    """Consulta ReceitaWS e retorna dict normalizado para HoraLoja.

    Args:
        cnpj: string com ou sem formatação.

    Returns:
        Dict com chaves: cnpj, razao_social, nome_fantasia, situacao_cadastral,
            data_abertura, porte, natureza_juridica, atividade_principal,
            logradouro, numero, complemento, bairro, cep, cidade, uf,
            telefone, email.

    Raises:
        ReceitaWSError: CNPJ inválido, timeout, rate limit ou resposta inesperada.
    """
    digitos = _sanitizar_cnpj(cnpj)
    if len(digitos) != 14:
        raise ReceitaWSError(f'CNPJ inválido (esperado 14 dígitos): {cnpj!r}')

    url = RECEITAWS_URL.format(cnpj=digitos)
    try:
        resp = requests.get(url, timeout=TIMEOUT_S, headers={'User-Agent': 'frete_sistema/hora'})
    except requests.Timeout:
        raise ReceitaWSError('ReceitaWS: timeout (>10s). Tente novamente em alguns segundos.')
    except requests.RequestException as exc:
        raise ReceitaWSError(f'ReceitaWS: erro de rede — {exc}')

    if resp.status_code == 429:
        raise ReceitaWSError('ReceitaWS: limite de requisições excedido (3/min). Aguarde 1 minuto.')
    if resp.status_code != 200:
        raise ReceitaWSError(f'ReceitaWS: HTTP {resp.status_code} — {resp.text[:200]}')

    try:
        data = resp.json()
    except ValueError:
        raise ReceitaWSError('ReceitaWS: resposta não-JSON.')

    if data.get('status') == 'ERROR':
        raise ReceitaWSError(f'ReceitaWS: {data.get("message", "erro desconhecido")}')

    # Atividade principal é lista de dicts {code, text}
    atividade = ''
    ativ_lista = data.get('atividade_principal') or []
    if ativ_lista and isinstance(ativ_lista, list):
        primeira = ativ_lista[0] or {}
        atividade = f"{primeira.get('code', '')} — {primeira.get('text', '')}".strip(' —')

    cep_raw = (data.get('cep') or '').replace('.', '').replace('-', '').strip()
    if len(cep_raw) == 8:
        cep_formatado = f'{cep_raw[:5]}-{cep_raw[5:]}'
    else:
        cep_formatado = data.get('cep') or ''

    return {
        'cnpj': digitos,
        'razao_social': (data.get('nome') or '').strip() or None,
        'nome_fantasia': (data.get('fantasia') or '').strip() or None,
        'situacao_cadastral': (data.get('situacao') or '').strip() or None,
        'data_abertura': _parse_data_br(data.get('abertura')),
        'porte': (data.get('porte') or '').strip() or None,
        'natureza_juridica': (data.get('natureza_juridica') or '').strip() or None,
        'atividade_principal': atividade or None,

        'logradouro': (data.get('logradouro') or '').strip() or None,
        'numero': (data.get('numero') or '').strip() or None,
        'complemento': (data.get('complemento') or '').strip() or None,
        'bairro': (data.get('bairro') or '').strip() or None,
        'cep': cep_formatado or None,
        'cidade': (data.get('municipio') or '').strip() or None,
        'uf': (data.get('uf') or '').strip().upper() or None,

        'telefone': (data.get('telefone') or '').strip() or None,
        'email': (data.get('email') or '').strip() or None,
    }
