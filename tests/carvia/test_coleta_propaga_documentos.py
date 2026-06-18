"""Frente A — propagacao de local_cd da Coleta para CarviaPedido + CarviaCotacao.

A Coleta e a FONTE da flag de CD (VM/TM). Ela ja propagava para CarviaNf (Stream 1).
Agora tambem propaga para o CarviaPedido e a CarviaCotacao que referenciam a NF
(via CarviaPedidoItem.numero_nf), para a VIEW pedidos (Partes 2A/2B) exibir o CD real.

Gatilhos cobertos: vincular_nf (manual/auto/lote), editar_coleta (re-propaga ao mudar
destino) e marcar_coletada. Match por numero_nf normalizado (so digitos, sem zeros a esq.).
"""
import uuid

from sqlalchemy import text

from app.carvia.services.documentos.coleta_service import CarviaColetaService


def _criar_nf(db, numero, local_cd='VICTORIO_MARCHEZINE'):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='12345678000199', nome_emitente='EMIT',
        cnpj_destinatario='98765432000155', nome_destinatario='CLIENTE REAL LTDA',
        tipo_fonte='MANUAL', status='ATIVA', local_cd=local_cd, criado_por='test@bot',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _criar_pedido_com_item_nf(db, numero_nf):
    """Cria cotacao + pedido (ambos VM) + 1 item com a numero_nf. Retorna (cot_id, ped_id)."""
    suf = uuid.uuid4().hex[:6]
    cli_id = db.session.execute(text("""
        INSERT INTO carvia_clientes (nome_comercial, criado_por)
        VALUES (:nome, 'test@bot') RETURNING id
    """), {'nome': f'Cliente T{suf}'}).scalar()
    end_id = db.session.execute(text("""
        INSERT INTO carvia_cliente_enderecos (cliente_id, tipo, criado_por)
        VALUES (:cli, 'ORIGEM', 'test@bot') RETURNING id
    """), {'cli': cli_id}).scalar()
    cot_id = db.session.execute(text("""
        INSERT INTO carvia_cotacoes
            (numero_cotacao, cliente_id, endereco_origem_id, endereco_destino_id,
             tipo_material, criado_por, local_cd)
        VALUES (:num, :cli, :end, :end, 'MOTO', 'test@bot', 'VICTORIO_MARCHEZINE') RETURNING id
    """), {'num': f'COT-T{suf}', 'cli': cli_id, 'end': end_id}).scalar()
    ped_id = db.session.execute(text("""
        INSERT INTO carvia_pedidos (numero_pedido, cotacao_id, filial, tipo_separacao, criado_por, local_cd)
        VALUES (:num, :cot, 'SP', 'ESTOQUE', 'test@bot', 'VICTORIO_MARCHEZINE') RETURNING id
    """), {'num': f'PED-T{suf}', 'cot': cot_id}).scalar()
    db.session.execute(text("""
        INSERT INTO carvia_pedido_itens (pedido_id, quantidade, numero_nf)
        VALUES (:ped, 1, :nf)
    """), {'ped': ped_id, 'nf': numero_nf})
    db.session.flush()
    return cot_id, ped_id


def _local_cd(db, tabela, _id):
    return db.session.execute(
        text(f"SELECT local_cd FROM {tabela} WHERE id = :id"), {'id': _id}
    ).scalar()


def test_vincular_nf_propaga_para_pedido_e_cotacao(db):
    """Ao vincular a NF a uma coleta TM, o pedido e a cotacao que a referenciam viram TM."""
    cot_id, ped_id = _criar_pedido_com_item_nf(db, numero_nf='999777')
    nf = _criar_nf(db, numero='999777', local_cd='VICTORIO_MARCHEZINE')

    coleta = CarviaColetaService.criar_coleta(local_cd='TENENTE_MARQUES', usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='999777')
    CarviaColetaService.vincular_nf(linha, nf.id)

    assert nf.local_cd == 'TENENTE_MARQUES'
    assert _local_cd(db, 'carvia_pedidos', ped_id) == 'TENENTE_MARQUES'
    assert _local_cd(db, 'carvia_cotacoes', cot_id) == 'TENENTE_MARQUES'


def test_match_normalizado_com_zeros_a_esquerda(db):
    """numero_nf '00999' (item) casa com '999' (coleta/NF) — normalizacao igual ao _norm_nf."""
    cot_id, ped_id = _criar_pedido_com_item_nf(db, numero_nf='00999')
    nf = _criar_nf(db, numero='999', local_cd='VICTORIO_MARCHEZINE')

    coleta = CarviaColetaService.criar_coleta(local_cd='TENENTE_MARQUES', usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='999')
    CarviaColetaService.vincular_nf(linha, nf.id)

    assert _local_cd(db, 'carvia_pedidos', ped_id) == 'TENENTE_MARQUES'
    assert _local_cd(db, 'carvia_cotacoes', cot_id) == 'TENENTE_MARQUES'


