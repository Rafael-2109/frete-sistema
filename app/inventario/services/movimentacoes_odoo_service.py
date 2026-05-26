"""Drill-down: busca movimentações Odoo on-demand paginadas (sem persistir)."""
from datetime import datetime
from typing import Dict, Any
from app.odoo.utils.connection import get_odoo_connection


COMPANIES = [1, 4, 5]
COMPANY_TO_ID = {'FB': 1, 'CD': 4, 'LF': 5}
ID_TO_COMPANY = {1: 'FB', 4: 'CD', 5: 'LF'}


def _m2o_id(v):
    return v[0] if isinstance(v, (list, tuple)) and v else None


def _m2o_name(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''


class MovimentacoesOdooService:

    PAGE_SIZES_VALIDOS = (100, 500, 1000)

    @staticmethod
    def buscar_paginado(filtros: Dict[str, Any]) -> Dict:
        page = int(filtros.get('page') or 1)
        page_size = int(filtros.get('page_size') or 100)
        if page_size not in MovimentacoesOdooService.PAGE_SIZES_VALIDOS:
            page_size = 100
        page = max(1, page)

        odoo = get_odoo_connection()

        product_id = None
        if filtros.get('cod'):
            prods = odoo.search_read('product.product',
                                      [['default_code', '=', str(filtros['cod'])]],
                                      ['id'], limit=1)
            if prods:
                product_id = prods[0]['id']

        domain = [['state', '=', 'done']]
        if filtros.get('data_inicio'):
            domain.append(['date', '>=', str(filtros['data_inicio'])])
        if filtros.get('data_fim'):
            domain.append(['date', '<=', str(filtros['data_fim'])])

        emp = filtros.get('empresa')
        if emp and emp != 'ALL' and emp in COMPANY_TO_ID:
            domain.append(['company_id', 'in', [COMPANY_TO_ID[emp]]])
        else:
            domain.append(['company_id', 'in', COMPANIES])

        if product_id:
            domain.append(['product_id', '=', product_id])
        if filtros.get('origem'):
            domain.append(['location_id.name', 'ilike', str(filtros['origem'])])
        if filtros.get('destino'):
            domain.append(['location_dest_id.name', 'ilike', str(filtros['destino'])])

        tipo = filtros.get('tipo')
        if tipo == 'PRODUCAO':
            mv_ids = odoo.search('stock.move',
                [['date', '>=', str(filtros.get('data_inicio') or '2000-01-01')],
                 ['state', '=', 'done'],
                 '|',
                 ['raw_material_production_id', '!=', False],
                 ['production_id', '!=', False]])
            if mv_ids:
                domain.append(['move_id', 'in', mv_ids])
            else:
                return {'total': 0, 'page': page, 'page_size': page_size, 'rows': []}

        if filtros.get('usuario'):
            user_ids = odoo.search('res.users',
                [['name', 'ilike', str(filtros['usuario'])]], limit=20)
            if user_ids:
                mv_filter = odoo.search('stock.move',
                    [['create_uid', 'in', user_ids]])
                if mv_filter:
                    domain.append(['move_id', 'in', mv_filter])
                else:
                    return {'total': 0, 'page': page, 'page_size': page_size, 'rows': []}

        ts = datetime.now()
        total = odoo.search_count('stock.move.line', domain)
        offset = (page - 1) * page_size
        ids = odoo.search('stock.move.line', domain,
                          offset=offset, limit=page_size, order='date desc')
        if not ids:
            return {'total': total, 'page': page, 'page_size': page_size, 'rows': []}

        rows = odoo.read('stock.move.line', ids,
                         ['date', 'company_id', 'product_id', 'lot_id',
                          'qty_done', 'location_id', 'location_dest_id',
                          'move_id', 'create_uid'])

        pids = [_m2o_id(r.get('product_id')) for r in rows]
        pids = [p for p in pids if p]
        prods = odoo.read('product.product', list(set(pids)),
                          ['default_code', 'name']) if pids else []
        pid_to_info = {p['id']: {'cod': p.get('default_code') or '',
                                  'nome': p.get('name') or ''}
                        for p in prods}

        out = []
        for r in rows:
            pid = _m2o_id(r.get('product_id'))
            info = pid_to_info.get(pid, {'cod': '', 'nome': ''})
            cid = _m2o_id(r.get('company_id'))
            emp_name = ID_TO_COMPANY.get(cid, '?')
            out.append({
                'data': r.get('date'),
                'empresa': emp_name,
                'cod': info['cod'],
                'produto': info['nome'],
                'lote': _m2o_name(r.get('lot_id')),
                'qtd': float(r.get('qty_done') or 0),
                'origem': _m2o_name(r.get('location_id')),
                'destino': _m2o_name(r.get('location_dest_id')),
                'usuario': _m2o_name(r.get('create_uid')),
                'move_id': _m2o_id(r.get('move_id')),
            })

        duracao = (datetime.now() - ts).total_seconds() * 1000
        return {
            'total': total, 'page': page, 'page_size': page_size,
            'rows': out, 'duracao_ms': int(duracao),
        }
