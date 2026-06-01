"""Integração Cíclico -> Confronto (spec §6.4): INV soma ajustes cíclicos do período."""
from datetime import datetime
from decimal import Decimal

from app.inventario.models import (
    InventarioBase, ContagemInventario, ContagemInventarioItem,
)
from app.inventario.services.confronto_service import ConfrontoService
from app.utils.timezone import agora_utc_naive


def _contagem(db, empresa, data_base, status, itens):
    """itens = [(location_name, cod, lote, ajuste_inventario)].

    O Confronto soma `ajuste_inventario` (coluna AJUSTE autoritativa), não `ajuste`.
    """
    c = ContagemInventario(
        codigo=f'CONT-{data_base.isoformat()}-{empresa}',
        empresa=empresa, data_base=data_base, status=status,
        criado_em=agora_utc_naive(),
    )
    db.session.add(c)
    db.session.flush()
    for loc, cod, lote, aj in itens:
        db.session.add(ContagemInventarioItem(
            contagem_id=c.id, location_name=loc, cod_produto=cod, lote=lote,
            company_id=1, contagem=Decimal('0'),
            ajuste=Decimal(str(aj)), ajuste_inventario=Decimal(str(aj)),
            classe='NORMAL',
        ))
    db.session.flush()
    return c


def test_produto_a_soma_ajuste_ciclico(db, ciclo):
    # ciclo.data_snapshot = 2026-05-16 (fixture). Baseline FB = 1000.
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4000001', empresa='FB', qtd=Decimal('1000')))
    # cíclico posterior: ajuste -100 (Lote 2/Local Y)
    _contagem(db, 'FB', datetime(2026, 5, 20, 10, 0), 'CONTABILIZADA',
              [('FB/Estoque', '4000001', 'L2', -100)])
    db.session.flush()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4000001')
    assert l['inv_fb'] == Decimal('900')
    assert l['inv_total'] == Decimal('900')


def test_regressao_sem_ciclico(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4000002', empresa='FB', qtd=Decimal('1000')))
    db.session.flush()
    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4000002')
    assert l['inv_fb'] == Decimal('1000')   # idêntico ao comportamento atual


def test_ignora_ciclico_anterior_a_baseline(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4000003', empresa='FB', qtd=Decimal('1000')))
    # cíclico ANTES de 2026-05-16 -> fora do período (não soma)
    _contagem(db, 'FB', datetime(2026, 5, 10, 10, 0), 'CONTABILIZADA',
              [('FB/Estoque', '4000003', 'L1', -100)])
    db.session.flush()
    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4000003')
    assert l['inv_fb'] == Decimal('1000')


def test_ignora_ciclico_nao_contabilizado(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4000004', empresa='FB', qtd=Decimal('1000')))
    _contagem(db, 'FB', datetime(2026, 5, 20, 10, 0), 'BASE_GERADA',
              [('FB/Estoque', '4000004', 'L1', -100)])
    db.session.flush()
    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4000004')
    assert l['inv_fb'] == Decimal('1000')


def test_confronto_usa_ajuste_inventario_nao_ajuste(db, ciclo):
    """Cenário 'semi-ajustado': o Odoo (qtd_esperada) divergiu do inventário, então
    `ajuste` (= contagem − qtd_esperada, p/ Odoo) ≠ `ajuste_inventario` (coluna AJUSTE,
    p/ Confronto). O Confronto deve usar ajuste_inventario.

    Baseline FB = 1000. Usuário contou 80 onde o Odoo (semi-ajustado) tinha 90 ⇒
    ajuste Odoo = -10, mas o delta real sobre o inventário é -20 (AJUSTE manual).
    INV deve ir a 980 (1000 - 20), NÃO a 990.
    """
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4000006', empresa='FB', qtd=Decimal('1000')))
    c = ContagemInventario(
        codigo='CONT-semiaj-FB', empresa='FB',
        data_base=datetime(2026, 5, 20, 10, 0), status='CONTABILIZADA',
        criado_em=agora_utc_naive(),
    )
    db.session.add(c)
    db.session.flush()
    db.session.add(ContagemInventarioItem(
        contagem_id=c.id, location_name='FB/Estoque', cod_produto='4000006', lote='L1',
        company_id=1, qtd_esperada=Decimal('90'), contagem=Decimal('80'),
        ajuste=Decimal('-10'),            # → Odoo (contagem − qtd_esperada)
        ajuste_inventario=Decimal('-20'), # → Confronto (coluna AJUSTE)
        classe='NORMAL',
    ))
    db.session.flush()
    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4000006')
    assert l['inv_fb'] == Decimal('980')      # usa ajuste_inventario (-20), não ajuste (-10)


def test_soma_so_na_empresa_da_contagem(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4000005', empresa='FB', qtd=Decimal('1000')))
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4000005', empresa='CD', qtd=Decimal('500')))
    _contagem(db, 'FB', datetime(2026, 5, 20, 10, 0), 'CONTABILIZADA',
              [('FB/Estoque', '4000005', 'L1', -100)])
    db.session.flush()
    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4000005')
    assert l['inv_fb'] == Decimal('900')    # FB recebe o ajuste
    assert l['inv_cd'] == Decimal('500')    # CD intocado
