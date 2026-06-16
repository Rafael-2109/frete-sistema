"""Testes da logica pura/mockavel da skill `auditando-reclassificacao-odoo`.

CONTEXTO (#164 / adhoc-cluster-4, aprovada na decisao 4-maos 2026-06-12):
A skill e READ-only de auditoria de reclassificacao contabil no Odoo. Nasceu dos
17 scripts distintos capturados do cluster 4 (sessao 4ce68a88, Marcus user 18).
Os helpers de logica vivem em
`.claude/skills/auditando-reclassificacao-odoo/scripts/auditar_reclassificacao.py`
e recebem a conexao Odoo INJETADA (parametro `c`) — aqui substituida por um
FakeOdoo deterministico que avalia o domain Odoo (operadores =, !=, in, >, >=,
<, <=) sobre listas de registros em memoria. Zero rede, zero LLM, zero PROD.

A skill e ESTRITAMENTE READ-only: nenhum helper escreve (sem button_draft,
write account_id, action_post). Isso e parte do escopo aprovado (C4) e foi o
motivo de a sugestao irma #163 (write em massa) ter sido REJEITADA.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / '.claude/skills/auditando-reclassificacao-odoo/scripts/auditar_reclassificacao.py'


def _load():
    spec = importlib.util.spec_from_file_location('auditar_reclassificacao', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def mod():
    return _load()


# ---------------------------------------------------------------------------
# FakeOdoo — avaliador minimo de domain Odoo (AND implicito) sobre dicts.
# many2one armazenado como [id, nome] (formato real do Odoo via XML-RPC).
# ---------------------------------------------------------------------------
class FakeOdoo:
    def __init__(self, tabelas):
        # tabelas: {modelo: [registro_dict, ...]} — cada registro precisa de 'id'
        self._tabelas = tabelas
        self.calls = []

    @staticmethod
    def _coerce(rv):
        if isinstance(rv, (list, tuple)) and len(rv) == 2 and isinstance(rv[0], int):
            return rv[0]  # many2one [id, nome] -> id
        return rv

    @classmethod
    def _match(cls, rec, cond):
        field, op, val = cond
        rv = cls._coerce(rec.get(field))
        if op == '=':
            return rv == val
        if op == '!=':
            return rv != val
        if op == 'in':
            return rv in val
        if op == 'not in':
            return rv not in val
        if op == '>':
            return rv is not None and rv > val
        if op == '>=':
            return rv is not None and rv >= val
        if op == '<':
            return rv is not None and rv < val
        if op == '<=':
            return rv is not None and rv <= val
        raise ValueError(f'operador nao suportado no FakeOdoo: {op}')

    def search_read(self, model, domain, fields, limit=None):
        self.calls.append((model, list(domain), list(fields)))
        rows = []
        for rec in self._tabelas.get(model, []):
            if all(self._match(rec, c) for c in domain):
                out = {'id': rec['id']}
                for f in fields:
                    out[f] = rec.get(f)
                rows.append(out)
                if limit and len(rows) >= limit:
                    break
        return rows


# ---------------------------------------------------------------------------
# parse_contas
# ---------------------------------------------------------------------------
def test_parse_contas_com_rotulo(mod):
    assert mod.parse_contas('25091:CPV,26785:VARNEG') == [(25091, 'CPV'), (26785, 'VARNEG')]


def test_parse_contas_sem_rotulo_usa_id(mod):
    assert mod.parse_contas('25091') == [(25091, '25091')]


def test_parse_contas_strip_espacos(mod):
    assert mod.parse_contas(' 25091:CPV , 26785 ') == [(25091, 'CPV'), (26785, '26785')]


# ---------------------------------------------------------------------------
# carregar_alvo
# ---------------------------------------------------------------------------
def test_carregar_alvo_extrai_chave(mod, tmp_path):
    p = tmp_path / 'alvo.json'
    p.write_text(json.dumps({'venda_NF': [{'line': 1, 'lid': 10, 'debit': 5.0}]}))
    regs = mod.carregar_alvo(str(p), 'venda_NF')
    assert regs == [{'line': 1, 'lid': 10, 'debit': 5.0}]


def test_carregar_alvo_chave_ausente_erro(mod, tmp_path):
    p = tmp_path / 'alvo.json'
    p.write_text(json.dumps({'outra': []}))
    with pytest.raises(KeyError):
        mod.carregar_alvo(str(p), 'venda_NF')


# ---------------------------------------------------------------------------
# detectar_duplicados
# ---------------------------------------------------------------------------
def test_detectar_duplicados(mod):
    regs = [{'lid': 1}, {'lid': 2}, {'lid': 1}, {'lid': 3}, {'lid': 1}]
    assert mod.detectar_duplicados(regs) == [1]


def test_detectar_duplicados_vazio_quando_unicos(mod):
    regs = [{'lid': 1}, {'lid': 2}, {'lid': 3}]
    assert mod.detectar_duplicados(regs) == []


# ---------------------------------------------------------------------------
# medir_saldos — exercita TODOS os filtros (conta, company, journal, periodo,
# debit>0, parent_state=posted)
# ---------------------------------------------------------------------------
def _fake_para_medir():
    CD, J, CPV, VAR = 4, 845, 25091, 26785
    mls = [
        {'id': 1, 'account_id': [CPV, 'CPV'], 'company_id': [CD, 'CD'], 'journal_id': [J, 'J'],
         'date': '2025-09-10', 'debit': 100.0, 'credit': 0.0, 'parent_state': 'posted'},
        {'id': 2, 'account_id': [CPV, 'CPV'], 'company_id': [CD, 'CD'], 'journal_id': [J, 'J'],
         'date': '2025-09-20', 'debit': 50.0, 'credit': 0.0, 'parent_state': 'posted'},
        {'id': 3, 'account_id': [VAR, 'VAR'], 'company_id': [CD, 'CD'], 'journal_id': [J, 'J'],
         'date': '2025-09-15', 'debit': 30.0, 'credit': 0.0, 'parent_state': 'posted'},
        # AGOSTO (fora do periodo)
        {'id': 4, 'account_id': [CPV, 'CPV'], 'company_id': [CD, 'CD'], 'journal_id': [J, 'J'],
         'date': '2025-08-31', 'debit': 999.0, 'credit': 0.0, 'parent_state': 'posted'},
        # DRAFT
        {'id': 5, 'account_id': [CPV, 'CPV'], 'company_id': [CD, 'CD'], 'journal_id': [J, 'J'],
         'date': '2025-09-05', 'debit': 77.0, 'credit': 0.0, 'parent_state': 'draft'},
        # debit=0 (lancamento a credito)
        {'id': 6, 'account_id': [CPV, 'CPV'], 'company_id': [CD, 'CD'], 'journal_id': [J, 'J'],
         'date': '2025-09-06', 'debit': 0.0, 'credit': 10.0, 'parent_state': 'posted'},
        # outra company
        {'id': 7, 'account_id': [CPV, 'CPV'], 'company_id': [1, 'FB'], 'journal_id': [J, 'J'],
         'date': '2025-09-07', 'debit': 5.0, 'credit': 0.0, 'parent_state': 'posted'},
        # outro journal
        {'id': 8, 'account_id': [CPV, 'CPV'], 'company_id': [CD, 'CD'], 'journal_id': [999, 'J2'],
         'date': '2025-09-08', 'debit': 3.0, 'credit': 0.0, 'parent_state': 'posted'},
    ]
    return FakeOdoo({'account.move.line': mls})


def test_medir_saldos_conta_e_soma(mod):
    c = _fake_para_medir()
    res = mod.medir_saldos(c, [(25091, 'CPV'), (26785, 'VARNEG')],
                           '2025-09-01', '2025-09-30', company_id=4, journal_id=845)
    saldos = {s['conta_id']: s for s in res['saldos']}
    assert saldos[25091]['n_linhas'] == 2
    assert saldos[25091]['total_debito'] == pytest.approx(150.0)
    assert saldos[25091]['rotulo'] == 'CPV'
    assert saldos[26785]['n_linhas'] == 1
    assert saldos[26785]['total_debito'] == pytest.approx(30.0)


def test_medir_saldos_metadados(mod):
    c = _fake_para_medir()
    res = mod.medir_saldos(c, [(25091, 'CPV')], '2025-09-01', '2025-09-30',
                           company_id=4, journal_id=845)
    assert res['company_id'] == 4
    assert res['journal_id'] == 845
    assert res['periodo'] == {'inicio': '2025-09-01', 'fim': '2025-09-30'}


def test_medir_saldos_state_default_posted(mod):
    # Sem --state, mantem o comportamento historico (so posted): ids 1,2 = 150.
    c = _fake_para_medir()
    res = mod.medir_saldos(c, [(25091, 'CPV')], '2025-09-01', '2025-09-30',
                           company_id=4, journal_id=845)
    assert res['state'] == 'posted'
    assert res['saldos'][0]['n_linhas'] == 2
    assert res['saldos'][0]['total_debito'] == pytest.approx(150.0)


def test_medir_saldos_state_draft(mod):
    # state='draft' conta SO a linha em move draft (id 5, debit 77).
    c = _fake_para_medir()
    res = mod.medir_saldos(c, [(25091, 'CPV')], '2025-09-01', '2025-09-30',
                           company_id=4, journal_id=845, state='draft')
    assert res['state'] == 'draft'
    assert res['saldos'][0]['n_linhas'] == 1
    assert res['saldos'][0]['total_debito'] == pytest.approx(77.0)


def test_medir_saldos_state_both(mod):
    # state='both' soma posted (1,2) + draft (5) = 227, sem filtro parent_state.
    c = _fake_para_medir()
    res = mod.medir_saldos(c, [(25091, 'CPV')], '2025-09-01', '2025-09-30',
                           company_id=4, journal_id=845, state='both')
    assert res['state'] == 'both'
    assert res['saldos'][0]['n_linhas'] == 3
    assert res['saldos'][0]['total_debito'] == pytest.approx(227.0)


# ---------------------------------------------------------------------------
# validar_lote — divergencias, ausentes, duplicados, draft
# ---------------------------------------------------------------------------
def _fake_e_regs_para_validar():
    CPV, VAR, OUTRA = 25091, 26785, 99999
    mls = [
        {'id': 1, 'account_id': [CPV, 'CPV'], 'parent_state': 'posted'},
        {'id': 2, 'account_id': [VAR, 'VAR'], 'parent_state': 'posted'},
        {'id': 3, 'account_id': [OUTRA, 'X'], 'parent_state': 'posted'},
        {'id': 5, 'account_id': [CPV, 'CPV'], 'parent_state': 'posted'},
        # id 4 ausente de proposito
    ]
    moves = [
        {'id': 1001, 'state': 'posted'},
        {'id': 1002, 'state': 'posted'},
        {'id': 1003, 'state': 'draft'},
        {'id': 1004, 'state': 'posted'},
    ]
    regs = [
        {'line': 1001, 'lid': 1, 'debit': 100.0},
        {'line': 1001, 'lid': 2, 'debit': 50.0},
        {'line': 1002, 'lid': 3, 'debit': 30.0},
        {'line': 1003, 'lid': 4, 'debit': 10.0},
        {'line': 1004, 'lid': 5, 'debit': 5.0},
        {'line': 1004, 'lid': 5, 'debit': 5.0},  # duplicado
    ]
    return FakeOdoo({'account.move.line': mls, 'account.move': moves}), regs


def test_validar_lote_classifica(mod):
    c, regs = _fake_e_regs_para_validar()
    res = mod.validar_lote(c, regs, conta_destino=25091, conta_origem=26785)
    assert res['total_alvo'] == 6
    assert res['linhas_unicas'] == 5
    assert res['processadas'] == 2          # lids 1 e 5 em CPV
    assert res['pendentes'] == 1            # lid 2 em VARNEG
    assert res['divergentes'] == [{'lid': 3, 'account_id': 99999}]
    assert res['ausentes'] == [4]
    assert res['duplicados'] == [5]
    assert res['moves_draft'] == 1          # move 1003 em draft
    assert res['integro'] is False


def test_validar_lote_integro_true_sem_anomalias(mod):
    CPV, VAR = 25091, 26785
    mls = [
        {'id': 1, 'account_id': [CPV, 'CPV'], 'parent_state': 'posted'},
        {'id': 2, 'account_id': [CPV, 'CPV'], 'parent_state': 'posted'},
    ]
    moves = [{'id': 1, 'state': 'posted'}]
    regs = [{'line': 1, 'lid': 1, 'debit': 1.0}, {'line': 1, 'lid': 2, 'debit': 1.0}]
    c = FakeOdoo({'account.move.line': mls, 'account.move': moves})
    res = mod.validar_lote(c, regs, conta_destino=CPV, conta_origem=VAR)
    assert res['duplicados'] == []
    assert res['ausentes'] == []
    assert res['divergentes'] == []
    assert res['integro'] is True


# ---------------------------------------------------------------------------
# monitorar_andamento — progresso (processadas/pendentes/pct/concluido)
# ---------------------------------------------------------------------------
def test_monitorar_andamento_em_curso(mod):
    CPV, VAR = 25091, 26785
    mls = [
        {'id': 10, 'account_id': [CPV, 'CPV']},
        {'id': 11, 'account_id': [CPV, 'CPV']},
        {'id': 12, 'account_id': [VAR, 'VAR']},
    ]
    regs = [
        {'line': 1, 'lid': 10, 'debit': 1.0},
        {'line': 1, 'lid': 11, 'debit': 1.0},
        {'line': 2, 'lid': 12, 'debit': 1.0},
    ]
    c = FakeOdoo({'account.move.line': mls, 'account.move': []})
    res = mod.monitorar_andamento(c, regs, conta_destino=CPV, conta_origem=VAR)
    assert res['total'] == 3
    assert res['processadas'] == 2
    assert res['pendentes'] == 1
    assert res['pct_concluido'] == pytest.approx(66.7)
    assert res['concluido'] is False


def test_monitorar_andamento_concluido(mod):
    CPV, VAR = 25091, 26785
    mls = [
        {'id': 10, 'account_id': [CPV, 'CPV']},
        {'id': 11, 'account_id': [CPV, 'CPV']},
    ]
    regs = [
        {'line': 1, 'lid': 10, 'debit': 1.0},
        {'line': 1, 'lid': 11, 'debit': 1.0},
    ]
    c = FakeOdoo({'account.move.line': mls, 'account.move': []})
    res = mod.monitorar_andamento(c, regs, conta_destino=CPV, conta_origem=VAR)
    assert res['processadas'] == 2
    assert res['pendentes'] == 0
    assert res['pct_concluido'] == pytest.approx(100.0)
    assert res['concluido'] is True


# ---------------------------------------------------------------------------
# CLI parser — modos e flags
# ---------------------------------------------------------------------------
def test_cli_parser_medir_saldos(mod):
    args = mod.build_parser().parse_args([
        'medir-saldos', '--contas', '25091:CPV,26785:VARNEG',
        '--data-inicio', '2025-09-01', '--data-fim', '2025-09-30',
    ])
    assert args.modo == 'medir-saldos'
    assert args.contas == '25091:CPV,26785:VARNEG'
    assert args.company_id == 4       # default CD
    assert args.journal_id == 845     # default
    assert args.json is False
    assert args.state == 'posted'     # default historico


def test_cli_parser_medir_saldos_state(mod):
    args = mod.build_parser().parse_args([
        'medir-saldos', '--contas', '25091:CPV',
        '--data-inicio', '2025-09-01', '--data-fim', '2025-09-30', '--state', 'both',
    ])
    assert args.state == 'both'


def test_cli_parser_validar_lote(mod):
    args = mod.build_parser().parse_args([
        'validar-lote', '--arquivo', '/tmp/x.json',
        '--conta-destino', '25091', '--conta-origem', '26785', '--json',
    ])
    assert args.modo == 'validar-lote'
    assert args.arquivo == '/tmp/x.json'
    assert args.chave == 'venda_NF'   # default
    assert args.conta_destino == 25091
    assert args.conta_origem == 26785
    assert args.json is True


def test_cli_parser_monitorar(mod):
    args = mod.build_parser().parse_args([
        'monitorar-andamento', '--arquivo', '/tmp/x.json',
        '--conta-destino', '25091', '--conta-origem', '26785',
    ])
    assert args.modo == 'monitorar-andamento'
    assert args.arquivo == '/tmp/x.json'
