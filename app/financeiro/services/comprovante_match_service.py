# -*- coding: utf-8 -*-
"""
Servico de Matching: Comprovante Pagamento ↔ Fatura Odoo
=========================================================

Encontra faturas de fornecedor no Odoo que correspondem a comprovantes
de pagamento de boleto, calculando score de confianca para cada match.

Fluxo:
1. Detectar empresa pelo CNPJ do pagador (Nacom ou LF)
2. Validar beneficiario (fornecedor direto ou financeira)
3. Buscar faturas candidatas no Odoo
4. Parsear numero_documento (NF + parcela)
5. Recalcular valores de parcelas se necessario
6. Calcular score de confianca
7. Persistir melhores matches

Uso:
    from app.financeiro.services.comprovante_match_service import ComprovanteMatchService

    service = ComprovanteMatchService()
    resultado = service.executar_matching_comprovantes(comprovante_ids=[1, 2, 3])
"""

import re
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional

from app import db
from app.financeiro.models_comprovante import (
    ComprovantePagamentoBoleto,
    LancamentoComprovante,
)
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES - MAPEAMENTO DE EMPRESAS
# =============================================================================

# CNPJ completo → company_ids Odoo
# FONTE: app/recebimento/routes/views.py:1581-1584
CNPJ_EMPRESAS = {
    '61724241000178': {'company_ids': [1, 3, 4], 'nome': 'NACOM GOYA - FB'},
    '61724241000259': {'company_ids': [1, 3, 4], 'nome': 'NACOM GOYA - SC'},
    '61724241000330': {'company_ids': [1, 3, 4], 'nome': 'NACOM GOYA - CD'},
    '18467441000163': {'company_ids': [5], 'nome': 'LA FAMIGLIA - LF'},
}

# Raiz do CNPJ (8 digitos) → company_ids
RAIZ_CNPJ_EMPRESAS = {
    '61724241': [1, 3, 4],  # Nacom (FB, SC, CD)
    '18467441': [5],         # LF
}

# =============================================================================
# CONSTANTES - SCORING
# =============================================================================

SCORE_MINIMO_AUTO = 85
LIMITE_CANDIDATOS = 20

# Campos do Odoo para busca de faturas (account.move.line payable)
CAMPOS_FATURA_ODOO = [
    'id', 'name', 'credit', 'debit', 'balance',
    'amount_residual', 'amount_residual_currency',
    'reconciled', 'matched_debit_ids', 'matched_credit_ids',
    'date_maturity', 'date',
    'partner_id', 'move_id', 'company_id',
    'l10n_br_cobranca_parcela',
    'x_studio_nf_e',
    'account_type', 'parent_state',
]

# Campos do Odoo para busca de invoices (account.move)
CAMPOS_MOVE_ODOO = [
    'id', 'name', 'amount_total', 'amount_residual',
    'invoice_payment_term_id', 'partner_id', 'company_id',
    'state', 'move_type',
]


# =============================================================================
# UTILITARIOS
# =============================================================================

def _limpar_cnpj(cnpj: str) -> Optional[str]:
    """Remove formatacao do CNPJ, retornando apenas digitos."""
    if not cnpj:
        return None
    return re.sub(r'\D', '', cnpj.strip())


def _extrair_raiz_cnpj(cnpj_limpo: str) -> Optional[str]:
    """Extrai os 8 primeiros digitos (raiz) do CNPJ."""
    if not cnpj_limpo or len(cnpj_limpo) < 8:
        return None
    return cnpj_limpo[:8]


