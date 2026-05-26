"""Teste do ExportXlsxService."""
import io
import openpyxl
from decimal import Decimal
from app.inventario.models import InventarioBase
from app.inventario.services.export_xlsx_service import ExportXlsxService


def test_export_gera_6_abas(db, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('100'), nome_produto='PROD',
    ))
    db.session.flush()
    blob = ExportXlsxService.gerar(ciclo.id)
    assert isinstance(blob, bytes)
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True)
    nomes_esperados = {'Confronto', 'Ajustes_Manuais', 'Apontamentos_PA_Comp',
                       'Movimentacoes_Sistema', 'Estoque_Odoo_por_Empresa',
                       'Inventario_Base'}
    assert nomes_esperados.issubset(set(wb.sheetnames))
