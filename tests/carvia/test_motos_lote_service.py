"""Contagem de motos por lote (CarVia) para o mapa de roteirizacao.

Cobre o caminho que o commit 8947b4e93 deixou SEM teste (so testou NACOM=0): o
contador do mapa contava motos por `CarviaPedidoItem.modelo_moto_id`, que e NULL
em 100% dos itens de pedido em producao -> qtd_motos sempre 0. A fonte canonica
e `carvia_nf_itens` (via `CarviaPedidoItem.numero_nf`).

Os itens faturados aqui sao criados com `modelo_moto_id=None` DE PROPOSITO, para
refletir producao e provar que a contagem vem da NF, nao do item de pedido.
"""
import uuid

from app import db as _db
from app.carvia.services.documentos.motos_lote_service import qtd_motos_por_lotes


def _modelo(ativo=True):
    from app.carvia.models.config_moto import CarviaModeloMoto
    m = CarviaModeloMoto(
        nome='MOD-' + uuid.uuid4().hex[:8],
        comprimento=180, largura=70, altura=110, peso_medio=200,
        cubagem_minima=300, ativo=ativo, criado_por='test@bot',
    )
    _db.session.add(m)
    _db.session.flush()
    return m


def _nf(numero, modelo, qtd, status='ATIVA'):
    from app.carvia.models.documentos import CarviaNf, CarviaNfItem
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='12345678000199', nome_emitente='EMIT',
        cnpj_destinatario='98765432000155', nome_destinatario='CLIENTE NF',
        cidade_destinatario='Sao Paulo', uf_destinatario='SP', valor_total=1000,
        tipo_fonte='MANUAL', status=status, criado_por='test@bot',
    )
    _db.session.add(nf)
    _db.session.flush()
    _db.session.add(CarviaNfItem(nf_id=nf.id, modelo_moto_id=modelo.id,
                                 quantidade=qtd, codigo_produto='X'))
    _db.session.flush()
    return nf


def _cotacao(tipo_material='MOTO'):
    from app.carvia.models.clientes import CarviaCliente, CarviaClienteEndereco
    from app.carvia.models.cotacao import CarviaCotacao
    cli = CarviaCliente(nome_comercial='CLI', ativo=True, criado_por='test@bot')
    _db.session.add(cli)
    _db.session.flush()
    origem = CarviaClienteEndereco(cliente_id=None, tipo='ORIGEM', criado_por='test@bot')
    destino = CarviaClienteEndereco(cliente_id=cli.id, tipo='DESTINO', criado_por='test@bot')
    _db.session.add_all([origem, destino])
    _db.session.flush()
    cot = CarviaCotacao(
        numero_cotacao='COT-' + uuid.uuid4().hex[:6], cliente_id=cli.id,
        endereco_origem_id=origem.id, endereco_destino_id=destino.id,
        tipo_material=tipo_material, entrega_cidade='Campinas', entrega_uf='SP',
        status='RASCUNHO', criado_por='test@bot',
    )
    _db.session.add(cot)
    _db.session.flush()
    return cot


def _pedido(cotacao):
    from app.carvia.models.cotacao import CarviaPedido
    p = CarviaPedido(
        numero_pedido='PED-' + uuid.uuid4().hex[:6], cotacao_id=cotacao.id,
        filial='SP', tipo_separacao='ESTOQUE', status='ABERTO', criado_por='test@bot',
    )
    _db.session.add(p)
    _db.session.flush()
    return p


def _pedido_item(pedido, qtd, numero_nf=None, modelo_moto_id=None):
    from app.carvia.models.cotacao import CarviaPedidoItem
    it = CarviaPedidoItem(pedido_id=pedido.id, modelo_moto_id=modelo_moto_id,
                          quantidade=qtd, numero_nf=numero_nf)
    _db.session.add(it)
    _db.session.flush()
    return it


def _cotacao_moto(cotacao, modelo, qtd):
    from app.carvia.models.cotacao import CarviaCotacaoMoto
    _db.session.add(CarviaCotacaoMoto(cotacao_id=cotacao.id,
                                      modelo_moto_id=modelo.id, quantidade=qtd))
    _db.session.flush()


# --------------------------------------------------------------------------- #

def test_pedido_faturado_conta_motos_via_nf_nao_pelo_item(db):
    """O bug: item faturado tem modelo_moto_id=None; as motos vem da NF."""
    modelo = _modelo()
    _nf('700001', modelo, qtd=5)
    ped = _pedido(_cotacao())
    _pedido_item(ped, qtd=5, numero_nf='700001', modelo_moto_id=None)

    lote = f'CARVIA-PED-{ped.id}'
    assert qtd_motos_por_lotes([lote]) == {lote: 5}


def test_pedido_faturado_duas_nfs_soma(db):
    modelo = _modelo()
    _nf('700010', modelo, qtd=2)
    _nf('700011', modelo, qtd=3)
    ped = _pedido(_cotacao())
    _pedido_item(ped, qtd=2, numero_nf='700010')
    _pedido_item(ped, qtd=3, numero_nf='700011')

    lote = f'CARVIA-PED-{ped.id}'
    assert qtd_motos_por_lotes([lote]) == {lote: 5}


def test_nf_cancelada_excluida(db):
    """numero_nf nao e unico: so conta a ATIVA (reemissao gera CANCELADA + ATIVA)."""
    modelo = _modelo()
    _nf('700020', modelo, qtd=9, status='CANCELADA')
    _nf('700020', modelo, qtd=2, status='ATIVA')
    ped = _pedido(_cotacao())
    _pedido_item(ped, qtd=2, numero_nf='700020')

    lote = f'CARVIA-PED-{ped.id}'
    assert qtd_motos_por_lotes([lote]) == {lote: 2}


def test_pedido_sem_nf_usa_fallback_modelo_direto(db):
    """Pre-faturamento (item sem NF) conta via modelo_moto_id do proprio item."""
    modelo = _modelo()
    ped = _pedido(_cotacao())
    _pedido_item(ped, qtd=3, numero_nf=None, modelo_moto_id=modelo.id)

    lote = f'CARVIA-PED-{ped.id}'
    assert qtd_motos_por_lotes([lote]) == {lote: 3}


def test_cotacao_solta_moto_usa_qtd_total_motos(db):
    modelo = _modelo()
    cot = _cotacao(tipo_material='MOTO')
    _cotacao_moto(cot, modelo, qtd=4)

    lote = f'CARVIA-{cot.id}'
    assert qtd_motos_por_lotes([lote]) == {lote: 4}


def test_cotacao_carga_geral_nao_conta_motos(db):
    cot = _cotacao(tipo_material='CARGA_GERAL')
    lote = f'CARVIA-{cot.id}'
    assert qtd_motos_por_lotes([lote]) == {lote: 0}


def test_lote_nacom_e_malformado_ficam_zero(db):
    res = qtd_motos_por_lotes(['LOTE_NACOM_123', 'CARVIA-NF-naoint', ''])
    assert res == {'LOTE_NACOM_123': 0, 'CARVIA-NF-naoint': 0, '': 0}


def test_lista_vazia(db):
    assert qtd_motos_por_lotes([]) == {}
    assert qtd_motos_por_lotes(None) == {}