def _formatar_cnpj(cnpj_limpo: str) -> Optional[str]:
    """Formata CNPJ (14 digitos) para XX.XXX.XXX/XXXX-XX.

    O Odoo armazena l10n_br_cnpj formatado, entao precisamos
    formatar antes de buscar com operador '='.
    """
    if not cnpj_limpo:
        return None
    # Garantir que temos apenas digitos
    digitos = re.sub(r'\D', '', cnpj_limpo)
    if len(digitos) != 14:
        return cnpj_limpo  # Retorna como esta se nao for CNPJ valido
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:14]}"


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class ComprovanteMatchService:
    """
    Servico de matching entre ComprovantePagamentoBoleto
    e faturas de fornecedor (account.move.line payable) no Odoo.
    """

    def __init__(self, connection=None):
        """
        Args:
            connection: OdooConnection ja autenticada (opcional).
                        Se None, cria nova conexao internamente.
        """
        self._connection = connection
        self.estatisticas = {
            'processados': 0,
            'com_match': 0,
            'sem_match': 0,
            'erros': 0,
        }
        # Cache para evitar queries repetidas ao Odoo
        self._cache_partners = {}        # cnpj -> partner_data
        self._cache_faturas_partner = {}  # partner_id -> [faturas]
        self._cache_recalculos = {}       # move_id -> {parcela: valor}

    @property
    def connection(self):
        """Conexao lazy - cria e autentica na primeira chamada."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            self._connection.authenticate()
        return self._connection

    # =========================================================================
    # METODO PRINCIPAL - BATCH
    # =========================================================================

    def executar_matching_comprovantes(
        self,
        comprovante_ids: List[int] = None,
        filtros: Dict = None,
        callback_progresso=None,
    ) -> Dict:
        """
        Executa matching em batch para comprovantes selecionados ou todos pendentes.

        Cada comprovante e commitado individualmente para atomicidade.
        Se um falhar, os anteriores ja estao salvos.

        Args:
            comprovante_ids: IDs especificos ou None para todos sem match
            filtros: Dict com data_inicio, data_fim (opcionais)
            callback_progresso: Funcao(processados, total, ultimo_resultado)
                                chamada apos cada comprovante processado

        Returns:
            Dict com estatisticas do processamento
        """
        import time

        logger.info("=== INICIO MATCHING BATCH ===")
        self.estatisticas = {
            'processados': 0, 'com_match': 0, 'sem_match': 0, 'erros': 0,
        }
        detalhes = []

        # Buscar comprovantes para processar
        query = ComprovantePagamentoBoleto.query

        if comprovante_ids:
            query = query.filter(ComprovantePagamentoBoleto.id.in_(comprovante_ids))
        else:
            # Todos que NAO tem lancamento CONFIRMADO
            subq = db.session.query(LancamentoComprovante.comprovante_id).filter(
                LancamentoComprovante.status == 'CONFIRMADO'
            ).subquery()
            query = query.filter(~ComprovantePagamentoBoleto.id.in_(subq))

        if filtros:
            if filtros.get('data_inicio'):
                query = query.filter(
                    ComprovantePagamentoBoleto.data_pagamento >= filtros['data_inicio']
                )
            if filtros.get('data_fim'):
                query = query.filter(
                    ComprovantePagamentoBoleto.data_pagamento <= filtros['data_fim']
                )

        comprovantes = query.order_by(ComprovantePagamentoBoleto.data_pagamento.desc()).all()
        total = len(comprovantes)
        logger.info(f"Comprovantes a processar: {total}")

        for idx, comp in enumerate(comprovantes, 1):
            try:
                resultado = self._processar_comprovante(comp)
                detalhes.append(resultado)

                if resultado.get('match_encontrado'):
                    self.estatisticas['com_match'] += 1
                else:
                    self.estatisticas['sem_match'] += 1

                # Commit individual por comprovante
                try:
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Erro commit comp={comp.id}: {e}", exc_info=True)
                    db.session.rollback()

            except Exception as e:
                logger.error(f"Erro no comprovante {comp.id}: {e}", exc_info=True)
                self.estatisticas['erros'] += 1
                detalhes.append({
                    'comprovante_id': comp.id,
                    'numero_documento': comp.numero_documento,
                    'match_encontrado': False,
                    'erro': str(e),
                })
                db.session.rollback()

            self.estatisticas['processados'] += 1

            # Callback de progresso (para RQ/Redis)
            if callback_progresso:
                try:
                    callback_progresso(
                        processados=idx,
                        total=total,
                        ultimo_resultado=detalhes[-1] if detalhes else {},
                    )
                except Exception:
                    pass  # Nao interromper por erro no callback

            # Rate limiting para proteger o Odoo (~20 chamadas/s max)
            time.sleep(0.05)

        logger.info(f"=== FIM MATCHING BATCH === {self.estatisticas}")
        return {
            'sucesso': True,
            'estatisticas': self.estatisticas,
            'detalhes': detalhes,
        }

    # =========================================================================
    # METODO PRINCIPAL - INDIVIDUAL
    # =========================================================================

    def buscar_candidatos_comprovante(self, comprovante_id: int) -> Dict:
        """
        Busca candidatos de match para um comprovante especifico.
        NAO persiste - retorna para UI exibir e usuario confirmar.

        Args:
            comprovante_id: ID do comprovante

        Returns:
            Dict com comprovante + lista de candidatos com score
        """
        comp = ComprovantePagamentoBoleto.query.get(comprovante_id)
        if not comp:
            return {'sucesso': False, 'erro': f'Comprovante {comprovante_id} nao encontrado'}

        try:
            candidatos = self._buscar_candidatos(comp)
            return {
                'sucesso': True,
                'comprovante': comp.to_dict(),
                'candidatos': candidatos,
                'total_candidatos': len(candidatos),
            }
        except Exception as e:
            logger.error(f"Erro ao buscar candidatos para {comprovante_id}: {e}", exc_info=True)
            return {
                'sucesso': False,
                'comprovante': comp.to_dict(),
                'erro': str(e),
            }

    # =========================================================================
    # CONFIRMACAO / REJEICAO
    # =========================================================================

    def confirmar_match(self, lancamento_id: int, usuario: str) -> Dict:
        """Confirma um match (PENDENTE -> CONFIRMADO)."""
        lanc = LancamentoComprovante.query.get(lancamento_id)
        if not lanc:
            return {'sucesso': False, 'erro': 'Lancamento nao encontrado'}
        if lanc.status != 'PENDENTE':
            return {'sucesso': False, 'erro': f'Status atual: {lanc.status}. Apenas PENDENTE pode ser confirmado.'}

        lanc.status = 'CONFIRMADO'
        lanc.confirmado_em = agora_brasil()
        lanc.confirmado_por = usuario

        # Rejeitar outros lancamentos PENDENTES e CONFIRMADOS do mesmo comprovante
        # (LANCADO nao e tocado — ja foi baixado no Odoo)
        outros = LancamentoComprovante.query.filter(
            LancamentoComprovante.comprovante_id == lanc.comprovante_id,
            LancamentoComprovante.id != lanc.id,
            LancamentoComprovante.status.in_(['PENDENTE', 'CONFIRMADO']),
        ).all()
        for outro in outros:
            outro.status = 'REJEITADO'
            outro.rejeitado_em = agora_brasil()
            outro.rejeitado_por = usuario
            outro.motivo_rejeicao = f'Substituido: lancamento {lancamento_id} confirmado por {usuario}'

        db.session.commit()
        logger.info(f"Lancamento {lancamento_id} CONFIRMADO por {usuario}")
        return {'sucesso': True, 'lancamento': lanc.to_dict()}

    def rejeitar_match(self, lancamento_id: int, usuario: str, motivo: str = None) -> Dict:
        """Rejeita um match (PENDENTE -> REJEITADO)."""
        lanc = LancamentoComprovante.query.get(lancamento_id)
        if not lanc:
            return {'sucesso': False, 'erro': 'Lancamento nao encontrado'}
        if lanc.status != 'PENDENTE':
            return {'sucesso': False, 'erro': f'Status atual: {lanc.status}. Apenas PENDENTE pode ser rejeitado.'}

        lanc.status = 'REJEITADO'
        lanc.rejeitado_em = agora_brasil()
        lanc.rejeitado_por = usuario
        lanc.motivo_rejeicao = motivo

        db.session.commit()
        logger.info(f"Lancamento {lancamento_id} REJEITADO por {usuario}: {motivo}")
        return {'sucesso': True, 'lancamento': lanc.to_dict()}

    # =========================================================================
    # VINCULACAO MANUAL
    # =========================================================================

    def vincular_manual(
        self,
        comprovante_id: int,
        nf: str,
        parcela: int,
        company_id: int,
        usuario: str,
    ) -> Dict:
        """
        Vinculacao manual: usuario informa NF + parcela + company.

        Busca a fatura no Odoo e cria lancamento CONFIRMADO diretamente.
        """
        comp = ComprovantePagamentoBoleto.query.get(comprovante_id)
        if not comp:
            return {'sucesso': False, 'erro': 'Comprovante nao encontrado'}

        try:
            # Buscar fatura no Odoo
            domain = [
                ['x_studio_nf_e', '=', str(nf)],
                ['l10n_br_cobranca_parcela', '=', parcela],
                ['account_type', '=', 'liability_payable'],
                ['parent_state', '=', 'posted'],
                ['company_id', '=', company_id],
                ['date_maturity', '!=', '2000-01-01'],
            ]
            faturas = self.connection.search_read(
                'account.move.line', domain, fields=CAMPOS_FATURA_ODOO, limit=5
            )

            if not faturas:
                # Fallback: buscar por move_name
                domain_fallback = [
                    ['move_id.name', 'ilike', str(nf)],
                    ['l10n_br_cobranca_parcela', '=', parcela],
                    ['account_type', '=', 'liability_payable'],
                    ['parent_state', '=', 'posted'],
                    ['company_id', '=', company_id],
                    ['date_maturity', '!=', '2000-01-01'],
                ]
                faturas = self.connection.search_read(
                    'account.move.line', domain_fallback, fields=CAMPOS_FATURA_ODOO, limit=5
                )

            if not faturas:
                return {
                    'sucesso': False,
                    'erro': f'Fatura NF {nf} parcela {parcela} nao encontrada na company {company_id}',
                }

            fatura = faturas[0]

            # Rejeitar lancamentos existentes (PENDENTE e CONFIRMADO) do mesmo comprovante
            existentes = LancamentoComprovante.query.filter(
                LancamentoComprovante.comprovante_id == comprovante_id,
                LancamentoComprovante.status.in_(['PENDENTE', 'CONFIRMADO']),
            ).all()
            for existente in existentes:
                existente.status = 'REJEITADO'
                existente.rejeitado_em = agora_brasil()
                existente.rejeitado_por = usuario
                existente.motivo_rejeicao = (
                    f'Substituido por vinculacao manual: NF {nf}/{parcela}'
                )
            if existentes:
                logger.info(
                    f"Vinculacao manual: rejeitados {len(existentes)} lancamento(s) "
                    f"anteriores do comp={comprovante_id}"
                )

            # Criar lancamento CONFIRMADO
            lanc = self._criar_lancamento(
                comp, fatura,
                nf_numero=str(nf),
                parcela_num=parcela,
                score=100,
                criterios='VINCULACAO_MANUAL',
                e_financeira=False,
                valor_recalculado=None,
            )
            lanc.status = 'CONFIRMADO'
            lanc.confirmado_em = agora_brasil()
            lanc.confirmado_por = usuario

            db.session.add(lanc)
            db.session.commit()

            logger.info(f"Vinculacao manual: comp={comprovante_id} → NF {nf}/{parcela} por {usuario}")
            return {'sucesso': True, 'lancamento': lanc.to_dict()}

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro vinculacao manual: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e)}

    # =========================================================================
    # FLUXO INTERNO - PROCESSAMENTO DE 1 COMPROVANTE
    # =========================================================================

    def _processar_comprovante(self, comp: ComprovantePagamentoBoleto) -> Dict:
        """
        Processa matching para 1 comprovante.
        Salva melhor(es) match(es) na tabela lancamento_comprovante.
        """
        logger.info(
            f"Processando comp={comp.id} | doc={comp.numero_documento} "
            f"| benef={comp.beneficiario_cnpj_cpf} | valor={comp.valor_documento}"
        )

        # Limpar lancamentos PENDENTES anteriores deste comprovante
        LancamentoComprovante.query.filter(
            LancamentoComprovante.comprovante_id == comp.id,
            LancamentoComprovante.status == 'PENDENTE',
        ).delete()

        candidatos = self._buscar_candidatos(comp)

        if not candidatos:
            return {
                'comprovante_id': comp.id,
                'numero_documento': comp.numero_documento,
                'match_encontrado': False,
                'motivo': 'Nenhum candidato encontrado',
            }

        # Salvar os melhores candidatos (top 5)
        salvos = 0
        for cand in candidatos[:5]:
            lanc = self._criar_lancamento_from_candidato(comp, cand)
            db.session.add(lanc)
            salvos += 1

        return {
            'comprovante_id': comp.id,
            'numero_documento': comp.numero_documento,
            'match_encontrado': True,
            'candidatos': len(candidatos),
            'salvos': salvos,
            'melhor_score': candidatos[0]['score'] if candidatos else 0,
        }

    def _buscar_candidatos(self, comp: ComprovantePagamentoBoleto) -> List[Dict]:
        """
        Busca e scoreia candidatos de match para um comprovante.

        Returns:
            Lista de candidatos ordenada por score DESC, vencimento ASC.
        """
        # 1. Detectar company_ids pelo pagador
        company_ids = self._detectar_company_ids(comp.pagador_cnpj_cpf)
        if not company_ids:
            logger.warning(f"CNPJ pagador nao reconhecido: {comp.pagador_cnpj_cpf}")
            return []

        # 2. Validar beneficiario
        benef_cnpj = _limpar_cnpj(comp.beneficiario_cnpj_cpf)
        benef_info = self._validar_beneficiario(benef_cnpj, company_ids)
        e_financeira = benef_info.get('e_financeira', False)
        partner_id = benef_info.get('partner_id')

        # 3. Buscar faturas candidatas
        if e_financeira:
            # Financeira: buscar TODAS faturas em aberto das companies
            faturas = self._buscar_faturas_todas(company_ids)
            logger.info(f"Financeira detectada. Buscando em todas as faturas: {len(faturas)}")
        else:
            # Fornecedor direto: filtrar por partner
            if partner_id:
                faturas = self._buscar_faturas_por_partner(partner_id, company_ids)
            else:
                faturas = []
            logger.info(f"Fornecedor direto partner_id={partner_id}. Faturas: {len(faturas)}")

        # Pre-filtrar por faixa de valor razoavel quando financeira
        # Evita trazer candidatos com valores absurdamente diferentes
        if e_financeira and faturas:
            valor_comp = float(comp.valor_documento or comp.valor_pago or 0)
            if valor_comp > 0:
                margem = max(valor_comp * 5, 500)  # 5x o valor ou R$500 minimo
                faturas_filtradas = [
                    f for f in faturas
                    if abs(float(f.get('credit', 0) or 0)) <= margem
                ]
                logger.info(
                    f"Pre-filtro valor (financeira): {len(faturas)} -> {len(faturas_filtradas)} "
                    f"(margem R$ {margem:.2f} para comp R$ {valor_comp:.2f})"
                )
                faturas = faturas_filtradas

        if not faturas:
            return []

        # 4. Parsear numero_documento
        parse_result = self._parsear_numero_documento(comp.numero_documento, faturas)
        logger.info(f"Parse doc: {parse_result}")

        # 5. Filtrar candidatos por NF (se parseado)
        candidatos_filtrados = self._filtrar_por_nf(faturas, parse_result)

        if not candidatos_filtrados:
            # Se nao encontrou com NF, usar todas faturas (score menor)
            candidatos_filtrados = faturas
            parse_result['confianca'] = max(parse_result.get('confianca', 0) - 20, 0)

        # 5b. Para FIDC sem NF: afunilar por vencimento se disponivel
        if e_financeira and parse_result.get('metodo') == 'VAZIO' and comp.data_vencimento:
            faturas_venc_exato = [
                f for f in candidatos_filtrados
                if self._vencimento_fatura_match(f, comp.data_vencimento, tolerancia_dias=0)
            ]
            faturas_venc_proximo = [
                f for f in candidatos_filtrados
                if self._vencimento_fatura_match(f, comp.data_vencimento, tolerancia_dias=5)
            ]

            if faturas_venc_exato:
                candidatos_filtrados = faturas_venc_exato
                logger.info(
                    f"FIDC afunilamento: vencimento exato {comp.data_vencimento} "
                    f"-> {len(faturas_venc_exato)} candidato(s)"
                )
            elif faturas_venc_proximo:
                candidatos_filtrados = faturas_venc_proximo
                logger.info(
                    f"FIDC afunilamento: vencimento +-5d {comp.data_vencimento} "
                    f"-> {len(faturas_venc_proximo)} candidato(s)"
                )
            # Se nenhum vencimento proximo, manter todos (o scoring vai penalizar)

        # 6. Recalcular parcelas e scorear cada candidato
        candidatos_scoreados = []
        for fatura in candidatos_filtrados[:LIMITE_CANDIDATOS]:
            score_data = self._scorear_candidato(comp, fatura, parse_result, e_financeira)
            if score_data:
                candidatos_scoreados.append(score_data)

        # Aplicar penalidade por multiplicidade
        n_cands = len(candidatos_scoreados)
        penalidade_mult = 0
        if 2 <= n_cands <= 3:
            penalidade_mult = 3
        elif n_cands >= 4:
            penalidade_mult = 8

        for c in candidatos_scoreados:
            c['score'] = max(c['score'] - penalidade_mult, 0)
            if penalidade_mult > 0:
                c['criterios'].append(f'MULTIPLICIDADE(-{penalidade_mult}%: {n_cands} candidatos)')

        # Ordenar: score DESC, vencimento ASC
        candidatos_scoreados.sort(
            key=lambda x: (-x['score'], x.get('odoo_vencimento') or '9999-99-99')
        )

        return candidatos_scoreados

    # =========================================================================
    # ETAPA 1: DETECCAO DE EMPRESA
    # =========================================================================

    def _detectar_company_ids(self, pagador_cnpj: str) -> List[int]:
        """
        Detecta company_ids a partir do CNPJ do pagador.

        Returns:
            Lista de company_ids ou lista vazia se nao reconhecido.
        """
        cnpj_limpo = _limpar_cnpj(pagador_cnpj)
        if not cnpj_limpo:
            return []

        # Tentar match exato
        info = CNPJ_EMPRESAS.get(cnpj_limpo)
        if info:
            return info['company_ids']

        # Tentar raiz (8 digitos)
        raiz = _extrair_raiz_cnpj(cnpj_limpo)
        if raiz and raiz in RAIZ_CNPJ_EMPRESAS:
            return RAIZ_CNPJ_EMPRESAS[raiz]

        return []

    # =========================================================================
    # ETAPA 2: VALIDACAO DE BENEFICIARIO
    # =========================================================================

    def _validar_beneficiario(self, cnpj_beneficiario: str, company_ids: List[int]) -> Dict:
        """
        Valida se o beneficiario e fornecedor real ou financeira.

        Returns:
            Dict com:
            - e_fornecedor: bool
            - e_financeira: bool
            - partner_id: int (se encontrado)
            - partner_name: str
            - partner_cnpj: str
        """
        if not cnpj_beneficiario:
            return {'e_fornecedor': False, 'e_financeira': False, 'partner_id': None}

        # Cache
        cache_key = cnpj_beneficiario
        if cache_key in self._cache_partners:
            return self._cache_partners[cache_key]

        resultado = {
            'e_fornecedor': False,
            'e_financeira': False,
            'partner_id': None,
            'partner_name': None,
            'partner_cnpj': cnpj_beneficiario,
        }

        try:
            # Buscar partner no Odoo por CNPJ formatado
            # O campo l10n_br_cnpj no Odoo armazena formatado (XX.XXX.XXX/XXXX-XX)
            cnpj_formatado = _formatar_cnpj(cnpj_beneficiario)
            partners = self.connection.search_read(
                'res.partner',
                [['l10n_br_cnpj', '=', cnpj_formatado]],
                fields=['id', 'name', 'l10n_br_cnpj'],
                limit=5,
            )

            # Fallback: buscar pela raiz FORMATADA com ilike
            # O campo l10n_br_cnpj armazena "33.652.456/0001-95", entao
            # ilike com "33652456" (limpo) NAO funciona.
            # Precisamos formatar a raiz: "33.652.456"
            if not partners:
                raiz_limpa = _extrair_raiz_cnpj(cnpj_beneficiario)
                if raiz_limpa and len(raiz_limpa) == 8:
                    raiz_formatada = f"{raiz_limpa[:2]}.{raiz_limpa[2:5]}.{raiz_limpa[5:8]}"
                    logger.info(
                        f"CNPJ formatado '{cnpj_formatado}' nao encontrado. "
                        f"Tentando raiz formatada '{raiz_formatada}' com ilike."
                    )
                    partners = self.connection.search_read(
                        'res.partner',
                        [['l10n_br_cnpj', 'ilike', raiz_formatada]],
                        fields=['id', 'name', 'l10n_br_cnpj'],
                        limit=5,
                    )

            if not partners:
                # CNPJ nao encontrado no Odoo -> pode ser financeira ou nao cadastrado
                logger.info(
                    f"Beneficiario CNPJ '{cnpj_beneficiario}' nao encontrado no Odoo "
                    f"(tentou formatado='{cnpj_formatado}' e raiz). Classificado como financeira."
                )
                resultado['e_financeira'] = True
                self._cache_partners[cache_key] = resultado
                return resultado

            partner = partners[0]
            resultado['partner_id'] = partner['id']
            resultado['partner_name'] = partner.get('name', '')

            # Verificar se este partner tem faturas de fornecedor (in_invoice)
            faturas_count = self.connection.search_read(
                'account.move',
                [
                    ['partner_id', '=', partner['id']],
                    ['move_type', '=', 'in_invoice'],
                    ['state', '=', 'posted'],
                    ['company_id', 'in', company_ids],
                ],
                fields=['id'],
                limit=1,
            )

            if faturas_count:
                resultado['e_fornecedor'] = True
            else:
                resultado['e_financeira'] = True
                logger.info(
                    f"CNPJ {cnpj_beneficiario} ({partner.get('name', '')}) "
                    f"encontrado mas sem faturas in_invoice -> financeira"
                )

        except Exception as e:
            logger.error(f"Erro ao validar beneficiario {cnpj_beneficiario}: {e}")
            resultado['e_financeira'] = True  # Em caso de erro, assumir financeira (mais seguro)

        self._cache_partners[cache_key] = resultado
        return resultado

    # =========================================================================
    # ETAPA 3: BUSCA DE FATURAS
    # =========================================================================

    def _buscar_faturas_por_partner(self, partner_id: int, company_ids: List[int]) -> List[Dict]:
        """Busca faturas payable em aberto para um partner especifico."""
        cache_key = f"{partner_id}_{','.join(map(str, company_ids))}"
        if cache_key in self._cache_faturas_partner:
            return self._cache_faturas_partner[cache_key]

        domain = [
            ['partner_id', '=', partner_id],
            ['account_type', '=', 'liability_payable'],
            ['parent_state', '=', 'posted'],
            ['date_maturity', '!=', '2000-01-01'],
            ['company_id', 'in', company_ids],
        ]

        try:
            faturas = self.connection.search_read(
                'account.move.line', domain, fields=CAMPOS_FATURA_ODOO, limit=500
            )
            self._cache_faturas_partner[cache_key] = faturas
            return faturas
        except Exception as e:
            logger.error(f"Erro buscar faturas partner {partner_id}: {e}")
            return []

    def _buscar_faturas_todas(self, company_ids: List[int]) -> List[Dict]:
        """Busca TODAS faturas payable em aberto (para quando beneficiario e financeira)."""
        cache_key = f"all_{','.join(map(str, company_ids))}"
        if cache_key in self._cache_faturas_partner:
            return self._cache_faturas_partner[cache_key]

        domain = [
            ['account_type', '=', 'liability_payable'],
            ['parent_state', '=', 'posted'],
            ['date_maturity', '!=', '2000-01-01'],
            ['company_id', 'in', company_ids],
            ['amount_residual', '!=', 0],
        ]

        try:
            faturas = self.connection.search_read(
                'account.move.line', domain, fields=CAMPOS_FATURA_ODOO, limit=2000
            )
            self._cache_faturas_partner[cache_key] = faturas
            return faturas
        except Exception as e:
            logger.error(f"Erro buscar todas faturas: {e}")
            return []

    # =========================================================================
    # ETAPA 4: PARSING DO NUMERO_DOCUMENTO
    # =========================================================================

    def _parsear_numero_documento(
        self, numero_documento: str, faturas: List[Dict]
    ) -> Dict:
        """
        Extrai NF + parcela do numero_documento do comprovante.

        Estrategias (em ordem):
        1. Com separador (-, /, espaco)
        2. Com letra final (A=1, B=2...)
        3. Sem separador (digitos contiguos) - valida contra NFs do fornecedor
        4. Fallback: doc inteiro = NF, parcela=1

        Returns:
            Dict com nf, parcela, metodo, confianca
        """
        if not numero_documento or numero_documento.strip() in ('--', '-', '---'):
            return {'nf': None, 'parcela': None, 'metodo': 'VAZIO', 'confianca': 0}

        doc = numero_documento.strip()

        # Construir set de NFs conhecidas do fornecedor
        nfs_conhecidas = set()
        parcelas_por_nf = {}
        for f in faturas:
            nf_val = f.get('x_studio_nf_e')
            if nf_val:
                nf_str = str(nf_val).strip()
                nfs_conhecidas.add(nf_str)
                parc = f.get('l10n_br_cobranca_parcela', 1)
                parcelas_por_nf.setdefault(nf_str, set()).add(parc)

        # Estrategia 1: Com separador (-, /, espaco)
        # Tolera ruido OCR no final: "78908-4 5" → captura NF=78908, parcela=4, ignora " 5"
        sep_match = re.match(r'^0*(\d+)\s*[-/\s]\s*0*(\d{1,3})(?:\s+\d{1,2})?$', doc)
        if sep_match:
            nf = sep_match.group(1)
            parcela = int(sep_match.group(2))

            # Validar NF contra conhecidas
            if nf in nfs_conhecidas:
                return {
                    'nf': nf,
                    'parcela': parcela,
                    'metodo': 'SEPARADOR',
                    'confianca': 95,
                }

            # NF nao conhecida: pode ter prefixo embutido (ex: "1002288" → NF "2288")
            nf_limpa = nf.lstrip('0') or '0'
            for i in range(1, len(nf_limpa)):
                sub_nf = nf_limpa[i:]
                if sub_nf in nfs_conhecidas:
                    return {
                        'nf': sub_nf,
                        'parcela': parcela,
                        'metodo': 'SEPARADOR_VALIDADO',
                        'confianca': 88,
                    }

            # NF nao encontrada nas conhecidas — manter resultado original
            # (pode ser NF nova ainda nao cadastrada no Odoo)
            return {
                'nf': nf,
                'parcela': parcela,
                'metodo': 'SEPARADOR',
                'confianca': 95,
            }

        # Estrategia 1b: Com espaco — lado direito é bloco NF+parcela zero-padded
        # Caso: "5 0006641" → prefixo="5", bloco="6641" → NF=664, parcela=1
        sep_bloco = re.match(r'^(\d+)\s+(0*)(\d+)$', doc)
        if sep_bloco:
            bloco = sep_bloco.group(3)  # dígitos significativos após zeros
            if len(bloco) >= 2:
                # Tentar extrair NF+parcela do bloco (1 ou 2 dígitos de parcela)
                for suffix_len in [1, 2]:
                    if len(bloco) <= suffix_len:
                        continue
                    nf_candidata = bloco[:-suffix_len]
                    parcela_val = int(bloco[-suffix_len:])
                    if parcela_val == 0:
                        continue
                    if nf_candidata in nfs_conhecidas:
                        return {
                            'nf': nf_candidata,
                            'parcela': parcela_val,
                            'metodo': 'SEPARADOR_BLOCO',
                            'confianca': 85,
                        }

        # Estrategia 2: Letra final (A=1, B=2...)
        letra_match = re.match(r'^0*(\d+)([A-Z])$', doc.upper())
        if letra_match:
            nf = letra_match.group(1)
            parcela = ord(letra_match.group(2)) - ord('A') + 1
            return {
                'nf': nf,
                'parcela': parcela,
                'metodo': 'LETRA',
                'confianca': 90,
            }

        # Estrategia 3: Sem separador - so digitos
        doc_limpo = re.sub(r'\D', '', doc)
        if doc_limpo and len(doc_limpo) > 1:
            # Tentar remover 1, 2, 3 digitos do final como parcela
            for suffix_len in [1, 2, 3]:
                if len(doc_limpo) <= suffix_len:
                    continue

                nf_candidata = doc_limpo[:-suffix_len].lstrip('0') or '0'
                parcela_str = doc_limpo[-suffix_len:]
                parcela_val = int(parcela_str)

                if parcela_val == 0:
                    continue

                # Verificar se NF existe nas conhecidas
                if nf_candidata in nfs_conhecidas:
                    return {
                        'nf': nf_candidata,
                        'parcela': parcela_val,
                        'metodo': f'SEM_SEPARADOR_{suffix_len}D',
                        'confianca': 80,
                    }

            # Se fornecedor so tem parcela unica, o doc inteiro pode ser a NF
            tem_multiplas = any(len(p) > 1 for p in parcelas_por_nf.values())
            if not tem_multiplas:
                nf_candidata = doc_limpo.lstrip('0') or '0'
                if nf_candidata in nfs_conhecidas:
                    return {
                        'nf': nf_candidata,
                        'parcela': None,
                        'metodo': 'PARCELA_UNICA',
                        'confianca': 85,
                    }

            # Estrategia 3c: Busca exaustiva — NF embutida em posicao desconhecida
            # Gera subsequencias a partir de cada posicao e valida contra nfs_conhecidas
            if nfs_conhecidas:
                for start in range(len(doc_limpo)):
                    substr = doc_limpo[start:].lstrip('0') or '0'
                    if not substr or substr == '0':
                        continue
                    for suffix_len in [1, 2]:
                        if len(substr) <= suffix_len:
                            continue
                        nf_candidata = substr[:-suffix_len]
                        parcela_val = int(substr[-suffix_len:])
                        if parcela_val == 0:
                            continue
                        if nf_candidata in nfs_conhecidas:
                            return {
                                'nf': nf_candidata,
                                'parcela': parcela_val,
                                'metodo': 'BUSCA_EXAUSTIVA',
                                'confianca': 70,
                            }
                    # Tambem tentar substr inteiro como NF (sem parcela)
                    if substr in nfs_conhecidas:
                        return {
                            'nf': substr,
                            'parcela': None,
                            'metodo': 'BUSCA_EXAUSTIVA_SEM_PARCELA',
                            'confianca': 65,
                        }

            # Fallback: doc inteiro como NF
            nf_candidata = doc_limpo.lstrip('0') or '0'
            return {
                'nf': nf_candidata,
                'parcela': None,
                'metodo': 'FALLBACK_COMPLETO',
                'confianca': 50,
            }

        # Nao parseavel
        return {
            'nf': doc,
            'parcela': None,
            'metodo': 'NAO_PARSEADO',
            'confianca': 20,
        }

    # =========================================================================
    # ETAPA 5: RECALCULO DE PARCELAS
    # =========================================================================

    def _recalcular_parcelas(self, move_id: int) -> Optional[Dict]:
        """
        Recalcula valores das parcelas dividindo total por N.

        Recalcula SOMENTE se nenhuma parcela tem pagamento.
        Se alguma ja tem pagamento, retorna valores originais.

        Returns:
            Dict {parcela_num: {'valor_original': x, 'valor_recalculado': y, ...}}
            ou None se erro.
        """
        if move_id in self._cache_recalculos:
            return self._cache_recalculos[move_id]

        try:
            # Buscar total da fatura
            moves = self.connection.search_read(
                'account.move',
                [['id', '=', move_id]],
                fields=['amount_total', 'invoice_payment_term_id'],
                limit=1,
            )
            if not moves:
                return None

            total = moves[0].get('amount_total', 0)

            # Buscar TODAS as parcelas payable desta fatura
            parcelas = self.connection.search_read(
                'account.move.line',
                [
                    ['move_id', '=', move_id],
                    ['account_type', '=', 'liability_payable'],
                    ['date_maturity', '!=', '2000-01-01'],
                ],
                fields=[
                    'id', 'credit', 'amount_residual',
                    'l10n_br_cobranca_parcela', 'date_maturity',
                    'matched_debit_ids', 'reconciled',
                ],
                limit=50,
            )

            if not parcelas:
                return None

            # Verificar se alguma parcela tem pagamento
            alguma_com_pagamento = any(
                p.get('matched_debit_ids') or p.get('reconciled')
                for p in parcelas
            )

            resultado = {}
            if alguma_com_pagamento:
                # Nao recalcular - usar valores originais
                for p in parcelas:
                    num = str(p.get('l10n_br_cobranca_parcela', 0))
                    resultado[num] = {
                        'valor_original': p.get('credit', 0),
                        'valor_recalculado': None,
                        'recalculado': False,
                        'move_line_id': p['id'],
                    }
            else:
                # Recalcular: dividir total igualmente
                n = len(parcelas)
                valor_parcela = round(total / n, 2)
                soma_n_menos_1 = round(valor_parcela * (n - 1), 2)
                valor_ultima = round(total - soma_n_menos_1, 2)

                parcelas_sorted = sorted(
                    parcelas,
                    key=lambda p: p.get('l10n_br_cobranca_parcela', 0)
                )

                for idx, p in enumerate(parcelas_sorted):
                    num = str(p.get('l10n_br_cobranca_parcela', idx + 1))
                    is_last = (idx == n - 1)
                    resultado[num] = {
                        'valor_original': p.get('credit', 0),
                        'valor_recalculado': valor_ultima if is_last else valor_parcela,
                        'recalculado': True,
                        'move_line_id': p['id'],
                    }

            self._cache_recalculos[move_id] = resultado
            return resultado

        except Exception as e:
            logger.error(f"Erro recalcular parcelas move_id={move_id}: {e}")
            return None

    # =========================================================================
    # ETAPA 6: FILTRAGEM E SCORING
    # =========================================================================

    def _filtrar_por_nf(self, faturas: List[Dict], parse_result: Dict) -> List[Dict]:
        """Filtra faturas pelo numero da NF e parcela parseados."""
        nf = parse_result.get('nf')
        parcela = parse_result.get('parcela')

        if not nf:
            return faturas

        filtradas = []
        for f in faturas:
            nf_odoo = str(f.get('x_studio_nf_e', '')).strip()

            # Match da NF
            if nf_odoo == nf:
                # Se temos parcela, filtrar tambem por parcela
                if parcela is not None:
                    parcela_odoo = f.get('l10n_br_cobranca_parcela', 0)
                    if parcela_odoo == parcela:
                        filtradas.append(f)
                else:
                    filtradas.append(f)

        return filtradas

    def _vencimento_fatura_match(
        self, fatura: Dict, data_comp: date, tolerancia_dias: int = 0
    ) -> bool:
        """Verifica se o vencimento da fatura esta dentro da tolerancia em relacao ao comprovante."""
        vencimento_str = fatura.get('date_maturity')
        if not vencimento_str or vencimento_str == '2000-01-01':
            return False
        if isinstance(vencimento_str, str):
            try:
                vencimento = datetime.strptime(vencimento_str, '%Y-%m-%d').date()
            except ValueError:
                return False
        elif isinstance(vencimento_str, date):
            vencimento = vencimento_str
        else:
            return False
        return abs((data_comp - vencimento).days) <= tolerancia_dias

    def _scorear_candidato(
        self,
        comp: ComprovantePagamentoBoleto,
        fatura: Dict,
        parse_result: Dict,
        e_financeira: bool,
    ) -> Optional[Dict]:
        """
        Calcula score de confianca de um candidato.

        Returns:
            Dict com dados do candidato + score + criterios, ou None se invalido.
        """
        score = 100
        criterios = []

        # --- CNPJ ---
        if e_financeira:
            score -= 15
            criterios.append('CNPJ_FINANCEIRA(-15%)')
        else:
            benef_cnpj = _limpar_cnpj(comp.beneficiario_cnpj_cpf)
            partner_id_data = fatura.get('partner_id')
            if partner_id_data and benef_cnpj:
                # CNPJ direto = 0%, raiz = -3%
                # Ja filtrado por partner_id, entao e match direto
                criterios.append('CNPJ_DIRETO(0%)')
            else:
                score -= 3
                criterios.append('CNPJ_RAIZ(-3%)')

        # --- VALOR ---
        valor_comp = float(comp.valor_documento or comp.valor_pago or 0)
        valor_odoo = abs(float(fatura.get('credit', 0)))
        valor_recalculado = None

        # Tentar recalculo
        move_id_data = fatura.get('move_id')
        move_id = move_id_data[0] if isinstance(move_id_data, (list, tuple)) else move_id_data
        parcela_num = fatura.get('l10n_br_cobranca_parcela', 0)

        recalculo = self._recalcular_parcelas(move_id) if move_id else None
        if recalculo:
            info_parcela = recalculo.get(str(parcela_num))
            if info_parcela and info_parcela.get('recalculado'):
                valor_recalculado = info_parcela['valor_recalculado']

        # Comparar valor: usar recalculado se disponivel
        valor_comparar = valor_recalculado if valor_recalculado is not None else valor_odoo
        diff = abs(valor_comp - valor_comparar)

        if diff <= 0.01:
            if valor_recalculado is not None:
                score -= 2
                criterios.append(f'VALOR_RECALCULADO_EXATO(-2%: diff={diff:.2f})')
            else:
                criterios.append(f'VALOR_EXATO(0%: diff={diff:.2f})')
        elif diff <= 0.10:
            score -= 3
            criterios.append(f'VALOR_PROXIMO(-3%: diff={diff:.2f})')
        elif diff <= 0.50:
            score -= 6
            criterios.append(f'VALOR_PROXIMO(-6%: diff={diff:.2f})')
        elif diff <= 1.00:
            score -= 10
            criterios.append(f'VALOR_PROXIMO(-10%: diff={diff:.2f})')
        else:
            score -= 25
            criterios.append(f'VALOR_DIFERENTE(-25%: diff={diff:.2f})')

        # --- NF PARSE ---
        metodo = parse_result.get('metodo', 'NAO_PARSEADO')
        if metodo == 'SEPARADOR':
            criterios.append('NF_SEPARADOR(0%)')
        elif metodo == 'SEPARADOR_VALIDADO':
            score -= 2
            criterios.append('NF_SEPARADOR_VALIDADO(-2%)')
        elif metodo == 'LETRA':
            score -= 2
            criterios.append('NF_LETRA(-2%)')
        elif metodo.startswith('SEM_SEPARADOR'):
            score -= 5
            criterios.append(f'NF_{metodo}(-5%)')
        elif metodo == 'SEPARADOR_BLOCO':
            score -= 3
            criterios.append('NF_SEPARADOR_BLOCO(-3%)')
        elif metodo == 'PARCELA_UNICA':
            criterios.append('NF_PARCELA_UNICA(0%)')
        elif metodo.startswith('BUSCA_EXAUSTIVA'):
            score -= 8
            criterios.append(f'NF_{metodo}(-8%)')
        elif metodo == 'FALLBACK_COMPLETO':
            score -= 15
            criterios.append('NF_FALLBACK(-15%)')
        elif metodo == 'VAZIO':
            score -= 20
            criterios.append('NF_VAZIO(-20%)')
        elif metodo == 'NAO_PARSEADO':
            score -= 20
            criterios.append('NF_NAO_PARSEADO(-20%)')

        # --- Extrair vencimento da fatura (necessario para scoring) ---
        vencimento_str = fatura.get('date_maturity')
        vencimento = None
        if vencimento_str and vencimento_str != '2000-01-01':
            if isinstance(vencimento_str, str):
                try:
                    vencimento = datetime.strptime(vencimento_str, '%Y-%m-%d').date()
                except ValueError:
                    vencimento = None
            elif isinstance(vencimento_str, date):
                vencimento = vencimento_str

        # --- VENCIMENTO ---
        # Comparar data_vencimento do comprovante com date_maturity da fatura
        comp_vencimento = comp.data_vencimento  # date ou None (do banco)
        if comp_vencimento and vencimento:
            diff_dias = abs((comp_vencimento - vencimento).days)
            if diff_dias == 0:
                score += 3
                criterios.append('VENCIMENTO_EXATO(+3%)')
            elif diff_dias <= 5:
                score -= 3
                criterios.append(f'VENCIMENTO_PROXIMO(-3%: {diff_dias}d)')
            elif diff_dias <= 30:
                score -= 8
                criterios.append(f'VENCIMENTO_DISTANTE(-8%: {diff_dias}d)')
            else:
                score -= 15
                criterios.append(f'VENCIMENTO_MUITO_DISTANTE(-15%: {diff_dias}d)')
        elif comp_vencimento and not vencimento:
            score -= 5
            criterios.append('VENCIMENTO_FATURA_SEM_DATA(-5%)')

        # --- PARCELA ---
        # Se o parse identificou parcela, verificar se coincide com a fatura
        parcela_parseada = parse_result.get('parcela')
        parcela_fatura = fatura.get('l10n_br_cobranca_parcela')
        if parcela_parseada is not None and parcela_fatura is not None:
            if parcela_parseada == parcela_fatura:
                score += 2
                criterios.append(f'PARCELA_MATCH(+2%: p{parcela_parseada})')
            else:
                score -= 10
                criterios.append(f'PARCELA_MISMATCH(-10%: parse={parcela_parseada} odoo={parcela_fatura})')

        score = min(max(score, 0), 100)

        # Extrair dados do candidato
        partner_id_val = fatura.get('partner_id')
        partner_id = partner_id_val[0] if isinstance(partner_id_val, (list, tuple)) else partner_id_val
        partner_name = partner_id_val[1] if isinstance(partner_id_val, (list, tuple)) and len(partner_id_val) > 1 else ''

        move_name = ''
        if isinstance(move_id_data, (list, tuple)) and len(move_id_data) > 1:
            move_name = move_id_data[1]

        company_id_val = fatura.get('company_id')
        company_id = company_id_val[0] if isinstance(company_id_val, (list, tuple)) else company_id_val

        return {
            'odoo_move_line_id': fatura['id'],
            'odoo_move_id': move_id,
            'odoo_move_name': move_name,
            'odoo_partner_id': partner_id,
            'odoo_partner_name': partner_name,
            'odoo_company_id': company_id,
            'nf_numero': str(fatura.get('x_studio_nf_e') or parse_result.get('nf') or ''),
            'nf_parseada': parse_result.get('nf'),
            'parcela': fatura.get('l10n_br_cobranca_parcela'),
            'odoo_valor_original': valor_odoo,
            'odoo_valor_residual': abs(float(fatura.get('amount_residual', 0))),
            'odoo_valor_recalculado': valor_recalculado,
            'odoo_vencimento': vencimento.isoformat() if vencimento else None,
            'odoo_vencimento_fmt': vencimento.strftime('%d/%m/%Y') if vencimento else None,
            'score': score,
            'criterios': criterios,
            'diferenca_valor': round(diff, 2),
            'beneficiario_e_financeira': e_financeira,
        }

    # =========================================================================
    # PERSISTENCIA
    # =========================================================================

    def _criar_lancamento_from_candidato(
        self, comp: ComprovantePagamentoBoleto, candidato: Dict
    ) -> LancamentoComprovante:
        """Cria LancamentoComprovante a partir de um candidato scoreado."""
        return LancamentoComprovante(
            comprovante_id=comp.id,
            odoo_move_line_id=candidato.get('odoo_move_line_id'),
            odoo_move_id=candidato.get('odoo_move_id'),
            odoo_move_name=candidato.get('odoo_move_name'),
            odoo_partner_id=candidato.get('odoo_partner_id'),
            odoo_partner_name=candidato.get('odoo_partner_name'),
            odoo_partner_cnpj=candidato.get('odoo_partner_cnpj'),
            odoo_company_id=candidato.get('odoo_company_id'),
            nf_numero=candidato.get('nf_numero'),
            parcela=candidato.get('parcela'),
            odoo_valor_original=candidato.get('odoo_valor_original'),
            odoo_valor_residual=candidato.get('odoo_valor_residual'),
            odoo_valor_recalculado=candidato.get('odoo_valor_recalculado'),
            odoo_vencimento=datetime.strptime(
                candidato['odoo_vencimento'], '%Y-%m-%d'
            ).date() if candidato.get('odoo_vencimento') else None,
            match_score=candidato.get('score', 0),
            match_criterios=json.dumps(candidato.get('criterios', []), ensure_ascii=False),
            diferenca_valor=candidato.get('diferenca_valor'),
            beneficiario_e_financeira=candidato.get('beneficiario_e_financeira', False),
            status='PENDENTE',
        )

    def _criar_lancamento(
        self,
        comp: ComprovantePagamentoBoleto,
        fatura: Dict,
        nf_numero: str,
        parcela_num: int,
        score: int,
        criterios: str,
        e_financeira: bool,
        valor_recalculado: Optional[float],
    ) -> LancamentoComprovante:
        """Cria LancamentoComprovante a partir de dados brutos."""
        partner_id_val = fatura.get('partner_id')
        partner_id = partner_id_val[0] if isinstance(partner_id_val, (list, tuple)) else partner_id_val
        partner_name = partner_id_val[1] if isinstance(partner_id_val, (list, tuple)) and len(partner_id_val) > 1 else ''

        move_id_val = fatura.get('move_id')
        move_id = move_id_val[0] if isinstance(move_id_val, (list, tuple)) else move_id_val
        move_name = move_id_val[1] if isinstance(move_id_val, (list, tuple)) and len(move_id_val) > 1 else ''

        company_id_val = fatura.get('company_id')
        company_id = company_id_val[0] if isinstance(company_id_val, (list, tuple)) else company_id_val

        vencimento_str = fatura.get('date_maturity')
        vencimento = None
        if vencimento_str and vencimento_str != '2000-01-01':
            if isinstance(vencimento_str, str):
                try:
                    vencimento = datetime.strptime(vencimento_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            elif isinstance(vencimento_str, date):
                vencimento = vencimento_str

        valor_odoo = abs(float(fatura.get('credit', 0)))
        valor_comp = float(comp.valor_documento or comp.valor_pago or 0)
        diff = abs(valor_comp - (valor_recalculado or valor_odoo))

        return LancamentoComprovante(
            comprovante_id=comp.id,
            odoo_move_line_id=fatura['id'],
            odoo_move_id=move_id,
            odoo_move_name=move_name,
            odoo_partner_id=partner_id,
            odoo_partner_name=partner_name,
            odoo_company_id=company_id,
            nf_numero=nf_numero,
            parcela=parcela_num,
            odoo_valor_original=valor_odoo,
            odoo_valor_residual=abs(float(fatura.get('amount_residual', 0))),
            odoo_valor_recalculado=valor_recalculado,
            odoo_vencimento=vencimento,
            match_score=score,
            match_criterios=criterios,
            diferenca_valor=round(diff, 2),
            beneficiario_e_financeira=e_financeira,
            status='PENDENTE',
        )
