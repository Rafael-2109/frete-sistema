# -*- coding: utf-8 -*-
"""
Serviço de Matching - Extrato vs Contas a Pagar
================================================

Encontra títulos candidatos para conciliação com linhas de extrato de pagamentos.

REGRAS DE MATCHING (score base 100%, descontos acumulativos):

=== COM CNPJ NO EXTRATO (TED/PIX) ===
| Critério                                | Desconto |
|-----------------------------------------|----------|
| Match PERFEITO (CNPJ + Valor + Venc)    |    0%    |
| Match RAIZ CNPJ (8 dig) + Valor + Venc  |   -2%    |
| CNPJ diferente                          |  -15%    |
| Vencimento ANTERIOR ao pagamento        |   -5%    |
| Vencimento POSTERIOR ao pagamento       |  -10%    |

=== TOLERÂNCIA DE VALOR ===
| Diferença     | Desconto |
|---------------|----------|
| até R$ 0,01   |    0%    |
| até R$ 0,10   |   -3%    |
| até R$ 0,30   |   -6%    |
| até R$ 0,50   |  -10%    |
| acima disso   |  -25%    |

=== SEM CNPJ NO EXTRATO (Boletos) ===
| Critério                                    | Desconto |
|---------------------------------------------|----------|
| Único título candidato (Valor + Venc)       |   -5%    |
| Único fornecedor candidato (N títulos)      |   -7%    |
| Fornecedor "sobrou" (outros já vinculados)  |   -3%    |

Autor: Sistema de Fretes
Data: 2025-12-13
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Set

from app import db
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAPagar
from app.financeiro.parcela_utils import parcela_to_int

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÕES DE MATCHING (ajustáveis)
# =============================================================================

# Score mínimo para considerar match automático
SCORE_MINIMO_AUTO = 90

# Limite de candidatos para retornar
LIMITE_CANDIDATOS = 50


class PagamentoMatchingService:
    """
    Serviço para encontrar títulos de contas a pagar candidatos para conciliação.
    """

    def __init__(self):
        self.estatisticas = {
            'processados': 0,
            'com_match': 0,
            'multiplos': 0,
            'sem_match': 0
        }
        # Cache de CNPJs já vinculados no lote atual (para regra 3)
        self._cnpjs_vinculados: Set[str] = set()

    def executar_matching_lote(self, lote_id: int) -> Dict:
        """
        Executa o matching para todos os itens pendentes de um lote de pagamentos.

        Args:
            lote_id: ID do lote

        Returns:
            Dict com estatísticas do matching
        """
        lote = db.session.get(ExtratoLote,lote_id) if lote_id else None
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado")

        if lote.tipo_transacao != 'saida':
            raise ValueError(f"Lote {lote_id} não é de pagamentos (tipo={lote.tipo_transacao})")

        logger.info(f"=" * 60)
        logger.info(f"EXECUTANDO MATCHING PAGAMENTOS - Lote {lote_id}")
        logger.info(f"=" * 60)

        # Pré-sync: sincronizar comprovantes LANCADOS antes de processar matching
        self._pre_sync_comprovantes(lote_id)

        # Limpar cache de CNPJs vinculados
        self._cnpjs_vinculados.clear()

        # Carregar CNPJs já vinculados em outros itens do lote
        itens_vinculados = ExtratoItem.query.filter(
            ExtratoItem.lote_id == lote_id,
            ExtratoItem.titulo_id.isnot(None)
        ).all()
        for item in itens_vinculados:
            if item.cnpj_pagador:
                self._cnpjs_vinculados.add(self._normalizar_cnpj(item.cnpj_pagador))

        # Buscar itens pendentes
        itens = ExtratoItem.query.filter_by(
            lote_id=lote_id,
            status_match='PENDENTE'
        ).all()

        logger.info(f"Itens a processar: {len(itens)}")
        logger.info(f"CNPJs já vinculados: {len(self._cnpjs_vinculados)}")

        # Primeira passada: processar itens COM CNPJ (TED/PIX/Favorecido resolvido)
        itens_com_cnpj = [i for i in itens if (i.favorecido_cnpj or i.cnpj_pagador)]
        itens_sem_cnpj = [i for i in itens if not (i.favorecido_cnpj or i.cnpj_pagador)]

        logger.info(f"  - Com CNPJ (TED/PIX/Favorecido): {len(itens_com_cnpj)}")
        logger.info(f"  - Sem CNPJ (Boleto): {len(itens_sem_cnpj)}")

        # Processar itens com CNPJ primeiro (maior confiança)
        for item in itens_com_cnpj:
            try:
                self._processar_item_matching(item)
                self.estatisticas['processados'] += 1

                # Adicionar CNPJ ao cache de vinculados
                cnpj_eff = item.favorecido_cnpj or item.cnpj_pagador
                if item.titulo_pagar_id and cnpj_eff:
                    self._cnpjs_vinculados.add(self._normalizar_cnpj(cnpj_eff))

            except Exception as e:
                logger.error(f"Erro no item {item.id}: {e}")
                item.status_match = 'ERRO'
                item.mensagem = str(e)

            db.session.commit()

        # Processar itens sem CNPJ (boletos) - após vincular os com CNPJ
        for item in itens_sem_cnpj:
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
        # Pular categorias sem fornecedor (IMPOSTO, TARIFA, JUROS, IOF, FOLHA)
        from app.financeiro.services.extrato_service import CATEGORIAS_SEM_FORNECEDOR
        if item.categoria_pagamento and item.categoria_pagamento in CATEGORIAS_SEM_FORNECEDOR:
            item.status_match = 'SEM_MATCH'
            item.mensagem = f'Categoria {item.categoria_pagamento} — sem fornecedor (resolução automática)'
            self.estatisticas['sem_match'] += 1
            return

        # Valor do pagamento é negativo no extrato, precisamos do valor absoluto
        valor = abs(item.valor) if item.valor else 0

        # Usar favorecido_cnpj como CNPJ primário (fallback para cnpj_pagador)
        cnpj = item.favorecido_cnpj or item.cnpj_pagador

        logger.info(f"Processando item {item.id}: R$ {valor} - CNPJ: {cnpj} - Data: {item.data_transacao}")

        # Buscar candidatos
        candidatos = self.buscar_titulos_candidatos(
            cnpj=cnpj,
            valor=valor,
            data_pagamento=item.data_transacao
        )

        if not candidatos:
            item.status_match = 'SEM_MATCH'
            item.mensagem = 'Nenhum título encontrado para CNPJ/valor/vencimento informados'
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
        Busca títulos de contas a pagar candidatos para um pagamento.

        Args:
            cnpj: CNPJ do fornecedor (pode ser None para boletos)
            valor: Valor do pagamento (absoluto)
            data_pagamento: Data do pagamento no extrato

        Returns:
            Lista de candidatos ordenada por score (desc)
        """
        candidatos = []

        if cnpj:
            # Com CNPJ: buscar por CNPJ exato ou raiz
            candidatos = self._buscar_com_cnpj(cnpj, valor, data_pagamento)
        else:
            # Sem CNPJ (boleto): buscar por valor + vencimento
            candidatos = self._buscar_sem_cnpj(valor, data_pagamento)

        # Ordenar por score decrescente
        candidatos.sort(key=lambda x: x['score'], reverse=True)

        return candidatos[:LIMITE_CANDIDATOS]

    def _buscar_com_cnpj(
        self,
        cnpj: str,
        valor: float,
        data_pagamento: Optional[date]
    ) -> List[Dict]:
        """
        Busca títulos quando o CNPJ está disponível (TED/PIX).
        """
        cnpj_limpo = self._normalizar_cnpj(cnpj)
        raiz_cnpj = cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else ''

        # Buscar títulos não pagos com valor próximo
        margem = valor * 0.10  # 10% de margem para busca inicial
        valor_min = valor - max(margem, 1.0)
        valor_max = valor + max(margem, 1.0)

        titulos = ContasAPagar.query.filter(
            ContasAPagar.parcela_paga == False,
            ContasAPagar.valor_residual.between(valor_min, valor_max)
        ).all()

        candidatos = []

        for titulo in titulos:
            titulo_cnpj = self._normalizar_cnpj(titulo.cnpj) if titulo.cnpj else ''
            titulo_raiz = titulo_cnpj[:8] if len(titulo_cnpj) >= 8 else ''

            # Calcular score
            score = 100  # Score base
            criterios = []

            # === REGRA DE CNPJ ===
            if titulo_cnpj == cnpj_limpo:
                # Regra 4: CNPJ exato = 0%
                criterios.append('CNPJ_EXATO')
            elif raiz_cnpj and titulo_raiz == raiz_cnpj:
                # Regra 5: CNPJ raiz = -2%
                score -= 2
                criterios.append('CNPJ_RAIZ')
            else:
                # Regra 6: CNPJ diferente = -15%
                score -= 15
                criterios.append('CNPJ_DIFERENTE')

            # === REGRA DE VALOR ===
            desconto_valor, criterio_valor = self._calcular_desconto_valor(valor, titulo.valor_residual or 0)
            score -= desconto_valor
            criterios.append(criterio_valor)

            # === REGRA DE VENCIMENTO ===
            if data_pagamento and titulo.vencimento:
                if titulo.vencimento < data_pagamento:
                    # Regra 7: Vencimento anterior = -5%
                    score -= 5
                    criterios.append('VENC_ANTERIOR')
                elif titulo.vencimento > data_pagamento:
                    # Regra 8: Vencimento posterior = -10%
                    score -= 10
                    criterios.append('VENC_POSTERIOR')
                else:
                    criterios.append('VENC_EXATO')

            # Score mínimo
            score = max(0, score)

            candidatos.append({
                'titulo_id': titulo.id,
                'titulo_nf': titulo.titulo_nf,
                'parcela': titulo.parcela,
                'valor': titulo.valor_residual,
                'valor_original': titulo.valor_original,
                'vencimento': titulo.vencimento.strftime('%d/%m/%Y') if titulo.vencimento else None,
                'vencimento_date': titulo.vencimento,
                'fornecedor': titulo.raz_social_red or titulo.raz_social,
                'cnpj': titulo.cnpj,
                'empresa': titulo.empresa,
                'score': score,
                'criterio': '+'.join(criterios),
                'diferenca_valor': abs((titulo.valor_residual or 0) - valor)
            })

        return candidatos

    def _buscar_sem_cnpj(
        self,
        valor: float,
        data_pagamento: Optional[date]
    ) -> List[Dict]:
        """
        Busca títulos quando o CNPJ NÃO está disponível (boletos).

        Regras especiais:
        - Regra 1: Único título candidato = -5%
        - Regra 2: Único fornecedor = -7%
        - Regra 3: Fornecedor "sobrou" = -3% adicional
        """
        if not data_pagamento:
            return []

        # Buscar títulos com valor próximo e vencimento próximo à data do pagamento
        margem_valor = max(valor * 0.05, 0.50)  # 5% ou R$ 0,50
        valor_min = valor - margem_valor
        valor_max = valor + margem_valor

        # Vencimento: até 5 dias antes ou depois
        from datetime import timedelta
        venc_min = data_pagamento - timedelta(days=5)
        venc_max = data_pagamento + timedelta(days=5)

        titulos = ContasAPagar.query.filter(
            ContasAPagar.parcela_paga == False,
            ContasAPagar.valor_residual.between(valor_min, valor_max),
            ContasAPagar.vencimento.between(venc_min, venc_max)
        ).all()

        if not titulos:
            return []

        # Agrupar por fornecedor (CNPJ)
        fornecedores: Dict[str, List] = {}
        for titulo in titulos:
            cnpj = self._normalizar_cnpj(titulo.cnpj) if titulo.cnpj else 'SEM_CNPJ'
            if cnpj not in fornecedores:
                fornecedores[cnpj] = []
            fornecedores[cnpj].append(titulo)

        # Identificar fornecedores que "sobraram" (não têm outros títulos vinculados)
        fornecedores_disponiveis = {
            cnpj: titulos
            for cnpj, titulos in fornecedores.items()
            if cnpj not in self._cnpjs_vinculados
        }

        candidatos = []

        for titulo in titulos:
            cnpj = self._normalizar_cnpj(titulo.cnpj) if titulo.cnpj else 'SEM_CNPJ'

            # Calcular score base
            score = 100
            criterios = []

            # === REGRA DE VALOR ===
            desconto_valor, criterio_valor = self._calcular_desconto_valor(valor, titulo.valor_residual or 0)
            score -= desconto_valor
            criterios.append(criterio_valor)

            # === REGRA DE VENCIMENTO ===
            if titulo.vencimento:
                if titulo.vencimento < data_pagamento:
                    score -= 5
                    criterios.append('VENC_ANTERIOR')
                elif titulo.vencimento > data_pagamento:
                    score -= 10
                    criterios.append('VENC_POSTERIOR')
                else:
                    criterios.append('VENC_EXATO')

            # === REGRAS ESPECIAIS SEM CNPJ ===

            # Quantos títulos candidatos no total?
            total_titulos = len(titulos)
            # Quantos fornecedores diferentes?
            total_fornecedores = len(fornecedores)
            # Este fornecedor tem títulos vinculados?
            fornecedor_ja_vinculado = cnpj in self._cnpjs_vinculados

            if total_titulos == 1:
                # Regra 1: Único título candidato = -5%
                score -= 5
                criterios.append('UNICO_TITULO')
            elif total_fornecedores == 1:
                # Regra 2: Único fornecedor = -7%
                score -= 7
                criterios.append('UNICO_FORNECEDOR')
            elif not fornecedor_ja_vinculado and len(fornecedores_disponiveis) == 1:
                # Regra 3: Este fornecedor "sobrou" = -3% adicional
                score -= 3
                criterios.append('FORNECEDOR_SOBROU')
                # Ainda aplica regra 1 ou 2 se aplicável
                if len(fornecedores[cnpj]) == 1:
                    score -= 5
                    criterios.append('UNICO_TITULO')
                else:
                    score -= 7
                    criterios.append('UNICO_FORNECEDOR')
            else:
                # Múltiplos fornecedores sem vínculo claro
                score -= 15
                criterios.append('MULTIPLOS_FORNECEDORES')

            # Score mínimo
            score = max(0, score)

            candidatos.append({
                'titulo_id': titulo.id,
                'titulo_nf': titulo.titulo_nf,
                'parcela': titulo.parcela,
                'valor': titulo.valor_residual,
                'valor_original': titulo.valor_original,
                'vencimento': titulo.vencimento.strftime('%d/%m/%Y') if titulo.vencimento else None,
                'vencimento_date': titulo.vencimento,
                'fornecedor': titulo.raz_social_red or titulo.raz_social,
                'cnpj': titulo.cnpj,
                'empresa': titulo.empresa,
                'score': score,
                'criterio': '+'.join(criterios),
                'diferenca_valor': abs((titulo.valor_residual or 0) - valor),
                'sem_cnpj': True
            })

        return candidatos

    def _calcular_desconto_valor(self, valor_extrato: float, valor_titulo: float) -> Tuple[int, str]:
        """
        Calcula o desconto baseado na diferença de valores.

        Regras:
        - até R$ 0,01: 0%
        - até R$ 0,10: -3%
        - até R$ 0,30: -6%
        - até R$ 0,50: -10%
        - acima disso: -25%

        Returns:
            Tuple (desconto, criterio)
        """
        diferenca = abs(valor_extrato - valor_titulo)

        if diferenca <= 0.01:
            return 0, 'VALOR_EXATO'
        elif diferenca <= 0.10:
            return 3, f'VALOR_DIF_{diferenca:.2f}'
        elif diferenca <= 0.30:
            return 6, f'VALOR_DIF_{diferenca:.2f}'
        elif diferenca <= 0.50:
            return 10, f'VALOR_DIF_{diferenca:.2f}'
        else:
            return 25, f'VALOR_DIF_{diferenca:.2f}'

    def _vincular_titulo(self, item: ExtratoItem, match: Dict) -> None:
        """
        Vincula um título A PAGAR ao item de extrato.
        Usa titulo_pagar_id para manter integridade referencial correta.
        """
        item.titulo_pagar_id = match['titulo_id']  # FK correta para ContasAPagar
        item.titulo_nf = match['titulo_nf']
        item.titulo_parcela = parcela_to_int(match['parcela'])
        item.titulo_valor = match['valor']
        item.titulo_cliente = match['fornecedor']  # Para pagamentos, é o fornecedor
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
        Vincula manualmente um título A PAGAR ao item de extrato.
        """
        titulo = db.session.get(ContasAPagar,titulo_id) if titulo_id else None
        if not titulo:
            raise ValueError(f"Título {titulo_id} não encontrado")

        item.titulo_pagar_id = titulo.id  # FK correta para ContasAPagar
        item.titulo_nf = titulo.titulo_nf
        item.titulo_parcela = titulo.parcela_int
        item.titulo_valor = titulo.valor_residual
        item.titulo_cliente = titulo.raz_social_red or titulo.raz_social
        item.titulo_cnpj = titulo.cnpj
        item.titulo_vencimento = titulo.vencimento

        # Calcular score base pelo valor
        valor = abs(item.valor) if item.valor else 0
        desconto_valor, criterio_valor = self._calcular_desconto_valor(valor, titulo.valor_residual or 0)
        score = 100 - desconto_valor
        criterios = ['MANUAL']
        if criterio_valor:
            criterios.append(criterio_valor)

        # Aplicar desconto de vencimento (igual à busca de candidatos)
        if item.data_transacao and titulo.vencimento:
            if titulo.vencimento < item.data_transacao:
                # Vencimento anterior = -5%
                score -= 5
                criterios.append('VENC_ANTERIOR')
            elif titulo.vencimento > item.data_transacao:
                # Vencimento posterior = -10%
                score -= 10
                criterios.append('VENC_POSTERIOR')
            else:
                criterios.append('VENC_EXATO')

        # Score mínimo
        score = max(0, score)

        item.match_score = score
        item.match_criterio = '+'.join(criterios)

        item.status_match = 'MATCH_ENCONTRADO'
        item.mensagem = 'Título vinculado manualmente'

        db.session.commit()

    def _pre_sync_comprovantes(self, lote_id: int) -> None:
        """
        Pré-sync: sincroniza comprovantes LANCADOS antes do matching.

        Itens com statement_line_id que possuem comprovante LANCADO devem
        ser marcados como CONCILIADO via ConciliacaoSyncService, evitando
        que apareçam como SEM_MATCH ou MULTIPLOS no matching.
        """
        from app.financeiro.models_comprovante import (
            ComprovantePagamentoBoleto,
            LancamentoComprovante,
        )
        from app.financeiro.services.conciliacao_sync_service import ConciliacaoSyncService

        # Buscar itens PENDENTE do lote que têm statement_line_id
        itens_com_stl = ExtratoItem.query.filter(
            ExtratoItem.lote_id == lote_id,
            ExtratoItem.status_match == 'PENDENTE',
            ExtratoItem.statement_line_id.isnot(None),
        ).all()

        if not itens_com_stl:
            return

        logger.info(f"[Pré-sync] {len(itens_com_stl)} itens com statement_line_id para verificar")

        sync_service = ConciliacaoSyncService()
        sincronizados = 0

        for item in itens_com_stl:
            # Buscar comprovante correspondente
            comp = ComprovantePagamentoBoleto.query.filter_by(
                odoo_statement_line_id=item.statement_line_id
            ).first()

            if not comp:
                continue

            # Verificar se tem lançamento LANCADO
            lanc_lancado = LancamentoComprovante.query.filter_by(
                comprovante_id=comp.id,
                status='LANCADO',
            ).first()

            if not lanc_lancado:
                continue

            # Sincronizar via ConciliacaoSyncService (reutiliza lógica existente)
            try:
                resultado = sync_service.sync_comprovante_para_extrato(comp.id)
                if resultado and resultado.get('action') == 'synced':
                    sincronizados += 1
                    logger.info(
                        f"[Pré-sync] Comprovante #{comp.id} → Item {item.id} sincronizado"
                    )
            except Exception as e:
                logger.warning(f"[Pré-sync] Erro ao sincronizar comprovante #{comp.id}: {e}")

        if sincronizados:
            db.session.commit()
            logger.info(f"[Pré-sync] {sincronizados} itens sincronizados como CONCILIADO")

    def _normalizar_cnpj(self, cnpj: str) -> str:
        """
        Normaliza CNPJ removendo caracteres especiais.
        """
        if not cnpj:
            return ''
        return re.sub(r'\D', '', cnpj)


# =============================================================================
# TABELA DE SCORES DE MATCHING PARA PAGAMENTOS
# =============================================================================
#
# SCORE BASE: 100%
#
# DESCONTOS POR CNPJ:
#     0% - CNPJ_EXATO (CNPJ do extrato = CNPJ do título)
#    -2% - CNPJ_RAIZ (primeiros 8 dígitos iguais)
#   -15% - CNPJ_DIFERENTE
#
# DESCONTOS POR VALOR:
#     0% - VALOR_EXATO (diferença <= R$ 0,01)
#    -3% - diferença até R$ 0,10
#    -6% - diferença até R$ 0,30
#   -10% - diferença até R$ 0,50
#   -25% - diferença > R$ 0,50
#
# DESCONTOS POR VENCIMENTO:
#     0% - VENC_EXATO (vencimento = data pagamento)
#    -5% - VENC_ANTERIOR (título já estava vencido)
#   -10% - VENC_POSTERIOR (pagamento antecipado)
#
# DESCONTOS PARA BOLETOS (sem CNPJ):
#    -5% - UNICO_TITULO (apenas 1 título candidato)
#    -7% - UNICO_FORNECEDOR (N títulos, mas mesmo fornecedor)
#    -3% - FORNECEDOR_SOBROU (outros fornecedores já vinculados)
#   -15% - MULTIPLOS_FORNECEDORES (vários fornecedores, sem vínculo claro)
#
# SCORE MÍNIMO PARA AUTO-MATCH: 90 (configurável via SCORE_MINIMO_AUTO)
#
