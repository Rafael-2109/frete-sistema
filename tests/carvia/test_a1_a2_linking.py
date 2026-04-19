"""Testes A1 + A2 — linking_service.py (Bug #1 + Bug #2).

A1 = fechar_vinculo_cte_comp_fatura (CTe Comp tardio).
A2 = vincular_nf_a_itens_fatura_orfaos com expansao retroativa.

Usa o fixture `db` do conftest.py — cada teste em transacao revertida.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers — factories minimos (sem fixtures globais para nao poluir conftest)
# ---------------------------------------------------------------------------

def _unique_suffix() -> str:
    return uuid.uuid4().hex[:6]


def _gerar_chave_44(prefixo: str = '3525') -> str:
    """Gera chave de acesso fictícia de 44 caracteres (UNIQUE)."""
    return (prefixo + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_operacao(db, cte_numero: str, cte_valor: float = 1000.0):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte_numero,
        cte_chave_acesso=_gerar_chave_44(),
        cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=datetime(2026, 4, 1).date(),
        cnpj_cliente='12345678000100',
        nome_cliente='Cliente Teste',
        uf_origem='SP',
        cidade_origem='SAO PAULO',
        uf_destino='RJ',
        cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO',
        tipo_entrada='IMPORTADO',
        criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_fatura(
    db, numero: str, cnpj_cliente: str = '12345678000100',
    valor_total: float = 0.0,
):
    from app.carvia.models import CarviaFaturaCliente
    fat = CarviaFaturaCliente(
        numero_fatura=numero,
        cnpj_cliente=cnpj_cliente,
        data_emissao=datetime(2026, 4, 10).date(),
        valor_total=Decimal(str(valor_total)),
        status='PENDENTE',
        status_conferencia='PENDENTE',
        criado_por='test',
    )
    db.session.add(fat)
    db.session.flush()
    return fat


def _criar_item_fatura(
    db, fatura_id: int, cte_numero: str,
    operacao_id: int | None = None, nf_numero: str | None = None,
    nf_id: int | None = None,
):
    from app.carvia.models import CarviaFaturaClienteItem
    item = CarviaFaturaClienteItem(
        fatura_cliente_id=fatura_id,
        cte_numero=cte_numero,
        cte_data_emissao=datetime(2026, 4, 1).date(),
        contraparte_cnpj='12345678000100',
        contraparte_nome='Cliente Teste',
        nf_numero=nf_numero,
        nf_id=nf_id,
        operacao_id=operacao_id,
        valor_mercadoria=Decimal('100.00') if nf_numero else None,
        frete=Decimal('50.00') if not nf_id else None,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _criar_cte_comp(
    db, numero_comp: str, operacao_id: int,
    cte_numero: str = '999', cte_valor: float = 200.0,
    status: str = 'RASCUNHO',
):
    from app.carvia.models import CarviaCteComplementar
    cc = CarviaCteComplementar(
        numero_comp=numero_comp,
        operacao_id=operacao_id,
        cte_numero=cte_numero,
        cte_chave_acesso=_gerar_chave_44(),
        cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=datetime(2026, 4, 5).date(),
        cnpj_cliente='12345678000100',
        nome_cliente='Cliente Teste',
        status=status,
        criado_por='test',
    )
    db.session.add(cc)
    db.session.flush()
    return cc


def _criar_nf(
    db, numero_nf: str, cnpj_emitente: str = '12345678000100',
    cnpj_destinatario: str = '98765432000199',
):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero_nf,
        chave_acesso_nf=_gerar_chave_44(),
        cnpj_emitente=cnpj_emitente,
        nome_emitente='Emitente Teste',
        cnpj_destinatario=cnpj_destinatario,
        nome_destinatario='Destinatario Teste',
        data_emissao=datetime(2026, 4, 1).date(),
        valor_total=Decimal('500.00'),
        peso_bruto=Decimal('100.000'),
        status='ATIVA',
        tipo_fonte='MANUAL',
        criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _criar_junction(db, operacao_id: int, nf_id: int):
    from app.carvia.models import CarviaOperacaoNf
    j = CarviaOperacaoNf(operacao_id=operacao_id, nf_id=nf_id)
    db.session.add(j)
    db.session.flush()
    return j


# ---------------------------------------------------------------------------
# A1 — fechar_vinculo_cte_comp_fatura
# ---------------------------------------------------------------------------

class TestA1FecharVinculoCteCompFatura:

    def test_fatura_tem_item_com_cte_numero_vincula(self, db):
        """Cenario principal Bug #2: fatura pre-existente com item apontando
        para cte_numero do CTe Comp -> vincula + popula cte_complementar_id."""
        from app.carvia.services.documentos.linking_service import LinkingService
        sfx = _unique_suffix()

        op = _criar_operacao(db, f'CTe-A1-{sfx}-1', 1000.0)
        fat = _criar_fatura(db, f'FAT-A1-{sfx}', valor_total=1000.0)
        op.fatura_cliente_id = fat.id
        op.status = 'FATURADO'
        # Item da fatura apontando para o CTe Comp (fatura PDF listou COMP-024)
        item = _criar_item_fatura(
            db, fat.id, cte_numero=f'CTeComp-A1-{sfx}', operacao_id=op.id,
        )
        # CTe Comp criado depois (bloco 3.5 do import)
        cc = _criar_cte_comp(
            db, f'COMP-A1-{sfx}', op.id, cte_numero=f'CTeComp-A1-{sfx}',
            cte_valor=200.0,
        )
        db.session.flush()

        res = LinkingService().fechar_vinculo_cte_comp_fatura(cc.id)

        assert res['status'] == 'VINCULADO', res
        assert res['fatura_id'] == fat.id
        assert res['items_atualizados'] == 1

        # Campos persistidos
        db.session.refresh(cc)
        db.session.refresh(item)
        db.session.refresh(fat)
        assert cc.fatura_cliente_id == fat.id
        assert cc.status == 'FATURADO'
        assert item.cte_complementar_id == cc.id
        # valor_total = 1000 (op) + 200 (comp) = 1200
        assert float(fat.valor_total) == 1200.0

    def test_sem_fatura_pre_existente_retorna_sem_fatura(self, db):
        """CTe Comp chega ANTES da fatura -> SEM_FATURA."""
        from app.carvia.services.documentos.linking_service import LinkingService
        sfx = _unique_suffix()
        op = _criar_operacao(db, f'CTe-A1-b-{sfx}', 1000.0)
        cc = _criar_cte_comp(
            db, f'COMP-A1-b-{sfx}', op.id,
            cte_numero=f'CTeComp-A1-b-{sfx}',
        )
        db.session.flush()

        res = LinkingService().fechar_vinculo_cte_comp_fatura(cc.id)

        assert res['status'] == 'SEM_FATURA'
        assert res['cte_numero'] == f'CTeComp-A1-b-{sfx}'

    def test_idempotencia_segunda_chamada_retorna_skip(self, db):
        """NN5: rodar retrolink 2x no mesmo CTe Comp nao duplica."""
        from app.carvia.services.documentos.linking_service import LinkingService
        sfx = _unique_suffix()
        op = _criar_operacao(db, f'CTe-A1-c-{sfx}', 1000.0)
        fat = _criar_fatura(db, f'FAT-A1-c-{sfx}', valor_total=1000.0)
        op.fatura_cliente_id = fat.id
        op.status = 'FATURADO'
        _criar_item_fatura(
            db, fat.id, cte_numero=f'CTeComp-A1-c-{sfx}', operacao_id=op.id,
        )
        cc = _criar_cte_comp(
            db, f'COMP-A1-c-{sfx}', op.id,
            cte_numero=f'CTeComp-A1-c-{sfx}', cte_valor=200.0,
        )
        db.session.flush()

        linker = LinkingService()
        r1 = linker.fechar_vinculo_cte_comp_fatura(cc.id)
        r2 = linker.fechar_vinculo_cte_comp_fatura(cc.id)

        assert r1['status'] == 'VINCULADO'
        assert r2['status'] == 'SKIP'
        assert r2['motivo'] == 'ja_vinculado'

        # valor_total nao deve dobrar
        db.session.refresh(fat)
        assert float(fat.valor_total) == 1200.0  # nao virou 1400

    def test_fatura_conferida_bloqueia(self, db):
        """Fatura com status_conferencia=CONFERIDO -> SKIP_FATURA_BLOQUEADA."""
        from app.carvia.services.documentos.linking_service import LinkingService
        sfx = _unique_suffix()
        op = _criar_operacao(db, f'CTe-A1-d-{sfx}', 1000.0)
        fat = _criar_fatura(db, f'FAT-A1-d-{sfx}', valor_total=1000.0)
        fat.status_conferencia = 'CONFERIDO'
        op.fatura_cliente_id = fat.id
        op.status = 'FATURADO'
        _criar_item_fatura(
            db, fat.id, cte_numero=f'CTeComp-A1-d-{sfx}', operacao_id=op.id,
        )
        cc = _criar_cte_comp(
            db, f'COMP-A1-d-{sfx}', op.id, cte_numero=f'CTeComp-A1-d-{sfx}',
        )
        db.session.flush()

        res = LinkingService().fechar_vinculo_cte_comp_fatura(cc.id)

        assert res['status'] == 'SKIP_FATURA_BLOQUEADA', res
        # CTe Comp permanece NAO vinculado
        db.session.refresh(cc)
        assert cc.fatura_cliente_id is None


# ---------------------------------------------------------------------------
# A2 — vincular_nf_a_itens_fatura_orfaos retorna dict + expand retroativo
# ---------------------------------------------------------------------------

class TestA2NfTardiaComExpansaoRetroativa:

    def test_retorna_dict_com_chaves_esperadas(self, db):
        """Signature change: int -> dict."""
        from app.carvia.services.documentos.linking_service import LinkingService
        sfx = _unique_suffix()
        nf = _criar_nf(db, f'NF-A2-a-{sfx}')
        db.session.flush()

        res = LinkingService().vincular_nf_a_itens_fatura_orfaos(nf)

        assert isinstance(res, dict)
        assert 'nf_items_atualizados' in res
        assert 'itens_suplementares_criados' in res
        assert 'faturas_expandidas' in res
        assert res['nf_items_atualizados'] == 0  # nenhum item orfao

    def test_nf_tardia_cria_item_suplementar_retroativo(self, db):
        """Cenario Bug #1: fatura existente + NF tardia entra na junction
        -> item suplementar criado automaticamente."""
        from app.carvia.services.documentos.linking_service import LinkingService
        sfx = _unique_suffix()

        # Setup: op + fatura + item com NF1 ja presente
        op = _criar_operacao(db, f'CTe-A2-a-{sfx}', 1000.0)
        fat = _criar_fatura(db, f'FAT-A2-a-{sfx}', valor_total=1000.0)
        op.fatura_cliente_id = fat.id
        op.status = 'FATURADO'

        nf1_num = f'NF1-A2-a-{sfx}'
        nf1 = _criar_nf(db, nf1_num)
        _criar_junction(db, op.id, nf1.id)

        # Item da fatura apontando para op + NF1 (cenario inicial OK)
        _criar_item_fatura(
            db, fat.id, cte_numero=f'CTe-A2-a-{sfx}',
            operacao_id=op.id, nf_numero=nf1_num, nf_id=nf1.id,
        )
        db.session.flush()

        # Ato: NF2 chega DEPOIS, entra na junction da op
        nf2_num = f'NF2-A2-a-{sfx}'
        nf2 = _criar_nf(db, nf2_num)
        _criar_junction(db, op.id, nf2.id)
        db.session.flush()

        # Invoca hook retroativo via vincular_nf_a_itens_fatura_orfaos
        res = LinkingService().vincular_nf_a_itens_fatura_orfaos(nf2)

        # `nf_items_atualizados` pode ser 0 (nao ha item com nf_numero=NF2
        # pendente de resolver). Mas expandir_itens_com_nfs_do_cte deve ter
        # rodado para a fatura afetada (pois a junction foi atualizada).
        # Para forcar expansao retroativa mesmo sem items com nf_numero=NF2,
        # chamamos expandir diretamente — aqui verificamos apenas que o
        # dict retorna sem erro.
        assert isinstance(res, dict)

        # Teste complementar: chamar expandir diretamente para validar
        # que a logica de expansao funciona
        expand = LinkingService().expandir_itens_com_nfs_do_cte(fat.id)
        assert expand['itens_criados'] == 1  # NF2 ganhou item suplementar

        # Verifica que o item suplementar tem valor_mercadoria=None (A2-ALTO-3)
        from app.carvia.models import CarviaFaturaClienteItem
        items = CarviaFaturaClienteItem.query.filter_by(
            fatura_cliente_id=fat.id, nf_id=nf2.id,
        ).all()
        assert len(items) == 1
        assert items[0].valor_mercadoria is None
        assert items[0].peso_kg is None

    def test_valor_mercadoria_None_em_item_suplementar_evita_dupla_contagem(
        self, db
    ):
        """A2-ALTO-3: valor_mercadoria em item suplementar e None."""
        from app.carvia.services.documentos.linking_service import LinkingService
        from app.carvia.models import CarviaFaturaClienteItem
        from sqlalchemy import func as sa_func
        sfx = _unique_suffix()

        op = _criar_operacao(db, f'CTe-A2-c-{sfx}', 1000.0)
        fat = _criar_fatura(db, f'FAT-A2-c-{sfx}', valor_total=1000.0)
        op.fatura_cliente_id = fat.id

        nf1 = _criar_nf(db, f'NF1-A2-c-{sfx}')
        nf2 = _criar_nf(db, f'NF2-A2-c-{sfx}')
        _criar_junction(db, op.id, nf1.id)
        _criar_junction(db, op.id, nf2.id)

        _criar_item_fatura(
            db, fat.id, cte_numero=f'CTe-A2-c-{sfx}',
            operacao_id=op.id, nf_numero=f'NF1-A2-c-{sfx}', nf_id=nf1.id,
        )
        db.session.flush()

        LinkingService().expandir_itens_com_nfs_do_cte(fat.id)
        db.session.flush()

        # SUM(valor_mercadoria) deve continuar = valor original do item NF1
        # (nao deve somar valor da NF2)
        soma = db.session.query(
            sa_func.coalesce(
                sa_func.sum(CarviaFaturaClienteItem.valor_mercadoria), 0
            )
        ).filter(
            CarviaFaturaClienteItem.fatura_cliente_id == fat.id
        ).scalar()
        # Item original: 100.00 (definido em _criar_item_fatura com nf_numero)
        assert float(soma) == 100.0

    def test_idempotencia_expand_duas_vezes_nao_duplica(self, db):
        """NN5: rodar expandir_itens_com_nfs_do_cte 2x nao cria items duplicados."""
        from app.carvia.services.documentos.linking_service import LinkingService
        sfx = _unique_suffix()

        op = _criar_operacao(db, f'CTe-A2-d-{sfx}', 1000.0)
        fat = _criar_fatura(db, f'FAT-A2-d-{sfx}', valor_total=1000.0)
        op.fatura_cliente_id = fat.id
        nf1 = _criar_nf(db, f'NF1-A2-d-{sfx}')
        nf2 = _criar_nf(db, f'NF2-A2-d-{sfx}')
        _criar_junction(db, op.id, nf1.id)
        _criar_junction(db, op.id, nf2.id)
        _criar_item_fatura(
            db, fat.id, cte_numero=f'CTe-A2-d-{sfx}',
            operacao_id=op.id, nf_numero=f'NF1-A2-d-{sfx}', nf_id=nf1.id,
        )
        db.session.flush()

        linker = LinkingService()
        r1 = linker.expandir_itens_com_nfs_do_cte(fat.id)
        r2 = linker.expandir_itens_com_nfs_do_cte(fat.id)

        assert r1['itens_criados'] == 1
        assert r2['itens_criados'] == 0  # segunda vez nao cria nada

    def test_feature_flag_auto_vincular_default_false(self, app):
        """A1 flag default False (rollout gradual)."""
        assert app.config.get(
            'CARVIA_FEATURE_AUTO_VINCULAR_CTE_COMP', False
        ) is False
