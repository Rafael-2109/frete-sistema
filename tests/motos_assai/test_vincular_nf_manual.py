"""Testes vincular_nf_manualmente (Plano 4 Task 6).

Reusa logica de ajustar_separacao_pela_nf v2 com pedido_id+loja_id explicitos.
Usado para NFs NAO_RECONCILIADO que nao foram cobertas por backfill.
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiPedidoVendaItem,
    AssaiLoja, AssaiModelo, AssaiMoto,
    AssaiNfQpa, AssaiNfQpaItem,
    PEDIDO_STATUS_ABERTO,
    NF_STATUS_NAO_RECONCILIADO, NF_STATUS_BATEU,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import emitir_evento
from app.motos_assai.services.parsers.nf_qpa_adapter import (
    vincular_nf_manualmente, VincularNfError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def test_vincular_nf_nao_reconciliado_cria_sep_em_faturada(app, admin_user):
    """NF NAO_RECONCILIADO + pedido + loja explicita -> sep criada via S1=b."""
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        loja = AssaiLoja.query.first()

        uid = _uid()
        pedido = AssaiPedidoVenda(numero=f'TST-V1-{uid}', status=PEDIDO_STATUS_ABERTO,
                                  criado_por_id=admin_user.id)
        db.session.add(pedido); db.session.flush()
        pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
        db.session.add(pvl); db.session.flush()
        # Item do pedido para que sep alvo possa receber chassis
        db.session.add(AssaiPedidoVendaItem(
            pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id,
            modelo_id=modelo.id, qtd_pedida=2,
            valor_unitario=1000.0, valor_total=2000.0,
        ))

        # 2 chassis cadastrados em assai_moto (DISPONIVEL)
        chassis = [f'TST_V1A_{_uid()}', f'TST_V1B_{_uid()}']
        for ch in chassis:
            moto = AssaiMoto(chassi=ch, modelo_id=modelo.id, cor='CINZA')
            db.session.add(moto); db.session.flush()
            for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL]:
                emitir_evento(ch, ev, admin_user.id)

        # NF NAO_RECONCILIADO sem loja_id (regex automatico nao detectou)
        chave = (str(uuid.uuid4().int)[:44]).ljust(44, '0')
        nf = AssaiNfQpa(
            chave_44=chave[:44], numero=f'TSTV1-{uid}',
            destinatario_nome='SENDAS LJ-DESCONHECIDA',
            loja_id=None,
            status_match=NF_STATUS_NAO_RECONCILIADO,
            importada_por_id=admin_user.id,
        )
        db.session.add(nf); db.session.flush()
        for ch in chassis:
            db.session.add(AssaiNfQpaItem(
                nf_id=nf.id, chassi=ch, modelo_extraido='DOT', valor_extraido=1000.0,
            ))
        db.session.commit()

        # Vincular manualmente
        result = vincular_nf_manualmente(
            nf_id=nf.id, pedido_id=pedido.id, loja_id=loja.id,
            operador_id=admin_user.id,
        )
        db.session.commit()

        assert result.get('ok') is True
        assert result.get('sep_alvo_id') is not None

        # NF.loja_id foi setado (era None antes)
        nf_ref = AssaiNfQpa.query.get(nf.id)
        assert nf_ref.loja_id == loja.id
        db.session.rollback()


def test_vincular_nf_ja_bateu_falha(app, admin_user):
    """NF ja BATEU nao pode ser revinculada — precisa cancelar antes."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        pedido = AssaiPedidoVenda(numero=f'TST-V2-{_uid()}',
                                  status=PEDIDO_STATUS_ABERTO,
                                  criado_por_id=admin_user.id)
        db.session.add(pedido); db.session.flush()

        chave = (str(uuid.uuid4().int)[:44]).ljust(44, '0')
        nf = AssaiNfQpa(
            chave_44=chave[:44], numero=f'TSTV2',
            loja_id=loja.id,
            status_match=NF_STATUS_BATEU,
            importada_por_id=admin_user.id,
        )
        db.session.add(nf)
        db.session.commit()

        with pytest.raises(VincularNfError, match='NAO_RECONCILIADO'):
            vincular_nf_manualmente(
                nf_id=nf.id, pedido_id=pedido.id, loja_id=loja.id,
                operador_id=admin_user.id,
            )
        db.session.rollback()


def test_vincular_nf_pedido_inexistente_falha(app, admin_user):
    """Pedido inexistente -> VincularNfError."""
    with app.app_context():
        loja = AssaiLoja.query.first()

        chave = (str(uuid.uuid4().int)[:44]).ljust(44, '0')
        nf = AssaiNfQpa(
            chave_44=chave[:44], numero=f'TSTV3',
            loja_id=None,
            status_match=NF_STATUS_NAO_RECONCILIADO,
            importada_por_id=admin_user.id,
        )
        db.session.add(nf)
        db.session.commit()

        with pytest.raises(VincularNfError, match='Pedido'):
            vincular_nf_manualmente(
                nf_id=nf.id, pedido_id=9999999, loja_id=loja.id,
                operador_id=admin_user.id,
            )
        db.session.rollback()
