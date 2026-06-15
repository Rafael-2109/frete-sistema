"""Testa o WIRE do R2 — orchestrator C3 que compõe o FLUXO L3 1.2.4 (entrada de
retorno de industrialização FB←LF). Reproduz a receita provada do s67 (piloto 4870112).

Constituição §3.1: orchestrator C3 SÓ COMPÕE átomos (Skill 7 + Skill 5 + revaloração +
descoberta) — não faz XML-RPC cru. Estes testes verificam a COMPOSIÇÃO (ordem, args
derivados, dry-run propagado), com os services-átomos injetados como mocks. A lógica de
cada átomo já tem testes próprios (FakeOdoo). NÃO testamos comportamento de mock — testamos
o que o orchestrator faz: dispatch, derivação de args do spec, propagação de dry_run.
"""
from unittest.mock import MagicMock
from app.odoo.estoque.orchestrators.entrada_retorno_industrializacao import (
    EntradaRetornoIndustrializacaoExecutor as Wire,
    JOURNAL_ENTRI, OP_3252_ENTRADA, ACC_TRANSIT_ID, JOURNAL_REVAL,
    COMPANY_FB, PARTNER_LF, TIPO_PEDIDO_NF1,
)

CHAVE_REMESSA = '35260661724241000178550010000946041007356795'
CHAVE_NF1 = '35260618467441000163550010000133131007914378'

DESCOBERTA = {
    'nf1_id': 791437,
    'pa': {'product_id': 27834, 'qtd_faturada': 1.0, 'lote': 60542},
    'produzido_total': 3.0,
    'componentes': [
        {'product_id': 210, 'default_code': '210030010', 'name': 'FRASCO', 'qty': 4.0,
         'price_unit': 22.231, 'subtotal': 88.924},
        {'product_id': 105, 'default_code': '104000007', 'name': 'CORANTE', 'qty': 0.06,
         'price_unit': 6.29, 'subtotal': 0.3774},
    ],
    'total': 89.30,
    'remessa': {'picking_id': 322451, 'picking_name': 'LF/IN/01790', 'votos': 2},
}


def _wire(**svc_overrides):
    """Wire com odoo + 4 services-átomos mockados (injeção test-friendly)."""
    odoo = MagicMock()
    descoberta = MagicMock()
    descoberta.descobrir_fonte_nf2.return_value = DESCOBERTA
    escrit = MagicMock()
    escrit.resolver_chave_remessa.return_value = {'status': 'OK', 'chave': CHAVE_REMESSA, 'chaves': [CHAVE_REMESSA], 'n': 1}
    escrit.buscar_dfe.return_value = {'encontrado': True, 'dfe_id': 44523, 'status': 'processado', 'n_linhas': 1}
    odoo.read.return_value = [{'id': 791437, 'l10n_br_chave_nf': CHAVE_NF1, 'invoice_date': '2026-06-14'}]
    w = Wire(odoo=odoo, escrit_svc=escrit, picking_svc=MagicMock(),
             reval_svc=MagicMock(), descoberta_svc=descoberta)
    for k, v in svc_overrides.items():
        setattr(w, k, v)
    return w, odoo, escrit, descoberta


# ── planejar (READ) ───────────────────────────────────────────────────────────
def test_planejar_monta_spec_via_descoberta_e_chaves():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='RET-IND-4870112-PILOTO')
    descoberta.descobrir_fonte_nf2.assert_called_once_with(791437)
    escrit.resolver_chave_remessa.assert_called_once()
    assert spec['chave_remessa'] == CHAVE_REMESSA
    assert spec['chave_nf1'] == CHAVE_NF1
    assert spec['dfe_nf1_id'] == 44523
    assert spec['pa_product_id'] == 27834
    assert spec['total_ic'] == 89.30
    assert spec['ciclo'] == 'RET-IND-4870112-PILOTO'
    assert len(spec['componentes']) == 2


