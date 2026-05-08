"""Fallback LLM para parsing de pedido VOE Q.P.A. quando determinístico falha.

Acionado pelo `pedido_service` quando confiança < 70% ou zero items extraídos.

Estratégia:
- Tentativa 1: Haiku 4.5 com schema JSON estruturado
- Tentativa 2: Sonnet 4.6 (se Haiku falhar parse JSON ou retornar incompleto)

Não usa caching: cada PDF é único; o prompt sistema é estático mas o conteúdo varia.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from decimal import Decimal
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

HAIKU_MODEL = 'claude-haiku-4-5-20251001'
SONNET_MODEL = 'claude-sonnet-4-6'

PROMPT_SYSTEM = """Você é um parser de PDFs de Pedido de Compras (sistema Consinco) emitidos pela Q.P.A. Distribuição LTDA para a Sendas Distribuidora (Assaí).

Cada PÁGINA do PDF representa UMA loja Sendas com header próprio + tabela de produtos.

Modelos comercializados (todos 1000W 60V 20AH autopropelidos):
- AUTOPROPELIDO X11 MINI 1000W 60V 20AH (código Q.P.A. típico: 1342056)
- AUTOPROPELIDO DOT 1000W 60V 20AH (código Q.P.A. típico: 1342059)
- AUTOPROPELIDO SOL 1000W 60V 20AH (código Q.P.A. típico: 1342063)

Retorne JSON puro (sem markdown fence, sem comentários) seguindo o schema:

{
  "numero_pedido": "21439695/L",
  "data_emissao": "DD/MM/YYYY",
  "previsao_entrega": "DD/MM/YYYY",
  "fornecedor_cnpj": "53780554000115",
  "lojas": [
    {
      "numero_loja": "12",
      "razao_social_loja": "SENDAS DISTRIBUIDORA S/A LJ12",
      "cnpj_loja": "06.057.223/0272-90",
      "cidade_loja": "JUNDIAI",
      "uf_loja": "SP",
      "itens": [
        {
          "codigo_qpa": "1342056",
          "descricao": "AUTOPROPELIDO X11 MINI 1000W 60V 20AH",
          "qtd": 10,
          "valor_unitario": 7100.00,
          "valor_total": 71000.00
        }
      ]
    }
  ]
}

REGRAS:
- Use ponto como separador decimal (não vírgula).
- numero_loja = só os dígitos (sem o prefixo "LJ").
- Se um campo não existir, omita-o (não use null).
- Não inclua qualquer texto antes ou depois do JSON.
"""


class QpaPedidoLlmFallbackError(Exception):
    """Erro irrecuperável do fallback LLM."""


def parse_via_llm(pdf_bytes: bytes) -> Dict[str, Any]:
    """Parseia PDF via LLM. Tenta Haiku, depois Sonnet em fallback.

    Retorna mesmo formato lista-flat do `QpaPedidoExtractor.extract()` para
    o `pedido_service` poder consumir uniformemente.
    """
    try:
        import anthropic
    except ImportError:
        raise QpaPedidoLlmFallbackError("Pacote 'anthropic' não instalado")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise QpaPedidoLlmFallbackError("ANTHROPIC_API_KEY não configurada")

    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.b64encode(pdf_bytes).decode('ascii')

    # Tentativa 1: Haiku
    try:
        data = _chamar_llm(client, pdf_b64, HAIKU_MODEL)
        items = _converter_para_lista_flat(data, modelo='HAIKU')
        if items:
            return {'parser_usado': 'LLM_HAIKU', 'items': items}
    except Exception as e:
        logger.warning(f'Haiku fallback falhou: {e}')

    # Tentativa 2: Sonnet
    data = _chamar_llm(client, pdf_b64, SONNET_MODEL)
    items = _converter_para_lista_flat(data, modelo='SONNET')
    if items:
        return {'parser_usado': 'LLM_SONNET', 'items': items}

    raise QpaPedidoLlmFallbackError("Haiku e Sonnet retornaram zero items")


def _chamar_llm(client, pdf_b64: str, model: str) -> Dict[str, Any]:
    """Chama Anthropic Messages API com PDF como document block."""
    response = client.messages.create(
        model=model,
        max_tokens=8192,
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
                    'text': 'Extraia o pedido completo em JSON.',
                },
            ],
        }],
    )

    raw = response.content[0].text.strip()
    json_str = _extrair_json(raw)
    return json.loads(json_str)


def _extrair_json(raw: str) -> str:
    """Remove markdown fence se presente; isola primeiro objeto JSON."""
    raw = raw.strip()
    if raw.startswith('```'):
        m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL)
        if m:
            return m.group(1)
    # Procura primeiro { e último } balanceado
    inicio = raw.find('{')
    if inicio < 0:
        raise QpaPedidoLlmFallbackError(f"Sem JSON em resposta: {raw[:200]}")
    return raw[inicio:]


def _converter_para_lista_flat(data: Dict, modelo: str) -> List[Dict]:
    """Converte schema JSON estruturado para lista-flat de items.

    Mesmo formato que `QpaPedidoExtractor.extract()` retorna.
    """
    items = []
    numero_pedido = data.get('numero_pedido')
    data_emissao = data.get('data_emissao')
    previsao = data.get('previsao_entrega')
    fornecedor_cnpj = data.get('fornecedor_cnpj')

    for loja in data.get('lojas', []):
        loja_dados = {
            'numero_loja': str(loja.get('numero_loja', '')).strip(),
            'razao_social_loja': loja.get('razao_social_loja'),
            'cnpj_loja': loja.get('cnpj_loja'),
            'cidade_loja': loja.get('cidade_loja'),
            'uf_loja': loja.get('uf_loja'),
        }
        for item in loja.get('itens', []):
            items.append({
                'numero_pedido': numero_pedido,
                'data_emissao': data_emissao,
                'previsao_entrega': previsao,
                'fornecedor_cnpj': fornecedor_cnpj,
                **loja_dados,
                'codigo_qpa': str(item.get('codigo_qpa', '')).strip(),
                'descricao': item.get('descricao'),
                'qtd': int(item.get('qtd', 0)),
                'valor_unitario': Decimal(str(item.get('valor_unitario', 0))),
                'valor_total': Decimal(str(item.get('valor_total', 0))),
            })
    return items
