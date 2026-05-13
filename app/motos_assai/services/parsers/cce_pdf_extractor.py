"""Parser deterministico de Carta de Correcao Eletronica (CCe) de NF-e.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §7.3
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 7

Extrai do PDF da CCe:
- numero_cce (formato: CCe-XXX-AAAA ou similar)
- numero_nf_referenciada (NF original sendo corrigida)
- chassis_corrigidos: list[(chassi_antigo, chassi_novo)]
- justificativa
- data_emissao
- confianca (0.0 a 1.0)

Quando confianca < CONFIANCA_LIMIAR, caller deve acionar fallback LLM
(cce_llm_fallback.extrair_cce_via_llm).
"""
from __future__ import annotations

import io
import re
from typing import Dict, Any

import pdfplumber


CONFIANCA_LIMIAR = 0.80

# Regex robustos
REGEX_NUMERO_CCE = re.compile(
    r'(?:CC[-\s]?[Ee]|Carta\s+de\s+Corre[cç][aã]o)[\s\:\-]*([0-9A-Za-z\-\/]+)',
    re.IGNORECASE,
)
REGEX_NUMERO_NF = re.compile(
    r'(?:NF[\-\s]?e?|Nota\s+Fiscal)[\s\:\-]*(\d{1,15})',
    re.IGNORECASE,
)
# Chassi VIN: 17 caracteres alfanumericos sem I, O, Q
REGEX_CHASSI = re.compile(r'\b([0-9A-HJ-NPR-Z]{17})\b')

# Captura sequencia "<chassi_antigo>" → "<chassi_novo>" (variacoes de seta)
REGEX_PAR_CHASSI = re.compile(
    r'\b([0-9A-HJ-NPR-Z]{17})\b\s*(?:[-=]>|→|para|substitu[íi]do?\s+por|alterad[oa]?\s+para)\s*\b([0-9A-HJ-NPR-Z]{17})\b',
    re.IGNORECASE,
)

REGEX_DATA = re.compile(r'\b(\d{2})/(\d{2})/(\d{2,4})\b')


class CceParseError(Exception):
    """Falha critica do parser deterministico — caller deve usar LLM fallback."""


def extrair_cce(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extrai dados estruturados de PDF de CCe.

    Args:
        pdf_bytes: bytes do PDF da Carta de Correcao.

    Returns:
        dict com campos:
            - numero_cce (str | None)
            - numero_nf_referenciada (str)
            - chassis_corrigidos: list[tuple[str, str]]  # [(antigo, novo), ...]
            - justificativa (str)  # vazia se nao detectada
            - data_emissao (str | None)  # formato DD/MM/AAAA
            - confianca (float)  # 0.0 a 1.0

    Raises:
        CceParseError: PDF sem texto extraivel ou estrutura minima.
    """
    if not pdf_bytes:
        raise CceParseError('PDF vazio')

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texto = '\n'.join((page.extract_text() or '') for page in pdf.pages)
    except Exception as e:
        raise CceParseError(f'Falha ao abrir PDF com pdfplumber: {e}')

    if not texto.strip():
        raise CceParseError('PDF sem texto extraivel')

    # 1. Numero da CCe
    numero_cce_match = REGEX_NUMERO_CCE.search(texto)
    numero_cce = numero_cce_match.group(1) if numero_cce_match else None

    # 2. Numero da NF referenciada
    numero_nf_match = REGEX_NUMERO_NF.search(texto)
    if not numero_nf_match:
        raise CceParseError('NF referenciada nao encontrada no PDF')
    numero_nf = numero_nf_match.group(1)

    # 3. Pares de chassis (chassi_antigo -> chassi_novo)
    pares_match = REGEX_PAR_CHASSI.findall(texto)
    chassis_corrigidos: list = []
    if pares_match:
        chassis_corrigidos = [(a.upper(), n.upper()) for (a, n) in pares_match]
    else:
        # Fallback: heuristica de chassis em pares (par-impar)
        chassis = REGEX_CHASSI.findall(texto)
        if len(chassis) >= 2 and len(chassis) % 2 == 0:
            for i in range(0, len(chassis), 2):
                chassis_corrigidos.append(
                    (chassis[i].upper(), chassis[i + 1].upper())
                )

    # 4. Data de emissao (primeira data DD/MM/AAAA encontrada)
    data_match = REGEX_DATA.search(texto)
    data_emissao = None
    if data_match:
        dia, mes, ano = data_match.groups()
        if len(ano) == 2:
            ano = '20' + ano
        data_emissao = f'{dia}/{mes}/{ano}'

    # 5. Justificativa: extracao deterministica sofisticada precisa LLM.
    # Por enquanto, busca trecho ate 200 chars apos "JUSTIFICATIVA" / "MOTIVO".
    justificativa = ''
    just_match = re.search(
        r'(?:JUSTIFICATIVA|MOTIVO|CORREC?A?O?)[\s\:]+(.{20,500}?)(?:\n\s*\n|$)',
        texto, re.IGNORECASE | re.DOTALL,
    )
    if just_match:
        justificativa = just_match.group(1).strip()[:500]

    # 6. Calcular confianca (0.0 a 1.0)
    confianca = 0.0
    if numero_cce:
        confianca += 0.20
    if numero_nf:
        confianca += 0.30
    if chassis_corrigidos:
        # Mais peso se foram extraidos via REGEX_PAR_CHASSI (par explicito) vs heuristica
        confianca += 0.30 if pares_match else 0.20
    if data_emissao:
        confianca += 0.10
    if justificativa:
        confianca += 0.10
    confianca = min(1.0, confianca)

    return {
        'numero_cce': numero_cce,
        'numero_nf_referenciada': numero_nf,
        'chassis_corrigidos': chassis_corrigidos,
        'justificativa': justificativa,
        'data_emissao': data_emissao,
        'confianca': confianca,
    }
