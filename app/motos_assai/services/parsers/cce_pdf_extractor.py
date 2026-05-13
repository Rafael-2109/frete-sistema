"""Parser deterministico de Carta de Correcao Eletronica (CCe) de NF-e.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §7.3
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 7

Suporta dois layouts observados em PRD (2026-05-13, fixtures NF 1729/1737/1757/1772/1779
e 1579/36673/36928):

1) Q.P.A. RELATORIO — emitidos pela "Q.p.a Distribuicao Ltda". Cabecalho fixo com
   "RELATORIO DE CARTA DE CORRECAO ELETRONICA" + bloco CORRECAO com 3 subtipos:
   - CORRECAO DE CHASSI (1 par ou N pares — SAINDO/ENTRANDO em linhas separadas)
   - DUPLICATAS (Numero/Vencimento/Valor)
   - Correcao de endereco (texto livre)

2) MOTOCHEFE Dados — emitidos pela "Motochefe" (CNPJ 09.089.839/0001-12). Cabecalho
   "Dados da Carta de Correcao Eletronica" + bloco "Texto" com:
   - CORRECAO DE CHASSI - SAINDO : MODELO CHASSI COR ENTRANDO : MODELO CHASSI COR
   - ENDERECO DE ENTREGA: ...

Retorna schema canonico:
- numero_cce (str | None)  — gerado como "CCe-<seq>-NF<numero_nf>" para log
- numero_nf_referenciada (str)
- chave_nfe (str | None)  — 44 digitos da chave NFe
- protocolo_cce (str | None)
- tipo_correcao (str)  — CHASSI | DUPLICATAS | ENDERECO | OUTRO
- chassis_corrigidos: list[tuple[str, str]]  — backward-compat (antigo, novo)
- chassis_detalhes: list[dict]  — novo, com modelo + cores
- duplicatas: list[dict]
- endereco_corrigido (str)
- texto_correcao_bruto (str)
- data_emissao (str | None)
- confianca (float)
- parser_usado (str)  — DETERMINISTICO_QPA | DETERMINISTICO_MOTOCHEFE | DETERMINISTICO_DESCONHECIDO
- formato_detectado (str)

Quando confianca < CONFIANCA_LIMIAR, caller deve acionar fallback LLM
(cce_llm_fallback.extrair_cce_via_llm).
"""
from __future__ import annotations

import io
import re
from typing import Dict, Any, List, Optional, Tuple

import pdfplumber


CONFIANCA_LIMIAR = 0.80

# Tipos de correcao reconhecidos
TIPO_CHASSI = 'CHASSI'
TIPO_DUPLICATAS = 'DUPLICATAS'
TIPO_ENDERECO = 'ENDERECO'
TIPO_OUTRO = 'OUTRO'

# Formatos de PDF
FORMATO_QPA = 'QPA_RELATORIO'
FORMATO_MOTOCHEFE = 'MOTOCHEFE_DADOS'
FORMATO_DESCONHECIDO = 'DESCONHECIDO'

# --- Detectores de formato ----------------------------------------------------
RE_FORMATO_QPA = re.compile(
    r'RELAT[ÓO]RIO\s+DE\s+CARTA\s+DE\s+CORRE[ÇC][ÃA]O\s+ELETR[ÔO]NICA',
    re.IGNORECASE,
)
RE_FORMATO_MOTOCHEFE = re.compile(
    r'Dados\s+da\s+Carta\s+de\s+Corre[çc][ãa]o\s+Eletr[ôo]nica',
    re.IGNORECASE,
)

