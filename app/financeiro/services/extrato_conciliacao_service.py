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
from app.financeiro.models import (
    ExtratoLote, ExtratoItem, ContasAReceber, ContasAPagar, ExtratoItemTitulo
)
from app.financeiro.services.baixa_titulos_service import (
    BaixaTitulosService,
    JOURNAL_GRAFENO_ID,
)

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
        lote = db.session.get(ExtratoLote,lote_id) if lote_id else None
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

        FLUXO:
        1. Verifica se item tem múltiplos títulos vinculados (M:N via ExtratoItemTitulo)
        2. Se sim: chama _conciliar_multiplos_titulos()
        3. Se não: fluxo original (1:1 via FK legacy)

        FLUXO MULTI-COMPANY (1:1):
        1. Se título tem payment vinculado (CNAB): reconcilia linha PENDENTES com linha EXTRATO
        2. Se título não tem payment: tenta reconciliar diretamente (mesma empresa)

        Args:
            item: ExtratoItem a conciliar

        Returns:
            Dict com resultado
        """
        # =========================================================================
        # VERIFICAR SE TEM MÚLTIPLOS TÍTULOS VINCULADOS (M:N)
        # =========================================================================
        if item.tem_multiplos_titulos:
            logger.info(
                f"Conciliando item {item.id} com MÚLTIPLOS títulos "
                f"({item.titulos_vinculados.count()} títulos)"
            )
            return self._conciliar_multiplos_titulos(item)

        # =========================================================================
        # FLUXO ORIGINAL (1:1)
        # =========================================================================
        logger.info(f"Conciliando item {item.id}: NF {item.titulo_nf} P{item.titulo_parcela}")

        if not item.titulo_receber_id:
            raise ValueError("Item não possui título vinculado")

        if not item.credit_line_id:
            # Buscar linha de crédito se não tiver
            item.credit_line_id = self._buscar_linha_credito(item.move_id)
            if not item.credit_line_id:
                raise ValueError(f"Linha de crédito não encontrada para move_id {item.move_id}")

        # Buscar título local (usando titulo_receber_id para clientes)
        titulo = db.session.get(ContasAReceber,item.titulo_receber_id) if item.titulo_receber_id else None
        if not titulo:
            raise ValueError(f"Título {item.titulo_receber_id} não encontrado no sistema")

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

                # Trocar conta do extrato ANTES de reconciliar
                self._trocar_conta_extrato(item.move_id)

                # Executar reconciliação: linha PENDENTES <-> linha EXTRATO
                logger.info(
                    f"  Reconciliando MULTI-COMPANY: "
                    f"payment_line={payment_pendente_line_id} (PENDENTES) <-> "
                    f"extrato_line={item.credit_line_id}"
                )
                self._executar_reconcile(payment_pendente_line_id, item.credit_line_id)

                # Atualizar partner e rótulo do extrato
                p_id, p_name = self._extrair_partner_dados(titulo_odoo)
                self._atualizar_campos_extrato(item, p_id, p_name)

                # Buscar partial_reconcile criado na linha do payment
                item.partial_reconcile_id = self._buscar_partial_reconcile_linha(payment_pendente_line_id)

            else:
                # Payment existe mas não tem linha PENDENTES disponível
                # Verificar se a linha do EXTRATO já está conciliada no Odoo
                logger.warning(
                    f"  Payment existe mas sem linha PENDENTES disponível. "
                    f"Verificando se extrato já está conciliado no Odoo..."
                )

                # Verificar se linha de crédito do extrato já está reconciliada
                linha_extrato = self._verificar_linha_extrato_reconciliada(item.credit_line_id)
                if linha_extrato and linha_extrato.get('reconciled'):
                    # JÁ ESTÁ CONCILIADO NO ODOO - Sincronizar para o sistema
                    logger.info(
                        f"  ✓ Extrato JÁ CONCILIADO no Odoo! Sincronizando informação..."
                    )
                    return self._sincronizar_conciliacao_existente(item, titulo_odoo, linha_extrato)

                # Verificar se o título já está completamente quitado
                saldo_titulo = titulo_odoo.get('amount_residual', 0)
                if saldo_titulo <= 0 or l10n_br_paga:
                    # Título já quitado por outro meio - sincronizar localmente
                    logger.info(
                        f"  ✓ Título já quitado (saldo={saldo_titulo}, paga={l10n_br_paga}). "
                        f"Marcando item como conciliado localmente..."
                    )
                    return self._marcar_conciliado_local(item, titulo_odoo, matched_credit_ids)

                # Realmente não há como conciliar
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
                # Verificar se a linha do EXTRATO já está conciliada no Odoo
                logger.info(f"  Título já quitado, verificando se extrato já conciliado no Odoo...")
                linha_extrato = self._verificar_linha_extrato_reconciliada(item.credit_line_id)
                if linha_extrato and linha_extrato.get('reconciled'):
                    # JÁ ESTÁ CONCILIADO NO ODOO - Sincronizar para o sistema
                    logger.info(
                        f"  ✓ Extrato JÁ CONCILIADO no Odoo! Sincronizando informação..."
                    )
                    return self._sincronizar_conciliacao_existente(item, titulo_odoo, linha_extrato)

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

                # Trocar conta do extrato ANTES de reconciliar
                self._trocar_conta_extrato(item.move_id)

                logger.info(
                    f"  Reconciliando DIRETO: "
                    f"credit_line={item.credit_line_id} <-> titulo={titulo_odoo_id}"
                )
                self._executar_reconcile(item.credit_line_id, titulo_odoo_id)

                # Atualizar partner e rótulo do extrato
                p_id, p_name = self._extrair_partner_dados(titulo_odoo)
                self._atualizar_campos_extrato(item, p_id, p_name)

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

                # Calcular juros: diferença entre valor do extrato e saldo do título
                valor_extrato = float(item.valor)
                valor_principal = min(valor_extrato, saldo_titulo)
                valor_juros = valor_extrato - valor_principal if valor_extrato > saldo_titulo else 0

                # Obter journal_id do lote do extrato (ou usar GRAFENO como padrão)
                # FLUXO TESTADO (22/01/2026): Retorno CNAB Grafeno (banco 274)
                journal_id = item.lote.journal_id if item.lote and item.lote.journal_id else JOURNAL_GRAFENO_ID

                # Criar payment COM ou SEM juros dependendo da diferença
                if valor_juros > 0.01:  # Tolerância de 1 centavo
                    # =========================================================
                    # CASO COM JUROS: Usar wizard com Write-Off
                    # O método _criar_pagamento_com_writeoff_juros() já:
                    # - Cria o payment com valor total (principal + juros)
                    # - Posta automaticamente
                    # - Reconcilia com o título automaticamente
                    # - Contabiliza juros na conta de receita financeira
                    # =========================================================
                    logger.info(
                        f"  Criando payment COM juros: "
                        f"Principal R$ {valor_principal:.2f} + Juros R$ {valor_juros:.2f}"
                    )
                    payment_id, payment_name = self.baixa_service._criar_pagamento_com_writeoff_juros(
                        titulo_id=titulo_odoo_id,  # ID da linha do título (account.move.line)
                        partner_id=partner_id_num,
                        valor_pagamento=valor_principal,  # Valor que abate do título
                        valor_juros=valor_juros,          # Valor que vai para receita financeira
                        journal_id=journal_id,
                        ref=move_name,
                        data=item.data_transacao or datetime.now().date(),
                        company_id=titulo_company_id
                    )
                    logger.info(f"  Payment com Write-Off criado: {payment_name} (ID {payment_id})")
                    # O wizard já postou e reconciliou com título - não chamar novamente!

                else:
                    # =========================================================
                    # CASO SEM JUROS: Fluxo original
                    # =========================================================
                    logger.info(f"  Criando payment: R$ {valor_principal:.2f}")
                    payment_id, payment_name = self.baixa_service._criar_pagamento(
                        partner_id=partner_id_num,
                        valor=valor_principal,
                        journal_id=journal_id,
                        ref=move_name,
                        data=item.data_transacao or datetime.now().date(),
                        company_id=titulo_company_id
                    )
                    logger.info(f"  Payment criado: {payment_name} (ID {payment_id})")

                    # Postar payment (só para caso sem juros)
                    self.baixa_service._postar_pagamento(payment_id)
                    logger.info(f"  Payment postado")

                    # Buscar linha de crédito do payment e reconciliar com título (só para caso sem juros)
                    credit_line_id = self.baixa_service._buscar_linha_credito(payment_id)
                    if credit_line_id:
                        self._executar_reconcile(credit_line_id, titulo_odoo_id)
                        logger.info(f"  Título reconciliado com payment")

                # Buscar linha PENDENTES do payment e reconciliar com extrato (SEMPRE - com ou sem juros)
                payment_pendente_line = self._buscar_linha_pendentes_payment(payment_id)
                if payment_pendente_line:
                    payment_pendente_line_id = payment_pendente_line['id']

                    # Trocar conta do extrato ANTES de reconciliar
                    self._trocar_conta_extrato(item.move_id)

                    logger.info(
                        f"  Reconciliando extrato: "
                        f"payment_line={payment_pendente_line_id} <-> extrato_line={item.credit_line_id}"
                    )
                    self._executar_reconcile(payment_pendente_line_id, item.credit_line_id)

                    # Atualizar partner e rótulo do extrato
                    p_id, p_name = self._extrair_partner_dados(titulo_odoo)
                    self._atualizar_campos_extrato(item, p_id, p_name)

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
            'success': True,  # ADICIONADO: Sinaliza sucesso para _executar_baixa_automatica()
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

    # =========================================================================
    # ATUALIZAÇÃO DE CAMPOS DO EXTRATO (PÓS-RECONCILIAÇÃO)
    # =========================================================================

    def _trocar_conta_extrato(self, move_id: int) -> bool:
        """
        Troca account_id da move line do extrato: TRANSITÓRIA → PENDENTES.

        Deve ser chamado ANTES da reconciliação, pois após reconciliar
        pode não ser possível alterar a move line.

        Args:
            move_id: ID do account.move do extrato

        Returns:
            True se trocou, False se não encontrou ou falhou
        """
        if not move_id:
            return False
        try:
            linhas = self.connection.search_read(
                'account.move.line',
                [
                    ['move_id', '=', move_id],
                    ['account_id', '=', CONTA_TRANSITORIA],
                    ['debit', '>', 0]
                ],
                fields=['id'],
                limit=1
            )
            if not linhas:
                return False
            self.connection.execute_kw(
                'account.move.line',
                'write',
                [[linhas[0]['id']], {'account_id': CONTA_PAGAMENTOS_PENDENTES}]
            )
            logger.info(
                f"  Conta atualizada: move_line {linhas[0]['id']}, "
                f"{CONTA_TRANSITORIA} → {CONTA_PAGAMENTOS_PENDENTES}"
            )
            return True
        except Exception as e:
            logger.warning(f"  Falha ao trocar conta do extrato move {move_id}: {e}")
            return False

    def _atualizar_campos_extrato(
        self, item: ExtratoItem, partner_id: int, partner_name: str
    ) -> None:
        """
        Atualiza partner_id e rótulo do extrato no Odoo (PÓS reconciliação).

        Corrige campos que o Odoo não preenche automaticamente para boletos:
        1. partner_id da statement line
        2. name/rótulo das move lines e payment_ref da statement line

        Args:
            item: ExtratoItem com statement_line_id e move_id
            partner_id: ID do res.partner (fornecedor/cliente)
            partner_name: Nome do fornecedor/cliente
        """
        if not item.statement_line_id or not item.move_id:
            return

        # 1. Atualizar partner_id da statement line
        try:
            self.connection.execute_kw(
                'account.bank.statement.line',
                'write',
                [[item.statement_line_id], {'partner_id': partner_id}]
            )
            logger.info(
                f"  Partner atualizado: statement_line "
                f"{item.statement_line_id} → partner_id={partner_id}"
            )
        except Exception as e:
            logger.warning(f"  Falha ao atualizar partner: {e}")

        # 2. Atualizar rótulo
        try:
            from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService
            rotulo = BaixaPagamentosService.formatar_rotulo_pagamento(
                valor=abs(float(item.valor)),
                nome_fornecedor=partner_name or '',
                data_pagamento=item.data_transacao,
            )

            # payment_ref da statement line
            self.connection.execute_kw(
                'account.bank.statement.line',
                'write',
                [[item.statement_line_id], {'payment_ref': rotulo}]
            )

            # name das move lines do extrato
            linhas = self.connection.search_read(
                'account.move.line',
                [['move_id', '=', item.move_id]],
                fields=['id'],
            )
            if linhas:
                line_ids = [l['id'] for l in linhas]
                self.connection.execute_kw(
                    'account.move.line',
                    'write',
                    [line_ids, {'name': rotulo}]
                )
            logger.info(f"  Rótulo atualizado: {rotulo[:60]}...")
        except Exception as e:
            logger.warning(f"  Falha ao atualizar rótulo: {e}")

    def _extrair_partner_dados(self, titulo_odoo: Dict) -> tuple:
        """
        Extrai partner_id (int) e partner_name (str) do título Odoo.

        Returns:
            Tuple (partner_id, partner_name)
        """
        partner = titulo_odoo.get('partner_id')
        if isinstance(partner, (list, tuple)):
            return partner[0], partner[1]
        return partner, ''

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

    def _verificar_linha_extrato_reconciliada(self, credit_line_id: int) -> Optional[Dict]:
        """
        Verifica se a linha de crédito do extrato já está reconciliada no Odoo.

        Esta verificação é importante para casos onde a conciliação foi feita
        diretamente no Odoo e precisamos sincronizar essa informação.

        Args:
            credit_line_id: ID da linha de crédito do extrato (account.move.line)

        Returns:
            Dict com dados da linha (incluindo 'reconciled', 'full_reconcile_id', etc)
            ou None se não encontrar
        """
        if not credit_line_id:
            return None

        try:
            linhas = self.connection.search_read(
                'account.move.line',
                [['id', '=', credit_line_id]],
                fields=[
                    'id', 'name', 'credit', 'debit', 'balance',
                    'reconciled', 'full_reconcile_id', 'matching_number',
                    'matched_credit_ids', 'matched_debit_ids',
                    'amount_residual', 'partner_id', 'move_id'
                ],
                limit=1
            )
            return linhas[0] if linhas else None
        except Exception as e:
            logger.error(f"Erro ao verificar linha extrato {credit_line_id}: {e}")
            return None

    def _sincronizar_conciliacao_existente(
        self, item: ExtratoItem, titulo_odoo: Dict, linha_extrato: Dict
    ) -> Dict:
        """
        Sincroniza uma conciliação que já existe no Odoo para o sistema local.

        Quando a conciliação foi feita diretamente no Odoo, este método
        captura as informações e atualiza o ExtratoItem local.

        Args:
            item: ExtratoItem do sistema local
            titulo_odoo: Dict com dados do título no Odoo
            linha_extrato: Dict com dados da linha de extrato reconciliada

        Returns:
            Dict com resultado da sincronização
        """
        logger.info(f"  Sincronizando conciliação existente do Odoo...")

        titulo_odoo_id = titulo_odoo['id']

        # Capturar snapshots
        snapshot_antes = {'titulo': titulo_odoo, 'linha_extrato': linha_extrato}
        item.set_snapshot_antes(snapshot_antes)
        item.set_snapshot_depois(snapshot_antes)  # Mesmo valor pois não alteramos nada

        # Extrair IDs de reconciliação da linha do extrato
        full_reconcile = linha_extrato.get('full_reconcile_id')
        if full_reconcile:
            if isinstance(full_reconcile, (list, tuple)) and len(full_reconcile) > 0:
                item.full_reconcile_id = full_reconcile[0]
            elif isinstance(full_reconcile, int):
                item.full_reconcile_id = full_reconcile

        # Buscar partial_reconcile
        matched_ids = linha_extrato.get('matched_debit_ids', []) or linha_extrato.get('matched_credit_ids', [])
        if matched_ids:
            item.partial_reconcile_id = matched_ids[-1] if isinstance(matched_ids, list) else matched_ids

        # Preencher saldos (já estava quitado, então saldo = 0)
        item.titulo_saldo_antes = titulo_odoo.get('amount_residual', 0)
        item.titulo_saldo_depois = titulo_odoo.get('amount_residual', 0)

        # Atualizar status
        item.status = 'CONCILIADO'
        item.processado_em = datetime.utcnow()
        item.mensagem = "Sincronizado do Odoo - conciliação já existente"

        logger.info(
            f"  ✅ Sincronizado: full_reconcile_id={item.full_reconcile_id}, "
            f"partial_reconcile_id={item.partial_reconcile_id}"
        )

        return {
            'success': True,  # ADICIONADO: Sinaliza sucesso para _executar_baixa_automatica()
            'item_id': item.id,
            'titulo_id': titulo_odoo_id,
            'saldo_antes': item.titulo_saldo_antes,
            'saldo_depois': item.titulo_saldo_depois,
            'partial_reconcile_id': item.partial_reconcile_id,
            'sincronizado_do_odoo': True,
            'mensagem': 'Conciliação já existia no Odoo - sincronizado para o sistema'
        }

    def _marcar_conciliado_local(
        self, item: ExtratoItem, titulo_odoo: Dict, matched_credit_ids: list
    ) -> Dict:
        """
        Reconcilia o extrato com o payment existente quando o título já está quitado.

        Este cenário acontece quando:
        - O pagamento foi registrado no Odoo por outro meio (ex: baixa manual)
        - A linha do extrato não foi usada na conciliação original
        - Precisamos fechar o ciclo: extrato ↔ payment

        Fluxo:
        1. Buscar linha PENDENTES não reconciliada do payment existente
        2. Se encontrar: reconciliar com a linha do extrato (fecha o ciclo)
        3. Se não encontrar: apenas marcar localmente (fallback)

        Args:
            item: ExtratoItem do sistema local
            titulo_odoo: Dict com dados do título no Odoo
            matched_credit_ids: IDs dos partial_reconcile vinculados ao título

        Returns:
            Dict com resultado da operação
        """
        titulo_odoo_id = titulo_odoo['id']
        extrato_reconciliado = False
        mensagem_resultado = ""

        # Capturar snapshot ANTES
        snapshot_antes = {
            'titulo': titulo_odoo,
            'matched_credit_ids': matched_credit_ids,
            'extrato_credit_line_id': item.credit_line_id
        }
        item.set_snapshot_antes(snapshot_antes)

        # =========================================================================
        # TENTAR RECONCILIAR EXTRATO COM PAYMENT EXISTENTE
        # =========================================================================
        if matched_credit_ids and item.credit_line_id:
            logger.info(
                f"  Título já quitado - tentando reconciliar extrato com payment existente..."
            )

            # Buscar linha PENDENTES não reconciliada do payment
            payment_pendente_line = self._buscar_linha_payment_pendentes(matched_credit_ids)

            if payment_pendente_line:
                payment_pendente_line_id = payment_pendente_line['id']
                logger.info(
                    f"  Encontrada linha PENDENTES não reconciliada: {payment_pendente_line_id}"
                )
                logger.info(
                    f"  Reconciliando: payment_line={payment_pendente_line_id} <-> "
                    f"extrato_line={item.credit_line_id}"
                )

                try:
                    # Trocar conta do extrato ANTES de reconciliar
                    self._trocar_conta_extrato(item.move_id)

                    # Executar reconciliação no Odoo
                    self._executar_reconcile(payment_pendente_line_id, item.credit_line_id)

                    # Atualizar partner e rótulo do extrato
                    p_id, p_name = self._extrair_partner_dados(titulo_odoo)
                    self._atualizar_campos_extrato(item, p_id, p_name)

                    # Buscar partial_reconcile criado
                    item.partial_reconcile_id = self._buscar_partial_reconcile_linha(
                        payment_pendente_line_id
                    )

                    extrato_reconciliado = True
                    mensagem_resultado = (
                        f"Extrato reconciliado com payment existente "
                        f"(partial_reconcile={item.partial_reconcile_id})"
                    )
                    logger.info(f"  ✅ {mensagem_resultado}")

                except Exception as e:
                    logger.warning(
                        f"  ⚠️ Falha ao reconciliar extrato com payment: {e}. "
                        f"Marcando apenas localmente."
                    )
                    mensagem_resultado = f"Título quitado - falha ao reconciliar extrato: {e}"
            else:
                logger.info(
                    f"  Não há linha PENDENTES disponível para reconciliar com extrato. "
                    f"O payment original pode ter sido feito por outro método."
                )
                mensagem_resultado = (
                    "Título já quitado no Odoo - extrato não reconciliado "
                    "(payment original não usou conta PENDENTES)"
                )

                # Buscar partial_reconcile do payment para referência
                primeiro_partial_id = matched_credit_ids[0]
                item.partial_reconcile_id = self._buscar_partial_reconcile_linha(
                    primeiro_partial_id
                )
        else:
            mensagem_resultado = "Título já quitado no Odoo - marcado localmente"

        # Capturar snapshot DEPOIS
        snapshot_depois = {
            'titulo': titulo_odoo,
            'extrato_reconciliado': extrato_reconciliado,
            'partial_reconcile_id': item.partial_reconcile_id
        }
        item.set_snapshot_depois(snapshot_depois)

        # O título já está quitado, então saldo = 0
        item.titulo_saldo_antes = 0
        item.titulo_saldo_depois = 0

        # Atualizar status
        item.status = 'CONCILIADO'
        item.processado_em = datetime.utcnow()
        item.mensagem = mensagem_resultado

        logger.info(
            f"  ✅ Concluído: partial_reconcile_id={item.partial_reconcile_id}, "
            f"extrato_reconciliado={extrato_reconciliado}"
        )

        return {
            'success': True,  # ADICIONADO: Sinaliza sucesso para _executar_baixa_automatica()
            'item_id': item.id,
            'titulo_id': titulo_odoo_id,
            'saldo_antes': 0,
            'saldo_depois': 0,
            'partial_reconcile_id': item.partial_reconcile_id,
            'sincronizado_do_odoo': True,
            'extrato_reconciliado': extrato_reconciliado,
            'mensagem': mensagem_resultado
        }

    # =========================================================================
    # MÉTODOS PARA MÚLTIPLOS TÍTULOS (M:N)
    # =========================================================================

    def _conciliar_multiplos_titulos(self, item: ExtratoItem) -> Dict:
        """
        Concilia múltiplos títulos vinculados a um item de extrato.

        Este método processa cada ExtratoItemTitulo individualmente:
        1. Busca título no Odoo
        2. Cria payment com valor_alocado (se necessário)
        3. Reconcilia payment ↔ título
        4. Atualiza status do ExtratoItemTitulo

        O extrato será marcado como CONCILIADO apenas se TODOS os títulos
        forem processados com sucesso.

        Args:
            item: ExtratoItem com titulos_vinculados (M:N)

        Returns:
            Dict com resultado da conciliação
        """
        vinculos = item.titulos_vinculados.all()

        if not vinculos:
            raise ValueError("Item não possui títulos vinculados (M:N)")

        logger.info(f"=" * 60)
        logger.info(f"CONCILIANDO MÚLTIPLOS TÍTULOS - Item {item.id}")
        logger.info(f"Total de títulos: {len(vinculos)}")
        logger.info(f"Valor extrato: R$ {item.valor:.2f}")
        logger.info(f"=" * 60)

        resultados = []
        total_conciliados = 0
        total_erros = 0

        for i, vinculo in enumerate(vinculos, 1):
            logger.info(f"\n--- Processando título {i}/{len(vinculos)} ---")
            logger.info(
                f"  Vínculo ID: {vinculo.id}, "
                f"Título: {vinculo.titulo_nf} P{vinculo.titulo_parcela}, "
                f"Valor alocado: R$ {vinculo.valor_alocado:.2f}"
            )

            try:
                resultado = self._conciliar_titulo_individual(item, vinculo)
                vinculo.status = 'CONCILIADO'
                vinculo.processado_em = datetime.utcnow()
                vinculo.mensagem = resultado.get('mensagem', 'OK')
                resultados.append(resultado)
                total_conciliados += 1
                logger.info(f"  ✅ Título conciliado com sucesso")

            except Exception as e:
                logger.error(f"  ❌ Erro no título: {e}")
                vinculo.status = 'ERRO'
                vinculo.processado_em = datetime.utcnow()
                vinculo.mensagem = str(e)
                resultados.append({
                    'vinculo_id': vinculo.id,
                    'erro': str(e),
                    'titulo_id': vinculo.titulo_receber_id or vinculo.titulo_pagar_id
                })
                total_erros += 1

            db.session.flush()  # Salvar progresso de cada vínculo

        # Determinar status final do item
        todos_ok = all(v.status == 'CONCILIADO' for v in vinculos)

        if todos_ok:
            item.status = 'CONCILIADO'
            item.mensagem = f"Todos os {len(vinculos)} títulos conciliados"
        elif total_conciliados > 0:
            item.status = 'PARCIAL'
            item.mensagem = f"{total_conciliados}/{len(vinculos)} títulos conciliados"
        else:
            item.status = 'ERRO'
            item.mensagem = f"Nenhum título conciliado (0/{len(vinculos)})"

        item.processado_em = datetime.utcnow()

        logger.info(f"\n{'=' * 60}")
        logger.info(f"RESULTADO FINAL - Item {item.id}")
        logger.info(f"Status: {item.status}")
        logger.info(f"Conciliados: {total_conciliados}/{len(vinculos)}")
        logger.info(f"Erros: {total_erros}")
        logger.info(f"{'=' * 60}")

        return {
            'success': todos_ok,  # ADICIONADO: True só se TODOS os títulos foram conciliados
            'item_id': item.id,
            'status': item.status,
            'total_titulos': len(vinculos),
            'conciliados': total_conciliados,
            'erros': total_erros,
            'resultados': resultados
        }

    def _conciliar_titulo_individual(
        self, item: ExtratoItem, vinculo: ExtratoItemTitulo
    ) -> Dict:
        """
        Concilia um título individual do vínculo M:N.

        IMPORTANTE: O valor a reconciliar é o valor_alocado do vínculo,
        não o valor total do extrato.

        Args:
            item: ExtratoItem pai
            vinculo: ExtratoItemTitulo com os dados do título

        Returns:
            Dict com resultado
        """
        # Determinar tipo de título (receber ou pagar)
        if vinculo.titulo_receber_id:
            titulo_local = db.session.get(ContasAReceber,vinculo.titulo_receber_id) if vinculo.titulo_receber_id else None
            tipo = 'receber'
        elif vinculo.titulo_pagar_id:
            titulo_local = db.session.get(ContasAPagar,vinculo.titulo_pagar_id) if vinculo.titulo_pagar_id else None
            tipo = 'pagar'
        else:
            raise ValueError("Vínculo não possui título associado")

        if not titulo_local:
            raise ValueError(f"Título ID {vinculo.titulo_receber_id or vinculo.titulo_pagar_id} não encontrado")

        # Buscar título no Odoo
        titulo_odoo = self._buscar_titulo_odoo_multicompany(
            titulo_local.titulo_nf, titulo_local.parcela
        )
        if not titulo_odoo:
            raise ValueError(
                f"Título NF {titulo_local.titulo_nf} P{titulo_local.parcela} "
                f"não encontrado no Odoo"
            )

        titulo_odoo_id = titulo_odoo['id']
        titulo_company = titulo_odoo.get('company_id')
        titulo_company_id = titulo_company[0] if isinstance(titulo_company, (list, tuple)) else titulo_company

        logger.info(f"    Título Odoo: ID={titulo_odoo_id}, Empresa={titulo_company_id}")

        # Verificar se título já foi baixado
        matched_credit_ids = titulo_odoo.get('matched_credit_ids', [])
        l10n_br_paga = titulo_odoo.get('l10n_br_paga', False)
        saldo_titulo = titulo_odoo.get('amount_residual', 0)

        # Salvar saldo antes
        vinculo.titulo_saldo_antes = saldo_titulo

        # Valor a processar é o valor_alocado do vínculo
        valor_alocado = float(vinculo.valor_alocado)
        logger.info(f"    Valor alocado: R$ {valor_alocado:.2f}, Saldo título: R$ {saldo_titulo:.2f}")

        # =========================================================================
        # CENÁRIO 1: Título já pago (tem payment vinculado)
        # =========================================================================
        if matched_credit_ids and (saldo_titulo <= 0 or l10n_br_paga):
            logger.info(f"    Título já quitado - marcando como conciliado")
            vinculo.titulo_saldo_depois = 0
            return {
                'vinculo_id': vinculo.id,
                'titulo_id': titulo_odoo_id,
                'saldo_antes': saldo_titulo,
                'saldo_depois': 0,
                'mensagem': 'Título já quitado'
            }

        # =========================================================================
        # CENÁRIO 2: Título com saldo - criar payment (com ou sem juros)
        # =========================================================================
        # CORREÇÃO 14 (22/01/2026): Separar juros quando valor_alocado > saldo_titulo
        # Se cliente pagou mais que o saldo (juros), usar wizard com Write-Off
        if saldo_titulo > 0:
            # Calcular valores: principal (abate título) e juros (receita financeira)
            valor_principal = min(valor_alocado, saldo_titulo)
            valor_juros = valor_alocado - valor_principal if valor_alocado > saldo_titulo else 0

            # Extrair dados do título
            partner_id = titulo_odoo.get('partner_id')
            partner_id_num = partner_id[0] if isinstance(partner_id, (list, tuple)) else partner_id

            move = titulo_odoo.get('move_id')
            move_name = move[1] if isinstance(move, (list, tuple)) else str(move)

            # Obter journal_id do lote do extrato (ou usar GRAFENO como padrão)
            # FLUXO TESTADO (22/01/2026): Retorno CNAB Grafeno (banco 274)
            journal_id = item.lote.journal_id if item.lote and item.lote.journal_id else JOURNAL_GRAFENO_ID

            # Tolerância de 1 centavo para considerar juros
            if valor_juros > 0.01:
                # =====================================================================
                # CASO COM JUROS: Usar wizard account.payment.register com Write-Off
                # =====================================================================
                # O wizard já faz: criar payment + postar + reconciliar título + contabilizar juros
                logger.info(
                    f"    Criando payment COM JUROS: Principal R$ {valor_principal:.2f} + "
                    f"Juros R$ {valor_juros:.2f} = Total R$ {valor_alocado:.2f}"
                )

                payment_id, payment_name = self.baixa_service._criar_pagamento_com_writeoff_juros(
                    titulo_id=titulo_odoo_id,
                    partner_id=partner_id_num,
                    valor_pagamento=valor_principal,
                    valor_juros=valor_juros,
                    journal_id=journal_id,
                    ref=f"{move_name} (Extrato {item.id})",
                    data=item.data_transacao or datetime.now().date(),
                    company_id=titulo_company_id
                )
                logger.info(f"    Payment com Write-Off criado: {payment_name} (ID {payment_id})")

                # O wizard já postou e reconciliou - não chamar _postar_pagamento nem _executar_reconcile
            else:
                # =====================================================================
                # CASO SEM JUROS: Fluxo original (criar payment simples)
                # =====================================================================
                logger.info(f"    Criando payment SEM juros: R$ {valor_principal:.2f}")

                payment_id, payment_name = self.baixa_service._criar_pagamento(
                    partner_id=partner_id_num,
                    valor=valor_principal,
                    journal_id=journal_id,
                    ref=f"{move_name} (Extrato {item.id})",
                    data=item.data_transacao or datetime.now().date(),
                    company_id=titulo_company_id
                )
                logger.info(f"    Payment criado: {payment_name} (ID {payment_id})")

                # Postar payment (só para caso sem juros)
                self.baixa_service._postar_pagamento(payment_id)
                logger.info(f"    Payment postado")

                # Buscar linha de crédito do payment e reconciliar com título (só para caso sem juros)
                credit_line_id = self.baixa_service._buscar_linha_credito(payment_id)
                if credit_line_id:
                    self._executar_reconcile(credit_line_id, titulo_odoo_id)
                    logger.info(f"    Título reconciliado com payment")

            # Salvar IDs de referência
            vinculo.payment_id = payment_id
            vinculo.partial_reconcile_id = self._buscar_partial_reconcile(titulo_odoo_id)

            # Buscar saldo atualizado
            titulo_atualizado = self._buscar_titulo_por_id(titulo_odoo_id)
            vinculo.titulo_saldo_depois = titulo_atualizado.get('amount_residual', 0) if titulo_atualizado else None

            # Verificar full_reconcile
            if titulo_atualizado and titulo_atualizado.get('full_reconcile_id'):
                full_rec = titulo_atualizado.get('full_reconcile_id')
                if isinstance(full_rec, (list, tuple)) and len(full_rec) > 0:
                    vinculo.full_reconcile_id = full_rec[0]

            return {
                'vinculo_id': vinculo.id,
                'titulo_id': titulo_odoo_id,
                'payment_id': payment_id,
                'payment_name': payment_name,
                'valor_principal': valor_principal,
                'valor_juros': valor_juros,
                'valor_total': valor_alocado,
                'saldo_antes': saldo_titulo,
                'saldo_depois': vinculo.titulo_saldo_depois,
                'partial_reconcile_id': vinculo.partial_reconcile_id,
                'mensagem': f'Payment criado: {payment_name}' + (f' (juros R$ {valor_juros:.2f})' if valor_juros > 0.01 else '')
            }

        # =========================================================================
        # CENÁRIO 3: Título sem saldo (já quitado por outro meio)
        # =========================================================================
        logger.info(f"    Título já sem saldo - apenas marcando")
        vinculo.titulo_saldo_depois = 0
        return {
            'vinculo_id': vinculo.id,
            'titulo_id': titulo_odoo_id,
            'saldo_antes': saldo_titulo,
            'saldo_depois': 0,
            'mensagem': 'Título já quitado (sem saldo)'
        }
