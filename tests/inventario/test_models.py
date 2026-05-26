"""Testes dos modelos do módulo inventario."""
from datetime import date
from decimal import Decimal
import sqlalchemy.exc
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo,
)


def test_criar_ciclo_inventario(db):
    c = CicloInventario(
        codigo='INV-2026-05-TEST',
        data_snapshot=date(2026, 5, 16),
        descricao='Ciclo maio',
        status='ATIVO',
    )
    db.session.add(c)
    db.session.flush()
    assert c.id is not None
    assert c.criado_em is not None


def test_inventario_base_unique_constraint(db, ciclo):
    b1 = InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('100.000'),
    )
    db.session.add(b1)
    db.session.flush()

    b2 = InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('200.000'),
    )
    db.session.add(b2)
    try:
        db.session.flush()
        assert False, 'esperava IntegrityError'
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()


def test_ajuste_manual_basico(db, ciclo):
    a = AjusteManualInventario(
        ciclo_id=ciclo.id, cod_produto='208000041',
        nome_produto='FILME TERMO ENCOLHIVEL', local='CD',
        qtd=Decimal('2120.800'), tipo_ajuste='POSITIVO',
        observacao='Ajuste pos-recontagem',
    )
    db.session.add(a)
    db.session.flush()
    assert a.id is not None
    assert a.atualizado_em is not None


def test_snapshot_odoo_unique_constraint(db, ciclo):
    s1 = InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='4320147',
        estoque_fb=Decimal('500'), estoque_cd=Decimal('0'), estoque_lf=Decimal('200'),
    )
    db.session.add(s1)
    db.session.flush()

    s2 = InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='4320147',
        estoque_fb=Decimal('999'),
    )
    db.session.add(s2)
    try:
        db.session.flush()
        assert False, 'esperava IntegrityError'
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
