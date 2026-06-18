# -*- coding: utf-8 -*-
"""Testes da skill baixando-credores-lote-odoo (passo 1a — PREVIEW READ-only).

Cobre a logica PURA (parser de planilha, calculo dos pares SICOOB+DESAGIO) e os
guards/status da orquestracao (com a conexao Odoo injetada como fake — boundary
externo). ZERO escrita no Odoo: o fake so responde search_read/execute_kw.
"""
import datetime as dt

import openpyxl
import pytest

from app.financeiro.services.baixa_credores_lote_service import (
    BaixaCredoresLoteService,
    LinhaCredor,
    calcular_pares,
    parsear_planilha,
    _to_date,
    _float,
    STATUS_DRY_RUN_OK,
    STATUS_BLOQUEADO_SALDO,
    STATUS_BLOQUEADO_AMBIGUO,
    STATUS_BLOQUEADO_CROSS_COMPANY,
    STATUS_BLOQUEADO_NAO_ENCONTRADA,
    STATUS_BLOQUEADO_VALOR,
    STATUS_BLOQUEADO_SEM_JOURNAL_DESAGIO,
    STATUS_BLOQUEADO_SEM_PAYABLE,
    STATUS_PULADO_SEM_DADOS,
    STATUS_JA_PROCESSADO,
)

J_SICOOB_FB = 10
J_DESAGIO_FB = 1025
J_SICOOB_LF = 386


# =============================================================================
# Helpers de fixture de planilha
# =============================================================================

