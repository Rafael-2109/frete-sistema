#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consulta Financeiro - Contas a Pagar/Receber no Odoo

Skill: consultando-odoo-financeiro
Modelos: account.move, account.move.line
"""

import argparse
import json
import sys
import os
from datetime import date, timedelta

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from typing import Dict, Any, List


# ==============================================================================
# CONFIGURACAO DOS MODELOS
# ==============================================================================

MODELO_CONFIG = {
    'financeiro': {
        'modelo': 'account.move',
        'modelo_linha': 'account.move.line',
        'campos_principais': [
            'id',
            'name',                      # Numero documento
            'ref',                       # Referencia
            'move_type',                 # Tipo (in_invoice, out_invoice, etc)
            'state',                     # Status (draft, posted, cancel)
            'payment_state',             # Status pagamento
            'partner_id',                # Parceiro
            'date',                      # Data contabil
            'invoice_date',              # Data fatura
            'invoice_date_due',          # Data vencimento
            'amount_total',              # Valor total
            'amount_untaxed',            # Valor sem impostos
            'amount_tax',                # Total impostos
            'amount_residual',           # Valor em aberto
            'amount_paid',               # Valor pago
            'currency_id',               # Moeda
            'company_id',                # Empresa
        ],
        'campos_brasileiros': [
            'l10n_br_cnpj',              # CNPJ
            'l10n_br_chave_nf',          # Chave NF-e
            'l10n_br_serie_nf',          # Serie NF
            'l10n_br_situacao_nf',       # Situacao NF
            'l10n_br_total_nfe',         # Total NF
            'l10n_br_prod_valor',        # Total produtos
            'l10n_br_frete',             # Total frete
            'l10n_br_total_tributos',    # Total tributos
        ],
        'campos_linha': [
            'id',
            'name',                      # Descricao
            'move_id',                   # Documento pai
            'partner_id',                # Parceiro
            'account_id',                # Conta contabil
            'date',                      # Data
            'date_maturity',             # Data vencimento
            'debit',                     # Debito
            'credit',                    # Credito
            'balance',                   # Saldo
            'amount_residual',           # Valor em aberto
            'amount_currency',           # Valor moeda estrangeira
        ],
        'campos_linha_cobranca': [
            'l10n_br_cobranca_nossonumero',   # Nosso numero
            'l10n_br_cobranca_situacao',      # Situacao cobranca
            'l10n_br_cobranca_parcela',       # Numero parcela
            'l10n_br_paga',                   # Parcela paga?
        ],
    }
}


# ==============================================================================
# FUNCOES AUXILIARES
# ==============================================================================

def get_odoo_connection():
    """Obtem conexao com Odoo usando integracao existente."""
    from app.odoo.utils.connection import get_odoo_connection as get_conn
    return get_conn()


def extrair_nome_many2one(valor):
    """Extrai nome de um campo many2one (retorna tupla [id, nome])."""
    if valor and isinstance(valor, (list, tuple)) and len(valor) > 1:
        return valor[1]
    return valor if isinstance(valor, str) else ''


def formatar_valor(valor):
    """Formata valor monetario."""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def traduzir_move_type(move_type):
    """Traduz move_type para portugues."""
    tipos = {
        'out_invoice': 'Fatura Cliente (A Receber)',
        'out_refund': 'Nota Credito Cliente',
        'in_invoice': 'Fatura Fornecedor (A Pagar)',
        'in_refund': 'Nota Credito Fornecedor',
        'entry': 'Lancamento Contabil',
    }
    return tipos.get(move_type, move_type)


def traduzir_state(state):
    """Traduz state para portugues."""
    estados = {
        'draft': 'Rascunho',
        'posted': 'Lancado',
        'cancel': 'Cancelado',
    }
    return estados.get(state, state)


def traduzir_payment_state(payment_state):
    """Traduz payment_state para portugues."""
    estados = {
        'not_paid': 'Nao Pago',
        'partial': 'Parcial',
        'paid': 'Pago',
        'in_payment': 'Em Pagamento',
        'reversed': 'Estornado',
    }
    return estados.get(payment_state, payment_state or 'N/A')


# ==============================================================================
# FUNCAO PRINCIPAL DE CONSULTA
# ==============================================================================

def consultar_financeiro(args) -> Dict[str, Any]:
    """Consulta documentos financeiros no Odoo."""
    resultado = {
        'sucesso': False,
        'tipo': 'financeiro',
        'subtipo': args.subtipo,
        'total': 0,
        'documentos': [],
        'resumo': {},
        'erro': None
    }

    try:
        odoo = get_odoo_connection()
        config = MODELO_CONFIG['financeiro']

        # Montar filtros base
        filtros = [('state', '=', 'posted')]  # Apenas documentos lancados

        # Filtrar por subtipo
        if args.subtipo == 'a-pagar':
            filtros.append(('move_type', 'in', ['in_invoice', 'in_refund']))
            filtros.append(('payment_state', 'in', ['not_paid', 'partial']))
        elif args.subtipo == 'a-receber':
            filtros.append(('move_type', 'in', ['out_invoice', 'out_refund']))
            filtros.append(('payment_state', 'in', ['not_paid', 'partial']))
        elif args.subtipo == 'vencidos':
            hoje = date.today().isoformat()
            filtros.append(('invoice_date_due', '<', hoje))
            filtros.append(('payment_state', 'in', ['not_paid', 'partial']))
        elif args.subtipo == 'a-vencer':
            hoje = date.today().isoformat()
            filtros.append(('invoice_date_due', '>=', hoje))
            filtros.append(('payment_state', 'in', ['not_paid', 'partial']))

        # Filtrar por parceiro (nome)
        if args.parceiro:
            filtros.append(('partner_id.name', 'ilike', args.parceiro))

        # Filtrar por CNPJ
        if args.cnpj:
            cnpj_limpo = args.cnpj.replace('.', '').replace('/', '').replace('-', '')
            filtros.append(('l10n_br_cnpj', 'ilike', cnpj_limpo))

        # Filtrar por vencimento (ate)
        if args.vencimento_ate:
            filtros.append(('invoice_date_due', '<=', args.vencimento_ate))

        # Filtrar por vencimento (de)
        if args.vencimento_de:
            filtros.append(('invoice_date_due', '>=', args.vencimento_de))

        # Filtrar por valor minimo
        if getattr(args, 'valor_min', None):
            filtros.append(('amount_residual', '>=', args.valor_min))

        # Filtrar por valor maximo
        if getattr(args, 'valor_max', None):
            filtros.append(('amount_residual', '<=', args.valor_max))

        # Filtrar por estado
        if getattr(args, 'estado', None):
            filtros.append(('state', '=', args.estado))

        # Filtrar por pagamento
        if getattr(args, 'pagamento', None):
            filtros.append(('payment_state', '=', args.pagamento))

        # Filtrar por dias de atraso
        if getattr(args, 'dias_atraso', None):
            data_limite = (date.today() - timedelta(days=args.dias_atraso)).isoformat()
            filtros.append(('invoice_date_due', '<', data_limite))
            filtros.append(('payment_state', 'in', ['not_paid', 'partial']))

        # Montar lista de campos a buscar
        campos_busca = list(config['campos_principais'])

        # Incluir campos brasileiros se detalhes
        if getattr(args, 'detalhes', False):
            campos_busca.extend(config['campos_brasileiros'])

        # Executar busca
        documentos = odoo.search_read(
            config['modelo'],
            filtros,
            fields=campos_busca,
            limit=args.limit or 100
        )

        # Se pediu detalhes, buscar linhas
        if getattr(args, 'detalhes', False):
            campos_linha = list(config['campos_linha'])
            campos_linha.extend(config['campos_linha_cobranca'])

            for doc in documentos:
                # Buscar linhas do tipo receivable/payable (parcelas)
                linhas = odoo.search_read(
                    config['modelo_linha'],
                    [
                        ('move_id', '=', doc['id']),
                        ('amount_residual', '!=', 0),  # Apenas parcelas com saldo
                    ],
                    fields=campos_linha,
                    limit=50
                )
                doc['parcelas'] = linhas

        # Calcular resumo se solicitado
        if getattr(args, 'resumo', False):
            total_documentos = len(documentos)
            valor_total = sum(doc.get('amount_total', 0) or 0 for doc in documentos)
            valor_pago = sum(doc.get('amount_paid', 0) or 0 for doc in documentos)
            valor_aberto = sum(doc.get('amount_residual', 0) or 0 for doc in documentos)

            # Calcular vencidos
            hoje = date.today().isoformat()
            valor_vencido = sum(
                doc.get('amount_residual', 0) or 0
                for doc in documentos
                if (doc.get('invoice_date_due') or '') < hoje
            )

            resultado['resumo'] = {
                'total_documentos': total_documentos,
                'valor_total': valor_total,
                'valor_pago': valor_pago,
                'valor_aberto': valor_aberto,
                'valor_vencido': valor_vencido,
            }

        resultado['sucesso'] = True
        resultado['total'] = len(documentos)
        resultado['documentos'] = documentos

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Consulta financeiro no Odoo (contas a pagar/receber)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Contas a pagar pendentes
  python consulta.py --tipo financeiro --subtipo a-pagar

  # Contas a pagar de um fornecedor
  python consulta.py --tipo financeiro --subtipo a-pagar --parceiro "atacadao"

  # Contas a receber vencidas
  python consulta.py --tipo financeiro --subtipo vencidos

  # Parcelas vencendo esta semana
  python consulta.py --tipo financeiro --subtipo a-vencer --vencimento-ate 2025-12-07

  # Titulos com mais de 30 dias de atraso
  python consulta.py --tipo financeiro --subtipo vencidos --dias-atraso 30

  # Buscar por CNPJ com detalhes
  python consulta.py --tipo financeiro --cnpj "18467441" --detalhes

  # Resumo de inadimplencia
  python consulta.py --tipo financeiro --subtipo vencidos --resumo
        """
    )

    # Argumentos obrigatorios
    parser.add_argument('--tipo', required=True, choices=['financeiro'],
                        help='Tipo de consulta')

    # Subtipos
    parser.add_argument('--subtipo', default='todos',
                        choices=['a-pagar', 'a-receber', 'vencidos', 'a-vencer', 'todos'],
                        help='Subtipo: a-pagar, a-receber, vencidos, a-vencer, todos')

    # Filtros basicos
    parser.add_argument('--parceiro', help='Nome do parceiro (busca parcial)')
    parser.add_argument('--cnpj', help='CNPJ do parceiro (busca parcial)')
    parser.add_argument('--vencimento-de', help='Data inicial vencimento (YYYY-MM-DD)')
    parser.add_argument('--vencimento-ate', help='Data final vencimento (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados')

    # Filtros avancados
    parser.add_argument('--valor-min', type=float, help='Valor minimo em aberto')
    parser.add_argument('--valor-max', type=float, help='Valor maximo em aberto')
    parser.add_argument('--estado', choices=['draft', 'posted', 'cancel'],
                        help='Status do documento')
    parser.add_argument('--pagamento', choices=['not_paid', 'partial', 'paid', 'in_payment'],
                        help='Status de pagamento')
    parser.add_argument('--dias-atraso', type=int, help='Minimo de dias em atraso')

    # Opcoes de saida
    parser.add_argument('--detalhes', action='store_true',
                        help='Incluir parcelas/linhas e campos brasileiros')
    parser.add_argument('--resumo', action='store_true',
                        help='Mostrar apenas totalizadores')
    parser.add_argument('--json', action='store_true', help='Saida em JSON')

    args = parser.parse_args()

    # Executar consulta
    resultado = consultar_financeiro(args)

    # Formatar saida
    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    else:
        if resultado['sucesso']:
            subtipo_nome = {
                'a-pagar': 'CONTAS A PAGAR',
                'a-receber': 'CONTAS A RECEBER',
                'vencidos': 'VENCIDOS',
                'a-vencer': 'A VENCER',
                'todos': 'TODOS'
            }.get(args.subtipo, args.subtipo.upper())

            print(f"\n=== {subtipo_nome} ===")
            print(f"Total encontrado: {resultado['total']}")

            # Mostrar resumo se solicitado
            if args.resumo and resultado['resumo']:
                r = resultado['resumo']
                print(f"\n--- RESUMO ---")
                print(f"Documentos: {r['total_documentos']}")
                print(f"Valor Total: {formatar_valor(r['valor_total'])}")
                print(f"Valor Pago: {formatar_valor(r['valor_pago'])}")
                print(f"Valor em Aberto: {formatar_valor(r['valor_aberto'])}")
                print(f"Valor Vencido: {formatar_valor(r['valor_vencido'])}")
                print()
            else:
                print()

                for doc in resultado['documentos'][:20]:
                    nome = doc.get('name') or 'S/N'
                    parceiro = extrair_nome_many2one(doc.get('partner_id'))
                    tipo = traduzir_move_type(doc.get('move_type'))
                    vencimento = doc.get('invoice_date_due') or 'N/A'
                    valor_total = doc.get('amount_total') or 0
                    valor_aberto = doc.get('amount_residual') or 0
                    state = traduzir_state(doc.get('state'))
                    payment = traduzir_payment_state(doc.get('payment_state'))

                    print(f"[{doc['id']}] {nome}")
                    print(f"  Parceiro: {parceiro}")
                    print(f"  Tipo: {tipo}")
                    print(f"  Vencimento: {vencimento}")
                    print(f"  Valor Total: {formatar_valor(valor_total)} | Em Aberto: {formatar_valor(valor_aberto)}")
                    print(f"  Status: {state} | Pagamento: {payment}")

                    # CNPJ se disponivel
                    cnpj = doc.get('l10n_br_cnpj')
                    if cnpj:
                        print(f"  CNPJ: {cnpj}")

                    # Chave NF se disponivel
                    chave = doc.get('l10n_br_chave_nf')
                    if chave:
                        print(f"  Chave NF: {chave}")

                    # Parcelas se detalhes solicitado
                    if 'parcelas' in doc and doc['parcelas']:
                        print(f"  Parcelas ({len(doc['parcelas'])}):")
                        for parc in doc['parcelas'][:5]:
                            venc = parc.get('date_maturity') or 'N/A'
                            valor = parc.get('amount_residual') or 0
                            nosso_num = parc.get('l10n_br_cobranca_nossonumero') or ''
                            situacao = parc.get('l10n_br_cobranca_situacao') or ''
                            paga = parc.get('l10n_br_paga', False)

                            info_extra = []
                            if nosso_num:
                                info_extra.append(f"NN:{nosso_num}")
                            if situacao:
                                info_extra.append(situacao)
                            if paga:
                                info_extra.append("PAGA")

                            extra_str = f" ({', '.join(info_extra)})" if info_extra else ""
                            print(f"    - Venc: {venc} | {formatar_valor(valor)}{extra_str}")

                        if len(doc['parcelas']) > 5:
                            print(f"    ... e mais {len(doc['parcelas']) - 5} parcela(s)")

                    print()

                if resultado['total'] > 20:
                    print(f"... e mais {resultado['total'] - 20} documento(s)")
        else:
            print(f"\nERRO: {resultado['erro']}")


if __name__ == '__main__':
    main()
