# -*- coding: utf-8 -*-
"""Service de baixa de credores em lote (par SICOOB + DESAGIO) — PREVIEW READ-only.

Passo 1a da skill `baixando-credores-lote-odoo`: a partir de uma planilha de
credores, localiza a fatura de compra (`in_invoice`) pelo `name` (coluna FT REF =
CMPMP), valida saldo/company/partner/journals e calcula o PLANO de pares
`account.payment` SICOOB (parcela) + DESAGIO (desagio) por data de vencimento.

ESTE MODULO NAO ESCREVE NO ODOO. Apenas `search_read` (READ). O WRITE real
(criar/postar/reconciliar pagamento) e o passo 1b — reusara `BaixaPagamentosService`.

Decisoes ancoradas no pre-flight Odoo (2026-06-18, validado ao vivo):
- Companies cobertas: FB(1) e LF(5). SC(3)/CD(4) nao tem journal bancario ->
  `BLOQUEADO_CROSS_COMPANY` (Fase 2). Ver `COMPANIES_SEM_JOURNAL_BANCARIO`.
- Journal DESAGIO (1025, type cash) EXISTE SOMENTE na FB. LF tem SICOOB (386) mas
  NAO tem DESAGIO -> desagio>0 em LF e' `BLOQUEADO_SEM_JOURNAL_DESAGIO` (par nao
  lancavel); desagio==0 em LF lanca so o SICOOB.
- `amount_residual` payable e' NEGATIVO -> usar abs() (gotcha O3).
"""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

import openpyxl

from app.financeiro.constants import (
    JOURNAL_SICOOB_POR_COMPANY,
    JOURNAL_DESAGIO_ID,
    COMPANIES_SEM_JOURNAL_BANCARIO,
    COMPANY_IDS_ODOO,
)

# =============================================================================
# STATUS (por linha) — superset do DESIGN + estados ancorados no pre-flight
# =============================================================================
STATUS_DRY_RUN_OK = 'DRY_RUN_OK'
STATUS_BLOQUEADO_SALDO = 'BLOQUEADO_SALDO'
STATUS_BLOQUEADO_AMBIGUO = 'BLOQUEADO_AMBIGUO'
STATUS_BLOQUEADO_CROSS_COMPANY = 'BLOQUEADO_CROSS_COMPANY'
STATUS_BLOQUEADO_NAO_ENCONTRADA = 'BLOQUEADO_NAO_ENCONTRADA'
STATUS_BLOQUEADO_VALOR = 'BLOQUEADO_VALOR'
STATUS_BLOQUEADO_SEM_JOURNAL_SICOOB = 'BLOQUEADO_SEM_JOURNAL_SICOOB'
STATUS_BLOQUEADO_SEM_JOURNAL_DESAGIO = 'BLOQUEADO_SEM_JOURNAL_DESAGIO'
STATUS_BLOQUEADO_SEM_PAYABLE = 'BLOQUEADO_SEM_PAYABLE'
STATUS_PULADO_SEM_DADOS = 'PULADO_SEM_DADOS'
STATUS_JA_PROCESSADO = 'JA_PROCESSADO'

# Conjunto de status que indicam "pronto para WRITE no passo 1b"
STATUS_OK = {STATUS_DRY_RUN_OK}

# Context multi-company para search_read (FB/SC/CD/LF) — sem ele o Odoo filtra
# pela company default do usuario e pode nao achar faturas de LF.
_CTX_MULTI_COMPANY = {'allowed_company_ids': [1, 3, 4, 5]}

CAMPOS_MOVE = ['id', 'name', 'move_type', 'state', 'company_id', 'partner_id',
               'amount_residual', 'amount_total']
CAMPOS_LINE = ['id', 'name', 'account_id', 'account_type', 'debit', 'credit',
               'amount_residual', 'reconciled', 'partner_id', 'company_id',
               'date_maturity', 'move_id']