def _criar_planilha(path, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Credores"
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return str(path)


# =============================================================================
# PARSER — logica pura
# =============================================================================

def test_parser_extrai_campos_conhecidos_e_uma_data(tmp_path):
    p = _criar_planilha(
        tmp_path / "cred.xlsx",
        ["CREDOR", "FT REF", "VALOR PARCELA", "VALOR DESAGIO", "VENCIMENTO", "REF PG SICOOB", "EMPRESA"],
        [["FORNECEDOR X LTDA", "CMPMP/2026/06/0123", 1000.0, 50.0, dt.datetime(2026, 7, 10), None, "FB"]],
    )
    linhas = parsear_planilha(p)
    assert len(linhas) == 1
    l = linhas[0]
    assert l.credor == "FORNECEDOR X LTDA"
    assert l.ft_ref == "CMPMP/2026/06/0123"
    assert l.valor_parcela == 1000.0
    assert l.valor_desagio == 50.0
    assert l.datas == [dt.date(2026, 7, 10)]
    assert l.empresa == "FB"
    assert l.ref_pg_sicoob in (None, "")


def test_parser_multiplas_colunas_de_data_com_header_duplicado(tmp_path):
    # "Header dup 6/6.1 do pandas": duas colunas de vencimento com header repetido.
    p = _criar_planilha(
        tmp_path / "cred.xlsx",
        ["CREDOR", "FT REF", "VALOR PARCELA", "VALOR DESAGIO", "DATA", "DATA", "REF PG SICOOB"],
        [["F", "CMPMP/2026/06/1", 500.0, 10.0, dt.datetime(2026, 7, 5), dt.datetime(2026, 8, 5), None]],
    )
    linhas = parsear_planilha(p)
    assert linhas[0].datas == [dt.date(2026, 7, 5), dt.date(2026, 8, 5)]


def test_parser_ignora_celulas_de_data_vazias(tmp_path):
    p = _criar_planilha(
        tmp_path / "cred.xlsx",
        ["CREDOR", "FT REF", "VALOR PARCELA", "VALOR DESAGIO", "DATA", "DATA"],
        [["F", "CMPMP/1", 500.0, 0.0, dt.datetime(2026, 7, 5), None]],
    )
    assert linhas_datas(parsear_planilha(p)) == [dt.date(2026, 7, 5)]


def linhas_datas(linhas):
    return linhas[0].datas


def test_parser_nao_confunde_coluna_emissao_com_vencimento(tmp_path):
    # PARSER-004: coluna EMISSAO contem data mas NAO e vencimento -> nao deve virar venc
    p = _criar_planilha(
        tmp_path / "cred.xlsx",
        ["CREDOR", "FT REF", "VALOR PARCELA", "VALOR DESAGIO", "EMISSAO", "VENCIMENTO"],
        [["F", "CMPMP/1", 500.0, 0.0, dt.datetime(2026, 6, 1), dt.datetime(2026, 7, 5)]],
    )
    linhas = parsear_planilha(p)
    assert linhas[0].datas == [dt.date(2026, 7, 5)]  # so o vencimento, nao a emissao


def test_parser_ignora_coluna_nf_numero_com_valor_data(tmp_path):
    # PARSER-004: coluna "NF NUMERO" (nao mapeada) com valor data nao vira vencimento
    p = _criar_planilha(
        tmp_path / "cred.xlsx",
        ["CREDOR", "FT REF", "VALOR PARCELA", "VALOR DESAGIO", "NF NUMERO", "DATA"],
        [["F", "CMPMP/1", 500.0, 0.0, dt.datetime(2026, 6, 12), dt.datetime(2026, 7, 5)]],
    )
    linhas = parsear_planilha(p)
    assert linhas[0].datas == [dt.date(2026, 7, 5)]


def test_parser_detecta_data_por_valor_com_header_dia_numerico(tmp_path):
    # preserva o caso "6/6.1" do DESIGN: headers numericos com valores-data sao vencimentos
    p = _criar_planilha(
        tmp_path / "cred.xlsx",
        ["CREDOR", "FT REF", "VALOR PARCELA", "VALOR DESAGIO", "6", "6.1"],
        [["F", "CMPMP/1", 500.0, 0.0, dt.datetime(2026, 7, 5), dt.datetime(2026, 8, 5)]],
    )
    linhas = parsear_planilha(p)
    assert linhas[0].datas == [dt.date(2026, 7, 5), dt.date(2026, 8, 5)]


# =============================================================================
# CALCULO DOS PARES — logica pura
# =============================================================================

def test_calcular_pares_um_vencimento_com_desagio():
    linha = LinhaCredor(idx=2, credor="F", ft_ref="X", valor_parcela=1000.0,
                        valor_desagio=50.0, datas=[dt.date(2026, 7, 10)],
                        empresa="FB", ref_pg_sicoob=None)
    pares = calcular_pares(linha, J_SICOOB_FB, J_DESAGIO_FB)
    assert len(pares) == 2
    sicoob, desagio = pares
    assert (sicoob.tipo, sicoob.valor, sicoob.journal_id, sicoob.data) == \
        ("SICOOB", 1000.0, J_SICOOB_FB, dt.date(2026, 7, 10))
    assert (desagio.tipo, desagio.valor, desagio.journal_id, desagio.data) == \
        ("DESAGIO", 50.0, J_DESAGIO_FB, dt.date(2026, 7, 10))


def test_calcular_pares_multiplos_vencimentos():
    linha = LinhaCredor(idx=2, credor="F", ft_ref="X", valor_parcela=300.0,
                        valor_desagio=20.0,
                        datas=[dt.date(2026, 7, 5), dt.date(2026, 8, 5)],
                        empresa="FB", ref_pg_sicoob=None)
    pares = calcular_pares(linha, J_SICOOB_FB, J_DESAGIO_FB)
    assert len(pares) == 4  # 2 vencimentos x (SICOOB + DESAGIO)
    assert sum(p.valor for p in pares) == pytest.approx((300.0 + 20.0) * 2)


def test_to_date_aceita_br_e_iso():
    assert _to_date("10/07/2026") == dt.date(2026, 7, 10)   # BR dd/mm/yyyy
    assert _to_date("2026-07-10") == dt.date(2026, 7, 10)   # ISO
    assert _to_date(dt.datetime(2026, 7, 10)) == dt.date(2026, 7, 10)


def test_to_date_rejeita_ano_absurdo():
    # PARSER-003: ano fora de [2000, 2100] -> None (input string patologico)
    assert _to_date("10/07/0026") is None
    assert _to_date("10/07/26") is None  # PARSER-002: 2 digitos ambiguo -> nao aceito


def test_float_formato_br():
    # PARSER-001: formato brasileiro
    assert _float("1.234,56") == pytest.approx(1234.56)
    assert _float("1234,56") == pytest.approx(1234.56)
    assert _float(1234.56) == pytest.approx(1234.56)
    assert _float(None) == 0.0


def test_calcular_pares_sem_desagio_so_sicoob():
    linha = LinhaCredor(idx=2, credor="F", ft_ref="X", valor_parcela=300.0,
                        valor_desagio=0.0, datas=[dt.date(2026, 7, 5)],
                        empresa="LF", ref_pg_sicoob=None)
    pares = calcular_pares(linha, J_SICOOB_LF, journal_desagio_id=None)
    assert len(pares) == 1
    assert pares[0].tipo == "SICOOB"


# =============================================================================
# FAKE da conexao Odoo (boundary externo — READ only)
# =============================================================================

class FakeOdoo:
    """Stub de OdooConnection: responde execute_kw('...','search_read',...).

    Dados pre-carregados: moves (account.move), move_lines (account.move.line),
    journals (account.journal). Registra chamadas de WRITE para o teste afirmar
    que NENHUMA aconteceu.
    """

    def __init__(self, moves=None, lines=None, journals=None):
        self.moves = moves or []
        self.lines = lines or []
        self.journals = journals or []
        self.write_calls = []

    def authenticate(self):
        return True

    def _match(self, registros, domain):
        out = []
        for reg in registros:
            ok = True
            for cond in domain:
                if not isinstance(cond, (list, tuple)) or len(cond) != 3:
                    continue  # operadores '|' '&' ignorados no fake simples
                campo, op, val = cond
                rv = reg.get(campo)
                if isinstance(rv, (list, tuple)) and rv:  # campos m2o [id, nome]
                    rv = rv[0]
                if op == '=' and rv != val:
                    ok = False
                elif op == 'in' and rv not in val:
                    ok = False
                elif op == '!=' and rv == val:
                    ok = False
            if ok:
                out.append(reg)
        return out

    def execute_kw(self, model, method, args, kwargs=None):
        if method in ('write', 'create', 'unlink', 'action_post', 'reconcile'):
            self.write_calls.append((model, method, args))
            raise AssertionError(f"WRITE proibido no preview: {model}.{method}")
        domain = args[0] if args else []
        fonte = {'account.move': self.moves, 'account.move.line': self.lines,
                 'account.journal': self.journals}.get(model, [])
        return self._match(fonte, domain)

    def search_read(self, model, domain, fields=None, limit=None, offset=None, order=None):
        return self.execute_kw(model, 'search_read', [domain], {'fields': fields})


def _journals_fb():
    return [
        {'id': 10, 'code': 'SIC', 'name': 'SICOOB', 'type': 'bank', 'company_id': [1, 'FB']},
        {'id': 1025, 'code': 'DESAG', 'name': 'DESAGIO', 'type': 'cash', 'company_id': [1, 'FB']},
    ]


def _journals_lf():
    return [{'id': 386, 'code': 'SIC', 'name': 'SICOOB', 'type': 'bank', 'company_id': [5, 'LF']}]


def _move_fb(name="CMPMP/2026/06/0123", residual=-1050.0):
    return {'id': 900, 'name': name, 'move_type': 'in_invoice', 'state': 'posted',
            'company_id': [1, 'FB'], 'partner_id': [777, 'FORNECEDOR X LTDA'],
            'amount_residual': abs(residual), 'amount_total': abs(residual)}


def _payable_fb(move_id=900, residual=-1050.0, company=1):
    return {'id': 5000, 'move_id': [move_id, 'CMPMP/2026/06/0123'],
            'account_type': 'liability_payable', 'account_id': [11038, 'FORNECEDORES NACIONAIS'],
            'debit': 0.0, 'credit': abs(residual), 'amount_residual': residual,
            'reconciled': False, 'partner_id': [777, 'FORNECEDOR X LTDA'],
            'company_id': [company, 'FB'], 'date_maturity': '2026-07-10'}


def _linha(ft_ref="CMPMP/2026/06/0123", parcela=1000.0, desagio=50.0,
           datas=None, empresa="FB", ref_pg=None):
    return LinhaCredor(idx=2, credor="FORNECEDOR X LTDA", ft_ref=ft_ref,
                       valor_parcela=parcela, valor_desagio=desagio,
                       datas=datas or [dt.date(2026, 7, 10)], empresa=empresa,
                       ref_pg_sicoob=ref_pg)


# =============================================================================
# GUARDS / STATUS — orquestracao (com fake)
# =============================================================================

def test_linha_ok_gera_dry_run_ok_com_plano():
    odoo = FakeOdoo(moves=[_move_fb()], lines=[_payable_fb()], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha())  # parcela 1000 + desagio 50 = 1050 == residual
    assert res.status == STATUS_DRY_RUN_OK
    assert res.company_id == 1
    assert res.partner_id == 777
    assert len(res.pares) == 2
    assert res.total == pytest.approx(1050.0)
    assert odoo.write_calls == []  # ZERO escrita


def test_fatura_nao_encontrada():
    odoo = FakeOdoo(moves=[], lines=[], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(ft_ref="NAO/EXISTE/0"))
    assert res.status == STATUS_BLOQUEADO_NAO_ENCONTRADA


def test_fatura_ambigua_mesma_company_partners_distintos():
    # mesmo name+company, 2 partners -> empresa nao desambigua -> AMBIGUO
    m1 = _move_fb()
    m2 = _move_fb(); m2['id'] = 901; m2['partner_id'] = [778, 'OUTRO']
    odoo = FakeOdoo(moves=[m1, m2], lines=[_payable_fb()], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(empresa="FB"))
    assert res.status == STATUS_BLOQUEADO_AMBIGUO


def test_desambigua_por_empresa_quando_name_colide_entre_companies():
    # name identico em FB(1) e LF(5) — a coluna EMPRESA resolve para FB
    m_fb = _move_fb()
    m_lf = _move_fb(); m_lf['id'] = 901; m_lf['company_id'] = [5, 'LF']; m_lf['partner_id'] = [778, 'OUTRO LF']
    odoo = FakeOdoo(moves=[m_fb, m_lf], lines=[_payable_fb(company=1)], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(empresa="FB"))
    assert res.status == STATUS_DRY_RUN_OK
    assert res.company_id == 1


def test_desambigua_aceita_nome_completo_da_empresa():
    m_fb = _move_fb()
    m_lf = _move_fb(); m_lf['id'] = 901; m_lf['company_id'] = [5, 'LF']; m_lf['partner_id'] = [778, 'X']
    odoo = FakeOdoo(moves=[m_fb, m_lf],
                    lines=[_payable_fb(move_id=901, company=5, residual=-1050.0)],
                    journals=_journals_lf())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(empresa="LA FAMIGLIA - LF", desagio=0.0, parcela=1050.0))
    assert res.status == STATUS_DRY_RUN_OK
    assert res.company_id == 5


