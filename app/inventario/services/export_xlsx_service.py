"""Export do Relatório de Confronto em XLSX (6 abas)."""
import io
import xlsxwriter
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo,
)
from app.inventario.services.confronto_service import ConfrontoService
from app.estoque.models import MovimentacaoEstoque


HEADER_FMT = {'bold': True, 'bg_color': '#E0E0E0', 'border': 1}
NUM_FMT = '#,##0.000'
DIFF_FMT_RED = {'num_format': NUM_FMT, 'bg_color': '#FFE6E6'}


class ExportXlsxService:

    @staticmethod
    def gerar(ciclo_id: int) -> bytes:
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        hfmt = wb.add_format(HEADER_FMT)
        nfmt = wb.add_format({'num_format': NUM_FMT})
        rfmt = wb.add_format(DIFF_FMT_RED)

        # Aba 1: Confronto
        ws = wb.add_worksheet('Confronto')
        cols = ['cod', 'produto', 'FB', 'CD', 'LF', 'TOTAL', 'COMPRAS',
                'PA', 'COMPONENTE', 'VENDAS', 'CONSUMO', 'PRODUCAO',
                'AJUSTE_LOCAL', 'AJUSTE_QTD', 'AJUSTE_TIPO',
                'ODOO', 'MOV', 'SIST', 'ODOO-MOV', 'SIST-MOV',
                'ODOO_FB', 'ODOO_CD', 'ODOO_LF',
                # NOVO 2026-05-28: estoque interno (sem transit) + em transit por destino
                'ODOO_FB_INTERNO', 'ODOO_CD_INTERNO', 'ODOO_LF_INTERNO',
                'EM_TRANSITO_FB', 'EM_TRANSITO_CD', 'EM_TRANSITO_LF',
                'EM_TRANSITO_TOTAL']
        for i, c in enumerate(cols):
            ws.write(0, i, c, hfmt)
        linhas = ConfrontoService.montar_linhas(ciclo_id)
        for r, l in enumerate(linhas, start=1):
            ws.write(r, 0, l['cod_produto'])
            ws.write(r, 1, l.get('nome_produto') or '')
            ws.write_number(r, 2, float(l['inv_fb']), nfmt)
            ws.write_number(r, 3, float(l['inv_cd']), nfmt)
            ws.write_number(r, 4, float(l['inv_lf']), nfmt)
            ws.write_number(r, 5, float(l['inv_total']), nfmt)
            ws.write_number(r, 6, float(l['compras']), nfmt)
            ws.write_number(r, 7, float(l['pa']), nfmt)
            ws.write_number(r, 8, float(l['componente']), nfmt)
            ws.write_number(r, 9, float(l['vendas']), nfmt)
            ws.write_number(r, 10, float(l['consumo']), nfmt)
            ws.write_number(r, 11, float(l['producao']), nfmt)
            ws.write(r, 12, l.get('ajuste_local') or '')
            if l.get('ajuste_qtd') is not None:
                ws.write_number(r, 13, float(l['ajuste_qtd']), nfmt)
            ws.write(r, 14, l.get('ajuste_tipo') or '')
            ws.write_number(r, 15, float(l['odoo']), nfmt)
            ws.write_number(r, 16, float(l['mov']), nfmt)
            ws.write_number(r, 17, float(l['sist']), nfmt)
            d1 = float(l['odoo_menos_mov'])
            d2 = float(l['sist_menos_mov'])
            ws.write_number(r, 18, d1, rfmt if abs(d1) > 1 else nfmt)
            ws.write_number(r, 19, d2, rfmt if abs(d2) > 1 else nfmt)
            # ODOO_FB/CD/LF agora refletem interno+em_transito (consistente com tela)
            ws.write_number(r, 20, float(l.get('est_fb_total', l['est_fb'])), nfmt)
            ws.write_number(r, 21, float(l.get('est_cd_total', l['est_cd'])), nfmt)
            ws.write_number(r, 22, float(l.get('est_lf_total', l['est_lf'])), nfmt)
            # NOVO 2026-05-28: 7 colunas — interno isolado + em transit detalhado
            ws.write_number(r, 23, float(l['est_fb']), nfmt)
            ws.write_number(r, 24, float(l['est_cd']), nfmt)
            ws.write_number(r, 25, float(l['est_lf']), nfmt)
            ws.write_number(r, 26, float(l.get('em_transito_fb') or 0), nfmt)
            ws.write_number(r, 27, float(l.get('em_transito_cd') or 0), nfmt)
            ws.write_number(r, 28, float(l.get('em_transito_lf') or 0), nfmt)
            ws.write_number(r, 29, float(l.get('em_transito_total') or 0), nfmt)
        ws.freeze_panes(1, 2)

        # Aba 2: Ajustes Manuais
        ws2 = wb.add_worksheet('Ajustes_Manuais')
        ws2.write_row(0, 0, ['cod', 'produto', 'local', 'qtd', 'tipo',
                              'observacao', 'criado_em', 'criado_por'], hfmt)
        ajs = AjusteManualInventario.query.filter_by(ciclo_id=ciclo_id).all()
        for r, a in enumerate(ajs, start=1):
            ws2.write(r, 0, a.cod_produto)
            ws2.write(r, 1, a.nome_produto or '')
            ws2.write(r, 2, a.local or '')
            ws2.write_number(r, 3, float(a.qtd or 0), nfmt)
            ws2.write(r, 4, a.tipo_ajuste or '')
            ws2.write(r, 5, a.observacao or '')
            ws2.write(r, 6, a.criado_em.isoformat() if a.criado_em else '')
            ws2.write(r, 7, a.criado_por or '')

        # Aba 3: Apontamentos
        ws3 = wb.add_worksheet('Apontamentos_PA_Comp')
        ws3.write_row(0, 0, ['cod', 'nome', 'pa_qtd', 'componente_qtd',
                              'compras_qtd_odoo'], hfmt)
        snaps = InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo_id).all()
        for r, s in enumerate(snaps, start=1):
            ws3.write(r, 0, s.cod_produto)
            ws3.write(r, 1, s.nome_produto or '')
            ws3.write_number(r, 2, float(s.pa_qtd or 0), nfmt)
            ws3.write_number(r, 3, float(s.componente_qtd or 0), nfmt)
            ws3.write_number(r, 4, float(s.compras_qtd or 0), nfmt)

        # Aba 4: Movimentações Sistema
        ws4 = wb.add_worksheet('Movimentacoes_Sistema')
        ws4.write_row(0, 0, ['data', 'tipo', 'local', 'cod', 'produto',
                              'qtd', 'nf', 'origem'], hfmt)
        ciclo = CicloInventario.query.get(ciclo_id)
        if ciclo:
            movs = (MovimentacaoEstoque.query
                    .filter(MovimentacaoEstoque.ativo.is_(True))
                    .filter(MovimentacaoEstoque.data_movimentacao >= ciclo.data_snapshot)
                    .order_by(MovimentacaoEstoque.data_movimentacao.desc())
                    .limit(20000).all())
            for r, m in enumerate(movs, start=1):
                ws4.write(r, 0, m.data_movimentacao.isoformat() if m.data_movimentacao else '')
                ws4.write(r, 1, m.tipo_movimentacao or '')
                ws4.write(r, 2, m.local_movimentacao or '')
                ws4.write(r, 3, m.cod_produto or '')
                ws4.write(r, 4, m.nome_produto or '')
                ws4.write_number(r, 5, float(m.qtd_movimentacao or 0), nfmt)
                ws4.write(r, 6, m.numero_nf or '')
                ws4.write(r, 7, m.tipo_origem or '')

        # Aba 5: Estoque Odoo por Empresa
        ws5 = wb.add_worksheet('Estoque_Odoo_por_Empresa')
        ws5.write_row(0, 0, ['cod', 'produto', 'FB', 'CD', 'LF', 'TOTAL'], hfmt)
        for r, s in enumerate(snaps, start=1):
            ws5.write(r, 0, s.cod_produto)
            ws5.write(r, 1, s.nome_produto or '')
            ws5.write_number(r, 2, float(s.estoque_fb or 0), nfmt)
            ws5.write_number(r, 3, float(s.estoque_cd or 0), nfmt)
            ws5.write_number(r, 4, float(s.estoque_lf or 0), nfmt)
            total = (float(s.estoque_fb or 0) + float(s.estoque_cd or 0) +
                     float(s.estoque_lf or 0))
            ws5.write_number(r, 5, total, nfmt)

        # Aba 6: Inventario Base
        ws6 = wb.add_worksheet('Inventario_Base')
        ws6.write_row(0, 0, ['cod', 'produto', 'empresa', 'qtd'], hfmt)
        bases = InventarioBase.query.filter_by(ciclo_id=ciclo_id).order_by(
            InventarioBase.cod_produto, InventarioBase.empresa).all()
        for r, b in enumerate(bases, start=1):
            ws6.write(r, 0, b.cod_produto)
            ws6.write(r, 1, b.nome_produto or '')
            ws6.write(r, 2, b.empresa)
            ws6.write_number(r, 3, float(b.qtd or 0), nfmt)

        wb.close()
        return buf.getvalue()
