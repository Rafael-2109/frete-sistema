import os
import pytest
from app.motos_assai.services.parsers.motochefe_recibo_xlsx_extractor import (
    MotochefeReciboXlsxExtractor,
)

FIXTURE_XLSX = os.path.join(os.path.dirname(__file__), 'fixtures', 'recibo_motochefe_exemplo.xlsx')
FIXTURE_SKIP = not os.path.exists(FIXTURE_XLSX)


@pytest.mark.skipif(FIXTURE_SKIP, reason='Fixture XLSX não presente — rodar generate_xlsx_fixture.py')
def test_fixture_xlsx_exists():
    assert os.path.exists(FIXTURE_XLSX)


@pytest.mark.skipif(FIXTURE_SKIP, reason='Fixture XLSX não presente')
def test_xlsx_extract_retorna_chassis():
    e = MotochefeReciboXlsxExtractor()
    items = e.extract(FIXTURE_XLSX)
    assert len(items) > 50, f'Esperava >=50 chassis (canon: 115), veio {len(items)}'


@pytest.mark.skipif(FIXTURE_SKIP, reason='Fixture XLSX não presente')
def test_xlsx_header_data_recibo():
    e = MotochefeReciboXlsxExtractor()
    items = e.extract(FIXTURE_XLSX)
    assert items
    datas = {i['data_recibo'] for i in items if i.get('data_recibo')}
    assert '05/05/2026' in datas


@pytest.mark.skipif(FIXTURE_SKIP, reason='Fixture XLSX não presente')
def test_xlsx_chassis_uppercase_e_distintos():
    e = MotochefeReciboXlsxExtractor()
    items = e.extract(FIXTURE_XLSX)
    chassis = [i['chassi'] for i in items]
    assert all(c == c.upper() for c in chassis)
    assert len(chassis) == len(set(chassis)), 'Chassis duplicados'


@pytest.mark.skipif(FIXTURE_SKIP, reason='Fixture XLSX não presente')
def test_xlsx_modelo_texto_dot_e_mia():
    """XLSX gerado a partir do recibo HAROLDO SP tem DOT 1000W e MIA 1000W."""
    e = MotochefeReciboXlsxExtractor()
    items = e.extract(FIXTURE_XLSX)
    modelos = {i.get('modelo_texto', '').upper() for i in items}
    assert any('DOT' in m for m in modelos)
    assert any('MIA' in m for m in modelos)


@pytest.mark.skipif(FIXTURE_SKIP, reason='Fixture XLSX não presente')
def test_xlsx_cnpj_extraido():
    e = MotochefeReciboXlsxExtractor()
    items = e.extract(FIXTURE_XLSX)
    assert items
    cnpjs = {i.get('cnpj_motochefe') for i in items if i.get('cnpj_motochefe')}
    assert cnpjs, 'Nenhum CNPJ extraído do XLSX'
    # CNPJ numérico (sem formatação)
    for cnpj in cnpjs:
        assert cnpj.isdigit(), f'CNPJ não é numérico: {cnpj}'


@pytest.mark.skipif(FIXTURE_SKIP, reason='Fixture XLSX não presente')
def test_xlsx_total_motos_declarado():
    e = MotochefeReciboXlsxExtractor()
    items = e.extract(FIXTURE_XLSX)
    assert items
    totais = {i.get('total_motos_declarado') for i in items if i.get('total_motos_declarado')}
    assert totais, 'total_motos_declarado não extraído'
    assert max(totais) >= 50
