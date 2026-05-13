"""Fallback LLM para parser CCe (Plano 4 Task 8).

Acionado quando cce_pdf_extractor.confianca < CONFIANCA_LIMIAR (0.80).
Escalada: Haiku 4.5 -> Sonnet 4.6 (mesmo padrao de qpa_pedido_llm_fallback).

Fix N-M1: try/except em json.loads (LLM pode retornar markdown ou texto solto).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Dict, Any, List, Tuple


logger = logging.getLogger(__name__)

CONFIANCA_LIMIAR = 0.80  # mesmo do extractor deterministico
HAIKU_MODEL = 'claude-haiku-4-5-20251001'
SONNET_MODEL = 'claude-sonnet-4-6'


PROMPT_SYSTEM = """Voce e um parser de PDFs de Carta de Correcao Eletronica (CCe) de NF-e.

Uma CCe corrige dados de uma NF-e ja emitida — frequentemente substituindo chassis
de motos quando houve erro de digitacao no momento da emissao da NF original.

Retorne JSON puro (sem markdown fence, sem comentarios) seguindo o schema:

{
  "numero_cce": "CCe-001-2026",
  "numero_nf_referenciada": "12345",
  "chassis_corrigidos": [
    ["CHASSI_ANTIGO_17_CHARS", "CHASSI_NOVO_17_CHARS"]
  ],
  "justificativa": "Erro de digitacao do chassi no momento da emissao da NF original.",
  "data_emissao": "DD/MM/AAAA",
  "confianca": 0.95
}

REGRAS:
- Chassis VIN tem 17 caracteres alfanumericos (sem I, O, Q).
- chassis_corrigidos e LISTA DE PARES (lista de listas), cada par [antigo, novo].
- Se nao houver chassis sendo trocados, retorne lista vazia [].
- Se um campo nao existir no PDF, omita-o (nao use null).
- confianca 0.0-1.0: quao certo voce esta da extracao.
- Nao inclua qualquer texto antes ou depois do JSON.
"""


class CceLlmFallbackError(Exception):
    """Erro irrecuperavel do fallback LLM."""


def extrair_cce_via_llm(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extrai dados de CCe via LLM. Tenta Haiku, depois Sonnet em fallback.

    Args:
        pdf_bytes: bytes do PDF da CCe.

    Returns:
        dict com mesmo schema que `cce_pdf_extractor.extrair_cce()`.

    Raises:
        CceLlmFallbackError: ambos modelos falharam.
    """
    try:
        import anthropic
    except ImportError:
        raise CceLlmFallbackError("Pacote 'anthropic' nao instalado")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise CceLlmFallbackError('ANTHROPIC_API_KEY nao configurada')

    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    # Tentativa 1: Haiku
    try:
        data = _chamar_llm(client, pdf_b64, HAIKU_MODEL)
        normalizado = _normalizar_resposta(data, modelo='HAIKU')
        if normalizado.get('chassis_corrigidos') or normalizado.get('numero_nf_referenciada'):
            return normalizado
        logger.info('Haiku CCe retornou vazio — escalando para Sonnet')
    except Exception as e:
        logger.warning(f'Haiku CCe fallback falhou: {e}')

    # Tentativa 2: Sonnet
    try:
        data = _chamar_llm(client, pdf_b64, SONNET_MODEL)
        normalizado = _normalizar_resposta(data, modelo='SONNET')
        if normalizado.get('numero_nf_referenciada'):
            return normalizado
        raise CceLlmFallbackError('Sonnet retornou JSON sem numero_nf_referenciada')
    except CceLlmFallbackError:
        raise
    except Exception as e:
        raise CceLlmFallbackError(f'Sonnet falhou: {e}')


def _chamar_llm(client, pdf_b64: str, model: str) -> Dict[str, Any]:
    """Chama Anthropic Messages API com PDF como document block.

    N-M1 fix: try/except em json.loads (LLM pode retornar markdown).
    """
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=PROMPT_SYSTEM,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'document',
                    'source': {
                        'type': 'base64',
                        'media_type': 'application/pdf',
                        'data': pdf_b64,
                    },
                },
                {
                    'type': 'text',
                    'text': 'Extraia a CCe completa em JSON.',
                },
            ],
        }],
    )

    raw = response.content[0].text.strip()
    json_str = _extrair_json(raw)

    # N-M1 fix: try/except em json.loads — LLM pode retornar markdown ou texto solto
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Tenta corrigir aspas simples -> duplas (erro comum)
        try:
            return json.loads(json_str.replace("'", '"'))
        except json.JSONDecodeError:
            raise CceLlmFallbackError(
                f'LLM retornou JSON invalido: {e}. Resposta: {raw[:300]}'
            )


def _extrair_json(raw: str) -> str:
    """Remove markdown fence se presente; isola primeiro objeto JSON."""
    raw = raw.strip()
    if raw.startswith('```'):
        m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL)
        if m:
            return m.group(1)
    inicio = raw.find('{')
    if inicio < 0:
        raise CceLlmFallbackError(f'Sem JSON em resposta: {raw[:200]}')
    return raw[inicio:]


def _normalizar_resposta(data: Dict[str, Any], modelo: str) -> Dict[str, Any]:
    """Normaliza resposta LLM para o schema canonico do parser deterministico."""
    chassis_raw = data.get('chassis_corrigidos') or []
    chassis_corrigidos: List[Tuple[str, str]] = []
    for par in chassis_raw:
        if isinstance(par, (list, tuple)) and len(par) == 2:
            antigo, novo = par
            if antigo and novo:
                chassis_corrigidos.append((str(antigo).strip().upper(), str(novo).strip().upper()))
        elif isinstance(par, dict):
            antigo = par.get('antigo') or par.get('chassi_antigo')
            novo = par.get('novo') or par.get('chassi_novo')
            if antigo and novo:
                chassis_corrigidos.append((str(antigo).strip().upper(), str(novo).strip().upper()))

    return {
        'numero_cce': data.get('numero_cce'),
        'numero_nf_referenciada': data.get('numero_nf_referenciada'),
        'chassis_corrigidos': chassis_corrigidos,
        'justificativa': data.get('justificativa', '') or '',
        'data_emissao': data.get('data_emissao'),
        'confianca': float(data.get('confianca', 0.85)),  # LLM = alta confianca por default
        'parser_usado': f'LLM_{modelo}',
    }
