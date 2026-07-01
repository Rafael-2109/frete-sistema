"""Testes de Pos-Venda -> Gerar pendencia + acompanhar (Spec 2 Task 13).

Cobertura:
1. Gerar pendencia SEM retorno fisico: origem POS_VENDA_LOJA, ficha nao trava
   a moto (evento_pendente_id None), aparece em pendencias_da_ocorrencia.
2. Gerar pendencia COM retorno fisico: ficha trava a moto (evento_pendente_id
   preenchido) e a moto emite evento PENDENTE.
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiNfQpa, AssaiNfQpaItem, NF_STATUS_BATEU,
    PENDENCIA_ORIGEM_POS_VENDA_LOJA, PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
    EVENTO_PENDENTE,
)
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.services import pos_venda_service
from app.motos_assai.services.moto_evento_service import status_efetivo


@pytest.fixture
def chassi_vendido(app, admin_user):
    """AssaiMoto + AssaiNfQpa + AssaiNfQpaItem minimos p/ passar chassi_foi_vendido
    (que so checa presenca em assai_nf_qpa_item). Retorna o chassi (str)."""
    with app.app_context():
        chassi = f'TSTPV{uuid.uuid4().hex[:6].upper()}'
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        assert modelo, 'Seed DOT obrigatorio em conftest'
        db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
        nf = AssaiNfQpa(
            chave_44=('9' * 38 + uuid.uuid4().hex[:6]).upper()[:44],
            status_match=NF_STATUS_BATEU, importada_em=agora_brasil_naive(),
            importada_por_id=admin_user.id)
        db.session.add(nf)
        db.session.flush()
        db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi=chassi))
        db.session.commit()
        yield chassi


def test_gerar_pendencia_sem_retorno_nao_trava(app, admin_user, chassi_vendido):
    with app.app_context():
        oc = pos_venda_service.criar_ocorrencia(
            chassi=chassi_vendido, categoria='LOJA', descricao='barulho',
            operador_id=admin_user.id)
        db.session.commit()

        f = pos_venda_service.gerar_pendencia_de_ocorrencia(
            ocorrencia_id=oc.id, categoria='AVARIA', retorno_fisico=False,
            operador_id=admin_user.id)
        db.session.commit()

        assert f.origem == PENDENCIA_ORIGEM_POS_VENDA_LOJA
        assert f.evento_pendente_id is None  # nao-fisica
        assert pos_venda_service.pendencias_da_ocorrencia(oc.id)[0].id == f.id
        assert pos_venda_service.contar_pendencias_abertas_por_chassi(chassi_vendido) == 1


def test_gerar_pendencia_com_retorno_fisico_trava_moto(app, admin_user, chassi_vendido):
    with app.app_context():
        oc = pos_venda_service.criar_ocorrencia(
            chassi=chassi_vendido, categoria='CLIENTE', descricao='cliente reclamou',
            operador_id=admin_user.id)
        db.session.commit()

        f = pos_venda_service.gerar_pendencia_de_ocorrencia(
            ocorrencia_id=oc.id, categoria='REVISAO', retorno_fisico=True,
            operador_id=admin_user.id)
        db.session.commit()

        assert f.origem == PENDENCIA_ORIGEM_POS_VENDA_CLIENTE
        assert f.evento_pendente_id is not None  # fisica: emite/reusa PENDENTE
        assert status_efetivo(chassi_vendido) == EVENTO_PENDENTE
