"""Tests para EscrituracaoLfService v19+ ABRANGENTE (7 atomos).

Cobertura — 1 atomo por bloco:
  buscar_dfe (READ-only)               - 3 testes
  criar_dfe_a_partir_do_invoice_saida  - 4 testes
  escriturar_dfe                       - 3 testes
  gerar_po_from_dfe                    - 3 testes
  preencher_po                         - 2 testes
  confirmar_po                         - 3 testes
  criar_invoice_from_po                - 3 testes

Total: 21 testes mockados.

Pattern: cada teste usa MagicMock(odoo) para simular XML-RPC + dry-run
sempre planeja (corrige AP4) + real-run idempotente (idempotency por
campos do Odoo, sem assumir DB local).
"""
from unittest.mock import MagicMock

from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService


# ============================================================
# buscar_dfe
# ============================================================

def test_buscar_dfe_not_found():
    """encontrado=False quando search_read retorna []."""
    odoo = MagicMock()
    odoo.search_read.return_value = []
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.buscar_dfe(
        chave_nfe='35260518467441000163550010000132451007099001',
        company_id=1,
    )
    assert res['encontrado'] is False
    assert res['dfe_id'] is None
    assert res['status'] == 'ausente'
    assert res['erro'] is None


def test_buscar_dfe_found_pendente():
    """status='03' -> 'pendente'."""
    odoo = MagicMock()
    odoo.search_read.return_value = [{
        'id': 4321,
        'l10n_br_status': '03',
        'l10n_br_situacao_dfe': 'autorizado',
        'nfe_infnfe_ide_nnf': '200',
        'protnfe_infnfe_chnfe': '35260518467441000163550010000132451007099001',
        'purchase_id': False,
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.buscar_dfe(
        chave_nfe='35260518467441000163550010000132451007099001',
        company_id=1,
    )
    assert res['encontrado'] is True
    assert res['dfe_id'] == 4321
    assert res['status'] == 'pendente'
    assert res['raw']['nfe_infnfe_ide_nnf'] == '200'


def test_buscar_dfe_found_processado():
    """status='04' -> 'processado'."""
    odoo = MagicMock()
    odoo.search_read.return_value = [{
        'id': 9999,
        'l10n_br_status': '04',
        'l10n_br_situacao_dfe': 'autorizado',
        'nfe_infnfe_ide_nnf': '201',
        'protnfe_infnfe_chnfe': '35260518467441000163550010000132451007099002',
        'purchase_id': [777, 'PO/2026/0001'],
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.buscar_dfe(
        chave_nfe='35260518467441000163550010000132451007099002',
        company_id=1,
    )
    assert res['status'] == 'processado'
    assert res['dfe_id'] == 9999


# ============================================================
# criar_dfe_a_partir_do_invoice_saida
# ============================================================

def test_criar_dfe_dry_run_planeja():
    """dry_run=True NAO escreve; reporta plano com size do XML."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_xml_aut_nfe': 'PHhtbD48L3htbD4=',  # base64 fake
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099003',
        'l10n_br_numero_nota_fiscal': '300',
        'company_id': [5, 'LF'],
        'state': 'posted',
    }]
    # buscar_dfe interno retorna NAO encontrado
    odoo.search_read.return_value = []
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.criar_dfe_a_partir_do_invoice_saida(
        invoice_id_saida=607443, company_destino=1, dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['chave_nfe'] == '35260518467441000163550010000132451007099003'
    assert res['dfe_id'] is None
    assert 'plano' in res
    assert res['plano']['create_model'] == 'l10n_br_ciel_it_account.dfe'
    assert res['erro'] is None


def test_criar_dfe_xml_vazio_falha():
    """XML aut_nfe vazio -> FALHA xml_aut_nfe_vazio."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_xml_aut_nfe': False,  # vazio
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099004',
        'l10n_br_numero_nota_fiscal': '301',
        'company_id': [5, 'LF'],
        'state': 'posted',
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.criar_dfe_a_partir_do_invoice_saida(
        invoice_id_saida=607444, company_destino=1, dry_run=False,
    )
    assert res['status'] == 'FALHA'
    assert res['erro'] == 'xml_aut_nfe_vazio'


def test_criar_dfe_idempotent_existe():
    """DFe ja existe na company destino -> IDEMPOTENT_EXISTE."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_xml_aut_nfe': 'PHhtbD48L3htbD4=',
        'l10n_br_chave_nf': '35260518467441000163550010000132451007099005',
        'l10n_br_numero_nota_fiscal': '302',
        'company_id': [5, 'LF'],
        'state': 'posted',
    }]
    odoo.search_read.return_value = [{
        'id': 5555,
        'l10n_br_status': '04',
        'l10n_br_situacao_dfe': 'autorizado',
        'nfe_infnfe_ide_nnf': '302',
        'protnfe_infnfe_chnfe': '35260518467441000163550010000132451007099005',
        'purchase_id': False,
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.criar_dfe_a_partir_do_invoice_saida(
        invoice_id_saida=607445, company_destino=1, dry_run=False,
    )
    assert res['status'] == 'IDEMPOTENT_EXISTE'
    assert res['dfe_id'] == 5555


def test_criar_dfe_real_criado(monkeypatch):
    """real_run cria DFe + fire_and_poll OK -> CRIADO."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        # 1a: invoice saida
        [{
            'l10n_br_xml_aut_nfe': 'PHhtbD48L3htbD4=',
            'l10n_br_chave_nf':
                '35260518467441000163550010000132451007099006',
            'l10n_br_numero_nota_fiscal': '303',
            'company_id': [5, 'LF'],
            'state': 'posted',
        }],
        # 2a: poll processar (status='04' = processado)
        [{
            'l10n_br_status': '04',
            'l10n_br_situacao_dfe': 'autorizado',
        }],
    ]
    odoo.search_read.return_value = []  # nao existe DFe
    odoo.create.return_value = 7777

    svc = EscrituracaoLfService(odoo=odoo)
    # Patch sleep para acelerar
    monkeypatch.setattr('time.sleep', lambda _: None)
    res = svc.criar_dfe_a_partir_do_invoice_saida(
        invoice_id_saida=607446, company_destino=1, dry_run=False,
    )
    assert res['status'] == 'CRIADO'
    assert res['dfe_id'] == 7777
    # create chamado com xml_b64
    assert odoo.create.called
    call_args = odoo.create.call_args
    assert call_args[0][0] == 'l10n_br_ciel_it_account.dfe'
    assert call_args[0][1]['company_id'] == 1
    assert call_args[0][1]['l10n_br_xml_dfe'] == 'PHhtbD48L3htbD4='


# ============================================================
# escriturar_dfe
# ============================================================

def test_escriturar_dfe_dry_run():
    """dry_run=True NAO escreve; reporta plano."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.escriturar_dfe(
        dfe_id=4321,
        l10n_br_tipo_pedido='serv-industrializacao',
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['plano']['write_model'] == 'l10n_br_ciel_it_account.dfe'
    assert res['plano']['write_values']['l10n_br_tipo_pedido'] == (
        'serv-industrializacao'
    )
    # data_entrada default = hoje
    assert res['data_entrada']  # nao vazio
    assert res['erro'] is None


def test_escriturar_dfe_real_escriturado():
    """real_run escreve + verify -> ESCRITURADO. FIX A v20+: pre-read
    retorna valores DIFERENTES do proposto (forca caminho de write)."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        # 1a chamada: pre-read FIX A — DFe ainda vazio (forca write)
        [{'l10n_br_tipo_pedido': False, 'l10n_br_data_entrada': False}],
        # 2a chamada: post-write verify — confirma valores escritos
        [{
            'l10n_br_tipo_pedido': 'transf-filial',
            'l10n_br_data_entrada': '2026-05-26',
        }],
    ]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.escriturar_dfe(
        dfe_id=4321,
        l10n_br_tipo_pedido='transf-filial',
        data_entrada='2026-05-26',
        dry_run=False,
    )
    assert res['status'] == 'ESCRITURADO'
    assert odoo.write.called
    odoo.write.assert_called_with(
        'l10n_br_ciel_it_account.dfe', [4321],
        {
            'l10n_br_data_entrada': '2026-05-26',
            'l10n_br_tipo_pedido': 'transf-filial',
        },
    )


# ============================================================
# FIX A v20+ — idempotencia escriturar_dfe (anti-sobrescrita fiscal)
# ============================================================

def test_escriturar_dfe_idempotent_campos_iguais():
    """FIX A v20+: pre-read mostra valores ja iguais ao proposto
    -> IDEMPOTENT_ESCRITURADO (no-op, sem write).

    Cenario: caller passa data_entrada explicito e ambos campos ja
    estao iguais no Odoo. Anti-sobrescrita defensiva.
    """
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_tipo_pedido': 'serv-industrializacao',
        'l10n_br_data_entrada': '2026-05-18',
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.escriturar_dfe(
        dfe_id=4321,
        l10n_br_tipo_pedido='serv-industrializacao',
        data_entrada='2026-05-18',
        dry_run=False,
    )
    assert res['status'] == 'IDEMPOTENT_ESCRITURADO'
    assert res['idempotent_via'] == 'campos_ja_iguais'
    assert not odoo.write.called  # CRUCIAL: nao escreve


def test_escriturar_dfe_preserva_data_entrada_populada():
    """FIX A v20+: data_entrada ja populada no Odoo + caller usou default
    (None -> date.today()) -> PRESERVA data atual + se tipo igual,
    IDEMPOTENT via 'data_preservada_tipo_igual'.

    Cenario REAL: 4 DFes INDUSTRIALIZACAO_FB_LF do ciclo INVENTARIO_2026_05
    tem l10n_br_data_entrada=18-20/05 e default caller seria 26/05;
    sem FIX A, write reescreveria data fiscal de invoice posted.
    """
    odoo = MagicMock()
    odoo.read.return_value = [{
        'l10n_br_tipo_pedido': 'serv-industrializacao',
        'l10n_br_data_entrada': '2026-05-18',  # ja populada
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.escriturar_dfe(
        dfe_id=4321,
        l10n_br_tipo_pedido='serv-industrializacao',
        data_entrada=None,  # caller usa default = date.today()
        dry_run=False,
    )
    assert res['status'] == 'IDEMPOTENT_ESCRITURADO'
    assert res['idempotent_via'] == 'data_preservada_tipo_igual'
    assert res['data_entrada'] == '2026-05-18'  # data atual preservada
    assert not odoo.write.called  # CRUCIAL: nao escreve


def test_escriturar_dfe_tipo_pedido_invalido():
    """tipo_pedido fora de whitelist -> FALHA tipo_pedido_invalido."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.escriturar_dfe(
        dfe_id=4321,
        l10n_br_tipo_pedido='valor-aleatorio',
        dry_run=True,
    )
    assert res['status'] == 'FALHA'
    assert 'tipo_pedido_invalido' in res['erro']


# ============================================================
# gerar_po_from_dfe
# ============================================================

def test_gerar_po_dry_run():
    """dry_run=True NAO dispara; reporta plano. FIX B v20+: precisa cobrir
    todos os 3 caminhos vazios para chegar no dry-run plano."""
    odoo = MagicMock()
    # FIX B v20+: dfe_check ja' le purchase_id+purchase_fiscal_id
    odoo.read.return_value = [{
        'purchase_id': False, 'purchase_fiscal_id': False,
    }]
    # Caminho 3 reverso vazio
    odoo.search_read.return_value = []
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.gerar_po_from_dfe(dfe_id=4321, dry_run=True)
    assert res['status'] == 'DRY_RUN_OK'
    assert res['plano']['action'] == (
        'l10n_br_ciel_it_account.dfe.action_gerar_po_dfe'
    )
    assert res['plano']['dfe_ids'] == [4321]


def test_gerar_po_idempotent_existe():
    """DFe ja tem purchase_id (caminho 1 direto) -> IDEMPOTENT_EXISTE."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'purchase_id': [777, 'PO/2026/0001'],
        'purchase_fiscal_id': False,
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.gerar_po_from_dfe(dfe_id=4321, dry_run=False)
    assert res['status'] == 'IDEMPOTENT_EXISTE'
    assert res['po_id'] == 777
    assert res['idempotent_via'] == 'dfe_purchase_id_direto'


def test_gerar_po_real_criado(monkeypatch):
    """real-run: fire + poll retorna po_id. FIX B v20+: precisa cobrir
    3 caminhos vazios antes de chegar no fire."""
    odoo = MagicMock()
    # Sequencia de .read: 1a dfe_check FIX B (sem PO em ambos campos)
    # → 2a poll_gerar_po (com PO encontrada)
    odoo.read.side_effect = [
        [{'purchase_id': False, 'purchase_fiscal_id': False}],  # dfe_check
        [{'purchase_id': [888, 'PO/2026/0002']}],               # poll
    ]
    # Caminho 3 reverso vazio (no dfe_check)
    odoo.search_read.return_value = []
    odoo.execute_kw.return_value = None  # fire action retorna None
    svc = EscrituracaoLfService(odoo=odoo)
    monkeypatch.setattr('time.sleep', lambda _: None)
    res = svc.gerar_po_from_dfe(
        dfe_id=4321, poll_timeout_s=10, dry_run=False,
    )
    assert res['status'] == 'CRIADO'
    assert res['po_id'] == 888


# ============================================================
# FIX B v20+ — idempotencia gerar_po_from_dfe (3 caminhos vinculo DFe<->PO)
# ============================================================

def test_gerar_po_idempotent_via_purchase_fiscal_id():
    """FIX B v20+ caminho 2: DFe tem purchase_fiscal_id populado
    (75% dos concluidos via escrituracao) -> IDEMPOTENT_EXISTE sem fire.

    Pattern minerado de validacao_nf_po_service.py:530-534.
    """
    odoo = MagicMock()
    odoo.read.return_value = [{
        'purchase_id': False,
        'purchase_fiscal_id': [555, 'PO/2026/0010'],  # escrituracao
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.gerar_po_from_dfe(dfe_id=4321, dry_run=False)
    assert res['status'] == 'IDEMPOTENT_EXISTE'
    assert res['po_id'] == 555
    assert res['idempotent_via'] == 'dfe_purchase_fiscal_id'
    # CRUCIAL: nao chamou search_read (caminho 2 detectou antes)
    assert not odoo.search_read.called
    # CRUCIAL: nao disparou action
    assert not odoo.execute_kw.called


def test_gerar_po_idempotent_via_po_dfe_id_reverso():
    """FIX B v20+ caminho 3: DFe vazio em ambos campos diretos MAS
    PO existe via po.dfe_id reverso -> IDEMPOTENT_EXISTE sem fire.

    Caso descoberto em PROD 2026-05-26: 4 DFes INDUSTRIALIZACAO_FB_LF do
    INVENTARIO_2026_05 (42868/42930/42931/42882) tem purchase_id=False
    mas POs 42121/22/25/26 apontam reverso. Sem este check, _fire_and_poll
    dispararia action_gerar_po_dfe e DUPLICARIA PO+picking+invoice.
    """
    odoo = MagicMock()
    odoo.read.return_value = [{
        'purchase_id': False, 'purchase_fiscal_id': False,
    }]
    odoo.search_read.return_value = [{'id': 42125}]  # PO reverso
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.gerar_po_from_dfe(dfe_id=42868, dry_run=False)
    assert res['status'] == 'IDEMPOTENT_EXISTE'
    assert res['po_id'] == 42125
    assert res['idempotent_via'] == 'po_dfe_id_reverso'
    # CRUCIAL: search_read chamado com filtro correto
    odoo.search_read.assert_called_with(
        'purchase.order',
        [('dfe_id', '=', 42868), ('state', '!=', 'cancel')],
        ['id'], limit=1, order='id desc',
    )
    # CRUCIAL: nao disparou action_gerar_po_dfe
    assert not odoo.execute_kw.called


def test_gerar_po_timeout(monkeypatch):
    """CR-v19+-MED-2: poll_fn retorna None perpetuamente -> TIMEOUT."""
    odoo = MagicMock()
    # Idempotencia: sem PO. Poll: search_read tambem vazio (nunca materializa)
    odoo.read.return_value = [{'purchase_id': False}]
    odoo.search_read.return_value = []
    svc = EscrituracaoLfService(odoo=odoo)
    monkeypatch.setattr('time.sleep', lambda _: None)
    res = svc.gerar_po_from_dfe(
        dfe_id=4321, poll_timeout_s=4, dry_run=False,
    )
    assert res['status'] == 'TIMEOUT'
    assert 'poll_timeout_s=4' in res['erro']


# ============================================================
# preencher_po
# ============================================================

def test_preencher_po_dry_run():
    """dry_run=True NAO escreve."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.preencher_po(
        po_id=888,
        team_id=119,
        payment_term_id=2791,
        picking_type_id=1,
        company_id=1,
        payment_provider_id=92,
        dry_run=True,
    )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['plano']['write_values']['team_id'] == 119


def test_preencher_po_real():
    """real-run escreve."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'team_id': [119, 'NACOM'],
        'picking_type_id': [1, 'FB Receipts'],
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.preencher_po(
        po_id=888,
        team_id=119,
        payment_term_id=2791,
        picking_type_id=1,
        company_id=1,
        payment_provider_id=92,
        dry_run=False,
    )
    assert res['status'] == 'PREENCHIDO'
    odoo.write.assert_called_once_with(
        'purchase.order', [888],
        {
            'team_id': 119,
            'payment_provider_id': 92,
            'payment_term_id': 2791,
            'company_id': 1,
            'picking_type_id': 1,
        },
    )


# ============================================================
# confirmar_po
# ============================================================

def test_confirmar_po_dry_run():
    """dry_run=True NAO chama button_confirm."""
    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'draft'}]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.confirmar_po(po_id=888, dry_run=True)
    assert res['status'] == 'DRY_RUN_OK'
    assert res['plano']['state_atual'] == 'draft'


def test_confirmar_po_idempotent_ja_purchase():
    """state='purchase' -> IDEMPOTENT_CONFIRMADO."""
    odoo = MagicMock()
    odoo.read.return_value = [{'state': 'purchase'}]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.confirmar_po(po_id=888, dry_run=False)
    assert res['status'] == 'IDEMPOTENT_CONFIRMADO'
    assert res['state_final'] == 'purchase'
    # button_confirm NAO chamado
    assert not odoo.execute_kw.called


def test_confirmar_po_real_confirmado(monkeypatch):
    """real-run: button_confirm + poll -> CONFIRMADO."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        [{'state': 'draft'}],     # check inicial
        [{'state': 'purchase'}],  # poll pos-confirm
    ]
    svc = EscrituracaoLfService(odoo=odoo)
    monkeypatch.setattr('time.sleep', lambda _: None)
    res = svc.confirmar_po(po_id=888, dry_run=False)
    assert res['status'] == 'CONFIRMADO'
    assert res['state_final'] == 'purchase'
    # button_confirm chamado
    assert odoo.execute_kw.called


# ============================================================
# criar_invoice_from_po
# ============================================================

def test_criar_invoice_dry_run():
    """dry_run=True NAO dispara."""
    odoo = MagicMock()
    odoo.read.return_value = [{'invoice_ids': [], 'state': 'purchase'}]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.criar_invoice_from_po(po_id=888, dry_run=True)
    assert res['status'] == 'DRY_RUN_OK'
    assert res['plano']['action'] == (
        'purchase.order.action_create_invoice'
    )


def test_criar_invoice_idempotent_existe():
    """po.invoice_ids ja contem invoice -> IDEMPOTENT_EXISTE."""
    odoo = MagicMock()
    odoo.read.return_value = [{
        'invoice_ids': [9991, 9992],
        'state': 'purchase',
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.criar_invoice_from_po(po_id=888, dry_run=False)
    assert res['status'] == 'IDEMPOTENT_EXISTE'
    assert res['invoice_id'] == 9992  # ultimo


def test_criar_invoice_real_criado(monkeypatch):
    """real-run: fire + poll -> CRIADO."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        [{'invoice_ids': [], 'state': 'purchase'}],  # check inicial
        [{'invoice_ids': [9999]}],                    # poll
    ]
    svc = EscrituracaoLfService(odoo=odoo)
    monkeypatch.setattr('time.sleep', lambda _: None)
    res = svc.criar_invoice_from_po(
        po_id=888, poll_timeout_s=10, dry_run=False,
    )
    assert res['status'] == 'CRIADO'
    assert res['invoice_id'] == 9999


# ============================================================
# Pre-cond validation (AP4 — dry_run-first, raise APENAS antes do dry_run check
# em casos onde input MUITO invalido — testado em alguns atomos acima)
# ============================================================

def test_buscar_dfe_chave_invalida_nao_raise():
    """AP4: chave_nfe invalida NAO raise — retorna {erro}."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.buscar_dfe(chave_nfe='abc', company_id=1)
    assert res['encontrado'] is False
    assert res['erro'] == 'chave_nfe_invalida'
    # NAO chamou search_read
    assert not odoo.search_read.called


# ============================================================
# v23+ G039 — garantir_purchase_team (NF inter-company)
# ============================================================

def test_garantir_purchase_team_idempotente_quando_existe():
    """Team com user+company+active ja existe -> OK_EXISTENTE sem create."""
    odoo = MagicMock()
    # search_read retorna team existente
    odoo.execute_kw.return_value = [{
        'id': 143,
        'name': 'Aprovação LF - RAFAEL',
        'user_id': [42, 'Rafael de Carvalho Nascimento'],
        'company_id': [5, 'LA FAMIGLIA - LF'],
        'active': True,
    }]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.garantir_purchase_team(user_id=42, company_id=5, dry_run=False)

    assert res['status'] == 'OK_EXISTENTE'
    assert res['team_id'] == 143
    assert res['criado'] is False
    assert res['team_data']['name'] == 'Aprovação LF - RAFAEL'
    # APENAS 1 chamada execute_kw (search_read) — sem CREATE
    assert odoo.execute_kw.call_count == 1
    args, _ = odoo.execute_kw.call_args
    assert args[0] == 'purchase.team'
    assert args[1] == 'search_read'


def test_garantir_purchase_team_dry_run_planeja_create():
    """Team nao existe + dry_run -> DRY_RUN_OK sem write."""
    odoo = MagicMock()
    odoo.execute_kw.return_value = []  # search_read vazio
    odoo.read.return_value = [{'name': 'Rafael de Carvalho Nascimento', 'login': 'rafael@x'}]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.garantir_purchase_team(user_id=42, company_id=5, dry_run=True)

    assert res['status'] == 'DRY_RUN_OK'
    assert res['criado'] is False
    assert res['team_id'] is None
    # plano com nome derivado
    assert 'plano' in res
    assert res['plano']['create_model'] == 'purchase.team'
    assert res['plano']['values']['user_id'] == 42
    assert res['plano']['values']['company_id'] == 5
    assert 'RAFAEL' in res['plano']['values']['name']
    assert 'LF' in res['plano']['values']['name']  # sigla company=5


def test_garantir_purchase_team_create_real_quando_nao_existe():
    """Team nao existe + real-run -> CRIADO com team_id novo."""
    odoo = MagicMock()
    # Order: search_read vazio (nao existe) -> read user -> create -> read team novo
    odoo.execute_kw.side_effect = [
        [],     # search_read purchase.team -> vazio
        144,    # create purchase.team -> id
    ]
    odoo.read.side_effect = [
        [{'name': 'Maria Silva', 'login': 'maria@y'}],  # read res.users
        [{                                                # read purchase.team novo
            'id': 144,
            'name': 'Aprovação CD - MARIA',
            'user_id': [55, 'Maria Silva'],
            'company_id': [4, 'NACOM GOYA - CD'],
            'active': True,
        }],
    ]
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.garantir_purchase_team(user_id=55, company_id=4, dry_run=False)

    assert res['status'] == 'CRIADO'
    assert res['team_id'] == 144
    assert res['criado'] is True
    assert res['team_data']['id'] == 144
    # 2 execute_kw chamadas: search_read + create
    assert odoo.execute_kw.call_count == 2
    args_create, _ = odoo.execute_kw.call_args_list[1]
    assert args_create[0] == 'purchase.team'
    assert args_create[1] == 'create'
    values = args_create[2][0]
    assert values['user_id'] == 55
    assert values['company_id'] == 4
    assert 'CD' in values['name']
    assert 'MARIA' in values['name']


def test_garantir_purchase_team_user_id_invalido():
    """user_id <= 0 -> FALHA imediato sem chamada Odoo."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.garantir_purchase_team(user_id=0, company_id=5, dry_run=False)

    assert res['status'] == 'FALHA'
    assert res['team_id'] is None
    assert 'user_id_invalido' in (res['erro'] or '')
    assert not odoo.execute_kw.called


def test_garantir_purchase_team_company_id_invalido():
    """company_id <= 0 -> FALHA imediato sem chamada Odoo."""
    odoo = MagicMock()
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.garantir_purchase_team(user_id=42, company_id=-1, dry_run=False)

    assert res['status'] == 'FALHA'
    assert res['team_id'] is None
    assert 'company_id_invalido' in (res['erro'] or '')
    assert not odoo.execute_kw.called


def test_garantir_purchase_team_search_falha_propaga_erro():
    """Exception em search_read -> FALHA com erro detalhado, sem create."""
    odoo = MagicMock()
    odoo.execute_kw.side_effect = Exception('Connection timeout')
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.garantir_purchase_team(user_id=42, company_id=5, dry_run=False)

    assert res['status'] == 'FALHA'
    assert res['team_id'] is None
    assert 'erro_search_purchase_team' in (res['erro'] or '')


def test_garantir_purchase_team_fallback_nome_user_sem_name():
    """Se res.users.read falhar/retornar vazio, usa fallback 'USER{id}'."""
    odoo = MagicMock()
    odoo.execute_kw.return_value = []  # search_read vazio
    odoo.read.return_value = []  # res.users.read vazio -> fallback
    svc = EscrituracaoLfService(odoo=odoo)
    res = svc.garantir_purchase_team(user_id=99, company_id=1, dry_run=True)

    assert res['status'] == 'DRY_RUN_OK'
    assert 'USER99' in res['plano']['values']['name']
    assert 'FB' in res['plano']['values']['name']  # sigla company=1