def test_planejar_busca_dfe_da_nf1_na_fb():
    w, odoo, escrit, descoberta = _wire()
    w.planejar(nf1_saida_lf_id=791437, ciclo='C')
    # buscar_dfe pela chave da NF-1 de saída, na company FB=1
    _, kw = escrit.buscar_dfe.call_args
    assert kw['chave_nfe'] == CHAVE_NF1
    assert kw['company_id'] == COMPANY_FB


# ── montar_nf2 (B1) ───────────────────────────────────────────────────────────
def test_montar_nf2_compoe_atomo_com_op3252_j1084_refnfe():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='RET-IND-4870112-PILOTO')
    escrit.montar_invoice_entrada_direta.return_value = {'status': 'DRY_RUN_OK', 'total': 89.30}
    w.montar_nf2(spec, dry_run=True)
    _, kw = escrit.montar_invoice_entrada_direta.call_args
    assert kw['journal_id'] == JOURNAL_ENTRI
    assert kw['operacao_id'] == OP_3252_ENTRADA
    assert kw['move_type'] == 'in_invoice'
    assert kw['partner_id'] == PARTNER_LF
    assert kw['company_id'] == COMPANY_FB
    assert kw['refnfe_chave'] == CHAVE_REMESSA
    assert kw['invoice_origin'] == 'RET-IND-4870112-PILOTO'
    assert kw['dry_run'] is True
    # linhas vêm dos componentes da descoberta (product_id/quantity/price_unit)
    linhas = kw['linhas']
    assert {'product_id', 'quantity', 'price_unit'} <= set(linhas[0])
    assert linhas[0]['product_id'] == 210 and linhas[0]['quantity'] == 4.0


def test_montar_nf2_dry_run_propaga():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=1, ciclo='C')
    escrit.montar_invoice_entrada_direta.return_value = {'status': 'DRY_RUN_OK'}
    w.montar_nf2(spec, dry_run=True)
    assert escrit.montar_invoice_entrada_direta.call_args.kwargs['dry_run'] is True
    w.montar_nf2(spec, dry_run=False)
    assert escrit.montar_invoice_entrada_direta.call_args.kwargs['dry_run'] is False


# ── postar_nf2 (B2 — baixa ATIVA) ─────────────────────────────────────────────
def test_postar_nf2_compoe_postar_invoice():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=1, ciclo='C')
    escrit.postar_invoice.return_value = {'status': 'DRY_RUN_OK'}
    w.postar_nf2(spec, nf2_invoice_id=795439, dry_run=True)
    _, kw = escrit.postar_invoice.call_args
    assert kw['invoice_id'] == 795439
    assert kw['company_id'] == COMPANY_FB
    assert kw['dry_run'] is True


# ── revalorar (C1 — account TRANSIT, não CMV) ─────────────────────────────────
def test_revalorar_usa_conta_transitoria_nao_cmv():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='C')
    w.reval.revalorar_custo.return_value = {'status': 'DRY_RUN_OK'}
    w.revalorar(spec, dry_run=True)
    _, kw = w.reval.revalorar_custo.call_args
    assert kw['product_id'] == 27834
    assert kw['added_value'] == 89.30          # = Ic (total da descoberta)
    assert kw['account_id'] == ACC_TRANSIT_ID   # transitória 1150100011 (NÃO CMV)
    assert kw['account_journal_id'] == JOURNAL_REVAL
    assert kw['company_id'] == COMPANY_FB
    assert kw['dry_run'] is True


# ── escriturar_nf1_po (caminho A, sub-etapa 1) ────────────────────────────────
def test_escriturar_nf1_po_compoe_caminho_a_em_ordem():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='C')
    escrit.garantir_purchase_team.return_value = {'status': 'DRY_RUN_OK', 'team_id': 144}
    escrit.alinhar_dfe_lines_company.return_value = {'status': 'OK'}
    escrit.escriturar_dfe.return_value = {'status': 'DRY_RUN_OK'}
    escrit.gerar_po_from_dfe.return_value = {'status': 'DRY_RUN_OK', 'po_id': None}
    w.escriturar_nf1_po(spec, dry_run=True)
    # tipo de pedido serv-industrializacao no escriturar_dfe
    assert escrit.escriturar_dfe.call_args.kwargs['l10n_br_tipo_pedido'] == TIPO_PEDIDO_NF1
    # dry_run propagado aos átomos que o aceitam
    assert escrit.escriturar_dfe.call_args.kwargs['dry_run'] is True
    assert escrit.gerar_po_from_dfe.call_args.kwargs['dry_run'] is True
    # garantir_team chamado para FB
    assert escrit.garantir_purchase_team.call_args.kwargs['company_id'] == COMPANY_FB


