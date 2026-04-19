"""Teste C4 (2026-04-19): refator 2.5 — operador JSONB `@>` substitui
ILIKE no linking NF->Operacao via nfs_referenciadas_json.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date


def _gerar_chave_44(prefixo='3525') -> str:
    return (prefixo + uuid.uuid4().hex).ljust(44, '0')[:44]


def _sfx() -> str:
    return uuid.uuid4().hex[:6]


def _criar_op(db, nfs_ref=None):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=f'CTE-{_sfx()}',
        cte_chave_acesso=_gerar_chave_44(),
        cte_valor=Decimal('1000.00'),
        cte_data_emissao=date(2026, 4, 1),
        cnpj_cliente='12345678000100',
        nome_cliente='Cliente',
        uf_origem='SP', cidade_origem='SP',
        uf_destino='RJ', cidade_destino='RJ',
        status='RASCUNHO', tipo_entrada='IMPORTADO',
        criado_por='test',
        nfs_referenciadas_json=nfs_ref,
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_nf(db, numero_nf, chave=None, cnpj='12345678000100'):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero_nf,
        chave_acesso_nf=chave or _gerar_chave_44(),
        cnpj_emitente=cnpj,
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


class TestC4JsonbLinking:

    def test_match_por_chave_via_jsonb(self, db):
        """NF com chave X encontra operacao que referencia chave X em
        nfs_referenciadas_json via operador @> (C4)."""
        from app.carvia.services.documentos.linking_service import LinkingService

        chave_nf = _gerar_chave_44()
        op = _criar_op(db, nfs_ref=[{
            'chave': chave_nf,
            'numero_nf': '12345',
            'cnpj_emitente': '12345678000100',
        }])
        nf = _criar_nf(db, numero_nf='12345', chave=chave_nf)
        db.session.flush()

        junctions = LinkingService().vincular_nf_a_operacoes_orfas(nf)

        assert junctions == 1
        # Junction criada
        from app.carvia.models import CarviaOperacaoNf
        j = CarviaOperacaoNf.query.filter_by(
            operacao_id=op.id, nf_id=nf.id
        ).first()
        assert j is not None

    def test_match_por_numero_nf_normalizado(self, db):
        """NF com numero '12345' encontra operacao que referencia '12345'
        sem dependencia de cast(String) + LIKE."""
        from app.carvia.services.documentos.linking_service import LinkingService

        op = _criar_op(db, nfs_ref=[{
            'chave': _gerar_chave_44(),  # chave diferente (forca match por numero)
            'numero_nf': '12345',
            'cnpj_emitente': '12345678000100',
        }])
        nf = _criar_nf(db, numero_nf='12345')
        db.session.flush()

        junctions = LinkingService().vincular_nf_a_operacoes_orfas(nf)
        assert junctions == 1

    def test_sem_match_nao_cria_junction(self, db):
        """NF que nao esta referenciada em nenhuma op nao cria junction."""
        from app.carvia.services.documentos.linking_service import LinkingService

        _criar_op(db, nfs_ref=[{
            'chave': _gerar_chave_44(),
            'numero_nf': '99999',
            'cnpj_emitente': '12345678000100',
        }])
        nf = _criar_nf(db, numero_nf='77777')  # nao referenciada
        db.session.flush()

        junctions = LinkingService().vincular_nf_a_operacoes_orfas(nf)
        assert junctions == 0

    def test_idempotencia(self, db):
        """Chamar 2x nao cria junction duplicada (UNIQUE protege)."""
        from app.carvia.services.documentos.linking_service import LinkingService
        from app.carvia.models import CarviaOperacaoNf

        chave_nf = _gerar_chave_44()
        op = _criar_op(db, nfs_ref=[{
            'chave': chave_nf,
            'numero_nf': '12345',
            'cnpj_emitente': '12345678000100',
        }])
        nf = _criar_nf(db, numero_nf='12345', chave=chave_nf)
        db.session.flush()

        linker = LinkingService()
        j1 = linker.vincular_nf_a_operacoes_orfas(nf)
        j2 = linker.vincular_nf_a_operacoes_orfas(nf)

        assert j1 == 1
        assert j2 == 0  # ja existia
        # Total permanece 1
        total = CarviaOperacaoNf.query.filter_by(
            operacao_id=op.id, nf_id=nf.id
        ).count()
        assert total == 1
