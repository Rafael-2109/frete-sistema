"""Prefill da rota do mapa -> Simulador 3D: chips removiveis por UNIDADE de
roteirizacao (NF real / pedido s/ NF / cotacao solta), nao apenas por NF.

Contexto: o mapa monta os lotes CarVia como `CARVIA-PED-{id}` / `CARVIA-{cot_id}`
(mapa_service.py), nao `CARVIA-NF-`. Como `CarviaPedidoItem.numero_nf` so e
preenchido apos faturamento, a roteirizacao (pre-faturamento) caia em
`itens_diretos` -> as motos apareciam mas SEM chip removivel. Esta feature
generaliza o breakdown `nfs` para `unidades` cobrindo os 3 casos.
"""
import uuid

from app import db as _db
from app.carvia.routes.simulador_routes import _resolver_prefill_rota


# --------------------------------------------------------------------------- #
# Fixtures helpers                                                             #
# --------------------------------------------------------------------------- #

def _modelo(peso=200):
    from app.carvia.models.config_moto import CarviaModeloMoto
    m = CarviaModeloMoto(
        nome='MOD-' + uuid.uuid4().hex[:8],
        comprimento=180, largura=70, altura=110, peso_medio=peso,
        cubagem_minima=300, ativo=True, criado_por='test@bot',
    )
    _db.session.add(m)
    _db.session.flush()
    return m


def _nf(numero, modelo, qtd, status='ATIVA', cliente='CLIENTE NF', cidade='Sao Paulo', uf='SP'):
    from app.carvia.models.documentos import CarviaNf, CarviaNfItem
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='12345678000199', nome_emitente='EMIT',
        cnpj_destinatario='98765432000155', nome_destinatario=cliente,
        cidade_destinatario=cidade, uf_destinatario=uf, valor_total=1000,
        tipo_fonte='MANUAL', status=status, criado_por='test@bot',
    )
    _db.session.add(nf)
    _db.session.flush()
    item = CarviaNfItem(nf_id=nf.id, modelo_moto_id=modelo.id, quantidade=qtd,
                        codigo_produto='X')
    _db.session.add(item)
    _db.session.flush()
    return nf


def _cliente(nome='CLIENTE PED'):
    from app.carvia.models.clientes import CarviaCliente
    c = CarviaCliente(nome_comercial=nome, ativo=True, criado_por='test@bot')
    _db.session.add(c)
    _db.session.flush()
    return c


def _endereco(cliente_id, tipo):
    from app.carvia.models.clientes import CarviaClienteEndereco
    e = CarviaClienteEndereco(cliente_id=cliente_id, tipo=tipo, criado_por='test@bot')
    _db.session.add(e)
    _db.session.flush()
    return e


def _cotacao(cliente, cidade='Campinas', uf='SP'):
    from app.carvia.models.cotacao import CarviaCotacao
    origem = _endereco(None, 'ORIGEM')
    destino = _endereco(cliente.id, 'DESTINO')
    cot = CarviaCotacao(
        numero_cotacao='COT-' + uuid.uuid4().hex[:6],
        cliente_id=cliente.id, endereco_origem_id=origem.id,
        endereco_destino_id=destino.id, tipo_material='MOTO',
        entrega_cidade=cidade, entrega_uf=uf, status='RASCUNHO',
        criado_por='test@bot',
    )
    _db.session.add(cot)
    _db.session.flush()
    return cot


def _pedido(cotacao, numero=None):
    from app.carvia.models.cotacao import CarviaPedido
    p = CarviaPedido(
        numero_pedido=numero or ('PED-' + uuid.uuid4().hex[:6]),
        cotacao_id=cotacao.id, filial='SP', tipo_separacao='ESTOQUE',
        status='ABERTO', criado_por='test@bot',
    )
    _db.session.add(p)
    _db.session.flush()
    return p


def _pedido_item(pedido, modelo, qtd, numero_nf=None):
    from app.carvia.models.cotacao import CarviaPedidoItem
    it = CarviaPedidoItem(pedido_id=pedido.id, modelo_moto_id=modelo.id,
                          quantidade=qtd, numero_nf=numero_nf)
    _db.session.add(it)
    _db.session.flush()
    return it


def _cotacao_moto(cotacao, modelo, qtd):
    from app.carvia.models.cotacao import CarviaCotacaoMoto
    cm = CarviaCotacaoMoto(cotacao_id=cotacao.id, modelo_moto_id=modelo.id,
                           quantidade=qtd)
    _db.session.add(cm)
    _db.session.flush()
    return cm


def _unidade(res, chave):
    return next((u for u in res['unidades'] if u['chave'] == chave), None)


def _qtd_total(motos):
    return sum(m['quantidade'] for m in motos)


# --------------------------------------------------------------------------- #
# Testes                                                                       #
# --------------------------------------------------------------------------- #

