"""Refresh cache Odoo (estoque + apontamentos + compras) + freeze MOV local.

Reaproveita lógica de:
- scripts/inventario_2026_05/monitor/export_excel_completo.py (estoque)
- scripts/inventario_2026_05/monitor/relatorio_apontamentos_compras.py (apt + compras)

Freeze 2026-05-27: alem dos dados Odoo, agrega `MovimentacaoEstoque` local
(mov_compras/vendas/consumo/producao filtrado >= data_snapshot, mov_sist_total
sem filtro de data) e grava no snapshot. Garante consistencia temporal do
ODOO-MOV no Confronto.
"""
from decimal import Decimal
from collections import defaultdict
from typing import Dict
from sqlalchemy import func, case
from app import db
from app.inventario.models import CicloInventario, InventarioSnapshotOdoo
from app.estoque.models import MovimentacaoEstoque
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive


COMPANIES = [1, 4, 5]
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}
ODOO_BATCH = 200


def _m2o_id(v):
    return v[0] if isinstance(v, (list, tuple)) and v else None


def _m2o_name(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''


def _norm_cod(s):
    return str(s or '').strip()


class SnapshotOdooService:

    @staticmethod
    def refresh(ciclo_id: int, job=None) -> Dict:
        ciclo = CicloInventario.query.get(ciclo_id)
        if ciclo is None:
            return {'erro': f'Ciclo {ciclo_id} não encontrado'}
        data_inicio = ciclo.data_snapshot.isoformat() + ' 00:00:00'

        def _progress(p, msg):
            if job is not None:
                try:
                    job.meta['progress'] = p
                    job.meta['msg'] = msg
                    job.save_meta()
                except Exception:
                    pass

        _progress(5, 'Conectando ao Odoo')
        odoo = get_odoo_connection()

        _progress(20, 'Baixando estoque por empresa')
        estoques = SnapshotOdooService._baixar_estoque(odoo)

        _progress(50, 'Baixando apontamentos (mrp.production)')
        apontamentos = SnapshotOdooService._baixar_apontamentos(odoo, data_inicio)

        _progress(75, 'Baixando compras externas')
        compras = SnapshotOdooService._baixar_compras(odoo, data_inicio)

        _progress(85, 'Congelando MOV local (MovimentacaoEstoque)')
        movs = SnapshotOdooService._baixar_movimentacoes_local(ciclo.data_snapshot)

        _progress(90, 'Persistindo snapshot')
        cods = (set(estoques.keys()) | set(apontamentos.keys()) |
                set(compras.keys()) | set(movs.keys()))

        InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo_id).delete()
        db.session.flush()

        for cod in cods:
            est = estoques.get(cod, {})
            apt = apontamentos.get(cod, {})
            cmp = compras.get(cod, {})
            mv = movs.get(cod, {})
            db.session.add(InventarioSnapshotOdoo(
                ciclo_id=ciclo_id,
                cod_produto=cod,
                nome_produto=(est.get('nome') or apt.get('nome') or
                              cmp.get('nome') or mv.get('nome')),
                estoque_fb=est.get('fb', Decimal('0')),
                estoque_cd=est.get('cd', Decimal('0')),
                estoque_lf=est.get('lf', Decimal('0')),
                pa_qtd=apt.get('pa', Decimal('0')),
                componente_qtd=apt.get('componente', Decimal('0')),
                compras_qtd=cmp.get('qtd', Decimal('0')),
                mov_compras=mv.get('compras', Decimal('0')),
                mov_vendas=mv.get('vendas', Decimal('0')),
                mov_consumo=mv.get('consumo', Decimal('0')),
                mov_producao=mv.get('producao', Decimal('0')),
                mov_sist_total=mv.get('sist_total', Decimal('0')),
                refresh_em=agora_utc_naive(),
            ))
        db.session.flush()  # commit fica para o caller (route/worker)
        _progress(100, 'Concluído')
        return {'inseridos': len(cods), 'refresh_em': agora_utc_naive().isoformat()}

    @staticmethod
    def _baixar_movimentacoes_local(data_snapshot) -> Dict:
        """{cod: {compras, vendas, consumo, producao, sist_total, nome}}.

        Replica EXATAMENTE a logica de ConfrontoService._agg_movimentacoes
        (sem unificacao cod_produto_raiz; agrupa por cod bruto p/ bater
        com planilha referencia). Congelar no snapshot garante que ODOO-MOV
        do confronto seja matematicamente valida (mesmo momento T0).
        """
        cod_raiz = MovimentacaoEstoque.cod_produto.label('raiz')
        # Periodo: ENTRADA/FATURAMENTO/CONSUMO/PRODUCAO desde data_snapshot
        q_periodo = db.session.query(
            cod_raiz,
            func.max(MovimentacaoEstoque.nome_produto),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'ENTRADA',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'CONSUMO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'PRODUÇÃO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
        ).filter(
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.data_movimentacao >= data_snapshot,
        ).group_by(cod_raiz)

        periodo = {r[0]: {
            'nome': r[1] or '',
            'compras': r[2] or Decimal('0'),
            'vendas': r[3] or Decimal('0'),
            'consumo': r[4] or Decimal('0'),
            'producao': r[5] or Decimal('0'),
        } for r in q_periodo.all()}

        # SIST total: sum acumulado ATIVO sem filtro de data
        q_saldo = db.session.query(
            cod_raiz,
            func.sum(MovimentacaoEstoque.qtd_movimentacao),
        ).filter(MovimentacaoEstoque.ativo.is_(True)).group_by(cod_raiz)

        for cod, sist in q_saldo.all():
            if cod not in periodo:
                periodo[cod] = {'nome': '', 'compras': Decimal('0'),
                                'vendas': Decimal('0'), 'consumo': Decimal('0'),
                                'producao': Decimal('0')}
            periodo[cod]['sist_total'] = sist or Decimal('0')

        for cod in periodo:
            periodo[cod].setdefault('sist_total', Decimal('0'))
        return periodo

    @staticmethod
    def _baixar_estoque(odoo) -> Dict:
        """{cod: {fb, cd, lf, nome}} — exclui locations Indisponivel."""
        domain = [('company_id', 'in', COMPANIES),
                  ('location_id.usage', '=', 'internal')]
        qids = odoo.search('stock.quant', domain)
        if not qids:
            return {}
        quants = []
        for i in range(0, len(qids), ODOO_BATCH):
            quants.extend(odoo.read('stock.quant', qids[i:i+ODOO_BATCH],
                                    ['company_id', 'product_id', 'location_id',
                                     'quantity']))
        product_ids = set()
        for q in quants:
            pid = _m2o_id(q.get('product_id'))
            if pid:
                product_ids.add(pid)

        pid_to_cod = {}
        if product_ids:
            prods = odoo.read('product.product', list(product_ids),
                              ['name', 'default_code'])
            pid_to_cod = {p['id']: (_norm_cod(p.get('default_code')),
                                     p.get('name') or '')
                          for p in prods}

        out = defaultdict(lambda: {'fb': Decimal('0'), 'cd': Decimal('0'),
                                    'lf': Decimal('0'), 'nome': ''})
        for q in quants:
            loc_name = _m2o_name(q.get('location_id'))
            if 'ndisponivel' in loc_name.lower() or 'indispon' in loc_name.lower():
                continue
            cid = _m2o_id(q.get('company_id'))
            emp = COMPANY_NAME.get(cid)
            pid = _m2o_id(q.get('product_id'))
            if not emp or not pid:
                continue
            cod, nome = pid_to_cod.get(pid, ('', ''))
            if not cod:
                continue
            qtd = Decimal(str(q.get('quantity') or 0))
            out[cod][emp.lower()] += qtd
            out[cod]['nome'] = nome
        return dict(out)

    @staticmethod
    def _baixar_apontamentos(odoo, data_inicio) -> Dict:
        """{cod: {pa, componente, nome}}."""
        base = [['date', '>=', data_inicio], ['company_id', 'in', COMPANIES],
                ['state', '=', 'done']]
        raw_ids = odoo.search('stock.move',
                              base + [['raw_material_production_id', '!=', False]])
        fin_ids = odoo.search('stock.move',
                              base + [['production_id', '!=', False]])

        move_meta = {}
        move_to_mo = {}
        mo_ids = set()
        for ids, tag, link in (
            (raw_ids, 'COMPONENTE', 'raw_material_production_id'),
            (fin_ids, 'FINISHED', 'production_id'),
        ):
            for i in range(0, len(ids), ODOO_BATCH):
                for m in odoo.read('stock.move', ids[i:i+ODOO_BATCH], [link]):
                    moid = _m2o_id(m.get(link))
                    if moid:
                        move_meta[m['id']] = tag
                        move_to_mo[m['id']] = moid
                        mo_ids.add(moid)

        mo_pa = {}
        mo_list = list(mo_ids)
        for i in range(0, len(mo_list), ODOO_BATCH):
            for mo in odoo.read('mrp.production', mo_list[i:i+ODOO_BATCH],
                                 ['product_id']):
                mo_pa[mo['id']] = _m2o_id(mo.get('product_id'))

        if not move_to_mo:
            return {}
        ml_ids = odoo.search('stock.move.line',
                             [['move_id', 'in', list(move_to_mo.keys())],
                              ['state', '=', 'done']])
        if not ml_ids:
            return {}

        mls = []
        for i in range(0, len(ml_ids), ODOO_BATCH):
            mls.extend(odoo.read('stock.move.line', ml_ids[i:i+ODOO_BATCH],
                                  ['product_id', 'qty_done', 'move_id']))

        product_ids = set()
        for ml in mls:
            pid = _m2o_id(ml.get('product_id'))
            if pid:
                product_ids.add(pid)
        pid_to_cod = {}
        if product_ids:
            prods = odoo.read('product.product', list(product_ids),
                              ['name', 'default_code'])
            pid_to_cod = {p['id']: (_norm_cod(p.get('default_code')),
                                     p.get('name') or '')
                          for p in prods}

        agg = defaultdict(lambda: {'pa': Decimal('0'), 'componente': Decimal('0'),
                                    'nome': ''})
        for ml in mls:
            pid = _m2o_id(ml.get('product_id'))
            mid = _m2o_id(ml.get('move_id'))
            if not pid or not mid:
                continue
            mo_id = move_to_mo.get(mid)
            tag = move_meta.get(mid)
            qtd = Decimal(str(ml.get('qty_done') or 0))
            cod, nome = pid_to_cod.get(pid, ('', ''))
            if not cod:
                continue
            tipo = ('PA' if tag == 'FINISHED' and pid == mo_pa.get(mo_id)
                    else 'COMPONENTE' if tag == 'COMPONENTE' else 'SUBPRODUTO')
            if tipo == 'PA':
                agg[cod]['pa'] += qtd
            elif tipo == 'COMPONENTE':
                agg[cod]['componente'] += qtd
            agg[cod]['nome'] = nome
        return dict(agg)

    @staticmethod
    def _baixar_compras(odoo, data_inicio) -> Dict:
        """{cod: {qtd, nome}} — entradas de fornecedor externo (exclui inter-company)."""
        ml_ids = odoo.search('stock.move.line',
                             [['date', '>=', data_inicio],
                              ['company_id', 'in', COMPANIES],
                              ['state', '=', 'done'],
                              ['location_id.usage', '=', 'supplier']])
        if not ml_ids:
            return {}
        mls = []
        for i in range(0, len(ml_ids), ODOO_BATCH):
            mls.extend(odoo.read('stock.move.line', ml_ids[i:i+ODOO_BATCH],
                                  ['product_id', 'qty_done', 'move_id',
                                   'picking_id']))

        move_ids = sorted({_m2o_id(ml.get('move_id')) for ml in mls
                           if _m2o_id(ml.get('move_id'))})
        mv_to_pl = {}
        for i in range(0, len(move_ids), ODOO_BATCH):
            for m in odoo.read('stock.move', move_ids[i:i+ODOO_BATCH],
                                ['purchase_line_id']):
                mv_to_pl[m['id']] = _m2o_id(m.get('purchase_line_id'))
        pl_ids = sorted({v for v in mv_to_pl.values() if v})
        pl_to_order = {}
        for i in range(0, len(pl_ids), ODOO_BATCH):
            for p in odoo.read('purchase.order.line', pl_ids[i:i+ODOO_BATCH],
                                ['order_id']):
                pl_to_order[p['id']] = _m2o_id(p.get('order_id'))
        order_ids = sorted({v for v in pl_to_order.values() if v})
        order_partner = {}
        for i in range(0, len(order_ids), ODOO_BATCH):
            for o in odoo.read('purchase.order', order_ids[i:i+ODOO_BATCH],
                                ['partner_id']):
                order_partner[o['id']] = _m2o_id(o.get('partner_id'))

        partners_empresas = set()
        for c in COMPANIES:
            try:
                recs = odoo.search_read('res.company', [['id', '=', c]], ['partner_id'])
                if recs:
                    pid = _m2o_id(recs[0].get('partner_id'))
                    if pid:
                        partners_empresas.add(pid)
            except Exception:
                pass
        all_part = set(order_partner.values())
        comm = {}
        if all_part:
            all_part_list = list(all_part)
            for i in range(0, len(all_part_list), ODOO_BATCH):
                batch = all_part_list[i:i+ODOO_BATCH]
                for r in odoo.read('res.partner', batch, ['commercial_partner_id']):
                    cp = r.get('commercial_partner_id')
                    comm[r['id']] = _m2o_id(cp) if cp else r['id']

        product_ids = set()
        for ml in mls:
            pid = _m2o_id(ml.get('product_id'))
            if pid:
                product_ids.add(pid)
        pid_to_cod = {}
        if product_ids:
            prods = odoo.read('product.product', list(product_ids),
                              ['name', 'default_code'])
            pid_to_cod = {p['id']: (_norm_cod(p.get('default_code')),
                                     p.get('name') or '')
                          for p in prods}

        agg = defaultdict(lambda: {'qtd': Decimal('0'), 'nome': ''})
        for ml in mls:
            mid = _m2o_id(ml.get('move_id'))
            plid = mv_to_pl.get(mid)
            partner_id = None
            if plid:
                partner_id = order_partner.get(pl_to_order.get(plid))
            if partner_id and comm.get(partner_id, partner_id) in partners_empresas:
                continue
            pid = _m2o_id(ml.get('product_id'))
            if not pid:
                continue
            cod, nome = pid_to_cod.get(pid, ('', ''))
            if not cod:
                continue
            agg[cod]['qtd'] += Decimal(str(ml.get('qty_done') or 0))
            agg[cod]['nome'] = nome
        return dict(agg)
