"""Testes do ContagemService: classificação, cálculo e regra por-quant."""
import io
from decimal import Decimal

import openpyxl
import pytest

from app.inventario.models import ContagemInventario, ContagemInventarioItem
from app.inventario.services.contagem_service import (
    classificar, calcular_linha, ContagemService,
)
from app.utils.timezone import agora_utc_naive

ZERO = Decimal('0')


# ----------------------------------------------------------------- puros
def test_classificar_sem_ajuste():
    assert classificar(Decimal('100'), ZERO, ZERO, False) == 'SEM_AJUSTE'


def test_classificar_lote_novo():
    assert classificar(ZERO, ZERO, Decimal('50'), True) == 'LOTE_NOVO'


def test_classificar_negativo():
    assert classificar(Decimal('-23'), ZERO, Decimal('23'), False) == 'NEGATIVO'


def test_classificar_reserva_fantasma():
    assert classificar(Decimal('14'), Decimal('14'), Decimal('-14'), False) == 'RESERVA_FANTASMA'


def test_classificar_normal():
    assert classificar(Decimal('100'), ZERO, Decimal('-30'), False) == 'NORMAL'


def test_calcular_linha_vazio_vira_zero():
    item = {'qtd_esperada': Decimal('220'), 'reservado_esperado': ZERO}
    r = calcular_linha(item, None)
    assert r['contagem'] == ZERO
    assert r['ajuste'] == Decimal('-220')
    assert r['classe'] == 'NORMAL'


def test_calcular_linha_lote_novo():
    r = calcular_linha(None, Decimal('145.44'))
    assert r['is_nova'] is True
    assert r['qtd_esperada'] == ZERO
    assert r['ajuste'] == Decimal('145.44')
    assert r['classe'] == 'LOTE_NOVO'


# ----------------------------------------------------------- integração DB
def _xlsx(linhas):
    """linhas = [(location_name, cod, lote, contagem|None)]."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['location_name', 'cod', 'lote', 'CONTAGEM'])
    for ln in linhas:
        ws.append(list(ln))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _contagem_base(db, itens):
    """itens = [(location_name, cod, lote, qtd_esperada, reservado_esperado)]."""
    c = ContagemInventario(
        codigo=f'CONT-T-{agora_utc_naive().timestamp()}', empresa='FB',
        data_base=agora_utc_naive(), status='BASE_GERADA',
        criado_em=agora_utc_naive(),
    )
    db.session.add(c)
    db.session.flush()
    for loc, cod, lote, qe, re_ in itens:
        db.session.add(ContagemInventarioItem(
            contagem_id=c.id, location_name=loc, cod_produto=cod, lote=lote,
            company_id=1, qtd_esperada=Decimal(str(qe)),
            reservado_esperado=Decimal(str(re_)),
        ))
    db.session.flush()
    return c


def test_regra_por_quant_presente_ausente_vazio(db):
    c = _contagem_base(db, [
        ('FB/Estoque', '4000001', 'L1', 500, 0),
        ('FB/Estoque', '4000001', 'L2', 500, 0),
        ('FB/Estoque', '4000001', 'L3', 500, 0),
        ('FB/Estoque', '4000001', 'L4', 500, 0),
        ('FB/Estoque', '4000001', 'L5', 500, 0),
    ])
    # planilha: L1=500 (bate), L2 vazio (=0), L3=400; L4/L5 ausentes
    ContagemService.confirmar_reupload(c.id, _xlsx([
        ('FB/Estoque', '4000001', 'L1', 500),
        ('FB/Estoque', '4000001', 'L2', None),
        ('FB/Estoque', '4000001', 'L3', 400),
    ]))
    db.session.flush()
    items = {it.lote: it for it in
             ContagemInventarioItem.query.filter_by(contagem_id=c.id)}
    assert items['L1'].ajuste == Decimal('0')        # bate
    assert items['L2'].ajuste == Decimal('-500')     # vazio -> 0 -> zera
    assert items['L3'].ajuste == Decimal('-100')     # 400-500
    # ausentes da planilha -> intocados
    assert items['L4'].contagem is None and items['L4'].ajuste == Decimal('0')
    assert items['L5'].contagem is None


def test_lote_novo_criado(db):
    c = _contagem_base(db, [('FB/Estoque', '4000001', 'L1', 500, 0)])
    ContagemService.confirmar_reupload(c.id, _xlsx([
        ('FB/Estoque', '4000001', 'L1', 500),
        ('FB/Estoque', '4000001', 'LX', 30),   # lote novo
    ]))
    db.session.flush()
    items = {it.lote: it for it in
             ContagemInventarioItem.query.filter_by(contagem_id=c.id)}
    assert 'LX' in items
    assert items['LX'].classe == 'LOTE_NOVO'
    assert items['LX'].ajuste == Decimal('30')
    assert items['LX'].qtd_esperada == Decimal('0')


def test_reserva_fantasma(db):
    c = _contagem_base(db, [('FB/Estoque', '101001001', 'MIGRACAO', 14, 14)])
    ContagemService.confirmar_reupload(c.id, _xlsx([
        ('FB/Estoque', '101001001', 'MIGRACAO', 0),
    ]))
    db.session.flush()
    it = ContagemInventarioItem.query.filter_by(contagem_id=c.id).first()
    assert it.ajuste == Decimal('-14')
    assert it.classe == 'RESERVA_FANTASMA'


def test_negativo(db):
    c = _contagem_base(db, [('FB/Pré-Produção/Linha Balde', '201030023', '2507/24', -211, 0)])
    ContagemService.confirmar_reupload(c.id, _xlsx([
        ('FB/Pré-Produção/Linha Balde', '201030023', '2507/24', 0),
    ]))
    db.session.flush()
    it = ContagemInventarioItem.query.filter_by(contagem_id=c.id).first()
    assert it.ajuste == Decimal('211')   # 0 - (-211)
    assert it.classe == 'NEGATIVO'


def test_status_vira_contabilizada_e_resumo(db):
    c = _contagem_base(db, [
        ('FB/Estoque', '4000001', 'L1', 500, 0),
        ('FB/Estoque', '4000001', 'L2', 500, 0),
    ])
    ContagemService.confirmar_reupload(c.id, _xlsx([
        ('FB/Estoque', '4000001', 'L1', 400),   # ajuste -100
        ('FB/Estoque', '4000001', 'L2', 500),   # bate
    ]))
    db.session.flush()
    assert c.status == 'CONTABILIZADA'
    assert c.tot_com_ajuste == 1
    assert c.tot_ajuste_neg == Decimal('-100')


def test_contagem_negativa_rejeitada(db):
    c = _contagem_base(db, [('FB/Estoque', '4000001', 'L1', 500, 0)])
    with pytest.raises(ValueError):
        ContagemService.preview_reupload(c.id, _xlsx([
            ('FB/Estoque', '4000001', 'L1', -5),
        ]))


def test_preview_nao_grava(db):
    c = _contagem_base(db, [('FB/Estoque', '4000001', 'L1', 500, 0)])
    ContagemService.preview_reupload(c.id, _xlsx([
        ('FB/Estoque', '4000001', 'L1', 0),
    ]))
    db.session.flush()
    it = ContagemInventarioItem.query.filter_by(contagem_id=c.id).first()
    assert it.contagem is None        # preview não gravou
    assert c.status == 'BASE_GERADA'
