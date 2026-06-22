"""Testes deterministicos do ReclassificacaoService (skill WRITE `reclassificando-amls-odoo`).

CONTEXTO (F2 #3 do D8, autorizada por Rafael 2026-06-21):
Skill EXECUTORA WRITE de reclassificacao contabil em lote de account.move.line no
Odoo. Irma WRITE da READ `auditando-reclassificacao-odoo` (que so mede/valida/
monitora). Reusa o dominio de busca (_dominio_saldo) e o CONTADOR REAL
(validar_lote) da skill READ como salvaguarda pos-write.

ESTRITAMENTE DETERMINISTICO: FakeOdoo em memoria (avalia domain Odoo +
button_draft/write/action_post simulados sobre dicts). Zero rede, zero PROD.

GUARDS testados:
- GUARD SEFAZ: move com l10n_br_situacao_nf in (autorizado/excecao_autorizado/
  enviado) NAO entra no plano (status SKIP_GUARD_SITUACAO_NF) — button_draft
  invalidaria a chave fiscal.
- dry-run NAO escreve (zero button_draft/write/action_post).
- write em batch por move: button_draft -> write account_id (SO linhas da
  conta_origem) -> action_post.
- INVARIANTE pos action_post: re-le state; se != posted, FALHA e PARA o batch.
- Reclassifica SO as linhas na conta_origem do move (nunca as demais).
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / 'app/odoo/estoque/scripts/reclassificacao.py'


def _load():
    spec = importlib.util.spec_from_file_location('reclassificacao_svc', SERVICE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def mod():
    return _load()


# ---------------------------------------------------------------------------
# FakeOdoo — avaliador de domain Odoo + simulador de button_draft/write/post.
# many2one armazenado como [id, nome] (formato real do Odoo via XML-RPC).
# ---------------------------------------------------------------------------
class FakeOdoo:
    def __init__(self, amls, moves):
        # amls: [dict com id, account_id, company_id, journal_id, date, debit,
        #        parent_state, move_id]
        # moves: [dict com id, state, l10n_br_situacao_nf]
        self._amls = {r['id']: r for r in amls}
        self._moves = {r['id']: r for r in moves}
        self.write_calls = []
        self.method_calls = []  # (model, method, ids)

    @staticmethod
    def _coerce(rv):
        if isinstance(rv, (list, tuple)) and len(rv) == 2 and isinstance(rv[0], int):
            return rv[0]
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
        raise ValueError(f'operador nao suportado: {op}')

    def _tabela(self, model):
        return self._moves if model == 'account.move' else self._amls

    def search_read(self, model, domain, fields=None, limit=None):
        tab = self._tabela(model)
        rows = []
        for rec in tab.values():
            if all(self._match(rec, c) for c in domain):
                out = {'id': rec['id']}
                for f in (fields or list(rec.keys())):
                    out[f] = rec.get(f)
                rows.append(out)
                if limit and len(rows) >= limit:
                    break
        return rows

    def read(self, model, ids, fields=None):
        tab = self._tabela(model)
        out = []
        for i in ids:
            rec = tab.get(i)
            if not rec:
                continue
            d = {'id': i}
            for f in (fields or list(rec.keys())):
                d[f] = rec.get(f)
            out.append(d)
        return out

    def write(self, model, ids, values):
        self.write_calls.append((model, list(ids), dict(values)))
        tab = self._tabela(model)
        for i in ids:
            if i in tab:
                tab[i].update(values)
        return True

    def execute_kw(self, model, method, args, kwargs=None):
        ids = args[0] if args else []
        self.method_calls.append((model, method, list(ids)))
        if method == 'button_draft':
            for i in ids:
                if i in self._moves:
                    self._moves[i]['state'] = 'draft'
        elif method == 'action_post':
            for i in ids:
                if i in self._moves:
                    self._moves[i]['state'] = 'posted'
        return True


CD, J = 4, 845
ORIG, DEST, OUTRA = 26784, 26844, 11111


def _fake_basico(situacao_nf_por_move=None, state_apos_post=None):
    """2 moves posted, cada um com 1 linha na conta ORIG (debit>0) + 1 linha
    em OUTRA conta (que NUNCA deve ser tocada).
    situacao_nf_por_move: dict move_id -> situacao (default rascunho).
    """
    sit = situacao_nf_por_move or {}
    amls = [
        {'id': 1, 'account_id': [ORIG, 'ORIG'], 'company_id': [CD, 'CD'],
         'journal_id': [J, 'J'], 'date': '2025-09-10', 'debit': 100.0,
         'parent_state': 'posted', 'move_id': [1001, 'M1']},
        {'id': 2, 'account_id': [OUTRA, 'OUTRA'], 'company_id': [CD, 'CD'],
         'journal_id': [J, 'J'], 'date': '2025-09-10', 'debit': 0.0,
         'parent_state': 'posted', 'move_id': [1001, 'M1']},
        {'id': 3, 'account_id': [ORIG, 'ORIG'], 'company_id': [CD, 'CD'],
         'journal_id': [J, 'J'], 'date': '2025-09-20', 'debit': 50.0,
         'parent_state': 'posted', 'move_id': [1002, 'M2']},
    ]
    moves = [
        {'id': 1001, 'state': 'posted',
         'l10n_br_situacao_nf': sit.get(1001, 'rascunho')},
        {'id': 1002, 'state': 'posted',
         'l10n_br_situacao_nf': sit.get(1002, 'rascunho')},
    ]
    return FakeOdoo(amls, moves)


# ---------------------------------------------------------------------------
# coletar_amls — dominio reusado da skill READ
# ---------------------------------------------------------------------------
def test_coletar_amls_filtra_conta_origem_debit_posted(mod):
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    rows = svc.coletar_amls(ORIG, '2025-09-01', '2025-09-30', CD, J)
    ids = sorted(r['id'] for r in rows)
    assert ids == [1, 3]  # so as linhas na conta ORIG, debit>0


def test_agrupar_por_move(mod):
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    rows = svc.coletar_amls(ORIG, '2025-09-01', '2025-09-30', CD, J)
    grupos = svc.agrupar_por_move(rows)
    assert set(grupos.keys()) == {1001, 1002}
    assert [r['lid'] for r in grupos[1001]] == [1]
    assert [r['lid'] for r in grupos[1002]] == [3]


# ---------------------------------------------------------------------------
# GUARD SEFAZ
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('situacao', ['autorizado', 'excecao_autorizado', 'enviado'])
def test_guard_sefaz_bloqueia_move_autorizada(mod, situacao):
    c = _fake_basico(situacao_nf_por_move={1001: situacao})
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    # move 1001 vai para skip_sefaz; so 1002 entra no plano efetivavel
    assert 1001 not in plano['grupos']
    assert 1002 in plano['grupos']
    sefaz = {s['move_id']: s for s in plano['skip_sefaz']}
    assert 1001 in sefaz
    assert sefaz[1001]['status'] == 'SKIP_GUARD_SITUACAO_NF'


def test_guard_sefaz_permite_rascunho(mod):
    c = _fake_basico()  # ambas rascunho
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    assert set(plano['grupos'].keys()) == {1001, 1002}
    assert plano['skip_sefaz'] == []


def test_planejar_totaliza(mod):
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    assert plano['conta_origem'] == ORIG
    assert plano['conta_destino'] == DEST
    assert plano['n_moves'] == 2
    assert plano['n_linhas'] == 2
    assert plano['total_debito'] == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# executar — dry-run NAO escreve
# ---------------------------------------------------------------------------
def test_executar_dry_run_nao_escreve(mod):
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    res = svc.executar(plano, confirmar=False)
    assert res['status'] == 'DRY_RUN_OK'
    assert c.write_calls == []
    assert c.method_calls == []


# ---------------------------------------------------------------------------
# executar — write em batch por move (ciclo button_draft->write->action_post)
# ---------------------------------------------------------------------------
def test_executar_write_ciclo_completo_por_move(mod):
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    res = svc.executar(plano, confirmar=True)
    assert res['status'] == 'EXECUTADO'
    assert res['moves_processados'] == 2

    # Para cada move: button_draft -> action_post (ordem)
    drafts = [m for m in c.method_calls if m[1] == 'button_draft']
    posts = [m for m in c.method_calls if m[1] == 'action_post']
    assert len(drafts) == 2
    assert len(posts) == 2

    # write SO nas linhas da conta_origem (lids 1 e 3), com account_id destino
    writes_aml = [w for w in c.write_calls if w[0] == 'account.move.line']
    ids_escritos = sorted(i for w in writes_aml for i in w[1])
    assert ids_escritos == [1, 3]  # NUNCA o lid 2 (conta OUTRA)
    for _, _, vals in writes_aml:
        assert vals == {'account_id': DEST}

    # Estado final: linha 2 (OUTRA) intocada
    assert c._amls[2]['account_id'] == [OUTRA, 'OUTRA']
    assert mod.ReclassificacaoService._acc_id(c._amls[1]) == DEST
    assert mod.ReclassificacaoService._acc_id(c._amls[3]) == DEST


def test_executar_ordem_draft_write_post(mod):
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    svc.executar(plano, confirmar=True)
    # filtrar eventos do move 1001: draft(move), write(aml), post(move)
    seq = []
    for model, method, ids in c.method_calls:
        if 1001 in ids:
            seq.append(method)
    # button_draft antes de action_post para o mesmo move
    assert seq.index('button_draft') < seq.index('action_post')


# ---------------------------------------------------------------------------
# INVARIANTE pos action_post: state != posted -> FALHA e PARA o batch
# ---------------------------------------------------------------------------
def test_executar_post_que_nao_volta_posted_para_batch(mod):
    c = _fake_basico()

    # Monkeypatch: action_post do move 1001 deixa em draft (simula falha)
    orig_exec = c.execute_kw

    def _exec(model, method, args, kwargs=None):
        r = orig_exec(model, method, args, kwargs)
        ids = args[0] if args else []
        if method == 'action_post' and 1001 in ids:
            c._moves[1001]['state'] = 'draft'  # NAO voltou posted
        return r

    c.execute_kw = _exec
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    res = svc.executar(plano, confirmar=True)
    assert res['status'] == 'FALHA_POST_NAO_POSTED'
    # PAROU no primeiro move — 1002 nao foi processado
    assert 1002 not in [m for m, _, _ in
                        [(mid, a, b) for mid, a, b in
                         [(ids[0] if ids else None, model, method)
                          for model, method, ids in c.method_calls
                          if method == 'button_draft']]]
    # forma mais simples: so 1 button_draft chegou a rodar
    drafts = [m for m in c.method_calls if m[1] == 'button_draft']
    assert len(drafts) == 1


# ---------------------------------------------------------------------------
# Validacao pos-write via CONTADOR REAL (validar_lote da skill READ)
# ---------------------------------------------------------------------------
def test_validar_pos_write_integro(mod):
    # Apos write OK, validar_lote deve achar processadas==total, draft==0.
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    svc.executar(plano, confirmar=True)
    val = svc.validar_pos_write(plano, conta_destino=DEST, conta_origem=ORIG)
    assert val['integro'] is True
    assert val['processadas'] == val['total_esperado']
    assert val['moves_draft'] == 0


def test_validar_pos_write_detecta_residual_origem(mod):
    # Forca 1 linha a NAO migrar (fica na origem) -> validar detecta pendente.
    c = _fake_basico()
    svc = mod.ReclassificacaoService(c)
    plano = svc.planejar(ORIG, DEST, '2025-09-01', '2025-09-30', CD, J)
    svc.executar(plano, confirmar=True)
    # reverter lid 3 para origem manualmente (simula write parcial)
    c._amls[3]['account_id'] = [ORIG, 'ORIG']
    val = svc.validar_pos_write(plano, conta_destino=DEST, conta_origem=ORIG)
    # validar_lote (READ) marca residual-na-origem como `pendente` (nao
    # `divergente`), logo `integro` permanece True (semantica da skill READ).
    # O sinal de residual e processadas < total_esperado + pendentes >= 1 —
    # e e esse criterio que o CLI usa para declarar EXECUTADO_PARCIAL.
    assert val['pendentes'] >= 1
    assert val['processadas'] < val['total_esperado']
