"""Parser de pedido HORA via imagem (print de WhatsApp).

Fallback ao XLSX import: operador sobe foto do PEDIDO DE VENDA - SCOOTER
ELETRICA e o sistema extrai dados via Claude Sonnet 4.6 (multimodal),
retornando o mesmo `PedidoExtraido` que o parser XLSX retorna. Tudo apos
o parser (triagem CNPJ matriz, resolucao de loja, preview, criacao do
pedido) reusa codigo existente sem modificacao.

Por que Sonnet 4.6 e nao Haiku 4.5:
    Chassis longos alfanumericos (LYDAE393XT1203290, MCBRMIA2511270089)
    sao o pior caso de OCR — sem contexto que ajude a desambiguar O vs 0,
    X vs K. Risco de chassi errado entrar no sistema e alto. Sonnet
    historicamente erra menos em alfanumericos sem dicionario.

Validacao pos-extracao (independente do modelo):
    - Soma produtos[*][-1] ≈ total_declarado (R$ 0,01 tolerancia) → warning se nao bater
    - Chassi 15-18 chars alfanumerico → marca aviso='chassi_suspeito'
    - Chassi duplicado no pedido → warning
    - PALLET nao-numerico e nao-string-conhecida → warning
    - Data fora DD/MM/AAAA → fallback date.today()
    - len(produtos) == 0 → erro fatal

Reusa helpers do XLSX parser via import:
    - _normalizar_chassi, _normalizar_preco, _normalizar_modelo, _normalizar_cnpj
    - regex de CNPJ/data/UF aplicada sobre cliente_str/endereco_str do dict

Uso:
    from app.hora.services.parsers.pedido_imagem_parser import parse_pedido_imagem
    extracao = parse_pedido_imagem(image_bytes, nome_arquivo='print.jpg', mime_type='image/jpeg')
    # extracao e PedidoExtraido — mesmo formato do parse_pedido_xlsx
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.hora.services.parsers.pedido_xlsx_parser import (
    CNPJ_MATRIZ_HORA,
    ItemPedidoExtraido,
    PedidoExtraido,
    PedidoParseError,
    _normalizar_chassi,
    _normalizar_modelo,
    _normalizar_preco,
)

logger = logging.getLogger(__name__)

SONNET_MODEL = 'claude-sonnet-5'
SONNET_MAX_TOKENS = 4096

# Tolerancia para validacao de soma vs total_declarado (R$).
TOLERANCIA_SOMA_TOTAL = Decimal('0.01')

# Comprimento esperado de chassi (15-18 chars). Fora dessa faixa = suspeito.
CHASSI_LEN_MIN = 15
CHASSI_LEN_MAX = 18

# MIME types aceitos.
MIME_TYPES_ACEITOS = ('image/jpeg', 'image/png', 'image/webp')

# Apelidos genericos que NAO discriminam loja — copia do XLSX parser para
# nao duplicar import.
TOKENS_GENERICOS_LOJA = frozenset({
    'MOTOCHEFE', 'HORA', 'LOJA', 'FRANQUIA', 'MATRIZ', 'FILIAL',
    'UNIDADE', 'FILIA',
})


SYSTEM_PROMPT = """Voce e um extrator de dados estruturados de pedidos de moto eletrica brasileira.

Recebe imagem de "PEDIDO DE VENDA - SCOOTER ELETRICA" (template HORA/Motochefe) e devolve EXCLUSIVAMENTE um JSON valido (sem markdown, sem prosa).

Schema obrigatorio:
{
  "cliente": "string (linha CLIENTE — razao social completa, ex: 'HORA COMERCIO DE MOTOCICLETAS ELETRICAS LTDA - MOTOCHEFE TATUAPE SP')",
  "cnpj": "string (linha CNPJ — ex: '62.634.044/0001-20')",
  "ie": "string (Inscricao Estadual, frequentemente vazia)",
  "endereco": "string (linha ENDERECO)",
  "bairro": "string (linha BAIRRO)",
  "cidade": "string (linha CIDADE — apenas o nome, ex: 'SAO PAULO')",
  "estado": "string (UF de 2 letras — ex: 'SP')",
  "cep": "string",
  "telefone": "string",
  "email": "string",
  "contato": "string DD/MM/AAAA (linha CONTATO ou data visivel no pedido)",
  "has_motor": true|false,
  "produtos": [
    [PRODUTO, CHASSI, COR, (MOTOR), PALLET, VALOR_UNITARIO],
    ...
  ],
  "total_declarado": <float, valor lido na linha amarela TOTAL no rodape da tabela>
}

