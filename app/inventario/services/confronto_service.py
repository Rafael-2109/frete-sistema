"""Agregador principal do Relatório de Confronto de Inventário."""
from datetime import datetime, time
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy import func, case
from app import db
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo, ContagemInventario, ContagemInventarioItem,
)
from app.estoque.models import MovimentacaoEstoque


class ConfrontoService:
    """Monta as linhas do Relatório de Confronto."""

    EMPRESAS = ('FB', 'CD', 'LF')

    @staticmethod
    def montar_linhas(ciclo_id: int) -> List[Dict[str, Any]]:
        ciclo = CicloInventario.query.get(ciclo_id)
        if ciclo is None:
            return []
        data_inicio = ciclo.data_snapshot

        inv = ConfrontoService._agg_inventario_base(ciclo_id)
        snap = ConfrontoService._agg_snapshot(ciclo_id)
        # FREEZE 2026-05-27: se snapshot tem MOV congelado (qualquer cod com
        # qualquer mov_* != 0 OU mov_sist_total != 0), usa snapshot — garante
        # ODOO-MOV/SIST-MOV consistentes (mesmo T0). Fallback live para retro-
        # compat com snapshots antigos (pre-freeze) ou ciclos sem snapshot.
        if ConfrontoService._snapshot_tem_mov_freezado(snap):
            movs = ConfrontoService._movs_do_snapshot(snap)
        else:
            movs = ConfrontoService._agg_movimentacoes(data_inicio)
        ajustes = ConfrontoService._agg_ajustes(ciclo_id)
        # Inventário Cíclico (2026-05-31): ajustes das contagens cíclicas do
        # período somam às colunas INV FB/CD/LF (spec §6.4).
        ajustes_ciclicos = ConfrontoService._agg_ajustes_ciclicos(ciclo)

        cods = (set(inv.keys()) | set(snap.keys()) | set(movs.keys()) |
                set(ajustes.keys()) | set(ajustes_ciclicos.keys()))

        # Filtra cods inativos no Odoo (product.product.active=False).
        # 1 batch query — silencioso se Odoo falhar (retorna set vazio).
        inativos = ConfrontoService._produtos_inativos_odoo(cods)
        cods = cods - inativos

        linhas = []
        for cod in sorted(cods):
            i = inv.get(cod, {})
            s = snap.get(cod, {})
            m = movs.get(cod, {})
            a = ajustes.get(cod, {})

            inv_fb = i.get('fb', Decimal('0'))
            inv_cd = i.get('cd', Decimal('0'))
            inv_lf = i.get('lf', Decimal('0'))
            # Soma os ajustes cíclicos do período por empresa (spec §6.4).
            ac = ajustes_ciclicos.get(cod)
            if ac:
                inv_fb += ac['fb']
                inv_cd += ac['cd']
                inv_lf += ac['lf']
            inv_total = inv_fb + inv_cd + inv_lf

            compras = m.get('compras', Decimal('0'))
            vendas = m.get('vendas', Decimal('0'))
            consumo = m.get('consumo', Decimal('0'))
            producao = m.get('producao', Decimal('0'))
            sist_total = m.get('sist_total', Decimal('0'))

            est_fb = s.get('estoque_fb', Decimal('0'))
            est_cd = s.get('estoque_cd', Decimal('0'))
            est_lf = s.get('estoque_lf', Decimal('0'))
            # Em transito (NFs inter-company pendentes — emitidas mas nao escrituradas).
            # Somado ao estoque do DESTINO para que odoo_total = estoque + em transito
            # capture o saldo real do grupo (sem perder o que ainda esta em locations
            # transit do Odoo, que o snapshot Odoo filtra por usage='internal').
            et_fb = s.get('em_transito_fb', Decimal('0'))
            et_cd = s.get('em_transito_cd', Decimal('0'))
            et_lf = s.get('em_transito_lf', Decimal('0'))
            est_fb_total = est_fb + et_fb
            est_cd_total = est_cd + et_cd
            est_lf_total = est_lf + et_lf
            odoo_total = est_fb_total + est_cd_total + est_lf_total
            em_transito_total = et_fb + et_cd + et_lf
            pa = s.get('pa_qtd', Decimal('0'))
            componente_pos = s.get('componente_qtd', Decimal('0'))
            componente_apres = -componente_pos

            # MOV = saldo previsto = inicial + compras + pa(Odoo MRP) -
            # componente(Odoo MRP) + vendas. NAO inclui 'consumo'/'producao'
            # locais porque pa/componente_apres ja sao o mesmo evento vindo
            # do snapshot Odoo MRP (apontamentos via _baixar_apontamentos) —
            # incluir ambos = double-count.
            # 'vendas' (FATURAMENTO) ja vem NEGATIVO (reconciliacao_service.py:151
            # grava qtd_movimentacao = -qtd_faturado), entao soma = subtracao.
            # componente_apres ja inverteu o sinal (componente eh consumo).
            mov = inv_total + compras + pa + componente_apres + vendas
            odoo_menos_mov = odoo_total - mov
            sist_menos_mov = sist_total - mov

            nome = (i.get('nome') or s.get('nome') or
                    m.get('nome') or a.get('nome') or '')

            snap_compras = s.get('compras_qtd')
            flag_div = (snap_compras is not None
                        and abs(Decimal(str(snap_compras)) - compras) > Decimal('1'))

            linhas.append({
                'cod_produto': cod,
                'nome_produto': nome,
                'inv_fb': inv_fb, 'inv_cd': inv_cd, 'inv_lf': inv_lf,
                'inv_total': inv_total,
                'compras': compras,
                'pa': pa,
                'componente': componente_apres,
                'vendas': vendas,
                'consumo': consumo,
                'producao': producao,
                'ajuste_local': a.get('local'),
                'ajuste_qtd': a.get('qtd'),
                'ajuste_tipo': a.get('tipo_ajuste'),
                'ajuste_obs': a.get('observacao'),
                'odoo': odoo_total,
                'mov': mov,
                'sist': sist_total,
                'odoo_menos_mov': odoo_menos_mov,
                'sist_menos_mov': sist_menos_mov,
                # Estoque interno do Odoo (location usage='internal') por empresa
                'est_fb': est_fb,
                'est_cd': est_cd,
                'est_lf': est_lf,
                # Em transito por DESTINO (NFs inter-company pendentes — emitidas
                # mas nao escrituradas). Somado a est_<destino> em odoo_total.
                'em_transito_fb': et_fb,
                'em_transito_cd': et_cd,
                'em_transito_lf': et_lf,
                'em_transito_total': em_transito_total,
                # Estoque consolidado por empresa (interno + em transito destino)
                'est_fb_total': est_fb_total,
                'est_cd_total': est_cd_total,
                'est_lf_total': est_lf_total,
                'snapshot_compras': snap_compras,
                'flag_divergencia_compras': flag_div,
            })
        return linhas

    @staticmethod
    def _produtos_inativos_odoo(cods):
        """Retorna set de cod_produto que estao com active=False no Odoo.

        Usa 1 batch search_read com context active_test=False (caso contrario
        Odoo filtra inativos por default e nao retorna nada).
        Silencioso em caso de falha (retorna set vazio — confronto continua).
        """
        if not cods:
            return set()
        try:
            from app.odoo.utils.connection import get_odoo_connection
            odoo = get_odoo_connection()
            prods = odoo.execute_kw(
                'product.product', 'search_read',
                [[['default_code', 'in', list(cods)]]],
                {'fields': ['default_code', 'active'],
                 'context': {'active_test': False}},
            )
            return {str(p['default_code']).strip()
                    for p in prods
                    if not p.get('active', True) and p.get('default_code')}
        except Exception:
            return set()

    @staticmethod
    def _agg_inventario_base(ciclo_id):
        q = db.session.query(
            InventarioBase.cod_produto,
            func.max(InventarioBase.nome_produto),
            func.sum(case((InventarioBase.empresa == 'FB', InventarioBase.qtd),
                          else_=0)),
            func.sum(case((InventarioBase.empresa == 'CD', InventarioBase.qtd),
                          else_=0)),
            func.sum(case((InventarioBase.empresa == 'LF', InventarioBase.qtd),
                          else_=0)),
        ).filter(InventarioBase.ciclo_id == ciclo_id).group_by(InventarioBase.cod_produto)
        return {r[0]: {'nome': r[1], 'fb': r[2] or Decimal('0'),
                       'cd': r[3] or Decimal('0'), 'lf': r[4] or Decimal('0')}
                for r in q.all()}

    @staticmethod
    def _agg_ajustes_ciclicos(ciclo) -> Dict[str, Dict[str, Decimal]]:
        """{cod: {'fb','cd','lf'}} — soma ContagemInventarioItem.ajuste_inventario
        (coluna AJUSTE autoritativa, NÃO o `ajuste`=contagem−qtd_esperada que vai p/ o
        Odoo) por (cod_produto, empresa) das contagens cíclicas CONTABILIZADAS do
        período do inventário completo (spec §6.4).

        Usar ajuste_inventario desacopla a coluna INV/MOV do saldo Odoo do T0: o delta
        somado ao último inventário é exatamente o que o usuário digitou em AJUSTE,
        sem carregar a divergência Odoo↔inventário ("semi-ajustado").

        Período (corte por dia): data_base >= ciclo.data_snapshot e, se houver um
        inventário completo posterior, < a data_snapshot dele. Para o ciclo
        vigente (sem completo posterior), o intervalo é aberto em cima — ou seja,
        simplesmente data_base >= data_snapshot.
        """
        if ciclo is None:
            return {}
        data_inicio = ciclo.data_snapshot
        inicio_dt = datetime.combine(data_inicio, time.min)
        proximo = (CicloInventario.query
                   .filter(CicloInventario.data_snapshot > data_inicio)
                   .order_by(CicloInventario.data_snapshot.asc())
                   .first())
        q = (db.session.query(
                ContagemInventarioItem.cod_produto,
                ContagemInventario.empresa,
                func.sum(ContagemInventarioItem.ajuste_inventario),
            )
            .join(ContagemInventario,
                  ContagemInventarioItem.contagem_id == ContagemInventario.id)
            .filter(ContagemInventario.status == 'CONTABILIZADA',
                    ContagemInventario.data_base >= inicio_dt))
        if proximo is not None:
            fim_dt = datetime.combine(proximo.data_snapshot, time.min)
            q = q.filter(ContagemInventario.data_base < fim_dt)
        q = q.group_by(ContagemInventarioItem.cod_produto, ContagemInventario.empresa)

        out: Dict[str, Dict[str, Decimal]] = {}
        for cod, empresa, soma in q.all():
            d = out.setdefault(cod, {'fb': Decimal('0'), 'cd': Decimal('0'),
                                     'lf': Decimal('0')})
            emp = (empresa or '').lower()
            if emp in d:
                d[emp] += (soma or Decimal('0'))
        return out

    @staticmethod
    def _agg_snapshot(ciclo_id):
        rows = InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo_id).all()
        return {r.cod_produto: {
            'nome': r.nome_produto,
            'estoque_fb': r.estoque_fb or Decimal('0'),
            'estoque_cd': r.estoque_cd or Decimal('0'),
            'estoque_lf': r.estoque_lf or Decimal('0'),
            # EM TRANSITO 2026-05-28: NFs inter-company pendentes por DESTINO
            # (defaults 0 para snapshots pre-2026-05-28).
            'em_transito_fb': getattr(r, 'em_transito_fb', None) or Decimal('0'),
            'em_transito_cd': getattr(r, 'em_transito_cd', None) or Decimal('0'),
            'em_transito_lf': getattr(r, 'em_transito_lf', None) or Decimal('0'),
            'pa_qtd': r.pa_qtd or Decimal('0'),
            'componente_qtd': r.componente_qtd or Decimal('0'),
            'compras_qtd': r.compras_qtd,
            # FREEZE 2026-05-27: MOV congelado no snapshot
            'mov_compras': r.mov_compras or Decimal('0'),
            'mov_vendas': r.mov_vendas or Decimal('0'),
            'mov_consumo': r.mov_consumo or Decimal('0'),
            'mov_producao': r.mov_producao or Decimal('0'),
            'mov_sist_total': r.mov_sist_total or Decimal('0'),
        } for r in rows}

    @staticmethod
    def _snapshot_tem_mov_freezado(snap):
        """True se qualquer linha do snapshot tem mov_* != 0 (foi freezado).

        Snapshots pre-freeze tem todas as cols mov_* = 0 (default) → cai no
        fallback live. Snapshots novos com qualquer movimentacao registrada
        no periodo retornam True e usam o snapshot.
        """
        if not snap:
            return False
        for v in snap.values():
            if (v.get('mov_compras', 0) or v.get('mov_vendas', 0) or
                v.get('mov_consumo', 0) or v.get('mov_producao', 0) or
                v.get('mov_sist_total', 0)):
                return True
        return False

    @staticmethod
    def _movs_do_snapshot(snap):
        """Reconstroi dict de movs no formato do _agg_movimentacoes a partir
        do snapshot. Permite usar o snapshot como source-of-truth do MOV/SIST.
        """
        return {cod: {
            'nome': v.get('nome') or '',
            'compras': v.get('mov_compras') or Decimal('0'),
            'vendas': v.get('mov_vendas') or Decimal('0'),
            'consumo': v.get('mov_consumo') or Decimal('0'),
            'producao': v.get('mov_producao') or Decimal('0'),
            'sist_total': v.get('mov_sist_total') or Decimal('0'),
        } for cod, v in snap.items()}

    @staticmethod
    def _agg_movimentacoes(data_inicio):
        # NOTA: agrupar por cod_produto direto (sem unificação cod_produto_raiz)
        # para bater 100% com a planilha referência do usuário, que usa
        # SUMIFS por cod_produto bruto. Unificação será opção futura.
        cod_raiz = MovimentacaoEstoque.cod_produto.label('raiz')

        # COMPRAS = tipo='ENTRADA' AND local='COMPRA'. Exclui REVERSAO/
        # TRANSFERENCIA/AJUSTE/PALLET (tambem ENTRADA, mas nao compra
        # externa). Alinhado com SnapshotOdooService._baixar_compras
        # (filtra PO partner externo).
        q_periodo = db.session.query(
            cod_raiz,
            func.max(MovimentacaoEstoque.nome_produto),
            func.sum(case(((MovimentacaoEstoque.tipo_movimentacao == 'ENTRADA') &
                           (MovimentacaoEstoque.local_movimentacao == 'COMPRA'),
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'CONSUMO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'PRODUÇÃO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
        ).filter(
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.data_movimentacao >= data_inicio,
        ).group_by(cod_raiz)

        periodo = {r[0]: {
            'nome': r[1],
            'compras': r[2] or Decimal('0'),
            'vendas': r[3] or Decimal('0'),
            'consumo': r[4] or Decimal('0'),
            'producao': r[5] or Decimal('0'),
        } for r in q_periodo.all()}

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
    def _agg_ajustes(ciclo_id):
        rows = AjusteManualInventario.query.filter_by(ciclo_id=ciclo_id).order_by(
            AjusteManualInventario.criado_em).all()
        out = {}
        for r in rows:
            cur = out.setdefault(r.cod_produto, {
                'local': r.local, 'qtd': r.qtd, 'tipo_ajuste': r.tipo_ajuste,
                'observacao': r.observacao or '', 'nome': r.nome_produto or '',
            })
            cur['local'] = r.local
            cur['qtd'] = r.qtd
            cur['tipo_ajuste'] = r.tipo_ajuste
            if r.observacao and r.observacao not in cur['observacao']:
                cur['observacao'] = (cur['observacao'] + ' | ' + r.observacao).strip(' |')
        return out
