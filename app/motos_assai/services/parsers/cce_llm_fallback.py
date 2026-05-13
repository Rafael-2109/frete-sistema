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

# P2 fix 12 (2026-05-13): single source of truth — importa do extractor para
# evitar drift de versoes. Antes ambos arquivos definiam CONFIANCA_LIMIAR = 0.80
# independentemente.
from app.motos_assai.services.parsers.cce_pdf_extractor import (  # noqa: E402
    CONFIANCA_LIMIAR,
    TIPO_CHASSI,
    TIPO_DUPLICATAS,
    TIPO_ENDERECO,
    TIPO_OUTRO,
)

HAIKU_MODEL = 'claude-haiku-4-5-20251001'
SONNET_MODEL = 'claude-sonnet-4-6'

_TIPOS_VALIDOS = {TIPO_CHASSI, TIPO_DUPLICATAS, TIPO_ENDERECO, TIPO_OUTRO}


PROMPT_SYSTEM = """Voce e um parser de PDFs de Carta de Correcao Eletronica (CCe) de NF-e.

Uma CCe corrige dados de uma NF-e ja emitida. Existem 3 subtipos de correcao
observados em PDFs brasileiros (formato Q.P.A. Distribuicao e formato Motochefe):

1) CHASSI: erro de digitacao no chassi de moto na NF original. Layout tem
   linhas "SAINDO: MODELO CHASSI COR" e "ENTRANDO: MODELO CHASSI COR".
   Chassis brasileiros tem 13 a 17 caracteres alfanumericos (NAO assuma 17 fixo).
2) DUPLICATAS: ajuste em duplicatas (numero, vencimento, valor).
3) ENDERECO: correcao de endereco de entrega.

Retorne JSON puro (sem markdown fence, sem comentarios) seguindo o schema:

{
  "numero_cce": "CCe-1-NF1729",
  "numero_nf_referenciada": "1729",
  "chave_nfe": "35260453780554000115550010000017291644542738",
  "protocolo_cce": "135261639015279",
  "tipo_correcao": "CHASSI",
  "chassis_corrigidos": [
    ["CHASSI_ANTIGO", "CHASSI_NOVO"]
  ],
  "chassis_detalhes": [
    {
      "modelo": "DOT",
      "chassi_antigo": "LA2025SA110004195",
      "chassi_novo": "LA2025SA110004319",
      "cor_antiga": "BRANCO",
      "cor_nova": "BRANCO"
    }
  ],
  "duplicatas": [],
  "endereco_corrigido": "",
  "data_emissao": "30/04/2026",
  "confianca": 0.95
}

REGRAS:
- tipo_correcao DEVE ser exatamente um destes: "CHASSI", "DUPLICATAS", "ENDERECO", "OUTRO".
- Se tipo_correcao = "CHASSI": preencha chassis_corrigidos E chassis_detalhes.
  chassis_corrigidos e lista de pares [antigo, novo]. chassis_detalhes inclui modelo+cores.
- Se tipo_correcao = "DUPLICATAS": preencha duplicatas com [{numero, vencimento, valor}].
- Se tipo_correcao = "ENDERECO": preencha endereco_corrigido com texto livre.
- Se um campo nao se aplica ao tipo, retorne lista vazia [] ou string vazia "".
- Chassis: 13-17 caracteres alfanumericos (SOL pode ter 15 chars so digitos).
- numero_nf_referenciada SEM zeros a esquerda ("1729" e nao "001729").
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
        if normalizado.get('numero_nf_referenciada'):
            # Se tipo CHASSI mas sem chassis ou tipo desconhecido — escalar
            tipo = normalizado.get('tipo_correcao')
            if tipo == TIPO_CHASSI and not normalizado.get('chassis_corrigidos'):
                logger.info('Haiku CCe retornou CHASSI sem chassis — escalando para Sonnet')
            else:
                return normalizado
        else:
            logger.info('Haiku CCe retornou sem numero_nf — escalando para Sonnet')
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
    # tipo_correcao — sanitizar
    tipo_raw = (data.get('tipo_correcao') or '').strip().upper()
    if tipo_raw not in _TIPOS_VALIDOS:
        # Inferir a partir do conteudo
        if data.get('chassis_corrigidos') or data.get('chassis_detalhes'):
            tipo_correcao = TIPO_CHASSI
        elif data.get('duplicatas'):
            tipo_correcao = TIPO_DUPLICATAS
        elif data.get('endereco_corrigido'):
            tipo_correcao = TIPO_ENDERECO
        else:
            tipo_correcao = TIPO_OUTRO
    else:
        tipo_correcao = tipo_raw

    # chassis_corrigidos — aceita lista de tuplas, lista de listas ou de dicts
    chassis_raw = data.get('chassis_corrigidos') or []
    chassis_corrigidos: List[Tuple[str, str]] = []
    for par in chassis_raw:
        if isinstance(par, (list, tuple)) and len(par) == 2:
            antigo, novo = par
            if antigo and novo:
                chassis_corrigidos.append(
                    (str(antigo).strip().upper(), str(novo).strip().upper())
                )
        elif isinstance(par, dict):
            antigo = par.get('antigo') or par.get('chassi_antigo')
            novo = par.get('novo') or par.get('chassi_novo')
            if antigo and novo:
                chassis_corrigidos.append(
                    (str(antigo).strip().upper(), str(novo).strip().upper())
                )

    # chassis_detalhes — pode vir do LLM ou ser derivado de chassis_corrigidos
    detalhes_raw = data.get('chassis_detalhes') or []
    chassis_detalhes: List[Dict[str, Any]] = []
    for d in detalhes_raw:
        if not isinstance(d, dict):
            continue
        chassis_detalhes.append({
            'modelo': (d.get('modelo') or '').upper() or None,
            'chassi_antigo': (d.get('chassi_antigo') or '').upper() or None,
            'chassi_novo': (d.get('chassi_novo') or '').upper() or None,
            'cor_antiga': (d.get('cor_antiga') or '').upper() or None,
            'cor_nova': (d.get('cor_nova') or '').upper() or None,
        })
    if not chassis_detalhes and chassis_corrigidos:
        # LLM nao retornou detalhes, mas retornou pares — preencher minimo
        for antigo, novo in chassis_corrigidos:
            chassis_detalhes.append({
                'modelo': None,
                'chassi_antigo': antigo,
                'chassi_novo': novo,
                'cor_antiga': None,
                'cor_nova': None,
            })

    # duplicatas
    duplicatas_raw = data.get('duplicatas') or []
    duplicatas: List[Dict[str, Any]] = []
    for d in duplicatas_raw:
        if not isinstance(d, dict):
            continue
        duplicatas.append({
            'numero': d.get('numero'),
            'vencimento': d.get('vencimento'),
            'valor': d.get('valor'),
        })

    # numero_nf_referenciada — strip de zeros a esquerda
    numero_nf = data.get('numero_nf_referenciada')
    if numero_nf:
        numero_nf = str(numero_nf).lstrip('0') or '0'

    return {
        'numero_cce': data.get('numero_cce'),
        'numero_nf_referenciada': numero_nf,
        'chave_nfe': data.get('chave_nfe'),
        'protocolo_cce': data.get('protocolo_cce'),
        'tipo_correcao': tipo_correcao,
        'chassis_corrigidos': chassis_corrigidos,
        'chassis_detalhes': chassis_detalhes,
        'duplicatas': duplicatas,
        'endereco_corrigido': (data.get('endereco_corrigido') or '')[:500],
        'texto_correcao_bruto': (data.get('texto_correcao_bruto') or '')[:2000],
        'justificativa': data.get('justificativa', '') or '',
        'data_emissao': data.get('data_emissao'),
        # LLM = alta confianca por default; usa o valor retornado se for razoavel
        'confianca': max(
            CONFIANCA_LIMIAR + 0.05,  # acima do limiar para nao re-disparar fallback
            float(data.get('confianca') or 0.85),
        ),
        'parser_usado': f'LLM_{modelo}',
        'formato_detectado': data.get('formato_detectado'),
    }
