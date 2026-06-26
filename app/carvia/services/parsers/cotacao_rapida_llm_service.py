"""Extrai MOTOS + QTD + REGIAO de um PDF/imagem de cotacao via Claude Haiku.

Segue o padrao canonico de chamada LLM do repo
(`app/motos_assai/services/parsers/qpa_pedido_llm_fallback.py` para PDF e
`app/hora/services/parsers/pedido_imagem_parser.py` para imagem): Haiku 4.5 com
fallback Sonnet 4.6; PDF = document block, imagem = image block.

A lista de modelos+categorias CADASTRADOS e injetada no prompt para o LLM so
devolver nomes que existem; os nomes retornados sao normalizados para
`CarviaModeloMoto` via `MotoRecognitionService.resolver_modelo_em_lista`.

Saida: `{'motos': [{modelo_id, modelo_nome, quantidade, texto_original,
reconhecido}], 'regiao': {cidade, uf, cep}, 'parser_usado': str}`.
"""

import base64
import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

HAIKU_MODEL = 'claude-haiku-4-5-20251001'
SONNET_MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 4096

MIME_PDF = 'application/pdf'
MIME_IMAGENS = ('image/jpeg', 'image/png', 'image/webp')
MIME_ACEITOS = (MIME_PDF,) + MIME_IMAGENS


class CotacaoRapidaLlmError(Exception):
    """Erro irrecuperavel da extracao via LLM (mensagem amigavel para a rota)."""


def extrair_motos_regiao(file_bytes: bytes, mime_type: str, modelos: List) -> Dict:
    """Le um PDF/imagem de cotacao e devolve motos + regiao.

    Args:
        file_bytes: conteudo binario do arquivo.
        mime_type: MIME (application/pdf | image/jpeg|png|webp).
        modelos: lista de `CarviaModeloMoto` ativos (para o prompt + normalizacao).

    Levanta:
        CotacaoRapidaLlmError: SDK/API ausente, MIME nao suportado, ou o LLM
        nao retornou nada utilizavel.
    """
    if not file_bytes:
        raise CotacaoRapidaLlmError('Arquivo vazio.')
    if mime_type not in MIME_ACEITOS:
        raise CotacaoRapidaLlmError(
            f'Formato nao suportado: {mime_type}. '
            f'Aceitos: PDF, JPG, PNG, WEBP.'
        )

    try:
        import anthropic
    except ImportError as exc:
        raise CotacaoRapidaLlmError("Biblioteca 'anthropic' nao instalada.") from exc

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise CotacaoRapidaLlmError('ANTHROPIC_API_KEY nao configurada.')

    client = anthropic.Anthropic(api_key=api_key)
    bloco = _bloco_arquivo(file_bytes, mime_type)
    prompt_system = _montar_prompt_system(modelos)

    # Haiku -> Sonnet
    data = None
    parser_usado = None
    for model in (HAIKU_MODEL, SONNET_MODEL):
        try:
            data = _chamar_llm(client, bloco, prompt_system, model)
            if data is not None and data.get('motos'):
                parser_usado = model
                break
        except Exception as e:  # noqa: BLE001 — tenta o proximo modelo
            logger.warning('Cotacao Rapida LLM (%s) falhou: %s', model, e)

    if data is None:
        raise CotacaoRapidaLlmError(
            'Nao foi possivel ler o arquivo (Haiku e Sonnet falharam).'
        )

    return _normalizar(data, modelos, parser_usado)


# --------------------------------------------------------------------------- #
# Internos
# --------------------------------------------------------------------------- #

def _bloco_arquivo(file_bytes: bytes, mime_type: str) -> Dict:
    """Bloco de conteudo Anthropic: document (PDF) ou image."""
    b64 = base64.b64encode(file_bytes).decode('ascii')
    if mime_type == MIME_PDF:
        return {
            'type': 'document',
            'source': {'type': 'base64', 'media_type': MIME_PDF, 'data': b64},
        }
    return {
        'type': 'image',
        'source': {'type': 'base64', 'media_type': mime_type, 'data': b64},
    }


