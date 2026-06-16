"""Testes — models de Comprovante de Pagamento CarVia (Frente 3a).

Valida estrutura: criacao, vinculo N:N, cascade delete e a flag pago da cotacao.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import date


def _criar_comprovante(db, nome='comp.pdf'):
    from app.carvia.models import CarviaComprovantePagamento
    c = CarviaComprovantePagamento(
        nome_original=nome,
        nome_arquivo='s3_' + nome,
        caminho_s3='carvia/comprovantes/' + nome,
        valor=Decimal('1500.00'),
        data_pagamento=date(2026, 6, 1),
        cnpj_pagador='12345678000199',
        criado_por='test',
    )
    db.session.add(c)
    db.session.flush()
    return c


class TestComprovanteModels:

    def test_criar_comprovante_e_vinculo_nn(self, db):
        from app.carvia.models import CarviaComprovanteVinculo
        c = _criar_comprovante(db)
        assert c.id is not None
        assert c.ativo is True
        # 1 comprovante -> 2 documentos (paga 2 fretes juntos)
        db.session.add(CarviaComprovanteVinculo(
            comprovante_id=c.id, entidade_tipo='cotacao', entidade_id=10,
            origem='MANUAL', criado_por='test'))
        db.session.add(CarviaComprovanteVinculo(
            comprovante_id=c.id, entidade_tipo='fatura_cliente', entidade_id=20,
            origem='PROPAGADO', criado_por='test'))
        db.session.flush()
        assert len(c.vinculos) == 2

    def test_cascade_delete_remove_vinculos(self, db):
        from app.carvia.models import CarviaComprovanteVinculo
        c = _criar_comprovante(db)
        db.session.add(CarviaComprovanteVinculo(
            comprovante_id=c.id, entidade_tipo='operacao', entidade_id=3,
            criado_por='test'))
        db.session.flush()
        cid = c.id
        db.session.delete(c)
        db.session.flush()
        assert CarviaComprovanteVinculo.query.filter_by(comprovante_id=cid).count() == 0

    def test_cotacao_tem_flag_pago(self, db):
        from app.carvia.models import CarviaCotacao
        for campo in ('pago', 'pago_em', 'pago_por'):
            assert hasattr(CarviaCotacao, campo), f'CarviaCotacao deveria ter {campo}'
