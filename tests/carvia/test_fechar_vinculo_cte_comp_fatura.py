"""Testes — fechar_vinculo_cte_comp_fatura (A1 Bug #2) com o gate revisado.

Cenario: a fatura SSW entra por PDF (cria item com cte_numero) ANTES do XML do
CTe Complementar virar `CarviaCteComplementar`. Quando o XML chega, o linking
amarra o item existente ao CTe Comp.

Mudanca 2026-06-22: amarrar e operacao DOCUMENTAL (preenche FK + marca o CTe
FATURADO), nao edicao financeira. Em fatura ja paga/conferida o vinculo passa a
ser permitido quando NAO altera o valor_total; se o valor mudaria, segue
bloqueado (protege o financeiro).
"""

from __future__ import annotations

from datetime import date


def _criar_operacao(db, cte_numero='297'):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte_numero, cnpj_cliente='09089839000112',
        nome_cliente='LAIOUNS', uf_destino='SP', cidade_destino='SAO PAULO',
        tipo_entrada='IMPORTACAO_MANUAL', status='RASCUNHO', criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_cte_comp(db, operacao_id, cte_numero='302', valor=100, status='EMITIDO'):
    from app.carvia.models import CarviaCteComplementar
    cc = CarviaCteComplementar(
        numero_comp=f'COMP-T{cte_numero}', operacao_id=operacao_id,
        cte_numero=cte_numero, cte_valor=valor, status=status,
        fatura_cliente_id=None, criado_por='test',
    )
    db.session.add(cc)
    db.session.flush()
    return cc


def _criar_fatura(db, valor_total, status='PENDENTE', status_conferencia='PENDENTE',
                  total_conciliado=0, conciliado=False, numero='194-5'):
    from app.carvia.models import CarviaFaturaCliente
    fat = CarviaFaturaCliente(
        cnpj_cliente='57339413000112', nome_cliente='ECOMOVE BRASIL LTDA',
        numero_fatura=numero, data_emissao=date(2026, 6, 5),
        valor_total=valor_total, status=status,
        status_conferencia=status_conferencia, total_conciliado=total_conciliado,
        conciliado=conciliado, criado_por='test',
    )
    db.session.add(fat)
    db.session.flush()
    return fat


def _criar_item(db, fatura_id, cte_numero='302', frete=100):
    from app.carvia.models import CarviaFaturaClienteItem
    item = CarviaFaturaClienteItem(
        fatura_cliente_id=fatura_id, cte_numero=cte_numero, nf_numero='38610',
        operacao_id=None, nf_id=None, cte_complementar_id=None, frete=frete,
    )
    db.session.add(item)
    db.session.flush()
    return item


class TestFecharVinculoCteCompFatura:

    def test_amarra_fatura_paga_quando_valor_nao_muda(self, db):
        """Fatura PAGA + valor identico (100=100): amarra (documental)."""
        from app.carvia.services.documentos.linking_service import LinkingService

        op = _criar_operacao(db)
        comp = _criar_cte_comp(db, op.id, cte_numero='302', valor=100)
        fat = _criar_fatura(db, valor_total=100, status='PAGA',
                            total_conciliado=100, conciliado=True)
        item = _criar_item(db, fat.id, cte_numero='302')

        res = LinkingService().fechar_vinculo_cte_comp_fatura(comp.id)

        assert res['status'] == 'VINCULADO', res
        assert comp.fatura_cliente_id == fat.id
        assert comp.status == 'FATURADO'
        assert item.cte_complementar_id == comp.id
        assert float(fat.valor_total) == 100.0  # inalterado

    def test_bloqueia_fatura_paga_quando_valor_mudaria(self, db):
        """Fatura PAGA cujo valor_total (100) divergiria do que a amarracao
        recalcula (50): segue bloqueada — protege o financeiro."""
        from app.carvia.services.documentos.linking_service import LinkingService

        op = _criar_operacao(db, cte_numero='400')
        comp = _criar_cte_comp(db, op.id, cte_numero='303', valor=50)
        fat = _criar_fatura(db, valor_total=100, status='PAGA',
                            total_conciliado=100, conciliado=True, numero='195-3')
        _criar_item(db, fat.id, cte_numero='303')

        res = LinkingService().fechar_vinculo_cte_comp_fatura(comp.id)

        assert res['status'] == 'SKIP_FATURA_BLOQUEADA', res
        assert comp.fatura_cliente_id is None
        assert comp.status == 'EMITIDO'

    def test_amarra_fatura_editavel_recalcula_valor(self, db):
        """Fatura PENDENTE (editavel): amarra e recalcula valor_total."""
        from app.carvia.services.documentos.linking_service import LinkingService

        op = _criar_operacao(db, cte_numero='401')
        comp = _criar_cte_comp(db, op.id, cte_numero='304', valor=240)
        fat = _criar_fatura(db, valor_total=0, status='PENDENTE', numero='196-1')
        _criar_item(db, fat.id, cte_numero='304')

        res = LinkingService().fechar_vinculo_cte_comp_fatura(comp.id)

        assert res['status'] == 'VINCULADO', res
        assert comp.fatura_cliente_id == fat.id
        assert float(fat.valor_total) == 240.0

    def test_sem_fatura_quando_nenhum_item_referencia(self, db):
        from app.carvia.services.documentos.linking_service import LinkingService

        op = _criar_operacao(db, cte_numero='402')
        comp = _criar_cte_comp(db, op.id, cte_numero='999', valor=100)
        # fatura existe mas o item referencia outro cte_numero
        fat = _criar_fatura(db, valor_total=100, status='PENDENTE', numero='197-9')
        _criar_item(db, fat.id, cte_numero='888')

        res = LinkingService().fechar_vinculo_cte_comp_fatura(comp.id)

        assert res['status'] == 'SEM_FATURA', res
        assert comp.fatura_cliente_id is None

    def test_idempotente_ja_vinculado(self, db):
        from app.carvia.services.documentos.linking_service import LinkingService

        op = _criar_operacao(db, cte_numero='403')
        fat = _criar_fatura(db, valor_total=100, status='PENDENTE', numero='198-7')
        comp = _criar_cte_comp(db, op.id, cte_numero='305', valor=100)
        comp.fatura_cliente_id = fat.id
        db.session.flush()

        res = LinkingService().fechar_vinculo_cte_comp_fatura(comp.id)
        assert res['status'] == 'SKIP', res
        assert res['motivo'] == 'ja_vinculado'
