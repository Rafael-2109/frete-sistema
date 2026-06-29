"""Parser OFX (SGML) para o modulo Pessoal — extrato NuConta e fatura de cartao Nubank.

Cobre os dois tipos de mensagem que o Nubank exporta:
- ``<BANKMSGSRSV1>`` / ``<STMTRS>``        -> extrato de conta corrente (ACCTTYPE CHECKING)
- ``<CREDITCARDMSGSRSV1>`` / ``<CCSTMTRS>`` -> fatura de cartao de credito

Mapeamento por ``<STMTTRN>`` para o modelo (PessoalTransacao guarda valor SEMPRE positivo):
- data       = DTPOSTED
- historico  = MEMO (fallback NAME)
- valor      = abs(TRNAMT)
- tipo       = 'credito' se TRNTYPE=CREDIT (ou TRNAMT > 0) senao 'debito'
- documento  = FITID

Transacoes com TRNAMT == 0 sao ignoradas (ruido de fatura, ex.: juros 0,00).

Encoding: o Nubank exporta o extrato em UTF-8 e a fatura em USASCII/CHARSET 1252.
``parsear_ofx_pessoal`` recebe bytes e detecta o encoding pelo header OFX (com
fallback utf-8 -> latin-1), preservando acentos do MEMO.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional
import re

from app.pessoal.services.parsers.base_parser import (
    TransacaoRaw, normalizar_historico,
)


@dataclass
class ResultadoOFX:
    """Resultado do parse de um arquivo OFX."""
    tipo: str  # 'extrato' (conta corrente) | 'cartao' (cartao de credito)
    acctid: Optional[str] = None
    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None
    transacoes: list[TransacaoRaw] = field(default_factory=list)


# =============================================================================
# DETECCAO / ENCODING
# =============================================================================
def detectar_ofx(conteudo) -> bool:
    """True se o conteudo (bytes ou str) parece ser um arquivo OFX."""
    if isinstance(conteudo, bytes):
        amostra = conteudo[:512].decode('ascii', errors='ignore')
    else:
        amostra = conteudo[:512]
    amostra = amostra.upper()
    return 'OFXHEADER' in amostra or '<OFX>' in amostra


def _decodificar(conteudo_bytes: bytes) -> str:
    """Decodifica os bytes do OFX respeitando o header ENCODING/CHARSET.

    Nubank: extrato = ENCODING:UTF-8; fatura = ENCODING:USASCII + CHARSET:1252.
    Fallback robusto: tenta o encoding do header, depois utf-8, depois latin-1.
    """
    head = conteudo_bytes[:400].decode('ascii', errors='ignore').upper()
    candidatos = []
    if 'ENCODING:UTF-8' in head:
        candidatos.append('utf-8')
    if 'CHARSET:1252' in head or 'ENCODING:USASCII' in head:
        candidatos.append('cp1252')
    # Fallbacks gerais
    candidatos += ['utf-8', 'cp1252', 'latin-1']

    for enc in candidatos:
        try:
            return conteudo_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    # latin-1 nunca falha, mas garante retorno
    return conteudo_bytes.decode('latin-1', errors='replace')


# =============================================================================
# EXTRACAO DE TAGS SGML
# =============================================================================
def _extrair_tag(bloco: str, tag: str) -> Optional[str]:
    """Extrai valor de uma tag OFX/SGML: ``<TAG>valor`` (sem fechamento) ou ``<TAG>valor</TAG>``."""
    m = re.search(rf'<{tag}>([^<\r\n]+)', bloco, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_data_ofx(valor: Optional[str]) -> Optional[date]:
    """Converte ``20260608000000[-3:BRT]`` -> date(2026, 6, 8)."""
    if not valor:
        return None
    m = re.match(r'(\d{4})(\d{2})(\d{2})', valor.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _parse_valor_ofx(valor: Optional[str]) -> Optional[Decimal]:
    """Converte ``-10.00`` / ``3000.00`` -> Decimal (mantem o sinal)."""
    if valor is None or not valor.strip():
        return None
    try:
        return Decimal(valor.strip())
    except InvalidOperation:
        return None


# =============================================================================
# PARSE PRINCIPAL
# =============================================================================
def parsear_ofx_pessoal(conteudo_bytes: bytes) -> ResultadoOFX:
    """Parseia um arquivo OFX (bytes) em ResultadoOFX.

    Levanta ValueError se o conteudo nao for um OFX reconhecivel.
    """
    if not detectar_ofx(conteudo_bytes):
        raise ValueError('Conteudo nao e um arquivo OFX.')

    conteudo = _decodificar(conteudo_bytes)
    upper = conteudo.upper()

    # Tipo de conta pela secao OFX
    if '<CREDITCARDMSGSRSV1>' in upper or '<CCSTMTRS>' in upper:
        tipo = 'cartao'
    else:
        tipo = 'extrato'

    acctid = _extrair_tag(conteudo, 'ACCTID')

    # Periodo (BANKTRANLIST)
    periodo_inicio = _parse_data_ofx(_extrair_tag(conteudo, 'DTSTART'))
    periodo_fim = _parse_data_ofx(_extrair_tag(conteudo, 'DTEND'))

    transacoes: list[TransacaoRaw] = []
    for bloco in re.findall(r'<STMTTRN>(.*?)</STMTTRN>', conteudo, re.DOTALL | re.IGNORECASE):
        t = _parsear_transacao(bloco)
        if t is not None:
            transacoes.append(t)

    return ResultadoOFX(
        tipo=tipo,
        acctid=acctid,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        transacoes=transacoes,
    )


def resolver_conta_ofx(acctid: Optional[str], tipo: str) -> Optional[int]:
    """Resolve a PessoalConta de um OFX a partir do ACCTID e do tipo.

    1. Match por ``numero_conta`` == ACCTID (comparacao alfanumerica e, para contas
       numericas, por digitos). Cobre o UUID do cartao e a conta CHECKING.
    2. Fallback: unica conta Nubank ativa do tipo correspondente.

    Retorna conta_id ou None.
    """
    from app.pessoal.models import PessoalConta

    tipo_conta = 'cartao_credito' if tipo == 'cartao' else 'conta_corrente'

    if acctid:
        acct_alnum = re.sub(r'\W', '', acctid).lower()
        acct_dig = re.sub(r'\D', '', acctid)
        contas = PessoalConta.query.filter_by(tipo=tipo_conta, ativa=True).all()
        for c in contas:
            if not c.numero_conta:
                continue
            n_alnum = re.sub(r'\W', '', c.numero_conta).lower()
            n_dig = re.sub(r'\D', '', c.numero_conta)
            if n_alnum == acct_alnum or (acct_dig and n_dig and n_dig == acct_dig):
                return c.id

    # Fallback: unica conta Nubank ativa do tipo (recurso e dedicado ao Nubank)
    nubank = PessoalConta.query.filter_by(
        banco='nubank', tipo=tipo_conta, ativa=True,
    ).all()
    if len(nubank) == 1:
        return nubank[0].id
    return None


def _parsear_transacao(bloco: str) -> Optional[TransacaoRaw]:
    """Converte um bloco ``<STMTTRN>`` em TransacaoRaw. Retorna None se invalido/zero."""
    dt = _parse_data_ofx(_extrair_tag(bloco, 'DTPOSTED'))
    valor_signed = _parse_valor_ofx(_extrair_tag(bloco, 'TRNAMT'))
    if dt is None or valor_signed is None:
        return None
    if valor_signed == 0:
        return None  # ignora ruido (ex.: juros 0,00)

    memo = _extrair_tag(bloco, 'MEMO') or _extrair_tag(bloco, 'NAME') or ''
    memo = memo.strip()
    if not memo:
        return None

    trntype = (_extrair_tag(bloco, 'TRNTYPE') or '').upper()
    if trntype == 'CREDIT':
        tipo = 'credito'
    elif trntype == 'DEBIT':
        tipo = 'debito'
    else:
        # Sem TRNTYPE confiavel: usa o sinal do valor
        tipo = 'credito' if valor_signed > 0 else 'debito'

    fitid = _extrair_tag(bloco, 'FITID')

    return TransacaoRaw(
        data=dt,
        historico=memo,
        descricao=None,
        historico_completo=normalizar_historico(memo),
        documento=fitid,
        valor=abs(valor_signed),
        tipo=tipo,
    )
