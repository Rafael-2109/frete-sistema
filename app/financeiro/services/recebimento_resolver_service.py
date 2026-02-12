# -*- coding: utf-8 -*-
"""
Serviço de Resolução de Pagador para Recebimentos (Extrato Entrada)
====================================================================

Pipeline de 5 camadas para identificar o pagador (cliente ou instituição
financeira) em recebimentos de entrada do extrato bancário.

Camadas (em ordem decrescente de confiança):
    Layer 0: Odoo partner_id → res.partner.l10n_br_cnpj  (95-100%)
    Layer 1: CNPJ já extraído → busca em contas_a_receber  (90-95%)
    Layer 2: Nome → tokenização → contas_a_receber          (70-85%)
    Layer 3: Classificação financeira (banco/FIDC/próprio)   (90%)
    Layer 4: Não resolvido (fallback)                        (0%)

Complementa o FavorecidoResolverService (saída) com lógica específica
para entrada: detecção de antecipações, cessões, transferências internas
e PIX de pessoa física com CPF mascarado.

Autor: Sistema de Fretes
Data: 2026-02-11
"""

import re
import logging
from typing import Dict, Tuple

from app import db
from app.financeiro.models import ExtratoItem, ExtratoLote, ContasAReceber
from app.financeiro.services._resolver_utils import (
    normalizar_cnpj,
    extrair_raiz_cnpj,
    resolver_por_tokenizacao,
    buscar_nome_por_cnpj,
    prefetch_partner_cnpjs,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES — CNPJs de Instituições Financeiras (NÃO são clientes)
# =============================================================================

# Bancos que fazem antecipação (confirming, cessão, etc.)
CNPJS_BANCOS: Dict[str, str] = {
    '90400888': 'SANTANDER',
    '60746948': 'BRADESCO',
    '01522368': 'BNP_PARIBAS',
    '62232889': 'DAYCOVAL',
    '00000000': 'BANCO_BRASIL',   # placeholder — ajustar quando descobrir
}

# FIDCs e fundos de cessão de crédito
CNPJS_FIDCS: Dict[str, str] = {
    '35689601': 'AGIS_FIDC',
    '60307274': 'BSB_FUNDO',
    '27967159': 'SOGIMA',
}

# CNPJs próprios (Nacom Goya e subsidiárias)
CNPJS_PROPRIOS: Dict[str, str] = {
    '61724241': 'NACOM_GOYA',
    '17811850': 'NG_PROMOCOES',
}

# Categorias de entrada que NÃO possuem título a receber correspondente
CATEGORIAS_SEM_TITULO_ENTRADA = {
    'ANTECIPACAO', 'CESSAO_CREDITO', 'TRANSFERENCIA_INTERNA', 'ESTORNO'
}

# Padrões de texto no payment_ref para classificação de categoria de entrada
PATTERNS_CATEGORIA_ENTRADA = [
    (re.compile(r'CONFIRMING|ANTECIPA[CÇ]', re.IGNORECASE), 'ANTECIPACAO'),
    (re.compile(r'Estorno\b', re.IGNORECASE), 'ESTORNO'),
    (re.compile(r'CESS[AÃ]O|SECURITIZA', re.IGNORECASE), 'CESSAO_CREDITO'),
    (re.compile(r'TRANSFER[EÊ]NCIA\s+INTERNA', re.IGNORECASE), 'TRANSFERENCIA_INTERNA'),
]

# Merge de todos os CNPJs de instituições para lookup rápido
_TODOS_CNPJS_INSTITUICOES: Dict[str, Tuple[str, str]] = {}
for _cnpj, _nome in CNPJS_BANCOS.items():
    _TODOS_CNPJS_INSTITUICOES[_cnpj] = (_nome, 'ANTECIPACAO')
for _cnpj, _nome in CNPJS_FIDCS.items():
    _TODOS_CNPJS_INSTITUICOES[_cnpj] = (_nome, 'CESSAO_CREDITO')
for _cnpj, _nome in CNPJS_PROPRIOS.items():
    _TODOS_CNPJS_INSTITUICOES[_cnpj] = (_nome, 'TRANSFERENCIA_INTERNA')


class RecebimentoResolverService:
    """
    Serviço para resolver o pagador em itens de extrato de entrada (recebimentos).

    Executa um pipeline de 5 camadas em ordem decrescente de confiança.
    A primeira camada que resolver, vence.
    """

    def __init__(self, connection=None):
        self._connection = connection
        self._partner_cnpj_cache: Dict[int, Dict] = {}

    @property
    def connection(self):
        """Retorna a conexão Odoo, criando se necessário."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise Exception("Falha na autenticação com Odoo")
        return self._connection

    # =========================================================================
    # MÉTODOS PÚBLICOS
    # =========================================================================

    def resolver_lote(self, lote_id: int) -> Dict:
        """
        Resolve pagadores para todos os itens de um lote de entrada.

        Args:
            lote_id: ID do ExtratoLote

        Returns:
            Dict com estatísticas da resolução
        """
        lote = db.session.get(ExtratoLote, lote_id) if lote_id else None
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado")

        if lote.tipo_transacao != 'entrada':
            raise ValueError(f"Lote {lote_id} não é de recebimentos (tipo={lote.tipo_transacao})")

        logger.info("=" * 60)
        logger.info(f"RESOLVENDO PAGADORES (ENTRADA) - Lote {lote_id}")
        logger.info("=" * 60)

        # Buscar itens sem favorecido resolvido
        itens = ExtratoItem.query.filter(
            ExtratoItem.lote_id == lote_id,
            ExtratoItem.favorecido_metodo.is_(None)
        ).all()

        logger.info(f"Itens a resolver: {len(itens)}")

        if not itens:
            return {'total': 0, 'resolvidos': 0, 'metodos': {}}

        # Pré-carregar CNPJs de parceiros Odoo (Layer 0)
        partner_ids = [i.odoo_partner_id for i in itens if i.odoo_partner_id]
        if partner_ids:
            prefetch_partner_cnpjs(self.connection, partner_ids, self._partner_cnpj_cache)

        # Estatísticas
        stats = {
            'total': len(itens),
            'resolvidos': 0,
            'metodos': {},
        }

        for item in itens:
            try:
                self._resolver_item(item)

                metodo = item.favorecido_metodo or 'NAO_RESOLVIDO'
                stats['metodos'][metodo] = stats['metodos'].get(metodo, 0) + 1
                if metodo != 'NAO_RESOLVIDO':
                    stats['resolvidos'] += 1

            except Exception as e:
                logger.error(f"Erro ao resolver item {item.id}: {e}")
                item.favorecido_metodo = 'ERRO'
                item.favorecido_confianca = 0
                stats['metodos']['ERRO'] = stats['metodos'].get('ERRO', 0) + 1

        db.session.commit()

        logger.info(f"Resolução concluída: {stats}")
        return stats

    def _resolver_item(self, item: ExtratoItem) -> None:
        """
        Executa o pipeline de resolução para um item de entrada.

        Camadas são executadas em ordem. A primeira que resolver, vence.
        """
        # Layer 0: Odoo Partner
        if self._layer0_odoo_partner(item):
            return

        # Layer 1: CNPJ já extraído
        if self._layer1_cnpj_extraido(item):
            return

        # Layer 2: Nome → tokenização → contas_a_receber
        if self._layer2_nome_tokenizacao(item):
            return

        # Layer 3: Classificação financeira (banco, FIDC, próprio)
        if self._layer3_classificacao_financeira(item):
            return

        # Layer 4: Não resolvido
        item.favorecido_metodo = 'NAO_RESOLVIDO'
        item.favorecido_confianca = 0

    # =========================================================================
    # LAYER 0: Odoo Partner
    # =========================================================================

    def _layer0_odoo_partner(self, item: ExtratoItem) -> bool:
        """
        Resolve via partner_id do Odoo.

        Se o item tem odoo_partner_id, busca o CNPJ do res.partner.
        Confiança: 100 se tem CNPJ, 95 se só tem nome.
        """
        if not item.odoo_partner_id:
            return False

        partner_data = self._partner_cnpj_cache.get(item.odoo_partner_id)

        if not partner_data:
            # Buscar individual se não está no cache
            prefetch_partner_cnpjs(self.connection, [item.odoo_partner_id], self._partner_cnpj_cache)
            partner_data = self._partner_cnpj_cache.get(item.odoo_partner_id)

        if not partner_data:
            return False

        cnpj = partner_data.get('cnpj')
        nome = partner_data.get('name')

        if cnpj:
            cnpj_normalizado = normalizar_cnpj(cnpj)
            item.odoo_partner_cnpj = cnpj_normalizado
            item.favorecido_cnpj = cnpj_normalizado
            item.favorecido_nome = nome
            item.favorecido_metodo = 'ODOO_PARTNER'
            item.favorecido_confianca = 100

            # Verificar se é instituição financeira (classificar categoria)
            self._classificar_se_instituicao(item, cnpj_normalizado)

            self._propagar_campos_legado(item)
            return True
        elif nome:
            item.favorecido_nome = nome
            item.favorecido_metodo = 'ODOO_PARTNER'
            item.favorecido_confianca = 95
            self._propagar_campos_legado(item)
            return True

        return False

    # =========================================================================
    # LAYER 1: CNPJ já extraído
    # =========================================================================

    def _layer1_cnpj_extraido(self, item: ExtratoItem) -> bool:
        """
        Resolve via CNPJ já extraído na importação (cnpj_pagador).

        Busca nome via contas_a_receber (em vez de contas_a_pagar).
        Confiança: 95.
        """
        cnpj = item.cnpj_pagador

        if not cnpj:
            return False

        item.favorecido_cnpj = cnpj
        item.favorecido_metodo = 'REGEX_CNPJ'
        item.favorecido_confianca = 95

        # Verificar se é instituição financeira
        if self._classificar_se_instituicao(item, cnpj):
            # É banco/FIDC — reclassificar para CATEGORIA com método correto
            item.favorecido_metodo = 'CATEGORIA'
            item.favorecido_confianca = 90
            self._propagar_campos_legado(item)
            return True

        # Buscar nome via contas_a_receber
        nome = buscar_nome_por_cnpj(cnpj, ContasAReceber)
        if nome:
            item.favorecido_nome = nome

        self._propagar_campos_legado(item)
        return True

    # =========================================================================
    # LAYER 2: Nome → Tokenização → ContasAReceber
    # =========================================================================

    def _layer2_nome_tokenizacao(self, item: ExtratoItem) -> bool:
        """
        Resolve via nome do pagador (extraído ou do parceiro Odoo) por tokenização.

        Para PIX com CPF mascarado: o nome vem em nome_pagador ou odoo_partner_name.
        Busca em contas_a_receber.raz_social e raz_social_red.

        Confiança: 85 se match único, 70 se nome extraído sem match.
        """
        # Prioridade: nome_pagador > odoo_partner_name
        nome = item.nome_pagador or item.odoo_partner_name

        if not nome:
            return False

        # Não tentar tokenizar nomes muito curtos (< 3 chars) ou genéricos
        if len(nome.strip()) < 3:
            return False

        # Tentar resolver via tokenização em contas_a_receber
        resultado = resolver_por_tokenizacao(
            nome, ContasAReceber,
            campo_razao_social='raz_social',
            campo_cnpj='cnpj',
            campo_filtro_ativo='parcela_paga',
            filtro_ativo_valor=False
        )

        if resultado:
            cnpj, raz_social, confianca = resultado
            item.favorecido_cnpj = cnpj
            item.favorecido_nome = raz_social
            item.favorecido_metodo = 'NOME_TOKENIZACAO'
            item.favorecido_confianca = confianca
            self._propagar_campos_legado(item)
            return True

        # Também tentar com raz_social_red (nome fantasia mais curto)
        resultado_red = resolver_por_tokenizacao(
            nome, ContasAReceber,
            campo_razao_social='raz_social_red',
            campo_cnpj='cnpj',
            campo_filtro_ativo='parcela_paga',
            filtro_ativo_valor=False
        )

        if resultado_red:
            cnpj, raz_social, confianca = resultado_red
            item.favorecido_cnpj = cnpj
            item.favorecido_nome = raz_social
            item.favorecido_metodo = 'NOME_TOKENIZACAO'
            item.favorecido_confianca = confianca
            self._propagar_campos_legado(item)
            return True

        return False

    # =========================================================================
    # LAYER 3: Classificação Financeira
    # =========================================================================

    def _layer3_classificacao_financeira(self, item: ExtratoItem) -> bool:
        """
        Classifica como operação financeira (banco, FIDC, transferência interna, estorno).

        Detecta por:
        1. CNPJ na whitelist de instituições
        2. Keywords no payment_ref

        Confiança: 90.
        """
        payment_ref = item.payment_ref or ''

        # 1. Tentar por CNPJ já disponível
        cnpj = item.cnpj_pagador or item.favorecido_cnpj
        if cnpj:
            if self._classificar_se_instituicao(item, cnpj):
                item.favorecido_metodo = 'CATEGORIA'
                item.favorecido_confianca = 90
                return True

        # 2. Tentar por keywords no payment_ref
        for pattern, categoria in PATTERNS_CATEGORIA_ENTRADA:
            if pattern.search(payment_ref):
                item.categoria_pagamento = categoria
                item.favorecido_metodo = 'CATEGORIA'
                item.favorecido_confianca = 90
                item.favorecido_nome = categoria

                # Marcar como SEM_MATCH pois não tem título correspondente
                if item.status_match == 'PENDENTE':
                    item.status_match = 'SEM_MATCH'
                    item.mensagem = f'Categoria {categoria} — operação financeira'

                return True

        return False

    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================

    def _classificar_se_instituicao(self, item: ExtratoItem, cnpj: str) -> bool:
        """
        Verifica se o CNPJ é de uma instituição financeira e classifica a categoria.

        Args:
            item: ExtratoItem para atualizar
            cnpj: CNPJ formatado ou só dígitos

        Returns:
            True se é instituição financeira (classificou categoria)
        """
        raiz = extrair_raiz_cnpj(cnpj)
        if not raiz:
            return False

        if raiz in _TODOS_CNPJS_INSTITUICOES:
            nome_inst, categoria = _TODOS_CNPJS_INSTITUICOES[raiz]
            item.categoria_pagamento = categoria
            item.favorecido_nome = nome_inst

            # Marcar como SEM_MATCH pois operações financeiras não têm título a receber
            if item.status_match == 'PENDENTE':
                item.status_match = 'SEM_MATCH'
                item.mensagem = f'Categoria {categoria} — {nome_inst}'

            return True

        return False

    def _propagar_campos_legado(self, item: ExtratoItem) -> None:
        """
        Propaga dados resolvidos para campos legado (cnpj_pagador, nome_pagador).

        Garante que o matching existente se beneficia imediatamente.
        """
        if item.favorecido_cnpj and not item.cnpj_pagador:
            item.cnpj_pagador = item.favorecido_cnpj

        if item.favorecido_nome and not item.nome_pagador:
            item.nome_pagador = item.favorecido_nome