def test_editar_coleta_repropaga_para_documentos(db):
    """Mudar o destino da coleta (VM->TM) re-propaga para a NF E para pedido/cotacao."""
    cot_id, ped_id = _criar_pedido_com_item_nf(db, numero_nf='888111')
    nf = _criar_nf(db, numero='888111', local_cd='VICTORIO_MARCHEZINE')

    coleta = CarviaColetaService.criar_coleta(local_cd='VICTORIO_MARCHEZINE', usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='888111')
    CarviaColetaService.vincular_nf(linha, nf.id)
    # Ainda VM
    assert _local_cd(db, 'carvia_pedidos', ped_id) == 'VICTORIO_MARCHEZINE'

    CarviaColetaService.editar_coleta(coleta, local_cd='TENENTE_MARQUES')
    assert _local_cd(db, 'carvia_pedidos', ped_id) == 'TENENTE_MARQUES'
    assert _local_cd(db, 'carvia_cotacoes', cot_id) == 'TENENTE_MARQUES'


def test_sem_item_de_pedido_nao_quebra(db):
    """NF sem pedido/item correspondente: vincular nao falha (so propaga p/ a NF)."""
    nf = _criar_nf(db, numero='123456', local_cd='VICTORIO_MARCHEZINE')
    coleta = CarviaColetaService.criar_coleta(local_cd='TENENTE_MARQUES', usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='123456')
    CarviaColetaService.vincular_nf(linha, nf.id)
    assert nf.local_cd == 'TENENTE_MARQUES'


def _criar_embarque_item_e_entrega(db, numero_nf, local_cd='VICTORIO_MARCHEZINE'):
    """Cria 1 EmbarqueItem CarVia (CARVIA-%) + 1 Nacom (controle) + 2 EntregaMonitorada
    (CARVIA + outra origem) para a NF. Retorna (ei_carvia, ei_nacom, ent_carvia, ent_nacom)."""
    from app.embarques.models import Embarque, EmbarqueItem
    from app.monitoramento.models import EntregaMonitorada
    from app.utils.timezone import agora_utc_naive
    numero_emb = int(uuid.uuid4().int % 9_000_000) + 1_000_000
    emb = Embarque(numero=numero_emb, status='ativo', criado_em=agora_utc_naive())
    db.session.add(emb)
    db.session.flush()
    base = dict(embarque_id=emb.id, nota_fiscal=numero_nf, cliente='X', status='ativo',
                uf_destino='SP', cidade_destino='X', local_cd=local_cd)
    ei_carvia = EmbarqueItem(separacao_lote_id=f'CARVIA-NF-{numero_nf}', pedido='P1', **base)
    ei_nacom = EmbarqueItem(separacao_lote_id='LOTE-NACOM', pedido='P2', **base)
    ent_carvia = EntregaMonitorada(numero_nf=numero_nf, cliente='X', origem='CARVIA', local_cd=local_cd)
    ent_nacom = EntregaMonitorada(numero_nf=numero_nf, cliente='X', origem='NACOM', local_cd=local_cd)
    db.session.add_all([ei_carvia, ei_nacom, ent_carvia, ent_nacom])
    db.session.flush()
    return ei_carvia, ei_nacom, ent_carvia, ent_nacom


def test_vincular_nf_propaga_para_embarque_item_e_entrega(db):
    """Vincular a NF a uma coleta TM propaga para o EmbarqueItem CarVia e a EntregaMonitorada
    CarVia; itens Nacom / entregas de outra origem ficam INTACTOS (R1: helper R1-safe)."""
    nf = _criar_nf(db, numero='770088', local_cd='VICTORIO_MARCHEZINE')
    ei_carvia, ei_nacom, ent_carvia, ent_nacom = _criar_embarque_item_e_entrega(db, '770088')

    coleta = CarviaColetaService.criar_coleta(local_cd='TENENTE_MARQUES', usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='770088')
    CarviaColetaService.vincular_nf(linha, nf.id)
    db.session.flush()
    for o in (ei_carvia, ei_nacom, ent_carvia, ent_nacom):
        db.session.refresh(o)

    assert ei_carvia.local_cd == 'TENENTE_MARQUES'
    assert ent_carvia.local_cd == 'TENENTE_MARQUES'
    assert ei_nacom.local_cd == 'VICTORIO_MARCHEZINE'   # Nacom NAO pode mudar
    assert ent_nacom.local_cd == 'VICTORIO_MARCHEZINE'


def test_editar_coleta_repropaga_para_embarque_item(db):
    """Mudar o destino da coleta (VM->TM) re-propaga para EmbarqueItem CarVia + Entrega CarVia."""
    nf = _criar_nf(db, numero='660099', local_cd='VICTORIO_MARCHEZINE')
    ei_carvia, _, ent_carvia, _ = _criar_embarque_item_e_entrega(db, '660099')

    coleta = CarviaColetaService.criar_coleta(local_cd='VICTORIO_MARCHEZINE', usuario='test@bot')
    linha = CarviaColetaService.adicionar_linha(coleta, numero_nf='660099')
    CarviaColetaService.vincular_nf(linha, nf.id)
    db.session.flush()
    db.session.refresh(ei_carvia)
    assert ei_carvia.local_cd == 'VICTORIO_MARCHEZINE'

    CarviaColetaService.editar_coleta(coleta, local_cd='TENENTE_MARQUES')
    db.session.flush()
    db.session.refresh(ei_carvia)
    db.session.refresh(ent_carvia)
    assert ei_carvia.local_cd == 'TENENTE_MARQUES'
    assert ent_carvia.local_cd == 'TENENTE_MARQUES'
