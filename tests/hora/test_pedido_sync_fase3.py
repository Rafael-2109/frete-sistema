"""Fase 3 da sync HORA<->TagPlus: descoberta reversa (numero-walk +3).

Cobre:
  - pedido_service.busca_pedido_por_numero (GET /pedidos?numero=n -> 1o item/None)
  - pedido_reverso_service._varrer (algoritmo numero-walk: reset de ausencias ao
    achar, para apos 3 ausencias seguidas, anti-loop por codigo_externo)
  - pedido_reverso_service.pedido_e_nosso (anti-loop + idempotencia)
  - pedido_reverso_service.numero_walk (persiste cursor ultimo_pedido_numero_reconciliado)

Verificacao #2 confirmada ao vivo 2026-06-29: GET /pedidos?numero={n} filtra exato.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app import db as _db
import app.hora.services.tagplus.pedido_service as pedido_service
import app.hora.services.tagplus.pedido_reverso_service as rev


# --------------------------------------------------------------------------
# busca_pedido_por_numero
# --------------------------------------------------------------------------
def test_busca_pedido_por_numero_retorna_primeiro():
    api = MagicMock()
    api.get.return_value = SimpleNamespace(status_code=200, json=lambda: [{'id': 1195, 'numero': 943}])
    p = pedido_service.busca_pedido_por_numero(api, 943)
    assert p['id'] == 1195
    api.get.assert_called_once_with('/pedidos', params={'numero': 943})


def test_busca_pedido_por_numero_vazio_retorna_none():
    api = MagicMock()
    api.get.return_value = SimpleNamespace(status_code=200, json=lambda: [])
    assert pedido_service.busca_pedido_por_numero(api, 999) is None


def test_busca_pedido_por_numero_erro_http_retorna_none():
    api = MagicMock()
    api.get.return_value = SimpleNamespace(status_code=500, json=lambda: {}, text='err')
    assert pedido_service.busca_pedido_por_numero(api, 943) is None


# --------------------------------------------------------------------------
# _varrer: algoritmo numero-walk (puro, busca/anti-loop injetados via monkeypatch)
# --------------------------------------------------------------------------
def _stub_busca(monkeypatch, existentes: dict):
    """existentes: {numero: pedido_dict}. None p/ ausente."""
    monkeypatch.setattr(rev, 'busca_pedido_por_numero',
                        lambda api, n: existentes.get(n))


def test_varrer_para_apos_3_ausencias(monkeypatch):
    # base=940; 941,942 existem; 943,944,945 ausentes -> para em 945.
    _stub_busca(monkeypatch, {941: {'numero': 941, 'codigo_externo': ''},
                              942: {'numero': 942, 'codigo_externo': ''}})
    monkeypatch.setattr(rev, 'pedido_e_nosso', lambda p: False)
    descobertos, maior = rev._varrer(MagicMock(), base=940)
    assert [d['numero'] for d in descobertos] == [941, 942]
    assert maior == 942


def test_varrer_reset_ausencias_estende_janela(monkeypatch):
    # base=940; gap em 941,942 (2 ausencias), 943 existe (reset), depois 944-946 ausentes.
    _stub_busca(monkeypatch, {943: {'numero': 943, 'codigo_externo': ''}})
    monkeypatch.setattr(rev, 'pedido_e_nosso', lambda p: False)
    descobertos, maior = rev._varrer(MagicMock(), base=940)
    assert [d['numero'] for d in descobertos] == [943]
    assert maior == 943


def test_varrer_ignora_pedidos_nossos_anti_loop(monkeypatch):
    # 941 e 942 existem, mas 941 e "nosso" (codigo_externo resolve venda) -> so 942.
    _stub_busca(monkeypatch, {941: {'numero': 941, 'codigo_externo': '500'},
                              942: {'numero': 942, 'codigo_externo': ''}})
    monkeypatch.setattr(rev, 'pedido_e_nosso', lambda p: p.get('codigo_externo') == '500')
    descobertos, maior = rev._varrer(MagicMock(), base=940)
    assert [d['numero'] for d in descobertos] == [942]
    assert maior == 942  # 941 conta como existente (reseta ausencia) mesmo sendo nosso


# --------------------------------------------------------------------------
# pedido_e_nosso: anti-loop (codigo_externo) + idempotencia (ja replicado)
# --------------------------------------------------------------------------
def _venda(**kw):
    from app.hora.models.venda import HoraVenda
    from decimal import Decimal
    base = dict(cpf_cliente='12345678909', nome_cliente='C', valor_total=Decimal('1'),
                status='COTACAO')
    base.update(kw)
    v = HoraVenda(**base)
    _db.session.add(v)
    _db.session.flush()
    return v


def test_pedido_e_nosso_por_codigo_externo(db):
    v = _venda()
    assert rev.pedido_e_nosso({'codigo_externo': str(v.id), 'id': 9999, 'numero': 8888}) is True


def test_pedido_e_nosso_por_tagplus_pedido_id_ja_replicado(db):
    v = _venda()
    v.tagplus_pedido_id = 1234
    _db.session.flush()
    assert rev.pedido_e_nosso({'codigo_externo': '', 'id': 1234, 'numero': 8888}) is True


def test_pedido_nao_e_nosso_quando_desconhecido(db):
    assert rev.pedido_e_nosso({'codigo_externo': '', 'id': 777777, 'numero': 666666}) is False


# --------------------------------------------------------------------------
# numero_walk: persiste o cursor
# --------------------------------------------------------------------------
def test_numero_walk_persiste_cursor(db, monkeypatch):
    from app.hora.models.tagplus import HoraTagPlusConta
    conta = HoraTagPlusConta(client_id='c', client_secret_encrypted='x', webhook_secret='s')
    _db.session.add(conta)
    _db.session.flush()
    monkeypatch.setattr(rev, '_maior_numero_conhecido', lambda: 940)
    _stub_busca(monkeypatch, {941: {'numero': 941, 'codigo_externo': ''}})
    monkeypatch.setattr(rev, 'pedido_e_nosso', lambda p: False)
    descobertos = rev.numero_walk(MagicMock(), conta)
    assert [d['numero'] for d in descobertos] == [941]
    assert conta.ultimo_pedido_numero_reconciliado == 941


# --------------------------------------------------------------------------
# replicar: pedido TagPlus -> HoraVenda INCOMPLETO (origem TAGPLUS)
# --------------------------------------------------------------------------
def _pedido_tp(**kw):
    base = {
        'id': 1300, 'numero': 970, 'codigo_externo': '',
        'valor_total': 9990,
        'cliente': {'cpf': '213.485.928-85', 'razao_social': 'Fulano de Tal'},
        'departamento': {'descricao': 'Praia Grande'},
        'itens': [{'produto_servico': {'id': 8, 'codigo': 'MT-X12', 'descricao': 'Scooter X12'},
                   'qtd': 1}],
    }
    base.update(kw)
    return base


def test_replicar_cria_venda_incompleto_tagplus(db):
    venda = rev.replicar(_pedido_tp())
    assert venda is not None
    assert venda.origem_criacao == 'TAGPLUS'
    assert venda.status == 'INCOMPLETO'
    assert venda.tagplus_pedido_id == 1300
    assert venda.tagplus_pedido_numero == 970
    assert venda.cpf_cliente == '21348592885'
    assert venda.nome_cliente == 'Fulano de Tal'
    assert venda.tagplus_departamento == 'Praia Grande'
    divs = [d for d in venda.divergencias if d.tipo == 'AGUARDANDO_CHASSI']
    assert len(divs) == 1
    assert divs[0].numero_chassi is None


def test_replicar_resolve_loja_via_departamento_map(db):
    from app.hora.models import HoraLoja
    from app.hora.models.tagplus import HoraTagPlusDepartamentoMap
    from app.utils.timezone import agora_utc_naive
    import uuid
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='PG', nome='Praia Grande', razao_social='PG LTDA',
                    nome_fantasia='PG', ativa=True, atualizado_em=agora_utc_naive())
    _db.session.add(loja)
    _db.session.flush()
    _db.session.add(HoraTagPlusDepartamentoMap(
        departamento_norm='praia grande', departamento_raw='Praia Grande', loja_id=loja.id))
    _db.session.flush()
    venda = rev.replicar(_pedido_tp())
    assert venda.loja_id == loja.id


def test_replicar_idempotente_nao_duplica(db):
    v1 = rev.replicar(_pedido_tp())
    v2 = rev.replicar(_pedido_tp())
    assert v1 is not None and v2 is None  # 2a chamada e' no-op (ja existe)


def test_reverso_habilitado_default_off(monkeypatch):
    monkeypatch.delenv('HORA_TAGPLUS_REVERSO', raising=False)
    assert rev.reverso_habilitado() is False
    monkeypatch.setenv('HORA_TAGPLUS_REVERSO', '1')
    assert rev.reverso_habilitado() is True


def test_descobrir_e_replicar_orquestra(db, monkeypatch):
    from app.hora.models.tagplus import HoraTagPlusConta
    conta = HoraTagPlusConta(client_id='c', client_secret_encrypted='x', webhook_secret='s')
    _db.session.add(conta)
    _db.session.flush()
    monkeypatch.setattr(rev, 'numero_walk', lambda api, c, **kw: [_pedido_tp(id=1301, numero=971)])
    replicados = rev.descobrir_e_replicar(MagicMock(), conta)
    assert len(replicados) == 1
    assert replicados[0].tagplus_pedido_numero == 971
