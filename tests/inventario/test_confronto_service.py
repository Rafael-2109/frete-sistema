"""Testes do ConfrontoService."""
from datetime import datetime
from decimal import Decimal
from app.inventario.models import (
    InventarioBase, AjusteManualInventario, InventarioSnapshotOdoo,
)
from app.estoque.models import MovimentacaoEstoque
from app.inventario.services.confronto_service import ConfrontoService


def _add_mov(db, cod, tipo, local, qtd, data='2026-05-20'):
    m = MovimentacaoEstoque(
        cod_produto=cod, nome_produto=f'PROD {cod}',
        data_movimentacao=datetime.fromisoformat(data).date(),
        tipo_movimentacao=tipo, local_movimentacao=local,
        qtd_movimentacao=Decimal(str(qtd)),
        tipo_origem='ODOO',
        criado_em=datetime.fromisoformat(data),
        atualizado_em=datetime.fromisoformat(data),
        ativo=True,
    )
    db.session.add(m)
    return m


def test_linha_so_com_inventario_base(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('100'), nome_produto='PROD 4320147'))
    db.session.flush()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4320147')
    assert l['inv_fb'] == Decimal('100')
    assert l['inv_cd'] == Decimal('0')
    assert l['inv_lf'] == Decimal('0')
    assert l['inv_total'] == Decimal('100')


def test_linha_com_compras_venda_consumo_producao(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB', qtd=Decimal('100')))
    _add_mov(db, '4320147', 'ENTRADA', 'COMPRA', 50)
    _add_mov(db, '4320147', 'ENTRADA', 'REVERSAO', 5)
    _add_mov(db, '4320147', 'FATURAMENTO', 'VENDA', -20)
    _add_mov(db, '4320147', 'CONSUMO', 'LF', -30)
    _add_mov(db, '4320147', 'PRODUÇÃO', '1106', 80)
    db.session.flush()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4320147')
    # mov_compras = SOMENTE ENTRADA+COMPRA (50). REVERSAO=5 NAO conta
    # (fix 2026-05-28: alinhar com Odoo._baixar_compras que filtra
    # PO partner externo, excluindo inter-company/devolucao).
    assert l['compras'] == Decimal('50')
    assert l['vendas'] == Decimal('-20')
    assert l['consumo'] == Decimal('-30')
    assert l['producao'] == Decimal('80')


def test_linha_com_snapshot_odoo(db, ciclo):
    db.session.add(InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='4320147',
        estoque_fb=Decimal('150'), estoque_cd=Decimal('50'),
        estoque_lf=Decimal('30'), pa_qtd=Decimal('80'),
        componente_qtd=Decimal('40'), compras_qtd=Decimal('50'),
    ))
    db.session.flush()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4320147')
    assert l['odoo'] == Decimal('230')
    assert l['est_fb'] == Decimal('150')
    assert l['pa'] == Decimal('80')
    assert l['componente'] == Decimal('-40')


def test_linha_com_ajuste_manual(db, ciclo):
    db.session.add(AjusteManualInventario(
        ciclo_id=ciclo.id, cod_produto='208000041',
        local='CD', qtd=Decimal('2120.8'), tipo_ajuste='POSITIVO',
        observacao='Ajuste pos-recontagem',
    ))
    db.session.flush()
    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '208000041')
    assert l['ajuste_local'] == 'CD'
    assert l['ajuste_qtd'] == Decimal('2120.8')
    assert l['ajuste_tipo'] == 'POSITIVO'


def test_calculo_mov_e_diferencas(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4999999', empresa='FB', qtd=Decimal('100')))
    db.session.add(InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='4999999',
        estoque_fb=Decimal('150'), pa_qtd=Decimal('80'),
        componente_qtd=Decimal('40'),
    ))
    _add_mov(db, '4999999', 'ENTRADA', 'COMPRA', 50)
    db.session.flush()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4999999')
    # MOV = inv_total(100) + compras(50, ENTRADA+COMPRA) + pa(80) + componente(-40) = 190
    assert l['mov'] == Decimal('190')
    # odoo(150) - mov(190) = -40
    assert l['odoo_menos_mov'] == Decimal('-40')
