# etapa: READ
# doc-dono: app/odoo/estoque/CLAUDE.md §6
"""DescobertaIndustrializacaoService — descoberta READ-only da fonte da NF-2 de
retorno de insumos (industrialização por encomenda FB↔LF, item 1 da automação).

A partir da NF-1 de serviço (5124) descobre, SEM escrever no Odoo, tudo que a SA
da SAÍDA precisa para montar a NF-2 de insumos (5902) e o R2 da entrada precisa
para conferir:
  - os MATERIAIS DE TERCEIROS (e quantidades rateadas) que voltam embutidos no PA;
  - o PREÇO de cada um (invariante 5902=5901 = valor da remessa);
  - a REMESSA (RPI) correspondente, para o vínculo refNFe (R3).

Mecânica (provada em PROD pelo s69 — NF-1 791437 / lote 60542, 16/16 itens):
  1. genealogia recursiva: lote do PA → MOs `done` → para cada matéria consumida,
     se o lote consumido foi produzido por uma MO é SEMI (desce recursivamente),
     senão é folha; acumula só as folhas vindas de `31092 LF/Materiais de Terceiros`.
     O RATEIO `qty × fator / produção_real` propaga pelos semis (robusto a múltiplas
     MOs do mesmo lote e a remessa parcial — decisão Rafael 2026-06-15).
  2. ÁGUA (`type=consu`, consumo local da LF) é EXCLUÍDA (não foi remetida, não volta).
  3. VALOR = `unit_cost` do SVL do move de ENTRADA em 31092 (= price_unit da remessa).
     NÃO o SVL do consumo (que carrega o AVCO interno da LF — divergiria do 5901).
  4. REMESSA = picking de entrada em 31092 com mais votos (cada material vota no seu).

READ-only: usa apenas `search_read`/`read`. Não recebe `--dry-run/--confirmar`.
Constituição: `app/odoo/estoque/CLAUDE.md` (READ ancillary, cross-objeto).
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LOC_TERCEIROS = 31092  # LF / Materiais de Terceiros


class DescobertaIndustrializacaoService:
    """Descoberta READ-only da fonte da NF-2 de retorno de insumos (FB↔LF)."""

    def __init__(self, odoo):
        self.odoo = odoo

    # ── API pública ───────────────────────────────────────────────────────────
    def descobrir_fonte_nf2(self, nf1_id: int) -> Dict[str, Any]:
        """Descobre componentes + valores + remessa da NF-2 a partir da NF-1 (serviço).

        Retorna o contrato consumido pela SA da saída e pelo R2 da entrada:
            {
              'nf1_id', 'pa': {'product_id','qtd_faturada','lote'},
              'produzido_total',                      # denominador do rateio
              'componentes': [{'product_id','default_code','name','qty','price_unit','subtotal'}],
              'total',
              'remessa': {'picking_id','picking_name','votos'},
            }
        """
        o = self.odoo
        pal = o.search_read(
            'account.move.line',
            [('move_id', '=', nf1_id), ('l10n_br_cfop_codigo', '=', '5124')],
            ['product_id', 'quantity'], limit=1,
        )
        if not pal:
            raise ValueError(f"NF-1 {nf1_id} sem linha de serviço (CFOP 5124)")
        pa_pid = pal[0]['product_id'][0]
        pa_qty = pal[0]['quantity']

        lote_pa = self._lote_do_pa(nf1_id, pa_pid)
        if not lote_pa:
            raise ValueError(f"NF-1 {nf1_id}: não foi possível resolver o lote do PA {pa_pid}")

        acc_qty: Dict[int, float] = defaultdict(float)
        acc_moves: Dict[int, List[int]] = defaultdict(list)
        self._explodir(lote_pa, pa_qty, acc_qty, acc_moves)

        pinfo = {p['id']: p for p in o.read(
            'product.product', list(acc_qty),
            ['id', 'default_code', 'name', 'standard_price', 'type'])}
        comps = [pid for pid in acc_qty if pinfo.get(pid, {}).get('type') != 'consu']

        entrada = o.search_read(
            'stock.move',
            [('product_id', 'in', comps), ('location_dest_id', '=', LOC_TERCEIROS),
             ('state', '=', 'done')],
            ['id', 'product_id', 'picking_id', 'date'],
        )
        svl = o.search_read(
            'stock.valuation.layer',
            [('stock_move_id', 'in', [e['id'] for e in entrada])],
            ['stock_move_id', 'unit_cost', 'quantity', 'value'],
        )
        precos = self._precos_svl_entrada(comps, entrada, svl)

        componentes = []
        total = 0.0
        for pid in comps:
            p = pinfo.get(pid, {})
            qty = acc_qty[pid]
            price_unit = precos.get(pid, p.get('standard_price') or 0.0)
            subtotal = qty * price_unit
            total += subtotal
            componentes.append({
                'product_id': pid,
                'default_code': p.get('default_code'),
                'name': p.get('name'),
                'qty': qty,
                'price_unit': price_unit,
                'subtotal': subtotal,
            })
        componentes.sort(key=lambda c: c['default_code'] or '')

        return {
            'nf1_id': nf1_id,
            'pa': {'product_id': pa_pid, 'qtd_faturada': pa_qty, 'lote': lote_pa},
            'produzido_total': self._producao_total(lote_pa),
            'componentes': componentes,
            'total': total,
            'remessa': self._votar_remessa(entrada),
        }

    # ── internos ────────────────────────────────────────────────────────────
    def _lote_do_pa(self, nf1_id: int, pa_pid: int) -> Optional[int]:
        pk = self.odoo.search_read(
            'stock.picking',
            ['|', ('invoice_id', '=', nf1_id), ('invoice_ids', 'in', [nf1_id])],
            ['id'], limit=1)
        if not pk:
            return None
        ml = self.odoo.search_read(
            'stock.move.line',
            [('picking_id', '=', pk[0]['id']), ('product_id', '=', pa_pid)],
            ['lot_id'], limit=1)
        if ml and ml[0].get('lot_id'):
            return ml[0]['lot_id'][0]
        return None

    def _explodir(self, lote_id: int, fator: float,
                  acc_qty: Dict[int, float], acc_moves: Dict[int, List[int]]) -> bool:
        """Acumula materiais de terceiros (31092) consumidos p/ produzir `fator` un
        do lote. Retorna True se o lote foi PRODUZIDO aqui (=semi/PA), False se é folha."""
        mos = self.odoo.search_read(
            'mrp.production',
            [('lot_producing_id', '=', lote_id), ('state', '=', 'done')],
            ['id', 'qty_producing', 'product_qty'])
        if not mos:
            return False  # folha (matéria-prima — não produzida aqui)
        total = sum((m.get('qty_producing') or m.get('product_qty') or 0) for m in mos) or 1.0
        for mo in mos:
            raws = self.odoo.search_read(
                'stock.move',
                [('raw_material_production_id', '=', mo['id']), ('state', '=', 'done')],
                ['id', 'product_id', 'product_qty', 'location_id'])
            for r in raws:
                pid = r['product_id'][0]
                q = r.get('product_qty') or 0
                share = q * fator / total
                comp_lot = self._lote_consumido(r['id'])
                is_semi = self._explodir(comp_lot, share, acc_qty, acc_moves) if comp_lot else False
                if not is_semi and r.get('location_id') and r['location_id'][0] == LOC_TERCEIROS:
                    acc_qty[pid] += share
                    acc_moves[pid].append(r['id'])
        return True

    def _lote_consumido(self, move_id: int) -> Optional[int]:
        mls = self.odoo.search_read('stock.move.line', [('move_id', '=', move_id)], ['lot_id'], limit=1)
        if mls and mls[0].get('lot_id'):
            return mls[0]['lot_id'][0]
        return None

    def _producao_total(self, lote_id: int) -> float:
        mos = self.odoo.search_read(
            'mrp.production',
            [('lot_producing_id', '=', lote_id), ('state', '=', 'done')],
            ['qty_producing'])
        return sum(m.get('qty_producing') or 0 for m in mos)

    @staticmethod
    def _precos_svl_entrada(comps: List[int], entrada: List[dict], svl: List[dict]) -> Dict[int, float]:
        """price_unit por produto = unit_cost do SVL da ENTRADA mais recente em 31092."""
        svl_by_move = {s['stock_move_id'][0]: s for s in svl if s.get('stock_move_id')}
        ent_by_prod: Dict[int, List[dict]] = defaultdict(list)
        for e in entrada:
            ent_by_prod[e['product_id'][0]].append(e)
        precos: Dict[int, float] = {}
        for pid in comps:
            for em in sorted(ent_by_prod.get(pid, []), key=lambda x: x.get('date') or '', reverse=True):
                s = svl_by_move.get(em['id'])
                if s and s.get('unit_cost'):
                    precos[pid] = s['unit_cost']
                    break
        return precos

    @staticmethod
    def _votar_remessa(entrada: List[dict]) -> Dict[str, Any]:
        votos: Dict[int, int] = defaultdict(int)
        nome: Dict[int, str] = {}
        for e in entrada:
            pk = e.get('picking_id')
            if pk:
                votos[pk[0]] += 1
                nome[pk[0]] = pk[1]
        if not votos:
            return {'picking_id': None, 'picking_name': None, 'votos': 0}
        top = max(votos, key=lambda k: votos[k])
        return {'picking_id': top, 'picking_name': nome.get(top), 'votos': votos[top]}
