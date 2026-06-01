"""Exportação Excel da Contagem Cíclica.

- excel_base: planilha-BASE para o usuário preencher. Duas colunas editáveis, com
  semânticas DISTINTAS (comentários de célula explicam no header):
    • CONTAGEM → físico contado; gera o `ajuste` (= contagem − qtd) p/ aplicar no Odoo.
    • AJUSTE   → autoritativo; delta somado ao último inventário na coluna INV/MOV
      do Confronto (`ajuste_inventario`). Vazio = sem ajuste. Independe do Odoo.
- excel_relatorio: relatório/plano por quant. Coluna `ajuste` (→ Odoo, plano que as
  skills gestor-estoque-odoo consomem) E `ajuste_inventario` (→ Confronto).

Engine: xlsxwriter (já em uso pelos scripts CLI).
"""
import io
from decimal import Decimal

import xlsxwriter

from app.inventario.models import ContagemInventario, ContagemInventarioItem


def _f(v):
    """Decimal/None -> float para o xlsxwriter."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v


class ContagemExportService:

    @staticmethod
    def _itens(contagem_id: int):
        return (ContagemInventarioItem.query
                .filter_by(contagem_id=contagem_id)
                .order_by(ContagemInventarioItem.location_name,
                          ContagemInventarioItem.cod_produto,
                          ContagemInventarioItem.lote)
                .all())

    @staticmethod
    def excel_base(contagem: ContagemInventario) -> bytes:
        """Planilha-base: location_name, local_tipo, cod, nome_produto, lote,
        qtd, reservado, disponivel, AJUSTE(vazio), CONTAGEM(vazio)."""
        itens = ContagemExportService._itens(contagem.id)
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Planilha1')
        fmt_hdr = wb.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        fmt_num = wb.add_format({'num_format': '#,##0.000'})
        fmt_fill = wb.add_format({'bg_color': '#FFF2CC', 'num_format': '#,##0.000'})

        headers = ['location_name', 'local_tipo', 'cod', 'nome_produto', 'lote',
                   'qtd', 'reservado', 'disponivel', 'AJUSTE', 'CONTAGEM']
        for c, h in enumerate(headers):
            ws.write(0, c, h, fmt_hdr)
        # Comentários de célula deixam a semântica das 2 colunas inequívoca.
        ws.write_comment(0, 8,
                         'AJUSTE (autoritativo): delta a SOMAR ao último inventário '
                         '— vai para a coluna INV/MOV do Confronto. Vazio = sem '
                         'ajuste. Aceita negativo. NÃO é calculado da contagem.')
        ws.write_comment(0, 9,
                         'CONTAGEM: quantidade física contada. Gera o ajuste a '
                         'aplicar no Odoo (= CONTAGEM − qtd). Vazio = 0 (zera o quant).')

        for r, it in enumerate(itens, start=1):
            qtd = _f(it.qtd_esperada) or 0
            res = _f(it.reservado_esperado) or 0
            ws.write_string(r, 0, it.location_name or '')
            ws.write_string(r, 1, it.local_tipo or '')
            ws.write_string(r, 2, str(it.cod_produto or ''))
            ws.write_string(r, 3, it.nome_produto or '')
            ws.write_string(r, 4, it.lote or '')
            ws.write_number(r, 5, qtd, fmt_num)
            ws.write_number(r, 6, res, fmt_num)
            ws.write_number(r, 7, qtd - res, fmt_num)
            ws.write_blank(r, 8, None, fmt_fill)    # AJUSTE → ajuste_inventario (Confronto)
            ws.write_blank(r, 9, None, fmt_fill)    # CONTAGEM → físico (plano Odoo)

        ws.set_column('A:A', 30)
        ws.set_column('B:B', 12)
        ws.set_column('C:C', 11)
        ws.set_column('D:D', 42)
        ws.set_column('E:E', 18)
        ws.set_column('F:J', 13)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(itens), len(headers) - 1)
        wb.close()
        buf.seek(0)
        return buf.getvalue()

    @staticmethod
    def excel_relatorio(contagem: ContagemInventario) -> bytes:
        """Relatório/plano: só linhas inventariadas (contagem != NULL), por quant,
        com ajuste e classe. Linhas SEM_AJUSTE incluídas para auditoria."""
        itens = [it for it in ContagemExportService._itens(contagem.id)
                 if it.contagem is not None]
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Plano')
        fmt_hdr = wb.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        fmt_num = wb.add_format({'num_format': '#,##0.000'})
        fmt_neg = wb.add_format({'num_format': '#,##0.000', 'font_color': '#C00000'})
        fmt_pos = wb.add_format({'num_format': '#,##0.000', 'font_color': '#006100'})

        # `ajuste` (→ Odoo, define a classe) e `ajuste_inventario` (→ Confronto)
        # são colunas distintas (não confundir).
        headers = ['location_name', 'location_id', 'local_tipo', 'cod', 'nome_produto',
                   'lote', 'company_id', 'qtd_esperada', 'reservado_esperado',
                   'contagem', 'ajuste', 'ajuste_inventario', 'classe']
        for c, h in enumerate(headers):
            ws.write(0, c, h, fmt_hdr)
        ws.write_comment(0, 10, 'ajuste = contagem − qtd_esperada → aplicar no Odoo.')
        ws.write_comment(0, 11, 'ajuste_inventario = coluna AJUSTE → soma na coluna '
                                'INV/MOV do Confronto.')

        def _fmt_signed(v):
            return fmt_neg if v < 0 else (fmt_pos if v > 0 else fmt_num)

        for r, it in enumerate(itens, start=1):
            aj = _f(it.ajuste) or 0
            aji = _f(it.ajuste_inventario) or 0
            ws.write_string(r, 0, it.location_name or '')
            ws.write(r, 1, it.location_id)
            ws.write_string(r, 2, it.local_tipo or '')
            ws.write_string(r, 3, str(it.cod_produto or ''))
            ws.write_string(r, 4, it.nome_produto or '')
            ws.write_string(r, 5, it.lote or '')
            ws.write(r, 6, it.company_id)
            ws.write_number(r, 7, _f(it.qtd_esperada) or 0, fmt_num)
            ws.write_number(r, 8, _f(it.reservado_esperado) or 0, fmt_num)
            ws.write_number(r, 9, _f(it.contagem) or 0, fmt_num)
            ws.write_number(r, 10, aj, _fmt_signed(aj))
            ws.write_number(r, 11, aji, _fmt_signed(aji))
            ws.write_string(r, 12, it.classe or '')

        ws.set_column('A:A', 30)
        ws.set_column('B:C', 11)
        ws.set_column('D:D', 11)
        ws.set_column('E:E', 42)
        ws.set_column('F:F', 18)
        ws.set_column('G:G', 11)
        ws.set_column('H:L', 14)
        ws.set_column('M:M', 18)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(itens), len(headers) - 1)
        wb.close()
        buf.seek(0)
        return buf.getvalue()