# Sinonimos de cabecalho (normalizados: sem acento, upper, espaco unico)
_ALIASES = {
    'credor': {'CREDOR', 'FORNECEDOR', 'NOME', 'BENEFICIARIO'},
    'ft_ref': {'FT REF', 'FTREF', 'REF FT', 'FT', 'FATURA', 'CMPMP',
               'REF FATURA', 'TITULO', 'NF'},
    'valor_parcela': {'VALOR PARCELA', 'VL PARCELA', 'PARCELA', 'VALOR',
                      'VALOR SICOOB'},
    'valor_desagio': {'VALOR DESAGIO', 'VL DESAGIO', 'DESAGIO'},
    'ref_pg_sicoob': {'REF PG SICOOB', 'REF PG', 'REF SICOOB', 'PG SICOOB',
                      'REFERENCIA PG SICOOB'},
    'empresa': {'EMPRESA', 'CIA', 'COMPANY', 'FILIAL', 'CIA EMPRESA'},
}

# Tokens de cabecalho que indicam coluna de data NAO-vencimento. Colunas nao-mapeadas
# cujo header contenha qualquer um destes NAO sao tratadas como vencimento, mesmo que os
# valores sejam datas (evita confundir EMISSAO / data da NF / competencia com vencimento).
_HEADERS_DATA_NAO_VENC = {
    'EMISSAO', 'EMISSAO NF', 'NF', 'NOTA', 'NUMERO', 'NUM', 'COMPETENCIA',
    'PAGAMENTO', 'PAGTO', 'PAGO', 'BAIXA', 'CRIACAO', 'CADASTRO', 'ENTRADA', 'SAIDA',
}


# =============================================================================
# DATACLASSES
# =============================================================================
@dataclass
class LinhaCredor:
    idx: int                       # numero da linha na planilha (1-based, com header)
    credor: str
    ft_ref: str                    # name da fatura in_invoice (CMPMP)
    valor_parcela: float           # -> par SICOOB
    valor_desagio: float           # -> par DESAGIO
    datas: List[date]              # vencimentos (1..N)
    empresa: Optional[str] = None  # declarado na planilha (informativo)
    ref_pg_sicoob: Optional[str] = None  # coluna de saida; preenchido = JA_PROCESSADO


@dataclass
class Par:
    tipo: str                      # 'SICOOB' | 'DESAGIO'
    valor: float
    journal_id: Optional[int]
    data: date


@dataclass
class ResultadoLinha:
    linha: LinhaCredor
    status: str
    motivo: str = ''
    company_id: Optional[int] = None
    partner_id: Optional[int] = None
    partner_nome: Optional[str] = None
    fatura_name: Optional[str] = None
    move_id: Optional[int] = None
    payable_line_id: Optional[int] = None
    residual: Optional[float] = None
    total: Optional[float] = None
    pares: List[Par] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)


# =============================================================================
# HELPERS PUROS
# =============================================================================
def _norm(s) -> str:
    if s is None:
        return ''
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii')
    return ' '.join(s.upper().split())


def _str(v) -> str:
    if v is None:
        return ''
    return str(v).strip()


def _float(v) -> float:
    if v is None or v == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r'[^\d,.\-]', '', str(v).strip())
    if not s:
        return 0.0
    if ',' in s and '.' in s:        # formato BR: 1.234,56
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:                   # 1234,56
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _to_date(v) -> Optional[date]:
    """Converte para date. Datas nativas (openpyxl) passam direto. Strings aceitam
    BR (dd/mm/aaaa, dd-mm-aaaa) e ISO (aaaa-mm-dd); ano de 2 digitos NAO e aceito
    (ambiguo). Ano fora de [2000, 2100] em string => None (input patologico)."""
    if v is None or v == '':
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            d = datetime.strptime(s, fmt).date()
        except ValueError:
            continue
        return d if 2000 <= d.year <= 2100 else None
    return None


def _m2o_id(v):
    """Extrai o id de um campo many2one Odoo ([id, nome]) ou escalar."""
    if isinstance(v, (list, tuple)) and v:
        return v[0]
    return v if v not in (None, False) else None


def _m2o_nome(v):
    if isinstance(v, (list, tuple)) and len(v) > 1:
        return v[1]
    return None


def _empresa_para_company(empresa) -> Optional[int]:
    """Mapeia o texto da coluna EMPRESA (ex 'FB', 'NACOM GOYA - FB', 'LA FAMIGLIA - LF')
    para o company_id Odoo, por token de sigla. Retorna None se nao reconhecer."""
    if not empresa:
        return None
    tokens = set(_norm(empresa).split())
    for sigla, cid in COMPANY_IDS_ODOO.items():
        if sigla in tokens:
            return cid
    return None