def test_ambiguo_persiste_sem_empresa_para_desambiguar():
    m_fb = _move_fb()
    m_lf = _move_fb(); m_lf['id'] = 901; m_lf['company_id'] = [5, 'LF']; m_lf['partner_id'] = [778, 'X']
    odoo = FakeOdoo(moves=[m_fb, m_lf], lines=[_payable_fb()], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(empresa=None))
    assert res.status == STATUS_BLOQUEADO_AMBIGUO


def test_cross_company_sc_cd_bloqueado():
    m = _move_fb(); m['company_id'] = [4, 'CD']
    odoo = FakeOdoo(moves=[m], lines=[_payable_fb(company=4)], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(empresa="CD"))
    assert res.status == STATUS_BLOQUEADO_CROSS_COMPANY


def test_saldo_insuficiente_bloqueado():
    # residual 1050, mas pares = (1000+50)*2 vencimentos = 2100 > 1050
    odoo = FakeOdoo(moves=[_move_fb(residual=-1050.0)], lines=[_payable_fb(residual=-1050.0)],
                    journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(datas=[dt.date(2026, 7, 10), dt.date(2026, 8, 10)]))
    assert res.status == STATUS_BLOQUEADO_SALDO


def test_desagio_maior_que_parcela_bloqueado():
    odoo = FakeOdoo(moves=[_move_fb()], lines=[_payable_fb()], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(parcela=100.0, desagio=200.0))
    assert res.status == STATUS_BLOQUEADO_VALOR


