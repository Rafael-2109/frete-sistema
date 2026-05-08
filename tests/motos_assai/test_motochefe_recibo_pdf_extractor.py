import os
import pytest
from app.motos_assai.services.parsers.motochefe_recibo_pdf_extractor import (
    MotochefeReciboPdfExtractor,
)


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'recibo_motochefe_exemplo.pdf')


def test_fixture_exists():
    assert os.path.exists(FIXTURE)


def test_extract_retorna_chassis():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    assert len(items) > 50, f'Esperava >=50 chassis (canon: 115), veio {len(items)}'


def test_header_data_recibo():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    assert items
    datas = {i['data_recibo'] for i in items if i.get('data_recibo')}
    assert '05/05/2026' in datas


def test_header_equipe_haroldo_sp():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    equipes = {i.get('equipe') for i in items if i.get('equipe')}
    assert any('HAROLDO' in str(e or '') for e in equipes)


def test_chassis_uppercase_e_distintos():
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    chassis = [i['chassi'] for i in items]
    # Uppercase
    assert all(c == c.upper() for c in chassis)
    # Distintos (sem duplicatas)
    assert len(chassis) == len(set(chassis)), 'Chassis duplicados'


def test_modelo_texto_dot_e_mia():
    """Recibo HAROLDO SP tem DOT 1000W e MIA 1000W."""
    e = MotochefeReciboPdfExtractor()
    items = e.extract(FIXTURE)
    modelos = {i.get('modelo_texto', '').upper() for i in items}
    assert any('DOT' in m for m in modelos)
    assert any('MIA' in m for m in modelos)