# --- Q.P.A. extractors --------------------------------------------------------
# NF: linha "001 001729 3526 0453 7805 5400..." apos "CHAVE DE ACESSO"
RE_QPA_NF_LINHA = re.compile(
    r'CHAVE\s+DE\s+ACESSO\s*\n\s*(\d{3})\s+(\d{6,9})\s+([\d\s]{40,80})',
    re.IGNORECASE,
)
# Sequencia do evento (1, 2, 3...)
RE_QPA_SEQ = re.compile(
    r'EVENTO\s+DESCRI[ÇC][ÃA]O\s+DO\s+EVENTO\s+SEQUENCIA\s+DO\s+EVENTO\s+VERS[ÃA]O\s+DO\s+EVENTO\s*\n'
    r'\s*\d+\s+CARTA\s+DE\s+CORRE[ÇC][ÃA]O\s+ELETR[ÔO]NICA\s+(\d+)\s+[\d\.]+',
    re.IGNORECASE,
)
# Protocolo (15 digitos apos "Status da Carta")
RE_QPA_PROTOCOLO = re.compile(
    r'Status\s+da\s+Carta\s+(\d{12,18})',
    re.IGNORECASE,
)
# Data registro do evento — DD/MM/AA as HH:MM:SS
RE_QPA_DATA = re.compile(
    r'DATA\s+E\s+HORA\s+DO\s+REGISTRO\s+DO\s+EVENTO[\s\S]{0,200}?'
    r'(\d{2})/(\d{2})/(\d{2,4})\s+[àa]s\s+\d{2}:\d{2}',
    re.IGNORECASE,
)

# --- MOTOCHEFE extractors -----------------------------------------------------
RE_MOTOCHEFE_NF = re.compile(
    r'Nota\s+Fiscal\s+N[uú]mero\s+(\d+)\s*-\s*S[eé]rie\s+(\d+)',
    re.IGNORECASE,
)
RE_MOTOCHEFE_CHAVE = re.compile(r'Chave\s+(\d{40,50})', re.IGNORECASE)
RE_MOTOCHEFE_SEQ = re.compile(
    r'Sequencial\s+da\s+Carta\s+de\s+Corre[çc][ãa]o\s+(\d+)',
    re.IGNORECASE,
)
RE_MOTOCHEFE_DATA = re.compile(
    r'Data\s+da\s+Carta\s+de\s+Corre[çc][ãa]o\s+(\d{2})/(\d{2})/(\d{4})',
    re.IGNORECASE,
)
# CORRECAO DE CHASSI - SAINDO : MODELO CHASSI COR ENTRANDO : MODELO CHASSI COR
RE_MOTOCHEFE_PAR_CHASSI = re.compile(
    r'SAINDO\s*:?\s*([A-Z][A-Z0-9\-]*)\s+([A-Z0-9]{13,17})\s+([A-ZÀ-Ü]+)'
    r'[\s\S]{0,80}?'
    r'ENTRANDO\s*:?\s*([A-Z][A-Z0-9\-]*)\s+([A-Z0-9]{13,17})\s+([A-ZÀ-Ü]+)',
    re.IGNORECASE,
)

# --- Linha de chassi (formato Q.P.A. e fallback geral) ------------------------
# "DOT LA2025SA110004195 BRANCO"
# "X11-MINI MCBRX11M251107081 AZUL"
# "SOL 172922504672358 CINZA"
RE_LINHA_CHASSI = re.compile(
    r'^\s*([A-Z][A-Z0-9\-]{1,15})\s+([A-Z0-9]{13,17})\s+([A-ZÀ-Ü]+)\s*$',
    re.IGNORECASE,
)


class CceParseError(Exception):
    """Falha critica do parser deterministico — caller deve usar LLM fallback."""


