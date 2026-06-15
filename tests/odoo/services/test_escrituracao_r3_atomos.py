"""Testa os 2 átomos-gap R3 da Skill 7 para o WIRE do R2 (FLUXO L3 1.2.4):

  - resolver_chave_remessa (READ): a chave da remessa (refNFe da entrada) vem de
    account.move(NF-1 saída LF).referencia_ids[].l10n_br_chave_nf — PROVADO no Odoo
    vivo (s70): NF-1 791437.referencia_ids=[1825] → chave RPI 35260661...356795.
    Caminho robusto (R3 já gravado pela SA da saída, s59); NÃO via picking.
  - marcar_vinculo_r3 (WRITE dry-run-first): grava invoice_origin + referencia_ids
    (com company_id — gotcha s67) numa NF JÁ criada (a NF-1 de ENTRADA, caminho A,
    que o criar_invoice_from_po NÃO preenche). Espelha o R3 do montar_invoice_entrada_direta
    (que cobre só a NF-2 montada-direto). Substitui as escritas cruas do s63:199/s64:100.
"""
from unittest.mock import MagicMock
from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService

CHAVE_RPI = '35260661724241000178550010000946041007356795'
REF_MODEL = 'l10n_br_ciel_it_account.account.move.referencia'


class FakeOdooRef:
    """Modela account.move.referencia_ids → modelo referencia (s70 ground truth)."""
    def __init__(self, referencia_ids, refs):
        self._referencia_ids = referencia_ids   # ids one2many na NF de saída
        self._refs = refs                        # {ref_id: {l10n_br_chave_nf, company_id}}
        self.writes = []                         # registra escritas (deve ficar vazio — READ)

    def read(self, model, ids, fields=None):
        if model == 'account.move':
            return [{'id': ids[0], 'referencia_ids': list(self._referencia_ids)}]
        if model == REF_MODEL:
            return [{'id': i, **self._refs[i]} for i in ids if i in self._refs]
        return []

    def execute_kw(self, *a, **k):
        self.writes.append((a, k))   # qualquer escrita = violação READ-only
        return None


# ── resolver_chave_remessa (READ) ─────────────────────────────────────────────
def test_resolver_chave_remessa_da_nf1_saida():
    """NF-1 de saída tem 1 referencia = a remessa RPI."""
    odoo = FakeOdooRef([1825], {1825: {'l10n_br_chave_nf': CHAVE_RPI, 'company_id': [5, 'LF']}})
    res = EscrituracaoLfService(odoo=odoo).resolver_chave_remessa(nf_saida_id=791437, company_id=5)
    assert res['status'] == 'OK'
    assert res['chave'] == CHAVE_RPI
    assert res['chaves'] == [CHAVE_RPI]
    assert res['n'] == 1
    assert odoo.writes == [], 'resolver_chave_remessa é READ-only'


def test_resolver_chave_remessa_sem_referencia():
    odoo = FakeOdooRef([], {})
    res = EscrituracaoLfService(odoo=odoo).resolver_chave_remessa(nf_saida_id=791437, company_id=5)
    assert res['status'] == 'VAZIO'
    assert res['chave'] is None
    assert res['chaves'] == []
    assert res['n'] == 0


def test_resolver_chave_remessa_multiplas_refs_retorna_todas():
    """NF-2 de saída tem 2 refs (remessa + cross-NF-1); retorna todas, chave=1ª."""
    chave_nf1 = '35260618467441000163550010000133131007914378'
    odoo = FakeOdooRef([1826, 1827], {
        1826: {'l10n_br_chave_nf': CHAVE_RPI, 'company_id': [5, 'LF']},
        1827: {'l10n_br_chave_nf': chave_nf1, 'company_id': [5, 'LF']},
    })
    res = EscrituracaoLfService(odoo=odoo).resolver_chave_remessa(nf_saida_id=791441, company_id=5)
    assert res['status'] == 'OK'
    assert res['n'] == 2
    assert set(res['chaves']) == {CHAVE_RPI, chave_nf1}
    assert res['chave'] == CHAVE_RPI


def test_resolver_chave_remessa_id_invalido():
    odoo = FakeOdooRef([], {})
    res = EscrituracaoLfService(odoo=odoo).resolver_chave_remessa(nf_saida_id=0, company_id=5)
    assert res['status'] == 'FALHA'
    assert res['erro']


# ── marcar_vinculo_r3 (WRITE dry-run-first) ───────────────────────────────────
def test_marcar_vinculo_r3_dry_run_nao_escreve():
    odoo = MagicMock()
    res = EscrituracaoLfService(odoo=odoo).marcar_vinculo_r3(
        invoice_id=792219, company_id=1, invoice_origin='RET-IND-4870112-PILOTO',
        refnfe_chave=CHAVE_RPI)   # dry_run default
    assert res['status'] == 'DRY_RUN_OK'
    assert res['plano']['invoice_origin'] == 'RET-IND-4870112-PILOTO'
    ref = res['plano']['referencia_ids'][0][2]
    assert ref['l10n_br_chave_nf'] == CHAVE_RPI and ref['company_id'] == 1
    odoo.execute_kw.assert_not_called()


def test_marcar_vinculo_r3_confirmar_escreve_origin_e_refnfe():
    odoo = MagicMock()
    res = EscrituracaoLfService(odoo=odoo).marcar_vinculo_r3(
        invoice_id=792219, company_id=1, invoice_origin='RET-IND-4870112-PILOTO',
        refnfe_chave=CHAVE_RPI, dry_run=False)
    assert res['status'] == 'OK'
    assert res['origin_set'] is True and res['r3'] is True
    model, method, args = odoo.execute_kw.call_args_list[0][0][:3]
    assert (model, method) == ('account.move', 'write')
    assert args[0] == [792219]
    vals = args[1]
    assert vals['invoice_origin'] == 'RET-IND-4870112-PILOTO'
    assert vals['referencia_ids'][0][2]['l10n_br_chave_nf'] == CHAVE_RPI
    assert vals['referencia_ids'][0][2]['company_id'] == 1


def test_marcar_vinculo_r3_so_origin_sem_chave():
    odoo = MagicMock()
    res = EscrituracaoLfService(odoo=odoo).marcar_vinculo_r3(
        invoice_id=792219, company_id=1, invoice_origin='RET-IND-X', dry_run=False)
    assert res['status'] == 'OK'
    assert res['origin_set'] is True and res['r3'] is False
    vals = odoo.execute_kw.call_args_list[0][0][2][1]
    assert vals['invoice_origin'] == 'RET-IND-X'
    assert 'referencia_ids' not in vals


def test_marcar_vinculo_r3_nada_a_fazer_falha():
    """Sem origin E sem chave = no-op → FALHA sem escrever."""
    odoo = MagicMock()
    res = EscrituracaoLfService(odoo=odoo).marcar_vinculo_r3(
        invoice_id=792219, company_id=1, dry_run=False)
    assert res['status'] == 'FALHA'
    odoo.execute_kw.assert_not_called()


def test_marcar_vinculo_r3_invoice_invalido():
    odoo = MagicMock()
    res = EscrituracaoLfService(odoo=odoo).marcar_vinculo_r3(
        invoice_id=0, company_id=1, invoice_origin='X', dry_run=False)
    assert res['status'] == 'FALHA'
    odoo.execute_kw.assert_not_called()
