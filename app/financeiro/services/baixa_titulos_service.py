# -*- coding: utf-8 -*-
"""
Servico de Baixa de Titulos via API Odoo
========================================

Implementa o fluxo completo de baixa de titulos de recebimento:
1. Buscar titulo no Odoo
2. Capturar snapshot ANTES
3. Criar account.payment
4. Postar pagamento (action_post)
5. Reconciliar com titulo (reconcile)
6. Capturar snapshot DEPOIS
7. Registrar campos alterados

Baseado na documentacao: DOCUMENTACAO_BAIXA_TITULOS_ODOO.md

Autor: Sistema de Fretes
Data: 2025-12-10
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app import db
from app.financeiro.models import BaixaTituloLote, BaixaTituloItem

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES - JOURNAL JUROS RECEBIDOS
# =============================================================================

# ID do journal especial para lancamento de juros recebidos
# Este journal permite valores acima do saldo do titulo
JOURNAL_JUROS_RECEBIDOS_ID = 1066
JOURNAL_JUROS_RECEBIDOS_CODE = 'JUROS'
JOURNAL_JUROS_RECEBIDOS_NAME = 'JUROS RECEBIDOS'


# Campos criticos para snapshot do titulo
CAMPOS_SNAPSHOT_TITULO = [
    'id', 'name', 'debit', 'credit', 'balance',
    'amount_residual', 'amount_residual_currency',
    'reconciled', 'matched_credit_ids', 'matched_debit_ids',
    'full_reconcile_id', 'matching_number',
    'date_maturity', 'partner_id', 'move_id', 'company_id',
    'l10n_br_paga', 'l10n_br_cobranca_parcela',
    'x_studio_status_de_pagamento', 'x_studio_nf_e'
]

# Campos criticos para snapshot da NF
CAMPOS_SNAPSHOT_MOVE = [
    'id', 'name', 'state', 'payment_state',
    'amount_total', 'amount_residual', 'amount_residual_signed',
    'has_reconciled_entries', 'partner_id'
]


class BaixaTitulosService:
    """
    Servico para criar baixas de titulos no Odoo via API.
    """

    def __init__(self, connection=None):
        self._connection = connection
        self.estatisticas = {
            'processados': 0,
            'sucesso': 0,
            'erro': 0,
            'ignorados': 0
        }

    @property
    def connection(self):
        """Retorna a conexao Odoo, criando se necessario."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise Exception("Falha na autenticacao com Odoo")
        return self._connection

    def processar_lote(self, lote_id: int) -> Dict:
        """
        Processa todas as baixas ativas de um lote.

        Args:
            lote_id: ID do lote a processar

        Returns:
            Dict com estatisticas do processamento
        """
        lote = BaixaTituloLote.query.get(lote_id)
        if not lote:
            raise ValueError(f"Lote {lote_id} nao encontrado")

        logger.info(f"=" * 60)
        logger.info(f"PROCESSANDO LOTE {lote_id} - {lote.nome_arquivo}")
        logger.info(f"=" * 60)

        # Buscar itens ativos e validos
        itens = BaixaTituloItem.query.filter_by(
            lote_id=lote_id,
            ativo=True,
            status='VALIDO'
        ).order_by(BaixaTituloItem.linha_excel).all()

        logger.info(f"Itens a processar: {len(itens)}")

        for item in itens:
            try:
                self._processar_item(item)
                self.estatisticas['sucesso'] += 1
            except Exception as e:
                logger.error(f"Erro no item {item.id}: {e}")
                item.status = 'ERRO'
                item.mensagem = str(e)
                item.processado_em = datetime.utcnow()
                self.estatisticas['erro'] += 1

            self.estatisticas['processados'] += 1
            db.session.commit()

        # Atualizar lote
        lote.status = 'CONCLUIDO'
        lote.processado_em = datetime.utcnow()
        lote.linhas_processadas = self.estatisticas['processados']
        lote.linhas_sucesso = self.estatisticas['sucesso']
        lote.linhas_erro = self.estatisticas['erro']
        db.session.commit()

        logger.info(f"Lote {lote_id} concluido: {self.estatisticas}")

        return self.estatisticas

    def _processar_item(self, item: BaixaTituloItem) -> None:
        """
        Processa um item de baixa individual.

        Suporta lancamento de juros:
        - Se juros_excel > 0: verifica se nao existe juros no Odoo e cria lancamento separado
        - Valor do juros pode ser acima do saldo do titulo
        - Usa journal JUROS RECEBIDOS (ID 1066)
        """
        juros_excel = getattr(item, 'juros_excel', 0) or 0

        logger.info(f"Processando: NF {item.nf_excel} P{item.parcela_excel} R$ {item.valor_excel}" +
                    (f" + JUROS R$ {juros_excel}" if juros_excel > 0 else ""))

        item.status = 'PROCESSANDO'
        db.session.commit()

        # 1. Buscar titulo no Odoo
        titulo = self._buscar_titulo(item.nf_excel, item.parcela_excel)
        if not titulo:
            raise ValueError(f"Titulo nao encontrado: NF {item.nf_excel} P{item.parcela_excel}")

        # Salvar dados do titulo
        item.titulo_odoo_id = titulo['id']
        item.move_odoo_id = self._extrair_id(titulo.get('move_id'))
        item.move_odoo_name = self._extrair_nome(titulo.get('move_id'))
        item.partner_odoo_id = self._extrair_id(titulo.get('partner_id'))
        item.valor_titulo_odoo = titulo.get('debit', 0)
        item.saldo_antes = titulo.get('amount_residual', 0)

        # Extrair company_id do titulo (IMPORTANTE para multi-company)
        company_id = self._extrair_id(titulo.get('company_id'))
        company_name = self._extrair_nome(titulo.get('company_id'))
        if not company_id:
            raise ValueError(f"Titulo sem company_id definido")

        logger.info(f"  Titulo encontrado: ID={item.titulo_odoo_id}, Company={company_id} ({company_name}), Saldo={item.saldo_antes}")

        # NOTA: O Odoo permite usar journal de outra empresa!
        journal_id_final = item.journal_odoo_id
        logger.info(f"  Usando journal: {item.journal_excel} (ID={journal_id_final})")

        # =================================================================
        # VALIDACAO DE JUROS - Verificar se ja existe no Odoo
        # =================================================================
        if juros_excel > 0:
            juros_existente = self._verificar_juros_existente_odoo(item.nf_excel, item.parcela_excel)
            if juros_existente:
                raise ValueError(
                    f"Ja existe baixa de JUROS RECEBIDOS para NF {item.nf_excel} P{item.parcela_excel}"
                )

        # =================================================================
        # VALIDACAO DE SALDO
        # - Valor principal deve respeitar saldo (exceto se for 0)
        # - Juros NAO valida saldo (pode ser acima)
        # =================================================================
        tem_valor_principal = item.valor_excel > 0

        if tem_valor_principal:
            if item.valor_excel > item.saldo_antes + 0.01:  # Tolerancia de 1 centavo
                raise ValueError(
                    f"Valor ({item.valor_excel}) maior que saldo ({item.saldo_antes})"
                )

        # 2. Capturar snapshot ANTES
        snapshot_antes = self._capturar_snapshot(item.titulo_odoo_id, item.move_odoo_id)
        item.set_snapshot_antes(snapshot_antes)

        # =================================================================
        # LANCAMENTO 1: VALOR PRINCIPAL (se > 0)
        # =================================================================
        if tem_valor_principal:
            # 3. Criar pagamento no Odoo (na mesma empresa do titulo!)
            payment_id, payment_name = self._criar_pagamento(
                partner_id=item.partner_odoo_id,
                valor=item.valor_excel,
                journal_id=journal_id_final,
                ref=item.move_odoo_name,
                data=item.data_excel,
                company_id=company_id
            )

            item.payment_odoo_id = payment_id
            item.payment_odoo_name = payment_name

            # 4. Postar pagamento
            self._postar_pagamento(payment_id)

            # 5. Buscar linha de credito criada
            credit_line_id = self._buscar_linha_credito(payment_id)
            if not credit_line_id:
                raise ValueError("Linha de credito nao encontrada apos postar pagamento")

            # 6. Reconciliar
            self._reconciliar(credit_line_id, item.titulo_odoo_id)

            logger.info(f"  Pagamento principal criado: {payment_name}")
        else:
            logger.info(f"  Sem valor principal (R$ 0), apenas juros sera lancado")

        # =================================================================
        # LANCAMENTO 2: JUROS (se > 0)
        # =================================================================
        if juros_excel > 0:
            payment_juros_id, payment_juros_name = self._criar_pagamento_juros(
                partner_id=item.partner_odoo_id,
                valor_juros=juros_excel,
                ref=item.move_odoo_name,
                data=item.data_excel,
                company_id=company_id
            )

            item.payment_juros_odoo_id = payment_juros_id
            item.payment_juros_odoo_name = payment_juros_name

            logger.info(f"  Pagamento JUROS criado: {payment_juros_name}")

        # 7. Capturar snapshot DEPOIS
        snapshot_depois = self._capturar_snapshot(item.titulo_odoo_id, item.move_odoo_id)
        item.set_snapshot_depois(snapshot_depois)

        # 8. Identificar campos alterados
        campos_alterados = self._comparar_snapshots(snapshot_antes, snapshot_depois)
        item.set_campos_alterados(campos_alterados)

        # 9. Atualizar saldo depois
        titulo_atualizado = self._buscar_titulo_por_id(item.titulo_odoo_id)
        item.saldo_depois = titulo_atualizado.get('amount_residual', 0) if titulo_atualizado else None

        # 10. Buscar partial_reconcile criado (se houve valor principal)
        if tem_valor_principal:
            item.partial_reconcile_id = self._buscar_partial_reconcile(item.titulo_odoo_id)

        item.status = 'SUCESSO'
        item.processado_em = datetime.utcnow()
        item.validado_em = datetime.utcnow()

        # Log de conclusao
        pagamentos_criados = []
        if item.payment_odoo_name:
            pagamentos_criados.append(item.payment_odoo_name)
        if item.payment_juros_odoo_name:
            pagamentos_criados.append(f"JUROS: {item.payment_juros_odoo_name}")

        logger.info(f"  OK - Payments: {', '.join(pagamentos_criados)}, Saldo: {item.saldo_antes} -> {item.saldo_depois}")

    def _buscar_titulo(self, nf: str, parcela: int) -> Optional[Dict]:
        """
        Busca titulo no Odoo por numero da NF-e e parcela.
        """
        # Buscar pelo campo x_studio_nf_e
        titulos = self.connection.search_read(
            'account.move.line',
            [
                ['x_studio_nf_e', '=', nf],
                ['l10n_br_cobranca_parcela', '=', parcela],
                ['account_type', '=', 'asset_receivable'],
                ['parent_state', '=', 'posted']
            ],
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=5
        )

        if titulos:
            # Se encontrou mais de um, preferir empresa 1 (FB)
            if len(titulos) > 1:
                for t in titulos:
                    company = t.get('company_id')
                    if company and isinstance(company, (list, tuple)):
                        if 'FB' in company[1]:
                            return t
            return titulos[0]

        # Fallback: buscar pelo nome do move
        titulos = self.connection.search_read(
            'account.move.line',
            [
                ['move_id.name', 'ilike', nf],
                ['l10n_br_cobranca_parcela', '=', parcela],
                ['account_type', '=', 'asset_receivable'],
                ['parent_state', '=', 'posted']
            ],
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=5
        )

        return titulos[0] if titulos else None

    def _buscar_titulo_por_id(self, titulo_id: int) -> Optional[Dict]:
        """Busca titulo por ID."""
        titulos = self.connection.search_read(
            'account.move.line',
            [['id', '=', titulo_id]],
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=1
        )
        return titulos[0] if titulos else None

    def _capturar_snapshot(self, titulo_id: int, move_id: int) -> Dict:
        """
        Captura snapshot completo do titulo e da NF.
        """
        snapshot = {'titulo': None, 'move': None}

        # Titulo
        titulos = self.connection.search_read(
            'account.move.line',
            [['id', '=', titulo_id]],
            fields=CAMPOS_SNAPSHOT_TITULO,
            limit=1
        )
        if titulos:
            snapshot['titulo'] = titulos[0]

        # Move (NF)
        if move_id:
            moves = self.connection.search_read(
                'account.move',
                [['id', '=', move_id]],
                fields=CAMPOS_SNAPSHOT_MOVE,
                limit=1
            )
            if moves:
                snapshot['move'] = moves[0]

        return snapshot

    def _criar_pagamento(
        self,
        partner_id: int,
        valor: float,
        journal_id: int,
        ref: str,
        data,
        company_id: int
    ) -> Tuple[int, str]:
        """
        Cria um account.payment no Odoo.

        Args:
            partner_id: ID do parceiro
            valor: Valor do pagamento
            journal_id: ID do journal
            ref: Referencia (nome do move)
            data: Data do pagamento
            company_id: ID da empresa (OBRIGATORIO para multi-company)

        Returns:
            Tuple com (payment_id, payment_name)
        """
        # Converter data para string se necessario
        data_str = data.strftime('%Y-%m-%d') if hasattr(data, 'strftime') else str(data)

        payment_data = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': partner_id,
            'amount': valor,
            'journal_id': journal_id,
            'ref': ref,
            'date': data_str,
            'company_id': company_id  # IMPORTANTE: mesma empresa do titulo
        }

        logger.info(f"  Criando pagamento: Company={company_id}, Journal={journal_id}, Valor={valor}")

        payment_id = self.connection.execute_kw(
            'account.payment',
            'create',
            [payment_data]
        )

        # Buscar nome gerado
        payment = self.connection.search_read(
            'account.payment',
            [['id', '=', payment_id]],
            fields=['name'],
            limit=1
        )

        payment_name = payment[0]['name'] if payment else f'Payment #{payment_id}'

        return payment_id, payment_name

    def _postar_pagamento(self, payment_id: int) -> None:
        """
        Confirma o pagamento (state = posted).
        Nota: action_post retorna None, causando erro de serializacao XML-RPC.
        Isso e esperado e deve ser ignorado.
        """
        try:
            self.connection.execute_kw(
                'account.payment',
                'action_post',
                [[payment_id]]
            )
        except Exception as e:
            # Ignorar erro de serializacao - operacao foi executada
            if "cannot marshal None" not in str(e):
                raise

    def _buscar_linha_credito(self, payment_id: int) -> Optional[int]:
        """
        Busca a linha de credito criada automaticamente pelo pagamento.
        """
        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['payment_id', '=', payment_id],
                ['account_type', '=', 'asset_receivable']
            ],
            fields=['id'],
            limit=1
        )
        return linhas[0]['id'] if linhas else None

    def _reconciliar(self, credit_line_id: int, titulo_id: int) -> None:
        """
        Reconcilia a linha de credito com o titulo.
        Nota: reconcile retorna None, causando erro de serializacao XML-RPC.
        Isso e esperado e deve ser ignorado.
        """
        try:
            self.connection.execute_kw(
                'account.move.line',
                'reconcile',
                [[credit_line_id, titulo_id]]
            )
        except Exception as e:
            # Ignorar erro de serializacao - operacao foi executada
            if "cannot marshal None" not in str(e):
                raise

    def _buscar_partial_reconcile(self, titulo_id: int) -> Optional[int]:
        """
        Busca o ultimo partial_reconcile criado para o titulo.
        """
        # Buscar matched_credit_ids do titulo
        titulo = self._buscar_titulo_por_id(titulo_id)
        if not titulo:
            return None

        matched_ids = titulo.get('matched_credit_ids', [])
        if matched_ids:
            return matched_ids[-1]  # Ultimo criado

        return None

    def _comparar_snapshots(self, antes: Dict, depois: Dict) -> List[str]:
        """
        Compara snapshots e retorna lista de campos alterados.
        """
        campos_alterados = []

        # Comparar titulo
        if antes.get('titulo') and depois.get('titulo'):
            for campo in CAMPOS_SNAPSHOT_TITULO:
                valor_antes = antes['titulo'].get(campo)
                valor_depois = depois['titulo'].get(campo)
                if valor_antes != valor_depois:
                    campos_alterados.append(f'titulo.{campo}')

        # Comparar move
        if antes.get('move') and depois.get('move'):
            for campo in CAMPOS_SNAPSHOT_MOVE:
                valor_antes = antes['move'].get(campo)
                valor_depois = depois['move'].get(campo)
                if valor_antes != valor_depois:
                    campos_alterados.append(f'move.{campo}')

        return campos_alterados

    def _extrair_id(self, valor) -> Optional[int]:
        """Extrai ID de um campo many2one do Odoo."""
        if not valor:
            return None
        if isinstance(valor, (list, tuple)) and len(valor) > 0:
            return valor[0]
        if isinstance(valor, int):
            return valor
        return None

    def _extrair_nome(self, valor) -> Optional[str]:
        """Extrai nome de um campo many2one do Odoo."""
        if not valor:
            return None
        if isinstance(valor, (list, tuple)) and len(valor) > 1:
            return valor[1]
        return None

    def _verificar_juros_existente_odoo(self, nf: str, parcela: int) -> bool:
        """
        Verifica se ja existe baixa de juros no Odoo para NF+parcela.

        Busca no account.payment com journal_id = JOURNAL_JUROS_RECEBIDOS_ID
        e ref contendo o numero da NF.

        Args:
            nf: Numero da NF-e
            parcela: Numero da parcela

        Returns:
            True se ja existe baixa de juros, False caso contrario
        """
        try:
            # Buscar pagamentos com journal de juros que referenciam esta NF
            pagamentos = self.connection.search_read(
                'account.payment',
                [
                    ['journal_id', '=', JOURNAL_JUROS_RECEBIDOS_ID],
                    ['ref', 'ilike', nf],
                    ['state', '=', 'posted']
                ],
                fields=['id', 'name', 'ref', 'amount'],
                limit=10
            )

            if not pagamentos:
                return False

            # Verificar se algum pagamento corresponde a esta NF+parcela
            for pagamento in pagamentos:
                ref = pagamento.get('ref', '') or ''
                # Verificar se a ref contem a NF (pode estar no formato "VND/2025/00123")
                if nf in ref:
                    logger.info(f"  Juros ja existe para NF {nf}: Payment {pagamento.get('name')}")
                    return True

            return False

        except Exception as e:
            logger.warning(f"Erro ao verificar juros existente: {e}")
            return False

    def _criar_pagamento_juros(
        self,
        partner_id: int,
        valor_juros: float,
        ref: str,
        data,
        company_id: int
    ) -> Tuple[int, str]:
        """
        Cria um pagamento de juros no Odoo usando journal JUROS RECEBIDOS.

        Diferente do pagamento normal, este pagamento:
        - NAO e reconciliado com o titulo (valor acima do saldo)
        - Usa journal especifico de juros

        Args:
            partner_id: ID do parceiro
            valor_juros: Valor do juros
            ref: Referencia (nome do move)
            data: Data do pagamento
            company_id: ID da empresa

        Returns:
            Tuple com (payment_id, payment_name)
        """
        # Converter data para string se necessario
        data_str = data.strftime('%Y-%m-%d') if hasattr(data, 'strftime') else str(data)

        payment_data = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': partner_id,
            'amount': valor_juros,
            'journal_id': JOURNAL_JUROS_RECEBIDOS_ID,
            'ref': f"JUROS - {ref}",
            'date': data_str,
            'company_id': company_id
        }

        logger.info(f"  Criando pagamento JUROS: Company={company_id}, Valor={valor_juros}")

        payment_id = self.connection.execute_kw(
            'account.payment',
            'create',
            [payment_data]
        )

        # Postar pagamento
        try:
            self.connection.execute_kw(
                'account.payment',
                'action_post',
                [[payment_id]]
            )
        except Exception as e:
            # Ignorar erro de serializacao - operacao foi executada
            if "cannot marshal None" not in str(e):
                raise

        # Buscar nome gerado
        payment = self.connection.search_read(
            'account.payment',
            [['id', '=', payment_id]],
            fields=['name'],
            limit=1
        )

        payment_name = payment[0]['name'] if payment else f'Payment #{payment_id}'

        return payment_id, payment_name
