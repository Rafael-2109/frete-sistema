#!/usr/bin/env python3
"""
ANÁLISE COMPLETA DE BAIXA DE TÍTULOS DE RECEBIMENTO NO ODOO
============================================================

Este script captura o estado COMPLETO de um título de recebimento e todas as
suas entidades relacionadas, permitindo comparação antes/depois de baixas.

OBJETIVO:
- Identificar o comportamento nos MICRO DETALHES da baixa de título de recebimento
- Capturar TODOS os campos de TODAS as tabelas relacionadas
- Permitir comparação antes/depois para identificar campos alterados
- Inferir métodos on_change através da análise de mudanças

CENÁRIOS DE BAIXA:
1. Pagamento Parcial do Título - Título recebe valor menor que total
2. Quitação do Título - Título é quitado 100%, outros da NF pendentes
3. Quitação da NF - Todos os títulos da NF são quitados

TABELAS ANALISADAS:
- account.move.line - Títulos/parcelas (PRINCIPAL)
- account.move - Documentos fiscais
- account.payment - Pagamentos registrados
- account.partial.reconcile - Reconciliações parciais
- account.full.reconcile - Reconciliações completas
- account.bank.statement - Extratos bancários
- account.bank.statement.line - Linhas de extrato
- l10n_br_ciel_it_account.dados.pagamento - Dados CNAB
- ir.model.fields - Metadados de campos (compute, depends)

Autor: Sistema de Fretes - Análise de Baixas
Data: 2025-12-10
"""

import sys
import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive


# ============================================================================
# CONFIGURAÇÃO DE TABELAS A ANALISAR
# ============================================================================

TABELAS_BAIXA_TITULO = [
    {
        'modelo': 'res.company',
        'descricao': 'Empresas do grupo - Para identificar IDs',
        'dominio_padrao': [],
        'relevancia': 'auxiliar',
        'campos_chave': ['id', 'name', 'partner_id', 'currency_id']
    },
    {
        'modelo': 'account.move.line',
        'descricao': 'Linhas de movimento contábil - TÍTULOS/PARCELAS (PRINCIPAL)',
        'dominio_padrao': [
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted']
        ],
        'relevancia': 'critica',
        'campos_chave': [
            'id', 'name', 'move_id', 'partner_id', 'account_id',
            'debit', 'credit', 'balance', 'amount_currency',
            'amount_residual', 'amount_residual_currency',
            'date', 'date_maturity', 'reconciled',
            'full_reconcile_id', 'matched_debit_ids', 'matched_credit_ids',
            'payment_id', 'company_id',
            # Campos brasileiros críticos
            'l10n_br_paga', 'l10n_br_cobranca_nossonumero',
            'l10n_br_cobranca_situacao', 'l10n_br_cobranca_protocolo'
        ]
    },
    {
        'modelo': 'account.move',
        'descricao': 'Documentos fiscais - Faturas, notas de crédito',
        'dominio_padrao': [
            ['move_type', 'in', ['out_invoice', 'out_refund']],
            ['state', '=', 'posted']
        ],
        'relevancia': 'critica',
        'campos_chave': [
            'id', 'name', 'ref', 'move_type', 'state', 'partner_id',
            'amount_total', 'amount_residual', 'amount_untaxed',
            'payment_state', 'invoice_date', 'invoice_date_due',
            'line_ids', 'invoice_line_ids', 'payment_id',
            'company_id', 'journal_id'
        ]
    },
    {
        'modelo': 'account.payment',
        'descricao': 'Pagamentos e recebimentos registrados',
        'dominio_padrao': [
            ['payment_type', '=', 'inbound'],
            ['state', '=', 'posted']
        ],
        'relevancia': 'critica',
        'campos_chave': [
            'id', 'name', 'payment_type', 'partner_type', 'state',
            'amount', 'currency_id', 'partner_id', 'date',
            'move_id', 'journal_id', 'company_id',
            'reconciled_invoice_ids', 'reconciled_bill_ids',
            'paired_internal_transfer_payment_id'
        ]
    },
    {
        'modelo': 'account.partial.reconcile',
        'descricao': 'Reconciliações parciais - Vincula débito com crédito',
        'dominio_padrao': [],
        'relevancia': 'critica',
        'campos_chave': [
            'id', 'debit_move_id', 'credit_move_id',
            'debit_amount_currency', 'credit_amount_currency',
            'amount', 'debit_currency_id', 'credit_currency_id',
            'company_id', 'full_reconcile_id', 'create_date'
        ]
    },
    {
        'modelo': 'account.full.reconcile',
        'descricao': 'Reconciliações completas - Quando saldo = 0',
        'dominio_padrao': [],
        'relevancia': 'critica',
        'campos_chave': [
            'id', 'name', 'partial_reconcile_ids', 'reconciled_line_ids',
            'create_date', 'exchange_move_id'
        ]
    },
    {
        'modelo': 'account.bank.statement',
        'descricao': 'Extratos bancários - Conciliação',
        'dominio_padrao': [],
        'relevancia': 'alta',
        'campos_chave': [
            'id', 'name', 'date', 'journal_id', 'company_id',
            'balance_start', 'balance_end', 'balance_end_real',
            'line_ids', 'state'
        ]
    },
    {
        'modelo': 'account.bank.statement.line',
        'descricao': 'Linhas de extrato bancário - Movimentos',
        'dominio_padrao': [],
        'relevancia': 'alta',
        'campos_chave': [
            'id', 'statement_id', 'sequence', 'date', 'payment_ref',
            'partner_id', 'amount', 'amount_currency', 'currency_id',
            'move_id', 'is_reconciled', 'company_id', 'journal_id'
        ]
    },
    {
        'modelo': 'l10n_br_ciel_it_account.dados.pagamento',
        'descricao': 'Dados de pagamento CNAB brasileiro',
        'dominio_padrao': [],
        'relevancia': 'alta',
        'campos_chave': ['id']  # Todos os campos serão buscados
    },
    {
        'modelo': 'ir.model.fields',
        'descricao': 'Metadados de campos - compute, depends, related',
        'dominio_padrao': [
            ['model', 'in', [
                'account.move.line', 'account.move', 'account.payment',
                'account.partial.reconcile', 'account.full.reconcile'
            ]]
        ],
        'relevancia': 'metadados',
        'campos_chave': [
            'id', 'name', 'model', 'ttype', 'field_description',
            'compute', 'depends', 'related', 'store', 'readonly',
            'required', 'relation', 'on_delete'
        ]
    }
]


