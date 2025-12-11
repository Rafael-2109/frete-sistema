# -*- coding: utf-8 -*-
"""
Serviço de Conciliação - Extrato Bancário no Odoo
=================================================

Executa a conciliação de linhas de extrato com títulos no Odoo.

FLUXO MULTI-COMPANY (descoberto em 2025-12-11):
===============================================

O título pode estar em empresa diferente do extrato:
- Título: Empresa 4 (CD)
- Extrato: Empresa 1 (FB)

Quando o título já foi baixado via CNAB/manual, existe um payment que
criou uma linha na conta "PAGAMENTOS/RECEBIMENTOS PENDENTES" (26868).

A conciliação do extrato conecta:
- Linha do PAYMENT (conta PENDENTES, empresa do título)
- Linha do EXTRATO (conta TRANSITÓRIA, empresa do banco)

Processo:
1. Buscar título e verificar se tem payment vinculado (matched_credit_ids)
2. Se tiver payment, buscar linha DÉBITO na conta PENDENTES (não reconciliada)
3. Buscar linha de CRÉDITO do extrato (conta TRANSITÓRIA)
4. Executar reconcile([payment_pendente_line_id, extrato_credit_line_id])

Se o título NÃO tiver payment (caso raro), tentar reconciliar diretamente.

Referência: scripts/analise_baixa_titulos/ANALISE_CONCILIACAO_EXTRATO_MULTICOMPANY.md

Autor: Sistema de Fretes
Data: 2025-12-11 (atualizado com lógica multi-company)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app import db
from app.financeiro.models import ExtratoLote, ExtratoItem, ContasAReceber
from app.financeiro.services.baixa_titulos_service import BaixaTitulosService

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES - IDs de contas contábeis no Odoo
# =============================================================================
CONTA_PAGAMENTOS_PENDENTES = 26868  # 1110100004 PAGAMENTOS/RECEBIMENTOS PENDENTES
CONTA_TRANSITORIA = 22199           # 1110100003 TRANSITÓRIA DE VALORES
CONTA_CLIENTES_NACIONAIS = 24801    # 1120100001 CLIENTES NACIONAIS


# Campos para snapshot
CAMPOS_SNAPSHOT_TITULO = [
    'id', 'name', 'debit', 'credit', 'balance',
    'amount_residual', 'amount_residual_currency',
    'reconciled', 'matched_credit_ids', 'matched_debit_ids',
    'full_reconcile_id', 'matching_number',
    'date_maturity', 'partner_id', 'move_id', 'company_id',
    'l10n_br_paga', 'l10n_br_cobranca_situacao', 'l10n_br_cobranca_nossonumero'
]


class ExtratoConciliacaoService:
    """
    Serviço para conciliar linhas de extrato com títulos no Odoo.
    """

    def __init__(self, connection=None):
        self._connection = connection
        self._baixa_service = None  # Lazy init para reutilizar métodos de pagamento
        self.estatisticas = {
            'processados': 0,
            'conciliados': 0,
            'erros': 0
        }

    @property
    def connection(self):
        """Retorna a conexão Odoo, criando se necessário."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise Exception("Falha na autenticação com Odoo")
        return self._connection

    @property
    def baixa_service(self) -> BaixaTitulosService:
        """
        Retorna instância do BaixaTitulosService para reutilizar métodos de pagamento.
        Usa mesma conexão Odoo para evitar autenticações duplicadas.
        """
        if self._baixa_service is None:
            self._baixa_service = BaixaTitulosService(connection=self.connection)
        return self._baixa_service

    def conciliar_lote(self, lote_id: int) -> Dict:
        """
        Concilia todos os itens aprovados de um lote.

        Args:
            lote_id: ID do lote

        Returns:
            Dict com estatísticas
        """
        lote = ExtratoLote.query.get(lote_id)
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado")

        logger.info(f"=" * 60)
        logger.info(f"CONCILIANDO LOTE {lote_id} - {lote.nome}")
        logger.info(f"=" * 60)

        # Buscar itens aprovados
        itens = ExtratoItem.query.filter_by(
            lote_id=lote_id,
            aprovado=True,
            status='APROVADO'
        ).all()

        logger.info(f"Itens a conciliar: {len(itens)}")

        for item in itens:
            try:
                self.conciliar_item(item)
                self.estatisticas['conciliados'] += 1
            except Exception as e:
                logger.error(f"Erro no item {item.id}: {e}")
                item.status = 'ERRO'
                item.mensagem = str(e)
                self.estatisticas['erros'] += 1

            self.estatisticas['processados'] += 1
            db.session.commit()

        logger.info(f"Conciliação concluída: {self.estatisticas}")

        return self.estatisticas

    def conciliar_item(self, item: ExtratoItem) -> Dict:
        """
        Concilia um item individual no Odoo.

        FLUXO MULTI-COMPANY:
        1. Se título tem payment vinculado (CNAB): reconcilia linha PENDENTES com linha EXTRATO
        2. Se título não tem payment: tenta reconciliar diretamente (mesma empresa)

        Args:
            item: ExtratoItem a conciliar

        Returns:
            Dict com resultado
        """
        logger.info(f"Conciliando item {item.id}: NF {item.titulo_nf} P{item.titulo_parcela}")

        if not item.titulo_id:
            raise ValueError("Item não possui título vinculado")

        if not item.credit_line_id:
            # Buscar linha de crédito se não tiver
            item.credit_line_id = self._buscar_linha_credito(item.move_id)
            if not item.credit_line_id:
                raise ValueError(f"Linha de crédito não encontrada para move_id {item.move_id}")

        # Buscar título local
        titulo = ContasAReceber.query.get(item.titulo_id)
        if not titulo:
            raise ValueError(f"Título {item.titulo_id} não encontrado no sistema")

        # Buscar título no Odoo (SEM filtro de empresa - vamos buscar por NF+parcela)
        titulo_odoo = self._buscar_titulo_odoo_multicompany(
            titulo.titulo_nf, titulo.parcela
        )
        if not titulo_odoo:
            raise ValueError(
                f"Título NF {titulo.titulo_nf} parcela {titulo.parcela} não encontrado no Odoo. "
                f"CNPJ: {titulo.cnpj}. "
                f"Verifique se o título existe."
            )

        titulo_odoo_id = titulo_odoo['id']
        titulo_company = titulo_odoo.get('company_id')
        titulo_company_id = titulo_company[0] if isinstance(titulo_company, (list, tuple)) else titulo_company
        titulo_company_name = titulo_company[1] if isinstance(titulo_company, (list, tuple)) else str(titulo_company)

        logger.info(f"  Título encontrado: ID={titulo_odoo_id}, Empresa={titulo_company_name}")

        # Verificar se título já foi baixado (tem payment vinculado)
        matched_credit_ids = titulo_odoo.get('matched_credit_ids', [])
        l10n_br_paga = titulo_odoo.get('l10n_br_paga', False)

        # Capturar snapshot ANTES
        snapshot_antes = self._capturar_snapshot(titulo_odoo_id)
        item.set_snapshot_antes(snapshot_antes)

        # =========================================================================
        # LÓGICA MULTI-COMPANY: Se título tem payment, reconciliar via conta PENDENTES
        # =========================================================================
        if matched_credit_ids:
            logger.info(f"  Título JÁ TEM payment vinculado (matched_credit_ids: {matched_credit_ids})")
            logger.info(f"  l10n_br_paga: {l10n_br_paga}")

            # Buscar linha do payment na conta PENDENTES (não reconciliada)
            payment_pendente_line = self._buscar_linha_payment_pendentes(matched_credit_ids)

            if payment_pendente_line:
                payment_pendente_line_id = payment_pendente_line['id']
                logger.info(
                    f"  Encontrada linha PENDENTES do payment: ID={payment_pendente_line_id}, "
                    f"saldo={payment_pendente_line.get('amount_residual')}"
                )

                # Executar reconciliação: linha PENDENTES <-> linha EXTRATO
                logger.info(
                    f"  Reconciliando MULTI-COMPANY: "
                    f"payment_line={payment_pendente_line_id} (PENDENTES) <-> "
                    f"extrato_line={item.credit_line_id} (TRANSITÓRIA)"
                )
                self._executar_reconcile(payment_pendente_line_id, item.credit_line_id)

                # Buscar partial_reconcile criado na linha do payment
                item.partial_reconcile_id = self._buscar_partial_reconcile_linha(payment_pendente_line_id)

            else:
                # Payment existe mas não tem linha PENDENTES disponível
                # Pode significar que já foi conciliado com outro extrato
                logger.warning(
                    f"  Payment existe mas sem linha PENDENTES disponível. "
                    f"Pode já estar conciliado com outro extrato."
                )
                raise ValueError(
                    f"Título NF {titulo.titulo_nf} P{titulo.parcela} já tem payment mas "
                    f"não há linha disponível na conta PENDENTES para conciliar. "
                    f"Verifique se já foi conciliado anteriormente."
                )

        else:
            # =========================================================================
            # TÍTULO SEM PAYMENT: Criar payment + conciliar com extrato
            # =========================================================================
            logger.info(f"  Título NÃO tem payment vinculado")

            # Verificar se há saldo para baixar
            saldo_titulo = titulo_odoo.get('amount_residual', 0)
            if saldo_titulo <= 0:
                raise ValueError(
                    f"Título NF {titulo.titulo_nf} P{titulo.parcela} já está quitado "
                    f"(saldo: R$ {saldo_titulo:.2f}). Reconciliado: {titulo_odoo.get('reconciled', False)}"
                )

            # Verificar se extrato e título são da mesma empresa
            company_id_extrato = self._buscar_company_linha_credito(item.credit_line_id)

            if titulo_company_id == company_id_extrato:
                # =====================================================================
                # MESMA EMPRESA: Reconciliar diretamente
                # =====================================================================
                logger.info(f"  Mesma empresa - reconciliação direta")
                logger.info(
                    f"  Reconciliando DIRETO: "
                    f"credit_line={item.credit_line_id} <-> titulo={titulo_odoo_id}"
                )
                self._executar_reconcile(item.credit_line_id, titulo_odoo_id)
                item.partial_reconcile_id = self._buscar_partial_reconcile(titulo_odoo_id)

            else:
                # =====================================================================
                # EMPRESAS DIFERENTES: Criar payment + conciliar
                # =====================================================================
                logger.info(
                    f"  Empresas diferentes - criando payment + conciliação"
                )
                logger.info(
                    f"  Título: {titulo_company_name} (ID {titulo_company_id}), "
                    f"Extrato: empresa ID {company_id_extrato}"
                )

                # Extrair dados para criar payment
                partner_id = titulo_odoo.get('partner_id')
                partner_id_num = partner_id[0] if isinstance(partner_id, (list, tuple)) else partner_id

                move = titulo_odoo.get('move_id')
                move_name = move[1] if isinstance(move, (list, tuple)) else str(move)

                # Usar o valor do extrato (pode ser diferente do título em caso de parcial)
                valor_payment = min(item.valor, saldo_titulo)

                # Criar payment na empresa do TÍTULO (reutiliza BaixaTitulosService)
                logger.info(f"  Criando payment: R$ {valor_payment:.2f}")
                payment_id, payment_name = self.baixa_service._criar_pagamento(
                    partner_id=partner_id_num,
                    valor=valor_payment,
                    journal_id=883,  # GRAFENO
                    ref=move_name,
                    data=item.data or datetime.now().date(),
                    company_id=titulo_company_id
                )
                logger.info(f"  Payment criado: {payment_name} (ID {payment_id})")

                # Postar payment (reutiliza BaixaTitulosService)
                self.baixa_service._postar_pagamento(payment_id)
                logger.info(f"  Payment postado")

                # Buscar linha de crédito do payment e reconciliar com título
                credit_line_id = self.baixa_service._buscar_linha_credito(payment_id)
                if credit_line_id:
                    self._executar_reconcile(credit_line_id, titulo_odoo_id)
                    logger.info(f"  Título reconciliado com payment")

                # Buscar linha PENDENTES do payment e reconciliar com extrato
                payment_pendente_line = self._buscar_linha_pendentes_payment(payment_id)
                if payment_pendente_line:
                    payment_pendente_line_id = payment_pendente_line['id']
                    logger.info(
                        f"  Reconciliando extrato: "
                        f"payment_line={payment_pendente_line_id} <-> extrato_line={item.credit_line_id}"
                    )
                    self._executar_reconcile(payment_pendente_line_id, item.credit_line_id)
                    item.partial_reconcile_id = self._buscar_partial_reconcile_linha(payment_pendente_line_id)
                else:
                    logger.warning(f"  Linha PENDENTES não encontrada - extrato não conciliado")

                # Salvar ID do payment criado
                item.payment_id = payment_id

        # =========================================================================
        # PÓS-PROCESSAMENTO
        # =========================================================================

        # Capturar snapshot DEPOIS
        snapshot_depois = self._capturar_snapshot(titulo_odoo_id)
        item.set_snapshot_depois(snapshot_depois)

        # Buscar dados atualizados
        titulo_atualizado = self._buscar_titulo_por_id(titulo_odoo_id)
        item.titulo_saldo_antes = titulo_odoo.get('amount_residual', 0)
        item.titulo_saldo_depois = titulo_atualizado.get('amount_residual', 0) if titulo_atualizado else None

        # Verificar full_reconcile (se titulo foi quitado)
        if titulo_atualizado and titulo_atualizado.get('full_reconcile_id'):
            full_rec = titulo_atualizado.get('full_reconcile_id')
            if isinstance(full_rec, (list, tuple)) and len(full_rec) > 0:
                item.full_reconcile_id = full_rec[0]

        # Atualizar status
        item.status = 'CONCILIADO'
        item.processado_em = datetime.utcnow()
        item.mensagem = f"Conciliado: Saldo {item.titulo_saldo_antes} -> {item.titulo_saldo_depois}"

        logger.info(f"  ✅ OK - Saldo: {item.titulo_saldo_antes} -> {item.titulo_saldo_depois}")

        return {
            'item_id': item.id,
            'titulo_id': titulo_odoo_id,
            'saldo_antes': item.titulo_saldo_antes,
            'saldo_depois': item.titulo_saldo_depois,
            'partial_reconcile_id': item.partial_reconcile_id
        }

    def _buscar_linha_credito(self, move_id: int) -> Optional[int]:
        """
        Busca a linha de crédito (contrapartida) do extrato.
        """
        if not move_id:
            return None

        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['credit', '>', 0]
            ],
            fields=['id'],
            limit=1
        )
        return linhas[0]['id'] if linhas else None

    def _buscar_company_linha_credito(self, credit_line_id: int) -> Optional[int]:
        """
        Busca a empresa (company_id) da linha de crédito do extrato.

        CRÍTICO: Esta informação é usada para garantir que o título a reconciliar
        seja da mesma empresa, evitando o erro "Expected singleton: res.company(X, Y)".
        """
        if not credit_line_id:
            return None

        linhas = self.connection.search_read(
            'account.move.line',
            [['id', '=', credit_line_id]],
            fields=['company_id'],
            limit=1
        )

        if linhas and linhas[0].get('company_id'):
            company = linhas[0]['company_id']
            # company_id vem como [id, name] ou int
            if isinstance(company, (list, tuple)):
                return company[0]
            return company

        return None

    def _buscar_titulo_odoo(
        self, nf: str, parcela: str, empresa: int, company_id_extrato: int = None
    ) -> Optional[Dict]:
        """
        Busca o título no Odoo pelo número da NF e parcela.

        Args:
            nf: Número da NF-e
            parcela: Número da parcela
            empresa: Código da empresa local (1=FB, 2=SC, 3=CD)
            company_id_extrato: ID da empresa no Odoo (obrigatório para reconciliação).
                                Se fornecido, FILTRA títulos pela mesma empresa.

        Estratégia:
        1. Busca por NF + parcela + empresa (se company_id_extrato fornecido)
        2. Se encontrar múltiplos, prefere empresa FB
        3. Fallback: busca pelo move_id.name

        NOTA: NÃO filtramos por reconciled nem amount_residual.
        O Odoo cuida automaticamente se pode ou não reconciliar.
        """
        # Limpar parcela - remover "P" se existir e converter para int
        parcela_limpa = str(parcela).upper().replace('P', '').strip() if parcela else None
        try:
            parcela_int = int(parcela_limpa) if parcela_limpa else None
        except (ValueError, TypeError):
            parcela_int = None
            logger.warning(f"Parcela inválida: '{parcela}' -> não será filtrada")

        logger.info(
            f"  Buscando título: NF={nf}, parcela={parcela_int}, "
            f"empresa_local={empresa}, company_id_extrato={company_id_extrato}"
        )

        # 1. Busca principal: NF + parcela + empresa (se fornecida)
        domain = [
            ['x_studio_nf_e', '=', str(nf)],
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted']
        ]

        if parcela_int:
            domain.append(['l10n_br_cobranca_parcela', '=', parcela_int])

        # CRÍTICO: Filtrar pela mesma empresa do extrato para evitar erro de multi-company
        if company_id_extrato:
            domain.append(['company_id', '=', company_id_extrato])

        titulos = self.connection.search_read(
            'account.move.line',
            domain,
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=5
        )

        if titulos:
            logger.info(f"  Encontrado(s) {len(titulos)} título(s)")
            return self._selecionar_titulo_empresa(titulos)

        # 2. Fallback: buscar pelo nome do move
        domain_fallback = [
            ['move_id.name', 'ilike', str(nf)],
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted']
        ]

        if parcela_int:
            domain_fallback.append(['l10n_br_cobranca_parcela', '=', parcela_int])

        # CRÍTICO: Também filtrar pelo company_id no fallback
        if company_id_extrato:
            domain_fallback.append(['company_id', '=', company_id_extrato])

        titulos = self.connection.search_read(
            'account.move.line',
            domain_fallback,
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=5
        )

        if titulos:
            logger.info(f"  Encontrado(s) {len(titulos)} título(s) via move_id.name")
            return self._selecionar_titulo_empresa(titulos)

        # 3. Log diagnóstico: buscar só por NF para mostrar parcelas disponíveis (sem filtro empresa)
        if parcela_int:
            domain_diag = [
                ['x_studio_nf_e', '=', str(nf)],
                ['account_type', '=', 'asset_receivable'],
                ['parent_state', '=', 'posted']
            ]
            titulos_diag = self.connection.search_read(
                'account.move.line',
                domain_diag,
                fields=['id', 'l10n_br_cobranca_parcela', 'amount_residual', 'reconciled', 'company_id'],
                limit=10
            )

            if titulos_diag:
                logger.warning(f"  NF {nf} encontrada, mas parcela {parcela_int} não existe (ou empresa diferente)")
                for t in titulos_diag:
                    company = t.get('company_id')
                    company_name = company[1] if isinstance(company, (list, tuple)) else str(company)
                    logger.warning(
                        f"    -> Parcela {t.get('l10n_br_cobranca_parcela')}: "
                        f"Saldo={t.get('amount_residual')}, "
                        f"Reconciliado={t.get('reconciled')}, "
                        f"Empresa={company_name}"
                    )
            else:
                logger.warning(f"  NF {nf} NÃO encontrada no Odoo")

        return None

    def _selecionar_titulo_empresa(self, titulos: list) -> Optional[Dict]:
        """
        Seleciona o título, priorizando empresa FB se houver múltiplos.
        Igual à lógica da baixa manual.
        """
        if not titulos:
            return None

        if len(titulos) == 1:
            return titulos[0]

        # Se encontrou mais de um, preferir empresa FB
        for t in titulos:
            company = t.get('company_id')
            if company and isinstance(company, (list, tuple)):
                if 'FB' in company[1]:
                    logger.info(f"  Múltiplos títulos encontrados, selecionando FB")
                    return t

        # Fallback: retorna o primeiro
        return titulos[0]

    def _buscar_titulo_por_id(self, titulo_id: int) -> Optional[Dict]:
        """Busca título por ID."""
        titulos = self.connection.search_read(
            'account.move.line',
            [['id', '=', titulo_id]],
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=1
        )
        return titulos[0] if titulos else None

    def _capturar_snapshot(self, titulo_id: int) -> Dict:
        """Captura snapshot do título."""
        titulo = self._buscar_titulo_por_id(titulo_id)
        return {'titulo': titulo} if titulo else {}

    def _executar_reconcile(self, credit_line_id: int, titulo_id: int) -> None:
        """
        Executa a reconciliação no Odoo.

        Nota: reconcile() retorna None, causando erro de serialização XML-RPC.
        Isso é esperado e deve ser ignorado.
        """
        try:
            self.connection.execute_kw(
                'account.move.line',
                'reconcile',
                [[credit_line_id, titulo_id]]
            )
        except Exception as e:
            # Ignorar erro de serialização - operação foi executada
            if "cannot marshal None" not in str(e):
                raise

    def _buscar_partial_reconcile(self, titulo_id: int) -> Optional[int]:
        """Busca o último partial_reconcile criado para o título."""
        titulo = self._buscar_titulo_por_id(titulo_id)
        if not titulo:
            return None

        matched_ids = titulo.get('matched_credit_ids', [])
        if matched_ids:
            return matched_ids[-1]

        return None

    # =========================================================================
    # MÉTODOS MULTI-COMPANY (adicionados em 2025-12-11)
    # =========================================================================

    def _buscar_titulo_odoo_multicompany(self, nf: str, parcela: str) -> Optional[Dict]:
        """
        Busca o título no Odoo pelo número da NF e parcela, SEM filtro de empresa.

        Esta versão é usada para encontrar títulos que podem estar em empresas
        diferentes do extrato. A lógica multi-company cuida da reconciliação.

        Args:
            nf: Número da NF-e
            parcela: Número da parcela

        Returns:
            Dict com dados do título ou None
        """
        # Limpar parcela
        parcela_limpa = str(parcela).upper().replace('P', '').strip() if parcela else None
        try:
            parcela_int = int(parcela_limpa) if parcela_limpa else None
        except (ValueError, TypeError):
            parcela_int = None
            logger.warning(f"Parcela inválida: '{parcela}' -> não será filtrada")

        logger.info(f"  Buscando título multi-company: NF={nf}, parcela={parcela_int}")

        # 1. Busca principal: NF + parcela (sem filtro de empresa)
        domain = [
            ['x_studio_nf_e', '=', str(nf)],
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted']
        ]

        if parcela_int:
            domain.append(['l10n_br_cobranca_parcela', '=', parcela_int])

        titulos = self.connection.search_read(
            'account.move.line',
            domain,
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=5
        )

        if titulos:
            logger.info(f"  Encontrado(s) {len(titulos)} título(s)")
            # Se múltiplos, preferir o que tem payment vinculado (já baixado)
            return self._selecionar_titulo_com_payment(titulos)

        # 2. Fallback: buscar pelo nome do move
        domain_fallback = [
            ['move_id.name', 'ilike', str(nf)],
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted']
        ]

        if parcela_int:
            domain_fallback.append(['l10n_br_cobranca_parcela', '=', parcela_int])

        titulos = self.connection.search_read(
            'account.move.line',
            domain_fallback,
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=5
        )

        if titulos:
            logger.info(f"  Encontrado(s) {len(titulos)} título(s) via move_id.name")
            return self._selecionar_titulo_com_payment(titulos)

        # 3. Log diagnóstico
        if parcela_int:
            domain_diag = [
                ['x_studio_nf_e', '=', str(nf)],
                ['account_type', '=', 'asset_receivable'],
                ['parent_state', '=', 'posted']
            ]
            titulos_diag = self.connection.search_read(
                'account.move.line',
                domain_diag,
                fields=['id', 'l10n_br_cobranca_parcela', 'amount_residual',
                        'reconciled', 'company_id', 'matched_credit_ids'],
                limit=10
            )

            if titulos_diag:
                logger.warning(f"  NF {nf} encontrada, mas parcela {parcela_int} não existe")
                for t in titulos_diag:
                    company = t.get('company_id')
                    company_name = company[1] if isinstance(company, (list, tuple)) else str(company)
                    logger.warning(
                        f"    -> Parcela {t.get('l10n_br_cobranca_parcela')}: "
                        f"Saldo={t.get('amount_residual')}, "
                        f"Empresa={company_name}, "
                        f"Payment={bool(t.get('matched_credit_ids'))}"
                    )
            else:
                logger.warning(f"  NF {nf} NÃO encontrada no Odoo")

        return None

    def _selecionar_titulo_com_payment(self, titulos: list) -> Optional[Dict]:
        """
        Seleciona o título, priorizando:
        1. Título que tem payment vinculado (matched_credit_ids) - já foi baixado
        2. Se nenhum tem payment, preferir empresa FB (igual BaixaTitulosService)

        IMPORTANTE: Usa mesma lógica do BaixaTitulosService para consistência,
        mas prioriza títulos com payment pois na conciliação do extrato
        precisamos encontrar a linha PENDENTES do payment.
        """
        if not titulos:
            return None

        if len(titulos) == 1:
            return titulos[0]

        # 1. Preferir título com payment vinculado (já foi baixado)
        # Isso é importante para conciliação do extrato pois precisamos
        # da linha PENDENTES do payment
        for t in titulos:
            if t.get('matched_credit_ids'):
                logger.info(f"  Múltiplos títulos, selecionando o que tem payment vinculado")
                return t

        # 2. Se nenhum tem payment, preferir empresa FB (igual BaixaTitulosService)
        for t in titulos:
            company = t.get('company_id')
            if company and isinstance(company, (list, tuple)):
                if 'FB' in company[1]:
                    logger.info(f"  Múltiplos títulos sem payment, selecionando FB")
                    return t

        # 3. Fallback: retorna o primeiro
        return titulos[0]

    def _buscar_linha_payment_pendentes(self, matched_credit_ids: List[int]) -> Optional[Dict]:
        """
        Busca a linha do payment na conta PAGAMENTOS PENDENTES (26868).

        Quando um título é baixado via CNAB, o payment cria duas linhas:
        - Uma linha de CRÉDITO na conta CLIENTES (reconcilia com título)
        - Uma linha de DÉBITO na conta PENDENTES (aguarda reconciliação com extrato)

        Esta função busca a linha de DÉBITO na conta PENDENTES que ainda não
        foi reconciliada.

        Args:
            matched_credit_ids: Lista de IDs de partial_reconcile do título

        Returns:
            Dict com dados da linha ou None
        """
        if not matched_credit_ids:
            return None

        logger.info(f"  Buscando linha PENDENTES nos partial_reconciles: {matched_credit_ids}")

        # Buscar os partial_reconciles
        partials = self.connection.search_read(
            'account.partial.reconcile',
            [['id', 'in', matched_credit_ids]],
            fields=['id', 'credit_move_id', 'debit_move_id', 'amount']
        )

        if not partials:
            logger.warning(f"  Nenhum partial_reconcile encontrado")
            return None

        # Para cada partial, buscar a linha de crédito (do payment)
        for p in partials:
            credit_move = p.get('credit_move_id')
            if not credit_move:
                continue

            credit_line_id = credit_move[0] if isinstance(credit_move, (list, tuple)) else credit_move

            # Buscar a linha de crédito
            credit_line = self.connection.search_read(
                'account.move.line',
                [['id', '=', credit_line_id]],
                fields=['id', 'payment_id', 'move_id', 'account_id']
            )

            if not credit_line or not credit_line[0].get('payment_id'):
                continue

            # Tem payment vinculado - buscar o move do payment
            payment_id = credit_line[0]['payment_id']
            payment_id_num = payment_id[0] if isinstance(payment_id, (list, tuple)) else payment_id

            payment = self.connection.search_read(
                'account.payment',
                [['id', '=', payment_id_num]],
                fields=['id', 'name', 'move_id']
            )

            if not payment or not payment[0].get('move_id'):
                continue

            # Buscar move do payment
            payment_move_id = payment[0]['move_id']
            payment_move_id_num = payment_move_id[0] if isinstance(payment_move_id, (list, tuple)) else payment_move_id

            # Buscar linha de DÉBITO na conta PENDENTES (26868) que NÃO está reconciliada
            linhas_pendentes = self.connection.search_read(
                'account.move.line',
                [
                    ['move_id', '=', payment_move_id_num],
                    ['account_id', '=', CONTA_PAGAMENTOS_PENDENTES],
                    ['debit', '>', 0],
                    ['reconciled', '=', False]
                ],
                fields=['id', 'name', 'debit', 'amount_residual', 'account_id', 'company_id']
            )

            if linhas_pendentes:
                logger.info(
                    f"  Encontrada linha PENDENTES: payment={payment[0]['name']}, "
                    f"linha_id={linhas_pendentes[0]['id']}"
                )
                return linhas_pendentes[0]

        logger.warning(f"  Nenhuma linha PENDENTES disponível encontrada")
        return None

    def _buscar_partial_reconcile_linha(self, linha_id: int) -> Optional[int]:
        """
        Busca o último partial_reconcile criado para uma linha específica.

        Args:
            linha_id: ID da account.move.line

        Returns:
            ID do partial_reconcile ou None
        """
        linha = self.connection.search_read(
            'account.move.line',
            [['id', '=', linha_id]],
            fields=['matched_credit_ids', 'matched_debit_ids']
        )

        if not linha:
            return None

        # Verificar matched_credit_ids (se a linha é débito)
        matched_ids = linha[0].get('matched_credit_ids', [])
        if matched_ids:
            return matched_ids[-1]

        # Verificar matched_debit_ids (se a linha é crédito)
        matched_ids = linha[0].get('matched_debit_ids', [])
        if matched_ids:
            return matched_ids[-1]

        return None

    def _buscar_linha_pendentes_payment(self, payment_id: int) -> Optional[Dict]:
        """
        Busca a linha DÉBITO na conta PAGAMENTOS PENDENTES do payment.
        Esta é a linha que será reconciliada com o EXTRATO.
        """
        # Buscar o payment para pegar o move_id
        payment = self.connection.search_read(
            'account.payment',
            [['id', '=', payment_id]],
            fields=['move_id'],
            limit=1
        )

        if not payment or not payment[0].get('move_id'):
            return None

        move_id = payment[0]['move_id']
        move_id_num = move_id[0] if isinstance(move_id, (list, tuple)) else move_id

        # Buscar linha DÉBITO na conta PENDENTES
        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id_num],
                ['account_id', '=', CONTA_PAGAMENTOS_PENDENTES],
                ['debit', '>', 0],
                ['reconciled', '=', False]
            ],
            fields=['id', 'name', 'debit', 'amount_residual', 'account_id', 'company_id']
        )

        return linhas[0] if linhas else None
