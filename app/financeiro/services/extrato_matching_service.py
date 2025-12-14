# -*- coding: utf-8 -*-
"""
Serviço de Matching - Extrato vs Títulos a Receber
==================================================

Encontra títulos candidatos para conciliação com linhas de extrato.

Estratégia de matching (do mais restritivo ao mais flexível):
1. CNPJ exato + Valor exato (100%)
2. CNPJ exato + Valor aproximado ±0.01 (95%)
3. CNPJ RAIZ (grupo empresarial) + Valor exato (90%) ← NOVO
4. CNPJ RAIZ + Valor aproximado (85%) ← NOVO
5. CNPJ exato + Valor diferente - candidatos múltiplos (80%)
6. Sem CNPJ + Valor exato (70%) - quando CNPJ não foi extraído

CASOS ESPECIAIS (configuráveis):
- Grupos empresariais: Matriz paga por filiais (busca por raiz do CNPJ)
- Descontos duplicados: Ignorar títulos com vencimento 01/01/2000
- Pagamentos parciais: Valor menor que o título

Autor: Sistema de Fretes
Data: 2025-12-11
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from app import db
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAReceber

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÕES DE MATCHING (ajustáveis)
# =============================================================================

# Tolerância para valor "exato" (em reais)
TOLERANCIA_VALOR = 0.02  # 2 centavos

# Score mínimo para considerar match automático
SCORE_MINIMO_AUTO = 95

# Ignorar títulos com esta data de vencimento (bug do Odoo com descontos)
DATA_VENCIMENTO_IGNORAR = date(2000, 1, 1)

# Limite de candidatos para retornar
LIMITE_CANDIDATOS = 50

# =============================================================================
# CONFIGURAÇÕES DE VENCIMENTO (ajustáveis)
# =============================================================================
# Cliente pagou ATRASADO (mais comum):
#   - Até 4 dias de atraso: 0% desconto (normal)
#   - Acima de 4 dias: -1% por dia adicional
#
# Cliente pagou ANTECIPADO (raro):
#   - Até 3 dias antecipado: -2% desconto
#   - 4 a 7 dias antecipado: -4% desconto
#   - Acima de 7 dias: -4% base + -1% por dia adicional

DIAS_ATRASO_TOLERANCIA = 4  # Dias de atraso sem penalidade
DIAS_ANTECIPADO_LEVE = 3    # Até 3 dias antecipado = -2%
DIAS_ANTECIPADO_MEDIO = 7   # 4-7 dias antecipado = -4%


class ExtratoMatchingService:
    """
    Serviço para encontrar títulos candidatos para conciliação.
    """

    def __init__(self):
        self.estatisticas = {
            'processados': 0,
            'com_match': 0,
            'multiplos': 0,
            'sem_match': 0
        }

    def executar_matching_lote(self, lote_id: int) -> Dict:
        """
        Executa o matching para todos os itens pendentes de um lote.

        Args:
            lote_id: ID do lote

        Returns:
            Dict com estatísticas do matching
        """
        lote = ExtratoLote.query.get(lote_id)
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado")

        logger.info(f"=" * 60)
        logger.info(f"EXECUTANDO MATCHING - Lote {lote_id}")
        logger.info(f"=" * 60)

        # Buscar itens pendentes
        itens = ExtratoItem.query.filter_by(
            lote_id=lote_id,
            status_match='PENDENTE'
        ).all()

        logger.info(f"Itens a processar: {len(itens)}")

        for item in itens:
            try:
                self._processar_item_matching(item)
                self.estatisticas['processados'] += 1
            except Exception as e:
                logger.error(f"Erro no item {item.id}: {e}")
                item.status_match = 'ERRO'
                item.mensagem = str(e)

            db.session.commit()

        logger.info(f"Matching concluído: {self.estatisticas}")

        return self.estatisticas

    def _processar_item_matching(self, item: ExtratoItem) -> None:
        """
        Processa o matching de um item individual.
        """
        logger.info(f"Processando item {item.id}: R$ {item.valor} - CNPJ: {item.cnpj_pagador}")

        # Buscar candidatos
        candidatos = self.buscar_titulos_candidatos(
            cnpj=item.cnpj_pagador,
            valor=item.valor,
            data_pagamento=item.data_transacao
        )

        if not candidatos:
            item.status_match = 'SEM_MATCH'
            item.mensagem = 'Nenhum título encontrado para CNPJ/valor informados'
            self.estatisticas['sem_match'] += 1
            return

        # Verificar se tem match único com score alto
        matches_altos = [c for c in candidatos if c['score'] >= SCORE_MINIMO_AUTO]

        if len(matches_altos) == 1:
            # Match único encontrado
            match = matches_altos[0]
            self._vincular_titulo(item, match)
            item.status_match = 'MATCH_ENCONTRADO'
            self.estatisticas['com_match'] += 1
            logger.info(f"  Match único: NF {match['titulo_nf']} P{match['parcela']} (score={match['score']})")

        elif len(matches_altos) > 1:
            # Múltiplos matches - precisa decisão manual
            item.status_match = 'MULTIPLOS_MATCHES'
            item.set_matches_candidatos(candidatos)
            item.mensagem = f'{len(matches_altos)} títulos encontrados com score >= {SCORE_MINIMO_AUTO}'
            self.estatisticas['multiplos'] += 1
            logger.info(f"  Múltiplos matches: {len(matches_altos)} candidatos")

        elif candidatos:
            # Candidatos com score baixo - precisa revisão
            item.status_match = 'MULTIPLOS_MATCHES'
            item.set_matches_candidatos(candidatos)
            item.mensagem = f'{len(candidatos)} candidato(s) encontrado(s) com score < {SCORE_MINIMO_AUTO}'
            self.estatisticas['multiplos'] += 1
            logger.info(f"  Candidatos com score baixo: {len(candidatos)}")

    def buscar_titulos_candidatos(
        self,
        cnpj: Optional[str],
        valor: float,
        data_pagamento: Optional[date] = None
    ) -> List[Dict]:
        """
        Busca títulos candidatos para um recebimento.

        Estratégia hierárquica:
        1. CNPJ exato - maior confiança
        2. CNPJ raiz (grupo empresarial) - quando matriz paga por filial
        3. Apenas valor - quando não tem CNPJ

        Args:
            cnpj: CNPJ do pagador (pode ser None)
            valor: Valor do recebimento
            data_pagamento: Data do pagamento

        Returns:
            Lista de candidatos ordenada por score (desc)
        """
        candidatos = []

        if cnpj:
            # 1. Busca por CNPJ exato
            candidatos = self._buscar_por_cnpj_exato(cnpj, valor, data_pagamento)

            # 2. Se não encontrou exato, busca por raiz do CNPJ (grupo empresarial)
            if not candidatos:
                candidatos = self._buscar_por_cnpj_raiz(cnpj, valor, data_pagamento)

        # 3. Se ainda não encontrou, busca por valor (mais arriscado)
        if not candidatos and valor > 0:
            candidatos = self._buscar_por_valor(valor, data_pagamento)

        # Ordenar por score decrescente
        candidatos.sort(key=lambda x: x['score'], reverse=True)

        return candidatos[:LIMITE_CANDIDATOS]

    def _buscar_por_cnpj_exato(self, cnpj: str, valor: float, data_pagamento: Optional[date] = None) -> List[Dict]:
        """
        Busca títulos pelo CNPJ EXATO do cliente.
        Score mais alto pois é match perfeito de CNPJ.
        """
        cnpj_limpo = self._normalizar_cnpj(cnpj)

        # Buscar títulos não pagos
        titulos = ContasAReceber.query.filter(
            ContasAReceber.parcela_paga == False,
            ContasAReceber.cnpj.isnot(None)
        ).all()

        candidatos = []

        for titulo in titulos:
            titulo_cnpj = self._normalizar_cnpj(titulo.cnpj)

            # Match exato de CNPJ
            if titulo_cnpj != cnpj_limpo:
                continue

            # Ignorar títulos com vencimento 01/01/2000 (bug desconto duplicado)
            if titulo.vencimento == DATA_VENCIMENTO_IGNORAR:
                continue

            # Ignorar NFs canceladas
            if titulo.nf_cancelada:
                continue

            # Calcular score baseado no valor
            score, criterio, diferenca = self._calcular_score_valor(valor, titulo.valor_titulo or 0)

            # Aplicar desconto de vencimento
            desconto_venc, criterio_venc = self._calcular_desconto_vencimento(data_pagamento, titulo.vencimento)
            score = max(0, score - desconto_venc)
            if criterio_venc:
                criterio = f'{criterio}+{criterio_venc}'

            candidatos.append({
                'titulo_id': titulo.id,
                'titulo_nf': titulo.titulo_nf,
                'parcela': titulo.parcela,
                'valor': titulo.valor_titulo,
                'vencimento': titulo.vencimento.strftime('%d/%m/%Y') if titulo.vencimento else None,
                'vencimento_date': titulo.vencimento,
                'cliente': titulo.raz_social_red or titulo.raz_social,
                'cnpj': titulo.cnpj,
                'empresa': titulo.empresa,
                'score': score,
                'criterio': criterio,
                'diferenca_valor': diferenca
            })

        return candidatos

    def _buscar_por_cnpj_raiz(self, cnpj: str, valor: float, data_pagamento: Optional[date] = None) -> List[Dict]:
        """
        Busca títulos pela RAIZ do CNPJ (primeiros 8 dígitos).
        Usado para grupos empresariais onde a matriz paga por filiais.

        Exemplo:
        - Pagador: 05.017.780/0001-04 (matriz)
        - Título: 05.017.780/0023-01 (filial)
        - Raiz comum: 05017780
        """
        cnpj_limpo = self._normalizar_cnpj(cnpj)
        if len(cnpj_limpo) < 8:
            return []

        # Extrair raiz do CNPJ (primeiros 8 dígitos)
        raiz_cnpj = cnpj_limpo[:8]

        # Buscar títulos não pagos
        titulos = ContasAReceber.query.filter(
            ContasAReceber.parcela_paga == False,
            ContasAReceber.cnpj.isnot(None)
        ).all()

        candidatos = []

        for titulo in titulos:
            titulo_cnpj = self._normalizar_cnpj(titulo.cnpj)

            # Match exato já foi testado, pular
            if titulo_cnpj == cnpj_limpo:
                continue

            # Verificar se tem a mesma raiz
            if len(titulo_cnpj) >= 8 and titulo_cnpj[:8] == raiz_cnpj:
                # Ignorar títulos com vencimento 01/01/2000 (bug desconto duplicado)
                if titulo.vencimento == DATA_VENCIMENTO_IGNORAR:
                    continue

                # Ignorar NFs canceladas
                if titulo.nf_cancelada:
                    continue

                # Calcular score baseado no valor
                score, criterio, diferenca = self._calcular_score_valor_grupo(valor, titulo.valor_titulo or 0)

                # Aplicar desconto de vencimento
                desconto_venc, criterio_venc = self._calcular_desconto_vencimento(data_pagamento, titulo.vencimento)
                score = max(0, score - desconto_venc)
                if criterio_venc:
                    criterio = f'{criterio}+{criterio_venc}'

                candidatos.append({
                    'titulo_id': titulo.id,
                    'titulo_nf': titulo.titulo_nf,
                    'parcela': titulo.parcela,
                    'valor': titulo.valor_titulo,
                    'vencimento': titulo.vencimento.strftime('%d/%m/%Y') if titulo.vencimento else None,
                    'vencimento_date': titulo.vencimento,
                    'cliente': titulo.raz_social_red or titulo.raz_social,
                    'cnpj': titulo.cnpj,
                    'empresa': titulo.empresa,
                    'score': score,
                    'criterio': criterio,
                    'diferenca_valor': diferenca
                })

        return candidatos

    def _buscar_por_valor(self, valor: float, data_pagamento: Optional[date] = None) -> List[Dict]:
        """
        Busca títulos apenas pelo valor (quando CNPJ não disponível).
        Score mais baixo pois é menos confiável.
        """
        # Margem de busca: ±5%
        margem = valor * 0.05
        valor_min = valor - margem
        valor_max = valor + margem

        titulos = ContasAReceber.query.filter(
            ContasAReceber.parcela_paga == False,
            ContasAReceber.valor_titulo.between(valor_min, valor_max),
            ContasAReceber.vencimento != DATA_VENCIMENTO_IGNORAR
        ).limit(20).all()

        candidatos = []

        for titulo in titulos:
            # Ignorar NFs canceladas
            if titulo.nf_cancelada:
                continue

            diferenca = abs((titulo.valor_titulo or 0) - valor)
            # Score base 70, reduzido pela diferença de valor
            score = max(50, 70 - int(diferenca / valor * 100))
            criterio = 'VALOR_APROXIMADO_SEM_CNPJ'

            # Aplicar desconto de vencimento
            desconto_venc, criterio_venc = self._calcular_desconto_vencimento(data_pagamento, titulo.vencimento)
            score = max(0, score - desconto_venc)
            if criterio_venc:
                criterio = f'{criterio}+{criterio_venc}'

            candidatos.append({
                'titulo_id': titulo.id,
                'titulo_nf': titulo.titulo_nf,
                'parcela': titulo.parcela,
                'valor': titulo.valor_titulo,
                'vencimento': titulo.vencimento.strftime('%d/%m/%Y') if titulo.vencimento else None,
                'vencimento_date': titulo.vencimento,
                'cliente': titulo.raz_social_red or titulo.raz_social,
                'cnpj': titulo.cnpj,
                'empresa': titulo.empresa,
                'score': score,
                'criterio': criterio,
                'diferenca_valor': diferenca
            })

        return candidatos

    def _calcular_score_valor(self, valor_extrato: float, valor_titulo: float) -> Tuple[int, str, float]:
        """
        Calcula o score baseado na diferença de valores (CNPJ EXATO).

        Returns:
            Tuple (score, criterio, diferenca)
        """
        if valor_titulo == 0:
            return 0, 'TITULO_ZERADO', valor_extrato

        diferenca = abs(valor_extrato - valor_titulo)

        # Valor exato (com tolerância)
        if diferenca <= TOLERANCIA_VALOR:
            return 100, 'CNPJ_EXATO+VALOR_EXATO', diferenca

        # Valor muito próximo (até 1 real)
        if diferenca <= 1.0:
            return 95, 'CNPJ_EXATO+VALOR_PROXIMO', diferenca

        # Valor aproximado (até 5%)
        percentual = diferenca / valor_titulo * 100
        if percentual <= 5:
            return 90 - int(percentual), f'CNPJ_EXATO+VALOR_APROX_{percentual:.1f}%', diferenca

        # Valor diferente mas mesmo CNPJ
        if percentual <= 20:
            return 70, f'CNPJ_EXATO+VALOR_DIF_{percentual:.1f}%', diferenca

        # Diferença grande - possível pagamento parcial
        if valor_extrato < valor_titulo:
            return 60, 'CNPJ_EXATO+POSSIVEL_PARCIAL', diferenca

        # Valor do extrato maior que título
        return 50, 'CNPJ_EXATO+VALOR_MAIOR', diferenca

    def _calcular_score_valor_grupo(self, valor_extrato: float, valor_titulo: float) -> Tuple[int, str, float]:
        """
        Calcula o score para GRUPO EMPRESARIAL (mesmo CNPJ raiz, filial diferente).
        Scores um pouco menores que CNPJ exato.

        Returns:
            Tuple (score, criterio, diferenca)
        """
        if valor_titulo == 0:
            return 0, 'TITULO_ZERADO', valor_extrato

        diferenca = abs(valor_extrato - valor_titulo)

        # Valor exato (com tolerância) - grupo empresarial
        if diferenca <= TOLERANCIA_VALOR:
            return 90, 'GRUPO_CNPJ+VALOR_EXATO', diferenca

        # Valor muito próximo (até 1 real)
        if diferenca <= 1.0:
            return 88, 'GRUPO_CNPJ+VALOR_PROXIMO', diferenca

        # Valor aproximado (até 5%)
        percentual = diferenca / valor_titulo * 100
        if percentual <= 5:
            return 85 - int(percentual), f'GRUPO_CNPJ+VALOR_APROX_{percentual:.1f}%', diferenca

        # Valor diferente mas mesmo grupo
        if percentual <= 20:
            return 65, f'GRUPO_CNPJ+VALOR_DIF_{percentual:.1f}%', diferenca

        # Diferença grande - possível pagamento parcial
        if valor_extrato < valor_titulo:
            return 55, 'GRUPO_CNPJ+POSSIVEL_PARCIAL', diferenca

        # Valor do extrato maior que título
        return 45, 'GRUPO_CNPJ+VALOR_MAIOR', diferenca

    def _vincular_titulo(self, item: ExtratoItem, match: Dict) -> None:
        """
        Vincula um título ao item de extrato.
        """
        item.titulo_id = match['titulo_id']
        item.titulo_nf = match['titulo_nf']
        item.titulo_parcela = match['parcela']
        item.titulo_valor = match['valor']
        item.titulo_cliente = match['cliente']

        if match.get('vencimento'):
            try:
                item.titulo_vencimento = datetime.strptime(match['vencimento'], '%d/%m/%Y').date()
            except:
                pass

        item.match_score = match['score']
        item.match_criterio = match['criterio']

    def vincular_titulo_manual(self, item: ExtratoItem, titulo_id: int) -> None:
        """
        Vincula manualmente um título ao item de extrato.
        """
        titulo = ContasAReceber.query.get(titulo_id)
        if not titulo:
            raise ValueError(f"Título {titulo_id} não encontrado")

        item.titulo_id = titulo.id
        item.titulo_nf = titulo.titulo_nf
        item.titulo_parcela = titulo.parcela
        item.titulo_valor = titulo.valor_titulo
        item.titulo_cliente = titulo.raz_social_red or titulo.raz_social
        item.titulo_vencimento = titulo.vencimento

        # Calcular score
        score, criterio, _ = self._calcular_score_valor(item.valor, titulo.valor_titulo or 0)
        item.match_score = score
        item.match_criterio = f'MANUAL+{criterio}'

        item.status_match = 'MATCH_ENCONTRADO'
        item.mensagem = 'Título vinculado manualmente'

        db.session.commit()

    def _normalizar_cnpj(self, cnpj: str) -> str:
        """
        Normaliza CNPJ removendo caracteres especiais.
        """
        if not cnpj:
            return ''
        import re
        return re.sub(r'\D', '', cnpj)

    def _calcular_desconto_vencimento(
        self,
        data_pagamento: Optional[date],
        data_vencimento: Optional[date]
    ) -> Tuple[int, str]:
        """
        Calcula o desconto baseado na diferença entre data de pagamento e vencimento.

        REGRAS:
        - Cliente ATRASOU até 4 dias: 0% (normal, tolerância)
        - Cliente ATRASOU > 4 dias: -1% por dia adicional
        - Cliente ANTECIPOU até 3 dias: -2%
        - Cliente ANTECIPOU 4-7 dias: -4%
        - Cliente ANTECIPOU > 7 dias: -4% base + -1% por dia adicional

        Args:
            data_pagamento: Data do pagamento no extrato
            data_vencimento: Data de vencimento do título

        Returns:
            Tuple (desconto_percentual, criterio)
        """
        if not data_pagamento or not data_vencimento:
            return 0, ''

        # Diferença em dias (positivo = atrasou, negativo = antecipou)
        diff_dias = (data_pagamento - data_vencimento).days

        if diff_dias >= 0:
            # Cliente ATRASOU (pagamento após vencimento) - MAIS COMUM
            if diff_dias <= DIAS_ATRASO_TOLERANCIA:
                # Até 4 dias de atraso: sem desconto
                return 0, f'ATRASO_{diff_dias}D_OK'
            else:
                # Acima de 4 dias: -1% por dia adicional
                dias_excedentes = diff_dias - DIAS_ATRASO_TOLERANCIA
                desconto = dias_excedentes  # -1% por dia
                return desconto, f'ATRASO_{diff_dias}D'
        else:
            # Cliente ANTECIPOU (pagamento antes do vencimento) - RARO
            dias_antecipado = abs(diff_dias)

            if dias_antecipado <= DIAS_ANTECIPADO_LEVE:
                # Até 3 dias antecipado: -2%
                return 2, f'ANTECIPADO_{dias_antecipado}D'
            elif dias_antecipado <= DIAS_ANTECIPADO_MEDIO:
                # 4-7 dias antecipado: -4%
                return 4, f'ANTECIPADO_{dias_antecipado}D'
            else:
                # Mais de 7 dias antecipado: -4% base + -1% por dia adicional
                dias_excedentes = dias_antecipado - DIAS_ANTECIPADO_MEDIO
                desconto = 4 + dias_excedentes  # -4% + -1% por dia
                return desconto, f'ANTECIPADO_{dias_antecipado}D'


# =============================================================================
# TABELA DE SCORES DE MATCHING
# =============================================================================
#
# CNPJ EXATO:
#   100 - CNPJ_EXATO+VALOR_EXATO      (tolerância ±0.02)
#    95 - CNPJ_EXATO+VALOR_PROXIMO    (diferença até R$ 1)
#    90 - CNPJ_EXATO+VALOR_APROX_X%   (diferença até 5%)
#    70 - CNPJ_EXATO+VALOR_DIF_X%     (diferença até 20%)
#    60 - CNPJ_EXATO+POSSIVEL_PARCIAL (pagador pagou menos)
#    50 - CNPJ_EXATO+VALOR_MAIOR      (pagador pagou mais)
#
# GRUPO EMPRESARIAL (mesma raiz de CNPJ):
#    90 - GRUPO_CNPJ+VALOR_EXATO      (tolerância ±0.02)
#    88 - GRUPO_CNPJ+VALOR_PROXIMO    (diferença até R$ 1)
#    85 - GRUPO_CNPJ+VALOR_APROX_X%   (diferença até 5%)
#    65 - GRUPO_CNPJ+VALOR_DIF_X%     (diferença até 20%)
#    55 - GRUPO_CNPJ+POSSIVEL_PARCIAL (pagador pagou menos)
#    45 - GRUPO_CNPJ+VALOR_MAIOR      (pagador pagou mais)
#
# SEM CNPJ (apenas valor):
#    70 - VALOR_APROXIMADO_SEM_CNPJ   (busca genérica por valor)
#
# DESCONTOS DE VENCIMENTO (aplicados sobre o score base):
#   CLIENTE ATRASOU (mais comum):
#     0% - ATRASO_XD_OK              (até 4 dias de atraso - tolerância)
#    -1% por dia - ATRASO_XD         (acima de 4 dias)
#
#   CLIENTE ANTECIPOU (raro):
#    -2% - ANTECIPADO_XD             (até 3 dias antecipado)
#    -4% - ANTECIPADO_XD             (4 a 7 dias antecipado)
#    -4% base + -1% por dia adicional (acima de 7 dias)
#
# SCORE MÍNIMO PARA AUTO-MATCH: 95 (configurável via SCORE_MINIMO_AUTO)