REGRAS DE EXTRACAO:

1. CHASSI:
   - Sempre string alfanumerico longo (tipicamente 15-18 chars).
   - Preserve apostrofo inicial se houver (ex: "'172922504731174").
   - Cuidado redobrado com confusao visual: O vs 0, I vs 1, X vs K, S vs 5.
     Se um caractere parece ambiguo, prefira a interpretacao que mantem
     o chassi alfanumerico consistente.
   - Exemplos canonicos: LYDAE393XT1203290, MCBRMIA2511270089, MZX1234ABC5678.

2. has_motor:
   - true se a tabela tiver coluna MOTOR; cada produto tem 6 elementos:
     [PRODUTO, CHASSI, COR, MOTOR, PALLET, VALOR_UNITARIO]
   - false se nao tiver; cada produto tem 5 elementos:
     [PRODUTO, CHASSI, COR, PALLET, VALOR_UNITARIO]

3. PALLET:
   - Numero inteiro se for numerico (ex: 15, 5531).
   - String se nao numerico (ex: "A", "B").
   - String vazia "" se a celula estiver vazia.

4. VALOR_UNITARIO:
   - Numero float (ex: 5750.00).
   - Converta formato brasileiro: "5.750,00" -> 5750.00, "11.500,00" -> 11500.00.
   - O ponto e separador de milhar; a virgula e separador decimal.

5. total_declarado:
   - Leia a celula TOTAL na linha amarela do rodape da tabela.
   - Mesmo formato BR de VALOR_UNITARIO ("55.000,00" -> 55000.00).
   - Se nao for visivel, retorne null.

6. CLIENTE:
   - Capture a linha CLIENTE inteira, incluindo o apelido da loja
     (ex: "MOTOCHEFE PRAIA GRANDE", "MOTOCHEFE TATUAPE SP", "MOTOCHEFE BRAGANCA").
   - O apelido apos "MOTOCHEFE " e essencial para resolver a loja destino.

7. NAO INVENTE. Se um campo nao esta visivel ou ilegivel, retorne string
   vazia "" (ou null para total_declarado).

8. NAO inclua a linha TOTAL nos produtos.

