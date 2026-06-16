"""Testes — propagacao de comprovante pela cadeia CarVia (Frente 3b).

Foco no nucleo robusto (FKs reais): NF <-> operacao (CTe) <-> fatura cliente.
sincronizar_cadeia deve ser idempotente e propagar o comprovante por toda a cadeia.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date


def _chave_44() -> str:
    return ('3525' + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_nf(db, numero='NF001', cnpj_emit='11111111000111'):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente=cnpj_emit,
        cnpj_destinatario='99999999000199',
        tipo_fonte='MANUAL', status='ATIVA', criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _criar_operacao(db, cte='CTe-T1'):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte, cte_chave_acesso=_chave_44(),
        cte_valor=Decimal('1000.00'), cte_data_emissao=date(2026, 4, 1),
        cnpj_cliente='22222222000122', nome_cliente='Cliente Teste',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_fatura(db, num='FAT-T1'):
    from app.carvia.models import CarviaFaturaCliente
    f = CarviaFaturaCliente(
        cnpj_cliente='22222222000122', numero_fatura=num,
        data_emissao=date(2026, 6, 1), valor_total=Decimal('1000.00'),
        criado_por='test',
    )
    db.session.add(f)
    db.session.flush()
    return f


def _vincular_nf_op(db, op, nf):
    from app.carvia.models import CarviaOperacaoNf
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id))
    db.session.flush()


def _comprovante_em(db, entidade_tipo, entidade_id, origem='MANUAL'):
    from app.carvia.models import CarviaComprovantePagamento, CarviaComprovanteVinculo
    comp = CarviaComprovantePagamento(
        nome_original='c.pdf', nome_arquivo='s.pdf', caminho_s3='carvia/comprovantes/c.pdf',
        valor=Decimal('1000.00'), criado_por='test',
    )
    db.session.add(comp)
    db.session.flush()
    db.session.add(CarviaComprovanteVinculo(
        comprovante_id=comp.id, entidade_tipo=entidade_tipo, entidade_id=entidade_id,
        origem=origem, criado_por='test',
    ))
    db.session.flush()
    return comp


class TestPropagacao:

    def test_entidades_relacionadas_da_operacao(self, db):
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        nf = _criar_nf(db)
        op = _criar_operacao(db)
        _vincular_nf_op(db, op, nf)
        fat = _criar_fatura(db)
        op.fatura_cliente_id = fat.id
        db.session.flush()

        rel = CarviaComprovanteService._entidades_relacionadas('operacao', op.id)
        assert ('operacao', op.id) in rel
        assert ('nf', nf.id) in rel
        assert ('fatura_cliente', fat.id) in rel

    def test_sincronizar_propaga_operacao_para_nf_e_fatura(self, db):
        from app.carvia.models import CarviaComprovanteVinculo
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        nf = _criar_nf(db)
        op = _criar_operacao(db)
        _vincular_nf_op(db, op, nf)
        fat = _criar_fatura(db)
        op.fatura_cliente_id = fat.id
        db.session.flush()

        comp = _comprovante_em(db, 'operacao', op.id)
        criados = CarviaComprovanteService.sincronizar_cadeia('operacao', op.id, 'test')

        tipos = {
            v.entidade_tipo for v in
            CarviaComprovanteVinculo.query.filter_by(comprovante_id=comp.id).all()
        }
        assert 'nf' in tipos
        assert 'fatura_cliente' in tipos
        assert criados >= 2

    def test_sincronizar_idempotente(self, db):
        from app.carvia.models import CarviaComprovanteVinculo
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        nf = _criar_nf(db)
        op = _criar_operacao(db)
        _vincular_nf_op(db, op, nf)
        comp = _comprovante_em(db, 'operacao', op.id)

        CarviaComprovanteService.sincronizar_cadeia('operacao', op.id, 'test')
        total1 = CarviaComprovanteVinculo.query.filter_by(comprovante_id=comp.id).count()
        criados2 = CarviaComprovanteService.sincronizar_cadeia('operacao', op.id, 'test')
        total2 = CarviaComprovanteVinculo.query.filter_by(comprovante_id=comp.id).count()

        assert criados2 == 0
        assert total1 == total2

    def test_propaga_da_fatura_para_baixo(self, db):
        """Comprovante anexado na FATURA propaga para operacao e NF (caso real:
        cliente pagou com CNPJ != fatura, anexa na fatura e a busca inverte)."""
        from app.carvia.models import CarviaComprovanteVinculo
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        nf = _criar_nf(db)
        op = _criar_operacao(db)
        _vincular_nf_op(db, op, nf)
        fat = _criar_fatura(db)
        op.fatura_cliente_id = fat.id
        db.session.flush()

        comp = _comprovante_em(db, 'fatura_cliente', fat.id)
        CarviaComprovanteService.sincronizar_cadeia('fatura_cliente', fat.id, 'test')

        tipos = {
            v.entidade_tipo for v in
            CarviaComprovanteVinculo.query.filter_by(comprovante_id=comp.id).all()
        }
        assert {'fatura_cliente', 'operacao', 'nf'} <= tipos

    def test_tem_comprovante_batch(self, db):
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        op1 = _criar_operacao(db, cte='CTe-B1')
        op2 = _criar_operacao(db, cte='CTe-B2')
        _comprovante_em(db, 'operacao', op1.id)

        flags = CarviaComprovanteService.tem_comprovante_batch('operacao', [op1.id, op2.id])
        assert flags[op1.id] is True
        assert flags[op2.id] is False

    def test_soft_delete_some_da_flag(self, db):
        from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService
        op = _criar_operacao(db, cte='CTe-D1')
        comp = _comprovante_em(db, 'operacao', op.id)

        assert CarviaComprovanteService.tem_comprovante_batch('operacao', [op.id])[op.id] is True
        CarviaComprovanteService.soft_delete(comp.id)
        assert CarviaComprovanteService.tem_comprovante_batch('operacao', [op.id])[op.id] is False
