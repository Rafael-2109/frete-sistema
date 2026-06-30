"""Testes de Troca em Garantia (Motos Assai)."""
import uuid
from decimal import Decimal

import pytest

from app import db
from app.motos_assai.models import (
    AssaiModelo, AssaiLoja, AssaiMoto, AssaiPedidoVenda,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiNfQpa, AssaiNfQpaItem, AssaiNfQpaItemVinculoHistorico,
    AssaiPosVendaOcorrencia,
    EVENTO_FATURADA, EVENTO_PENDENTE, EVENTO_DISPONIVEL,
    NF_STATUS_BATEU, SEPARACAO_STATUS_FATURADA,
    TIPO_RELATO, TIPO_TROCA_GARANTIA, VINCULO_MOTIVO_TROCA_GARANTIA,
    CATEGORIA_CLIENTE,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.separacao_mirror_service import (
    mirror_assai_to_separacao, lote_id_de,
)
from app.separacao.models import Separacao


def _chave_44():
    base = '35260453780554000115550010000099' + str(uuid.uuid4().int)[-20:]
    return base[:44].ljust(44, '0')


def _cenario(admin, *, chassi_a=None, chassi_b=None, mesmo_modelo=True,
             estado_b=EVENTO_DISPONIVEL):
    """Monta cenario completo: venda Q.P.A. faturada (chassi A) + moto livre (B),
    incluindo o espelho Nacom com numero_nf. Retorna dict com handles."""
    suf = uuid.uuid4().hex[:6].upper()
    chassi_a = (chassi_a or f'LA2025TROCAA{suf}').upper()
    chassi_b = (chassi_b or f'LA2025TROCAB{suf}').upper()

    modelo = AssaiModelo(codigo=f'TRC{suf}', nome=f'Modelo {suf}', peso_kg=Decimal('50'))
    db.session.add(modelo)
    db.session.flush()
    modelo_b = modelo
    if not mesmo_modelo:
        modelo_b = AssaiModelo(codigo=f'TRD{suf}', nome=f'Outro {suf}', peso_kg=Decimal('50'))
        db.session.add(modelo_b)
        db.session.flush()

    loja = AssaiLoja(
        numero=f'9{suf[:3]}', nome='Loja Troca', razao_social='Loja Troca LTDA',
        cnpj='12345678000199', cidade='SAO PAULO', uf='SP',
    )
    db.session.add(loja)
    db.session.flush()

    moto_a = AssaiMoto(chassi=chassi_a, modelo_id=modelo.id, cor='PRETO')
    moto_b = AssaiMoto(chassi=chassi_b, modelo_id=modelo_b.id, cor='VERMELHO')
    db.session.add_all([moto_a, moto_b])
    db.session.flush()

    pedido = AssaiPedidoVenda(numero=f'VOE-{suf}')
    db.session.add(pedido)
    db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                         status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.flush()
    sep_item = AssaiSeparacaoItem(
        separacao_id=sep.id, chassi=chassi_a, modelo_id=modelo.id,
        valor_unitario_qpa=Decimal('5000.00'),
    )
    db.session.add(sep_item)
    db.session.flush()

    nf = AssaiNfQpa(
        chave_44=_chave_44(), numero='9' + suf[:4], loja_id=loja.id,
        status_match=NF_STATUS_BATEU, separacao_id=sep.id, importada_por_id=admin.id,
    )
    db.session.add(nf)
    db.session.flush()
    nf_item = AssaiNfQpaItem(
        nf_id=nf.id, chassi=chassi_a, separacao_item_id=sep_item.id,
        valor_extraido=Decimal('5000.00'),
    )
    db.session.add(nf_item)
    db.session.flush()

    emitir_evento(chassi_a, EVENTO_FATURADA, operador_id=admin.id)
    emitir_evento(chassi_b, estado_b, operador_id=admin.id)

    mirror_assai_to_separacao(sep.id)
    for ln in Separacao.query.filter_by(separacao_lote_id=lote_id_de(sep.id)).all():
        ln.numero_nf = nf.numero
    db.session.commit()

    return dict(
        modelo=modelo, modelo_b=modelo_b, loja=loja, moto_a=moto_a, moto_b=moto_b,
        pedido=pedido, sep=sep, sep_item=sep_item, nf=nf, nf_item=nf_item,
        chassi_a=chassi_a, chassi_b=chassi_b,
    )


def test_pos_venda_ocorrencia_aceita_campos_de_troca(app, admin_user):
    """A migration 34 adicionou tipo/chassi_substituto/nf_qpa_id — round-trip."""
    with app.app_context():
        c = _cenario(admin_user)
        oc = AssaiPosVendaOcorrencia(
            chassi=c['chassi_a'], categoria=CATEGORIA_CLIENTE,
            descricao='defeito X', tipo=TIPO_TROCA_GARANTIA,
            chassi_substituto=c['chassi_b'], nf_qpa_id=c['nf'].id,
            criado_por_id=admin_user.id,
        )
        db.session.add(oc)
        db.session.commit()

        lido = AssaiPosVendaOcorrencia.query.get(oc.id)
        assert lido.tipo == TIPO_TROCA_GARANTIA
        assert lido.chassi_substituto == c['chassi_b']
        assert lido.nf_qpa_id == c['nf'].id


from app.motos_assai.services.separacao_mirror_service import trocar_chassi_no_espelho


def test_trocar_chassi_no_espelho_preserva_numero_nf(app, admin_user):
    """Troca chassi_assai A->B na linha espelho, preservando numero_nf/status."""
    with app.app_context():
        c = _cenario(admin_user)
        lote = lote_id_de(c['sep'].id)

        antes = Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_a']).all()
        assert len(antes) == 1
        assert antes[0].numero_nf == c['nf'].numero

        n = trocar_chassi_no_espelho(c['sep'].id, c['chassi_a'], c['chassi_b'])
        db.session.commit()

        assert n == 1
        assert Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_a']).count() == 0
        linha_b = Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_b']).one()
        assert linha_b.numero_nf == c['nf'].numero


from app.motos_assai.services.troca_garantia_service import (
    registrar_troca, TrocaGarantiaError,
)


def test_registrar_troca_swap_completo(app, admin_user):
    """B vira FATURADA, A vira PENDENTE, NF/sep/espelho apontam para B, ocorrencia criada."""
    with app.app_context():
        c = _cenario(admin_user)

        res = registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='Motor com defeito', dry_run=False,
        )
        assert res['ok'] is True
        assert res['dry_run'] is False

        assert status_efetivo(c['chassi_b']) == EVENTO_FATURADA
        assert status_efetivo(c['chassi_a']) == EVENTO_PENDENTE

        nf_item = AssaiNfQpaItem.query.get(c['nf_item'].id)
        assert nf_item.chassi == c['chassi_b']
        assert nf_item.separacao_item_id == c['sep_item'].id

        sep_item = AssaiSeparacaoItem.query.get(c['sep_item'].id)
        assert sep_item.chassi == c['chassi_b']

        lote = lote_id_de(c['sep'].id)
        linha_b = Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_b']).one()
        assert linha_b.numero_nf == c['nf'].numero

        hist = AssaiNfQpaItemVinculoHistorico.query.filter_by(
            nf_qpa_item_id=c['nf_item'].id, motivo=VINCULO_MOTIVO_TROCA_GARANTIA,
        ).one()
        assert hist.chassi_no_momento == c['chassi_a']

        oc = AssaiPosVendaOcorrencia.query.get(res['ocorrencia_id'])
        assert oc.tipo == TIPO_TROCA_GARANTIA
        assert oc.chassi == c['chassi_a']
        assert oc.chassi_substituto == c['chassi_b']
        assert oc.nf_qpa_id == c['nf'].id
        assert oc.descricao == 'Motor com defeito'

        assert AssaiNfQpa.query.get(c['nf'].id).status_match == NF_STATUS_BATEU
        assert nf_item.devolvido is False


def test_registrar_troca_dry_run_nao_escreve(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        res = registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='Motor com defeito',
        )
        assert res['ok'] is True
        assert res['dry_run'] is True
        assert res['ocorrencia_id'] is None
        assert isinstance(res['plano'], list) and res['plano']

        assert status_efetivo(c['chassi_a']) == EVENTO_FATURADA
        assert status_efetivo(c['chassi_b']) == EVENTO_DISPONIVEL
        assert AssaiNfQpaItem.query.get(c['nf_item'].id).chassi == c['chassi_a']
        assert AssaiPosVendaOcorrencia.query.filter_by(nf_qpa_id=c['nf'].id).count() == 0


def test_registrar_troca_rejeita_a_nao_faturada(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        emitir_evento(c['chassi_a'], EVENTO_PENDENTE, operador_id=admin_user.id)
        db.session.commit()
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )


def test_registrar_troca_rejeita_b_nao_disponivel(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user, estado_b=EVENTO_FATURADA)
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )


def test_registrar_troca_rejeita_modelo_diferente(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user, mesmo_modelo=False)
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )


def test_registrar_troca_idempotente(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='x', dry_run=False,
        )
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )
