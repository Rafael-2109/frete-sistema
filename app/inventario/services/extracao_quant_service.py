"""Extração de estoque do Odoo na granularidade de QUANT (location + cod + lote).

Porta a lógica de scripts/inventario_2026_05/extrair_estoque_locais_emp.py para
uso programático pelo módulo (sem pandas). Gera a planilha-BASE da contagem
cíclica: uma linha por (location_name, cod_produto, lote) com qtd/reservado.

A função pura `agregar_quants` é testável sem Odoo; `extrair` faz as queries.
Spec: docs/superpowers/specs/2026-05-31-inventario-ciclico-contagem-ajustes-design.md
"""
from decimal import Decimal
from typing import Dict, List, Optional

from app.odoo.utils.connection import get_odoo_connection


# Escopo do módulo (igual ao Confronto): FB / CD / LF
COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}
LOCAIS_INDISPONIVEL_IDS = [31088, 31089, 31090, 31091]  # FB/SC/CD/LF Indisponivel
ODOO_BATCH = 200

# Proxy de lote "vazio" (P-15/05 representa sem-lote no inventário) e variantes MIGRACAO
LOTES_PROXY_VAZIO = {'P-15/05'}
LOTES_MIGRACAO = {'MIGRACAO', 'MIGRAÇÃO', 'MIGRACÃO', 'MIGRAÇAO', 'MIG'}


def _m2o_id(v):
    return v[0] if isinstance(v, (list, tuple)) and v else None


def _m2o_name(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''


def is_migracao(lot_name) -> bool:
    if not lot_name:
        return False
    return str(lot_name).upper().strip() in LOTES_MIGRACAO


def classificar_local(location_id) -> str:
    return 'Indisponivel' if location_id in LOCAIS_INDISPONIVEL_IDS else 'Estoque'


def is_location_emp_root(loc_name) -> bool:
    """True se location pertence a uma filial física ({FB,SC,CD,LF}/...) e não é virtual."""
    if not loc_name:
        return False
    if not loc_name.startswith(('FB/', 'SC/', 'CD/', 'LF/')):
        return False
    virtual_kw = ['Virtual', 'Production', 'Inventory adjustment', 'Customers', 'Vendors']
    return not any(k in loc_name for k in virtual_kw)


def norm_cod(x) -> str:
    if x is None or x is False:
        return ''
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def norm_lote(x) -> str:
    """Normaliza nome do lote; '' = sem lote. P-15/05 (proxy vazio) -> ''."""
    if x is None or x is False:
        return ''
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    if s in LOTES_PROXY_VAZIO:
        return ''
    return s


def agregar_quants(quants: List[dict], pid_to_cod: Dict[int, tuple],
                   filtro_locais: Optional[List[str]] = None,
                   incluir_indisponivel: bool = False) -> List[dict]:
    """Lógica PURA: agrega quants brutos do Odoo por (location_name, cod, lote).

    `quants`: dicts com company_id, product_id, lot_id, location_id, quantity,
              reserved_quantity (formato XML-RPC: m2o = [id, name]).
    `pid_to_cod`: {product_id: (cod_produto, nome_produto)}.
    Retorna lista de dicts agregados, ordenada por (location_name, cod, lote).
    """
    filtro_set = {str(l).strip() for l in filtro_locais} if filtro_locais else None
    agg: Dict[tuple, dict] = {}

    for q in quants:
        loc_id = _m2o_id(q.get('location_id'))
        loc_name = _m2o_name(q.get('location_id'))
        if not is_location_emp_root(loc_name):
            continue
        local_tipo = classificar_local(loc_id)
        if not incluir_indisponivel and local_tipo == 'Indisponivel':
            continue
        if filtro_set is not None and loc_name not in filtro_set:
            continue

        pid = _m2o_id(q.get('product_id'))
        if not pid:
            continue
        cod, nome = pid_to_cod.get(pid, ('', ''))
        cod = norm_cod(cod)
        if not cod:
            continue  # itens sem default_code não entram (paletes etc.)

        lot_name = _m2o_name(q.get('lot_id'))
        lote = norm_lote(lot_name)
        company_id = _m2o_id(q.get('company_id'))

        key = (loc_name, cod, lote)
        cur = agg.get(key)
        if cur is None:
            cur = {
                'location_name': loc_name,
                'location_id': loc_id,
                'local_tipo': local_tipo,
                'is_migracao': is_migracao(lot_name),
                'cod_produto': cod,
                'nome_produto': nome,
                'lote': lote,
                'company_id': company_id,
                'qtd': Decimal('0'),
                'reservado': Decimal('0'),
            }
            agg[key] = cur
        cur['qtd'] += Decimal(str(q.get('quantity') or 0))
        cur['reservado'] += Decimal(str(q.get('reserved_quantity') or 0))
        # is_migracao verdadeiro se qualquer quant do grupo for MIGRACAO
        if is_migracao(lot_name):
            cur['is_migracao'] = True

    linhas = list(agg.values())
    linhas.sort(key=lambda r: (r['location_name'], r['cod_produto'], r['lote']))
    return linhas


class ExtracaoQuantService:
    """Extrai os stock.quant atuais do Odoo conforme empresa + filtros."""

    @staticmethod
    def extrair(empresa: str, filtro_locais: Optional[List[str]] = None,
                filtro_codigos: Optional[List[str]] = None,
                incluir_indisponivel: bool = False, odoo=None) -> List[dict]:
        empresa = (empresa or '').strip().upper()
        if empresa not in COMPANY_ID:
            raise ValueError(f'Empresa inválida: {empresa!r}. Use FB, CD ou LF.')
        company_id = COMPANY_ID[empresa]
        odoo = odoo or get_odoo_connection()

        domain = [('company_id', '=', company_id),
                  ('location_id.usage', '=', 'internal')]
        if not incluir_indisponivel:
            domain.append(('location_id', 'not in', LOCAIS_INDISPONIVEL_IDS))

        # Filtro de códigos -> resolve product_ids (default_code in [...])
        if filtro_codigos:
            cods = [str(c).strip() for c in filtro_codigos if str(c).strip()]
            if not cods:
                return []
            prods = odoo.search_read('product.product',
                                     [['default_code', 'in', cods]],
                                     ['id'])
            pids = [p['id'] for p in prods]
            if not pids:
                return []
            domain.append(('product_id', 'in', pids))

        qids = odoo.search('stock.quant', domain)
        if not qids:
            return []

        fields = ['company_id', 'product_id', 'lot_id', 'location_id',
                  'quantity', 'reserved_quantity']
        quants = []
        for i in range(0, len(qids), ODOO_BATCH):
            quants.extend(odoo.read('stock.quant', qids[i:i + ODOO_BATCH], fields))

        # Resolver default_code + nome dos produtos
        product_ids = {_m2o_id(q.get('product_id')) for q in quants
                       if _m2o_id(q.get('product_id'))}
        pid_to_cod: Dict[int, tuple] = {}
        product_ids = list(product_ids)
        for i in range(0, len(product_ids), ODOO_BATCH):
            for p in odoo.read('product.product', product_ids[i:i + ODOO_BATCH],
                               ['default_code', 'name']):
                pid_to_cod[p['id']] = (p.get('default_code') or '', p.get('name') or '')

        return agregar_quants(quants, pid_to_cod,
                              filtro_locais=filtro_locais,
                              incluir_indisponivel=incluir_indisponivel)
