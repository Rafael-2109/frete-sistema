"""Regra (2026-06-28): moto com avaria ABERTA fica NAO-VENDAVEL — bloqueia a
reserva (_lock_chassi_e_validar_disponivel) e a confirmacao; volta ao vendavel
quando a ULTIMA avaria aberta e resolvida ou ignorada.

Fonte de verdade da vendabilidade: avaria_service.avarias_abertas_por_chassi
(HoraAvaria status='ABERTA') — NAO o tipo do ultimo evento (AVARIADA segue em
EVENTOS_EM_ESTOQUE para a moto continuar aparecendo no estoque).
"""
import pytest

from app import db as _db
from app.hora.services import avaria_service, venda_service
from app.hora.services.venda_service import ChassiIndisponivelError


def _avaria(chassi, loja, desc='dano que bloqueia a venda'):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi, descricao=desc, fotos=[], usuario='x', loja_id=loja.id)
    _db.session.flush()
    return a


def _moto_em_estoque(loja, modelo, cor='PRETA'):
    """Cria uma moto NOVA (chassi único) em estoque no modelo informado.
    Chassi único evita o insert-once do fixture chassi_em_estoque (que reusa um
    chassi fixo e pode ter modelo_id de resíduo) e isola a contagem por modelo."""
    import uuid
    from app.hora.services.moto_service import get_or_create_moto, registrar_evento
    chassi = f'9OFFER{uuid.uuid4().hex[:18].upper()}'[:25]
    get_or_create_moto(numero_chassi=chassi, modelo_nome=modelo.nome_modelo,
                       cor=cor, criado_por='t')
    registrar_evento(numero_chassi=chassi, tipo='RECEBIDA', loja_id=loja.id, operador='t')
    registrar_evento(numero_chassi=chassi, tipo='CONFERIDA', loja_id=loja.id, operador='t')
    _db.session.flush()
    return chassi


def test_avaria_aberta_bloqueia_reserva(db, chassi_em_estoque, loja_origem):
    _avaria(chassi_em_estoque, loja_origem)
    with pytest.raises(ChassiIndisponivelError, match=r'(?i)avaria'):
        venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)


def test_resolver_libera_reserva(db, chassi_em_estoque, loja_origem):
    a = _avaria(chassi_em_estoque, loja_origem)
    with pytest.raises(ChassiIndisponivelError):
        venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    avaria_service.resolver_avaria(a.id, 'consertada na oficina', 'chefe')
    _db.session.flush()
    moto, _ult = venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    assert moto.numero_chassi == chassi_em_estoque


def test_ignorar_libera_reserva(db, chassi_em_estoque, loja_origem):
    a = _avaria(chassi_em_estoque, loja_origem)
    avaria_service.ignorar_avaria(a.id, 'dano pre-existente aceitavel', 'chefe')
    _db.session.flush()
    moto, _ult = venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    assert moto.numero_chassi == chassi_em_estoque


def test_multi_avaria_so_libera_quando_todas_finalizadas(db, chassi_em_estoque, loja_origem):
    a1 = _avaria(chassi_em_estoque, loja_origem, 'primeiro dano aqui')
    a2 = _avaria(chassi_em_estoque, loja_origem, 'segundo dano aqui')
    avaria_service.resolver_avaria(a1.id, 'consertou o primeiro', 'chefe')
    _db.session.flush()
    with pytest.raises(ChassiIndisponivelError):
        venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    avaria_service.resolver_avaria(a2.id, 'consertou o segundo', 'chefe')
    _db.session.flush()
    moto, _ult = venda_service._lock_chassi_e_validar_disponivel(chassi_em_estoque)
    assert moto.numero_chassi == chassi_em_estoque


# --- Offer-for-sale: as listas que oferecem moto para venda excluem a avariada ---

def test_offer_for_sale_exclui_avariada(db, loja_origem, modelo_moto):
    from app.hora.services import estoque_service, autocomplete_service
    chassi = _moto_em_estoque(loja_origem, modelo_moto, cor='PRETA')
    # ANTES da avaria: aparece em todas as listas de venda
    assert any(c['chassi'] == chassi
               for c in estoque_service.chassis_disponiveis_para_venda(modelo_moto.id))
    assert 'PRETA' in estoque_service.cores_disponiveis_por_modelo(modelo_moto.id)
    assert any(r['chassi'] == chassi
               for r in autocomplete_service.chassis(chassi[:8], disponivel=True))

    _avaria(chassi, loja_origem)

    # DEPOIS: some das listas de venda (continua no estoque com flag — Task #5)
    assert all(c['chassi'] != chassi
               for c in estoque_service.chassis_disponiveis_para_venda(modelo_moto.id))
    assert 'PRETA' not in estoque_service.cores_disponiveis_por_modelo(modelo_moto.id)
    assert all(r['chassi'] != chassi
               for r in autocomplete_service.chassis(chassi[:8], disponivel=True))


def test_resolver_avaria_devolve_para_listas_de_venda(db, loja_origem, modelo_moto):
    from app.hora.services import estoque_service
    chassi = _moto_em_estoque(loja_origem, modelo_moto, cor='PRETA')
    a = _avaria(chassi, loja_origem)
    assert all(c['chassi'] != chassi
               for c in estoque_service.chassis_disponiveis_para_venda(modelo_moto.id))
    avaria_service.resolver_avaria(a.id, 'consertada na oficina', 'chefe')
    _db.session.flush()
    assert any(c['chassi'] == chassi
               for c in estoque_service.chassis_disponiveis_para_venda(modelo_moto.id))


# --- Estoque (req 2): avariada CONTINUA no estoque, com flag não-vendável ---

def test_listar_estoque_flag_nao_vendavel(db, loja_origem, modelo_moto):
    from app.hora.services import estoque_service
    chassi = _moto_em_estoque(loja_origem, modelo_moto)

    def _row():
        return next((r for r in estoque_service.listar_estoque(
            lojas_permitidas_ids=[loja_origem.id]) if r['chassi'] == chassi), None)

    r = _row()
    assert r and r['moto_disponivel'] is True and r['moto_vendavel'] is True
    _avaria(chassi, loja_origem)
    r = _row()
    # continua NO estoque (moto_disponivel True), mas NÃO-vendável (flag)
    assert r and r['moto_disponivel'] is True and r['moto_vendavel'] is False
    assert r['avarias_abertas'] == 1


def test_filtro_incluir_avariadas_usa_contagem(db, loja_origem, modelo_moto):
    """incluir_avariadas=False ESCONDE moto com avaria ABERTA e MOSTRA moto cuja
    avaria foi resolvida (último evento ainda AVARIADA — resolver não emite
    evento). Visibilidade pela contagem HoraAvaria, não pelo tipo. #3 do review."""
    from app.hora.services import estoque_service
    chassi = _moto_em_estoque(loja_origem, modelo_moto)
    a = _avaria(chassi, loja_origem)  # último evento vira AVARIADA, count=1

    def _listar(incluir):
        return [r['chassi'] for r in estoque_service.listar_estoque(
            lojas_permitidas_ids=[loja_origem.id], incluir_avariadas=incluir)]

    assert chassi in _listar(True)
    assert chassi not in _listar(False)

    avaria_service.resolver_avaria(a.id, 'consertada na oficina', 'chefe')
    _db.session.flush()
    # resolvida: count=0 → aparece nas duas (último evento segue AVARIADA, mas não esconde)
    assert chassi in _listar(True)
    assert chassi in _listar(False)
