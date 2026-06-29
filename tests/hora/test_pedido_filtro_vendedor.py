"""Testes de filtro de pedidos de venda por vendedor/criador.

Cobre:
  - criar_venda_manual grava criado_por_id.
  - _query_vendas com filtro_vendedor filtra por nome ou criado_por_id.
  - _query_vendas com lojas_permitidas_ids mantem comportamento atual (regressao).

Padrão de fixtures: reusa conftest.py (loja_origem, modelo_moto, chassi_em_estoque).
Limpeza via autouse fixture por prefixo de vendedor 'VENDTEST%' e chassi '9VENDTEST%'.
"""
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture
def loja_vendtest(db):
    """Loja isolada para testes de filtro vendedor (prefixo VENDTEST)."""
    from app.utils.timezone import agora_utc_naive
    loja = HoraLoja(
        cnpj='33333333000133',
        apelido='LojaVendTest',
        nome='Loja VendTest',
        razao_social='Loja VendTest LTDA',
        nome_fantasia='Loja VendTest',
        ativa=True,
        atualizado_em=agora_utc_naive(),
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


@pytest.fixture
def modelo_vendtest(db):
    """Modelo isolado para testes de filtro vendedor."""
    m = HoraModelo(nome_modelo='VENDTEST-MODEL', ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


def _criar_moto_disponivel(chassi, modelo_nome, loja_id):
    """Cria HoraMoto + eventos RECEBIDA+CONFERIDA na loja."""
    moto = get_or_create_moto(
        numero_chassi=chassi,
        modelo_nome=modelo_nome,
        cor='PRETO',
        criado_por='fixture',
        fallback_sentinela=True,
    )
    registrar_evento(
        numero_chassi=moto.numero_chassi, tipo='RECEBIDA',
        loja_id=loja_id, operador='fixture',
    )
    registrar_evento(
        numero_chassi=moto.numero_chassi, tipo='CONFERIDA',
        loja_id=loja_id, operador='fixture',
    )
    _db.session.flush()
    return moto


@pytest.fixture(autouse=True)
def _cleanup_vendtest(db):
    """Limpa dados de teste antes de cada execucao.

    Limpa por prefixo de vendedor 'VENDTEST%', chassi '9VENDTEST%'
    e loja 'LojaVendTest' / modelo 'VENDTEST-MODEL'.
    """
    _db.session.execute(_db.text("""
        DELETE FROM hora_venda_auditoria
            WHERE venda_id IN (
                SELECT id FROM hora_venda WHERE vendedor LIKE 'VENDTEST%'
            );
        DELETE FROM hora_venda_divergencia
            WHERE venda_id IN (
                SELECT id FROM hora_venda WHERE vendedor LIKE 'VENDTEST%'
            );
        DELETE FROM hora_venda_item
            WHERE venda_id IN (
                SELECT id FROM hora_venda WHERE vendedor LIKE 'VENDTEST%'
            );
        DELETE FROM hora_venda WHERE vendedor LIKE 'VENDTEST%';
        DELETE FROM hora_moto_evento WHERE numero_chassi LIKE '9VENDTEST%';
        DELETE FROM hora_moto WHERE numero_chassi LIKE '9VENDTEST%';
        DELETE FROM hora_loja WHERE apelido = 'LojaVendTest';
        DELETE FROM hora_modelo WHERE nome_modelo = 'VENDTEST-MODEL';
    """))
    _db.session.commit()
    yield
    _db.session.rollback()


def _criar_pedido_vendtest(chassi, vendedor, criado_por_id, loja_id):
    """Helper para criar pedido de venda com vendedor e criado_por_id."""
    return venda_service.criar_venda_manual(
        cpf_cliente='52998224725',
        nome_cliente='Cliente VendTest',
        cep=None,
        endereco_logradouro=None,
        endereco_numero=None,
        endereco_complemento=None,
        endereco_bairro=None,
        endereco_cidade=None,
        endereco_uf=None,
        numero_chassi=chassi,
        valor_final=Decimal('5000.00'),
        vendedor=vendedor,
        criado_por=vendedor,
        loja_id_override=loja_id,
        criado_por_id=criado_por_id,
    )


# ---------------------------------------------------------------------------
# Task 4: criar_venda_manual grava criado_por_id
# ---------------------------------------------------------------------------

def test_criar_venda_manual_grava_criado_por_id(db, loja_vendtest, modelo_vendtest):
    """criar_venda_manual deve gravar criado_por_id quando passado."""
    chassi = '9VENDTEST0001CRIADOR000000'
    _criar_moto_disponivel(chassi, modelo_vendtest.nome_modelo, loja_vendtest.id)

    venda = venda_service.criar_venda_manual(
        cpf_cliente='52998224725',
        nome_cliente='Cliente VendTest',
        cep=None,
        endereco_logradouro=None,
        endereco_numero=None,
        endereco_complemento=None,
        endereco_bairro=None,
        endereco_cidade=None,
        endereco_uf=None,
        numero_chassi=chassi,
        valor_final=Decimal('1000.00'),
        vendedor='VENDTEST Joao',
        criado_por='VENDTEST Joao',
        loja_id_override=loja_vendtest.id,
        criado_por_id=910001,
    )
    assert venda.criado_por_id == 910001


def test_criar_venda_manual_criado_por_id_none_quando_omitido(db, loja_vendtest, modelo_vendtest):
    """criar_venda_manual deve aceitar ausencia de criado_por_id (retrocompat)."""
    chassi = '9VENDTEST0002SEMSID000000'
    _criar_moto_disponivel(chassi, modelo_vendtest.nome_modelo, loja_vendtest.id)

    venda = venda_service.criar_venda_manual(
        cpf_cliente='52998224725',
        nome_cliente='Cliente VendTest',
        cep=None,
        endereco_logradouro=None,
        endereco_numero=None,
        endereco_complemento=None,
        endereco_bairro=None,
        endereco_cidade=None,
        endereco_uf=None,
        numero_chassi=chassi,
        valor_final=Decimal('1000.00'),
        vendedor='VENDTEST Joao',
        criado_por='VENDTEST Joao',
        loja_id_override=loja_vendtest.id,
        # criado_por_id nao passado — deve ficar NULL
    )
    assert venda.criado_por_id is None


# ---------------------------------------------------------------------------
# Task 5: filtro_vendedor em _query_vendas / paginar_vendas
# ---------------------------------------------------------------------------

def test_query_vendas_filtro_vendedor_por_nome_ou_criador(db, loja_vendtest, modelo_vendtest):
    """_query_vendas com filtro_vendedor filtra por nome de vendedor OU criado_por_id."""
    loja_id = loja_vendtest.id

    # Pedido A: vendedor 'VENDTEST Joao' (casa por nome)
    chassi_a = '9VENDTESTA001FILTRO000000'
    _criar_moto_disponivel(chassi_a, modelo_vendtest.nome_modelo, loja_id)
    venda_a = _criar_pedido_vendtest(chassi_a, 'VENDTEST Joao', criado_por_id=None, loja_id=loja_id)

    # Pedido B: vendedor 'VENDTEST Outro', criado_por_id=910002 (casa por criado_por_id)
    chassi_b = '9VENDTESTB002FILTRO000000'
    _criar_moto_disponivel(chassi_b, modelo_vendtest.nome_modelo, loja_id)
    venda_b = _criar_pedido_vendtest(chassi_b, 'VENDTEST Outro', criado_por_id=910002, loja_id=loja_id)

    # Pedido C: vendedor 'VENDTEST Maria', criado_por_id=None — nao deve aparecer
    chassi_c = '9VENDTESTC003FILTRO000000'
    _criar_moto_disponivel(chassi_c, modelo_vendtest.nome_modelo, loja_id)
    venda_c = _criar_pedido_vendtest(chassi_c, 'VENDTEST Maria', criado_por_id=None, loja_id=loja_id)

    q = venda_service._query_vendas(
        filtro_vendedor={'nomes': ['VENDTEST Joao'], 'user_id': 910002},
    )
    assert q is not None
    ids = {v.id for v in q.all()}
    assert venda_a.id in ids       # casa por nome
    assert venda_b.id in ids       # casa por criado_por_id
    assert venda_c.id not in ids   # nao casa nenhum


def test_query_vendas_filtro_vendedor_sem_criterio_retorna_none(db):
    """_query_vendas com filtro_vendedor vazio (nomes=[] e user_id=None) retorna None."""
    q = venda_service._query_vendas(
        filtro_vendedor={'nomes': [], 'user_id': None},
    )
    assert q is None


def test_query_vendas_filtro_loja_inalterado(db, loja_vendtest, modelo_vendtest):
    """Regressao: _query_vendas com lojas_permitidas_ids mantem comportamento atual."""
    loja_id = loja_vendtest.id

    chassi = '9VENDTESTD004LOJA0000000'
    _criar_moto_disponivel(chassi, modelo_vendtest.nome_modelo, loja_id)
    _criar_pedido_vendtest(chassi, 'VENDTEST Joao', criado_por_id=None, loja_id=loja_id)

    q = venda_service._query_vendas(lojas_permitidas_ids=[loja_id])
    assert q is not None
    ids = {v.id for v in q.all()}
    # Pedido da loja aparece
    assert len(ids) >= 1

    # Loja inexistente -> None (lista vazia)
    q2 = venda_service._query_vendas(lojas_permitidas_ids=[])
    assert q2 is None


# ---------------------------------------------------------------------------
# Multi-status: _query_vendas aceita lista de status (filtro IN) e string (compat)
# ---------------------------------------------------------------------------

def test_query_vendas_multi_status(db, loja_vendtest, modelo_vendtest):
    """_query_vendas com `status` lista filtra via IN; string mantem compat;
    lista vazia nao filtra status."""
    loja_id = loja_vendtest.id

    chassi_a = '9VENDTESTS01STATUS0000000'
    _criar_moto_disponivel(chassi_a, modelo_vendtest.nome_modelo, loja_id)
    va = _criar_pedido_vendtest(chassi_a, 'VENDTEST Joao', criado_por_id=None, loja_id=loja_id)

    chassi_b = '9VENDTESTS02STATUS0000000'
    _criar_moto_disponivel(chassi_b, modelo_vendtest.nome_modelo, loja_id)
    vb = _criar_pedido_vendtest(chassi_b, 'VENDTEST Joao', criado_por_id=None, loja_id=loja_id)

    chassi_c = '9VENDTESTS03STATUS0000000'
    _criar_moto_disponivel(chassi_c, modelo_vendtest.nome_modelo, loja_id)
    vc = _criar_pedido_vendtest(chassi_c, 'VENDTEST Joao', criado_por_id=None, loja_id=loja_id)

    # Seta status direto (testamos o filtro da query, nao a maquina de estado).
    va.status = 'COTACAO'
    vb.status = 'FATURADO'
    vc.status = 'CANCELADO'
    _db.session.commit()

    # Lista de 2 status -> filtro IN (A e B sim, C nao).
    q = venda_service._query_vendas(
        lojas_permitidas_ids=[loja_id], status=['COTACAO', 'FATURADO'],
    )
    ids = {v.id for v in q.all()}
    assert va.id in ids
    assert vb.id in ids
    assert vc.id not in ids

    # String unica (retrocompat) -> filtro ==.
    q2 = venda_service._query_vendas(lojas_permitidas_ids=[loja_id], status='CANCELADO')
    ids2 = {v.id for v in q2.all()}
    assert vc.id in ids2
    assert va.id not in ids2
    assert vb.id not in ids2

    # Lista vazia -> nao filtra status (os 3 aparecem no escopo da loja).
    q3 = venda_service._query_vendas(lojas_permitidas_ids=[loja_id], status=[])
    ids3 = {v.id for v in q3.all()}
    assert {va.id, vb.id, vc.id} <= ids3