class SnapshotTituloRecebimento:
    """Classe para capturar e comparar snapshots de títulos de recebimento"""

    def __init__(self):
        self.app = create_app()
        self.connection = None
        self.empresas = {}
        self.metadados_campos = {}
        self.output_dir = os.path.dirname(__file__)

    def conectar(self) -> bool:
        """Estabelece conexão com Odoo"""
        with self.app.app_context():
            self.connection = get_odoo_connection()
            if not self.connection.authenticate():
                print("❌ Falha na autenticação com Odoo")
                return False
            print("✅ Conectado ao Odoo!")
            return True

    def descobrir_empresas(self) -> Dict[int, str]:
        """Descobre todas as empresas do grupo no Odoo"""
        print("\n" + "="*80)
        print("🏢 DESCOBRINDO EMPRESAS DO GRUPO")
        print("="*80)

        with self.app.app_context():
            empresas = self.connection.search_read(
                'res.company',
                [],
                fields=['id', 'name', 'partner_id', 'currency_id', 'l10n_br_cnpj']
            )

            self.empresas = {}
            for emp in empresas:
                self.empresas[emp['id']] = {
                    'name': emp['name'],
                    'partner_id': emp.get('partner_id'),
                    'currency_id': emp.get('currency_id'),
                    'l10n_br_cnpj': emp.get('l10n_br_cnpj')
                }
                print(f"   ID {emp['id']}: {emp['name']}")
                if emp.get('l10n_br_cnpj'):
                    print(f"          CNPJ: {emp['l10n_br_cnpj']}")

            return self.empresas

    def buscar_todos_campos_modelo(self, modelo: str) -> Dict[str, Any]:
        """Busca TODOS os campos de um modelo com metadados expandidos"""
        with self.app.app_context():
            try:
                campos = self.connection.execute_kw(
                    modelo,
                    'fields_get',
                    [],
                    {'attributes': [
                        'string', 'type', 'help', 'selection', 'relation',
                        'required', 'readonly', 'store', 'compute', 'depends',
                        'related', 'inverse', 'default', 'domain', 'context',
                        'groups', 'copy', 'index', 'group_operator'
                    ]}
                )
                return campos
            except Exception as e:
                print(f"❌ Erro ao buscar campos de {modelo}: {e}")
                return {}

    def buscar_metadados_campos_ir_model(self, modelos: List[str]) -> Dict[str, Dict]:
        """Busca metadados de campos via ir.model.fields (compute, depends)"""
        print("\n" + "="*80)
        print("📋 BUSCANDO METADADOS DE CAMPOS (ir.model.fields)")
        print("="*80)

        with self.app.app_context():
            try:
                campos_meta = self.connection.search_read(
                    'ir.model.fields',
                    [['model', 'in', modelos]],
                    fields=[
                        'name', 'model', 'ttype', 'field_description',
                        'compute', 'depends', 'related', 'store', 'readonly',
                        'required', 'relation', 'on_delete', 'selection_ids'
                    ]
                )

                resultado = {}
                for campo in campos_meta:
                    modelo = campo['model']
                    nome = campo['name']

                    if modelo not in resultado:
                        resultado[modelo] = {}

                    resultado[modelo][nome] = {
                        'ttype': campo.get('ttype'),
                        'field_description': campo.get('field_description'),
                        'compute': campo.get('compute'),
                        'depends': campo.get('depends'),
                        'related': campo.get('related'),
                        'store': campo.get('store'),
                        'readonly': campo.get('readonly'),
                        'required': campo.get('required'),
                        'relation': campo.get('relation')
                    }

                # Estatísticas
                for modelo, campos in resultado.items():
                    computados = sum(1 for c in campos.values() if c.get('compute'))
                    relacionados = sum(1 for c in campos.values() if c.get('related'))
                    print(f"   {modelo}: {len(campos)} campos ({computados} compute, {relacionados} related)")

                self.metadados_campos = resultado
                return resultado

            except Exception as e:
                print(f"❌ Erro ao buscar metadados: {e}")
                return {}

    def buscar_titulo_por_id(self, titulo_id: int) -> Optional[Dict]:
        """Busca um título específico pelo ID"""
        with self.app.app_context():
            titulos = self.connection.search_read(
                'account.move.line',
                [['id', '=', titulo_id]],
                fields=None  # Todos os campos
            )
            return titulos[0] if titulos else None

    def buscar_titulo_por_criterio(self, partner_name: str = None,
                                    nosso_numero: str = None,
                                    move_name: str = None,
                                    company_id: int = None) -> List[Dict]:
        """Busca títulos por critérios diversos"""
        domain = [
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted']
        ]

        if partner_name:
            domain.append(['partner_id.name', 'ilike', partner_name])
        if nosso_numero:
            domain.append(['l10n_br_cobranca_nossonumero', '=', nosso_numero])
        if move_name:
            domain.append(['move_id.name', 'ilike', move_name])
        if company_id:
            domain.append(['company_id', '=', company_id])

        with self.app.app_context():
            titulos = self.connection.search_read(
                'account.move.line',
                domain,
                fields=[
                    'id', 'name', 'move_id', 'partner_id',
                    'debit', 'credit', 'balance',
                    'amount_residual', 'date_maturity',
                    'reconciled', 'l10n_br_cobranca_nossonumero',
                    'l10n_br_paga', 'company_id'
                ],
                limit=50
            )
            return titulos

    def snapshot_titulo_completo(self, titulo_id: int,
                                  descricao: str = "",
                                  salvar: bool = True) -> Dict[str, Any]:
        """
        Captura snapshot COMPLETO de um título e todas as entidades relacionadas

        Args:
            titulo_id: ID do account.move.line (título)
            descricao: Descrição do momento do snapshot (ex: "antes_baixa_parcial")
            salvar: Se True, salva em arquivo JSON

        Returns:
            Dicionário com todos os dados capturados
        """
        print("\n" + "="*80)
        print(f"📸 CAPTURANDO SNAPSHOT COMPLETO DO TÍTULO ID {titulo_id}")
        print(f"   Descrição: {descricao or 'Não informada'}")
        print("="*80)

        snapshot = {
            'meta': {
                'titulo_id': titulo_id,
                'descricao': descricao,
                'timestamp': agora_utc_naive().isoformat(),
                'versao_script': '1.0.0'
            },
            'entidades': {}
        }

        with self.app.app_context():
            # 1. TÍTULO PRINCIPAL (account.move.line)
            print("\n1️⃣ Buscando TÍTULO PRINCIPAL (account.move.line)...")
            titulo = self.connection.read('account.move.line', [titulo_id])
            if not titulo:
                print(f"❌ Título ID {titulo_id} não encontrado!")
                return None

            titulo = titulo[0]
            snapshot['entidades']['account.move.line'] = {
                titulo_id: titulo
            }
            print(f"   ✅ Título encontrado: {titulo.get('name')} | Saldo: {titulo.get('amount_residual')}")

            # 2. DOCUMENTO FISCAL (account.move)
            move_id = titulo.get('move_id')
            if move_id:
                move_id = move_id[0] if isinstance(move_id, (list, tuple)) else move_id
                print(f"\n2️⃣ Buscando DOCUMENTO FISCAL (account.move) ID {move_id}...")
                move = self.connection.read('account.move', [move_id])
                if move:
                    snapshot['entidades']['account.move'] = {move_id: move[0]}
                    print(f"   ✅ Documento: {move[0].get('name')} | Estado Pgto: {move[0].get('payment_state')}")

                    # Buscar TODAS as linhas do documento (outros títulos da mesma NF)
                    line_ids = move[0].get('line_ids', [])
                    if line_ids:
                        print(f"\n   2.1️⃣ Buscando TODAS as {len(line_ids)} linhas do documento...")
                        all_lines = self.connection.read('account.move.line', line_ids)
                        for line in all_lines:
                            snapshot['entidades']['account.move.line'][line['id']] = line

                        # Estatísticas das linhas
                        recebiveis = [l for l in all_lines if l.get('account_type') == 'asset_receivable']
                        print(f"   ✅ {len(recebiveis)} linhas a receber encontradas")

            # 3. PAGAMENTO VINCULADO (account.payment)
            payment_id = titulo.get('payment_id')
            if payment_id:
                payment_id = payment_id[0] if isinstance(payment_id, (list, tuple)) else payment_id
                print(f"\n3️⃣ Buscando PAGAMENTO VINCULADO (account.payment) ID {payment_id}...")
                payment = self.connection.read('account.payment', [payment_id])
                if payment:
                    snapshot['entidades']['account.payment'] = {payment_id: payment[0]}
                    print(f"   ✅ Pagamento: {payment[0].get('name')} | Valor: {payment[0].get('amount')}")
            else:
                snapshot['entidades']['account.payment'] = {}

            # 4. RECONCILIAÇÕES PARCIAIS (account.partial.reconcile)
            print(f"\n4️⃣ Buscando RECONCILIAÇÕES PARCIAIS...")
            matched_debit_ids = titulo.get('matched_debit_ids', [])
            matched_credit_ids = titulo.get('matched_credit_ids', [])
            all_partial_ids = list(set(matched_debit_ids + matched_credit_ids))

            if all_partial_ids:
                partials = self.connection.read('account.partial.reconcile', all_partial_ids)
                snapshot['entidades']['account.partial.reconcile'] = {
                    p['id']: p for p in partials
                }
                print(f"   ✅ {len(partials)} reconciliações parciais encontradas")
                for p in partials:
                    print(f"      - ID {p['id']}: Valor {p.get('amount')} | Débito: {p.get('debit_move_id')} → Crédito: {p.get('credit_move_id')}")
            else:
                snapshot['entidades']['account.partial.reconcile'] = {}
                print(f"   ⚠️ Nenhuma reconciliação parcial encontrada")

            # 5. RECONCILIAÇÃO COMPLETA (account.full.reconcile)
            full_reconcile_id = titulo.get('full_reconcile_id')
            if full_reconcile_id:
                full_id = full_reconcile_id[0] if isinstance(full_reconcile_id, (list, tuple)) else full_reconcile_id
                print(f"\n5️⃣ Buscando RECONCILIAÇÃO COMPLETA (account.full.reconcile) ID {full_id}...")
                full = self.connection.read('account.full.reconcile', [full_id])
                if full:
                    snapshot['entidades']['account.full.reconcile'] = {full_id: full[0]}
                    print(f"   ✅ Reconciliação completa: {full[0].get('name')}")
            else:
                snapshot['entidades']['account.full.reconcile'] = {}
                print(f"\n5️⃣ ⚠️ Título NÃO possui reconciliação completa (não quitado)")

            # 6. EXTRATO BANCÁRIO (se houver)
            print(f"\n6️⃣ Buscando LINHAS DE EXTRATO relacionadas...")
            # Buscar por linhas de extrato que podem estar vinculadas ao pagamento ou ao move
            statement_lines = []
            if payment_id:
                # Buscar linhas de extrato vinculadas ao pagamento
                stmt_lines = self.connection.search_read(
                    'account.bank.statement.line',
                    [['move_id.payment_id', '=', payment_id]],
                    fields=None,
                    limit=10
                )
                statement_lines.extend(stmt_lines)

            if statement_lines:
                snapshot['entidades']['account.bank.statement.line'] = {
                    sl['id']: sl for sl in statement_lines
                }
                print(f"   ✅ {len(statement_lines)} linhas de extrato encontradas")

                # Buscar os extratos relacionados
                stmt_ids = list(set(
                    sl['statement_id'][0] if isinstance(sl.get('statement_id'), (list, tuple)) else sl.get('statement_id')
                    for sl in statement_lines if sl.get('statement_id')
                ))
                if stmt_ids:
                    stmts = self.connection.read('account.bank.statement', stmt_ids)
                    snapshot['entidades']['account.bank.statement'] = {
                        s['id']: s for s in stmts
                    }
            else:
                snapshot['entidades']['account.bank.statement.line'] = {}
                snapshot['entidades']['account.bank.statement'] = {}
                print(f"   ⚠️ Nenhuma linha de extrato encontrada")

            # 7. DADOS CNAB BRASILEIRO
            print(f"\n7️⃣ Buscando DADOS CNAB (l10n_br_ciel_it_account.dados.pagamento)...")
            try:
                dados_pag_ids = titulo.get('l10n_br_dados_pagamento_id', [])
                if dados_pag_ids:
                    dados_pag = self.connection.read('l10n_br_ciel_it_account.dados.pagamento', dados_pag_ids)
                    snapshot['entidades']['l10n_br_ciel_it_account.dados.pagamento'] = {
                        dp['id']: dp for dp in dados_pag
                    }
                    print(f"   ✅ {len(dados_pag)} registros CNAB encontrados")
                else:
                    snapshot['entidades']['l10n_br_ciel_it_account.dados.pagamento'] = {}
                    print(f"   ⚠️ Nenhum dado CNAB encontrado")
            except Exception as e:
                print(f"   ⚠️ Erro ao buscar dados CNAB: {e}")
                snapshot['entidades']['l10n_br_ciel_it_account.dados.pagamento'] = {}

            # Calcular hash do snapshot para identificação única
            snapshot_str = json.dumps(snapshot, sort_keys=True, default=str)
            snapshot['meta']['hash'] = hashlib.md5(snapshot_str.encode()).hexdigest()[:12]

            # Estatísticas finais
            print("\n" + "-"*80)
            print("📊 RESUMO DO SNAPSHOT:")
            total_registros = 0
            for modelo, dados in snapshot['entidades'].items():
                count = len(dados)
                total_registros += count
                print(f"   {modelo}: {count} registros")
            print(f"   TOTAL: {total_registros} registros capturados")
            print(f"   HASH: {snapshot['meta']['hash']}")

            # Salvar se solicitado
            if salvar:
                self._salvar_snapshot(snapshot, descricao)

            return snapshot

    def _salvar_snapshot(self, snapshot: Dict, descricao: str):
        """Salva snapshot em arquivo JSON"""
        titulo_id = snapshot['meta']['titulo_id']
        timestamp = agora_utc_naive().strftime('%Y%m%d_%H%M%S')
        descricao_safe = descricao.replace(' ', '_').replace('/', '-') if descricao else 'snapshot'

        filename = f"snapshot_titulo_{titulo_id}_{descricao_safe}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, 'snapshots', filename)

        # Criar diretório se não existir
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n💾 Snapshot salvo em: {filepath}")
        return filepath

    def comparar_snapshots(self, snapshot_antes: Dict, snapshot_depois: Dict) -> Dict:
        """
        Compara dois snapshots e identifica todas as diferenças

        Returns:
            Dicionário com análise detalhada das diferenças
        """
        print("\n" + "="*80)
        print("🔍 COMPARANDO SNAPSHOTS")
        print("="*80)
        print(f"   ANTES:  {snapshot_antes['meta'].get('descricao')} ({snapshot_antes['meta'].get('timestamp')})")
        print(f"   DEPOIS: {snapshot_depois['meta'].get('descricao')} ({snapshot_depois['meta'].get('timestamp')})")

        diferencas = {
            'meta': {
                'titulo_id': snapshot_antes['meta']['titulo_id'],
                'antes': {
                    'descricao': snapshot_antes['meta'].get('descricao'),
                    'timestamp': snapshot_antes['meta'].get('timestamp'),
                    'hash': snapshot_antes['meta'].get('hash')
                },
                'depois': {
                    'descricao': snapshot_depois['meta'].get('descricao'),
                    'timestamp': snapshot_depois['meta'].get('timestamp'),
                    'hash': snapshot_depois['meta'].get('hash')
                }
            },
            'campos_alterados': {},
            'registros_novos': {},
            'registros_removidos': {},
            'resumo': {
                'total_campos_alterados': 0,
                'total_registros_novos': 0,
                'total_registros_removidos': 0
            }
        }

        # Analisar cada modelo
        for modelo in set(list(snapshot_antes['entidades'].keys()) + list(snapshot_depois['entidades'].keys())):
            dados_antes = snapshot_antes['entidades'].get(modelo, {})
            dados_depois = snapshot_depois['entidades'].get(modelo, {})

            ids_antes = set(dados_antes.keys())
            ids_depois = set(dados_depois.keys())

            # Registros novos
            ids_novos = ids_depois - ids_antes
            if ids_novos:
                diferencas['registros_novos'][modelo] = {
                    rid: dados_depois[rid] for rid in ids_novos
                }
                diferencas['resumo']['total_registros_novos'] += len(ids_novos)
                print(f"\n   ➕ {modelo}: {len(ids_novos)} registros NOVOS: {list(ids_novos)}")

            # Registros removidos
            ids_removidos = ids_antes - ids_depois
            if ids_removidos:
                diferencas['registros_removidos'][modelo] = {
                    rid: dados_antes[rid] for rid in ids_removidos
                }
                diferencas['resumo']['total_registros_removidos'] += len(ids_removidos)
                print(f"\n   ➖ {modelo}: {len(ids_removidos)} registros REMOVIDOS: {list(ids_removidos)}")

            # Campos alterados em registros existentes
            ids_comuns = ids_antes & ids_depois
            for rid in ids_comuns:
                reg_antes = dados_antes[rid]
                reg_depois = dados_depois[rid]

                campos_diferentes = []
                for campo in set(list(reg_antes.keys()) + list(reg_depois.keys())):
                    val_antes = reg_antes.get(campo)
                    val_depois = reg_depois.get(campo)

                    # Normalizar para comparação
                    if val_antes != val_depois:
                        campos_diferentes.append({
                            'campo': campo,
                            'antes': val_antes,
                            'depois': val_depois
                        })

                if campos_diferentes:
                    if modelo not in diferencas['campos_alterados']:
                        diferencas['campos_alterados'][modelo] = {}

                    diferencas['campos_alterados'][modelo][rid] = campos_diferentes
                    diferencas['resumo']['total_campos_alterados'] += len(campos_diferentes)

                    print(f"\n   🔄 {modelo} ID {rid}: {len(campos_diferentes)} campos alterados:")
                    for diff in campos_diferentes[:10]:  # Limitar output
                        print(f"      • {diff['campo']}: {diff['antes']} → {diff['depois']}")
                    if len(campos_diferentes) > 10:
                        print(f"      ... e mais {len(campos_diferentes) - 10} campos")

        # Resumo final
        print("\n" + "-"*80)
        print("📊 RESUMO DAS DIFERENÇAS:")
        print(f"   Total de campos alterados: {diferencas['resumo']['total_campos_alterados']}")
        print(f"   Total de registros novos: {diferencas['resumo']['total_registros_novos']}")
        print(f"   Total de registros removidos: {diferencas['resumo']['total_registros_removidos']}")

        return diferencas

    def analisar_causa_alteracao(self, diferencas: Dict) -> Dict:
        """
        Tenta inferir a causa de cada alteração baseado nos metadados de campos
        """
        print("\n" + "="*80)
        print("🔬 ANALISANDO CAUSAS DAS ALTERAÇÕES")
        print("="*80)

        analise = {
            'campos_computados': [],
            'campos_relacionados': [],
            'campos_manuais': [],
            'inferencias': []
        }

        for modelo, registros in diferencas.get('campos_alterados', {}).items():
            meta_modelo = self.metadados_campos.get(modelo, {})

            for rid, campos in registros.items():
                for diff in campos:
                    campo_nome = diff['campo']
                    meta_campo = meta_modelo.get(campo_nome, {})

                    info = {
                        'modelo': modelo,
                        'registro_id': rid,
                        'campo': campo_nome,
                        'antes': diff['antes'],
                        'depois': diff['depois'],
                        'compute': meta_campo.get('compute'),
                        'depends': meta_campo.get('depends'),
                        'related': meta_campo.get('related'),
                        'tipo_alteracao': 'desconhecido'
                    }

                    # Classificar tipo de alteração
                    if meta_campo.get('compute'):
                        info['tipo_alteracao'] = 'computado'
                        info['inferencia'] = f"Campo computado via: {meta_campo.get('compute')}"
                        if meta_campo.get('depends'):
                            info['inferencia'] += f" | Depende de: {meta_campo.get('depends')}"
                        analise['campos_computados'].append(info)

                    elif meta_campo.get('related'):
                        info['tipo_alteracao'] = 'relacionado'
                        info['inferencia'] = f"Campo relacionado: {meta_campo.get('related')}"
                        analise['campos_relacionados'].append(info)

                    else:
                        info['tipo_alteracao'] = 'manual_ou_trigger'
                        info['inferencia'] = "Alterado diretamente ou via trigger/onchange"
                        analise['campos_manuais'].append(info)

        # Gerar inferências
        if analise['campos_computados']:
            print(f"\n   📐 {len(analise['campos_computados'])} campos COMPUTADOS alterados:")
            for c in analise['campos_computados'][:5]:
                print(f"      • {c['modelo']}.{c['campo']}: {c['inferencia']}")

        if analise['campos_relacionados']:
            print(f"\n   🔗 {len(analise['campos_relacionados'])} campos RELACIONADOS alterados:")
            for c in analise['campos_relacionados'][:5]:
                print(f"      • {c['modelo']}.{c['campo']}: {c['inferencia']}")

        if analise['campos_manuais']:
            print(f"\n   ✋ {len(analise['campos_manuais'])} campos MANUAIS/TRIGGER alterados:")
            for c in analise['campos_manuais'][:5]:
                print(f"      • {c['modelo']}.{c['campo']}: {c['antes']} → {c['depois']}")

        return analise

    def documentar_campos_modelo(self, modelo: str, output_file: str = None) -> Dict:
        """Documenta TODOS os campos de um modelo com metadados expandidos"""
        print(f"\n📋 Documentando campos de {modelo}...")

        with self.app.app_context():
            campos = self.buscar_todos_campos_modelo(modelo)

            if not campos:
                print(f"❌ Nenhum campo encontrado para {modelo}")
                return {}

            resultado = {
                'modelo': modelo,
                'total_campos': len(campos),
                'campos': campos,
                'estatisticas': {
                    'computados': 0,
                    'relacionados': 0,
                    'armazenados': 0,
                    'obrigatorios': 0
                }
            }

            # Estatísticas
            for nome, info in campos.items():
                if info.get('compute'):
                    resultado['estatisticas']['computados'] += 1
                if info.get('related'):
                    resultado['estatisticas']['relacionados'] += 1
                if info.get('store', True):
                    resultado['estatisticas']['armazenados'] += 1
                if info.get('required'):
                    resultado['estatisticas']['obrigatorios'] += 1

            print(f"   Total: {resultado['total_campos']} campos")
            print(f"   Computados: {resultado['estatisticas']['computados']}")
            print(f"   Relacionados: {resultado['estatisticas']['relacionados']}")
            print(f"   Armazenados: {resultado['estatisticas']['armazenados']}")
            print(f"   Obrigatórios: {resultado['estatisticas']['obrigatorios']}")

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)
                print(f"   💾 Salvo em: {output_file}")

            return resultado

    def gerar_documentacao_completa(self):
        """Gera documentação completa de todas as tabelas relacionadas a baixas"""
        print("\n" + "="*80)
        print("📚 GERANDO DOCUMENTAÇÃO COMPLETA DE TABELAS")
        print("="*80)

        output_dir = os.path.join(self.output_dir, 'documentacao')
        os.makedirs(output_dir, exist_ok=True)

        modelos_principais = [
            'account.move.line',
            'account.move',
            'account.payment',
            'account.partial.reconcile',
            'account.full.reconcile',
            'account.bank.statement',
            'account.bank.statement.line'
        ]

        with self.app.app_context():
            # Buscar metadados via ir.model.fields
            self.buscar_metadados_campos_ir_model(modelos_principais)

            # Documentar cada modelo
            documentacao = {}
            for modelo in modelos_principais:
                output_file = os.path.join(output_dir, f'{modelo.replace(".", "_")}_campos.json')
                doc = self.documentar_campos_modelo(modelo, output_file)
                documentacao[modelo] = doc

            # Gerar resumo consolidado
            resumo_path = os.path.join(output_dir, 'RESUMO_TABELAS_BAIXA.json')
            with open(resumo_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'gerado_em': agora_utc_naive().isoformat(),
                    'modelos': {
                        m: {
                            'total_campos': d.get('total_campos', 0),
                            'estatisticas': d.get('estatisticas', {})
                        }
                        for m, d in documentacao.items()
                    },
                    'metadados_ir_model': self.metadados_campos
                }, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n💾 Resumo salvo em: {resumo_path}")
            return documentacao

    def listar_titulos_pendentes(self, company_id: int = None, limit: int = 20) -> List[Dict]:
        """Lista títulos pendentes (não quitados) para seleção"""
        print("\n" + "="*80)
        print("📋 LISTANDO TÍTULOS PENDENTES (NÃO QUITADOS)")
        print("="*80)

        domain = [
            ['account_type', '=', 'asset_receivable'],
            ['parent_state', '=', 'posted'],
            ['reconciled', '=', False],
            ['amount_residual', '>', 0]
        ]

        if company_id:
            domain.append(['company_id', '=', company_id])
            print(f"   Filtro: Empresa ID {company_id}")

        with self.app.app_context():
            titulos = self.connection.search_read(
                'account.move.line',
                domain,
                fields=[
                    'id', 'name', 'move_id', 'partner_id',
                    'debit', 'credit', 'balance',
                    'amount_residual', 'date_maturity',
                    'l10n_br_cobranca_nossonumero',
                    'l10n_br_paga', 'company_id'
                ],
                limit=limit
            )

            print(f"\n   Encontrados {len(titulos)} títulos pendentes:\n")
            print(f"   {'ID':<10} {'Documento':<20} {'Cliente':<30} {'Valor':<15} {'Saldo':<15} {'Vencimento':<12}")
            print("   " + "-"*110)

            for t in titulos:
                partner = t.get('partner_id', [0, 'N/A'])
                partner_name = partner[1][:28] if isinstance(partner, (list, tuple)) else str(partner)[:28]
                move = t.get('move_id', [0, 'N/A'])
                move_name = move[1][:18] if isinstance(move, (list, tuple)) else str(move)[:18]

                print(f"   {t['id']:<10} {move_name:<20} {partner_name:<30} {t.get('balance', 0):>13.2f} {t.get('amount_residual', 0):>13.2f} {str(t.get('date_maturity', '')):<12}")

            return titulos


