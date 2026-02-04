# -*- coding: utf-8 -*-
"""
Serviço de Baixa de Pagamentos (Contas a Pagar) via API Odoo
============================================================

Implementa o fluxo completo de baixa de pagamentos a fornecedores:
1. Buscar título a pagar no Odoo (liability_payable)
2. Buscar linha de extrato correspondente (amount < 0)
3. Capturar snapshot ANTES
4. Criar account.payment (outbound, supplier)
5. Postar pagamento (action_post)
6. Reconciliar payment com título
7. Reconciliar payment com extrato
8. Capturar snapshot DEPOIS
9. Registrar resultado

DIFERENÇAS CHAVE EM RELAÇÃO A RECEBIMENTOS:
- payment_type = 'outbound' (não 'inbound')
- partner_type = 'supplier' (não 'customer')
- account_type = 'liability_payable' (não 'asset_receivable')
- Linha do título tem credit > 0 (não debit > 0)
- amount_residual é NEGATIVO (representa valor a pagar)
- Extrato: amount < 0 (saídas)

Autor: Sistema de Fretes
Data: 2025-12-13
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app import db
from app.financeiro.models import BaixaPagamentoLote, BaixaPagamentoItem

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Campos para snapshot do título a pagar
CAMPOS_SNAPSHOT_TITULO = [
    'id', 'name', 'debit', 'credit', 'balance',
    'amount_residual', 'amount_residual_currency',
    'reconciled', 'matched_credit_ids', 'matched_debit_ids',
    'full_reconcile_id', 'matching_number',
    'date_maturity', 'partner_id', 'move_id', 'company_id',
    'l10n_br_paga', 'l10n_br_cobranca_parcela', 'x_studio_nf_e'
]

# Contas contábeis (mesmo do recebimentos)
CONTA_PAGAMENTOS_PENDENTES = 26868  # 1110100004 PAGAMENTOS/RECEBIMENTOS PENDENTES
CONTA_TRANSITORIA = 22199           # 1110100003 TRANSITÓRIA DE VALORES

# Conta 3701010003 JUROS DE PAGAMENTOS EM ATRASO (expense)
# Quando pagamento a fornecedor tem juros (valor_pago > saldo do título),
# a diferença vai para esta conta como DESPESA
CONTA_JUROS_PAGAMENTOS_POR_COMPANY = {
    1: 22769,  # NACOM GOYA - FB
    3: 24051,  # NACOM GOYA - SC
    4: 25335,  # NACOM GOYA - CD
    5: 26619,  # LA FAMIGLIA - LF
}

# Regex para extrair CNPJ do payment_ref
REGEX_CNPJ = re.compile(r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-.\s]?\d{2})')


class BaixaPagamentosService:
    """
    Serviço para baixar pagamentos (contas a pagar) via API Odoo.
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
        """Retorna a conexão Odoo, criando se necessário."""
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
            if not self._connection.authenticate():
                raise Exception("Falha na autenticação com Odoo")
        return self._connection

    # =========================================================================
    # BUSCA DE TÍTULO A PAGAR
    # =========================================================================

    def buscar_titulo_por_nf_parcela(self, nf: str, parcela: int) -> Optional[Dict]:
        """
        Busca título a pagar por NF e parcela.

        Args:
            nf: Número da NF-e
            parcela: Número da parcela

        Returns:
            Dict com dados do título ou None
        """
        titulos = self.connection.search_read(
            'account.move.line',
            [
                ['x_studio_nf_e', '=', nf],
                ['l10n_br_cobranca_parcela', '=', parcela],
                ['account_type', '=', 'liability_payable'],  # Contas a PAGAR
                ['parent_state', '=', 'posted']
            ],
            fields=CAMPOS_SNAPSHOT_TITULO + ['account_id'],
            limit=5
        )

        if not titulos:
            return None

        # Se encontrou mais de um, filtrar por não reconciliado
        for titulo in titulos:
            if not titulo.get('reconciled', False):
                return titulo

        # Se todos reconciliados, retornar o primeiro
        return titulos[0] if titulos else None

    def buscar_titulo_por_id(self, titulo_id: int) -> Optional[Dict]:
        """Busca título por ID."""
        titulos = self.connection.search_read(
            'account.move.line',
            [['id', '=', titulo_id]],
            fields=CAMPOS_SNAPSHOT_TITULO + ['account_id'],
            limit=1
        )
        return titulos[0] if titulos else None

    def buscar_titulos_por_cnpj_valor(
        self,
        cnpj: str,
        valor: float,
        tolerancia: float = 0.05
    ) -> List[Dict]:
        """
        Busca títulos a pagar por CNPJ do fornecedor e valor aproximado.

        Args:
            cnpj: CNPJ do fornecedor (limpo ou formatado)
            valor: Valor do pagamento (positivo)
            tolerancia: Tolerância de valor

        Returns:
            Lista de títulos candidatos ordenados por score
        """
        cnpj_limpo = re.sub(r'\D', '', cnpj) if cnpj else ''

        if not cnpj_limpo:
            return []

        # Buscar fornecedor pelo CNPJ
        parceiros = self.connection.search_read(
            'res.partner',
            [['l10n_br_cnpj', 'ilike', cnpj_limpo[:8]]],  # Busca pela raiz do CNPJ
            fields=['id', 'name', 'l10n_br_cnpj'],
            limit=20
        )

        if not parceiros:
            return []

        partner_ids = [p['id'] for p in parceiros]

        # Buscar títulos desses fornecedores
        valor_min = valor - tolerancia
        valor_max = valor + tolerancia

        titulos = self.connection.search_read(
            'account.move.line',
            [
                ['partner_id', 'in', partner_ids],
                ['account_type', '=', 'liability_payable'],
                ['parent_state', '=', 'posted'],
                ['reconciled', '=', False],
                ['credit', '>=', valor_min],
                ['credit', '<=', valor_max]
            ],
            fields=CAMPOS_SNAPSHOT_TITULO + ['account_id'],
            limit=20
        )

        # Calcular score para cada título
        resultados = []
        for titulo in titulos:
            diferenca = abs(titulo['credit'] - valor)
            if diferenca <= 0.02:
                score = 100
                criterio = 'CNPJ+VALOR_EXATO'
            elif diferenca <= 1.00:
                score = 95
                criterio = 'CNPJ+VALOR_PROXIMO'
            else:
                score = 90 - int(diferenca)
                criterio = 'CNPJ+VALOR_APROX'

            resultados.append({
                'titulo': titulo,
                'score': max(score, 50),
                'criterio': criterio,
                'diferenca_valor': diferenca
            })

        # Ordenar por score
        resultados.sort(key=lambda x: x['score'], reverse=True)

        return resultados

    # =========================================================================
    # BUSCA DE EXTRATO (SAÍDAS)
    # =========================================================================

    def buscar_linha_extrato_por_valor(
        self,
        valor: float,
        data_inicio: str = None,
        data_fim: str = None,
        tolerancia: float = 0.05
    ) -> List[Dict]:
        """
        Busca linhas de extrato (saídas) por valor aproximado.

        Args:
            valor: Valor do pagamento (positivo)
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            tolerancia: Tolerância de valor

        Returns:
            Lista de linhas de extrato
        """
        # Extrato de saída tem amount NEGATIVO
        valor_min = -(valor + tolerancia)
        valor_max = -(valor - tolerancia)

        filtro = [
            ['amount', '>=', valor_min],
            ['amount', '<=', valor_max],
            ['is_reconciled', '=', False]
        ]

        if data_inicio:
            filtro.append(['date', '>=', data_inicio])
        if data_fim:
            filtro.append(['date', '<=', data_fim])

        linhas = self.connection.search_read(
            'account.bank.statement.line',
            filtro,
            fields=[
                'id', 'statement_id', 'move_id', 'date', 'amount',
                'payment_ref', 'partner_id', 'is_reconciled',
                'journal_id', 'company_id'
            ],
            limit=20
        )

        return linhas

    def buscar_linha_debito_extrato(self, move_id: int) -> Optional[int]:
        """
        Busca a linha de DÉBITO do extrato (conta TRANSITÓRIA).

        Args:
            move_id: ID do account.move do extrato

        Returns:
            ID da linha de débito ou None
        """
        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['move_id', '=', move_id],
                ['debit', '>', 0],
                ['reconciled', '=', False]
            ],
            fields=['id', 'debit', 'account_id'],
            limit=5
        )

        for linha in linhas:
            # Preferir linha na conta transitória
            if linha.get('account_id') and linha['account_id'][0] == CONTA_TRANSITORIA:
                return linha['id']

        # Se não encontrar na transitória, retornar qualquer uma não reconciliada
        return linhas[0]['id'] if linhas else None

    # =========================================================================
    # EXTRAÇÃO DE DADOS DO PAYMENT_REF
    # =========================================================================

    def extrair_dados_payment_ref(self, payment_ref: str) -> Dict:
        """
        Extrai CNPJ, nome e tipo de transação do payment_ref.

        Formatos comuns de SAÍDA:
        - ": PIX Enviado - FORNECEDOR - 12.345.678/0001-90 - Banco: ..."
        - ": TED Enviada - FORNECEDOR - 12.345.678/0001-90 - ..."
        - ": Pagamento - FORNECEDOR - 12345678000190"

        Returns:
            Dict com tipo_transacao, nome_beneficiario, cnpj_beneficiario
        """
        resultado = {
            'tipo_transacao': None,
            'nome_beneficiario': None,
            'cnpj_beneficiario': None
        }

        if not payment_ref:
            return resultado

        # Extrair CNPJ
        match_cnpj = REGEX_CNPJ.search(payment_ref)
        if match_cnpj:
            cnpj_raw = match_cnpj.group(1)
            resultado['cnpj_beneficiario'] = re.sub(r'\D', '', cnpj_raw)

        # Identificar tipo de transação
        payment_ref_upper = payment_ref.upper()
        if 'PIX ENVIADO' in payment_ref_upper:
            resultado['tipo_transacao'] = 'PIX'
        elif 'TED ENVIADA' in payment_ref_upper or 'TED ENV' in payment_ref_upper:
            resultado['tipo_transacao'] = 'TED'
        elif 'PAGAMENTO' in payment_ref_upper:
            resultado['tipo_transacao'] = 'PAGAMENTO'
        elif 'BOLETO' in payment_ref_upper:
            resultado['tipo_transacao'] = 'BOLETO'
        elif 'DEB' in payment_ref_upper:
            resultado['tipo_transacao'] = 'DEBITO'
        else:
            resultado['tipo_transacao'] = 'OUTROS'

        # Extrair nome do beneficiário
        # Formato típico: "PIX Enviado - NOME - CNPJ - ..."
        partes = payment_ref.split(' - ')
        if len(partes) >= 2:
            # O nome geralmente está na segunda parte
            nome = partes[1].strip()
            # Limpar sufixos comuns
            nome = re.sub(r'\s*(LTDA|ME|EPP|EIRELI|S/?A|S\.A\.).*$', '', nome, flags=re.IGNORECASE)
            resultado['nome_beneficiario'] = nome.strip()[:255]

        return resultado

    # =========================================================================
    # CRIAR PAGAMENTO (OUTBOUND)
    # =========================================================================

    def criar_pagamento_outbound(
        self,
        partner_id: int,
        valor: float,
        journal_id: int,
        ref: str,
        data: str,
        company_id: int
    ) -> Tuple[int, str]:
        """
        Cria um account.payment OUTBOUND (pagamento a fornecedor) no Odoo.

        Args:
            partner_id: ID do fornecedor
            valor: Valor do pagamento
            journal_id: ID do journal (conta bancária)
            ref: Referência (nome do move/NF)
            data: Data do pagamento (YYYY-MM-DD)
            company_id: ID da empresa

        Returns:
            Tuple com (payment_id, payment_name)
        """
        # Converter data para string se necessário
        data_str = data.strftime('%Y-%m-%d') if hasattr(data, 'strftime') else str(data)

        payment_data = {
            'payment_type': 'outbound',    # SAÍDA (diferente de recebimentos)
            'partner_type': 'supplier',     # FORNECEDOR (diferente de recebimentos)
            'partner_id': partner_id,
            'amount': valor,
            'journal_id': journal_id,
            'ref': ref,
            'date': data_str,
            'company_id': company_id
        }

        logger.info(f"  Criando pagamento OUTBOUND: Company={company_id}, Journal={journal_id}, Valor={valor}")

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

    def criar_pagamento_outbound_com_writeoff(
        self,
        titulo_id: int,
        partner_id: int,
        valor_titulo: float,
        valor_juros: float,
        journal_id: int,
        ref: str,
        data,
        company_id: int
    ) -> Tuple[int, str]:
        """
        Cria pagamento OUTBOUND usando wizard account.payment.register com Write-Off para juros.

        Quando pagamento a fornecedor tem valor > saldo do título, a diferença (juros)
        vai para conta de despesa 3701010003 JUROS DE PAGAMENTOS EM ATRASO.

        O wizard automaticamente:
        1. Cria o payment com valor_total (principal + juros)
        2. Separa principal vs juros
        3. Lança juros na conta contábil correta
        4. Reconcilia TOTALMENTE o título

        Args:
            titulo_id: ID da linha do título (account.move.line)
            partner_id: ID do fornecedor (res.partner)
            valor_titulo: Valor do título (saldo a pagar, sem juros)
            valor_juros: Valor dos juros a ser lançado como write-off
            journal_id: ID do journal de pagamento
            ref: Referência (nome do move/NF)
            data: Data do pagamento
            company_id: ID da empresa

        Returns:
            Tuple com (payment_id, payment_name)
        """
        # Converter data para string
        data_str = data.strftime('%Y-%m-%d') if hasattr(data, 'strftime') else str(data)

        # Buscar conta de juros para a empresa
        conta_juros_id = CONTA_JUROS_PAGAMENTOS_POR_COMPANY.get(company_id)
        if not conta_juros_id:
            raise ValueError(f"Conta de juros de pagamentos não mapeada para company_id={company_id}")

        # Valor total do pagamento (principal + juros)
        valor_total = round(valor_titulo + valor_juros, 2)

        logger.info(
            f"  Criando pagamento OUTBOUND com Write-Off: "
            f"Principal={valor_titulo:.2f}, Juros={valor_juros:.2f}, "
            f"Total={valor_total:.2f}, Conta Juros={conta_juros_id}"
        )

        # 1. Criar o wizard account.payment.register vinculado ao título
        wizard_context = {
            'active_model': 'account.move.line',
            'active_ids': [titulo_id],
        }

        wizard_data = {
            'payment_type': 'outbound',      # SAÍDA (pagamento a fornecedor)
            'partner_type': 'supplier',       # FORNECEDOR
            'partner_id': partner_id,
            'amount': valor_total,            # Valor total (principal + juros)
            'journal_id': journal_id,
            'payment_date': data_str,
            'communication': ref,
            'payment_difference_handling': 'reconcile',  # Marcar como totalmente pago
            'writeoff_account_id': conta_juros_id,       # Conta de juros
            'writeoff_label': 'Juros de pagamento em atraso',
        }

        # Criar wizard com contexto
        wizard_id = self.connection.execute_kw(
            'account.payment.register',
            'create',
            [wizard_data],
            {'context': wizard_context}
        )

        logger.info(f"  Wizard criado: ID={wizard_id}")

        # 2. Executar o wizard para criar o pagamento
        try:
            self.connection.execute_kw(
                'account.payment.register',
                'action_create_payments',
                [[wizard_id]],
                {'context': wizard_context}
            )
        except Exception as e:
            if "cannot marshal None" not in str(e):
                raise

        # 3. Buscar o pagamento criado pelo wizard
        payments = self.connection.execute_kw(
            'account.payment',
            'search_read',
            [[
                ['partner_id', '=', partner_id],
                ['amount', '=', valor_total],
                ['journal_id', '=', journal_id],
                ['company_id', '=', company_id],
            ]],
            {
                'fields': ['id', 'name', 'move_id', 'state'],
                'order': 'id desc',
                'limit': 1
            }
        )

        if not payments:
            raise ValueError("Pagamento não encontrado após criar via wizard")

        payment_id = payments[0]['id']
        payment_name = payments[0]['name']

        logger.info(
            f"  Pagamento OUTBOUND com Write-Off criado: "
            f"{payment_name} (ID={payment_id}, state={payments[0].get('state')})"
        )

        return payment_id, payment_name

    def postar_pagamento(self, payment_id: int) -> None:
        """
        Confirma o pagamento (state = posted).
        Nota: action_post retorna None, causando erro de serialização XML-RPC.
        Isso é esperado e deve ser ignorado.
        """
        try:
            self.connection.execute_kw(
                'account.payment',
                'action_post',
                [[payment_id]]
            )
        except Exception as e:
            # Ignorar erro de serialização - operação foi executada
            if "cannot marshal None" not in str(e):
                raise

    def buscar_linhas_payment(self, payment_id: int) -> Dict:
        """
        Busca as linhas criadas pelo payment após postar.

        Returns:
            Dict com:
            - debit_line_id: Linha de DÉBITO (liability_payable) - para reconciliar com título
            - credit_line_id: Linha de CRÉDITO (PENDENTES) - para reconciliar com extrato
        """
        linhas = self.connection.search_read(
            'account.move.line',
            [['payment_id', '=', payment_id]],
            fields=['id', 'debit', 'credit', 'account_id', 'account_type'],
            limit=10
        )

        resultado = {
            'debit_line_id': None,   # Para reconciliar com título
            'credit_line_id': None   # Para reconciliar com extrato
        }

        for linha in linhas:
            # Linha de DÉBITO na conta de FORNECEDORES (liability_payable)
            if linha.get('account_type') == 'liability_payable' and linha.get('debit', 0) > 0:
                resultado['debit_line_id'] = linha['id']

            # Linha de CRÉDITO na conta PENDENTES
            if linha.get('credit', 0) > 0:
                account_id = linha.get('account_id')
                if account_id and account_id[0] == CONTA_PAGAMENTOS_PENDENTES:
                    resultado['credit_line_id'] = linha['id']

        return resultado

    # =========================================================================
    # RECONCILIAÇÃO
    # =========================================================================

    def reconciliar(self, line1_id: int, line2_id: int) -> None:
        """
        Reconcilia duas linhas de account.move.line.
        Nota: reconcile retorna None, causando erro de serialização XML-RPC.
        Isso é esperado e deve ser ignorado.
        """
        try:
            self.connection.execute_kw(
                'account.move.line',
                'reconcile',
                [[line1_id, line2_id]]
            )
        except Exception as e:
            # Ignorar erro de serialização - operação foi executada
            if "cannot marshal None" not in str(e):
                raise

    # =========================================================================
    # ATUALIZAÇÃO DE CAMPOS DO EXTRATO (PÓS-RECONCILIAÇÃO)
    # =========================================================================

    def atualizar_statement_line_partner(self, statement_line_id: int, partner_id: int) -> bool:
        """
        Atualiza o partner_id da account.bank.statement.line no Odoo.

        Necessário porque o Odoo não mapeia automaticamente boletos
        (payment_ref genérico como "DÉB.TIT.COMPE").

        Args:
            statement_line_id: ID da account.bank.statement.line
            partner_id: ID do res.partner (fornecedor)

        Returns:
            True se atualizou, False se falhou
        """
        try:
            self.connection.execute_kw(
                'account.bank.statement.line',
                'write',
                [[statement_line_id], {'partner_id': partner_id}]
            )
            logger.info(f"  Partner atualizado na statement_line {statement_line_id}: partner_id={partner_id}")
            return True
        except Exception as e:
            logger.warning(f"  Falha ao atualizar partner da statement_line {statement_line_id}: {e}")
            return False

    def trocar_conta_move_line_extrato(self, move_id: int, conta_origem: int, conta_destino: int) -> bool:
        """
        Troca o account_id da move line do extrato.

        Necessário porque o Odoo usa CONTA_TRANSITORIA (22199) por padrão,
        mas o correto para conciliação com payment é CONTA_PAGAMENTOS_PENDENTES (26868).

        Args:
            move_id: ID do account.move do extrato
            conta_origem: ID da conta atual (22199 TRANSITÓRIA)
            conta_destino: ID da conta desejada (26868 PENDENTES)

        Returns:
            True se atualizou, False se falhou
        """
        try:
            # Buscar linha de débito na conta de origem
            linhas = self.connection.search_read(
                'account.move.line',
                [
                    ['move_id', '=', move_id],
                    ['account_id', '=', conta_origem],
                    ['debit', '>', 0]
                ],
                fields=['id'],
                limit=1
            )

            if not linhas:
                logger.warning(f"  Linha com conta {conta_origem} não encontrada no move {move_id}")
                return False

            line_id = linhas[0]['id']
            self.connection.execute_kw(
                'account.move.line',
                'write',
                [[line_id], {'account_id': conta_destino}]
            )
            logger.info(f"  Conta atualizada: move_line {line_id}, {conta_origem} → {conta_destino}")
            return True
        except Exception as e:
            logger.warning(f"  Falha ao trocar conta do extrato move {move_id}: {e}")
            return False

    def atualizar_rotulo_extrato(self, move_id: int, statement_line_id: int, rotulo: str) -> bool:
        """
        Atualiza o rótulo (name) nas move lines do extrato E payment_ref da statement line.

        Padrão correto: "Pagamento de fornecedor R$ {valor} - {fornecedor} - {data}"

        Args:
            move_id: ID do account.move do extrato
            statement_line_id: ID da account.bank.statement.line
            rotulo: Texto do rótulo formatado

        Returns:
            True se atualizou, False se falhou
        """
        try:
            # 1. Atualizar payment_ref da statement line
            self.connection.execute_kw(
                'account.bank.statement.line',
                'write',
                [[statement_line_id], {'payment_ref': rotulo}]
            )

            # 2. Atualizar name das move lines do extrato
            linhas = self.connection.search_read(
                'account.move.line',
                [['move_id', '=', move_id]],
                fields=['id'],
            )
            if linhas:
                line_ids = [l['id'] for l in linhas]
                self.connection.execute_kw(
                    'account.move.line',
                    'write',
                    [line_ids, {'name': rotulo}]
                )

            logger.info(f"  Rótulo atualizado: stmt={statement_line_id}, move={move_id}")
            return True
        except Exception as e:
            logger.warning(f"  Falha ao atualizar rótulo do extrato: {e}")
            return False

    @staticmethod
    def formatar_rotulo_pagamento(valor: float, nome_fornecedor: str, data_pagamento) -> str:
        """
        Formata o rótulo padrão para pagamentos de fornecedor.

        Padrão: "Pagamento de fornecedor R$ {valor} - {fornecedor} - {data}"

        Exemplo: "Pagamento de fornecedor R$ 657,80 - UNITECH SERVICOS - 02/02/2026"
        """
        # Formatar valor no padrão brasileiro
        valor_formatado = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        # Formatar data
        if hasattr(data_pagamento, 'strftime'):
            data_str = data_pagamento.strftime('%d/%m/%Y')
        else:
            # Se for string YYYY-MM-DD, converter
            from datetime import datetime as dt_cls
            try:
                dt = dt_cls.strptime(str(data_pagamento), '%Y-%m-%d')
                data_str = dt.strftime('%d/%m/%Y')
            except (ValueError, TypeError):
                data_str = str(data_pagamento)

        return f"Pagamento de fornecedor R$ {valor_formatado} - {nome_fornecedor} - {data_str}"

    # =========================================================================
    # SNAPSHOT
    # =========================================================================

    def capturar_snapshot(self, titulo_id: int) -> Dict:
        """Captura snapshot do título para auditoria."""
        titulo = self.buscar_titulo_por_id(titulo_id)
        return {'titulo': titulo} if titulo else {}

    # =========================================================================
    # PROCESSAMENTO DE ITEM
    # =========================================================================

    def processar_item(self, item: BaixaPagamentoItem) -> None:
        """
        Processa um item de baixa de pagamento.

        Fluxo:
        1. Buscar título no Odoo
        2. Capturar snapshot ANTES
        3. Criar payment outbound
        4. Postar payment
        5. Buscar linhas do payment
        6. Reconciliar payment com título
        7. Reconciliar payment com extrato (se houver)
        8. Capturar snapshot DEPOIS
        9. Atualizar item com resultado
        """
        logger.info(f"Processando item {item.id}: {item.nome_beneficiario} R$ {item.valor:.2f}")

        # Verificar se tem título vinculado
        if not item.titulo_id:
            raise ValueError("Item não tem título vinculado")

        # 1. Buscar título no Odoo
        titulo = self.buscar_titulo_por_id(item.titulo_id)
        if not titulo:
            raise ValueError(f"Título {item.titulo_id} não encontrado no Odoo")

        # Extrair IDs
        partner_id = titulo['partner_id'][0] if titulo['partner_id'] else None
        company_id = titulo['company_id'][0] if titulo['company_id'] else None
        move_id = titulo['move_id'][0] if titulo['move_id'] else None
        move_name = titulo['move_id'][1] if titulo['move_id'] else ''

        if not partner_id:
            raise ValueError("Título sem partner_id")
        if not company_id:
            raise ValueError("Título sem company_id")

        # Obter journal_id do lote
        lote = item.lote
        journal_id = lote.journal_id
        if not journal_id:
            raise ValueError("Lote sem journal_id definido")

        # 2. Capturar snapshot ANTES
        snapshot_antes = self.capturar_snapshot(item.titulo_id)
        item.set_snapshot_antes(snapshot_antes)
        item.saldo_antes = titulo.get('amount_residual', 0)

        # 3. Criar payment outbound
        payment_id, payment_name = self.criar_pagamento_outbound(
            partner_id=partner_id,
            valor=item.valor,
            journal_id=journal_id,
            ref=move_name,
            data=item.data_transacao,
            company_id=company_id
        )

        item.payment_id = payment_id
        item.payment_name = payment_name

        logger.info(f"  Payment criado: {payment_name} (ID: {payment_id})")

        # 4. Postar payment
        self.postar_pagamento(payment_id)
        logger.info(f"  Payment postado")

        # 5. Buscar linhas do payment
        linhas_payment = self.buscar_linhas_payment(payment_id)
        item.debit_line_id_payment = linhas_payment.get('debit_line_id')
        item.credit_line_id_payment = linhas_payment.get('credit_line_id')

        logger.info(f"  Linhas do payment: debit={item.debit_line_id_payment}, credit={item.credit_line_id_payment}")

        # 6. Reconciliar payment com título
        if item.debit_line_id_payment:
            self.reconciliar(item.debit_line_id_payment, item.titulo_id)
            logger.info(f"  Reconciliado payment com título")

            # Buscar full_reconcile_id
            titulo_atualizado = self.buscar_titulo_por_id(item.titulo_id)
            if titulo_atualizado:
                full_rec = titulo_atualizado.get('full_reconcile_id')
                if full_rec:
                    item.full_reconcile_titulo_id = full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec

        # 7. Reconciliar payment com extrato (se houver linha de extrato)
        if item.debit_line_id_extrato and item.credit_line_id_payment:
            self.reconciliar(item.credit_line_id_payment, item.debit_line_id_extrato)
            logger.info(f"  Reconciliado payment com extrato")

            # Buscar full_reconcile_id do extrato
            linha_extrato = self.connection.search_read(
                'account.move.line',
                [['id', '=', item.debit_line_id_extrato]],
                fields=['full_reconcile_id'],
                limit=1
            )
            if linha_extrato and linha_extrato[0].get('full_reconcile_id'):
                full_rec = linha_extrato[0]['full_reconcile_id']
                item.full_reconcile_extrato_id = full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec

        # 8. Capturar snapshot DEPOIS
        snapshot_depois = self.capturar_snapshot(item.titulo_id)
        item.set_snapshot_depois(snapshot_depois)

        # Atualizar saldo depois
        titulo_final = self.buscar_titulo_por_id(item.titulo_id)
        if titulo_final:
            item.saldo_depois = titulo_final.get('amount_residual', 0)

        # 9. Atualizar status
        item.status = 'SUCESSO'
        item.processado_em = datetime.utcnow()

        logger.info(f"  ✅ Item processado com sucesso! Saldo: {item.saldo_antes} -> {item.saldo_depois}")

    def processar_lote(self, lote_id: int) -> Dict:
        """
        Processa todos os itens aprovados de um lote.

        Args:
            lote_id: ID do lote

        Returns:
            Dict com estatísticas
        """
        lote = db.session.get(BaixaPagamentoLote,lote_id) if lote_id else None
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado")

        logger.info(f"=" * 60)
        logger.info(f"PROCESSANDO LOTE DE PAGAMENTOS {lote_id} - {lote.nome}")
        logger.info(f"=" * 60)

        # Buscar itens aprovados
        itens = BaixaPagamentoItem.query.filter_by(
            lote_id=lote_id,
            aprovado=True,
            status='APROVADO'
        ).all()

        logger.info(f"Itens a processar: {len(itens)}")

        lote.status = 'PROCESSANDO'
        db.session.commit()

        for item in itens:
            try:
                item.status = 'PROCESSANDO'
                db.session.commit()

                self.processar_item(item)
                self.estatisticas['sucesso'] += 1

            except Exception as e:
                logger.error(f"Erro no item {item.id}: {e}")
                item.status = 'ERRO'
                item.mensagem = str(e)[:500]
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

        logger.info(f"Lote {lote_id} concluído: {self.estatisticas}")

        return self.estatisticas