# =============================================================================
# PARSER (puro) — openpyxl, robusto a header duplicado e colunas de data 1..N
# =============================================================================
def parsear_planilha(path: str, sheet: Optional[str] = None) -> List[LinhaCredor]:
    """Le a planilha de credores e retorna as linhas estruturadas.

    Colunas conhecidas sao mapeadas POR NOME (nunca por posicao — guard F2). As
    colunas de vencimento ("DATAS 1..N", que podem ter cabecalho duplicado tipo
    `6`/`6.1` do pandas) sao detectadas pelos VALORES: qualquer coluna nao-mapeada
    cujas celulas contenham datas e' tratada como coluna de vencimento.
    """
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[sheet] if sheet else wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return []

    header = rows[0]
    ncol = len(header)
    norm_headers = [_norm(h) for h in header]

    # mapear campos conhecidos -> indice de coluna (primeira ocorrencia vence)
    field_col = {}
    for ci, nh in enumerate(norm_headers):
        for fld, aliases in _ALIASES.items():
            if fld not in field_col and nh in aliases:
                field_col[fld] = ci
                break
    mapped_cols = set(field_col.values())

    data_rows = rows[1:]

    # colunas de data (vencimento) = nao-mapeadas, com pelo menos 1 celula-data, e
    # cujo header NAO indique data de outro tipo (emissao, nf, competencia... — PARSER-004)
    date_cols = []
    for ci in range(ncol):
        if ci in mapped_cols:
            continue
        if set(norm_headers[ci].split()) & _HEADERS_DATA_NAO_VENC:
            continue
        for r in data_rows:
            v = r[ci] if ci < len(r) else None
            if isinstance(v, (datetime, date)) or (v not in (None, '') and _to_date(v) is not None):
                date_cols.append(ci)
                break

    linhas = []
    for ri, r in enumerate(data_rows, start=2):
        def cell(fld):
            ci = field_col.get(fld)
            return r[ci] if ci is not None and ci < len(r) else None

        credor = _str(cell('credor'))
        ft_ref = _str(cell('ft_ref'))
        parcela = _float(cell('valor_parcela'))
        desagio = _float(cell('valor_desagio'))
        empresa = _str(cell('empresa')) or None
        ref_pg = _str(cell('ref_pg_sicoob')) or None

        datas = []
        for ci in date_cols:
            d = _to_date(r[ci] if ci < len(r) else None)
            if d:
                datas.append(d)

        # pular linhas totalmente vazias
        if not any([credor, ft_ref, parcela, desagio, datas]):
            continue

        linhas.append(LinhaCredor(
            idx=ri, credor=credor, ft_ref=ft_ref, valor_parcela=parcela,
            valor_desagio=desagio, datas=datas, empresa=empresa,
            ref_pg_sicoob=ref_pg,
        ))
    return linhas


# =============================================================================
# CALCULO DOS PARES (puro)
# =============================================================================
def calcular_pares(linha: LinhaCredor, journal_sicoob_id, journal_desagio_id) -> List[Par]:
    """Para cada vencimento: par SICOOB (parcela) + DESAGIO (desagio, se > 0)."""
    pares: List[Par] = []
    for d in linha.datas:
        pares.append(Par('SICOOB', round(linha.valor_parcela, 2), journal_sicoob_id, d))
        if linha.valor_desagio and linha.valor_desagio > 0:
            pares.append(Par('DESAGIO', round(linha.valor_desagio, 2), journal_desagio_id, d))
    return pares


