"""Append-prompt versionado para o parser de DANFE / extrator de chassi-motor.

Mecanismo de aprendizado por feedback:

  1. Operador detecta extracao errada (ex.: chassi capturado como motor).
  2. Cola o `texto bruto` (campo `detalhes` da API TagPlus, ou trecho da
     secao "Dados Adicionais" da DANFE) e os `valores corretos`.
  3. Sistema chama Sonnet pedindo uma instrucao curta a ser ANEXADA ao
     append vigente (so o acrescimo, nao reescrita inteira).
  4. Operador testa o append proposto via Haiku (extrai com o append) — ve
     se o resultado bate com o esperado.
  5. Se OK, grava nova versao (ativa). Antiga vira historico.

Uso pelo backfill:
  - `extrair_via_llm_com_append(detalhes)` — chamado como fallback no
    `backfill_service._extrair_chassi_motor` quando regex nao encontrou
    chassi. Le append ATIVO (cache em request) e chama Haiku.

Uso pelo parser DANFE PDF (CarVia):
  - `app/hora/services/parsers/hora_danfe_parser.HoraDanfePDFParser`
    sobrescreve `_extrair_veiculos_llm` injetando o append no `texto_secao`.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from app import db
from app.hora.models.tagplus import HoraDanfeParserAppend
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# Modelos Anthropic (alinhados com parser CarVia).
HAIKU_MODEL = 'claude-haiku-4-5-20251001'
SONNET_MODEL = 'claude-sonnet-4-6'

# Regras CONSOLIDADAS de extracao chassi/motor de moto eletrica.
# Adaptado do prompt do parser CarVia
# (`app/carvia/services/parsers/danfe_pdf_parser.DanfePDFParser._extrair_veiculos_llm`).
# Removidas partes que so se aplicam a DANFE PDF (qtd_esperada, ancora de
# codigos de produto). Mantidas as regras de DESAMBIGUACAO chassi vs motor
# que valem para qualquer fonte de texto livre — incluindo o campo
# `detalhes` / `inf_contribuinte` / `observacoes` da API TagPlus.
_REGRAS_CHASSI_MOTOR = (
    "REGRAS DE EXTRACAO:\n"
    "- chassi: codigo alfanumerico longo (>=8 chars). Pode aparecer apos "
    "rotulos como 'CHASSI:', 'Nº SERIE:', 'N SERIE:', 'SERIE:', "
    "'Nº de Serie:', ou em linha separada apos MOTOR (sem prefixo).\n"
    "- numero_motor (campo 'motor'): codigo do motor, alfanumerico OU "
    "puramente numerico, DIFERENTE do chassi. Geralmente apos rotulo "
    "'MOTOR:' ou 'Nº MOTOR:'. DANFEs/NFs TagPlus de scooter eletrica "
    "frequentemente NAO declaram motor — retorne null nesse caso.\n"
    "- ORDEM POSICIONAL OBRIGATORIA quando aparecem 2 codigos longos "
    "(>=10 chars) em sequencia apos modelo+cor SEM rotulos: o PRIMEIRO eh "
    "SEMPRE o chassi e o SEGUNDO eh SEMPRE o motor. Vale INDEPENDENTE do "
    "formato de cada um (ambos alfanumericos, ambos digitos puros, "
    "1º numerico + 2º alfanumerico, 1º alfanumerico + 2º numerico). "
    "NUNCA inverta a ordem.\n"
    "- ATENCAO: quando chassi e motor aparecem com ROTULOS em linhas "
    "separadas tipo 'MOTOR: <a>\\nCHASSI: <b>' a ordem do TEXTO "
    "(motor primeiro, chassi depois) e o que vale; preserve os "
    "valores pelos rotulos — NAO inverta.\n"
    "- Codigos longos (>=10 chars) podem ser chassi OU motor (decide pela "
    "ordem/rotulo acima), NUNCA modelo. Vale para alfanumericos como "
    "'LA25860V1000W2087' E para digitos puros como '172922502660076'.\n"
    "- Especificacoes de potencia como '1000WATTS', '1000W', '500W', "
    "'2000W' NAO sao numero de motor — sao texto descritivo da potencia.\n"
    "- IGNORE classificacoes fiscais genericas como "
    "'VEICULO AUTOPROPELIDO', 'BICICLETA ELETRICA', textos entre "
    "<colchetes angulares>, ou frases que citam 'RESOLUCAO 996/2023 "
    "CONTRAN'. Esses textos NAO sao modelo nem chassi.\n"
    "- IGNORE rotulos como 'Inf. Contribuinte:', 'Informacoes "
    "Complementares', 'Inf. Complementar:', 'GARANTIA', 'COR:', "
    "'ANO/MODELO', 'MOD'. Sao cabecalhos/atributos, nao chassi.\n"
    "- IGNORE CNPJ, CPF, CEP, telefone, valores monetarios, datas.\n"
    "- Se nao houver chassi identificavel, retorne null.\n"
)

# Exemplos canonicos (alinhados com os do parser CarVia mas focados em
# chassi/motor) para o LLM ancorar a desambiguacao.
_EXEMPLOS_CHASSI_MOTOR = (
    "EXEMPLOS:\n"
    "1. 'DOT LA25860V1000W2087 QS60V30H25111101233 CINZA' "
    "→ chassi='LA25860V1000W2087' (1º), motor='QS60V30H25111101233' (2º).\n"
    "2. 'Inf. Contribuinte: RET 172922506731512 LM60V1000W2025062100444 "
    "CINZA' → chassi='172922506731512' (1º, NAO se engane com numerico "
    "puro), motor='LM60V1000W2025062100444' (2º).\n"
    "3. TagPlus: 'Nº SERIE: LYDAE3936T1203254 COR: Preta ANO/MODELO "
    "2025/2026' → chassi='LYDAE3936T1203254', motor=null.\n"
    "4. TagPlus: 'Nº SERIE: MCBRX122511110209 COR: VERMELHA' "
    "→ chassi='MCBRX122511110209', motor=null.\n"
    "5. Linhas separadas com rotulos:\n"
    "   'MOTOR: ABC123\\nCHASSI: XYZ789' "
    "→ chassi='XYZ789', motor='ABC123'. Os rotulos prevalecem.\n"
    "6. 'CHASSI: 9BD17822506731512 / Motor: 1000WATTS' "
    "→ chassi='9BD17822506731512', motor=null (1000WATTS e potencia, nao motor).\n"
)

_PROMPT_BASE_EXTRACAO = (
    "Voce extrai chassi e numero de motor de uma NF de moto eletrica "
    "brasileira a partir de um trecho de texto livre (campo "
    "`inf_contribuinte`/`observacoes`/`detalhes` da API).\n\n"
    + _REGRAS_CHASSI_MOTOR
    + "\n"
    + _EXEMPLOS_CHASSI_MOTOR
    + "\n"
    + "Retorne APENAS JSON valido com as chaves `chassi` e `motor` "
    "(strings ou null). Nao inclua texto fora do JSON.\n"
)


# --------------------------------------------------------------------------
# CRUD do append
# --------------------------------------------------------------------------

def get_append_ativo() -> Optional[HoraDanfeParserAppend]:
    """Retorna o registro ativo, ou None se nenhum foi criado ainda."""
    return (
        HoraDanfeParserAppend.query
        .filter_by(ativo=True)
        .first()
    )


def texto_append_ativo() -> str:
    """Retorna o texto do append ativo, ou '' se nao existe."""
    ativo = get_append_ativo()
    return (ativo.texto_append or '') if ativo else ''


def listar_historico(limit: int = 30) -> list[HoraDanfeParserAppend]:
    """Lista N versoes mais recentes em ordem descendente."""
    return (
        HoraDanfeParserAppend.query
        .order_by(HoraDanfeParserAppend.versao.desc())
        .limit(limit)
        .all()
    )


def proxima_versao() -> int:
    last = (
        HoraDanfeParserAppend.query
        .order_by(HoraDanfeParserAppend.versao.desc())
        .first()
    )
    return (last.versao + 1) if last else 1


def salvar_nova_versao(
    texto_completo: str,
    *,
    acrescimo_aplicado: Optional[str] = None,
    motivo: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraDanfeParserAppend:
    """Cria uma nova versao ativa. Desativa a anterior atomicamente.

    Levanta ValueError se `texto_completo` vazio.
    """
    texto = (texto_completo or '').strip()
    if not texto:
        raise ValueError('texto_append vazio')

    # Desativa todos os anteriores (UNIQUE WHERE ativo=TRUE protege).
    HoraDanfeParserAppend.query.filter_by(ativo=True).update(
        {HoraDanfeParserAppend.ativo: False},
        synchronize_session=False,
    )

    nova = HoraDanfeParserAppend(
        versao=proxima_versao(),
        texto_append=texto,
        acrescimo_aplicado=(acrescimo_aplicado or '').strip() or None,
        motivo=(motivo or '').strip()[:500] or None,
        criado_por=(criado_por or '').strip()[:100] or None,
        criado_em=agora_utc_naive(),
        ativo=True,
    )
    db.session.add(nova)
    db.session.commit()
    logger.info(
        'parser_append: nova versao gravada v%s por %s',
        nova.versao, nova.criado_por,
    )
    return nova


# --------------------------------------------------------------------------
# Cliente Anthropic (lazy)
# --------------------------------------------------------------------------

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logger.warning('ANTHROPIC_API_KEY ausente — append-LLM desabilitado.')
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
        return _client
    except ImportError:
        logger.warning('anthropic SDK nao instalado.')
        return None


# --------------------------------------------------------------------------
# Extracao via LLM (chamada pelo backfill TagPlus)
# --------------------------------------------------------------------------

def _extract_json_object(texto: str) -> Optional[dict]:
    """Extrai primeiro objeto JSON valido da resposta do LLM."""
    if not texto:
        return None
    # Tenta ```json...``` primeiro
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', texto, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Fallback: primeiro objeto na resposta
    m = re.search(r'\{.*?\}', texto, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def extrair_lote_via_llm_com_append(
    casos: list[dict],
    *,
    append_override: Optional[str] = None,
    model: str = HAIKU_MODEL,
    max_tokens: int = 8000,
) -> Optional[list[dict]]:
    """Extrai chassi/motor de MULTIPLAS NFs em UMA UNICA chamada LLM.

    Pensado para o final do backfill: regex rodou em todas as NFs e algumas
    falharam (chassi=None). Em vez de N chamadas Haiku per-NF (lento e caro),
    enviamos a lista inteira em 1 prompt e recebemos array com a extracao.

    Args:
        casos: lista de dicts `{nfe_id, detalhes}` (texto bruto da NF).
            Recomenda-se max ~50 por chamada para nao estourar contexto/saida.
        append_override: usa este append em vez do ativo (modo TESTE).
        model: default Haiku (rapido, barato).
        max_tokens: limite de saida do LLM.

    Returns:
        Lista de dicts `[{nfe_id, chassi, motor}]` na MESMA ordem dos casos.
        None se LLM indisponivel ou resposta nao parseavel.
    """
    if not casos:
        return []

    client = _get_client()
    if client is None:
        return None

    append = (append_override
              if append_override is not None
              else texto_append_ativo())

    # Monta payload do batch — JSON com cada caso identificado por nfe_id.
    blocos = []
    for c in casos:
        nfe_id = c.get('nfe_id')
        detalhes = (c.get('detalhes') or '').strip()
        if nfe_id is None or not detalhes:
            continue
        blocos.append(
            f"### NFE_ID={nfe_id} ###\n{detalhes[:1500]}"
            # Cap por NF a 1500 chars — `inf_contribuinte`+`observacoes` raro
            # passa disso. Evita contexto inflado em batch grande.
        )
    if not blocos:
        return []

    instrucoes_append = ''
    if append:
        instrucoes_append = (
            "\n\nINSTRUCOES ADICIONAIS APRENDIDAS POR FEEDBACK "
            "(OBRIGATORIO RESPEITAR EM TODAS AS NFs):\n"
            + append.strip() + "\n"
        )

    prompt = (
        "Voce extrai chassi e numero de motor de VARIAS NFs brasileiras de "
        "moto eletrica EM LOTE. Cada NF eh um bloco delimitado por "
        "'### NFE_ID=<numero> ###'.\n\n"
        + _REGRAS_CHASSI_MOTOR
        + "\n"
        + _EXEMPLOS_CHASSI_MOTOR
        + f"\n{instrucoes_append}\n"
        + "FORMATO DE SAIDA: array JSON com 1 objeto por bloco, na MESMA "
        "ORDEM dos blocos:\n"
        '[{"nfe_id": <int>, "chassi": <str|null>, "motor": <str|null>}, ...]\n'
        "NUMERO DE OBJETOS DEVE BATER COM NUMERO DE BLOCOS. Se nao "
        "identificar chassi em um bloco, retorne null nele (nao pule). "
        "Nao inclua texto fora do array.\n\n"
        f"BLOCOS ({len(blocos)} NFs):\n\n"
        + '\n\n'.join(blocos)
        + '\n\nResponda APENAS com o array JSON.'
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        texto_resposta = (
            response.content[0].text.strip() if response.content else ''
        )
    except Exception:
        logger.exception(
            'parser_append: chamada batch LLM falhou (modelo=%s, n=%s)',
            model, len(blocos),
        )
        return None

    # Extrai array JSON.
    arr_match = re.search(r'\[.*\]', texto_resposta, re.DOTALL)
    if not arr_match:
        logger.warning(
            'parser_append batch: resposta sem array JSON. Resposta=%r',
            texto_resposta[:300],
        )
        return None
    try:
        arr = json.loads(arr_match.group(0))
    except json.JSONDecodeError:
        logger.exception('parser_append batch: JSON invalido')
        return None

    if not isinstance(arr, list):
        return None

    def _norm(v):
        if v in (None, '', 'null', 'NULL'):
            return None
        s = str(v).strip().upper()
        return s or None

    resultado = []
    for item in arr:
        if not isinstance(item, dict):
            continue
        try:
            nfe_id = int(item.get('nfe_id'))
        except (TypeError, ValueError):
            continue
        resultado.append({
            'nfe_id': nfe_id,
            'chassi': _norm(item.get('chassi')),
            'motor': _norm(item.get('motor')),
        })
    return resultado


def extrair_via_llm_com_append(
    detalhes: str,
    *,
    append_override: Optional[str] = None,
    model: str = HAIKU_MODEL,
) -> Optional[dict]:
    """Chama Haiku (default) com o append ATIVO + texto bruto.

    Args:
        detalhes: texto bruto a parsear (campo `detalhes` da API TagPlus).
        append_override: se informado, usa este texto em vez do append ativo
            (modo TESTE — ver `testar_append`).
        model: modelo Anthropic (default Haiku).

    Returns:
        dict com chaves `chassi` e `motor` (str ou None), ou None se o LLM
        nao respondeu / SDK indisponivel.
    """
    if not detalhes or len(detalhes.strip()) < 5:
        return None

    client = _get_client()
    if client is None:
        return None

    append = (append_override
              if append_override is not None
              else texto_append_ativo())

    prompt_parts = [_PROMPT_BASE_EXTRACAO]
    if append:
        prompt_parts.append(
            "\nINSTRUCOES ADICIONAIS APRENDIDAS POR FEEDBACK "
            "(OBRIGATORIO RESPEITAR):\n"
            + append.strip()
            + "\n"
        )
    prompt_parts.append(
        f"\nTrecho da NF:\n{detalhes.strip()}\n\n"
        f"Responda APENAS com o JSON {{chassi, motor}}."
    )
    prompt = ''.join(prompt_parts)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        texto_resposta = response.content[0].text.strip() if response.content else ''
    except Exception:
        logger.exception('parser_append: chamada LLM falhou (modelo=%s)', model)
        return None

    obj = _extract_json_object(texto_resposta)
    if not isinstance(obj, dict):
        logger.warning(
            'parser_append: LLM retornou nao-JSON (modelo=%s): %s',
            model, texto_resposta[:200],
        )
        return None

    def _norm(v):
        if v in (None, '', 'null', 'NULL'):
            return None
        s = str(v).strip().upper()
        return s or None

    return {
        'chassi': _norm(obj.get('chassi')),
        'motor': _norm(obj.get('motor')),
        '_raw_response': texto_resposta,
    }


# --------------------------------------------------------------------------
# Sonnet — recomendar acrescimo a partir de exemplo de erro
# --------------------------------------------------------------------------

def recomendar_acrescimo(
    detalhes: str,
    extracao_atual: Optional[dict],
    valor_correto: dict,
    append_atual: Optional[str] = None,
) -> Optional[str]:
    """Pede ao Sonnet uma instrucao curta a ANEXAR ao append vigente.

    Args:
        detalhes: trecho bruto da NF onde a extracao falhou.
        extracao_atual: o que o sistema extraiu (ex: {'chassi': 'X', 'motor': None})
            ou None se nao extraiu nada.
        valor_correto: o que o operador informou como correto (mesmo formato).
        append_atual: texto do append ativo (para o LLM nao redundar).

    Returns:
        Texto do ACRESCIMO sugerido (1-3 frases), ou None se LLM falhou.
    """
    client = _get_client()
    if client is None:
        return None

    append_atual = (append_atual or '').strip()

    prompt = (
        "Voce ajuda a melhorar um prompt de extracao de chassi/motor de "
        "moto eletrica em NFs brasileiras. O extrator base usa LLM com um "
        "prompt principal e um APPEND de instrucoes aprendidas por feedback.\n\n"
        f"APPEND ATUAL (instrucoes ja aplicadas):\n"
        f"---\n{append_atual or '(vazio)'}\n---\n\n"
        f"TRECHO DA NF QUE GEROU ERRO:\n"
        f"---\n{(detalhes or '').strip()[:2000]}\n---\n\n"
        f"O QUE O EXTRATOR RETORNOU (ERRADO):\n"
        f"{json.dumps(extracao_atual or {}, ensure_ascii=False)}\n\n"
        f"O QUE O OPERADOR DISSE QUE E O CORRETO:\n"
        f"{json.dumps(valor_correto or {}, ensure_ascii=False)}\n\n"
        "TAREFA: Sugira UM ACRESCIMO curto (1 a 3 frases, max 400 chars) ao "
        "APPEND ATUAL para corrigir esse tipo de erro no futuro. NAO repita "
        "o que ja esta no APPEND ATUAL. NAO reescreva o append inteiro — "
        "retorne APENAS o trecho a ser anexado.\n\n"
        "Responda APENAS com o texto do acrescimo, sem aspas, sem JSON, "
        "sem prefixo. Em portugues."
    )

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = response.content[0].text.strip() if response.content else ''
    except Exception:
        logger.exception('parser_append: recomendar_acrescimo falhou')
        return None

    # Limpeza minima — remove cercas markdown se vierem.
    texto = re.sub(r'^```\w*\s*', '', texto)
    texto = re.sub(r'\s*```$', '', texto)
    texto = texto.strip()
    return texto[:400] or None


# --------------------------------------------------------------------------
# Testar append proposto (executa Haiku com o append e retorna extracao)
# --------------------------------------------------------------------------

def testar_append(detalhes: str, append_proposto: str) -> dict:
    """Roda Haiku com o append proposto sobre o `detalhes` e retorna extracao.

    Returns:
        dict com `chassi`, `motor`, `_raw_response`, `ok` (bool — true se
        SDK respondeu).
    """
    res = extrair_via_llm_com_append(
        detalhes, append_override=append_proposto, model=HAIKU_MODEL,
    )
    if res is None:
        return {
            'chassi': None, 'motor': None,
            'ok': False,
            '_raw_response': '(LLM indisponivel ou ANTHROPIC_API_KEY ausente)',
        }
    res['ok'] = True
    return res