def menu_interativo():
    """Menu interativo para operações"""
    print("\n" + "="*80)
    print("🔧 ANÁLISE DE BAIXA DE TÍTULOS - MENU INTERATIVO")
    print("="*80)
    print("""
    1. Descobrir empresas do grupo
    2. Gerar documentação completa de tabelas
    3. Listar títulos pendentes
    4. Capturar snapshot de título (ANTES da baixa)
    5. Capturar snapshot de título (DEPOIS da baixa)
    6. Comparar dois snapshots
    7. Sair
    """)

    snapshot = SnapshotTituloRecebimento()

    if not snapshot.conectar():
        return

    while True:
        opcao = input("\nEscolha uma opção (1-7): ").strip()

        if opcao == '1':
            snapshot.descobrir_empresas()

        elif opcao == '2':
            snapshot.gerar_documentacao_completa()

        elif opcao == '3':
            company_id = input("ID da empresa (Enter para todas): ").strip()
            company_id = int(company_id) if company_id else None
            snapshot.listar_titulos_pendentes(company_id)

        elif opcao == '4':
            titulo_id = input("ID do título: ").strip()
            if titulo_id:
                descricao = input("Descrição (ex: antes_baixa_parcial): ").strip()
                snapshot.snapshot_titulo_completo(int(titulo_id), descricao or "antes_baixa")

        elif opcao == '5':
            titulo_id = input("ID do título: ").strip()
            if titulo_id:
                descricao = input("Descrição (ex: depois_baixa_parcial): ").strip()
                snapshot.snapshot_titulo_completo(int(titulo_id), descricao or "depois_baixa")

        elif opcao == '6':
            print("\n📁 Arquivos de snapshot disponíveis:")
            snapshots_dir = os.path.join(snapshot.output_dir, 'snapshots')
            if os.path.exists(snapshots_dir):
                files = sorted([f for f in os.listdir(snapshots_dir) if f.endswith('.json')])
                for i, f in enumerate(files, 1):
                    print(f"   {i}. {f}")

                idx_antes = input("\nNúmero do snapshot ANTES: ").strip()
                idx_depois = input("Número do snapshot DEPOIS: ").strip()

                if idx_antes and idx_depois:
                    try:
                        with open(os.path.join(snapshots_dir, files[int(idx_antes)-1]), 'r') as f:
                            snap_antes = json.load(f)
                        with open(os.path.join(snapshots_dir, files[int(idx_depois)-1]), 'r') as f:
                            snap_depois = json.load(f)

                        diferencas = snapshot.comparar_snapshots(snap_antes, snap_depois)

                        # Salvar diferenças
                        diff_file = os.path.join(snapshots_dir, f"diferencas_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.json")
                        with open(diff_file, 'w', encoding='utf-8') as f:
                            json.dump(diferencas, f, indent=2, ensure_ascii=False, default=str)
                        print(f"\n💾 Diferenças salvas em: {diff_file}")

                        # Analisar causas
                        if diferencas['resumo']['total_campos_alterados'] > 0:
                            snapshot.analisar_causa_alteracao(diferencas)

                    except Exception as e:
                        print(f"❌ Erro ao comparar: {e}")
            else:
                print("   Nenhum snapshot encontrado. Capture snapshots primeiro.")

        elif opcao == '7':
            print("\n👋 Saindo...")
            break

        else:
            print("❌ Opção inválida!")


