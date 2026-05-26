"""Agregador principal do Relatório de Confronto de Inventário."""
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy import func, case, and_
from app import db
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo,
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
        movs = ConfrontoService._agg_movimentacoes(data_inicio)
        ajustes = ConfrontoService._agg_ajustes(ciclo_id)

        cods = set(inv.keys()) | set(snap.keys()) | set(movs.keys()) | set(ajustes.keys())

        linhas = []
        for cod in sorted(cods):
            i = inv.get(cod, {})
            s = snap.get(cod, {})
            m = movs.get(cod, {})
            a = ajustes.get(cod, {})

            inv_fb = i.get('fb', Decimal('0'))
            inv_cd = i.get('cd', Decimal('0'))
            inv_lf = i.get('lf', Decimal('0'))
            inv_total = inv_fb + inv_cd + inv_lf

            compras = m.get('compras', Decimal('0'))
            vendas = m.get('vendas', Decimal('0'))
            consumo = m.get('consumo', Decimal('0'))
            producao = m.get('producao', Decimal('0'))
            sist_total = m.get('sist_total', Decimal('0'))

            est_fb = s.get('estoque_fb', Decimal('0'))
            est_cd = s.get('estoque_cd', Decimal('0'))
            est_lf = s.get('estoque_lf', Decimal('0'))
            odoo_total = est_fb + est_cd + est_lf
            pa = s.get('pa_qtd', Decimal('0'))
            componente_pos = s.get('componente_qtd', Decimal('0'))
            componente_apres = -componente_pos

            mov = inv_total + compras + pa + componente_apres
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
                'est_fb': est_fb,
                'est_cd': est_cd,
                'est_lf': est_lf,
                'snapshot_compras': snap_compras,
                'flag_divergencia_compras': flag_div,
            })
        return linhas

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
    def _agg_snapshot(ciclo_id):
        rows = InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo_id).all()
        return {r.cod_produto: {
            'nome': r.nome_produto,
            'estoque_fb': r.estoque_fb or Decimal('0'),
            'estoque_cd': r.estoque_cd or Decimal('0'),
            'estoque_lf': r.estoque_lf or Decimal('0'),
            'pa_qtd': r.pa_qtd or Decimal('0'),
            'componente_qtd': r.componente_qtd or Decimal('0'),
            'compras_qtd': r.compras_qtd,
        } for r in rows}

    @staticmethod
    def _agg_movimentacoes(data_inicio):
        cod_raiz = func.coalesce(
            MovimentacaoEstoque.cod_produto_raiz, MovimentacaoEstoque.cod_produto
        ).label('raiz')

        q_periodo = db.session.query(
            cod_raiz,
            func.max(MovimentacaoEstoque.nome_produto),
            func.sum(case((and_(
                MovimentacaoEstoque.tipo_movimentacao == 'ENTRADA',
                MovimentacaoEstoque.local_movimentacao == 'COMPRA',
            ), MovimentacaoEstoque.qtd_movimentacao), else_=0)),
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