def test_desagio_negativo_bloqueado():
    # GUARD-001: desagio negativo e invalido (nao deve passar como DRY_RUN_OK)
    odoo = FakeOdoo(moves=[_move_fb()], lines=[_payable_fb()], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(parcela=1000.0, desagio=-50.0))
    assert res.status == STATUS_BLOQUEADO_VALOR


def test_lf_com_desagio_sem_journal_desagio_bloqueado():
    m = _move_fb(); m['company_id'] = [5, 'LF']
    odoo = FakeOdoo(moves=[m], lines=[_payable_fb(company=5)], journals=_journals_lf())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(empresa="LF", desagio=50.0))
    assert res.status == STATUS_BLOQUEADO_SEM_JOURNAL_DESAGIO


def test_lf_sem_desagio_so_sicoob_ok():
    m = _move_fb(); m['company_id'] = [5, 'LF']
    odoo = FakeOdoo(moves=[m], lines=[_payable_fb(company=5, residual=-1000.0)], journals=_journals_lf())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(empresa="LF", parcela=1000.0, desagio=0.0))
    assert res.status == STATUS_DRY_RUN_OK
    assert all(p.tipo == "SICOOB" for p in res.pares)


def test_multiplas_payable_somam_residual_e_avisam():
    # fatura parcelada: 2 linhas payable abertas -> residual = soma; aviso de multiplas
    l1 = _payable_fb(residual=-500.0); l1['id'] = 5001
    l2 = _payable_fb(residual=-550.0); l2['id'] = 5002
    odoo = FakeOdoo(moves=[_move_fb()], lines=[l1, l2], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha())  # pares = 1000 + 50 = 1050 == soma residual 1050
    assert res.status == STATUS_DRY_RUN_OK
    assert res.residual == pytest.approx(1050.0)
    assert any('payable' in a.lower() or 'parcela' in a.lower() for a in res.avisos)


def test_sem_payable_aberta_bloqueado():
    odoo = FakeOdoo(moves=[_move_fb()], lines=[], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha())
    assert res.status == STATUS_BLOQUEADO_SEM_PAYABLE


def test_linha_sem_dados_pulada():
    odoo = FakeOdoo(journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(ft_ref="", datas=[]))
    assert res.status == STATUS_PULADO_SEM_DADOS


def test_ja_processado_quando_ref_pg_preenchido():
    odoo = FakeOdoo(moves=[_move_fb()], lines=[_payable_fb()], journals=_journals_fb())
    svc = BaixaCredoresLoteService(connection=odoo)
    res = svc.analisar_linha(_linha(ref_pg="PSIC/2026/06/0001"))
    assert res.status == STATUS_JA_PROCESSADO