def main():
    """Função principal - execução direta"""
    import argparse

    parser = argparse.ArgumentParser(description='Análise de Baixa de Títulos de Recebimento')
    parser.add_argument('--empresas', action='store_true', help='Listar empresas do grupo')
    parser.add_argument('--documentar', action='store_true', help='Gerar documentação completa')
    parser.add_argument('--pendentes', type=int, nargs='?', const=0, help='Listar títulos pendentes (opcional: ID empresa)')
    parser.add_argument('--snapshot', type=int, help='ID do título para snapshot')
    parser.add_argument('--descricao', type=str, default='', help='Descrição do snapshot')
    parser.add_argument('--interativo', action='store_true', help='Modo interativo')

    args = parser.parse_args()

    # Se nenhum argumento, modo interativo
    if not any([args.empresas, args.documentar, args.pendentes is not None, args.snapshot, args.interativo]):
        args.interativo = True

    if args.interativo:
        menu_interativo()
        return

    snapshot = SnapshotTituloRecebimento()
    if not snapshot.conectar():
        return

    if args.empresas:
        snapshot.descobrir_empresas()

    if args.documentar:
        snapshot.gerar_documentacao_completa()

    if args.pendentes is not None:
        company_id = args.pendentes if args.pendentes > 0 else None
        snapshot.listar_titulos_pendentes(company_id)

    if args.snapshot:
        snapshot.snapshot_titulo_completo(args.snapshot, args.descricao)


if __name__ == '__main__':
    main()
