"""Testa EscrituracaoLfService.postar_invoice — átomo-gap do WIRE do R2.

action_post de uma NF de ENTRADA (escrituração contábil, NÃO SEFAZ): o s67 fazia
XML-RPC cru (--postar-nf1/--postar-nf2). Vira átomo (dry-run-first + idempotente por
state) para o orchestrator C3 só COMPOR, sem XML-RPC cru (constituição §3.1). É o
action_post que baixa a compensação no_payment (NF-2) / cruza o SVL do picking (NF-1).
"""
from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService


class FakeOdooPost:
    def __init__(self, state='draft'):
        self._state = state
        self.posts = []   # registra action_post chamados

    def read(self, model, ids, fields=None):
        if model == 'account.move':
            return [{'id': ids[0], 'state': self._state}]
        return []

    def execute_kw(self, model, method, args, kwargs=None):
        if method == 'action_post':
            self.posts.append((model, args))
            self._state = 'posted'   # simula efeito do post
        return True


def test_postar_invoice_dry_run_nao_posta():
    odoo = FakeOdooPost(state='draft')
    res = EscrituracaoLfService(odoo=odoo).postar_invoice(invoice_id=795439, company_id=1)
    assert res['status'] == 'DRY_RUN_OK'
    assert res['state_atual'] == 'draft'
    assert odoo.posts == []


def test_postar_invoice_confirmar_posta_draft():
    odoo = FakeOdooPost(state='draft')
    res = EscrituracaoLfService(odoo=odoo).postar_invoice(
        invoice_id=795439, company_id=1, dry_run=False)
    assert res['status'] == 'POSTADO'
    assert res['state_final'] == 'posted'
    assert odoo.posts and odoo.posts[0][0] == 'account.move'
    assert odoo.posts[0][1][0] == [795439]


def test_postar_invoice_idempotente_ja_posted():
    odoo = FakeOdooPost(state='posted')
    res = EscrituracaoLfService(odoo=odoo).postar_invoice(
        invoice_id=795439, company_id=1, dry_run=False)
    assert res['status'] == 'IDEMPOTENT_POSTED'
    assert res['state_final'] == 'posted'
    assert odoo.posts == [], 'não deve re-postar uma NF já posted'


def test_postar_invoice_id_invalido():
    odoo = FakeOdooPost()
    res = EscrituracaoLfService(odoo=odoo).postar_invoice(invoice_id=0, company_id=1, dry_run=False)
    assert res['status'] == 'FALHA'
    assert odoo.posts == []
