#!/usr/bin/env python3
"""
Script de Importação de Baixas/Reconciliações do Odoo
=====================================================

Este script importa dados de baixas (pagamentos, notas de crédito, ajustes)
do Odoo para as tabelas locais, permitindo visualização no sistema.

Tabelas populadas:
1. contas_a_receber_reconciliacao - account.partial.reconcile
2. contas_a_receber_pagamento - account.payment
3. contas_a_receber_documento - account.move (notas de crédito, ajustes)
4. contas_a_receber_linha_credito - account.move.line (linhas de crédito)

Uso:
    python scripts/importar_baixas_odoo.py                    # Importar todos os títulos pagos
    python scripts/importar_baixas_odoo.py --limite 10        # Limitar a 10 títulos para teste
    python scripts/importar_baixas_odoo.py --titulo 141787    # Importar baixas de um título específico
    python scripts/importar_baixas_odoo.py --empresa 1        # Apenas empresa FB (1=FB, 2=SC, 3=CD)

Autor: Sistema de Fretes
Data: 2025-11-28
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.odoo.utils.connection import get_odoo_connection
from app.financeiro.models import (
    ContasAReceber,
    ContasAReceberReconciliacao,
    ContasAReceberPagamento,
    ContasAReceberDocumento,
    ContasAReceberLinhaCredito
)
from app.utils.timezone import agora_utc_naive, agora_brasil

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImportadorBaixasOdoo:
    """
    Importa dados de baixas/reconciliações do Odoo para as tabelas locais.
    """

    def __init__(self, connection):
        self.connection = connection
        self.estatisticas = {
            'titulos_processados': 0,
            'reconciliacoes_criadas': 0,
            'pagamentos_criados': 0,
            'documentos_criados': 0,
            'linhas_credito_criadas': 0,
            'erros': 0
        }

        # Cache para evitar duplicatas
        self._pagamentos_importados = set()
        self._documentos_importados = set()
        self._linhas_credito_importadas = set()

    def importar_titulo(self, conta: ContasAReceber) -> int:
        """
        Importa todas as baixas de um título específico.

        Returns:
            Número de reconciliações importadas
        """
        logger.info(f"\n{'─'*40}")
        logger.info(f"📋 Processando: {conta.empresa}/{conta.titulo_nf}-{conta.parcela}")

        # Buscar a linha do título no Odoo (account.move.line)
        titulo_odoo = self._buscar_titulo_odoo(conta)

        if not titulo_odoo:
            logger.warning(f"   ⚠️ Título não encontrado no Odoo")
            return 0

        matched_credit_ids = titulo_odoo.get('matched_credit_ids', [])

        if not matched_credit_ids:
            logger.info(f"   ℹ️ Sem reconciliações (matched_credit_ids vazio)")
            return 0

        logger.info(f"   📌 {len(matched_credit_ids)} reconciliações encontradas")

        # Buscar detalhes de cada reconciliação
        reconciliacoes = self._buscar_reconciliacoes(matched_credit_ids)

        for rec in reconciliacoes:
            try:
                self._processar_reconciliacao(conta, rec, titulo_odoo)
            except Exception as e:
                logger.error(f"   ❌ Erro na reconciliação {rec.get('id')}: {e}")
                self.estatisticas['erros'] += 1

        self.estatisticas['titulos_processados'] += 1
        return len(reconciliacoes)

    def _buscar_titulo_odoo(self, conta: ContasAReceber) -> Optional[Dict]:
        """Busca a linha do título no Odoo"""
        # Mapear empresa
        empresa_map = {
            1: 'FB',
            2: 'SC',
            3: 'CD'
        }
        empresa_sufixo = empresa_map.get(conta.empresa, '')

        # Buscar por NF-e e parcela
        linhas = self.connection.search_read(
            'account.move.line',
            [
                ['x_studio_nf_e', '=', conta.titulo_nf],
                ['l10n_br_cobranca_parcela', '=', int(conta.parcela) if conta.parcela.isdigit() else 0],
                ['account_type', '=', 'asset_receivable'],
                ['parent_state', '=', 'posted']
            ],
            fields=[
                'id', 'name', 'x_studio_nf_e', 'l10n_br_cobranca_parcela',
                'balance', 'amount_residual', 'debit', 'credit',
                'matched_credit_ids', 'matched_debit_ids',
                'full_reconcile_id', 'reconciled', 'l10n_br_paga',
                'company_id', 'partner_id', 'move_id'
            ],
            limit=10
        )

        if not linhas:
            return None

        # Se tiver mais de uma, filtrar pela empresa
        if len(linhas) > 1 and empresa_sufixo:
            for linha in linhas:
                company = linha.get('company_id')
                if company and isinstance(company, (list, tuple)):
                    if empresa_sufixo in company[1]:
                        return linha
            # Se não encontrar por empresa, retornar a primeira
            return linhas[0]

        return linhas[0]

    def _buscar_reconciliacoes(self, matched_credit_ids: List[int]) -> List[Dict]:
        """Busca detalhes das reconciliações no Odoo"""
        if not matched_credit_ids:
            return []

        return self.connection.search_read(
            'account.partial.reconcile',
            [['id', 'in', matched_credit_ids]],
            fields=[
                'id', 'amount', 'debit_move_id', 'credit_move_id',
                'debit_amount_currency', 'credit_amount_currency',
                'debit_currency_id', 'credit_currency_id',
                'full_reconcile_id', 'exchange_move_id',
                'max_date', 'company_id',
                'create_date', 'create_uid', 'write_date', 'write_uid'
            ],
            limit=100
        )

    def _processar_reconciliacao(self, conta: ContasAReceber, rec: Dict, titulo_odoo: Dict):
        """Processa e salva uma reconciliação"""
        odoo_id = rec.get('id')

        # Verificar se já existe
        existente = ContasAReceberReconciliacao.query.filter_by(odoo_id=odoo_id).first()
        if existente:
            logger.debug(f"      Reconciliação {odoo_id} já existe, atualizando...")
            reconciliacao = existente
        else:
            reconciliacao = ContasAReceberReconciliacao()
            reconciliacao.odoo_id = odoo_id
            reconciliacao.conta_a_receber_id = conta.id
            db.session.add(reconciliacao)

        # Preencher campos básicos
        reconciliacao.amount = rec.get('amount')
        reconciliacao.debit_move_id = self._extrair_id(rec.get('debit_move_id'))
        reconciliacao.credit_move_id = self._extrair_id(rec.get('credit_move_id'))
        reconciliacao.debit_amount_currency = rec.get('debit_amount_currency')
        reconciliacao.credit_amount_currency = rec.get('credit_amount_currency')
        reconciliacao.debit_currency = self._extrair_nome(rec.get('debit_currency_id'))
        reconciliacao.credit_currency = self._extrair_nome(rec.get('credit_currency_id'))
        reconciliacao.full_reconcile_id = self._extrair_id(rec.get('full_reconcile_id'))
        reconciliacao.exchange_move_id = self._extrair_id(rec.get('exchange_move_id'))
        reconciliacao.max_date = self._parse_date(rec.get('max_date'))
        reconciliacao.company_id = self._extrair_id(rec.get('company_id'))
        reconciliacao.company_name = self._extrair_nome(rec.get('company_id'))

        # Auditoria Odoo
        reconciliacao.odoo_create_date = self._parse_datetime(rec.get('create_date'))
        reconciliacao.odoo_create_uid = self._extrair_id(rec.get('create_uid'))
        reconciliacao.odoo_create_user = self._extrair_nome(rec.get('create_uid'))
        reconciliacao.odoo_write_date = self._parse_datetime(rec.get('write_date'))
        reconciliacao.odoo_write_uid = self._extrair_id(rec.get('write_uid'))
        reconciliacao.odoo_write_user = self._extrair_nome(rec.get('write_uid'))

        # Buscar detalhes da linha de crédito
        credit_move_id = reconciliacao.credit_move_id
        if credit_move_id:
            linha_credito = self._buscar_e_salvar_linha_credito(credit_move_id)

            if linha_credito:
                reconciliacao.credit_move_name = linha_credito.name
                reconciliacao.credit_move_ref = linha_credito.ref
                reconciliacao.tipo_baixa_odoo = linha_credito.move_type

                # Classificar tipo de baixa
                reconciliacao.tipo_baixa = self._classificar_tipo_baixa(linha_credito)

                # Se tiver payment_id, buscar pagamento
                if linha_credito.payment_id:
                    pagamento = self._buscar_e_salvar_pagamento(linha_credito.payment_id)
                    if pagamento:
                        reconciliacao.payment_id = pagamento.id

                # Buscar documento (move)
                if linha_credito.move_id:
                    documento = self._buscar_e_salvar_documento(linha_credito.move_id)
                    if documento:
                        reconciliacao.documento_id = documento.id

        reconciliacao.ultima_sincronizacao = agora_utc_naive()

        if not existente:
            self.estatisticas['reconciliacoes_criadas'] += 1

        logger.info(f"      ✅ Reconciliação {odoo_id}: R$ {reconciliacao.amount} ({reconciliacao.tipo_baixa_display})")

    def _buscar_e_salvar_linha_credito(self, odoo_id: int) -> Optional[ContasAReceberLinhaCredito]:
        """Busca e salva uma linha de crédito do Odoo"""
        if odoo_id in self._linhas_credito_importadas:
            return ContasAReceberLinhaCredito.query.filter_by(odoo_id=odoo_id).first()

        # Buscar no Odoo
        linhas = self.connection.search_read(
            'account.move.line',
            [['id', '=', odoo_id]],
            fields=[
                'id', 'name', 'ref', 'move_id', 'move_name', 'move_type',
                'balance', 'debit', 'credit', 'amount_currency', 'amount_residual',
                'currency_id', 'date', 'date_maturity',
                'account_id', 'partner_id', 'payment_id',
                'reconciled', 'full_reconcile_id', 'matching_number',
                'journal_id', 'company_id', 'parent_state',
                'create_date', 'write_date'
            ],
            limit=1
        )

        if not linhas:
            return None

        linha_odoo = linhas[0]

        # Verificar se já existe
        existente = ContasAReceberLinhaCredito.query.filter_by(odoo_id=odoo_id).first()
        if existente:
            linha = existente
        else:
            linha = ContasAReceberLinhaCredito()
            linha.odoo_id = odoo_id
            db.session.add(linha)

        # Preencher campos
        linha.name = linha_odoo.get('name')
        linha.ref = linha_odoo.get('ref')
        linha.move_id = self._extrair_id(linha_odoo.get('move_id'))
        linha.move_name = self._extrair_nome(linha_odoo.get('move_id'))
        linha.move_type = linha_odoo.get('move_type')
        linha.balance = linha_odoo.get('balance')
        linha.debit = linha_odoo.get('debit')
        linha.credit = linha_odoo.get('credit')
        linha.amount_currency = linha_odoo.get('amount_currency')
        linha.amount_residual = linha_odoo.get('amount_residual')
        linha.currency = self._extrair_nome(linha_odoo.get('currency_id'))
        linha.date = self._parse_date(linha_odoo.get('date'))
        linha.date_maturity = self._parse_date(linha_odoo.get('date_maturity'))
        linha.account_id = self._extrair_id(linha_odoo.get('account_id'))
        linha.account_name = self._extrair_nome(linha_odoo.get('account_id'))
        linha.partner_id = self._extrair_id(linha_odoo.get('partner_id'))
        linha.partner_name = self._extrair_nome(linha_odoo.get('partner_id'))
        linha.payment_id = self._extrair_id(linha_odoo.get('payment_id'))
        linha.reconciled = linha_odoo.get('reconciled', False)
        linha.full_reconcile_id = self._extrair_id(linha_odoo.get('full_reconcile_id'))
        linha.matching_number = linha_odoo.get('matching_number')
        linha.journal_id = self._extrair_id(linha_odoo.get('journal_id'))
        linha.journal_name = self._extrair_nome(linha_odoo.get('journal_id'))
        linha.company_id = self._extrair_id(linha_odoo.get('company_id'))
        linha.company_name = self._extrair_nome(linha_odoo.get('company_id'))
        linha.parent_state = linha_odoo.get('parent_state')
        linha.odoo_create_date = self._parse_datetime(linha_odoo.get('create_date'))
        linha.odoo_write_date = self._parse_datetime(linha_odoo.get('write_date'))
        linha.ultima_sincronizacao = agora_utc_naive()

        self._linhas_credito_importadas.add(odoo_id)

        if not existente:
            self.estatisticas['linhas_credito_criadas'] += 1

        return linha

    def _buscar_e_salvar_pagamento(self, odoo_id: int) -> Optional[ContasAReceberPagamento]:
        """Busca e salva um pagamento do Odoo"""
        if odoo_id in self._pagamentos_importados:
            return ContasAReceberPagamento.query.filter_by(odoo_id=odoo_id).first()

        # Buscar no Odoo
        pagamentos = self.connection.search_read(
            'account.payment',
            [['id', '=', odoo_id]],
            fields=[
                'id', 'name', 'ref', 'payment_type', 'partner_type',
                'amount', 'currency_id', 'date', 'state',
                'move_id', 'partner_id', 'journal_id',
                'reconciled_invoice_ids', 'reconciled_invoices_count',
                'payment_method_line_id', 'company_id',
                'create_date', 'create_uid', 'write_date', 'write_uid'
            ],
            limit=1
        )

        if not pagamentos:
            return None

        pag_odoo = pagamentos[0]

        # Verificar se já existe
        existente = ContasAReceberPagamento.query.filter_by(odoo_id=odoo_id).first()
        if existente:
            pagamento = existente
        else:
            pagamento = ContasAReceberPagamento()
            pagamento.odoo_id = odoo_id
            db.session.add(pagamento)

        # Preencher campos
        pagamento.name = pag_odoo.get('name')
        pagamento.ref = pag_odoo.get('ref')
        pagamento.payment_type = pag_odoo.get('payment_type')
        pagamento.partner_type = pag_odoo.get('partner_type')
        pagamento.amount = pag_odoo.get('amount')
        pagamento.currency = self._extrair_nome(pag_odoo.get('currency_id'))
        pagamento.date = self._parse_date(pag_odoo.get('date'))
        pagamento.state = pag_odoo.get('state')
        pagamento.move_id = self._extrair_id(pag_odoo.get('move_id'))
        pagamento.partner_id = self._extrair_id(pag_odoo.get('partner_id'))
        pagamento.partner_name = self._extrair_nome(pag_odoo.get('partner_id'))
        pagamento.journal_id = self._extrair_id(pag_odoo.get('journal_id'))
        pagamento.journal_name = self._extrair_nome(pag_odoo.get('journal_id'))

        # Reconciled invoices (guardar como JSON)
        rec_invoices = pag_odoo.get('reconciled_invoice_ids', [])
        if rec_invoices:
            pagamento.reconciled_invoice_ids = json.dumps(rec_invoices)
        pagamento.reconciled_invoices_count = pag_odoo.get('reconciled_invoices_count')

        pagamento.payment_method_line_id = self._extrair_id(pag_odoo.get('payment_method_line_id'))
        pagamento.company_id = self._extrair_id(pag_odoo.get('company_id'))
        pagamento.company_name = self._extrair_nome(pag_odoo.get('company_id'))
        pagamento.odoo_create_date = self._parse_datetime(pag_odoo.get('create_date'))
        pagamento.odoo_create_user = self._extrair_nome(pag_odoo.get('create_uid'))
        pagamento.odoo_write_date = self._parse_datetime(pag_odoo.get('write_date'))
        pagamento.odoo_write_user = self._extrair_nome(pag_odoo.get('write_uid'))
        pagamento.ultima_sincronizacao = agora_utc_naive()

        # Buscar CNPJ do parceiro se disponível
        if pagamento.partner_id:
            try:
                partners = self.connection.search_read(
                    'res.partner',
                    [['id', '=', pagamento.partner_id]],
                    fields=['cnpj_cpf'],
                    limit=1
                )
                if partners:
                    pagamento.partner_cnpj = partners[0].get('cnpj_cpf')
            except Exception:
                pass

        self._pagamentos_importados.add(odoo_id)

        if not existente:
            self.estatisticas['pagamentos_criados'] += 1

        return pagamento

    def _buscar_e_salvar_documento(self, odoo_id: int) -> Optional[ContasAReceberDocumento]:
        """Busca e salva um documento (account.move) do Odoo"""
        if odoo_id in self._documentos_importados:
            return ContasAReceberDocumento.query.filter_by(odoo_id=odoo_id).first()

        # Buscar no Odoo
        docs = self.connection.search_read(
            'account.move',
            [['id', '=', odoo_id]],
            fields=[
                'id', 'name', 'ref', 'move_type', 'state', 'payment_state',
                'amount_total', 'amount_residual', 'amount_untaxed', 'amount_tax',
                'currency_id', 'date', 'invoice_date',
                'partner_id', 'reversed_entry_id', 'reversal_move_id',
                'payment_id', 'journal_id', 'company_id', 'invoice_origin',
                'create_date', 'create_uid', 'write_date', 'write_uid'
            ],
            limit=1
        )

        if not docs:
            return None

        doc_odoo = docs[0]

        # Verificar se já existe
        existente = ContasAReceberDocumento.query.filter_by(odoo_id=odoo_id).first()
        if existente:
            documento = existente
        else:
            documento = ContasAReceberDocumento()
            documento.odoo_id = odoo_id
            db.session.add(documento)

        # Preencher campos
        documento.name = doc_odoo.get('name')
        documento.ref = doc_odoo.get('ref')
        documento.move_type = doc_odoo.get('move_type')
        documento.state = doc_odoo.get('state')
        documento.payment_state = doc_odoo.get('payment_state')
        documento.amount_total = doc_odoo.get('amount_total')
        documento.amount_residual = doc_odoo.get('amount_residual')
        documento.amount_untaxed = doc_odoo.get('amount_untaxed')
        documento.amount_tax = doc_odoo.get('amount_tax')
        documento.currency = self._extrair_nome(doc_odoo.get('currency_id'))
        documento.date = self._parse_date(doc_odoo.get('date'))
        documento.invoice_date = self._parse_date(doc_odoo.get('invoice_date'))
        documento.partner_id = self._extrair_id(doc_odoo.get('partner_id'))
        documento.partner_name = self._extrair_nome(doc_odoo.get('partner_id'))
        documento.reversed_entry_id = self._extrair_id(doc_odoo.get('reversed_entry_id'))

        # Reversal move IDs (guardar como JSON)
        rev_ids = doc_odoo.get('reversal_move_id', [])
        if rev_ids:
            documento.reversal_move_ids = json.dumps(rev_ids)

        documento.payment_id = self._extrair_id(doc_odoo.get('payment_id'))
        documento.journal_id = self._extrair_id(doc_odoo.get('journal_id'))
        documento.journal_name = self._extrair_nome(doc_odoo.get('journal_id'))
        documento.company_id = self._extrair_id(doc_odoo.get('company_id'))
        documento.company_name = self._extrair_nome(doc_odoo.get('company_id'))
        documento.invoice_origin = doc_odoo.get('invoice_origin')
        documento.odoo_create_date = self._parse_datetime(doc_odoo.get('create_date'))
        documento.odoo_create_user = self._extrair_nome(doc_odoo.get('create_uid'))
        documento.odoo_write_date = self._parse_datetime(doc_odoo.get('write_date'))
        documento.odoo_write_user = self._extrair_nome(doc_odoo.get('write_uid'))
        documento.ultima_sincronizacao = agora_utc_naive()

        # Buscar CNPJ do parceiro se disponível
        if documento.partner_id:
            try:
                partners = self.connection.search_read(
                    'res.partner',
                    [['id', '=', documento.partner_id]],
                    fields=['cnpj_cpf'],
                    limit=1
                )
                if partners:
                    documento.partner_cnpj = partners[0].get('cnpj_cpf')
            except Exception:
                pass

        self._documentos_importados.add(odoo_id)

        if not existente:
            self.estatisticas['documentos_criados'] += 1

        return documento

    def _classificar_tipo_baixa(self, linha_credito: ContasAReceberLinhaCredito) -> str:
        """Classifica o tipo de baixa baseado na linha de crédito"""
        move_type = linha_credito.move_type

        if linha_credito.payment_id:
            return 'pagamento'
        elif move_type == 'out_refund':
            return 'nota_credito'
        elif move_type == 'entry':
            return 'ajuste'
        else:
            return 'outro'

    # =========================================================================
    # Utilitários
    # =========================================================================

    def _extrair_id(self, valor) -> Optional[int]:
        """Extrai ID de um campo many2one do Odoo"""
        if not valor:
            return None
        if isinstance(valor, (list, tuple)) and len(valor) > 0:
            return valor[0]
        if isinstance(valor, int):
            return valor
        return None

    def _extrair_nome(self, valor) -> Optional[str]:
        """Extrai nome de um campo many2one do Odoo"""
        if not valor:
            return None
        if isinstance(valor, (list, tuple)) and len(valor) > 1:
            return str(valor[1])[:100]  # Truncar para evitar overflow
        return None

    def _parse_date(self, valor) -> Optional[datetime]:
        """Converte string de data do Odoo para date"""
        if not valor or valor is False:
            return None
        try:
            if isinstance(valor, str):
                return datetime.strptime(valor, '%Y-%m-%d').date()
            return valor
        except Exception:
            return None

    def _parse_datetime(self, valor) -> Optional[datetime]:
        """Converte string de datetime do Odoo para datetime"""
        if not valor or valor is False:
            return None
        try:
            if isinstance(valor, str):
                # Odoo pode retornar com ou sem microsegundos
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        return datetime.strptime(valor, fmt)
                    except ValueError:
                        continue
            return valor
        except Exception:
            return None


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Importa dados de baixas/reconciliações do Odoo'
    )
    parser.add_argument(
        '--limite', type=int, default=None,
        help='Limitar número de títulos para teste'
    )
    parser.add_argument(
        '--titulo', type=str, default=None,
        help='Importar baixas de um título específico (ex: 141787)'
    )
    parser.add_argument(
        '--empresa', type=int, default=None,
        help='Filtrar por empresa (1=FB, 2=SC, 3=CD)'
    )
    parser.add_argument(
        '--apenas-pagos', action='store_true',
        help='Importar apenas títulos marcados como pagos'
    )

    args = parser.parse_args()

    print("="*80)
    print("IMPORTAÇÃO DE BAIXAS/RECONCILIAÇÕES DO ODOO")
    print("="*80)
    print(f"Início: {agora_brasil().strftime('%Y-%m-%d %H:%M:%S')}")

    app = create_app()

    with app.app_context():
        # Conectar ao Odoo
        print("\n🔌 Conectando ao Odoo...")
        connection = get_odoo_connection()

        if not connection.authenticate():
            print("❌ Falha na autenticação com Odoo")
            return

        print("✅ Conectado ao Odoo!")

        # Inicializar importador
        importador = ImportadorBaixasOdoo(connection)

        # Construir query de títulos
        query = ContasAReceber.query

        if args.titulo:
            query = query.filter(ContasAReceber.titulo_nf == args.titulo)
            print(f"\n📋 Filtrando título: {args.titulo}")
        elif args.apenas_pagos:
            query = query.filter(ContasAReceber.parcela_paga == True)
            print("\n📋 Filtrando apenas títulos pagos")

        if args.empresa:
            query = query.filter(ContasAReceber.empresa == args.empresa)
            empresas = {1: 'FB', 2: 'SC', 3: 'CD'}
            print(f"📋 Filtrando empresa: {empresas.get(args.empresa, args.empresa)}")

        query = query.order_by(ContasAReceber.vencimento.desc())

        if args.limite:
            query = query.limit(args.limite)
            print(f"📋 Limitando a {args.limite} títulos")

        titulos = query.all()
        print(f"\n📊 {len(titulos)} títulos a processar")

        if not titulos:
            print("\n⚠️ Nenhum título encontrado com os filtros especificados")
            return

        # Processar cada título
        for i, titulo in enumerate(titulos, 1):
            print(f"\n[{i}/{len(titulos)}]", end="")
            try:
                importador.importar_titulo(titulo)
                db.session.commit()
            except Exception as e:
                logger.error(f"❌ Erro ao processar título {titulo.titulo_nf}: {e}")
                db.session.rollback()
                importador.estatisticas['erros'] += 1

        # Resumo final
        print("\n" + "="*80)
        print("✅ IMPORTAÇÃO CONCLUÍDA")
        print("="*80)
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   Títulos processados:      {importador.estatisticas['titulos_processados']}")
        print(f"   Reconciliações criadas:   {importador.estatisticas['reconciliacoes_criadas']}")
        print(f"   Pagamentos criados:       {importador.estatisticas['pagamentos_criados']}")
        print(f"   Documentos criados:       {importador.estatisticas['documentos_criados']}")
        print(f"   Linhas crédito criadas:   {importador.estatisticas['linhas_credito_criadas']}")
        print(f"   Erros:                    {importador.estatisticas['erros']}")
        print(f"\nFim: {agora_brasil().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
