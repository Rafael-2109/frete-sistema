"""Testes de Pos-Venda -> listagem com contagem BATCHED de pendencias abertas
(fast-follow pos-review Spec 2: kill do N+1 em `pos_venda_lista`).

Cobertura:
1. `contar_pendencias_abertas_por_chassis` (service, direto): 2 chassis vendidos,
   1 com pendencia aberta -> dict {chassi: count} correto (determinístico).
2. GET /motos-assai/pos-venda com login_admin -> 200 (smoke da rota, que agora
   usa a versao batched em vez de N chamadas por linha).
"""
import uuid

import pytest

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiNfQpa, AssaiNfQpaItem, NF_STATUS_BATEU,
    PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_ORIGEM_GALPAO,
)
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.services import pos_venda_service
from app.motos_assai.services.pendencia_service import abrir_pendencia


@pytest.fixture
def dois_chassis_vendidos(app, admin_user):
    """2 AssaiMoto + AssaiNfQpa + AssaiNfQpaItem minimos p/ passar chassi_foi_vendido.

    Retorna tupla (chassi_com_pendencia, chassi_sem_pendencia).
    """
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        assert modelo, 'Seed DOT obrigatorio em conftest'

        chassi_a = f'TSTLP{uuid.uuid4().hex[:6].upper()}'
        chassi_b = f'TSTLP{uuid.uuid4().hex[:6].upper()}'
        db.session.add(AssaiMoto(chassi=chassi_a, modelo_id=modelo.id, cor='CINZA'))
        db.session.add(AssaiMoto(chassi=chassi_b, modelo_id=modelo.id, cor='PRETA'))

        nf = AssaiNfQpa(
            chave_44=('9' * 38 + uuid.uuid4().hex[:6]).upper()[:44],
            status_match=NF_STATUS_BATEU, importada_em=agora_brasil_naive(),
            importada_por_id=admin_user.id)
        db.session.add(nf)
        db.session.flush()
        db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi=chassi_a))
        db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi=chassi_b))
        db.session.commit()
        yield chassi_a, chassi_b


def test_contar_pendencias_abertas_por_chassis_agrupa_corretamente(
    app, admin_user, dois_chassis_vendidos,
):
    chassi_com_pendencia, chassi_sem_pendencia = dois_chassis_vendidos
    with app.app_context():
        abrir_pendencia(
            chassi=chassi_com_pendencia,
            categoria=PENDENCIA_CATEGORIA_AVARIA,
            origem=PENDENCIA_ORIGEM_GALPAO,
            descricao='avaria teste fast-follow',
            operador_id=admin_user.id,
        )
        db.session.commit()

        resultado = pos_venda_service.contar_pendencias_abertas_por_chassis(
            [chassi_com_pendencia, chassi_sem_pendencia]
        )
        assert resultado.get(chassi_com_pendencia) == 1
        assert resultado.get(chassi_sem_pendencia, 0) == 0


def test_contar_pendencias_abertas_por_chassis_lista_vazia_nao_gera_query():
    assert pos_venda_service.contar_pendencias_abertas_por_chassis([]) == {}


def test_pos_venda_lista_200(login_admin, dois_chassis_vendidos):
    resp = login_admin.get('/motos-assai/pos-venda')
    assert resp.status_code == 200
