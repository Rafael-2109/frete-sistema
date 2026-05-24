"""StockQuantQueryService — atomos READ-only para consultar quants no Odoo AO VIVO.

Skill: `consultando-quant-odoo` (C1 mineracao parcial + C2-C5 minimo viavel).
Constituicao: `app/odoo/estoque/CLAUDE.md`. READ-only — nao escreve no Odoo.

Atomos implementados:
  - listar_quants(cods=None, pids=None, empresas=None, pares_cod_empresa=None,
                  locations_excluir=None, com_lote=None, incluir_qty_zero=False,
                  only_principal=False, agregar=False)
        Query versatil de stock.quant. Resolve cods → pids automaticamente.
        `pares_cod_empresa` filtra EXATAMENTE pares (cod, empresa) — evita
        produto-cartesiano quando o caso e' "lista de pares especificos".
        Inclui agregacao opcional por (cod, empresa) via parametro agregar.

  - auditar_pares(pares_cod_empresa, incluir_indisp=True)
        Audita N pares (cod, empresa): para cada par, classifica em
        ['totalmente_zerado', 'so_indisp', 'com_saldo_nao_indisp', 'sem_produto'].
        Helper de mais alto nivel (compoe listar_quants 2x: principais + indisp).
        Util para auditoria pos-WRITE (caso real 2026-05-23).

Atomos previstos (catalogo, sem implementacao ainda):
  - listar_move_lines(quant_ids=None, picking_ids=None, mo_ids=None, states=None)
  - listar_pickings(states=None, picking_type_ids=None, partner_ids=None)
  - find_orphan_mls(quant_ids) → MLs apontando para quants com qty=0
  - snapshot_estoque_por_lote(empresa) → relatorio agregado por lote
  - saldo_fora_principal(empresa) → INTERNAL_FORA vs ESTOQUE_RAIZ (do script
    auditoria/levantar_estoque_fora_principal.py)

Constantes:
  - INDISP = {1: 31088 (FB), 4: 31090 (CD), 5: 31091 (LF), 3: 31089 (SC)}
  - PRINCIPAL = {1: 8 (FB), 4: 32 (CD), 5: 42 (LF)}
  - EMP_TO_CID = {'FB': 1, 'CD': 4, 'LF': 5}
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

INDISP = {1: 31088, 3: 31089, 4: 31090, 5: 31091}
PRINCIPAL = {1: 8, 4: 32, 5: 42}
EMP_TO_CID = {'FB': 1, 'CD': 4, 'LF': 5}
CID_TO_EMP = {v: k for k, v in EMP_TO_CID.items()}


class StockQuantQueryService:
    """Atomos READ-only para consultar quants no Odoo AO VIVO (skill 9)."""

    def __init__(self, odoo):
        self.odoo = odoo

    def listar_quants(
        self,
        cods: Optional[List[str]] = None,
        pids: Optional[List[int]] = None,
        empresas: Optional[List[str]] = None,  # ['FB', 'CD', 'LF']
        pares_cod_empresa: Optional[List[Tuple[str, str]]] = None,  # [(cod, 'FB'), ...]
        locations_excluir: Optional[List[int]] = None,  # ex.: INDISP values
        com_lote: Optional[str] = None,  # padrao ilike no nome do lote
        incluir_qty_zero: bool = False,
        only_principal: bool = False,
        agregar: bool = False,  # se True, retorna agregado por (cod, empresa)
        limit: int = 20000,
    ) -> Dict[str, Any]:
        """Lista stock.quant com filtros versateis.

        Args:
            cods: default_codes a buscar (resolvidos para pids internamente).
            pids: product_ids diretos (alternativa a cods).
            empresas: lista de empresas ('FB','CD','LF'). Default: todas.
                CUIDADO: cods + empresas = produto-cartesiano (cada cod em CADA
                empresa). Para casos onde cada cod tem UMA empresa especifica,
                use `pares_cod_empresa` em vez disso.
            pares_cod_empresa: lista de pares EXATOS (cod, empresa). Quando
                fornecido, ignora `cods` e `empresas` e busca SO os pares
                especificos. Ideal para auditoria de planilha com pares
                heterogeneos (cod=X em FB + cod=Y em CD + cod=X em LF).
            locations_excluir: location_ids a EXCLUIR (ex.: [INDISP[1], INDISP[4]]
                para excluir Indisponivel de FB e CD).
            com_lote: padrao ilike no nome do lote (ex.: 'MIGRA' filtra
                lotes com 'migra' no nome — incluindo MIGRACAO, MIGRAÇÃO).
            incluir_qty_zero: se False (default), filtra quantity != 0.
            only_principal: se True, busca SO na location principal (FB=8, CD=32, LF=42).
            agregar: se True, retorna agregado por (cod, empresa).
            limit: max quants para retornar.

        Returns:
            dict {
                'total_quants': int,
                'quants': [{'id', 'cod', 'product_name', 'empresa', 'company_id',
                            'location_id', 'location_name', 'lot_id', 'lote',
                            'quantity', 'reserved_quantity', 'available'}, ...],
                'agregado': {(cod, empresa): {'qty_total', 'reserved_total',
                                              'n_quants', 'lotes': [...]}}  (se agregar=True)
            }
        """
        # 1) Resolver cods (se nao temos pids)
        # CASO ESPECIAL: pares_cod_empresa fornecido -> derivar cods + filtrar depois
        pares_set: Optional[set] = None
        if pares_cod_empresa:
            pares_set = {(c, e) for c, e in pares_cod_empresa}
            cods_dos_pares = sorted({c for c, _ in pares_cod_empresa})
            cods = cods_dos_pares  # override
            empresas = sorted({e for _, e in pares_cod_empresa})  # override (CIDs uniao)

        if cods and not pids:
            prods = self.odoo.search_read(
                'product.product',
                [('default_code', 'in', list(cods)), ('active', '=', True)],
                ['id', 'default_code', 'name', 'tracking'],
                limit=len(cods) * 3,
            )
            pid_to_info = {}
            for p in prods:
                pid_to_info[p['id']] = {
                    'cod': p['default_code'], 'name': p['name'], 'tracking': p['tracking'],
                }
            pids = list(pid_to_info.keys())
        else:
            pid_to_info = None

        if not pids:
            return {'total_quants': 0, 'quants': [], 'agregado': {}}

        # 2) Determinar empresas/CIDs
        if empresas:
            cids = [EMP_TO_CID[e] for e in empresas if e in EMP_TO_CID]
        else:
            cids = list(EMP_TO_CID.values())  # todas

        # 3) Montar domain
        domain: List[Any] = [
            ('product_id', 'in', pids),
            ('company_id', 'in', cids),
            ('location_id.usage', '=', 'internal'),
        ]
        if not incluir_qty_zero:
            domain.append(('quantity', '!=', 0))
        if only_principal:
            domain.append(('location_id', 'in', list(PRINCIPAL.values())))
        if locations_excluir:
            for lid in locations_excluir:
                domain.append(('location_id', '!=', lid))
        if com_lote:
            domain.append(('lot_id.name', 'ilike', com_lote))

        # 4) Buscar quants
        raw = self.odoo.search_read(
            'stock.quant', domain,
            ['id', 'product_id', 'company_id', 'location_id', 'lot_id',
             'quantity', 'reserved_quantity'],
            limit=limit,
        )

        # 4b) Se pares_cod_empresa, filtrar para os pares EXATOS
        if pares_set:
            pid_to_cod_local = (
                {pid: info['cod'] for pid, info in pid_to_info.items()}
                if pid_to_info else {}
            )
            raw = [
                q for q in raw
                if (
                    pid_to_cod_local.get(q['product_id'][0] if q['product_id'] else None),
                    CID_TO_EMP.get(q['company_id'][0] if q['company_id'] else None),
                ) in pares_set
            ]

        # 5) Resolver nomes de produtos se ainda não temos
        if not pid_to_info:
            pids_no_map = list({q['product_id'][0] for q in raw if q['product_id']})
            if pids_no_map:
                prods = self.odoo.read('product.product', pids_no_map,
                                       ['default_code', 'name', 'tracking'])
                pid_to_info = {p['id']: {
                    'cod': p.get('default_code') or '',
                    'name': p['name'], 'tracking': p['tracking'],
                } for p in prods}

        # 6) Enriquecer + normalizar
        quants = []
        for q in raw:
            pid = q['product_id'][0] if q['product_id'] else None
            cid = q['company_id'][0] if q['company_id'] else None
            info = pid_to_info.get(pid, {}) if pid else {}
            quants.append({
                'id': q['id'],
                'cod': info.get('cod', ''),
                'product_name': info.get('name', ''),
                'tracking': info.get('tracking', ''),
                'pid': pid,
                'company_id': cid,
                'empresa': CID_TO_EMP.get(cid, '?'),
                'location_id': q['location_id'][0] if q['location_id'] else None,
                'location_name': q['location_id'][1] if q['location_id'] else '',
                'lot_id': q['lot_id'][0] if q['lot_id'] else None,
                'lote': q['lot_id'][1] if q['lot_id'] else '',
                'quantity': round(q['quantity'], 6),
                'reserved_quantity': round(q['reserved_quantity'], 6),
                'available': round(q['quantity'] - q['reserved_quantity'], 6),
            })

        out: Dict[str, Any] = {'total_quants': len(quants), 'quants': quants}

        # 7) Agregar se solicitado
        if agregar:
            agg: Dict[Any, Dict[str, Any]] = {}
            for q in quants:
                key = (q['cod'], q['empresa'])
                if key not in agg:
                    agg[key] = {
                        'cod': q['cod'], 'empresa': q['empresa'],
                        'product_name': q['product_name'],
                        'qty_total': 0.0, 'reserved_total': 0.0,
                        'available_total': 0.0, 'n_quants': 0,
                        'lotes': [], 'locations': [],
                    }
                agg[key]['qty_total'] += q['quantity']
                agg[key]['reserved_total'] += q['reserved_quantity']
                agg[key]['available_total'] += q['available']
                agg[key]['n_quants'] += 1
                if q['lote'] and q['lote'] not in agg[key]['lotes']:
                    agg[key]['lotes'].append(q['lote'])
                if q['location_name'] not in agg[key]['locations']:
                    agg[key]['locations'].append(q['location_name'])
            # Round
            for v in agg.values():
                v['qty_total'] = round(v['qty_total'], 6)
                v['reserved_total'] = round(v['reserved_total'], 6)
                v['available_total'] = round(v['available_total'], 6)
            out['agregado'] = agg

        return out

    def auditar_pares(
        self,
        pares_cod_empresa: List[Tuple[str, str]],
        incluir_detalhe_quants: bool = False,
    ) -> Dict[str, Any]:
        """Audita N pares (cod, empresa) ao vivo no Odoo.

        Para cada par, classifica em:
          - 'totalmente_zerado': sem quants ativos em loc internal (qty=0 em qq lugar)
          - 'so_indisp': saldo so na location Indisponivel da empresa
          - 'com_saldo_nao_indisp': saldo em location internal !=Indisponivel
          - 'sem_produto': default_code nao existe no Odoo (ativo)

        Helper de mais alto nivel — para auditoria pos-WRITE.
        Caso real (2026-05-23): 104 pares ajustados → 17 zerados + 46 so_indisp
        + 39 com_saldo + 2 sem_produto.

        Args:
            pares_cod_empresa: lista [(cod, empresa), ...].
            incluir_detalhe_quants: se True, inclui lista de quants em cada par.

        Returns:
            {
                'totais': {<categoria>: int},
                'por_par': [{cod, empresa, classificacao, qty_nao_indisp,
                             qty_indisp, reserved_nao_indisp,
                             quants_nao_indisp: [...] (opcional),
                             quants_indisp: [...] (opcional)}],
            }
        """
        # 1) Resolver produtos
        cods_unique = sorted({c for c, _ in pares_cod_empresa})
        prods = self.odoo.search_read(
            'product.product',
            [('default_code', 'in', cods_unique), ('active', '=', True)],
            ['id', 'default_code', 'name'],
        )
        cod_to_pid = {p['default_code']: p['id'] for p in prods}
        cod_to_name = {p['default_code']: p['name'] for p in prods}

        # 2) Para cada empresa em uso, query loc!=Indisp E query Indisp
        from collections import defaultdict
        sn = defaultdict(lambda: {'qty': 0.0, 'reserved': 0.0, 'quants': []})
        si = defaultdict(lambda: {'qty': 0.0, 'reserved': 0.0, 'quants': []})

        emps_em_uso = sorted({e for _, e in pares_cod_empresa})
        for emp in emps_em_uso:
            if emp not in EMP_TO_CID:
                continue
            cid = EMP_TO_CID[emp]
            pids_dessa = [cod_to_pid[c] for c, e in pares_cod_empresa
                          if e == emp and c in cod_to_pid]
            if not pids_dessa:
                continue
            # Loc !=Indisponivel — inclui qty=0 com reserved!=0 (MLs orfas pos-cirurgia)
            qs = self.odoo.search_read(
                'stock.quant',
                ['&',
                 ('product_id', 'in', pids_dessa),
                 '&', ('company_id', '=', cid),
                 '&', ('location_id.usage', '=', 'internal'),
                 '&', ('location_id', '!=', INDISP[cid]),
                 '|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)],
                ['id', 'product_id', 'location_id', 'lot_id',
                 'quantity', 'reserved_quantity'],
                limit=10000,
            )
            pid_to_cod = {pid: c for c, pid in cod_to_pid.items()}
            for q in qs:
                cod = pid_to_cod.get(q['product_id'][0])
                key = (cod, emp)
                sn[key]['qty'] += q['quantity']
                sn[key]['reserved'] += q['reserved_quantity']
                if incluir_detalhe_quants:
                    sn[key]['quants'].append({
                        'id': q['id'],
                        'location': q['location_id'][1] if q['location_id'] else '',
                        'lote': q['lot_id'][1] if q['lot_id'] else '',
                        'qty': round(q['quantity'], 6),
                        'reserved': round(q['reserved_quantity'], 6),
                    })
            # Indisponivel
            qsi = self.odoo.search_read(
                'stock.quant',
                [('product_id', 'in', pids_dessa), ('company_id', '=', cid),
                 ('location_id', '=', INDISP[cid]),
                 ('quantity', '!=', 0)],
                ['id', 'product_id', 'lot_id', 'quantity'],
                limit=5000,
            )
            for q in qsi:
                cod = pid_to_cod.get(q['product_id'][0])
                key = (cod, emp)
                si[key]['qty'] += q['quantity']
                if incluir_detalhe_quants:
                    si[key]['quants'].append({
                        'id': q['id'],
                        'lote': q['lot_id'][1] if q['lot_id'] else '',
                        'qty': round(q['quantity'], 6),
                    })

        # 3) Classificar cada par
        por_par = []
        totais = {'totalmente_zerado': 0, 'so_indisp': 0,
                  'com_saldo_nao_indisp': 0, 'quant_orfao_reserva': 0,
                  'sem_produto': 0}
        for cod, emp in pares_cod_empresa:
            key = (cod, emp)
            if cod not in cod_to_pid:
                classif = 'sem_produto'
            elif abs(sn[key]['qty']) > 0.0001:
                classif = 'com_saldo_nao_indisp'
            elif abs(sn[key]['reserved']) > 0.0001:
                # quantity=0 mas reserved!=0 -> ML orfa apontando para quant zerado
                classif = 'quant_orfao_reserva'
            elif abs(si[key]['qty']) > 0.0001:
                classif = 'so_indisp'
            else:
                classif = 'totalmente_zerado'
            totais[classif] += 1
            par_out = {
                'cod': cod, 'empresa': emp,
                'produto': cod_to_name.get(cod, '-'),
                'classificacao': classif,
                'qty_nao_indisp': round(sn[key]['qty'], 6),
                'qty_indisp': round(si[key]['qty'], 6),
                'reserved_nao_indisp': round(sn[key]['reserved'], 6),
            }
            if incluir_detalhe_quants:
                par_out['quants_nao_indisp'] = sn[key]['quants']
                par_out['quants_indisp'] = si[key]['quants']
            por_par.append(par_out)

        return {'totais': totais, 'por_par': por_par}
