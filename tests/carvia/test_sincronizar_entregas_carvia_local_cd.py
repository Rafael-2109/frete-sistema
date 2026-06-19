"""Fix PED-281-1: o sincronizador de entregas CarVia reconcilia o local_cd do
EmbarqueItem CarVia com o da fonte (CarviaNf).

Contexto: a propagacao da Coleta casa o EmbarqueItem POR NF (`nota_fiscal == numero_nf`).
Um item provisorio (lote `CARVIA-PED-*`) que recebe a NF DEPOIS de a Coleta ja ter
propagado nunca era alcancado -> ficava com o default VM divergente da NF/coleta.
`sincronizar_entrega_carvia_por_nf` roda em TODOS os caminhos de anexacao de NF
(portaria, form de embarque, import) e agora alinha tambem o EmbarqueItem.
"""
import uuid

from app import db as _db
from app.utils.sincronizar_entregas_carvia import sincronizar_entrega_carvia_por_nf


def _criar_nf(numero, local_cd='TENENTE_MARQUES'):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='12345678000199', nome_emitente='EMIT',
        cnpj_destinatario='98765432000155', nome_destinatario='CLIENTE REAL LTDA',
        cidade_destinatario='Sao Paulo', uf_destinatario='SP', valor_total=1000,
        tipo_fonte='MANUAL', status='ATIVA', local_cd=local_cd, criado_por='test@bot',
    )
    _db.session.add(nf)
    _db.session.flush()
    return nf


def _criar_embarque_item(numero_nf, lote, local_cd='VICTORIO_MARCHEZINE'):
    from app.embarques.models import Embarque, EmbarqueItem
    from app.utils.timezone import agora_utc_naive
    numero_emb = int(uuid.uuid4().int % 9_000_000) + 1_000_000
    emb = Embarque(numero=numero_emb, status='ativo', criado_em=agora_utc_naive())
    _db.session.add(emb)
    _db.session.flush()
    ei = EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id=lote, pedido='P1', cliente='X',
        nota_fiscal=numero_nf, status='ativo', uf_destino='SP', cidade_destino='X',
        local_cd=local_cd,
    )
    _db.session.add(ei)
    _db.session.flush()
    return ei


def test_sincronizar_alinha_embarque_item_provisorio_divergente(db):
    """Item provisorio (CARVIA-PED-*) com NF anexada e local_cd VM divergente da NF TM:
    apos sincronizar, o item vira TM (mesmo da fonte). Reproduz o bug PED-281-1."""
    nf = _criar_nf('550044', local_cd='TENENTE_MARQUES')
    ei = _criar_embarque_item('550044', lote=f'CARVIA-PED-{nf.id}', local_cd='VICTORIO_MARCHEZINE')

    sincronizar_entrega_carvia_por_nf('550044')
    db.session.refresh(ei)

    assert ei.local_cd == 'TENENTE_MARQUES'


def test_sincronizar_nao_toca_item_nacom_da_mesma_nf(db):
    """Item Nacom (lote nao-CARVIA) com a MESMA NF nao pode ser alterado (R1)."""
    _criar_nf('550055', local_cd='TENENTE_MARQUES')
    ei_carvia = _criar_embarque_item('550055', lote='CARVIA-PED-999', local_cd='VICTORIO_MARCHEZINE')
    ei_nacom = _criar_embarque_item('550055', lote='LOTE-NACOM', local_cd='VICTORIO_MARCHEZINE')

    sincronizar_entrega_carvia_por_nf('550055')
    db.session.refresh(ei_carvia)
    db.session.refresh(ei_nacom)

    assert ei_carvia.local_cd == 'TENENTE_MARQUES'
    assert ei_nacom.local_cd == 'VICTORIO_MARCHEZINE'


def test_sincronizar_idempotente_quando_ja_alinhado(db):
    """Item ja no mesmo CD da NF: sincronizar nao muda nada (idempotente)."""
    _criar_nf('550066', local_cd='TENENTE_MARQUES')
    ei = _criar_embarque_item('550066', lote='CARVIA-NF-550066', local_cd='TENENTE_MARQUES')

    sincronizar_entrega_carvia_por_nf('550066')
    db.session.refresh(ei)

    assert ei.local_cd == 'TENENTE_MARQUES'
