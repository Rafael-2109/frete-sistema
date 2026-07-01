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
SONNET_MODEL = 'claude-sonnet-5'
MAX_TOKENS = 4096

MIME_PDF = 'application/pdf'
MIME_IMAGENS = ('image/jpeg', 'image/png', 'image/webp')
MIME_ACEITOS = (MIME_PDF,) + MIME_IMAGENS


class CotacaoRapidaLlmError(Exception):
    """Erro irrecuperavel da extracao via LLM (mensagem amigavel para a rota)."""


def extrair_motos_regiao(
    file_bytes: bytes, mime_type: str, modelos: List, filename: str = None
) -> Dict:
    """Le um PDF/imagem de cotacao e devolve motos + regiao.

    Args:
        file_bytes: conteudo binario do arquivo.
        mime_type: MIME do cliente (pode vir vazio/octet-stream — resolvido por
            extensao/magic bytes como fallback).
        modelos: lista de `CarviaModeloMoto` ativos (para o prompt + normalizacao).
        filename: nome do arquivo (fallback de deteccao por extensao).

    Levanta:
        CotacaoRapidaLlmError: SDK/API ausente, formato nao suportado, ou o LLM
        nao retornou nada utilizavel.
    """
    if not file_bytes:
        raise CotacaoRapidaLlmError('Arquivo vazio.')

    # mime do cliente nem sempre e confiavel (octet-stream/vazio em drag-drop):
    # resolve por mime -> extensao -> magic bytes.
    tipo = _resolver_tipo(file_bytes, mime_type, filename)

    try:
        import anthropic
    except ImportError as exc:
        raise CotacaoRapidaLlmError("Biblioteca 'anthropic' nao instalada.") from exc

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise CotacaoRapidaLlmError('ANTHROPIC_API_KEY nao configurada.')

    client = anthropic.Anthropic(api_key=api_key)
    bloco = _bloco_arquivo(file_bytes, tipo)
    prompt_system = _montar_prompt_system(modelos)

    # Haiku -> Sonnet. Aceita a 1a resposta com JSON bem-formado (mesmo motos
    # vazias = "nenhuma moto no documento"); so escala para Sonnet em erro/parse-fail.
    data = None
    parser_usado = None
    erros = []
    for model in (HAIKU_MODEL, SONNET_MODEL):
        try:
            data = _chamar_llm(client, bloco, prompt_system, model)
            parser_usado = model
            break
        except Exception as e:  # noqa: BLE001 — tenta o proximo modelo
            erros.append(f'{model}: {e}')
            logger.warning('Cotacao Rapida LLM (%s) falhou: %s', model, e)

    if data is None:
        raise CotacaoRapidaLlmError(
            'Nao foi possivel ler o arquivo (Haiku e Sonnet falharam). '
            + ' | '.join(erros)
        )

    return _normalizar(data, modelos, parser_usado)


# --------------------------------------------------------------------------- #
# Internos
# --------------------------------------------------------------------------- #

# Assinaturas (magic bytes) para deteccao robusta quando o mime do cliente falha.
def _resolver_tipo(file_bytes: bytes, mime_type: str, filename: str) -> str:
    """Resolve o MIME efetivo: mime do cliente -> extensao -> magic bytes."""
    mt = (mime_type or '').lower().split(';')[0].strip()
    if mt in MIME_ACEITOS:
        return mt

    ext = ''
    if filename and '.' in filename:
        ext = filename.rsplit('.', 1)[-1].lower()
    ext_map = {
        'pdf': MIME_PDF, 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png', 'webp': 'image/webp',
    }
    if ext in ext_map:
        return ext_map[ext]

    head = file_bytes[:16]
    if head[:4] == b'%PDF':
        return MIME_PDF
    if head[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if head[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if head[:4] == b'RIFF' and file_bytes[8:12] == b'WEBP':
        return 'image/webp'

    raise CotacaoRapidaLlmError(
        f'Formato nao suportado (mime={mime_type or "?"}). Aceitos: PDF, JPG, PNG, WEBP.'
    )


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
        raise CotacaoRapidaLlmError('resposta vazia do modelo')
    raw = response.content[0].text
    if not isinstance(raw, str) or not raw.strip():
        raise CotacaoRapidaLlmError('resposta nao-textual do modelo')
    return json.loads(_extrair_json(raw))


def _extrair_json(raw: str) -> str:
    """Isola o objeto JSON da resposta (cerca markdown, preambulo E postambulo)."""
    raw = raw.strip()
    m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL)
    if m:
        return m.group(1)
    # Recorta do primeiro '{' ao ULTIMO '}' — cobre texto antes E depois do JSON
    # (Haiku as vezes adiciona "Espero ter ajudado." apos o objeto -> 'Extra data').
    inicio = raw.find('{')
    fim = raw.rfind('}')
    if inicio < 0 or fim < inicio:
        raise CotacaoRapidaLlmError(f'Resposta sem JSON: {raw[:200]}')
    return raw[inicio:fim + 1]


def _normalizar(data: Dict, modelos: List, parser_usado: Optional[str]) -> Dict:
    """Normaliza nomes de modelo para CarviaModeloMoto e agrega a regiao.

    Defensivo contra estrutura malformada (motos=null/str, item nao-dict,
    regiao=str): degrada para "nada reconhecido" em vez de 500.
    """
    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService

    motos_raw = data.get('motos') if isinstance(data, dict) else None
    if not isinstance(motos_raw, list):
        motos_raw = []

    motos_out = []
    for moto in motos_raw:
        if not isinstance(moto, dict):
            continue
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

    regiao_raw = data.get('regiao') if isinstance(data, dict) else None
    if not isinstance(regiao_raw, dict):
        regiao_raw = {}
    regiao = {
        'cidade': (str(regiao_raw.get('cidade') or '').strip() or None),
        'uf': (str(regiao_raw.get('uf') or '').strip().upper() or None),
        'cep': (str(regiao_raw.get('cep') or '').strip() or None),
    }

    return {'motos': motos_out, 'regiao': regiao, 'parser_usado': parser_usado}
