"""Fase 2b da sync HORA->TagPlus: payload COMPLETO do pedido + wiring + to_nfe.

Cobre (atras da flag HORA_TAGPLUS_PUSH_PEDIDO, default OFF):
  - PayloadBuilder.resolver_id_cliente (GET /clientes -> id_cliente, best-effort)
  - PayloadBuilder.montar_corpo_pedido (cliente/itens/faturas/valores; tolerante
    no modo criacao, estrito antes de emitir via to_nfe)
  - pedido_sync_service.criar_pedido com corpo completo
  - emissao via GET /pedidos/to_nfe/{id} (condicional flag + tagplus_pedido_id)

Contrato do POST /pedidos confirmado AO VIVO em 2026-06-29 (teste controlado):
itens usam `produto_servico` (igual /nfes); `cliente` = id_cliente (NAO id_entidade);
departamento/vendedor = int opcional. Ver spec secao "Contrato da API".
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app import db as _db
from app.hora.services.tagplus.payload_builder import PayloadBuilder, PayloadBuilderError
import app.hora.services.tagplus.pedido_sync_service as svc


def _builder_com_api_mock():
    """PayloadBuilder com ApiClient substituido por MagicMock (sem rede)."""
    pb = PayloadBuilder(SimpleNamespace(id=1))
    pb.api = MagicMock()
    return pb


# --------------------------------------------------------------------------
# resolver_id_cliente: GET /clientes -> id_cliente (best-effort, nao cria)
# --------------------------------------------------------------------------
def test_resolver_id_cliente_match_exato_por_documento():
    pb = _builder_com_api_mock()
    pb.api.get.return_value = SimpleNamespace(
        status_code=200,
        json=lambda: [{'id': 957, 'id_entidade': 979, 'cpf': '213.485.928-85'}],
    )
    venda = SimpleNamespace(cpf_cliente='21348592885', nome_cliente='X')
    assert pb.resolver_id_cliente(venda) == 957


def test_resolver_id_cliente_sem_match_retorna_none():
    pb = _builder_com_api_mock()
    pb.api.get.return_value = SimpleNamespace(status_code=200, json=lambda: [])
    venda = SimpleNamespace(cpf_cliente='21348592885', nome_cliente='X')
    assert pb.resolver_id_cliente(venda) is None


def test_resolver_id_cliente_ignora_cpf_divergente():
    # LIKE do TagPlus pode trazer candidato com documento diferente — descartar.
    pb = _builder_com_api_mock()
    pb.api.get.return_value = SimpleNamespace(
        status_code=200,
        json=lambda: [{'id': 111, 'cpf': '999.999.999-99'}],
    )
    venda = SimpleNamespace(cpf_cliente='21348592885', nome_cliente='X')
    assert pb.resolver_id_cliente(venda) is None


def test_resolver_id_cliente_documento_invalido_retorna_none():
    pb = _builder_com_api_mock()
    venda = SimpleNamespace(cpf_cliente='abc', nome_cliente='X')
    assert pb.resolver_id_cliente(venda) is None
    pb.api.get.assert_not_called()


# --------------------------------------------------------------------------
# montar_corpo_pedido: tolerante (criacao) x estrito (emissao)
# --------------------------------------------------------------------------
def test_montar_corpo_pedido_tolerante_omite_blocos_que_falham():
    pb = _builder_com_api_mock()
    venda = SimpleNamespace(id=940, valor_total=1000, itens=[], cpf_cliente='21348592885')
    # itens e faturas levantam (sem mapa); cliente nao resolve
    pb._montar_itens = MagicMock(side_effect=PayloadBuilderError('x', 'sem item'))
    pb._montar_faturas = MagicMock(side_effect=PayloadBuilderError('y', 'sem forma'))
    pb.resolver_id_cliente = MagicMock(return_value=None)
    corpo = pb.montar_corpo_pedido(venda, estrito=False)
    assert 'itens' not in corpo and 'faturas' not in corpo and 'cliente' not in corpo
    assert corpo['valor_total'] == 1000.0


def test_montar_corpo_pedido_inclui_blocos_resolviveis():
    pb = _builder_com_api_mock()
    venda = SimpleNamespace(id=940, valor_total=1000, itens=[], cpf_cliente='21348592885')
    pb._montar_itens = MagicMock(return_value=[{'produto_servico': '8', 'qtd': 1}])
    pb._montar_faturas = MagicMock(return_value=[{'forma_pagamento': 14, 'parcelas': []}])
    pb.resolver_id_cliente = MagicMock(return_value=957)
    corpo = pb.montar_corpo_pedido(venda, estrito=False)
    assert corpo['cliente'] == 957
    assert corpo['itens'] == [{'produto_servico': '8', 'qtd': 1}]
    assert corpo['faturas'] == [{'forma_pagamento': 14, 'parcelas': []}]


def test_montar_corpo_pedido_estrito_propaga_erro():
    pb = _builder_com_api_mock()
    venda = SimpleNamespace(id=940, valor_total=1000, itens=[], cpf_cliente='21348592885')
    pb._montar_itens = MagicMock(side_effect=PayloadBuilderError('x', 'sem item'))
    import pytest
    with pytest.raises(PayloadBuilderError):
        pb.montar_corpo_pedido(venda, estrito=True)


def test_montar_corpo_pedido_estrito_sem_cliente_levanta():
    # Review FIX B: estrito (antes de to_nfe) exige cliente — omitir em silencio
    # faria a NFe sair sem destinatario.
    pb = _builder_com_api_mock()
    venda = SimpleNamespace(id=940, valor_total=1000, itens=[], cpf_cliente='21348592885')
    pb._montar_itens = MagicMock(return_value=[{'produto_servico': '8'}])
    pb._montar_faturas = MagicMock(return_value=[])
    pb._resolver_destinatario = MagicMock()  # nao popula _ultimo_id_cliente
    import pytest
    with pytest.raises(PayloadBuilderError):
        pb.montar_corpo_pedido(venda, estrito=True)


def test_resolver_id_cliente_ambiguo_retorna_none():
    # Review FIX E: 2 clientes com mesmo documento -> ambiguo -> None (nao chuta).
    pb = _builder_com_api_mock()
    pb.api.get.return_value = SimpleNamespace(
        status_code=200,
        json=lambda: [{'id': 1, 'cpf': '213.485.928-85'}, {'id': 2, 'cpf': '21348592885'}],
    )
    venda = SimpleNamespace(cpf_cliente='21348592885', nome_cliente='X')
    assert pb.resolver_id_cliente(venda) is None


# --------------------------------------------------------------------------
# pedido_sync_service.criar_pedido com builder -> payload completo
# --------------------------------------------------------------------------
def _svc():
    import app.hora.services.tagplus.pedido_sync_service as svc
    return svc


def test_montar_payload_pedido_sem_builder_so_identidade():
    svc = _svc()
    p = svc.montar_payload_pedido(SimpleNamespace(id=940, status='COTACAO', observacoes=None))
    assert set(p) == {'codigo_externo', 'status', 'integracao'}


def test_montar_payload_pedido_com_builder_mescla_corpo():
    svc = _svc()
    builder = MagicMock()
    builder.montar_corpo_pedido.return_value = {
        'itens': [{'produto_servico': '8'}], 'cliente': 957, 'valor_total': 1000.0,
    }
    venda = SimpleNamespace(id=940, status='COTACAO', observacoes='obs')
    p = svc.montar_payload_pedido(venda, builder=builder)
    assert p['codigo_externo'] == '940' and p['status'] == 'A'
    assert p['cliente'] == 957 and p['itens'] == [{'produto_servico': '8'}]
    assert p['observacoes'] == 'obs'
    builder.montar_corpo_pedido.assert_called_once_with(venda, estrito=False)


def test_criar_pedido_com_builder_envia_corpo_completo(monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    svc = _svc()
    api = MagicMock()
    api.post.return_value = SimpleNamespace(
        status_code=201, json=lambda: {'id': 7, 'numero': 967})
    builder = MagicMock()
    builder.montar_corpo_pedido.return_value = {'cliente': 957, 'valor_total': 1000.0}
    venda = SimpleNamespace(id=940, status='COTACAO', observacoes=None)
    res = svc.criar_pedido(api, venda, dry_run=False, builder=builder)
    assert res['tagplus_pedido_id'] == 7
    assert res['tagplus_pedido_numero'] == 967
    enviado = api.post.call_args.kwargs['json']
    assert enviado['codigo_externo'] == '940' and enviado['cliente'] == 957


# --------------------------------------------------------------------------
# Wiring (push pos-commit, tolerante a falha, atras da flag) — usa DB real
# --------------------------------------------------------------------------
def _venda_db(status='COTACAO'):
    from app.hora.models.venda import HoraVenda
    v = HoraVenda(cpf_cliente='12345678909', nome_cliente='Cliente Teste',
                  valor_total=Decimal('1000'), status=status)
    _db.session.add(v)
    _db.session.flush()
    return v


def test_push_criar_pedido_flag_off_noop(db, monkeypatch):
    monkeypatch.delenv('HORA_TAGPLUS_PUSH_PEDIDO', raising=False)
    v = _venda_db()
    assert svc.push_criar_pedido(v) is None
    assert v.tagplus_pedido_id is None


def test_push_criar_pedido_grava_id_numero(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    v = _venda_db()
    monkeypatch.setattr(svc, '_conta_builder', lambda: (MagicMock(), MagicMock()))
    monkeypatch.setattr(svc, 'criar_pedido',
                        lambda api, venda, **kw: {'tagplus_pedido_id': 7, 'tagplus_pedido_numero': 967})
    svc.push_criar_pedido(v)
    assert v.tagplus_pedido_id == 7 and v.tagplus_pedido_numero == 967


def test_push_criar_pedido_idempotente_se_ja_tem(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    v = _venda_db()
    v.tagplus_pedido_id = 5
    called = []
    monkeypatch.setattr(svc, '_conta_builder', lambda: called.append(1) or (MagicMock(), MagicMock()))
    svc.push_criar_pedido(v)
    assert called == [] and v.tagplus_pedido_id == 5


def test_push_criar_pedido_noop_para_faturado(db, monkeypatch):
    # Review FIX C: venda FATURADO (ja tem NF) nao deve criar pedido novo no
    # TagPlus (orfao desvinculado da NF). Idem CANCELADO.
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    v = _venda_db(status='FATURADO')
    called = []
    monkeypatch.setattr(svc, '_conta_builder', lambda: called.append(1) or (MagicMock(), MagicMock()))
    svc.push_criar_pedido(v)
    assert called == [] and v.tagplus_pedido_id is None


def test_push_criar_pedido_tolerante_a_falha(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    v = _venda_db()
    monkeypatch.setattr(svc, '_conta_builder', lambda: (MagicMock(), MagicMock()))

    def boom(*a, **k):
        raise RuntimeError('rede caiu')
    monkeypatch.setattr(svc, 'criar_pedido', boom)
    assert svc.push_criar_pedido(v) is None
    assert v.tagplus_pedido_id is None


def test_push_atualizar_status_patch_b(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    v = _venda_db(status='CONFIRMADO')
    v.tagplus_pedido_id = 7
    captured = {}
    monkeypatch.setattr(svc, '_conta_builder', lambda: (MagicMock(), MagicMock()))
    monkeypatch.setattr(svc, 'atualizar_status_pedido',
                        lambda api, pid, status_tp, **kw: captured.update(pid=pid, status=status_tp))
    svc.push_atualizar_status(v)
    assert captured == {'pid': 7, 'status': 'B'}


def test_push_atualizar_status_sem_pedido_noop(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    v = _venda_db(status='CONFIRMADO')

    def nao_chamar(*a, **k):
        raise AssertionError('nao deveria chamar a API sem tagplus_pedido_id')
    monkeypatch.setattr(svc, 'atualizar_status_pedido', nao_chamar)
    assert svc.push_atualizar_status(v) is None


def test_push_cancelar(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    v = _venda_db(status='CANCELADO')
    v.tagplus_pedido_id = 7
    captured = {}
    monkeypatch.setattr(svc, '_conta_builder', lambda: (MagicMock(), MagicMock()))
    monkeypatch.setattr(svc, 'cancelar_pedido', lambda api, pid, **kw: captured.update(pid=pid))
    svc.push_cancelar(v)
    assert captured == {'pid': 7}


# --------------------------------------------------------------------------
# Wiring nos pontos de transicao do venda_service (criar/confirmar/cancelar)
# --------------------------------------------------------------------------
def _setup_chassi():
    import uuid
    from app.hora.models import HoraLoja, HoraModelo
    from app.hora.services.moto_service import get_or_create_moto, registrar_evento
    from app.utils.timezone import agora_utc_naive
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='L-' + cnpj[:6], nome='Loja', razao_social='L LTDA',
                    nome_fantasia='L', ativa=True, atualizado_em=agora_utc_naive())
    _db.session.add(loja)
    _db.session.flush()
    m = HoraModelo(nome_modelo='MOD-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=Decimal('1000'))
    _db.session.add(m)
    _db.session.flush()
    ch = ('CH' + uuid.uuid4().hex).upper()[:25]
    get_or_create_moto(numero_chassi=ch, modelo_nome=m.nome_modelo, cor='PRETA', criado_por='t')
    registrar_evento(numero_chassi=ch, tipo='RECEBIDA', loja_id=loja.id, operador='t')
    registrar_evento(numero_chassi=ch, tipo='CONFERIDA', loja_id=loja.id, operador='t')
    _db.session.flush()
    return loja, ch


def test_criar_venda_manual_dispara_push_criar(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    from app.hora.services import venda_service
    loja, ch = _setup_chassi()
    chamada = {}
    monkeypatch.setattr(svc, 'push_criar_pedido', lambda venda: chamada.update(id=venda.id))
    v = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C',
        itens=[{'numero_chassi': ch, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1000'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t')
    assert chamada.get('id') == v.id


def test_confirmar_venda_dispara_push_status(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    from app.hora.services import venda_service
    v = _venda_db(status='COTACAO')
    v.tagplus_pedido_id = 7
    _db.session.commit()
    chamada = {}
    monkeypatch.setattr(svc, 'push_atualizar_status', lambda venda: chamada.update(id=venda.id))
    venda_service.confirmar_venda(v.id, usuario='t')
    assert chamada.get('id') == v.id


def test_cancelar_venda_dispara_push_cancelar(db, monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    from app.hora.services import venda_service
    v = _venda_db(status='COTACAO')
    v.tagplus_pedido_id = 7
    _db.session.commit()
    chamada = {}
    monkeypatch.setattr(svc, 'push_cancelar', lambda venda: chamada.update(id=venda.id))
    venda_service.cancelar_venda(v.id, motivo='teste cancelamento', usuario='t')
    assert chamada.get('id') == v.id


# --------------------------------------------------------------------------
# Emissao via to_nfe (gated: flag ON + tagplus_pedido_id) — evita pedido dup
# --------------------------------------------------------------------------
def test_enviar_nfe_flag_off_usa_post_nfes(monkeypatch):
    monkeypatch.delenv('HORA_TAGPLUS_PUSH_PEDIDO', raising=False)
    from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
    client, builder = MagicMock(), MagicMock()
    client.post.return_value = SimpleNamespace(status_code=201)
    venda = SimpleNamespace(tagplus_pedido_id=7)  # tem pedido, mas flag OFF
    EmissorNfeHora._enviar_nfe(client, builder, venda, {'p': 1})
    assert client.post.call_args.args[0] == '/nfes'
    client.get.assert_not_called()
    client.patch.assert_not_called()


def test_enviar_nfe_flag_on_com_pedido_usa_to_nfe(monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
    client, builder = MagicMock(), MagicMock()
    builder.montar_corpo_pedido.return_value = {'itens': [], 'cliente': 957}
    client.patch.return_value = SimpleNamespace(status_code=200)
    client.get.return_value = SimpleNamespace(status_code=200)
    venda = SimpleNamespace(tagplus_pedido_id=7)
    EmissorNfeHora._enviar_nfe(client, builder, venda, {'p': 1})
    assert client.patch.call_args.args[0] == '/pedidos/7'
    assert client.patch.call_args.kwargs['json']['status'] == 'B'
    assert client.get.call_args.args[0] == '/pedidos/to_nfe/7'
    client.post.assert_not_called()
    builder.montar_corpo_pedido.assert_called_once_with(venda, estrito=True)


def test_enviar_nfe_flag_on_sem_pedido_fallback_post(monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
    client, builder = MagicMock(), MagicMock()
    client.post.return_value = SimpleNamespace(status_code=201)
    venda = SimpleNamespace(tagplus_pedido_id=None)
    EmissorNfeHora._enviar_nfe(client, builder, venda, {'p': 1})
    assert client.post.call_args.args[0] == '/nfes'
    client.get.assert_not_called()


def test_enviar_nfe_patch_falho_nao_emite_to_nfe(monkeypatch):
    # Review FIX A/critico: PATCH 4xx (ApiClient nao faz raise_for_status) NAO
    # pode prosseguir p/ to_nfe sobre pedido nao-atualizado.
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    import pytest
    from app.hora.services.tagplus.emissor_nfe import EmissorNfeHora
    client, builder = MagicMock(), MagicMock()
    builder.montar_corpo_pedido.return_value = {'cliente': 957}
    client.patch.return_value = SimpleNamespace(status_code=422, text='campo invalido')
    venda = SimpleNamespace(tagplus_pedido_id=7)
    with pytest.raises(PayloadBuilderError):
        EmissorNfeHora._enviar_nfe(client, builder, venda, {'p': 1})
    client.get.assert_not_called()  # nao emitiu to_nfe sobre pedido stale