9. Devolva SOMENTE o JSON valido, sem cercas de codigo (```json), sem prosa,
   sem comentarios.
"""


# --------------------------------------------------------------------------
# API publica
# --------------------------------------------------------------------------

def parse_pedido_imagem(
    image_bytes: bytes,
    nome_arquivo: Optional[str] = None,
    mime_type: str = 'image/jpeg',
) -> PedidoExtraido:
    """Parseia imagem de pedido HORA via Claude Sonnet 4.6 e retorna PedidoExtraido.

    Args:
        image_bytes: conteudo binario da imagem (JPG/PNG/WEBP).
        nome_arquivo: nome do arquivo para logging/auditoria (opcional).
        mime_type: MIME type da imagem (default 'image/jpeg').

    Levanta:
        PedidoParseError: API indisponivel, JSON invalido, ou produtos vazios.

    Retorna:
        PedidoExtraido com metodo_extracao='IMAGEM_LLM_SONNET_4_6'.
    """
    if not image_bytes:
        raise PedidoParseError('image_bytes vazio')
    if mime_type not in MIME_TYPES_ACEITOS:
        raise PedidoParseError(
            f'MIME type nao suportado: {mime_type}. Aceitos: {MIME_TYPES_ACEITOS}'
        )

    # 1. Chama o LLM
    dict_bruto = _chamar_llm_visao(image_bytes, mime_type)

    # 2. Validacao pos-extracao (anexa avisos)
    dict_normalizado, avisos_validacao = _validar_extracao(dict_bruto)

    # 3. Converte para PedidoExtraido (reusa helpers do XLSX parser)
    extraido = _dict_para_pedido_extraido(
        dict_normalizado, nome_arquivo, avisos_extra=avisos_validacao,
    )
    return extraido


# --------------------------------------------------------------------------
# Cliente Anthropic + chamada LLM
# --------------------------------------------------------------------------

_anthropic_client = None


def _get_anthropic_client():
    """Lazy: carrega cliente Anthropic apenas quando necessario.

    Levanta PedidoParseError se SDK nao instalado ou API key ausente.
    """
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise PedidoParseError(
            'ANTHROPIC_API_KEY ausente — parser de imagem desabilitado. '
            'Configure a variavel de ambiente para habilitar.'
        )
    try:
        import anthropic
    except ImportError as exc:
        raise PedidoParseError(
            f"Biblioteca 'anthropic' nao instalada: {exc}"
        ) from exc

    _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _chamar_llm_visao(image_bytes: bytes, mime_type: str) -> dict:
    """POST imagem em base64 + system prompt para Sonnet 4.6.

    Levanta PedidoParseError se API falhar ou retornar JSON invalido.
    """
    client = _get_anthropic_client()
    image_b64 = base64.standard_b64encode(image_bytes).decode('ascii')

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=SONNET_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': mime_type,
                                'data': image_b64,
                            },
                        },
                        {
                            'type': 'text',
                            'text': (
                                'Extraia este pedido como JSON, seguindo '
                                'exatamente o schema descrito.'
                            ),
                        },
                    ],
                },
            ],
        )
    except Exception as exc:
        logger.exception('parse_pedido_imagem: chamada Sonnet falhou')
        raise PedidoParseError(f'Sonnet 4.6 falhou: {exc}') from exc

    if not response.content:
        raise PedidoParseError('Sonnet retornou resposta vazia')

    texto_resposta = response.content[0].text  # type: ignore[union-attr]
    if not isinstance(texto_resposta, str) or not texto_resposta.strip():
        raise PedidoParseError('Sonnet retornou conteudo nao-textual ou vazio')

    dict_extraido = _extrair_json_object(texto_resposta)
    if dict_extraido is None:
        logger.warning(
            'parse_pedido_imagem: JSON invalido. Resposta=%r',
            texto_resposta[:500],
        )
        raise PedidoParseError(
            'Sonnet retornou JSON invalido. Veja log para detalhes.'
        )
    return dict_extraido


def _extrair_json_object(texto: str) -> Optional[dict]:
    """Extrai primeiro objeto JSON valido da resposta. Lida com cercas markdown."""
    if not texto:
        return None
    s = texto.strip()
    # Cerca markdown explicita ```json ... ```
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Primeiro objeto na resposta (greedy)
    m = re.search(r'\{.*\}', s, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------
# Validacao pos-extracao
# --------------------------------------------------------------------------

def _validar_extracao(dict_bruto: dict) -> tuple[dict, list[str]]:
    """Aplica validacoes ao dict do LLM. Retorna (dict_normalizado, warnings).

    Levanta PedidoParseError em casos fatais (produtos vazios, schema
    quebrado).

    Warnings sao mensagens estrategicamente formatadas para o operador
    visualizar no preview e tomar decisao informada.
    """
    if not isinstance(dict_bruto, dict):
        raise PedidoParseError(f'LLM retornou nao-dict: {type(dict_bruto)}')

    produtos = dict_bruto.get('produtos')
    if not isinstance(produtos, list) or not produtos:
        raise PedidoParseError('LLM retornou sem produtos — imagem ilegivel ou layout fora do padrao HORA')

    has_motor = bool(dict_bruto.get('has_motor', False))
    expected_cols = 6 if has_motor else 5

    warnings: list[str] = []
    soma_calculada = Decimal('0')
    chassis_vistos: dict[str, int] = {}

    for i, prod in enumerate(produtos):
        if not isinstance(prod, list):
            warnings.append(f'Produto {i+1}: linha mal formatada (tipo {type(prod).__name__})')
            continue
        if len(prod) != expected_cols:
            warnings.append(
                f'Produto {i+1}: {len(prod)} colunas, esperado {expected_cols} '
                f'(has_motor={has_motor})'
            )
            continue

        # Posicoes:
        #   has_motor=False: [PROD, CHASSI, COR, PALLET, VALOR]
        #   has_motor=True:  [PROD, CHASSI, COR, MOTOR, PALLET, VALOR]
        chassi_raw = prod[1]
        pallet_idx = 4 if has_motor else 3
        valor_idx = 5 if has_motor else 4
        pallet_raw = prod[pallet_idx]
        valor_raw = prod[valor_idx]

        # Soma do valor (independente de validacao de chassi)
        valor_decimal = _normalizar_preco(valor_raw)
        if valor_decimal is not None:
            soma_calculada += valor_decimal

        # Chassi: alfanumerico 15-18 chars
        if chassi_raw:
            chassi_norm = _normalizar_chassi(chassi_raw)
            if chassi_norm:
                # Comprimento e alfanumerico
                if len(chassi_norm) < CHASSI_LEN_MIN or len(chassi_norm) > CHASSI_LEN_MAX:
                    warnings.append(
                        f'Produto {i+1}: chassi "{chassi_norm}" tem {len(chassi_norm)} chars '
                        f'(esperado {CHASSI_LEN_MIN}-{CHASSI_LEN_MAX}) — verifique no preview.'
                    )
                if not chassi_norm.isalnum():
                    warnings.append(
                        f'Produto {i+1}: chassi "{chassi_norm}" tem caractere nao-alfanumerico — '
                        f'verifique se o LLM leu corretamente.'
                    )
                # Duplicado
                if chassi_norm in chassis_vistos:
                    chassis_vistos[chassi_norm] += 1
                    warnings.append(
                        f'Chassi {chassi_norm} aparece duas vezes (produtos '
                        f'{chassis_vistos[chassi_norm]} e {i+1}) — '
                        f'um deles pode estar errado.'
                    )
                else:
                    chassis_vistos[chassi_norm] = i + 1

        # PALLET: numerico, vazio, ou string curta
        if pallet_raw not in ('', None):
            if isinstance(pallet_raw, str) and not pallet_raw.strip().isdigit():
                # Strings curtas tipo "A", "B" sao OK; longas/com simbolos sao suspeitas
                if len(pallet_raw.strip()) > 5 or not pallet_raw.strip().replace('-', '').replace('_', '').isalnum():
                    warnings.append(
                        f'Produto {i+1}: PALLET "{pallet_raw}" parece estranho — verifique.'
                    )

    # Soma vs total_declarado
    total_declarado_raw = dict_bruto.get('total_declarado')
    if total_declarado_raw is not None:
        total_decimal = _normalizar_preco(total_declarado_raw)
        if total_decimal is not None:
            diferenca = abs(soma_calculada - total_decimal)
            if diferenca > TOLERANCIA_SOMA_TOTAL:
                warnings.append(
                    f'Total declarado R$ {total_decimal:.2f} mas soma dos itens '
                    f'R$ {soma_calculada:.2f} — diferenca R$ {diferenca:.2f}. '
                    f'Verifique se algum valor foi extraido errado.'
                )

    # Data: tenta parse para fallback nao-quebrado
    contato = (dict_bruto.get('contato') or '').strip()
    if contato:
        try:
            datetime.strptime(contato, '%d/%m/%Y')
        except ValueError:
            warnings.append(
                f'Data "{contato}" nao parseavel como DD/MM/AAAA — '
                f'usando data de hoje como fallback.'
            )
            dict_bruto['contato'] = ''  # forca fallback no _dict_para_pedido_extraido

    return dict_bruto, warnings


# --------------------------------------------------------------------------
# Adapter: dict do LLM → PedidoExtraido
# --------------------------------------------------------------------------

def _detectar_apelido(cliente_str: str) -> Optional[str]:
    """Extrai apelido da loja da string CLIENTE.

    Padrao tipico: "HORA COMERCIO DE MOTOCICLETAS ELETRICAS LTDA - MOTOCHEFE TATUAPE SP"
                                                                   ^^^^^^^^^^^^^^^^^^^^^
                                                                   apelido (apos hifen ou MOTOCHEFE)
    Para casar com `resolver_loja_por_apelido` do XLSX parser, retornamos
    o trecho APOS "MOTOCHEFE " (ou tudo apos o hifen final se nao tiver MOTOCHEFE).
    """
    if not cliente_str:
        return None
    cliente_upper = cliente_str.upper().strip()

    # Tenta encontrar "MOTOCHEFE <APELIDO>"
    m = re.search(r'\bMOTOCHEFE\s+([A-ZÀ-ÿ][A-ZÀ-ÿ\s]+?)(?:\s*[-—|,]|\s*$)', cliente_upper)
    if m:
        candidato = m.group(1).strip()
        if 2 < len(candidato) < 50:
            return candidato

    # Fallback: tenta a parte apos o ultimo hifen
    if ' - ' in cliente_upper:
        candidato = cliente_upper.rsplit(' - ', 1)[-1].strip()
        if 2 < len(candidato) < 50:
            return candidato
    if ' -' in cliente_upper:
        candidato = cliente_upper.rsplit(' -', 1)[-1].strip()
        if 2 < len(candidato) < 50:
            return candidato

    return None


def _data_de_str(s: str) -> Optional[date]:
    """'DD/MM/AAAA' → date. None se vazio ou invalido."""
    if not s:
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, '%d/%m/%Y').date()
    except ValueError:
        # Tenta DD/MM/AA
        try:
            return datetime.strptime(s, '%d/%m/%y').date()
        except ValueError:
            return None


def _digitos_cnpj(raw: str) -> Optional[str]:
    if not raw:
        return None
    digitos = ''.join(c for c in str(raw) if c.isdigit())
    return digitos if len(digitos) == 14 else None


def _gerar_numero_pedido_fallback(extraido_data: Optional[date], apelido: Optional[str]) -> str:
    """Gera numero_pedido determinístico para imagens sem numero explicito.

    Padrao 'IMG-DD.MM-APELIDO-HHMMSS' — combina data do pedido + apelido +
    timestamp atual. Determinístico para deduplicacao razoavel mas com
    timestamp para evitar colisoes em re-uploads no mesmo dia.
    """
    data_str = extraido_data.strftime('%d.%m') if extraido_data else 'SEMDATA'
    apelido_str = (apelido or 'SEM_LOJA').upper().replace(' ', '_')[:20]
    ts = datetime.now().strftime('%H%M%S')
    return f'IMG-{data_str}-{apelido_str}-{ts}'


def _dict_para_pedido_extraido(
    d: dict,
    nome_arquivo: Optional[str],
    avisos_extra: Optional[list[str]] = None,
) -> PedidoExtraido:
    """Converte dict do LLM em PedidoExtraido. Reusa helpers do XLSX parser."""
    avisos: list[str] = list(avisos_extra or [])

    # Metadados
    cliente_nome = (d.get('cliente') or '').strip() or None
    cnpj_raw = d.get('cnpj') or ''
    cnpj_destino = _digitos_cnpj(cnpj_raw)
    cnpjs_candidatos: list[str] = []
    if cnpj_destino:
        cnpjs_candidatos.append(cnpj_destino)

    cidade = (d.get('cidade') or '').strip() or None
    uf = (d.get('estado') or '').strip().upper() or None
    apelido_detectado = _detectar_apelido(cliente_nome or '')

    # Data: tenta parse + fallback hoje
    data_pedido = _data_de_str(d.get('contato') or '')
    if data_pedido is None:
        data_pedido = date.today()

    # numero_pedido: se LLM nao retornou, gera fallback (determinístico-ish)
    numero_pedido = (d.get('numero_pedido') or '').strip()
    if not numero_pedido and nome_arquivo:
        # Se o nome do arquivo tem padrao XX.YY, usa
        m = re.search(r'(\d{2}\.\d{2})', nome_arquivo)
        if m:
            numero_pedido = f'IMG-{m.group(1)}-{(apelido_detectado or "X").replace(" ", "_")[:20]}'
    if not numero_pedido:
        numero_pedido = _gerar_numero_pedido_fallback(data_pedido, apelido_detectado)

    # Itens
    has_motor = bool(d.get('has_motor', False))
    produtos = d.get('produtos') or []
    itens: list[ItemPedidoExtraido] = []

    for i, prod in enumerate(produtos):
        if not isinstance(prod, list):
            continue
        # Validacao de tamanho ja foi feita; aqui defensivamente:
        try:
            modelo_raw = prod[0]
            chassi_raw = prod[1]
            cor_raw = prod[2]
            valor_raw = prod[5] if has_motor else prod[3 + 1]  # idx 4 ou 5
        except IndexError:
            avisos.append(f'Produto {i+1}: estrutura quebrada — ignorado.')
            continue

        chassi = _normalizar_chassi(chassi_raw) if chassi_raw else None
        modelo = _normalizar_modelo(modelo_raw) if modelo_raw else None
        cor = _normalizar_modelo(cor_raw) if cor_raw else None

        # Valor: usa _normalizar_preco para aceitar string BR ou float
        preco = _normalizar_preco(valor_raw)
        if preco is None:
            preco = Decimal('0')

        # aviso por item (chassi suspeito repassa do _validar_extracao,
        # mas aqui marca defensivamente tambem)
        aviso_item = None
        if not chassi:
            aviso_item = 'chassi_pendente'
        elif len(chassi) < CHASSI_LEN_MIN or len(chassi) > CHASSI_LEN_MAX:
            aviso_item = 'chassi_suspeito'

        itens.append(ItemPedidoExtraido(
            numero_chassi=chassi,
            modelo=modelo,
            cor=cor,
            preco_compra_esperado=preco,
            linha_origem=i + 1,
            aviso=aviso_item,
        ))

    if not itens:
        raise PedidoParseError('Nenhum item parseavel apos extracao via LLM')

    # Aviso geral: reforça que extracao veio de OCR e operador deve conferir
    # chassis. Mesmo com validacao automatica (comprimento, alfanum, soma),
    # o LLM pode trocar caracteres visualmente parecidos (9→3, O→0, X→K)
    # sem o sistema detectar — operador e o ultimo filtro.
    avisos.insert(
        0,
        f'Extraido via OCR ({SONNET_MODEL}) — confira CADA chassi com atencao. '
        f'Caracteres visualmente parecidos (9/3, O/0, X/K, I/1, S/5) podem ser '
        f'confundidos pelo modelo.',
    )

    # Avisos finais
    if not cnpj_destino:
        avisos.append(
            'CNPJ destino nao identificado pelo LLM — preencha manualmente '
            'antes de confirmar.'
        )
    if not apelido_detectado:
        avisos.append(
            'Apelido da loja nao identificado pelo LLM (campo CLIENTE) — '
            'selecione a loja destino manualmente no preview.'
        )

    return PedidoExtraido(
        numero_pedido=numero_pedido,
        cnpj_destino=cnpj_destino,
        cnpjs_candidatos=cnpjs_candidatos,
        data_pedido=data_pedido,
        cliente_nome=cliente_nome,
        cidade=cidade,
        uf=uf,
        apelido_detectado=apelido_detectado,
        itens=itens,
        avisos=avisos,
        header_row=None,
        metodo_extracao='IMAGEM_LLM_SONNET_4_6',
    )


# Re-exports para conveniencia
__all__ = [
    'parse_pedido_imagem',
    'CNPJ_MATRIZ_HORA',  # re-export do XLSX parser
    'MIME_TYPES_ACEITOS',
    'SONNET_MODEL',
]
