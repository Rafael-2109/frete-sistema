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
from typing import Dict, Any, Optional, Tuple

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

    # ========================================
    # HELPERS PRIVADOS (reutilizados pelos modais)
    # ========================================

    def _calcular_consumo_por_dia(
        self,
        cod_produto: str,
        codigos_unificados: list,
        data_inicio: date,
        data_fim: date
    ) -> Dict[date, float]:
        """
        Calcula consumo previsto dia-a-dia via BOM x ProgramacaoProducao.
        Retorna dict[date, float] com consumo por dia.
        """
        # Carregar BOMs ativas
        todas_boms = ListaMateriais.query.filter_by(status='ativo').all()
        bom_por_componente = defaultdict(list)
        bom_por_produzido = defaultdict(list)
        for bom in todas_boms:
            bom_por_componente[bom.cod_produto_componente].append(bom)
            bom_por_produzido[bom.cod_produto_produzido].append(bom)

        # Carregar programacoes no periodo
        programacoes = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.data_programacao.between(data_inicio, data_fim)
        ).all()
        prog_por_produto = defaultdict(list)
        for prog in programacoes:
            prog_por_produto[prog.cod_produto].append(prog)

        # Mapa intermediarios
        produtos_produzidos_set = {p.cod_produto for p in CadastroPalletizacao.query.filter_by(
            produto_produzido=True, ativo=True
        ).all()}
        usados_como_componente = {b.cod_produto_componente for b in todas_boms}
        tem_bom_propria = {b.cod_produto_produzido for b in todas_boms}
        intermediarios = produtos_produzidos_set & usados_como_componente & tem_bom_propria

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

        return dict(consumo_por_dia)

    def _calcular_entradas_por_dia(
        self,
        codigos_unificados: list,
        data_inicio: date,
        data_fim: date
    ) -> Tuple[Dict[date, float], float]:
        """
        Calcula entradas previstas dia-a-dia via PedidoCompras abertos.

        POs com previsao anterior a data_inicio (atrasados) sao projetados
        como chegada em data_inicio (D0), pois humanos controlam os pedidos
        e provavelmente ainda chegarao.

        Returns:
            Tuple[dict[date, float], float]:
                - entradas_por_dia: dict com entradas por dia
                - total_atrasado: soma dos saldos de POs atrasados (projetados em D0)
        """
        pedidos = PedidoCompras.query.filter(
            PedidoCompras.importado_odoo == True,
            PedidoCompras.status_odoo.notin_(['cancel', 'done']),
            PedidoCompras.cod_produto.in_(codigos_unificados),
            PedidoCompras.data_pedido_previsao.isnot(None),
            PedidoCompras.data_pedido_previsao <= data_fim
        ).all()

        entradas_por_dia = defaultdict(float)
        total_atrasado = 0.0
        for ped in pedidos:
            saldo_ped = float(ped.qtd_produto_pedido) - float(ped.qtd_recebida or 0)
            if saldo_ped > 0:
                if ped.data_pedido_previsao < data_inicio:
                    # PO atrasado: projetar chegada em D0 (hoje)
                    entradas_por_dia[data_inicio] += saldo_ped
                    total_atrasado += saldo_ped
                else:
                    entradas_por_dia[ped.data_pedido_previsao] += saldo_ped

        return dict(entradas_por_dia), total_atrasado

    # ========================================
    # METODOS PUBLICOS PARA MODAIS
    # ========================================

    def buscar_em_transito(self, cod_produto: str) -> Dict[str, Any]:
        """
        Modal 1: Detalha POs e Requisicoes em transito para um produto.
        """
        # Resolver codigos unificados
        codigos_unificados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
        if not codigos_unificados:
            codigos_unificados = [cod_produto]

        # Buscar produto para nome
        produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = produto.nome_produto if produto else cod_produto

        # 1. Pedidos de Compra abertos
        pedidos = PedidoCompras.query.filter(
            PedidoCompras.importado_odoo == True,
            PedidoCompras.status_odoo.notin_(['cancel', 'done']),
            PedidoCompras.cod_produto.in_(codigos_unificados)
        ).order_by(PedidoCompras.data_pedido_previsao).all()

        hoje = date.today()

        lista_pedidos = []
        total_pedidos_saldo = 0.0
        total_pedidos_atrasados = 0
        for ped in pedidos:
            saldo = float(ped.qtd_produto_pedido) - float(ped.qtd_recebida or 0)
            if saldo > 0:
                total_pedidos_saldo += saldo
                atrasado = (
                    ped.data_pedido_previsao is not None
                    and ped.data_pedido_previsao < hoje
                )
                sem_previsao = ped.data_pedido_previsao is None
                if atrasado:
                    total_pedidos_atrasados += 1
                lista_pedidos.append({
                    'num_pedido': ped.num_pedido,
                    'fornecedor': ped.raz_social or '-',
                    'cod_produto': ped.cod_produto,
                    'qtd_pedida': round(float(ped.qtd_produto_pedido), 2),
                    'qtd_recebida': round(float(ped.qtd_recebida or 0), 2),
                    'saldo': round(saldo, 2),
                    'status': ped.status_odoo or '-',
                    'previsao': ped.data_pedido_previsao.isoformat() if ped.data_pedido_previsao else None,
                    'data_criacao': ped.data_pedido_criacao.isoformat() if ped.data_pedido_criacao else None,
                    'atrasado': atrasado,
                    'sem_previsao': sem_previsao
                })

        # 2. Requisicoes de Compra com saldo
        requisicoes_com_alocacoes = db.session.query(
            RequisicaoCompras,
            func.coalesce(func.sum(RequisicaoCompraAlocacao.qtd_alocada), 0).label('total_alocado')
        ).outerjoin(
            RequisicaoCompraAlocacao,
            RequisicaoCompraAlocacao.requisicao_compra_id == RequisicaoCompras.id
        ).filter(
            RequisicaoCompras.importado_odoo == True,
            RequisicaoCompras.cod_produto.in_(codigos_unificados),
            or_(
                RequisicaoCompras.status.is_(None),
                ~RequisicaoCompras.status.in_(['Cancelada', 'Rejeitada', 'Concluída'])
            ),
            or_(
                RequisicaoCompras.status_requisicao.is_(None),
                ~RequisicaoCompras.status_requisicao.in_(['rejected', 'cancel', 'done'])
            )
        ).group_by(RequisicaoCompras.id).all()

        lista_requisicoes = []
        total_req_saldo = 0.0
        total_req_atrasadas = 0
        for req, total_alocado in requisicoes_com_alocacoes:
            saldo = float(req.qtd_produto_requisicao) - float(total_alocado)
            if saldo > 0:
                total_req_saldo += saldo
                atrasada = (
                    req.data_requisicao_solicitada is not None
                    and req.data_requisicao_solicitada < hoje
                )
                if atrasada:
                    total_req_atrasadas += 1
                lista_requisicoes.append({
                    'num_requisicao': req.num_requisicao,
                    'cod_produto': req.cod_produto,
                    'qtd_requisitada': round(float(req.qtd_produto_requisicao), 2),
                    'qtd_alocada': round(float(total_alocado), 2),
                    'saldo': round(saldo, 2),
                    'status': req.status or '-',
                    'status_requisicao': req.status_requisicao or '-',
                    'data_solicitada': req.data_requisicao_solicitada.isoformat() if req.data_requisicao_solicitada else None,
                    'data_criacao': req.data_requisicao_criacao.isoformat() if req.data_requisicao_criacao else None,
                    'atrasada': atrasada
                })

        return {
            'sucesso': True,
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'codigos_unificados': codigos_unificados,
            'pedidos': lista_pedidos,
            'requisicoes': lista_requisicoes,
            'totais': {
                'total_pedidos': len(lista_pedidos),
                'total_requisicoes': len(lista_requisicoes),
                'saldo_pedidos': round(total_pedidos_saldo, 2),
                'saldo_requisicoes': round(total_req_saldo, 2),
                'total_em_transito': round(total_pedidos_saldo + total_req_saldo, 2),
                'pedidos_atrasados': total_pedidos_atrasados,
                'requisicoes_atrasadas': total_req_atrasadas
            }
        }

    def projetar_cardex(
        self,
        cod_produto: str,
        dia_inicio: int = 0,
        dia_fim: int = 30
    ) -> Dict[str, Any]:
        """
        Modal 2: Projecao dia-a-dia do cardex (estoque projetado).
        """
        hoje = date.today()
        data_inicio = hoje + timedelta(days=dia_inicio)
        data_fim_abs = hoje + timedelta(days=dia_fim)

        # Resolver codigos unificados
        codigos_unificados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
        if not codigos_unificados:
            codigos_unificados = [cod_produto]

        # Buscar produto
        produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = produto.nome_produto if produto else cod_produto
        lead_time = produto.lead_time if produto else 0
        lote_minimo = produto.lote_minimo_compra if produto else 1
        lead_time = lead_time or 0
        lote_minimo = lote_minimo or 1

        # Estoque atual
        estoques_raw = db.session.query(
            func.sum(MovimentacaoEstoque.qtd_movimentacao)
        ).filter(
            MovimentacaoEstoque.ativo == True,
            MovimentacaoEstoque.cod_produto.in_(codigos_unificados)
        ).scalar()
        estoque_atual = float(estoques_raw or 0)

        # Consumo e entradas para horizonte completo (de D0 ate dia_fim)
        consumo = self._calcular_consumo_por_dia(cod_produto, codigos_unificados, hoje, data_fim_abs)
        entradas, total_atrasado = self._calcular_entradas_por_dia(codigos_unificados, hoje, data_fim_abs)

        # Simular dia a dia
        projecao = []
        saldo = estoque_atual
        menor_saldo = estoque_atual

        data_atual = hoje
        while data_atual <= data_fim_abs:
            consumo_dia = consumo.get(data_atual, 0)
            entrada_dia = entradas.get(data_atual, 0)
            saldo_inicial = saldo
            saldo = saldo - consumo_dia + entrada_dia
            menor_saldo = min(menor_saldo, saldo)

            # So incluir dias dentro do range solicitado
            if data_atual >= data_inicio:
                projecao.append({
                    'data': data_atual.isoformat(),
                    'estoque_inicial': round(saldo_inicial, 2),
                    'consumo': round(consumo_dia, 2),
                    'chegada': round(entrada_dia, 2),
                    'chegada_atrasada': round(total_atrasado, 2) if data_atual == hoje else 0,
                    'saldo_final': round(saldo, 2)
                })

            data_atual += timedelta(days=1)

        return {
            'sucesso': True,
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'estoque_atual': round(estoque_atual, 2),
            'lead_time': lead_time,
            'lote_minimo': lote_minimo,
            'menor_saldo': round(menor_saldo, 2),
            'dia_inicio': dia_inicio,
            'dia_fim': dia_fim,
            'projecao': projecao
        }

    def sugestao_inteligente(
        self,
        cod_produto: str,
        dia_inicio: int = 0,
        dia_fim: int = 30
    ) -> Dict[str, Any]:
        """
        Modal 3: Projecao dia-a-dia com sugestoes automaticas de compra.
        Quando saldo fica negativo, gera sugestao arredondada ao lote minimo
        com data_pedir = data_chegada - lead_time.
        """
        hoje = date.today()
        data_inicio = hoje + timedelta(days=dia_inicio)
        data_fim_abs = hoje + timedelta(days=dia_fim)
        # Horizonte estendido para capturar todas as sugestoes
        horizonte_max = max(dia_fim, 180)
        data_horizonte = hoje + timedelta(days=horizonte_max)

        # Resolver codigos unificados
        codigos_unificados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
        if not codigos_unificados:
            codigos_unificados = [cod_produto]

        # Buscar produto
        produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = produto.nome_produto if produto else cod_produto
        lead_time = produto.lead_time if produto else 0
        lote_minimo = produto.lote_minimo_compra if produto else 1
        lead_time = lead_time or 0
        lote_minimo = max(lote_minimo or 1, 1)

        # Estoque atual
        estoques_raw = db.session.query(
            func.sum(MovimentacaoEstoque.qtd_movimentacao)
        ).filter(
            MovimentacaoEstoque.ativo == True,
            MovimentacaoEstoque.cod_produto.in_(codigos_unificados)
        ).scalar()
        estoque_atual = float(estoques_raw or 0)

        # Consumo e entradas para horizonte completo
        consumo = self._calcular_consumo_por_dia(cod_produto, codigos_unificados, hoje, data_horizonte)
        entradas, total_atrasado = self._calcular_entradas_por_dia(codigos_unificados, hoje, data_horizonte)

        # Algoritmo de sugestao inteligente
        saldo = estoque_atual
        sugestoes_chegam_dia = defaultdict(float)
        sugestoes = []

        # Dados dia-a-dia para todo horizonte
        projecao_completa = {}

        for day_offset in range(0, horizonte_max + 1):
            dia = hoje + timedelta(days=day_offset)
            consumo_dia = consumo.get(dia, 0)
            entrada_dia = entradas.get(dia, 0)
            sugestao_chegada_dia = sugestoes_chegam_dia.get(dia, 0)

            saldo_inicial = saldo
            saldo = saldo - consumo_dia + entrada_dia + sugestao_chegada_dia

            if saldo < 0:
                necessidade = abs(saldo)
                qtd = math.ceil(necessidade / lote_minimo) * lote_minimo
                data_chegada = dia
                data_pedir = dia - timedelta(days=lead_time)
                dias_ate_pedir = (data_pedir - hoje).days

                sugestoes_chegam_dia[dia] += qtd
                saldo += qtd

                sugestoes.append({
                    'data_pedir': data_pedir.isoformat(),
                    'data_chegada': data_chegada.isoformat(),
                    'dias_ate_pedir': dias_ate_pedir,
                    'qtd_comprar': round(qtd, 2),
                    'necessidade': round(necessidade, 2),
                    'atrasado': dias_ate_pedir < 0
                })

            # RE-LER apos potencial adicao de sugestao (fix: leitura pre-adicao)
            sugestao_total_dia = sugestoes_chegam_dia.get(dia, 0)

            projecao_completa[dia] = {
                'data': dia.isoformat(),
                'estoque_inicial': round(saldo_inicial, 2),
                'consumo': round(consumo_dia, 2),
                'chegada_po': round(entrada_dia, 2),
                'chegada_sugestao': round(sugestao_total_dia, 2),
                'chegada_atrasada': round(total_atrasado, 2) if dia == hoje else 0,
                'saldo_final': round(saldo, 2),
                'tem_sugestao': sugestao_total_dia > 0
            }

        # Slice apenas o periodo solicitado
        projecao = []
        data_atual = data_inicio
        while data_atual <= data_fim_abs:
            if data_atual in projecao_completa:
                projecao.append(projecao_completa[data_atual])
            data_atual += timedelta(days=1)

        return {
            'sucesso': True,
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'estoque_atual': round(estoque_atual, 2),
            'lead_time': lead_time,
            'lote_minimo': lote_minimo,
            'dia_inicio': dia_inicio,
            'dia_fim': dia_fim,
            'sugestoes': sugestoes,
            'total_sugestoes': len(sugestoes),
            'projecao': projecao
        }
