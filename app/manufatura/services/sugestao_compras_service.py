"""
Servico de Sugestao de Compras (MRP Simplificado)
==================================================

Para cada componente comprado, calcula:
  DEMANDA = consumo via BOM x ProgramacaoProducao (60 dias)
  ESTOQUE = estoque_atual
  EM_TRANSITO = saldo pedidos + saldo requisicoes
  NECESSIDADE_LIQUIDA = DEMANDA - ESTOQUE - EM_TRANSITO

  Se NECESSIDADE_LIQUIDA > 0:
    QTD_SUGERIDA = ceil(necessidade / lote_minimo) * lote_minimo
    DATA_PEDIR = data_ruptura - lead_time
    URGENCIA = dias_ate_pedir

Autor: Sistema de Fretes
Data: 10/02/2026
"""

import math
import time
import logging
from datetime import date, timedelta
from collections import defaultdict
from typing import Dict, Any, Optional

from sqlalchemy import func, or_

from app import db
from app.manufatura.models import (
    PedidoCompras,
    RequisicaoCompras,
    RequisicaoCompraAlocacao,
    ListaMateriais
)
from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos

logger = logging.getLogger(__name__)


class ServicoSugestaoCompras:
    """
    Servico MRP simplificado para sugestao de compras.
    Usa pre-carga batch para performance (< 3s para todos componentes).
    """

    def calcular_sugestoes(self, dias_horizonte: int = 60) -> Dict[str, Any]:
        """
        Calcula sugestoes de compra para TODOS os componentes comprados.

        Args:
            dias_horizonte: Horizonte de planejamento em dias (default: 60)

        Returns:
            Dict com sugestoes por componente
        """
        t0 = time.time()
        hoje = date.today()
        data_fim = hoje + timedelta(days=dias_horizonte)

        # ========================================
        # PRE-CARGA BATCH (7 queries grandes)
        # ========================================

        # 1. Produtos comprados
        produtos_comprados = CadastroPalletizacao.query.filter_by(
            produto_comprado=True,
            ativo=True
        ).order_by(CadastroPalletizacao.cod_produto).all()

        if not produtos_comprados:
            return {
                'sucesso': True,
                'data_calculo': hoje.isoformat(),
                'horizonte_dias': dias_horizonte,
                'total_sugestoes': 0,
                'sugestoes': [],
                'tempo_calculo_s': round(time.time() - t0, 2)
            }

        todos_cod = [p.cod_produto for p in produtos_comprados]

        # 2. BOMs ativas
        todas_boms = ListaMateriais.query.filter_by(status='ativo').all()
        bom_por_componente = defaultdict(list)
        bom_por_produzido = defaultdict(list)
        for bom in todas_boms:
            bom_por_componente[bom.cod_produto_componente].append(bom)
            bom_por_produzido[bom.cod_produto_produzido].append(bom)

        # 3. Estoques em batch
        estoques_raw = db.session.query(
            MovimentacaoEstoque.cod_produto,
            func.sum(MovimentacaoEstoque.qtd_movimentacao)
        ).filter(
            MovimentacaoEstoque.ativo == True
        ).group_by(MovimentacaoEstoque.cod_produto).all()
        estoque_map = {str(cod): float(qtd or 0) for cod, qtd in estoques_raw}

        # 4. Programacoes futuras
        programacoes = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.data_programacao.between(hoje, data_fim)
        ).all()
        prog_por_produto = defaultdict(list)
        for prog in programacoes:
            prog_por_produto[prog.cod_produto].append(prog)

        # 5. Pedidos de compra abertos (saldo nao recebido)
        pedidos = PedidoCompras.query.filter(
            PedidoCompras.importado_odoo == True,
            PedidoCompras.status_odoo.notin_(['cancel', 'done'])
        ).all()
        pedidos_por_produto = defaultdict(list)
        for p in pedidos:
            pedidos_por_produto[p.cod_produto].append(p)

        # 6. Requisicoes com saldo nao alocado
        requisicoes_com_alocacoes = db.session.query(
            RequisicaoCompras,
            func.coalesce(func.sum(RequisicaoCompraAlocacao.qtd_alocada), 0).label('total_alocado')
        ).outerjoin(
            RequisicaoCompraAlocacao,
            RequisicaoCompraAlocacao.requisicao_compra_id == RequisicaoCompras.id
        ).filter(
            RequisicaoCompras.importado_odoo == True,
            or_(
                RequisicaoCompras.status.is_(None),
                ~RequisicaoCompras.status.in_(['Cancelada', 'Rejeitada', 'Concluída'])
            ),
            or_(
                RequisicaoCompras.status_requisicao.is_(None),
                ~RequisicaoCompras.status_requisicao.in_(['rejected', 'cancel', 'done'])
            )
        ).group_by(RequisicaoCompras.id).all()

        req_saldo_por_produto = defaultdict(float)
        for req, total_alocado in requisicoes_com_alocacoes:
            saldo = float(req.qtd_produto_requisicao) - float(total_alocado)
            if saldo > 0:
                req_saldo_por_produto[req.cod_produto] += saldo

        # 7. Mapa intermediarios
        produtos_produzidos_set = {p.cod_produto for p in CadastroPalletizacao.query.filter_by(
            produto_produzido=True, ativo=True
        ).all()}
        usados_como_componente = {b.cod_produto_componente for b in todas_boms}
        tem_bom_propria = {b.cod_produto_produzido for b in todas_boms}
        intermediarios = produtos_produzidos_set & usados_como_componente & tem_bom_propria

        # 8. Unificacao de codigos
        try:
            mapa_unificacao = UnificacaoCodigos.get_todos_codigos_relacionados_batch(todos_cod)
        except AttributeError:
            mapa_unificacao = {cod: UnificacaoCodigos.get_todos_codigos_relacionados(cod) for cod in todos_cod}

        # ========================================
        # LOOP POR COMPONENTE (sem queries)
        # ========================================

        sugestoes = []

        for produto in produtos_comprados:
            cod = produto.cod_produto
            codigos_unificados = mapa_unificacao.get(cod, [cod])

            # Estoque atual (soma de codigos unificados)
            estoque_atual = sum(estoque_map.get(str(c), 0) for c in codigos_unificados)

            # Em transito: pedidos (saldo nao recebido)
            em_transito_pedidos = 0.0
            for c in codigos_unificados:
                for ped in pedidos_por_produto.get(c, []):
                    saldo_ped = float(ped.qtd_produto_pedido) - float(ped.qtd_recebida or 0)
                    if saldo_ped > 0:
                        em_transito_pedidos += saldo_ped

            # Em transito: requisicoes (saldo nao alocado)
            em_transito_req = sum(req_saldo_por_produto.get(c, 0) for c in codigos_unificados)

            em_transito_total = em_transito_pedidos + em_transito_req

            # Demanda 60 dias (consumo via BOM x Programacao)
            demanda = self._calcular_demanda_batch(
                cod, codigos_unificados, bom_por_componente,
                prog_por_produto, intermediarios, bom_por_produzido,
                hoje, data_fim
            )

            # Necessidade liquida
            necessidade_liquida = demanda - estoque_atual - em_transito_total

            # Sugestao de compra
            lote_minimo = produto.lote_minimo_compra or 1
            lead_time_dias = produto.lead_time or 0

            if necessidade_liquida > 0:
                qtd_sugerida = math.ceil(necessidade_liquida / lote_minimo) * lote_minimo
            else:
                qtd_sugerida = 0

            # Data de ruptura estimada (quando estoque + entradas < consumo acumulado)
            data_ruptura = self._estimar_data_ruptura(
                cod, codigos_unificados, estoque_atual,
                bom_por_componente, prog_por_produto,
                intermediarios, bom_por_produzido,
                pedidos_por_produto, hoje, data_fim
            )

            # Data pedir = data_ruptura - lead_time
            data_pedir = None
            dias_ate_pedir = None
            if data_ruptura and lead_time_dias > 0:
                data_pedir = data_ruptura - timedelta(days=lead_time_dias)
                dias_ate_pedir = (data_pedir - hoje).days
            elif data_ruptura:
                data_pedir = data_ruptura
                dias_ate_pedir = (data_pedir - hoje).days

            # Urgencia
            if dias_ate_pedir is not None:
                if dias_ate_pedir < 0:
                    urgencia = 'critico'
                elif dias_ate_pedir <= 7:
                    urgencia = 'alerta'
                else:
                    urgencia = 'ok'
            elif necessidade_liquida > 0:
                urgencia = 'alerta'
            else:
                urgencia = 'ok'

            sugestoes.append({
                'cod_produto': cod,
                'nome_produto': produto.nome_produto,
                'estoque_atual': round(estoque_atual, 2),
                'demanda_60d': round(demanda, 2),
                'em_transito': round(em_transito_total, 2),
                'em_transito_pedidos': round(em_transito_pedidos, 2),
                'em_transito_requisicoes': round(em_transito_req, 2),
                'necessidade_liquida': round(necessidade_liquida, 2),
                'lote_minimo': lote_minimo,
                'qtd_sugerida': qtd_sugerida,
                'lead_time': lead_time_dias,
                'data_ruptura': data_ruptura.isoformat() if data_ruptura else None,
                'data_pedir': data_pedir.isoformat() if data_pedir else None,
                'dias_ate_pedir': dias_ate_pedir,
                'urgencia': urgencia,
                'tipo_materia_prima': produto.tipo_materia_prima,
                'categoria_produto': produto.categoria_produto,
                'tipo_embalagem': produto.tipo_embalagem
            })

        tempo = round(time.time() - t0, 2)
        logger.info(f"ServicoSugestaoCompras.calcular_sugestoes: {tempo}s para {len(sugestoes)} componentes")

        return {
            'sucesso': True,
            'data_calculo': hoje.isoformat(),
            'horizonte_dias': dias_horizonte,
            'total_sugestoes': len(sugestoes),
            'sugestoes': sugestoes,
            'tempo_calculo_s': tempo
        }

    def _calcular_demanda_batch(
        self,
        cod_produto: str,
        codigos_unificados: list,
        bom_por_componente: dict,
        prog_por_produto: dict,
        intermediarios: set,
        bom_por_produzido: dict,
        data_inicio: date,
        data_fim: date
    ) -> float:
        """
        Calcula demanda total de um componente via BOM x Programacao.
        Usa dados pre-carregados (sem queries).
        Suporta intermediarios recursivamente.
        """
        demanda_total = 0.0
        visitados = set()

        for c in codigos_unificados:
            boms = bom_por_componente.get(c, [])
            for bom in boms:
                cod_pai = bom.cod_produto_produzido
                qtd_base = float(bom.qtd_utilizada)

                # Buscar programacoes (diretas ou upstream)
                progs_e_fatores = self._buscar_progs_upstream_batch(
                    cod_pai, qtd_base, prog_por_produto,
                    intermediarios, bom_por_componente, bom_por_produzido,
                    data_inicio, data_fim, visitados.copy()
                )

                for prog, fator in progs_e_fatores:
                    demanda_total += float(prog.qtd_programada) * fator

        return demanda_total

    def _buscar_progs_upstream_batch(
        self,
        cod_produto: str,
        fator_mult: float,
        prog_por_produto: dict,
        intermediarios: set,
        bom_por_componente: dict,
        bom_por_produzido: dict,
        data_inicio: date,
        data_fim: date,
        visitados: set
    ) -> list:
        """
        Busca programacoes upstream recursivamente usando dados pre-carregados.
        """
        if cod_produto in visitados:
            return []
        visitados.add(cod_produto)

        resultado = []

        # Verificar programacoes diretas
        progs = prog_por_produto.get(cod_produto, [])
        progs_no_periodo = [p for p in progs if data_inicio <= p.data_programacao <= data_fim]

        if progs_no_periodo:
            for prog in progs_no_periodo:
                resultado.append((prog, fator_mult))
            return resultado

        # Se intermediario sem programacao, subir na hierarquia via BOM
        if cod_produto in intermediarios:
            # Buscar BOMs onde cod_produto e usado como COMPONENTE (upstream)
            boms_upstream = bom_por_componente.get(cod_produto, [])

            for bom in boms_upstream:
                fator_acum = fator_mult * float(bom.qtd_utilizada)
                progs_up = self._buscar_progs_upstream_batch(
                    bom.cod_produto_produzido, fator_acum,
                    prog_por_produto, intermediarios,
                    bom_por_componente, bom_por_produzido,
                    data_inicio, data_fim, visitados
                )
                resultado.extend(progs_up)

        return resultado

    def _estimar_data_ruptura(
        self,
        cod_produto: str,
        codigos_unificados: list,
        estoque_atual: float,
        bom_por_componente: dict,
        prog_por_produto: dict,
        intermediarios: set,
        bom_por_produzido: dict,
        pedidos_por_produto: dict,
        data_inicio: date,
        data_fim: date
    ) -> Optional[date]:
        """
        Estima a data em que o estoque zera, considerando consumo diario
        e entradas de pedidos de compra.
        """
        # Calcular consumo por dia
        consumo_por_dia = defaultdict(float)

        for c in codigos_unificados:
            boms = bom_por_componente.get(c, [])
            for bom in boms:
                cod_pai = bom.cod_produto_produzido
                qtd_base = float(bom.qtd_utilizada)

                progs_e_fatores = self._buscar_progs_upstream_batch(
                    cod_pai, qtd_base, prog_por_produto,
                    intermediarios, bom_por_componente, bom_por_produzido,
                    data_inicio, data_fim, set()
                )

                for prog, fator in progs_e_fatores:
                    consumo_por_dia[prog.data_programacao] += float(prog.qtd_programada) * fator

        # Calcular entradas por dia (pedidos de compra)
        entradas_por_dia = defaultdict(float)
        for c in codigos_unificados:
            for ped in pedidos_por_produto.get(c, []):
                saldo_ped = float(ped.qtd_produto_pedido) - float(ped.qtd_recebida or 0)
                if saldo_ped > 0 and ped.data_pedido_previsao:
                    entradas_por_dia[ped.data_pedido_previsao] += saldo_ped

        # Simular dia a dia
        saldo = estoque_atual
        data_atual = data_inicio

        while data_atual <= data_fim:
            entrada_dia = entradas_por_dia.get(data_atual, 0)
            consumo_dia = consumo_por_dia.get(data_atual, 0)

            saldo = saldo + entrada_dia - consumo_dia

            if saldo < 0:
                return data_atual

            data_atual += timedelta(days=1)

        return None  # Sem ruptura no horizonte
