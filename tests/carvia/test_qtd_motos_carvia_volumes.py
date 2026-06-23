"""`qtd_motos_carvia` / `qtd_motos_de_item` — fonte canonica de
`EmbarqueItem.volumes` (= qtd de motos) dos itens CarVia.

Diferente de `qtd_motos_por_lotes` (mapa, so itens-modelo), este helper usa
`max(chassis, Σ itens-modelo)` por NF (regra Portal/Gerencial) e tem fallback
para a cotacao (provisorio sem NF). Reusa as fixtures de
`test_motos_lote_service.py`.
"""
import uuid

from app import db as _db
from app.carvia.services.documentos.motos_lote_service import (
    qtd_motos_carvia, qtd_motos_de_item,
)
from tests.carvia.test_motos_lote_service import (
    _modelo, _nf, _cotacao, _pedido, _pedido_item, _cotacao_moto,
)


def _add_chassis(nf, modelo, n):
    """Adiciona N CarviaNfVeiculo (chassis) a uma NF."""
    from app.carvia.models.documentos import CarviaNfVeiculo
    for _ in range(n):
        _db.session.add(CarviaNfVeiculo(
            nf_id=nf.id, chassi='CH-' + uuid.uuid4().hex[:12],
            modelo=modelo.nome,
        ))
    _db.session.flush()


def _embarque_item(separacao_lote_id=None, nota_fiscal=None, carvia_cotacao_id=None):
    """EmbarqueItem transiente (nao persiste) — o helper so le 3 atributos."""
    from app.embarques.models import EmbarqueItem
    return EmbarqueItem(
        separacao_lote_id=separacao_lote_id,
        nota_fiscal=nota_fiscal,
        carvia_cotacao_id=carvia_cotacao_id,
    )


# --------------------------------------------------------------------------- #

def test_lote_nf_conta_motos_da_nf(db):
    modelo = _modelo()
    nf = _nf('800001', modelo, qtd=4)
    assert qtd_motos_carvia(separacao_lote_id=f'CARVIA-NF-{nf.id}') == 4


def test_lote_ped_conta_via_nf(db):
    modelo = _modelo()
    _nf('800010', modelo, qtd=3)
    ped = _pedido(_cotacao())
    _pedido_item(ped, qtd=3, numero_nf='800010', modelo_moto_id=None)
    assert qtd_motos_carvia(separacao_lote_id=f'CARVIA-PED-{ped.id}') == 3


def test_resolve_por_nota_fiscal_quando_lote_nao_resolve(db):
    """Item com lote PED sem itens mas com nota_fiscal preenchida resolve pela NF."""
    modelo = _modelo()
    _nf('800020', modelo, qtd=6)
    # lote inexistente / sem pedido-item -> cai no fallback por nota_fiscal
    assert qtd_motos_carvia(
        separacao_lote_id='CARVIA-PED-99999999', nota_fiscal='800020',
    ) == 6


def test_chassi_maior_que_item_usa_max(db):
    """A diferenca vs qtd_motos_por_lotes: NF com mais chassis que itens-modelo."""
    modelo = _modelo()
    nf = _nf('800030', modelo, qtd=2)   # item diz 2
    _add_chassis(nf, modelo, 5)          # mas ha 5 chassis fisicos
    assert qtd_motos_carvia(separacao_lote_id=f'CARVIA-NF-{nf.id}') == 5


def test_nf_cancelada_excluida(db):
    modelo = _modelo()
    _nf('800040', modelo, qtd=9, status='CANCELADA')
    _nf('800040', modelo, qtd=2, status='ATIVA')
    ped = _pedido(_cotacao())
    _pedido_item(ped, qtd=2, numero_nf='800040')
    assert qtd_motos_carvia(separacao_lote_id=f'CARVIA-PED-{ped.id}') == 2


def test_fallback_cotacao_sem_nf(db):
    """Provisorio (sem NF): cai na qtd_total_motos da cotacao via carvia_cotacao_id."""
    modelo = _modelo()
    cot = _cotacao(tipo_material='MOTO')
    _cotacao_moto(cot, modelo, qtd=7)
    assert qtd_motos_carvia(carvia_cotacao_id=cot.id) == 7
    assert qtd_motos_carvia(separacao_lote_id=f'CARVIA-{cot.id}') == 7


def test_carga_geral_retorna_zero(db):
    cot = _cotacao(tipo_material='CARGA_GERAL')
    assert qtd_motos_carvia(carvia_cotacao_id=cot.id) == 0


def test_sem_dados_retorna_zero(db):
    assert qtd_motos_carvia() == 0
    assert qtd_motos_carvia(separacao_lote_id='LOTE_NACOM_123') == 0
    assert qtd_motos_carvia(separacao_lote_id='CARVIA-NF-naoint') == 0


def test_qtd_motos_de_item_wrapper(db):
    modelo = _modelo()
    nf = _nf('800050', modelo, qtd=3)
    item = _embarque_item(separacao_lote_id=f'CARVIA-NF-{nf.id}')
    assert qtd_motos_de_item(item) == 3
    assert qtd_motos_de_item(None) == 0
