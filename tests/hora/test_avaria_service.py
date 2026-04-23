"""Tests do avaria_service: regras de negocio da avaria."""
import pytest

from app import db as _db
from app.hora.models import HoraMotoEvento
from app.hora.services import avaria_service


FOTOS_OK = [('s3://hora/avarias/test/1.jpg', 'foto frontal')]


def test_registrar_avaria_cria_header_foto_e_evento(db, chassi_em_estoque, loja_origem):
    avaria = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque,
        descricao='arranhao profundo no para-lama',
        fotos=FOTOS_OK,
        usuario='operador_x',
        loja_id=loja_origem.id,
    )
    assert avaria.id is not None
    assert avaria.status == 'ABERTA'
    assert len(avaria.fotos) == 1
    assert avaria.fotos[0].foto_s3_key == 's3://hora/avarias/test/1.jpg'
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='AVARIADA')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.origem_tabela == 'hora_avaria'
    assert ev.origem_id == avaria.id


def test_registrar_sem_foto_falha(db, chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match=r"pelo menos 1 foto"):
        avaria_service.registrar_avaria(
            numero_chassi=chassi_em_estoque, descricao='dano',
            fotos=[], usuario='x', loja_id=loja_origem.id,
        )


def test_descricao_curta_falha(db, chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match=r"descricao"):
        avaria_service.registrar_avaria(
            numero_chassi=chassi_em_estoque, descricao='.',
            fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
        )


def test_chassi_inexistente_falha(db, loja_origem):
    with pytest.raises(ValueError, match=r"chassi"):
        avaria_service.registrar_avaria(
            numero_chassi='9CHASSIINEXISTENTE000000000',
            descricao='dano',
            fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
        )


def test_multiplas_avarias_no_mesmo_chassi(db, chassi_em_estoque, loja_origem):
    a1 = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='primeira ocorrencia',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    a2 = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='segunda ocorrencia diferente',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    assert a1.id != a2.id
    abertas = avaria_service.avarias_abertas_por_chassi([chassi_em_estoque])
    assert abertas[chassi_em_estoque] == 2


def test_resolver_avaria_muda_status(db, chassi_em_estoque, loja_origem):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='dano',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    assert a.status == 'ABERTA'
    avaria_service.resolver_avaria(a.id, 'consertada na oficina', 'chefe')
    _db.session.refresh(a)
    assert a.status == 'RESOLVIDA'
    assert a.resolvido_por == 'chefe'
    assert a.resolucao_observacao == 'consertada na oficina'


def test_ignorar_avaria(db, chassi_em_estoque, loja_origem):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='dano',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    avaria_service.ignorar_avaria(a.id, 'pre-existente', 'chefe')
    _db.session.refresh(a)
    assert a.status == 'IGNORADA'


def test_resolver_ja_finalizada_falha(db, chassi_em_estoque, loja_origem):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='dano',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    avaria_service.resolver_avaria(a.id, 'consertada', 'c1')
    with pytest.raises(ValueError, match=r"re-finalizar"):
        avaria_service.resolver_avaria(a.id, 'tentativa 2', 'c2')


def test_adicionar_foto_depois(db, chassi_em_estoque, loja_origem):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='dano',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    foto = avaria_service.adicionar_foto(
        a.id, 's3://hora/avarias/test/extra.jpg', 'lado direito', 'outro',
    )
    assert foto.id is not None
    _db.session.refresh(a)
    assert len(a.fotos) == 2


def test_avarias_abertas_por_chassi_vazio(db):
    assert avaria_service.avarias_abertas_por_chassi([]) == {}


def test_chassi_ja_vendido_falha(db, chassi_em_estoque, loja_origem):
    from app.hora.services.moto_service import registrar_evento
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='VENDIDA',
        loja_id=loja_origem.id, operador='teste',
    )
    _db.session.flush()
    with pytest.raises(ValueError, match=r"estoque"):
        avaria_service.registrar_avaria(
            numero_chassi=chassi_em_estoque, descricao='tentativa',
            fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
        )
