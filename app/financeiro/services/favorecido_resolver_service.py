# -*- coding: utf-8 -*-
"""
Serviço de Resolução de Favorecido para Extrato Bancário
=========================================================

Pipeline de 6 camadas para identificar o favorecido (fornecedor) em
pagamentos de saída do extrato bancário.

Camadas (em ordem decrescente de confiança):
    Layer 0: Odoo partner_id → res.partner.l10n_br_cnpj  (95-100%)
    Layer 1: CNPJ/CPF via regex no payment_ref             (90-95%)
    Layer 2: Nome extraído do payment_ref (FAV.:, etc.)     (70-85%)
    Layer 3: CPF mascarado → busca em contas_a_pagar        (60-85%)
    Layer 4: Nome → busca fuzzy em contas_a_pagar           (60-85%)
    Layer 5: Classificação categórica (IMPOSTO, TARIFA...)  (90%)
    Layer 6: Não resolvido (fallback)                       (0%)

Autor: Sistema de Fretes
Data: 2026-02-11
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

from app import db
from app.financeiro.models import ExtratoItem, ExtratoLote, ContasAPagar
from app.financeiro.services.extrato_service import (
    REGEX_CPF_MASCARADO,
    REGEX_CPF_MASCARADO_TED,
    REGEX_FAV_NOME,
    REGEX_PAGAMENTO_NOME,
    PATTERNS_CATEGORIA,
    CATEGORIAS_SEM_FORNECEDOR,
    TIPOS_TRANSACAO_SAIDA,
)
from app.financeiro.services._resolver_utils import (
    normalizar_cnpj,
    tokenizar_nome,
    resolver_por_tokenizacao,
    buscar_nome_por_cnpj,
    prefetch_partner_cnpjs,
)

logger = logging.getLogger(__name__)


class FavorecidoResolverService:
    """
    Serviço para resolver o favorecido (fornecedor) em itens de extrato de saída.

    Executa um pipeline de 6 camadas em ordem decrescente de confiança.
    A primeira camada que resolver, vence.
    """

    def __init__(self, connection=None):
        self._connection = connection
        self._partner_cnpj_cache: Dict[int, Dict] = {}  # partner_id -> {cnpj, name}
        self._contas_pagar_cache: Optional[List] = None   # cache de fornecedores

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
        Resolve favorecidos para todos os itens de um lote de saída.

        Args:
            lote_id: ID do ExtratoLote

        Returns:
            Dict com estatísticas da resolução
        """
        lote = db.session.get(ExtratoLote, lote_id) if lote_id else None
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado")

        if lote.tipo_transacao != 'saida':
            raise ValueError(f"Lote {lote_id} não é de pagamentos (tipo={lote.tipo_transacao})")

        logger.info("=" * 60)
        logger.info(f"RESOLVENDO FAVORECIDOS - Lote {lote_id}")
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
            self._prefetch_partner_cnpjs(partner_ids)

        # Estatísticas
        stats = {
            'total': len(itens),
            'resolvidos': 0,
            'metodos': {},
        }

        for item in itens:
            try:
                self.resolver_item(item)

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

    def resolver_item(self, item: ExtratoItem) -> None:
        """
        Executa o pipeline de resolução para um item individual.

        Camadas são executadas em ordem. A primeira que resolver, vence.
        """
        payment_ref = item.payment_ref or ''

        # Classificar categoria de pagamento (sempre, independente de resolver)
        if not item.categoria_pagamento:
            item.categoria_pagamento = self._classificar_categoria(payment_ref)

        # Layer 0: Odoo Partner
        if self._layer0_odoo_partner(item):
            return

        # Layer 1: Regex CNPJ/CPF no payment_ref
        if self._layer1_regex_cnpj(item):
            return

        # Layer 2: Nome extraído do payment_ref → tokenização → busca
        if self._layer2_regex_nome(item):
            return

        # Layer 3: CPF mascarado
        if self._layer3_cpf_mascarado(item):
            return

        # Layer 4: Nome do parceiro Odoo → tokenização → busca
        if self._layer4_nome_fuzzy(item):
            return

        # Layer 5: Categoria (IMPOSTO, TARIFA, etc.)
        if self._layer5_categoria(item):
            return

        # Layer 6: Não resolvido
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
            self._prefetch_partner_cnpjs([item.odoo_partner_id])
            partner_data = self._partner_cnpj_cache.get(item.odoo_partner_id)

        if not partner_data:
            return False

        cnpj = partner_data.get('cnpj')
        nome = partner_data.get('name')

        if cnpj:
            cnpj_normalizado = self._normalizar_cnpj(cnpj)
            item.odoo_partner_cnpj = cnpj_normalizado
            item.favorecido_cnpj = cnpj_normalizado
            item.favorecido_nome = nome
            item.favorecido_metodo = 'ODOO_PARTNER'
            item.favorecido_confianca = 100
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
    # LAYER 1: Regex CNPJ
    # =========================================================================

    def _layer1_regex_cnpj(self, item: ExtratoItem) -> bool:
        """
        Resolve via CNPJ já extraído no import ou re-extração via regex.

        Confiança: 95 para formato padrão, 90 para formato com espaços.
        """
        cnpj = item.cnpj_pagador

        if cnpj:
            item.favorecido_cnpj = cnpj
            item.favorecido_metodo = 'REGEX_CNPJ'
            item.favorecido_confianca = 95

            # Tentar buscar nome via contas_a_pagar
            nome = self._buscar_nome_por_cnpj(cnpj)
            if nome:
                item.favorecido_nome = nome

            self._propagar_campos_legado(item)
            return True

        return False

    # =========================================================================
    # LAYER 2: Regex Nome → tokenização → busca
    # =========================================================================

    def _layer2_regex_nome(self, item: ExtratoItem) -> bool:
        """
        Extrai nome do payment_ref via regex e resolve via tokenização.

        Padrões:
        - FAV.: NOME: ...
        - Pagamento - NOME - CNPJ

        Confiança: 85 se match único, 70 se nome extraído sem match.
        """
        payment_ref = item.payment_ref or ''

        nome_extraido = None

        # Tentar FAV.:
        match_fav = REGEX_FAV_NOME.search(payment_ref)
        if match_fav:
            nome_extraido = match_fav.group(1).strip().rstrip(':')

        # Tentar Pagamento - NOME - CNPJ
        if not nome_extraido:
            match_pag = REGEX_PAGAMENTO_NOME.search(payment_ref)
            if match_pag:
                nome_extraido = match_pag.group(1).strip()

        if not nome_extraido:
            return False

        # Tentar resolver via tokenização
        resultado = self._resolver_por_tokenizacao(nome_extraido)

        if resultado:
            cnpj, raz_social, confianca = resultado
            item.favorecido_cnpj = cnpj
            item.favorecido_nome = raz_social
            item.favorecido_metodo = 'REGEX_NOME'
            item.favorecido_confianca = confianca
            self._propagar_campos_legado(item)
            return True

        # Não resolveu mas extraiu nome — salvar para matching posterior
        item.favorecido_nome = nome_extraido
        item.favorecido_metodo = 'REGEX_NOME'
        item.favorecido_confianca = 70
        self._propagar_campos_legado(item)
        return True

    # =========================================================================
    # LAYER 3: CPF Mascarado
    # =========================================================================

    def _layer3_cpf_mascarado(self, item: ExtratoItem) -> bool:
        """
        Resolve via CPF mascarado no payment_ref.

        Formatos:
        - ***.564.018-** → extrai 6 dígitos centrais
        - 058.***.***-05 → extrai 3 primeiros + 2 últimos

        Confiança: 85 se match único, 60 se ambíguo.
        """
        payment_ref = item.payment_ref or ''

        digitos_parciais = None

        # Formato ***.564.018-**
        match = REGEX_CPF_MASCARADO.search(payment_ref)
        if match:
            # Extrai "564.018" → "564018"
            digitos_parciais = re.sub(r'\D', '', match.group(1))

        # Formato 058.***.***-05
        if not digitos_parciais:
            match_ted = REGEX_CPF_MASCARADO_TED.search(payment_ref)
            if match_ted:
                # Extrai "058" + "05"
                digitos_parciais = match_ted.group(1) + match_ted.group(2)

        if not digitos_parciais:
            return False

        # Buscar em contas_a_pagar por CPF que contenha esses dígitos
        resultado = self._buscar_por_cpf_parcial(digitos_parciais)

        if resultado:
            cnpj, raz_social, confianca = resultado
            item.favorecido_cnpj = cnpj
            item.favorecido_nome = raz_social
            item.favorecido_metodo = 'CPF_PARCIAL'
            item.favorecido_confianca = confianca
            self._propagar_campos_legado(item)
            return True

        return False

    # =========================================================================
    # LAYER 4: Nome Fuzzy (odoo_partner_name ou nome_pagador)
    # =========================================================================

    def _layer4_nome_fuzzy(self, item: ExtratoItem) -> bool:
        """
        Resolve via nome do parceiro Odoo ou nome_pagador, usando tokenização.

        Usa: odoo_partner_name, nome_pagador, ou nome já extraído.

        Confiança: 85 se match único, 60 se ambíguo.
        """
        # Prioridade: odoo_partner_name > nome_pagador
        nome = item.odoo_partner_name or item.nome_pagador

        if not nome:
            return False

        # Se já tentou na Layer 2 com o mesmo nome, skip
        if item.favorecido_metodo == 'REGEX_NOME' and item.favorecido_nome == nome:
            return False

        resultado = self._resolver_por_tokenizacao(nome)

        if resultado:
            cnpj, raz_social, confianca = resultado
            item.favorecido_cnpj = cnpj
            item.favorecido_nome = raz_social
            item.favorecido_metodo = 'NOME_FUZZY'
            item.favorecido_confianca = confianca
            self._propagar_campos_legado(item)
            return True

        return False

    # =========================================================================
    # LAYER 5: Categoria
    # =========================================================================

    def _layer5_categoria(self, item: ExtratoItem) -> bool:
        """
        Classifica como categoria sem fornecedor (IMPOSTO, TARIFA, etc.).

        Confiança: 90.
        """
        categoria = item.categoria_pagamento

        if categoria and categoria in CATEGORIAS_SEM_FORNECEDOR:
            item.favorecido_metodo = 'CATEGORIA'
            item.favorecido_confianca = 90
            item.favorecido_nome = categoria
            return True

        # Tentar classificar pelo payment_ref diretamente
        payment_ref = item.payment_ref or ''
        for pattern, cat in PATTERNS_CATEGORIA:
            if pattern.search(payment_ref):
                item.categoria_pagamento = cat
                item.favorecido_metodo = 'CATEGORIA'
                item.favorecido_confianca = 90
                item.favorecido_nome = cat
                return True

        return False

    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================

    def _classificar_categoria(self, payment_ref: str) -> Optional[str]:
        """Classifica a categoria de pagamento pelo payment_ref."""
        if not payment_ref:
            return None

        # Tentar tipos de saída conhecidos
        for padrao, tipo in TIPOS_TRANSACAO_SAIDA.items():
            if padrao in payment_ref:
                return tipo

        # Tentar padrões categóricos
        for pattern, cat in PATTERNS_CATEGORIA:
            if pattern.search(payment_ref):
                return cat

        return 'OUTRO'

    def _prefetch_partner_cnpjs(self, partner_ids: List[int]) -> None:
        """Busca CNPJs de parceiros Odoo em batch. Delega para _resolver_utils."""
        prefetch_partner_cnpjs(self.connection, partner_ids, self._partner_cnpj_cache)

    def _normalizar_cnpj(self, cnpj_raw: str) -> str:
        """Normaliza CNPJ. Delega para _resolver_utils."""
        return normalizar_cnpj(cnpj_raw)

    def _tokenizar_nome(self, nome: str) -> List[str]:
        """Tokeniza nome de fornecedor. Delega para _resolver_utils."""
        return tokenizar_nome(nome)

    def _resolver_por_tokenizacao(self, nome: str) -> Optional[Tuple[str, str, int]]:
        """Resolve nome via tokenização em contas_a_pagar. Delega para _resolver_utils."""
        return resolver_por_tokenizacao(
            nome, ContasAPagar,
            campo_razao_social='raz_social',
            campo_cnpj='cnpj',
            campo_filtro_ativo='parcela_paga',
            filtro_ativo_valor=False
        )

    def _buscar_por_cpf_parcial(self, digitos: str) -> Optional[Tuple[str, str, int]]:
        """
        Busca fornecedor em contas_a_pagar por dígitos parciais de CPF/CNPJ.

        Args:
            digitos: Dígitos parciais extraídos (ex: "564018" ou "05805")

        Returns:
            Tuple (cnpj, raz_social, confiança) ou None
        """
        try:
            resultados = ContasAPagar.query.filter(
                ContasAPagar.parcela_paga == False,  # noqa: E712
                db.func.regexp_replace(ContasAPagar.cnpj, r'\D', '', 'g').like(f'%{digitos}%')
            ).limit(5).all()

        except Exception as e:
            logger.warning(f"Erro na busca por CPF parcial ({digitos}): {e}")
            return None

        if not resultados:
            return None

        # Deduplicar por CNPJ raiz
        cnpjs_unicos = {}
        for r in resultados:
            if r.cnpj:
                raiz = re.sub(r'\D', '', r.cnpj)[:8]
                if raiz not in cnpjs_unicos:
                    cnpjs_unicos[raiz] = r

        if len(cnpjs_unicos) == 1:
            fornecedor = list(cnpjs_unicos.values())[0]
            cnpj_normalizado = normalizar_cnpj(fornecedor.cnpj)
            return cnpj_normalizado, fornecedor.raz_social, 85

        if len(cnpjs_unicos) <= 3:
            # Poucos candidatos — ambíguo
            fornecedor = list(cnpjs_unicos.values())[0]
            cnpj_normalizado = normalizar_cnpj(fornecedor.cnpj)
            return cnpj_normalizado, fornecedor.raz_social, 60

        return None

    def _buscar_nome_por_cnpj(self, cnpj: str) -> Optional[str]:
        """Busca nome do fornecedor em contas_a_pagar pelo CNPJ. Delega para _resolver_utils."""
        return buscar_nome_por_cnpj(cnpj, ContasAPagar)

    def _propagar_campos_legado(self, item: ExtratoItem) -> None:
        """
        Propaga dados resolvidos para campos legado (cnpj_pagador, nome_pagador).

        Garante que o matching existente se beneficia imediatamente.
        """
        if item.favorecido_cnpj and not item.cnpj_pagador:
            item.cnpj_pagador = item.favorecido_cnpj

        if item.favorecido_nome and not item.nome_pagador:
            item.nome_pagador = item.favorecido_nome
