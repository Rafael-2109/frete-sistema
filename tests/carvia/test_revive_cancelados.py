"""Regressao: importacao/re-linking NAO deve ressuscitar documentos CANCELADOS.

Cobre os vetores corrigidos do bug "revive de cancelados" (2026-06-16), alinhados
a R4 (status irreversivel) e R5 (fatura vincula apenas status elegivel):
- resolver_operacao_por_cte ignora operacao CANCELADA;
- _criar_junction_se_necessario nao recria junction p/ operacao CANCELADA;
- vincular_operacoes_da_fatura nao promove operacao CANCELADA -> FATURADO;
- regressao inversa: operacao elegivel CONTINUA sendo promovida normalmente.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date


def _chave() -> str:
    return ('3525' + uuid.uuid4().hex).ljust(44, '0')[:44]


def _sfx() -> str:
    return uuid.uuid4().hex[:6]


def _criar_op(db, status='RASCUNHO', cte_numero=None, nfs_ref=None):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte_numero or f'CTE-{_sfx()}',
        cte_chave_acesso=_chave(),
        cte_valor=Decimal('1000.00'),
        cte_data_emissao=date(2026, 4, 1),
        cnpj_cliente='12345678000100',
        nome_cliente='Cliente',
        uf_origem='SP', cidade_origem='SP',
        uf_destino='RJ', cidade_destino='RJ',
        status=status, tipo_entrada='IMPORTADO',
        criado_por='test',
        nfs_referenciadas_json=nfs_ref,
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_nf(db, numero_nf, chave=None):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero_nf,
        chave_acesso_nf=chave or _chave(),
        cnpj_emitente='12345678000100',
        nome_emitente='Emit',
        cnpj_destinatario='98765432000199',
        nome_destinatario='Dest',
        data_emissao=date(2026, 4, 1),
        valor_total=Decimal('500.00'),
        peso_bruto=Decimal('100.000'),
        status='ATIVA',
        tipo_fonte='MANUAL',
        criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _criar_fatura(db, numero=None):
    from app.carvia.models import CarviaFaturaCliente
    fat = CarviaFaturaCliente(
        numero_fatura=numero or f'FAT-{_sfx()}',
        cnpj_cliente='12345678000100',
        data_emissao=date(2026, 4, 10),
        valor_total=Decimal('0.00'),
        status='PENDENTE',
        status_conferencia='PENDENTE',
        criado_por='test',
    )
    db.session.add(fat)
    db.session.flush()
    return fat


def _criar_item(db, fatura_id, cte_numero, operacao_id):
    from app.carvia.models import CarviaFaturaClienteItem
    item = CarviaFaturaClienteItem(
        fatura_cliente_id=fatura_id,
        cte_numero=cte_numero,
        cte_data_emissao=date(2026, 4, 1),
        contraparte_cnpj='12345678000100',
        contraparte_nome='Cliente',
        operacao_id=operacao_id,
        frete=Decimal('50.00'),
    )
    db.session.add(item)
    db.session.flush()
    return item


class TestNaoReviveCancelados:

    def test_resolver_operacao_por_cte_ignora_cancelada(self, db):
        from app.carvia.services.documentos.linking_service import LinkingService
        _criar_op(db, status='CANCELADO', cte_numero='CTE-7001')
        db.session.flush()
        assert LinkingService.resolver_operacao_por_cte('CTE-7001') is None

    def test_junction_nao_criada_para_operacao_cancelada(self, db):
        from app.carvia.services.documentos.linking_service import LinkingService
        from app.carvia.models import CarviaOperacaoNf
        chave = _chave()
        op = _criar_op(db, status='CANCELADO', nfs_ref=[{
            'chave': chave, 'numero_nf': '12345',
            'cnpj_emitente': '12345678000100',
        }])
        nf = _criar_nf(db, numero_nf='12345', chave=chave)
        db.session.flush()

        junctions = LinkingService().vincular_nf_a_operacoes_orfas(nf)

        assert junctions == 0
        assert CarviaOperacaoNf.query.filter_by(
            operacao_id=op.id, nf_id=nf.id
        ).first() is None

    def test_fatura_nao_promove_operacao_cancelada(self, db):
        from app.carvia.services.documentos.linking_service import LinkingService
        op = _criar_op(db, status='CANCELADO', cte_numero='CTE-7002')
        fat = _criar_fatura(db)
        _criar_item(db, fat.id, 'CTE-7002', op.id)
        db.session.flush()

        stats = LinkingService().vincular_operacoes_da_fatura(fat.id)
        db.session.refresh(op)

        assert op.status == 'CANCELADO'        # nao ressuscitou
        assert op.fatura_cliente_id is None
        assert stats['operacoes_vinculadas'] == 0

    def test_operacao_ativa_continua_sendo_promovida(self, db):
        """Regressao inversa: operacao elegivel AINDA vira FATURADO."""
        from app.carvia.services.documentos.linking_service import LinkingService
        op = _criar_op(db, status='CONFIRMADO', cte_numero='CTE-7003')
        fat = _criar_fatura(db)
        _criar_item(db, fat.id, 'CTE-7003', op.id)
        db.session.flush()

        stats = LinkingService().vincular_operacoes_da_fatura(fat.id)
        db.session.refresh(op)

        assert op.status == 'FATURADO'
        assert op.fatura_cliente_id == fat.id
        assert stats['operacoes_vinculadas'] == 1
