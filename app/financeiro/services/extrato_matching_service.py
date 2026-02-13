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
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from app import db
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAReceber, ContasAPagar, ExtratoItemTitulo
from app.financeiro.parcela_utils import parcela_to_int
from app.financeiro.services.extrato_service import CATEGORIAS_SEM_TITULO_ENTRADA

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
        lote = db.session.get(ExtratoLote,lote_id) if lote_id else None
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
        # Filtrar categorias financeiras de entrada (banco, FIDC, transferência)
        # Estas não têm título a receber correspondente
        if item.categoria_pagamento and item.categoria_pagamento in CATEGORIAS_SEM_TITULO_ENTRADA:
            item.status_match = 'SEM_MATCH'
            item.mensagem = f'Categoria {item.categoria_pagamento} — operação financeira sem título'
            self.estatisticas['sem_match'] += 1
            return

        logger.info(f"Processando item {item.id}: R$ {item.valor} - CNPJ: {item.cnpj_pagador}")

        # Buscar candidatos (passa nome_pagador para boost em PIX sem CNPJ)
        candidatos = self.buscar_titulos_candidatos(
            cnpj=item.cnpj_pagador,
            valor=item.valor,
            data_pagamento=item.data_transacao,
            nome_pagador=item.nome_pagador
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
            # Guardar score/criterio do melhor candidato (já ordenado DESC)
            melhor = candidatos[0]
            item.match_score = melhor['score']
            item.match_criterio = melhor.get('criterio', '') + f'+MULTIPLOS({len(matches_altos)})'
            item.mensagem = f'{len(matches_altos)} títulos encontrados com score >= {SCORE_MINIMO_AUTO}'
            self.estatisticas['multiplos'] += 1
            logger.info(f"  Múltiplos matches: {len(matches_altos)} candidatos (melhor score={melhor['score']})")

        elif candidatos:
            # Candidatos com score baixo - precisa revisão
            item.status_match = 'MULTIPLOS_MATCHES'
            item.set_matches_candidatos(candidatos)
            # Guardar score/criterio do melhor candidato (já ordenado DESC)
            melhor = candidatos[0]
            item.match_score = melhor['score']
            item.match_criterio = melhor.get('criterio', '') + f'+MULTIPLOS({len(candidatos)})'
            item.mensagem = f'{len(candidatos)} candidato(s) encontrado(s) com score < {SCORE_MINIMO_AUTO}'
            self.estatisticas['multiplos'] += 1
            logger.info(f"  Candidatos com score baixo: {len(candidatos)} (melhor score={melhor['score']})")

    def buscar_titulos_candidatos(
        self,
        cnpj: Optional[str],
        valor: float,
        data_pagamento: Optional[date] = None,
        incluir_agrupamentos: bool = True,
        nome_pagador: Optional[str] = None
    ) -> List[Dict]:
        """
        Busca títulos candidatos para um recebimento.

        Estratégia hierárquica:
        1. CNPJ exato - maior confiança
        2. CNPJ raiz (grupo empresarial) - quando matriz paga por filial
        3. Apenas valor - quando não tem CNPJ (com boost por nome se disponível)
        4. Agrupamentos - múltiplos títulos que somam o valor (se habilitado)

        Args:
            cnpj: CNPJ do pagador (pode ser None)
            valor: Valor do recebimento
            data_pagamento: Data do pagamento
            incluir_agrupamentos: Se True, busca combinações de múltiplos títulos
            nome_pagador: Nome do pagador para boost em busca por valor (PIX sem CNPJ)

        Returns:
            Lista de candidatos ordenada por score (desc)
            Se houver sugestão de agrupamento, inclui item especial com:
            - tipo: 'agrupamento'
            - titulos: lista de títulos sugeridos
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
            candidatos = self._buscar_por_valor(valor, data_pagamento, nome_pagador=nome_pagador)

        # 4. Verificar se há sugestão de agrupamento (múltiplos títulos)
        # Só sugere se não encontrou match único com score alto
        match_alto = any(c['score'] >= SCORE_MINIMO_AUTO for c in candidatos)

        if incluir_agrupamentos and cnpj and not match_alto:
            agrupamento = self.buscar_titulos_agrupados(cnpj, valor, data_pagamento)
            if agrupamento and agrupamento['qtd_titulos'] > 1:
                # Adicionar como candidato especial
                candidatos.append({
                    'tipo': 'agrupamento',
                    'titulo_id': None,  # Não é um título único
                    'titulo_nf': f"AGRUPADO ({agrupamento['qtd_titulos']} NFs)",
                    'parcela': None,
                    'valor': agrupamento['soma'],
                    'vencimento': None,
                    'vencimento_date': None,
                    'cliente': agrupamento['titulos'][0]['cliente'] if agrupamento['titulos'] else None,
                    'cnpj': cnpj,
                    'score': agrupamento['score'],
                    'criterio': agrupamento['criterio'],
                    'diferenca_valor': agrupamento['diferenca'],
                    # Dados específicos do agrupamento
                    'agrupamento': agrupamento
                })

        # Ordenar por score decrescente
        candidatos.sort(key=lambda x: x['score'], reverse=True)

        return candidatos[:LIMITE_CANDIDATOS]

    def _buscar_por_cnpj_exato(self, cnpj: str, valor: float, data_pagamento: Optional[date] = None) -> List[Dict]:
        """
        Busca títulos pelo CNPJ EXATO do cliente.
        Score mais alto pois é match perfeito de CNPJ.

        Bug ano 2000: Títulos com vencimento 01/01/2000 são phantom (gerados por
        desconto duplicado no Odoo). Em vez de ignorá-los, agrupa-os com seus
        títulos irmãos (mesma NF) e apresenta o valor somado como candidato único.
        """
        cnpj_limpo = self._normalizar_cnpj(cnpj)

        # Buscar títulos não pagos
        titulos = ContasAReceber.query.filter(
            ContasAReceber.parcela_paga == False,
            ContasAReceber.cnpj.isnot(None)
        ).all()

        # Separar títulos por NF para detectar phantom ano 2000
        titulos_por_nf: Dict[str, Dict] = {}  # nf -> {'reais': [], 'phantom_2000': []}
        titulos_sem_nf = []

        for titulo in titulos:
            titulo_cnpj = self._normalizar_cnpj(titulo.cnpj)
            if titulo_cnpj != cnpj_limpo:
                continue
            if titulo.nf_cancelada:
                continue

            nf = titulo.titulo_nf
            if not nf:
                if titulo.vencimento != DATA_VENCIMENTO_IGNORAR:
                    titulos_sem_nf.append(titulo)
                continue

            if nf not in titulos_por_nf:
                titulos_por_nf[nf] = {'reais': [], 'phantom_2000': []}

            if titulo.vencimento == DATA_VENCIMENTO_IGNORAR:
                titulos_por_nf[nf]['phantom_2000'].append(titulo)
            else:
                titulos_por_nf[nf]['reais'].append(titulo)

        candidatos = []

        for nf, grupo in titulos_por_nf.items():
            if grupo['phantom_2000'] and grupo['reais']:
                # NF com títulos phantom: agregar valor real + phantom
                valor_agregado = sum(
                    (t.valor_titulo or 0)
                    for t in grupo['reais'] + grupo['phantom_2000']
                )
                # Usar o primeiro título real como referência
                titulo_ref = grupo['reais'][0]
                titulos_ids = [t.id for t in grupo['reais'] + grupo['phantom_2000']]

                score, criterio, diferenca = self._calcular_score_valor(valor, valor_agregado)

                desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                    data_pagamento, titulo_ref.vencimento
                )
                score = max(0, score - desconto_venc)
                if criterio_venc:
                    criterio = f'{criterio}+{criterio_venc}'

                candidatos.append({
                    'titulo_id': titulo_ref.id,
                    'titulo_nf': nf,
                    'parcela': titulo_ref.parcela,
                    'valor': valor_agregado,
                    'vencimento': titulo_ref.vencimento.strftime('%d/%m/%Y') if titulo_ref.vencimento else None,
                    'vencimento_date': titulo_ref.vencimento,
                    'cliente': titulo_ref.raz_social_red or titulo_ref.raz_social,
                    'cnpj': titulo_ref.cnpj,
                    'empresa': titulo_ref.empresa,
                    'score': score,
                    'criterio': criterio,
                    'diferenca_valor': diferenca,
                    # Flag para conciliação saber que precisa corrigir ano 2000
                    'tem_desconto_2000': True,
                    'titulos_agregados': titulos_ids,
                })
            elif grupo['phantom_2000'] and not grupo['reais']:
                # Só phantom sem título real — ignorar (não deveria acontecer)
                continue
            else:
                # NF normal (sem phantom) — cada título é um candidato separado
                for titulo in grupo['reais']:
                    score, criterio, diferenca = self._calcular_score_valor(
                        valor, titulo.valor_titulo or 0
                    )

                    desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                        data_pagamento, titulo.vencimento
                    )
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

        # Títulos sem NF (caso raro)
        for titulo in titulos_sem_nf:
            score, criterio, diferenca = self._calcular_score_valor(valor, titulo.valor_titulo or 0)
            desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                data_pagamento, titulo.vencimento
            )
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

        Também agrega títulos phantom ano 2000 (mesma lógica de _buscar_por_cnpj_exato).
        """
        cnpj_limpo = self._normalizar_cnpj(cnpj)
        if len(cnpj_limpo) < 8:
            return []

        raiz_cnpj = cnpj_limpo[:8]

        # Buscar títulos não pagos
        titulos = ContasAReceber.query.filter(
            ContasAReceber.parcela_paga == False,
            ContasAReceber.cnpj.isnot(None)
        ).all()

        # Separar por NF para agregar phantom ano 2000
        titulos_por_nf: Dict[str, Dict] = {}
        titulos_sem_nf = []

        for titulo in titulos:
            titulo_cnpj = self._normalizar_cnpj(titulo.cnpj)

            # Match exato já foi testado, pular
            if titulo_cnpj == cnpj_limpo:
                continue

            # Verificar se tem a mesma raiz
            if not (len(titulo_cnpj) >= 8 and titulo_cnpj[:8] == raiz_cnpj):
                continue

            if titulo.nf_cancelada:
                continue

            nf = titulo.titulo_nf
            if not nf:
                if titulo.vencimento != DATA_VENCIMENTO_IGNORAR:
                    titulos_sem_nf.append(titulo)
                continue

            if nf not in titulos_por_nf:
                titulos_por_nf[nf] = {'reais': [], 'phantom_2000': []}

            if titulo.vencimento == DATA_VENCIMENTO_IGNORAR:
                titulos_por_nf[nf]['phantom_2000'].append(titulo)
            else:
                titulos_por_nf[nf]['reais'].append(titulo)

        candidatos = []

        for nf, grupo in titulos_por_nf.items():
            if grupo['phantom_2000'] and grupo['reais']:
                # Agregar valor real + phantom
                valor_agregado = sum(
                    (t.valor_titulo or 0)
                    for t in grupo['reais'] + grupo['phantom_2000']
                )
                titulo_ref = grupo['reais'][0]
                titulos_ids = [t.id for t in grupo['reais'] + grupo['phantom_2000']]

                score, criterio, diferenca = self._calcular_score_valor_grupo(valor, valor_agregado)
                desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                    data_pagamento, titulo_ref.vencimento
                )
                score = max(0, score - desconto_venc)
                if criterio_venc:
                    criterio = f'{criterio}+{criterio_venc}'

                candidatos.append({
                    'titulo_id': titulo_ref.id,
                    'titulo_nf': nf,
                    'parcela': titulo_ref.parcela,
                    'valor': valor_agregado,
                    'vencimento': titulo_ref.vencimento.strftime('%d/%m/%Y') if titulo_ref.vencimento else None,
                    'vencimento_date': titulo_ref.vencimento,
                    'cliente': titulo_ref.raz_social_red or titulo_ref.raz_social,
                    'cnpj': titulo_ref.cnpj,
                    'empresa': titulo_ref.empresa,
                    'score': score,
                    'criterio': criterio,
                    'diferenca_valor': diferenca,
                    'tem_desconto_2000': True,
                    'titulos_agregados': titulos_ids,
                })
            elif grupo['phantom_2000'] and not grupo['reais']:
                continue
            else:
                for titulo in grupo['reais']:
                    score, criterio, diferenca = self._calcular_score_valor_grupo(
                        valor, titulo.valor_titulo or 0
                    )
                    desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                        data_pagamento, titulo.vencimento
                    )
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

        # Títulos sem NF
        for titulo in titulos_sem_nf:
            score, criterio, diferenca = self._calcular_score_valor_grupo(
                valor, titulo.valor_titulo or 0
            )
            desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                data_pagamento, titulo.vencimento
            )
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

    def _buscar_por_valor(
        self,
        valor: float,
        data_pagamento: Optional[date] = None,
        nome_pagador: Optional[str] = None
    ) -> List[Dict]:
        """
        Busca títulos apenas pelo valor (quando CNPJ não disponível).
        Score mais baixo pois é menos confiável.

        Se nome_pagador fornecido (ex: PIX pessoa física), faz boost de score
        quando tokens do nome aparecem no raz_social_red do título.
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

        # Preparar tokens do nome do pagador para boost
        tokens_pagador = []
        if nome_pagador:
            from app.financeiro.services._resolver_utils import tokenizar_nome
            tokens_pagador = tokenizar_nome(nome_pagador)

        candidatos = []

        for titulo in titulos:
            # Ignorar NFs canceladas
            if titulo.nf_cancelada:
                continue

            diferenca = abs((titulo.valor_titulo or 0) - valor)
            # Score base 70, reduzido pela diferença de valor
            score = max(50, 70 - int(diferenca / valor * 100))
            criterio = 'VALOR_APROXIMADO_SEM_CNPJ'

            # Boost para PIX com nome: se tokens do nome_pagador aparecem no título
            if tokens_pagador and titulo.raz_social_red:
                raz_upper = (titulo.raz_social_red or '').upper()
                tokens_match = sum(1 for t in tokens_pagador if t in raz_upper)
                if tokens_match > 0 and tokens_match >= len(tokens_pagador) * 0.5:
                    # Mais de 50% dos tokens batem — boost +10
                    score = min(score + 10, 80)
                    criterio = f'VALOR_SEM_CNPJ+NOME_PARCIAL({tokens_match}/{len(tokens_pagador)})'

            # Boost para data exata de vencimento
            if data_pagamento and titulo.vencimento and data_pagamento == titulo.vencimento:
                score = min(score + 5, 85)
                criterio = f'{criterio}+VENC_EXATO'

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
        Vincula um título A RECEBER ao item de extrato.
        Usa titulo_receber_id para manter integridade referencial correta.
        """
        item.titulo_receber_id = match['titulo_id']  # FK correta para ContasAReceber
        item.titulo_nf = match['titulo_nf']
        item.titulo_parcela = parcela_to_int(match['parcela'])
        item.titulo_valor = match['valor']
        item.titulo_cliente = match['cliente']
        item.titulo_cnpj = match.get('cnpj')

        if match.get('vencimento_date'):
            item.titulo_vencimento = match['vencimento_date']
        elif match.get('vencimento'):
            try:
                item.titulo_vencimento = datetime.strptime(match['vencimento'], '%d/%m/%Y').date()
            except Exception as e:
                logger.error(f"Erro ao converter vencimento: {e}")
                pass

        item.match_score = match['score']
        item.match_criterio = match['criterio']

    def vincular_titulo_manual(self, item: ExtratoItem, titulo_id: int) -> None:
        """
        Vincula manualmente um título A RECEBER ao item de extrato.
        """
        titulo = db.session.get(ContasAReceber,titulo_id) if titulo_id else None
        if not titulo:
            raise ValueError(f"Título {titulo_id} não encontrado")

        item.titulo_receber_id = titulo.id  # FK correta para ContasAReceber
        item.titulo_nf = titulo.titulo_nf
        item.titulo_parcela = titulo.parcela_int
        item.titulo_valor = titulo.valor_titulo
        item.titulo_cliente = titulo.raz_social_red or titulo.raz_social
        item.titulo_cnpj = titulo.cnpj
        item.titulo_vencimento = titulo.vencimento

        # Calcular score base pelo valor
        score, criterio, _ = self._calcular_score_valor(item.valor, titulo.valor_titulo or 0)

        # Aplicar desconto de vencimento (igual à busca de candidatos)
        desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
            item.data_transacao, titulo.vencimento
        )
        score = max(0, score - desconto_venc)
        if criterio_venc:
            criterio = f'{criterio}+{criterio_venc}'

        item.match_score = score
        item.match_criterio = f'MANUAL+{criterio}'

        item.status_match = 'MATCH_ENCONTRADO'
        item.mensagem = 'Título vinculado manualmente'

        db.session.commit()

    # =========================================================================
    # MÉTODOS PARA MÚLTIPLOS TÍTULOS (M:N)
    # =========================================================================

    def vincular_multiplos_titulos(
        self,
        item: ExtratoItem,
        titulos: List[Dict],
        tipo: str = 'receber',
        usuario: str = None
    ) -> List[ExtratoItemTitulo]:
        """
        Vincula múltiplos títulos a um item de extrato.

        Usa a tabela de associação ExtratoItemTitulo para relacionamento M:N.

        Args:
            item: ExtratoItem a vincular
            titulos: Lista de dicts com:
                - titulo_id: ID do título (ContasAReceber ou ContasAPagar)
                - valor_alocado: Valor a alocar deste título
            tipo: 'receber' ou 'pagar' (default: 'receber')
            usuario: Nome do usuário que está vinculando (opcional)

        Returns:
            Lista de ExtratoItemTitulo criados

        Raises:
            ValueError: Se soma dos valores > valor do extrato
        """
        # Validar soma dos valores
        valor_extrato = abs(item.valor) if item.valor else 0
        soma_alocada = sum(t.get('valor_alocado', 0) for t in titulos)
        if soma_alocada > valor_extrato * 1.01:  # 1% tolerância
            raise ValueError(
                f"Soma dos valores alocados (R$ {soma_alocada:.2f}) "
                f"excede o valor do extrato (R$ {valor_extrato:.2f})"
            )

        # Remover vinculações anteriores (se houver)
        self.desvincular_titulos(item)

        vinculos_criados = []

        # Selecionar modelo baseado no tipo
        if tipo == 'pagar':
            TituloModel = ContasAPagar
        else:
            TituloModel = ContasAReceber

        for t in titulos:
            titulo = db.session.get(TituloModel,t['titulo_id']) if t['titulo_id'] else None
            if not titulo:
                raise ValueError(f"Título {t['titulo_id']} não encontrado")

            # Obter valor do título (ContasAReceber usa valor_titulo, ContasAPagar usa valor_original)
            valor_titulo = getattr(titulo, 'valor_titulo', None) or getattr(titulo, 'valor_original', None) or 0
            valor_alocado = t.get('valor_alocado', valor_titulo)

            # Criar vinculação M:N (com FK correta baseada no tipo)
            vinculo = ExtratoItemTitulo(
                extrato_item_id=item.id,
                valor_alocado=valor_alocado
            )

            # Definir FK correta baseada no tipo
            if tipo == 'pagar':
                vinculo.titulo_pagar_id = titulo.id
            else:
                vinculo.titulo_receber_id = titulo.id

            # Preencher cache (passa título diretamente pois relação ainda não foi carregada)
            vinculo.preencher_cache(titulo)

            # Calcular score
            score, criterio, _ = self._calcular_score_valor(
                valor_alocado, valor_titulo
            )

            # Aplicar desconto de vencimento
            desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                item.data_transacao, titulo.vencimento
            )
            score = max(0, score - desconto_venc)
            if criterio_venc:
                criterio = f'{criterio}+{criterio_venc}'

            vinculo.match_score = score
            vinculo.match_criterio = f'MULTIPLO+{criterio}'
            vinculo.status = 'PENDENTE'

            db.session.add(vinculo)
            vinculos_criados.append(vinculo)

        # Limpar FK legacy (usar apenas M:N)
        item.titulo_receber_id = None
        item.titulo_pagar_id = None
        item.titulo_id = None

        # Atualizar status do item
        item.status_match = 'MULTIPLOS_VINCULADOS'
        item.mensagem = f'{len(titulos)} títulos vinculados (total: R$ {soma_alocada:.2f})'

        # Cache do primeiro título para exibição rápida
        if vinculos_criados:
            primeiro = vinculos_criados[0]
            item.titulo_nf = primeiro.titulo_nf
            item.titulo_parcela = primeiro.titulo_parcela
            item.titulo_valor = float(soma_alocada)
            item.titulo_cliente = primeiro.titulo_cliente
            item.titulo_cnpj = primeiro.titulo_cnpj
            item.match_score = min(v.match_score for v in vinculos_criados)
            item.match_criterio = f'AGRUPADO_{len(titulos)}_TITULOS'

        db.session.commit()

        logger.info(
            f"Vinculados {len(vinculos_criados)} títulos ao item {item.id} "
            f"(total: R$ {soma_alocada:.2f})"
        )

        return vinculos_criados

    def desvincular_titulos(self, item: ExtratoItem) -> int:
        """
        Remove todas as vinculações de títulos de um item.

        Remove tanto o FK legacy quanto os registros M:N.

        Args:
            item: ExtratoItem a desvincular

        Returns:
            Número de vinculações removidas
        """
        # Remover FK legacy
        item.titulo_receber_id = None
        item.titulo_pagar_id = None
        item.titulo_id = None
        item.titulo_nf = None
        item.titulo_parcela = None
        item.titulo_valor = None
        item.titulo_cliente = None
        item.titulo_cnpj = None
        item.titulo_vencimento = None
        item.match_score = None
        item.match_criterio = None

        # Remover vinculações M:N
        count = ExtratoItemTitulo.query.filter_by(
            extrato_item_id=item.id
        ).delete()

        item.status_match = 'PENDENTE'
        item.mensagem = None

        logger.info(f"Desvinculados {count} títulos do item {item.id}")

        return count

    def buscar_titulos_agrupados(
        self,
        cnpj: Optional[str],
        valor: float,
        data_pagamento: Optional[date] = None,
        tolerancia_percentual: float = 0.02
    ) -> Optional[Dict]:
        """
        Busca combinações de títulos do mesmo CNPJ cuja soma aproxima do valor.

        Estratégia: Busca gulosa (greedy) - ordena por valor decrescente e
        vai adicionando títulos até atingir o valor ou ultrapassar.

        Args:
            cnpj: CNPJ do pagador
            valor: Valor do extrato
            data_pagamento: Data do pagamento
            tolerancia_percentual: Tolerância para considerar "exato" (default 2%)

        Returns:
            Dict com:
                - titulos: Lista de títulos sugeridos
                - soma: Soma dos valores
                - diferenca: Diferença para o valor do extrato
                - score: Score do agrupamento
                - criterio: Descrição do critério
            Ou None se não encontrar combinação válida
        """
        if not cnpj or valor <= 0:
            return None

        cnpj_limpo = self._normalizar_cnpj(cnpj)
        raiz_cnpj = cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else cnpj_limpo

        # Buscar títulos não pagos do mesmo CNPJ ou grupo
        titulos = ContasAReceber.query.filter(
            ContasAReceber.parcela_paga == False,
            ContasAReceber.cnpj.isnot(None)
        ).all()

        # Filtrar por CNPJ exato ou raiz
        titulos_cnpj = []
        for titulo in titulos:
            titulo_cnpj = self._normalizar_cnpj(titulo.cnpj)

            # Ignorar vencimento 01/01/2000 e NFs canceladas
            if titulo.vencimento == DATA_VENCIMENTO_IGNORAR:
                continue
            if titulo.nf_cancelada:
                continue

            # Match exato ou por raiz
            if titulo_cnpj == cnpj_limpo or (
                len(titulo_cnpj) >= 8 and titulo_cnpj[:8] == raiz_cnpj
            ):
                titulos_cnpj.append(titulo)

        if not titulos_cnpj:
            return None

        # Se só tem 1 título, não é agrupamento
        if len(titulos_cnpj) == 1:
            return None

        # Ordenar por valor decrescente (greedy)
        titulos_cnpj.sort(key=lambda t: t.valor_titulo or 0, reverse=True)

        # Tentar encontrar combinação que fecha o valor
        melhor_combinacao = self._encontrar_combinacao_valores(
            titulos_cnpj, valor, tolerancia_percentual
        )

        if not melhor_combinacao:
            return None

        titulos_selecionados, soma = melhor_combinacao
        diferenca = abs(soma - valor)
        diferenca_pct = (diferenca / valor * 100) if valor > 0 else 0

        # Calcular score baseado na diferença
        if diferenca_pct <= tolerancia_percentual * 100:
            score = 92
            criterio = 'AGRUPADO+VALOR_EXATO'
        elif diferenca_pct <= 1:
            score = 88
            criterio = f'AGRUPADO+VALOR_APROX_{diferenca_pct:.1f}%'
        elif diferenca_pct <= 5:
            score = 82
            criterio = f'AGRUPADO+VALOR_DIF_{diferenca_pct:.1f}%'
        else:
            score = 70
            criterio = f'AGRUPADO+VALOR_DIF_{diferenca_pct:.1f}%'

        # Preparar resultado
        titulos_result = []
        for titulo in titulos_selecionados:
            # Calcular desconto de vencimento individual
            desconto_venc, criterio_venc = self._calcular_desconto_vencimento(
                data_pagamento, titulo.vencimento
            )

            titulos_result.append({
                'titulo_id': titulo.id,
                'titulo_nf': titulo.titulo_nf,
                'parcela': titulo.parcela,
                'valor': titulo.valor_titulo,
                'valor_alocado': titulo.valor_titulo,  # Inicialmente aloca 100%
                'vencimento': titulo.vencimento.strftime('%d/%m/%Y') if titulo.vencimento else None,
                'vencimento_date': titulo.vencimento,
                'cliente': titulo.raz_social_red or titulo.raz_social,
                'cnpj': titulo.cnpj,
                'desconto_vencimento': desconto_venc,
                'criterio_vencimento': criterio_venc
            })

        return {
            'titulos': titulos_result,
            'soma': soma,
            'diferenca': diferenca,
            'diferenca_pct': diferenca_pct,
            'score': score,
            'criterio': criterio,
            'qtd_titulos': len(titulos_result)
        }

    def _encontrar_combinacao_valores(
        self,
        titulos: List[ContasAReceber],
        valor_alvo: float,
        tolerancia: float = 0.02
    ) -> Optional[Tuple[List[ContasAReceber], float]]:
        """
        Encontra combinação de títulos que soma próximo ao valor alvo.

        Usa algoritmo subset sum simplificado (greedy + backtracking limitado).

        Args:
            titulos: Lista de títulos candidatos (já filtrados por CNPJ)
            valor_alvo: Valor a atingir
            tolerancia: Tolerância percentual

        Returns:
            Tuple (lista de títulos, soma) ou None
        """
        # Limite para considerar "exato"
        limite_inferior = valor_alvo * (1 - tolerancia)
        limite_superior = valor_alvo * (1 + tolerancia)

        # Tentar combinações com subset sum simplificado
        # Começamos com greedy e refinamos se necessário

        # 1. Greedy: adicionar títulos até atingir ou ultrapassar
        selecionados = []
        soma = 0

        for titulo in titulos:
            valor_titulo = titulo.valor_titulo or 0
            if soma + valor_titulo <= limite_superior:
                selecionados.append(titulo)
                soma += valor_titulo

                # Se chegou no range, retorna
                if limite_inferior <= soma <= limite_superior:
                    return (selecionados, soma)

        # Se greedy encontrou algo próximo, retorna
        if selecionados and limite_inferior <= soma <= limite_superior:
            return (selecionados, soma)

        # 2. Se greedy falhou mas está próximo (< 20% diferença), retorna mesmo assim
        if selecionados and soma >= valor_alvo * 0.8 and soma <= valor_alvo * 1.2:
            return (selecionados, soma)

        # 3. Tentar subset sum com backtracking limitado (até 10 títulos)
        if len(titulos) <= 10:
            melhor = self._subset_sum_limitado(titulos, valor_alvo, tolerancia)
            if melhor:
                return melhor

        # Não encontrou combinação válida
        return None

    def _subset_sum_limitado(
        self,
        titulos: List[ContasAReceber],
        valor_alvo: float,
        tolerancia: float
    ) -> Optional[Tuple[List[ContasAReceber], float]]:
        """
        Subset sum com backtracking limitado.
        Tenta todas as combinações de até N títulos.
        """
        from itertools import combinations

        limite_inferior = valor_alvo * (1 - tolerancia)
        limite_superior = valor_alvo * (1 + tolerancia)

        melhor_diff = float('inf')
        melhor_combo = None

        # Tentar combinações de 2 a min(len, 5) títulos
        for r in range(2, min(len(titulos) + 1, 6)):
            for combo in combinations(titulos, r):
                soma = sum(t.valor_titulo or 0 for t in combo)

                # Match exato
                if limite_inferior <= soma <= limite_superior:
                    return (list(combo), soma)

                # Guardar melhor aproximação
                diff = abs(soma - valor_alvo)
                if diff < melhor_diff and soma <= valor_alvo * 1.2:
                    melhor_diff = diff
                    melhor_combo = (list(combo), soma)

        # Retorna melhor aproximação se diferença < 10%
        if melhor_combo and melhor_diff / valor_alvo <= 0.1:
            return melhor_combo

        return None

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