def test_pedido_faturado_uma_nf_vira_unidade_nf(db):
    """Pedido com item faturado (numero_nf) -> 1 unidade do tipo NF."""
    modelo = _modelo()
    nf = _nf('700001', modelo, qtd=4)
    cot = _cotacao(_cliente())
    ped = _pedido(cot)
    _pedido_item(ped, modelo, qtd=4, numero_nf='700001')

    res = _resolver_prefill_rota([f'CARVIA-PED-{ped.id}'])

    # chave da NF = numero puro (casa com o fluxo manual "NF nao entregue",
    # evitando chip duplicado se o usuario re-adicionar a mesma NF).
    u = _unidade(res, '700001')
    assert u is not None, res['unidades']
    assert u['tipo'] == 'nf'
    assert u['rotulo'] == 'NF 700001'
    assert u['cliente'] == 'CLIENTE NF'
    assert u['uf'] == 'SP'
    assert _qtd_total(u['motos']) == 4
    assert _qtd_total(res['motos']) == 4
    _ = nf  # silencia linter


def test_pedido_faturado_duas_nfs_vira_duas_unidades(db):
    """Pedido faturado em 2 NFs distintas -> 2 unidades NF (granularidade fina)."""
    modelo = _modelo()
    _nf('700010', modelo, qtd=2)
    _nf('700011', modelo, qtd=3)
    cot = _cotacao(_cliente())
    ped = _pedido(cot)
    _pedido_item(ped, modelo, qtd=2, numero_nf='700010')
    _pedido_item(ped, modelo, qtd=3, numero_nf='700011')

    res = _resolver_prefill_rota([f'CARVIA-PED-{ped.id}'])

    chaves = {u['chave'] for u in res['unidades']}
    assert chaves == {'700010', '700011'}, chaves
    assert all(u['tipo'] == 'nf' for u in res['unidades'])
    assert _qtd_total(res['motos']) == 5


def test_pedido_sem_nf_vira_unidade_pedido(db):
    """Pedido pre-faturamento (itens sem numero_nf) -> 1 unidade do tipo Pedido."""
    modelo = _modelo()
    cot = _cotacao(_cliente('CLIENTE PRE FAT'), cidade='Sorocaba', uf='SP')
    ped = _pedido(cot, numero='PED-9001')
    _pedido_item(ped, modelo, qtd=3, numero_nf=None)

    res = _resolver_prefill_rota([f'CARVIA-PED-{ped.id}'])

    u = _unidade(res, f'PED-{ped.id}')
    assert u is not None, res['unidades']
    assert u['tipo'] == 'pedido'
    assert 'PED-9001' in u['rotulo']
    assert u['cliente'] == 'CLIENTE PRE FAT'
    assert u['municipio'] == 'Sorocaba'
    assert _qtd_total(u['motos']) == 3
    assert _qtd_total(res['motos']) == 3
    # Nenhuma unidade NF foi criada (nao ha NF)
    assert all(u2['tipo'] != 'nf' for u2 in res['unidades'])


def test_cotacao_solta_vira_unidade_cotacao(db):
    """Cotacao sem pedido (CARVIA-{cot_id}) -> unidade via CarviaCotacaoMoto.

    Antes da feature o simulador abria VAZIO para cotacao solta (so lia
    CarviaPedidoItem). Agora le CarviaCotacaoMoto.
    """
    modelo = _modelo()
    cli = _cliente('CLIENTE COTACAO')
    cot = _cotacao(cli, cidade='Jundiai', uf='SP')
    _cotacao_moto(cot, modelo, qtd=2)

    res = _resolver_prefill_rota([f'CARVIA-{cot.id}'])

    u = _unidade(res, f'COT-{cot.id}')
    assert u is not None, res['unidades']
    assert u['tipo'] == 'cotacao'
    assert cot.numero_cotacao in u['rotulo']
    assert u['cliente'] == 'CLIENTE COTACAO'
    assert u['municipio'] == 'Jundiai'
    assert _qtd_total(u['motos']) == 2
    assert _qtd_total(res['motos']) == 2


def test_dedup_nf_cancelada(db):
    """numero_nf nao e unico: reemissao gera CANCELADA + ATIVA. So conta a ATIVA."""
    modelo = _modelo()
    _nf('700020', modelo, qtd=9, status='CANCELADA')
    _nf('700020', modelo, qtd=2, status='ATIVA')
    cot = _cotacao(_cliente())
    ped = _pedido(cot)
    _pedido_item(ped, modelo, qtd=2, numero_nf='700020')

    res = _resolver_prefill_rota([f'CARVIA-PED-{ped.id}'])

    u = _unidade(res, '700020')
    assert u is not None, res['unidades']
    assert _qtd_total(u['motos']) == 2  # da ATIVA, nao 9 nem 11
    assert _qtd_total(res['motos']) == 2


def test_total_motos_soma_nf_e_pedido_sem_nf(db):
    """data.motos = total agregado por modelo (NF + pedido sem NF) — retrocompat:
    as motos aparecem mesmo se o frontend ignorar `unidades`."""
    modelo = _modelo()
    _nf('700030', modelo, qtd=2)
    cot_fat = _cotacao(_cliente())
    ped_fat = _pedido(cot_fat)
    _pedido_item(ped_fat, modelo, qtd=2, numero_nf='700030')

    cot_pre = _cotacao(_cliente())
    ped_pre = _pedido(cot_pre)
    _pedido_item(ped_pre, modelo, qtd=3, numero_nf=None)

    res = _resolver_prefill_rota(
        [f'CARVIA-PED-{ped_fat.id}', f'CARVIA-PED-{ped_pre.id}']
    )

    assert len(res['unidades']) == 2
    # mesmo modelo -> 1 linha agregada de 5 no total
    assert len(res['motos']) == 1
    assert _qtd_total(res['motos']) == 5