def _montar_prompt_system(modelos: List) -> str:
    """System prompt com a lista de modelos+categorias cadastrados."""
    linhas = []
    for m in modelos:
        cat = getattr(getattr(m, 'categoria', None), 'nome', None)
        nome = getattr(m, 'nome', None)
        if nome:
            linhas.append(f'- {nome}' + (f' (categoria: {cat})' if cat else ''))
    catalogo = '\n'.join(linhas) if linhas else '(nenhum modelo cadastrado)'

    return (
        'Voce extrai dados de um pedido/cotacao de transporte de MOTOS de um '
        'documento (PDF ou imagem). Devolva EXCLUSIVAMENTE um JSON valido '
        '(sem markdown, sem comentarios, sem texto antes/depois).\n\n'
        'Modelos de moto cadastrados (use SOMENTE estes nomes no campo '
        '"modelo"; se um item do documento corresponder a um destes, use o '
        'nome cadastrado exatamente como abaixo):\n'
        f'{catalogo}\n\n'
        'Schema:\n'
        '{\n'
        '  "motos": [{"modelo": "<nome cadastrado>", "quantidade": <int>}],\n'
        '  "regiao": {"cidade": "<nome>", "uf": "<UF 2 letras>", "cep": "<CEP ou vazio>"}\n'
        '}\n\n'
        'REGRAS:\n'
        '- Agregue a quantidade por modelo (se o mesmo modelo aparece em varias '
        'linhas, some).\n'
        '- "regiao" e o DESTINO da entrega (cidade/UF e, se houver, o CEP).\n'
        '- Se um campo nao existir, use string vazia "" (ou omita o item de moto '
        'se nao houver modelo/quantidade).\n'
        '- NAO invente modelos fora da lista; se nao reconhecer, devolva o texto '
        'do documento no campo "modelo" mesmo assim (sera tratado depois).'
    )


def _chamar_llm(client, bloco: Dict, prompt_system: str, model: str) -> Optional[Dict]:
    """Chama a Messages API e devolve o JSON parseado (ou levanta)."""
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=prompt_system,
        messages=[{
            'role': 'user',
            'content': [
                bloco,
                {'type': 'text', 'text': 'Extraia as motos e a regiao em JSON.'},
            ],
        }],
    )
    if not response.content:
        return None
    raw = response.content[0].text
    if not isinstance(raw, str) or not raw.strip():
        return None
    return json.loads(_extrair_json(raw))


def _extrair_json(raw: str) -> str:
    """Isola o objeto JSON da resposta (remove cercas markdown)."""
    raw = raw.strip()
    m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL)
    if m:
        return m.group(1)
    inicio = raw.find('{')
    if inicio < 0:
        raise CotacaoRapidaLlmError(f'Resposta sem JSON: {raw[:200]}')
    return raw[inicio:]


def _normalizar(data: Dict, modelos: List, parser_usado: Optional[str]) -> Dict:
    """Normaliza nomes de modelo para CarviaModeloMoto e agrega a regiao."""
    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService

    motos_out = []
    for moto in data.get('motos', []) or []:
        texto = str(moto.get('modelo') or '').strip()
        try:
            qtd = int(moto.get('quantidade') or 0)
        except (TypeError, ValueError):
            qtd = 0
        if not texto or qtd <= 0:
            continue

        modelo = MotoRecognitionService.resolver_modelo_em_lista(texto, modelos)
        motos_out.append({
            'modelo_id': modelo.id if modelo else None,
            'modelo_nome': modelo.nome if modelo else None,
            'quantidade': qtd,
            'texto_original': texto,
            'reconhecido': modelo is not None,
        })

    regiao_raw = data.get('regiao') or {}
    regiao = {
        'cidade': (str(regiao_raw.get('cidade') or '').strip() or None),
        'uf': (str(regiao_raw.get('uf') or '').strip().upper() or None),
        'cep': (str(regiao_raw.get('cep') or '').strip() or None),
    }

    return {'motos': motos_out, 'regiao': regiao, 'parser_usado': parser_usado}