# ── escriturar_nf1_invoice (caminho A, sub-etapa 2 — picking C9 + invoice) ─────
def test_escriturar_nf1_invoice_dry_run_nao_chama_picking_c9():
    """C9 (criar_picking_entrada_destino_manual) NÃO tem dry_run — SEMPRE escreve.
    Em dry-run o orchestrator NÃO pode chamá-la (só reporta o plano)."""
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='C')
    escrit.garantir_purchase_team.return_value = {'status': 'OK_EXISTENTE', 'team_id': 144}
    escrit.preencher_po.return_value = {'status': 'DRY_RUN_OK'}
    escrit.confirmar_po.return_value = {'status': 'DRY_RUN_OK'}
    escrit.criar_invoice_from_po.return_value = {'status': 'DRY_RUN_OK', 'invoice_id': None}
    w.escriturar_nf1_invoice(spec, po_id=43464, dry_run=True)
    w.picking.criar_picking_entrada_destino_manual.assert_not_called()
    assert escrit.preencher_po.call_args.kwargs['dry_run'] is True


def test_escriturar_nf1_invoice_confirmar_chama_c9_com_po_line():
    w, odoo, escrit, descoberta = _wire()
    odoo.search_read.return_value = [{'id': 131508}]  # po.line do PA
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='RET-IND-4870112-PILOTO')
    escrit.garantir_purchase_team.return_value = {'status': 'OK_EXISTENTE', 'team_id': 144}
    escrit.preencher_po.return_value = {'status': 'PREENCHIDO'}
    escrit.confirmar_po.return_value = {'status': 'CONFIRMADO', 'state_final': 'purchase'}
    w.picking.criar_picking_entrada_destino_manual.return_value = {'status': 'CRIADO', 'picking_id': 325347, 'state': 'done'}
    escrit.criar_invoice_from_po.return_value = {'status': 'CRIADO', 'invoice_id': 792219}
    res = w.escriturar_nf1_invoice(spec, po_id=43464, dry_run=False)
    # C9 chamado com o PA, src 26489 → dst 8, pt52, purchase_line_id, partner LF
    args, kw = w.picking.criar_picking_entrada_destino_manual.call_args
    call = kw if kw else dict(zip(
        ['company_destino_id', 'location_origem_id', 'location_destino_id', 'moves_data',
         'picking_type_id', 'origin', 'partner_id'], args))
    assert call['company_destino_id'] == COMPANY_FB
    assert call['location_origem_id'] == 26489 and call['location_destino_id'] == 8
    assert call['picking_type_id'] == 52 and call['partner_id'] == PARTNER_LF
    mv = call['moves_data'][0]
    assert mv['product_id'] == 27834 and mv['purchase_line_id'] == 131508
    assert res['nf1_invoice_id'] == 792219


# ── postar_nf1 + R3 ───────────────────────────────────────────────────────────
def test_postar_nf1_posta_e_marca_r3():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='RET-IND-4870112-PILOTO')
    escrit.postar_invoice.return_value = {'status': 'POSTADO', 'state_final': 'posted'}
    escrit.marcar_vinculo_r3.return_value = {'status': 'OK', 'r3': True}
    w.postar_nf1(spec, nf1_invoice_id=792219, dry_run=False)
    assert escrit.postar_invoice.call_args.kwargs['invoice_id'] == 792219
    # R3 marca origin + chave da remessa na NF-1
    _, kw = escrit.marcar_vinculo_r3.call_args
    assert kw['invoice_id'] == 792219
    assert kw['invoice_origin'] == 'RET-IND-4870112-PILOTO'
    assert kw['refnfe_chave'] == CHAVE_REMESSA


