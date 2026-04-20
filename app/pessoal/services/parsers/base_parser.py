"""Helpers compartilhados para parsers de extratos bancarios."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional
import hashlib
import re
from unidecode import unidecode


@dataclass
class TransacaoRaw:
    """Transacao parseada do CSV, antes de salvar no banco."""
    data: date
    historico: str
    descricao: Optional[str] = None
    historico_completo: Optional[str] = None
    documento: Optional[str] = None
    valor: Decimal = Decimal('0')
    tipo: str = 'debito'  # debito | credito
    saldo: Optional[Decimal] = None
    # Cartao
    valor_dolar: Optional[Decimal] = None
    parcela_atual: Optional[int] = None
    parcela_total: Optional[int] = None
    identificador_parcela: Optional[str] = None
    titular_cartao: Optional[str] = None
    ultimos_digitos_cartao: Optional[str] = None
    # Controle
    eh_provisoria: bool = False  # "Ultimos Lancamentos"


def parse_valor_brasileiro(texto: str) -> Decimal:
    """Parse valor brasileiro: "-1.234,56" -> Decimal('1234.56'). Retorna valor ABSOLUTO."""
    if not texto or not texto.strip():
        return Decimal('0')
    texto = texto.strip().strip('"').strip("'").strip()
    # Remove R$ prefix
    texto = texto.replace('R$', '').strip()
    # Track sign
    negativo = '-' in texto
    texto = texto.replace('-', '').strip()
    if not texto:
        return Decimal('0')
    # Brazilian format: 1.234,56 -> 1234.56
    texto = texto.replace('.', '').replace(',', '.')
    try:
        val = Decimal(texto)
        return val  # Always positive (abs)
    except InvalidOperation:
        return Decimal('0')


def parse_data_brasileira(texto: str, ano_referencia: int = None) -> Optional[date]:
    """Parse data brasileira: '15/01' ou '15/01/2025' -> date."""
    if not texto or not texto.strip():
        return None
    texto = texto.strip()
    partes = texto.split('/')
    if len(partes) == 2:
        dia, mes = int(partes[0]), int(partes[1])
        ano = ano_referencia or date.today().year
        return date(ano, mes, dia)
    elif len(partes) == 3:
        dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
        if ano < 100:
            ano += 2000
        return date(ano, mes, dia)
    return None


def extrair_cpf_cnpj(texto: str) -> Optional[str]:
    """Extrai CPF (11 digitos) ou CNPJ (14 digitos) de um texto.

    Aceita formatos com ou sem mascara:
    - CPF: "123.456.789-00", "12345678900"
    - CNPJ: "12.345.678/0001-99", "12345678000199"

    Retorna so digitos (11 ou 14 chars) ou None. CNPJ tem prioridade sobre CPF
    quando ambos aparecerem no mesmo texto (mais especifico).

    Nao valida digitos verificadores — so extrai o formato.
    """
    if not texto:
        return None

    # CNPJ primeiro (mais especifico, 14 digitos)
    match = re.search(
        r'\b(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})\b',
        texto,
    )
    if match:
        return ''.join(match.groups())

    # CPF (11 digitos)
    match = re.search(
        r'\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b',
        texto,
    )
    if match:
        digitos = ''.join(match.groups())
        # Evitar falsos positivos: sequencia de 11 digitos iguais (ex: 00000000000)
        if len(set(digitos)) > 1:
            return digitos

    return None


def gerar_hash_transacao(conta_id: int, data: date, historico: str, valor: Decimal, tipo: str, documento: str = '', sequencia: int = 0) -> str:
    """Gera hash SHA256 para deduplicacao.

    O parametro sequencia diferencia transacoes identicas no mesmo dia
    (ex: 3x GRAN COFFEE R$5,00 em 05/12 -> sequencias 0, 1, 2).
    """
    conteudo = f"{conta_id}|{data.isoformat()}|{normalizar_historico(historico)}|{valor}|{tipo}|{documento or ''}|{sequencia}"
    return hashlib.sha256(conteudo.encode('utf-8')).hexdigest()


def normalizar_historico(texto: str) -> str:
    """Normaliza historico: upper, strip, unidecode, colapsar espacos."""
    if not texto:
        return ''
    texto = unidecode(texto).upper().strip()
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def limpar_prefixo_descricao(texto: str) -> str:
    """Remove prefixos comuns de descricoes Bradesco: Des:, Rem:, Remet., Dest., Dest:"""
    if not texto:
        return ''
    texto = texto.strip()
    prefixos = [
        r'^Des:\s*', r'^Rem:\s*', r'^Remet\.\s*', r'^Dest\.\s*', r'^Dest:\s*',
        r'^Fav:\s*', r'^Fav\.\s*', r'^Ben:\s*', r'^Benef\.\s*',
    ]
    for prefixo in prefixos:
        texto = re.sub(prefixo, '', texto, flags=re.IGNORECASE)
    return texto.strip()


def remover_data_transacao(texto: str, data_transacao: date) -> str:
    """Remove DD/MM do texto quando corresponde a data da transacao.

    Diferencia data da transacao (redundante) de parcela ou outra data:
    - "Pix XYZ 10/11" com data=10/11/2025 -> "Pix XYZ" (remove, e a data)
    - "Compra 3/12" com data=15/01/2025 -> "Compra 3/12" (mantem, e parcela)
    - "Compra 10/11/2025" com data=10/11/2025 -> nao mexe (DD/MM/YYYY e ignorado)

    Args:
        texto: historico ou descricao original.
        data_transacao: date da transacao.

    Returns: texto com a data DD/MM removida (se matchou) ou inalterado.
    """
    if not texto or not data_transacao:
        return texto or ''

    dia = data_transacao.day
    mes = data_transacao.month

    def _substituir(m):
        d, m_val = int(m.group(1)), int(m.group(2))
        if d == dia and m_val == mes:
            return ''  # Remove — e a data da transacao (redundante)
        return m.group(0)  # Mantem — parcela ou outra data

    # Match DD/MM (1-2 digitos cada), mas NAO DD/MM/YYYY (negative lookahead /)
    resultado = re.sub(r'\b(\d{1,2})/(\d{1,2})\b(?!/)', _substituir, texto)

    # Limpar espacos extras SOMENTE se algo foi removido
    if resultado != texto:
        resultado = re.sub(r'\s+', ' ', resultado).strip()

    return resultado


def remover_todas_datas(texto: str) -> str:
    """Remove TODAS as datas DD/MM do texto (para PIX e transacoes sem parcela).

    Diferente de remover_data_transacao() que so remove a data exata da transacao,
    esta funcao remove qualquer DD/MM (exceto DD/MM/YYYY).

    Uso: transacoes PIX nunca sao parceladas, entao qualquer DD/MM no texto
    e uma data (geralmente D-1 ou D+1, nao parcela).
    """
    if not texto:
        return texto or ''

    resultado = re.sub(r'\b\d{1,2}/\d{1,2}\b(?!/)', '', texto)

    if resultado != texto:
        resultado = re.sub(r'\s+', ' ', resultado).strip()

    return resultado


def _eh_pix(historico: str) -> bool:
    """Verifica se transacao e PIX (case insensitive, apos normalize)."""
    if not historico:
        return False
    h = historico.upper()
    return 'PIX' in h or 'TRANSF PIX' in h


def extrair_parcela(historico: str) -> tuple:
    """Extrai parcela do historico: 'LOJA 3/12' -> (3, 12). Retorna (None, None) se nao encontrar."""
    if not historico:
        return (None, None)
    match = re.search(r'(\d{1,2})/(\d{1,2})(?:\s|$)', historico)
    if match:
        atual = int(match.group(1))
        total = int(match.group(2))
        if 1 <= atual <= total <= 99:
            return (atual, total)
    return (None, None)


def gerar_identificador_parcela(historico: str) -> Optional[str]:
    """Gera identificador para agrupar parcelas: remove 'N/M' do historico."""
    if not historico:
        return None
    parcela_atual, parcela_total = extrair_parcela(historico)
    if parcela_atual is None:
        return None
    # Remove a parte N/M e normaliza
    texto = re.sub(r'\d{1,2}/\d{1,2}', '', historico).strip()
    return normalizar_historico(texto)


# =============================================================================
# AUTO-DETECCAO DE TIPO CSV
# =============================================================================

@dataclass
class ResultadoDeteccao:
    """Resultado da auto-deteccao de tipo de CSV Bradesco."""
    tipo: str = 'desconhecido'  # extrato_cc | fatura_cartao | desconhecido
    confianca: float = 0.0  # 0.0 a 1.0
    agencia: Optional[str] = None  # Extraida do header CC
    conta: Optional[str] = None  # Extraida do header CC
    digitos_cartao: list[str] = field(default_factory=list)  # Digitos encontrados na fatura


def detectar_tipo_csv(conteudo: str) -> ResultadoDeteccao:
    """Detecta automaticamente se o CSV e extrato CC ou fatura de cartao Bradesco.

    Analisa as primeiras 30 linhas buscando fingerprints:
    - Cartao: "FATURA", "TOTAL DA FATURA", situacao PAGO/ABERTA, titulares NOME;;;DDDD
    - CC: "AGENCIA"/"AG:", "CONTA"/"C/C", colunas Hist+Docto

    Sistema de pontuacao: cada sinal da pontos, tipo com mais pontos vence.
    Minimo 3 pontos para confianca > 0.
    """
    resultado = ResultadoDeteccao()

    linhas = conteudo.splitlines()
    primeiras = linhas[:30]

    pontos_cartao = 0
    pontos_cc = 0

    for linha_raw in primeiras:
        linha = linha_raw.strip()
        if not linha:
            continue

        campos = [c.strip().strip('"') for c in linha.split(';')]
        texto_upper = linha.upper()

        # --- Sinais de FATURA CARTAO ---
        if 'FATURA' in texto_upper and 'TOTAL' not in texto_upper:
            pontos_cartao += 2

        if 'TOTAL DA FATURA' in texto_upper or 'TOTAL GERAL' in texto_upper:
            pontos_cartao += 2

        if re.search(r'\b(PAGO|ABERTA)\b', texto_upper):
            pontos_cartao += 1

        # Detectar titular: NOME EM MAIUSCULAS + ultimos campos com 4-5 digitos
        if len(campos) >= 2:
            primeiro = campos[0].strip()
            ultimo_preenchido = None
            for c in reversed(campos):
                c = c.strip()
                if c:
                    ultimo_preenchido = c
                    break
            if (ultimo_preenchido and re.match(r'^\d{4,5}$', ultimo_preenchido)
                    and primeiro and re.match(r'^[A-Z\s]{4,}$', primeiro)):
                pontos_cartao += 3
                resultado.digitos_cartao.append(ultimo_preenchido)

        # --- Sinais de EXTRATO CC ---
        if 'AGENCIA' in texto_upper or re.search(r'\bAG[\s:]+\d', texto_upper):
            pontos_cc += 2
            match = re.search(r'AG(?:ENCIA)?[\s:]*(\d+)', texto_upper)
            if match:
                resultado.agencia = match.group(1)

        if 'CONTA' in texto_upper or 'C/C' in texto_upper:
            pontos_cc += 2
            match = re.search(r'(?:CONTA|C/C)[\s:]*(\d[\d.-]+)', texto_upper)
            if match:
                resultado.conta = match.group(1)

        # Colunas tipicas de extrato CC
        if (any('HIST' in c.upper() for c in campos[:3])
                and any('DOCTO' in c.upper() or 'DOC' in c.upper() for c in campos[:5])):
            pontos_cc += 3

        if 'CREDITO' in texto_upper and 'DEBITO' in texto_upper and 'SALDO' in texto_upper:
            pontos_cc += 2

    # Decidir tipo
    if pontos_cartao > pontos_cc and pontos_cartao >= 3:
        resultado.tipo = 'fatura_cartao'
        resultado.confianca = min(1.0, pontos_cartao / 10.0)
    elif pontos_cc > pontos_cartao and pontos_cc >= 3:
        resultado.tipo = 'extrato_cc'
        resultado.confianca = min(1.0, pontos_cc / 10.0)
    else:
        # Empate ou pontuacao baixa
        resultado.tipo = 'desconhecido'
        resultado.confianca = 0.0

    return resultado


def resolver_conta(deteccao: ResultadoDeteccao) -> Optional[int]:
    """Resolve a conta bancaria a partir do resultado da deteccao.

    CC: match por numero_conta (normalizado, sem pontos/tracos).
        Fallback: se so 1 CC ativa, retorna ela.
    Cartao: match por ultimos_digitos_cartao (primeiro digito encontrado).
    Desconhecido: retorna None.

    Retorna conta_id ou None.
    """
    # Import lazy para evitar circular
    from app.pessoal.models import PessoalConta

    if deteccao.tipo == 'desconhecido':
        return None

    if deteccao.tipo == 'extrato_cc':
        # Tentar match por numero_conta
        if deteccao.conta:
            conta_normalizada = re.sub(r'[.\-\s]', '', deteccao.conta)
            contas_cc = PessoalConta.query.filter_by(
                tipo='conta_corrente', ativa=True
            ).all()
            for conta in contas_cc:
                if conta.numero_conta:
                    numero_normalizado = re.sub(r'[.\-\s]', '', conta.numero_conta)
                    if numero_normalizado == conta_normalizada:
                        return conta.id
        # Fallback: se so 1 CC ativa, retorna ela
        contas_cc = PessoalConta.query.filter_by(
            tipo='conta_corrente', ativa=True
        ).all()
        if len(contas_cc) == 1:
            return contas_cc[0].id
        return None

    if deteccao.tipo == 'fatura_cartao':
        # Match pelo primeiro digito encontrado
        if deteccao.digitos_cartao:
            digitos = deteccao.digitos_cartao[0]
            conta = PessoalConta.query.filter_by(
                tipo='cartao_credito',
                ultimos_digitos_cartao=digitos,
                ativa=True,
            ).first()
            if conta:
                return conta.id
        # Sem digitos — nao tem como resolver cartao
        return None

    return None
