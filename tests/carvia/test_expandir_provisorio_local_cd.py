"""expandir_provisorio reconcilia o local_cd do EmbarqueItem CarVia a fonte (CarviaNf),
INDEPENDENTE de o embarque ja ter saido (data_embarque).

Bug (COL-004, 2026-06-23): a reconciliacao do local_cd via sincronizador so rodava dentro do
bloco `if embarque.data_embarque` do expandir_provisorio. Antes da saida da portaria, um item
CarVia (CARVIA-PED-*/CARVIA-NF-*) que recebia a NF ficava com o local_cd da criacao (VM default)
divergente da NF/Coleta TM. A entrega (casa por numero_nf) era reconciliada; o EmbarqueItem nao.
"""
import uuid

from sqlalchemy import text

from app.carvia.services.documentos.embarque_carvia_service import EmbarqueCarViaService


def _criar_nf(db, numero, local_cd='TENENTE_MARQUES'):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='12345678000199', nome_emitente='EMIT',
        cnpj_destinatario='98765432000155', nome_destinatario='CLIENTE REAL LTDA',
        cidade_destinatario='Sao Paulo', uf_destinatario='SP', valor_total=1000,
        tipo_fonte='MANUAL', status='ATIVA', local_cd=local_cd, criado_por='test@bot',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _criar_cot_ped(db, numero_nf):
    """Cria cliente+endereco+cotacao+pedido (ambos VM) + item de pedido com a NF."""
    suf = uuid.uuid4().hex[:6]
    cli_id = db.session.execute(text(
        "INSERT INTO carvia_clientes (nome_comercial, criado_por) "
        "VALUES (:n, 'test@bot') RETURNING id"
    ), {'n': f'Cli{suf}'}).scalar()
    end_id = db.session.execute(text(
        "INSERT INTO carvia_cliente_enderecos (cliente_id, tipo, criado_por) "
        "VALUES (:c, 'ORIGEM', 'test@bot') RETURNING id"
    ), {'c': cli_id}).scalar()
    cot_id = db.session.execute(text(
        "INSERT INTO carvia_cotacoes (numero_cotacao, cliente_id, endereco_origem_id, "
        "endereco_destino_id, tipo_material, criado_por, local_cd) "
        "VALUES (:num, :cli, :e, :e, 'MOTO', 'test@bot', 'VICTORIO_MARCHEZINE') RETURNING id"
    ), {'num': f'COT-{suf}', 'cli': cli_id, 'e': end_id}).scalar()
    ped_id = db.session.execute(text(
        "INSERT INTO carvia_pedidos (numero_pedido, cotacao_id, filial, tipo_separacao, "
        "criado_por, local_cd) "
        "VALUES (:n, :c, 'SP', 'ESTOQUE', 'test@bot', 'VICTORIO_MARCHEZINE') RETURNING id"
    ), {'n': f'PED-{suf}', 'c': cot_id}).scalar()
    db.session.execute(text(
        "INSERT INTO carvia_pedido_itens (pedido_id, quantidade, numero_nf) "
        "VALUES (:p, 1, :nf)"
    ), {'p': ped_id, 'nf': numero_nf})
    db.session.flush()
    return cot_id, ped_id


def _criar_embarque_item(db, cot_id, ped_id, numero_nf, *, local_cd, provisorio,
                         data_embarque=None):
    from app.embarques.models import Embarque, EmbarqueItem
    from app.utils.timezone import agora_utc_naive
    numero_emb = int(uuid.uuid4().int % 9_000_000) + 1_000_000
    emb = Embarque(numero=numero_emb, status='ativo', criado_em=agora_utc_naive(),
                   data_embarque=data_embarque)
    db.session.add(emb)
    db.session.flush()
    ei = EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id=f'CARVIA-PED-{ped_id}', pedido='P1',
        cliente='X', status='ativo', uf_destino='SP', cidade_destino='X',
        local_cd=local_cd, provisorio=provisorio, carvia_cotacao_id=cot_id,
        nota_fiscal=numero_nf, volumes=1,
    )
    db.session.add(ei)
    db.session.flush()
    return emb, ei


def test_expandir_reconcilia_local_cd_sem_saida_portaria(db):
    """Item CARVIA-* VM + NF TM, embarque SEM data_embarque: apos expandir_provisorio o
    item fica TM (mesmo da fonte). Reproduz o caso COL-004 (coleta nao coletada)."""
    _criar_nf(db, '550100', local_cd='TENENTE_MARQUES')
    cot_id, ped_id = _criar_cot_ped(db, '550100')
    _emb, ei = _criar_embarque_item(
        db, cot_id, ped_id, '550100',
        local_cd='VICTORIO_MARCHEZINE', provisorio=False, data_embarque=None,
    )

    EmbarqueCarViaService.expandir_provisorio(cot_id, ped_id, '550100')
    db.session.refresh(ei)

    assert ei.local_cd == 'TENENTE_MARQUES'


def test_expandir_nao_toca_item_nacom_da_mesma_nf(db):
    """Item Nacom (lote nao-CARVIA) com a MESMA NF nao pode ser alterado (R1)."""
    from app.embarques.models import EmbarqueItem
    _criar_nf(db, '550101', local_cd='TENENTE_MARQUES')
    cot_id, ped_id = _criar_cot_ped(db, '550101')
    emb, ei = _criar_embarque_item(
        db, cot_id, ped_id, '550101',
        local_cd='VICTORIO_MARCHEZINE', provisorio=False, data_embarque=None,
    )
    ei_nacom = EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id='LOTE-NACOM', pedido='P2', cliente='X',
        status='ativo', uf_destino='SP', cidade_destino='X',
        local_cd='VICTORIO_MARCHEZINE', nota_fiscal='550101', volumes=1,
    )
    db.session.add(ei_nacom)
    db.session.flush()

    EmbarqueCarViaService.expandir_provisorio(cot_id, ped_id, '550101')
    db.session.refresh(ei)
    db.session.refresh(ei_nacom)

    assert ei.local_cd == 'TENENTE_MARQUES'
    assert ei_nacom.local_cd == 'VICTORIO_MARCHEZINE'