def extrair_cce(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extrai dados estruturados de PDF de CCe.

    Args:
        pdf_bytes: bytes do PDF da Carta de Correcao.

    Returns:
        dict (schema completo na docstring do modulo).

    Raises:
        CceParseError: PDF sem texto extraivel ou estrutura minima ausente.
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

    formato = _detectar_formato(texto)

    if formato == FORMATO_QPA:
        dados = _parse_qpa(texto)
        dados['parser_usado'] = 'DETERMINISTICO_QPA'
    elif formato == FORMATO_MOTOCHEFE:
        dados = _parse_motochefe(texto)
        dados['parser_usado'] = 'DETERMINISTICO_MOTOCHEFE'
    else:
        # Formato desconhecido — tentar parser generico, escalar para LLM via baixa confianca
        dados = _parse_generico(texto)
        dados['parser_usado'] = 'DETERMINISTICO_DESCONHECIDO'

    dados['formato_detectado'] = formato

    if not dados.get('numero_nf_referenciada'):
        raise CceParseError(
            f'NF referenciada nao encontrada (formato={formato}). '
            f'Acione fallback LLM.'
        )

    dados['confianca'] = _calcular_confianca(dados)
    return dados


# =============================================================================
# Deteccao de formato
# =============================================================================

def _detectar_formato(texto: str) -> str:
    if RE_FORMATO_QPA.search(texto):
        return FORMATO_QPA
    if RE_FORMATO_MOTOCHEFE.search(texto):
        return FORMATO_MOTOCHEFE
    return FORMATO_DESCONHECIDO


# =============================================================================
# Parser Q.P.A. (layout "RELATORIO DE CARTA DE CORRECAO ELETRONICA")
# =============================================================================

def _parse_qpa(texto: str) -> Dict[str, Any]:
    """Extrai dados de PDF formato Q.P.A. RELATORIO."""
    # 1. NF + chave de acesso
    numero_nf = None
    chave_nfe = None
    m = RE_QPA_NF_LINHA.search(texto)
    if m:
        # group(1)=serie (3 digitos, descartado), group(2)=numero NF, group(3)=chave
        numero_nf = m.group(2)
        chave_raw = m.group(3)
        chave_nfe = re.sub(r'\s+', '', chave_raw)
        # Strip do "001729" → "1729" (sem zeros a esquerda — padroniza com Motochefe)
        numero_nf = numero_nf.lstrip('0') or '0'

    # 2. Sequencia da CCe
    seq_match = RE_QPA_SEQ.search(texto)
    sequencia = seq_match.group(1) if seq_match else '1'

    # 3. Protocolo
    proto_match = RE_QPA_PROTOCOLO.search(texto)
    protocolo = proto_match.group(1) if proto_match else None

    # 4. Data
    data_emissao = None
    dm = RE_QPA_DATA.search(texto)
    if dm:
        dia, mes, ano = dm.groups()
        if len(ano) == 2:
            ano = '20' + ano
        data_emissao = f'{dia}/{mes}/{ano}'

    # 5. Bloco CORRECAO (entre "CORRECAO" e "CONDICOES DE USO")
    bloco_correcao = _extrair_bloco_correcao_qpa(texto)
    tipo_correcao, conteudo = _classificar_correcao_qpa(bloco_correcao)

    chassis_detalhes: List[Dict[str, Any]] = []
    duplicatas: List[Dict[str, Any]] = []
    endereco_corrigido = ''

    if tipo_correcao == TIPO_CHASSI:
        chassis_detalhes = _extrair_chassis_qpa(conteudo)
    elif tipo_correcao == TIPO_DUPLICATAS:
        duplicatas = _extrair_duplicatas_qpa(conteudo)
    elif tipo_correcao == TIPO_ENDERECO:
        endereco_corrigido = _extrair_endereco_qpa(conteudo)

    chassis_corrigidos = [
        (d['chassi_antigo'], d['chassi_novo']) for d in chassis_detalhes
    ]

    numero_cce = f'CCe-{sequencia}-NF{numero_nf}' if numero_nf else None

    return {
        'numero_cce': numero_cce,
        'numero_nf_referenciada': numero_nf,
        'chave_nfe': chave_nfe,
        'protocolo_cce': protocolo,
        'tipo_correcao': tipo_correcao,
        'chassis_corrigidos': chassis_corrigidos,
        'chassis_detalhes': chassis_detalhes,
        'duplicatas': duplicatas,
        'endereco_corrigido': endereco_corrigido,
        'texto_correcao_bruto': bloco_correcao.strip(),
        'justificativa': '',
        'data_emissao': data_emissao,
    }


def _extrair_bloco_correcao_qpa(texto: str) -> str:
    """Retorna o miolo entre a secao 'CORRECAO' e 'CONDICOES DE USO'."""
    m = re.search(
        r'(?:^|\n)\s*CORRE[ÇC][ÃA]O\s*\n([\s\S]+?)(?:CONDI[ÇC][ÕO]ES\s+DE\s+USO|$)',
        texto, re.IGNORECASE,
    )
    return m.group(1) if m else ''


def _classificar_correcao_qpa(bloco: str) -> Tuple[str, str]:
    """Detecta subtipo do bloco CORRECAO e retorna (tipo, conteudo apos header)."""
    if not bloco.strip():
        return TIPO_OUTRO, ''

    # Subtipo chassi: header "CORRECAO DE CHASSI"
    m = re.search(
        r'CORRE[ÇC][ÃA]O\s+DE\s+CHASSI\s*\n([\s\S]+)$',
        bloco, re.IGNORECASE,
    )
    if m:
        return TIPO_CHASSI, m.group(1)

    # Subtipo duplicatas: header "DUPLICATAS"
    m = re.search(r'DUPLICATAS\s*\n([\s\S]+)$', bloco, re.IGNORECASE)
    if m:
        return TIPO_DUPLICATAS, m.group(1)

    # Subtipo endereco: header "Correcao de endereco"
    m = re.search(
        r'Corre[çc][ãa]o\s+de\s+endere[çc]o\s*\n([\s\S]+)$',
        bloco, re.IGNORECASE,
    )
    if m:
        return TIPO_ENDERECO, m.group(1)

    return TIPO_OUTRO, bloco


def _extrair_chassis_qpa(conteudo: str) -> List[Dict[str, Any]]:
    """Extrai chassis SAINDO/ENTRANDO do bloco CORRECAO DE CHASSI.

    Layout multi-linha Q.P.A.:
        SAINDO: DOT LA2025SA110004420 PRETO
               X11-MINI MCBRX11M251107081 AZUL
        ENTRANDO: DOT LA2025SA110006720 CINZA
               X11-MINI MCBRX11M251106043 BRANCO
    """
    saindo: List[Dict[str, str]] = []
    entrando: List[Dict[str, str]] = []
    estado: Optional[str] = None

    for linha in conteudo.splitlines():
        linha_stripped = linha.strip()
        if not linha_stripped:
            continue

        upper = linha_stripped.upper()

        # Detectar inicio SAINDO
        if upper.startswith('SAINDO'):
            estado = 'SAINDO'
            resto = re.sub(r'^SAINDO\s*:?\s*', '', linha_stripped, flags=re.IGNORECASE)
            item = _parse_linha_chassi(resto)
            if item:
                saindo.append(item)
            continue

        # Detectar inicio ENTRANDO
        if upper.startswith('ENTRANDO'):
            estado = 'ENTRANDO'
            resto = re.sub(r'^ENTRANDO\s*:?\s*', '', linha_stripped, flags=re.IGNORECASE)
            item = _parse_linha_chassi(resto)
            if item:
                entrando.append(item)
            continue

        # Linha de continuacao (sem prefixo)
        item = _parse_linha_chassi(linha_stripped)
        if not item:
            continue
        if estado == 'SAINDO':
            saindo.append(item)
        elif estado == 'ENTRANDO':
            entrando.append(item)

    # Parear 1:1 (saindo[i] vs entrando[i])
    chassis_detalhes: List[Dict[str, Any]] = []
    for i in range(min(len(saindo), len(entrando))):
        a, n = saindo[i], entrando[i]
        chassis_detalhes.append({
            'modelo': n.get('modelo') or a.get('modelo'),
            'chassi_antigo': a['chassi'],
            'chassi_novo': n['chassi'],
            'cor_antiga': a.get('cor'),
            'cor_nova': n.get('cor'),
        })

    return chassis_detalhes


def _parse_linha_chassi(linha: str) -> Optional[Dict[str, str]]:
    """Tenta extrair {modelo, chassi, cor} de uma linha unica."""
    m = RE_LINHA_CHASSI.match(linha.strip())
    if not m:
        return None
    modelo, chassi, cor = m.groups()
    return {
        'modelo': modelo.upper(),
        'chassi': chassi.upper(),
        'cor': cor.upper(),
    }


def _extrair_duplicatas_qpa(conteudo: str) -> List[Dict[str, Any]]:
    """Extrai dados de duplicatas. Layout:
        Numero 001
        Vencimento 09/06/2026
        Valor 34.800,00
    """
    # Cada duplicata pode ter os 3 campos. Buscar trincas.
    numeros = re.findall(r'N[uú]mero\s+(\S+)', conteudo, re.IGNORECASE)
    vencimentos = re.findall(r'Vencimento\s+(\d{2}/\d{2}/\d{2,4})', conteudo, re.IGNORECASE)
    valores = re.findall(r'Valor\s+([\d\.\,]+)', conteudo, re.IGNORECASE)

    n = max(len(numeros), len(vencimentos), len(valores))
    duplicatas: List[Dict[str, Any]] = []
    for i in range(n):
        duplicatas.append({
            'numero': numeros[i] if i < len(numeros) else None,
            'vencimento': vencimentos[i] if i < len(vencimentos) else None,
            'valor': valores[i] if i < len(valores) else None,
        })
    return duplicatas


def _extrair_endereco_qpa(conteudo: str) -> str:
    """Retorna o texto livre do endereco corrigido (primeira linha nao vazia)."""
    for linha in conteudo.splitlines():
        s = linha.strip()
        if s:
            return s[:500]
    return ''


# =============================================================================
# Parser MOTOCHEFE (layout "Dados da Carta de Correcao Eletronica")
# =============================================================================

def _parse_motochefe(texto: str) -> Dict[str, Any]:
    """Extrai dados de PDF formato MOTOCHEFE."""
    # 1. NF
    numero_nf = None
    m = RE_MOTOCHEFE_NF.search(texto)
    if m:
        numero_nf = m.group(1).lstrip('0') or '0'

    # 2. Chave
    chave_nfe = None
    cm = RE_MOTOCHEFE_CHAVE.search(texto)
    if cm:
        chave_nfe = cm.group(1)

    # 3. Sequencia
    sequencia = '1'
    sm = RE_MOTOCHEFE_SEQ.search(texto)
    if sm:
        sequencia = sm.group(1)

    # 4. Data
    data_emissao = None
    dm = RE_MOTOCHEFE_DATA.search(texto)
    if dm:
        dia, mes, ano = dm.groups()
        data_emissao = f'{dia}/{mes}/{ano}'

    # 5. Texto da correcao — tudo entre "Texto" e "Condição de Uso"
    bloco_correcao = _extrair_bloco_correcao_motochefe(texto)

    # 6. Tipo da correcao
    tipo_correcao = TIPO_OUTRO
    chassis_detalhes: List[Dict[str, Any]] = []
    endereco_corrigido = ''

    if re.search(r'CORRE[CÇ]AO\s+DE\s+CHASSI', bloco_correcao, re.IGNORECASE):
        tipo_correcao = TIPO_CHASSI
        chassis_detalhes = _extrair_chassis_motochefe(bloco_correcao)
    elif re.search(r'ENDERE[CÇ]O', bloco_correcao, re.IGNORECASE):
        tipo_correcao = TIPO_ENDERECO
        # Limpa boilerplate "ENDERECO DE ENTREGA:" e junta todas as linhas
        # uteis (CEP pode quebrar em linha separada apos remocao do label "Texto")
        texto_end = re.sub(
            r'ENDERE[CÇ]O\s+DE\s+ENTREGA\s*:?\s*',
            '',
            bloco_correcao,
            flags=re.IGNORECASE,
        ).strip()
        # Une linhas nao-vazias com espaco (mantem coerencia do endereco multi-linha)
        partes = [linha.strip() for linha in texto_end.splitlines() if linha.strip()]
        endereco_corrigido = ' '.join(partes)[:500]

    chassis_corrigidos = [
        (d['chassi_antigo'], d['chassi_novo']) for d in chassis_detalhes
    ]

    numero_cce = f'CCe-{sequencia}-NF{numero_nf}' if numero_nf else None

    return {
        'numero_cce': numero_cce,
        'numero_nf_referenciada': numero_nf,
        'chave_nfe': chave_nfe,
        'protocolo_cce': None,
        'tipo_correcao': tipo_correcao,
        'chassis_corrigidos': chassis_corrigidos,
        'chassis_detalhes': chassis_detalhes,
        'duplicatas': [],
        'endereco_corrigido': endereco_corrigido,
        'texto_correcao_bruto': bloco_correcao.strip(),
        'justificativa': '',
        'data_emissao': data_emissao,
    }


def _extrair_bloco_correcao_motochefe(texto: str) -> str:
    """Retorna o conteudo da correcao Motochefe.

    Layout (pdfplumber extrai zig-zag — label 'Texto' aparece NO MEIO):
        Data da Carta de Correção 04/05/2026
        CORRECAO DE CHASSI - SAINDO : ROMA HL5TCAH37S9W75986 BEGE ENTRANDO :
        Texto
        ROMA HL5TCAH30S9W75986 BEGE
        A Carta de Correção é disciplinada...

    Estrategia: pegar tudo entre "Data da Carta de Correcao DD/MM/AAAA" e
    "A Carta de Correcao e disciplinada" (boilerplate legal), REMOVER a palavra
    'Texto' solta entre linhas (artefato de pdfplumber sobre celula de tabela).
    """
    m = re.search(
        r'Data\s+da\s+Carta\s+de\s+Corre[çc][ãa]o\s+\d{2}/\d{2}/\d{4}\s*\n'
        r'([\s\S]+?)'
        r'(?:A\s+Carta\s+de\s+Corre[çc][ãa]o\s+[eé]\s+disciplinada|Condi[çc][ãa]o\s+de\s+Uso|$)',
        texto, re.IGNORECASE,
    )
    bruto = m.group(1) if m else ''

    # Remove a linha solitaria "Texto" (label de celula da tabela que pdfplumber
    # extrai isolada) — assim o conteudo se torna contiguo
    linhas = [
        linha for linha in bruto.splitlines()
        if linha.strip().lower() != 'texto'
    ]
    return '\n'.join(linhas)


def _extrair_chassis_motochefe(bloco: str) -> List[Dict[str, Any]]:
    """Extrai pares de chassis do formato compactado Motochefe.

    Formato:
        CORRECAO DE CHASSI - SAINDO : ROMA HL5TCAH37S9W75986 BEGE ENTRANDO :
        ROMA HL5TCAH30S9W75986 BEGE
    """
    chassis_detalhes: List[Dict[str, Any]] = []
    # Compactar quebras de linha — o regex aceita ate 80 chars de gap entre SAINDO/ENTRANDO
    for m in RE_MOTOCHEFE_PAR_CHASSI.finditer(bloco):
        # group(1)=modelo_a (descartado — usamos modelo_n), 2=chassi_a, 3=cor_a,
        # 4=modelo_n, 5=chassi_n, 6=cor_n
        chassi_a = m.group(2)
        cor_a = m.group(3)
        modelo_n = m.group(4)
        chassi_n = m.group(5)
        cor_n = m.group(6)
        chassis_detalhes.append({
            'modelo': modelo_n.upper(),
            'chassi_antigo': chassi_a.upper(),
            'chassi_novo': chassi_n.upper(),
            'cor_antiga': cor_a.upper(),
            'cor_nova': cor_n.upper(),
        })
    return chassis_detalhes


# =============================================================================
# Parser generico (formato desconhecido — fallback fraco antes do LLM)
# =============================================================================

def _parse_generico(texto: str) -> Dict[str, Any]:
    """Parser de ultima esperanca: extrai apenas o que conseguir.

    Pensado para gerar confianca baixa que aciona LLM fallback.
    """
    # NF: primeiro numero apos "Nota Fiscal" ou "NF"
    numero_nf = None
    m = re.search(
        r'(?:Nota\s+Fiscal|NF[\-\s]?e?)[\s:]*N[uú]?[mM]?[eE]?[rR]?[oO]?\s*(\d{1,15})',
        texto, re.IGNORECASE,
    )
    if m:
        numero_nf = m.group(1).lstrip('0') or '0'

    # Data
    data_emissao = None
    dm = re.search(r'\b(\d{2})/(\d{2})/(\d{2,4})\b', texto)
    if dm:
        dia, mes, ano = dm.groups()
        if len(ano) == 2:
            ano = '20' + ano
        data_emissao = f'{dia}/{mes}/{ano}'

    # Chassis em pares heuristicos (linhas SAINDO/ENTRANDO sequenciais)
    chassis_detalhes = _extrair_chassis_qpa(texto)

    # Fallback motochefe (regex compactado)
    if not chassis_detalhes:
        chassis_detalhes = _extrair_chassis_motochefe(texto)

    # Heuristica par-impar caso nada mais funcione
    if not chassis_detalhes:
        chassis_raw = re.findall(r'\b([A-Z0-9]{13,17})\b', texto)
        if chassis_raw and len(chassis_raw) >= 2 and len(chassis_raw) % 2 == 0:
            for i in range(0, len(chassis_raw), 2):
                chassis_detalhes.append({
                    'modelo': None,
                    'chassi_antigo': chassis_raw[i].upper(),
                    'chassi_novo': chassis_raw[i + 1].upper(),
                    'cor_antiga': None,
                    'cor_nova': None,
                })

    chassis_corrigidos = [
        (d['chassi_antigo'], d['chassi_novo']) for d in chassis_detalhes
    ]

    tipo_correcao = TIPO_CHASSI if chassis_detalhes else TIPO_OUTRO

    return {
        'numero_cce': None,
        'numero_nf_referenciada': numero_nf,
        'chave_nfe': None,
        'protocolo_cce': None,
        'tipo_correcao': tipo_correcao,
        'chassis_corrigidos': chassis_corrigidos,
        'chassis_detalhes': chassis_detalhes,
        'duplicatas': [],
        'endereco_corrigido': '',
        'texto_correcao_bruto': '',
        'justificativa': '',
        'data_emissao': data_emissao,
    }


# =============================================================================
# Confianca
# =============================================================================

def _calcular_confianca(dados: Dict[str, Any]) -> float:
    """Heuristica de confianca 0.0 a 1.0.

    Pesos:
    - 0.20  formato detectado (Q.P.A. ou MOTOCHEFE — nao DESCONHECIDO)
    - 0.20  tipo_correcao identificado (nao OUTRO)
    - 0.20  numero_nf_referenciada presente
    - 0.30  conteudo principal do tipo presente (chassis OU duplicatas OU endereco)
    - 0.10  data_emissao presente

    Total: 1.0
    """
    score = 0.0

    formato = dados.get('formato_detectado')
    if formato in (FORMATO_QPA, FORMATO_MOTOCHEFE):
        score += 0.20

    tipo = dados.get('tipo_correcao')
    if tipo and tipo != TIPO_OUTRO:
        score += 0.20

    if dados.get('numero_nf_referenciada'):
        score += 0.20

    # Conteudo principal do tipo
    if tipo == TIPO_CHASSI and dados.get('chassis_corrigidos'):
        score += 0.30
    elif tipo == TIPO_DUPLICATAS and dados.get('duplicatas'):
        score += 0.30
    elif tipo == TIPO_ENDERECO and dados.get('endereco_corrigido'):
        score += 0.30
    elif tipo == TIPO_OUTRO and dados.get('chassis_corrigidos'):
        # Parser generico achou chassis sem identificar tipo — peso menor
        score += 0.15

    if dados.get('data_emissao'):
        score += 0.10

    return min(1.0, round(score, 2))
