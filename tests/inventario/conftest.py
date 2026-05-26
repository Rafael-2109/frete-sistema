"""Fixtures compartilhadas para testes do módulo inventario."""
import io
import pytest
import openpyxl
from datetime import date
from app.inventario.models import CicloInventario


@pytest.fixture
def ciclo(db):
    c = CicloInventario(
        codigo='INV-TESTE-2026-05',
        data_snapshot=date(2026, 5, 16),
        descricao='Ciclo de teste',
        status='ATIVO',
        criado_por='pytest',
    )
    db.session.add(c)
    db.session.flush()
    return c


def _make_test_xlsx(rows_por_aba):
    """Cria xlsx em memória com abas FB/CD/LF + dados.

    rows_por_aba = {'FB': [(cod, lote, qtd), ...], ...}
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for aba, rows in rows_por_aba.items():
        ws = wb.create_sheet(aba)
        ws.append(['CODIGO', 'LOTE', 'QTD'])
        for r in rows:
            ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@pytest.fixture
def xlsx_valido():
    return _make_test_xlsx({
        'FB': [('4320147', '139/26', 100), ('208000041', '', 50)],
        'CD': [('4320147', '139/26', 200), ('103000037', '023/26', 75.5)],
        'LF': [('4320147', '139/26', 50)],
    })


@pytest.fixture
def xlsx_com_invalidos():
    """Inclui código que começa com letra (deve pular) e qtd negativa."""
    return _make_test_xlsx({
        'FB': [('CHAVE-X', '', 10), ('4320147', '139/26', 100)],
        'CD': [('208000041', '', -5)],
        'LF': [],
    })