# ── medir (gate, READ) ────────────────────────────────────────────────────────
def test_medir_e_read_only_e_reporta_26489():
    w, odoo, escrit, descoberta = _wire()
    spec = w.planejar(nf1_saida_lf_id=791437, ciclo='C')
    # odoo.read_group / search_read mockados via MagicMock retornam MagicMock; medir não deve escrever
    gate = w.medir(spec)
    assert 'contas' in gate or 'gate' in gate
    # nenhuma escrita
    for call in odoo.execute_kw.call_args_list:
        assert call[0][1] not in ('create', 'write', 'action_post', 'unlink')


def _dom_get(domain, field):
    for t in domain:
        if isinstance(t, (list, tuple)) and len(t) == 3 and t[0] == field:
            return t[2]
    return None


class FakeOdooMedir:
    """Modela as 3 fontes do gate por CICLO: remessa (chave) · entradas (invoice_origin) ·
    revaloração (SVL→account_move). Prova que medir SOMA as 3, não só as entradas."""
    REMESSA, NF2_ENT, NF1_ENT, REVAL_MOVE = 735679, 795439, 792219, 900

    def search_read(self, model, domain, fields=None, **k):
        if model == 'account.move':
            if _dom_get(domain, 'l10n_br_chave_nf'):                  # remessa por chave
                return [{'id': self.REMESSA, 'name': 'RPI/2026/00245'}]
            if _dom_get(domain, 'invoice_origin'):                    # entradas por origin
                return [{'id': self.NF2_ENT, 'name': 'ENTRI'}, {'id': self.NF1_ENT, 'name': 'ENTSI'}]
            return []
        if model == 'stock.valuation.layer':                          # revaloração por SVL
            return [{'account_move_id': [self.REVAL_MOVE, 'reval'], 'value': 279.23}]
        if model == 'account.move.line':
            acc = _dom_get(domain, 'account_id')
            mids = _dom_get(domain, 'move_id') or []
            if acc == 22800:    # ATIVA: remessa +279,23 / NF-2 −279,23 = 0
                out = []
                if self.REMESSA in mids: out.append({'debit': 279.23, 'credit': 0.0})
                if self.NF2_ENT in mids: out.append({'debit': 0.0, 'credit': 279.23})
                return out
            if acc == 26842:    # TRANSIT: NF-2 +279,23, NF-1 +26,23, reval −279,23 = +26,23
                out = []
                if self.NF2_ENT in mids: out.append({'debit': 279.23, 'credit': 0.0})
                if self.NF1_ENT in mids: out.append({'debit': 26.23, 'credit': 0.0})
                if self.REVAL_MOVE in mids: out.append({'debit': 0.0, 'credit': 279.23})
                return out
            if acc == 22294:    # PA: reval +279,23 (só a revaloração toca o PA)
                return [{'debit': 279.23, 'credit': 0.0}] if self.REVAL_MOVE in mids else []
            return []
        if model == 'stock.quant':
            return [{'quantity': 0.0}]
        return []


def test_medir_soma_remessa_entradas_e_revaloracao():
    spec = {'ciclo': 'RET-IND-4870112-PILOTO', 'pa_product_id': 27834,
            'chave_remessa': CHAVE_REMESSA, 'total_ic': 279.23}
    w = Wire(odoo=FakeOdooMedir())
    gate = w.medir(spec)
    assert gate['contas']['ATIVA'] == 0.0            # remessa − NF-2 (lote inteiro fecha)
    assert gate['contas']['PA'] == 279.23            # SÓ a revaloração toca o PA → prova a coleta de SVL
    assert gate['contas']['TRANSIT'] == 26.23        # NF-2 + NF-1 − reval
    tipos = {m['tipo'] for m in gate['moves_incluidos']}
    assert tipos == {'remessa', 'entrada', 'revaloracao'}