# =============================================================================
# SERVICE — orquestracao READ + guards
# =============================================================================
class BaixaCredoresLoteService:
    """Preview (READ-only) do lote de baixa de credores. NAO escreve no Odoo."""

    def __init__(self, connection=None, tolerancia_saldo: float = 0.01):
        self._connection = connection
        self.tolerancia_saldo = tolerancia_saldo
        self._journals_cache = {}

    @property
    def connection(self):
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise RuntimeError("Falha na autenticacao com Odoo")
        return self._connection

    # ---- camada Odoo (READ) -------------------------------------------------
    def localizar_fatura(self, ft_ref: str) -> List[dict]:
        """Faturas in_invoice posted com name == ft_ref (multi-company)."""
        domain = [['name', '=', ft_ref], ['move_type', '=', 'in_invoice'],
                  ['state', '=', 'posted']]
        return self.connection.execute_kw(
            'account.move', 'search_read', [domain],
            {'fields': CAMPOS_MOVE, 'context': _CTX_MULTI_COMPANY, 'limit': 10},
        ) or []

    def linhas_payable_abertas(self, move_id: int) -> List[dict]:
        """Linhas liability_payable abertas (reconciled=False) do move.

        Faturas parceladas tem N linhas payable (uma por parcela); todas as abertas
        compoem o residual em aberto do fornecedor naquela fatura."""
        domain = [['move_id', '=', move_id],
                  ['account_type', '=', 'liability_payable'],
                  ['reconciled', '=', False]]
        return self.connection.execute_kw(
            'account.move.line', 'search_read', [domain],
            {'fields': CAMPOS_LINE, 'context': _CTX_MULTI_COMPANY},
        ) or []

    def resolver_journals(self, company_id: int) -> dict:
        """Resolve os journals SICOOB/DESAGIO da company AO VIVO (READ), com
        fallback para constants. Cacheado por company."""
        if company_id in self._journals_cache:
            return self._journals_cache[company_id]

        domain = [['company_id', '=', company_id], ['type', 'in', ['bank', 'cash']]]
        js = self.connection.execute_kw(
            'account.journal', 'search_read', [domain],
            {'fields': ['id', 'code', 'name', 'type', 'company_id'],
             'context': _CTX_MULTI_COMPANY},
        ) or []

        sicoob = desagio = None
        for j in js:
            code = (j.get('code') or '').upper()
            name = (j.get('name') or '').upper()
            if sicoob is None and j.get('type') == 'bank' and code == 'SIC' and name == 'SICOOB':
                sicoob = j['id']
            if desagio is None and j.get('type') == 'cash' and code == 'DESAG':
                desagio = j['id']

        if sicoob is None:
            sicoob = JOURNAL_SICOOB_POR_COMPANY.get(company_id)
        if desagio is None and company_id == 1:
            desagio = JOURNAL_DESAGIO_ID

        res = {'sicoob': sicoob, 'desagio': desagio}
        self._journals_cache[company_id] = res
        return res

    # ---- orquestracao -------------------------------------------------------
    def analisar_linha(self, linha: LinhaCredor) -> ResultadoLinha:
        res = ResultadoLinha(linha=linha, status='', fatura_name=linha.ft_ref)

        # 1. ja processado (idempotencia soft do preview)
        if linha.ref_pg_sicoob:
            res.status = STATUS_JA_PROCESSADO
            res.motivo = f'REF PG SICOOB ja preenchido: {linha.ref_pg_sicoob}'
            return res

        # 2. sem dados suficientes
        if not linha.ft_ref or not linha.datas or linha.valor_parcela <= 0:
            res.status = STATUS_PULADO_SEM_DADOS
            res.motivo = 'linha sem ft_ref, sem datas de vencimento ou sem valor de parcela'
            return res

        # 3. guard de valor (F2): 0 <= desagio < parcela (negativo tambem e invalido — GUARD-001)
        if linha.valor_desagio and (linha.valor_desagio < 0 or linha.valor_desagio >= linha.valor_parcela):
            res.status = STATUS_BLOQUEADO_VALOR
            res.motivo = (f'desagio invalido ({linha.valor_desagio}): '
                          f'deve ser 0 <= desagio < parcela ({linha.valor_parcela})')
            return res

        # 4. localizar fatura (F1) — match unico em (name, company, partner)
        moves = self.localizar_fatura(linha.ft_ref)
        if not moves:
            res.status = STATUS_BLOQUEADO_NAO_ENCONTRADA
            res.motivo = f'fatura in_invoice posted name={linha.ft_ref!r} nao encontrada'
            return res
        # name de fatura COLIDE entre companies (numeracao por journal/company se repete):
        # a coluna EMPRESA da planilha desambigua qual fatura. A company efetiva ainda
        # vem da fatura resolvida (autoridade — gotcha O8), nao do texto da planilha.
        if len(moves) > 1:
            cid_hint = _empresa_para_company(linha.empresa)
            if cid_hint:
                filtrados = [m for m in moves if _m2o_id(m.get('company_id')) == cid_hint]
                if filtrados:
                    moves = filtrados
        chaves = {(_m2o_id(m.get('company_id')), _m2o_id(m.get('partner_id'))) for m in moves}
        if len(chaves) > 1:
            res.status = STATUS_BLOQUEADO_AMBIGUO
            res.motivo = (f'{len(moves)} faturas para name={linha.ft_ref!r} em '
                          f'companies/partners distintos: {sorted(chaves)}; '
                          f'preencha/confira a coluna EMPRESA (FB/LF/SC/CD) para desambiguar')
            return res

        fatura = moves[0]
        company_id = _m2o_id(fatura.get('company_id'))
        res.company_id = company_id
        res.partner_id = _m2o_id(fatura.get('partner_id'))
        res.partner_nome = _m2o_nome(fatura.get('partner_id'))
        res.move_id = fatura.get('id')
        res.fatura_name = fatura.get('name')

        # 5. cross-company (SC/CD) — Fase 2
        if company_id in COMPANIES_SEM_JOURNAL_BANCARIO:
            res.status = STATUS_BLOQUEADO_CROSS_COMPANY
            res.motivo = (f'company {company_id} (SC/CD) sem journal bancario proprio '
                          f'— pagamento cross-company e Fase 2')
            return res

        # 6. journals da company (ao vivo)
        journals = self.resolver_journals(company_id)
        if not journals.get('sicoob'):
            res.status = STATUS_BLOQUEADO_SEM_JOURNAL_SICOOB
            res.motivo = f'journal SICOOB nao encontrado para company {company_id}'
            return res
        if linha.valor_desagio and linha.valor_desagio > 0 and not journals.get('desagio'):
            res.status = STATUS_BLOQUEADO_SEM_JOURNAL_DESAGIO
            res.motivo = (f'company {company_id} sem journal DESAGIO; desagio>0 nao e '
                          f'lancavel (par SICOOB+DESAGIO so existe na FB)')
            return res

        # 7. linha(s) payable aberta(s) — faturas parceladas tem N
        payables = self.linhas_payable_abertas(fatura.get('id'))
        if not payables:
            res.status = STATUS_BLOQUEADO_SEM_PAYABLE
            res.motivo = 'nenhuma linha payable aberta (liability_payable, reconciled=False)'
            return res
        res.payable_line_id = payables[0].get('id')
        # gotcha O3: amount_residual payable e NEGATIVO -> abs(); soma todas as parcelas abertas
        residual = round(sum(abs(p.get('amount_residual') or 0.0) for p in payables), 2)
        res.residual = residual
        if len(payables) > 1:
            res.avisos.append(
                f'fatura parcelada: {len(payables)} linhas payable abertas (residual somado); '
                f'mapeamento par->parcela e responsabilidade do WRITE (1b)')

        # validacao de partner (aviso, nao bloqueio)
        if res.partner_nome and linha.credor and _norm(res.partner_nome) != _norm(linha.credor):
            res.avisos.append(
                f'credor planilha {linha.credor!r} difere do partner da fatura '
                f'{res.partner_nome!r} (confira)')

        # 8. pares + total + guard de saldo
        pares = calcular_pares(linha, journals['sicoob'], journals.get('desagio'))
        total = round(sum(p.valor for p in pares), 2)
        res.pares = pares
        res.total = total
        if residual + self.tolerancia_saldo < total:
            res.status = STATUS_BLOQUEADO_SALDO
            res.motivo = (f'total dos pares R$ {total:.2f} > residual R$ {residual:.2f} '
                          f'(+tol {self.tolerancia_saldo})')
            return res

        res.status = STATUS_DRY_RUN_OK
        return res

    def gerar_preview(self, linhas: List[LinhaCredor]) -> List[ResultadoLinha]:
        """Analisa todas as linhas e retorna os resultados (preview do lote)."""
        return [self.analisar_linha(l) for l in linhas]
