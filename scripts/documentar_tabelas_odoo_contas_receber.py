#!/usr/bin/env python3
"""
DOCUMENTAÇÃO COMPLETA: TABELAS DO ODOO VINCULADAS AO CONTAS A RECEBER
======================================================================

Este script documenta TODAS as tabelas do Odoo relacionadas ao Contas a Receber,
listando TODOS os campos de cada uma com seus tipos, descrições e exemplos reais.

Tabelas a documentar:
1. account.move.line - Linhas de movimento (parcelas/títulos)
2. account.move - Documentos fiscais (faturas, notas de crédito)
3. account.payment - Pagamentos/Recebimentos
4. account.partial.reconcile - Reconciliações parciais
5. account.full.reconcile - Reconciliações completas

Autor: Sistema de Fretes
Data: 2025-11-28
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive


# Tabelas a documentar (ordem de dependência)
TABELAS_ODOO = [
    {
        'modelo': 'account.move.line',
        'descricao': 'Linhas de movimento contábil - onde estão as parcelas/títulos a receber',
        'dominio_exemplo': [
            ['account_type', '=', 'asset_receivable'],
            ['l10n_br_paga', '=', True],
            ['parent_state', '=', 'posted']
        ]
    },
    {
        'modelo': 'account.move',
        'descricao': 'Documentos fiscais - faturas, notas de crédito, lançamentos',
        'dominio_exemplo': [
            ['move_type', 'in', ['out_invoice', 'out_refund']],
            ['state', '=', 'posted']
        ]
    },
    {
        'modelo': 'account.payment',
        'descricao': 'Pagamentos e recebimentos registrados no sistema',
        'dominio_exemplo': [
            ['payment_type', '=', 'inbound'],
            ['state', '=', 'posted']
        ]
    },
    {
        'modelo': 'account.partial.reconcile',
        'descricao': 'Reconciliações parciais - vincula débito com crédito',
        'dominio_exemplo': []
    },
    {
        'modelo': 'account.full.reconcile',
        'descricao': 'Reconciliações completas - quando saldo = 0',
        'dominio_exemplo': []
    }
]


def buscar_todos_campos(connection, modelo: str) -> dict:
    """Busca TODOS os campos de um modelo com detalhes completos"""
    try:
        campos = connection.execute_kw(
            modelo,
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'help', 'selection', 'relation', 'required', 'readonly', 'store']}
        )
        return campos
    except Exception as e:
        print(f"❌ Erro ao buscar campos de {modelo}: {e}")
        return {}


def buscar_exemplo_registro(connection, modelo: str, dominio: list, campos_lista: list) -> dict:
    """Busca um exemplo de registro para ver valores reais"""
    try:
        # Limitar campos para evitar timeout
        campos_busca = campos_lista[:50] if len(campos_lista) > 50 else campos_lista

        registros = connection.search_read(
            modelo,
            dominio,
            fields=campos_busca,
            limit=1
        )

        if registros:
            return registros[0]
        return {}
    except Exception as e:
        print(f"⚠️ Erro ao buscar exemplo de {modelo}: {e}")
        return {}


def formatar_tipo_campo(info: dict) -> str:
    """Formata o tipo do campo para exibição"""
    tipo = info.get('type', '?')

    if tipo == 'many2one' and info.get('relation'):
        return f"many2one → {info.get('relation')}"
    elif tipo == 'one2many' and info.get('relation'):
        return f"one2many → {info.get('relation')}"
    elif tipo == 'many2many' and info.get('relation'):
        return f"many2many → {info.get('relation')}"
    elif tipo == 'selection':
        opcoes = info.get('selection', [])
        if opcoes:
            opcoes_str = ', '.join([f"{k}={v}" for k, v in opcoes[:5]])
            if len(opcoes) > 5:
                opcoes_str += f"... (+{len(opcoes)-5})"
            return f"selection [{opcoes_str}]"
        return "selection"

    return tipo


def formatar_valor_exemplo(valor, tipo: str) -> str:
    """Formata o valor de exemplo para exibição"""
    if valor is None:
        return "NULL"
    elif valor is False:
        return "False"
    elif valor is True:
        return "True"
    elif isinstance(valor, (list, tuple)):
        if len(valor) == 2 and isinstance(valor[0], int):
            # Many2one retorna [id, name]
            return f"[{valor[0]}, '{valor[1][:50]}...']" if len(str(valor[1])) > 50 else f"[{valor[0]}, '{valor[1]}']"
        elif len(valor) > 5:
            return f"[{len(valor)} itens: {valor[:3]}...]"
        return str(valor)
    elif isinstance(valor, str):
        if len(valor) > 100:
            return f"'{valor[:100]}...'"
        return f"'{valor}'"
    elif isinstance(valor, (int, float)):
        return str(valor)
    else:
        return str(valor)[:100]


def documentar_tabela(connection, tabela_info: dict, output_file) -> dict:
    """Documenta uma tabela completa"""
    modelo = tabela_info['modelo']
    descricao = tabela_info['descricao']
    dominio = tabela_info['dominio_exemplo']

    print(f"\n{'='*80}")
    print(f"📋 DOCUMENTANDO: {modelo}")
    print(f"   {descricao}")
    print('='*80)

    output_file.write(f"\n\n{'='*80}\n")
    output_file.write(f"## {modelo}\n")
    output_file.write(f"**Descrição:** {descricao}\n")
    output_file.write('='*80 + '\n\n')

    # 1. Buscar TODOS os campos
    print(f"   🔍 Buscando todos os campos...")
    campos = buscar_todos_campos(connection, modelo)

    if not campos:
        output_file.write("❌ Não foi possível obter campos deste modelo\n")
        return {'modelo': modelo, 'total_campos': 0, 'campos': {}}

    print(f"   ✅ Encontrados {len(campos)} campos")
    output_file.write(f"**Total de campos:** {len(campos)}\n\n")

    # 2. Buscar exemplo
    print(f"   🔍 Buscando exemplo de registro...")
    campos_lista = list(campos.keys())
    exemplo = buscar_exemplo_registro(connection, modelo, dominio, campos_lista)

    if exemplo:
        print(f"   ✅ Exemplo encontrado (ID: {exemplo.get('id', '?')})")
        output_file.write(f"**Exemplo encontrado:** ID = {exemplo.get('id', '?')}\n\n")
    else:
        print(f"   ⚠️ Nenhum exemplo encontrado com o domínio padrão")
        output_file.write("**Exemplo:** Nenhum registro encontrado com filtro padrão\n\n")

    # 3. Documentar cada campo
    output_file.write("### CAMPOS:\n\n")
    output_file.write("| # | Campo | Tipo | Label | Armazenado | Obrigatório | Valor Exemplo |\n")
    output_file.write("|---|-------|------|-------|------------|-------------|---------------|\n")

    resultado = {
        'modelo': modelo,
        'descricao': descricao,
        'total_campos': len(campos),
        'campos': {}
    }

    for idx, (nome_campo, info) in enumerate(sorted(campos.items()), 1):
        tipo_formatado = formatar_tipo_campo(info)
        label = info.get('string', '-')
        store = '✅' if info.get('store', True) else '❌'
        required = '✅' if info.get('required', False) else '❌'

        # Valor exemplo
        valor_exemplo = exemplo.get(nome_campo, '-') if exemplo else '-'
        valor_formatado = formatar_valor_exemplo(valor_exemplo, info.get('type', ''))

        # Truncar para tabela
        if len(valor_formatado) > 50:
            valor_formatado = valor_formatado[:47] + "..."

        # Escapar pipe para markdown
        valor_formatado = valor_formatado.replace('|', '\\|')
        label = label.replace('|', '\\|') if label else '-'

        output_file.write(f"| {idx} | `{nome_campo}` | {tipo_formatado} | {label} | {store} | {required} | {valor_formatado} |\n")

        # Guardar no resultado
        resultado['campos'][nome_campo] = {
            'tipo': info.get('type'),
            'label': info.get('string'),
            'help': info.get('help'),
            'relation': info.get('relation'),
            'selection': info.get('selection'),
            'required': info.get('required', False),
            'readonly': info.get('readonly', False),
            'store': info.get('store', True),
            'valor_exemplo': valor_exemplo if nome_campo in (exemplo or {}) else None
        }

        # Progress
        if idx % 20 == 0:
            print(f"   📝 Documentados {idx}/{len(campos)} campos...")

    print(f"   ✅ Documentados {len(campos)} campos")

    # 4. Detalhar campos com help text
    output_file.write("\n\n### DETALHAMENTO DOS CAMPOS:\n\n")

    for nome_campo, info in sorted(campos.items()):
        help_text = info.get('help', '')
        relation = info.get('relation', '')
        selection = info.get('selection', [])

        output_file.write(f"#### `{nome_campo}`\n")
        output_file.write(f"- **Label:** {info.get('string', '-')}\n")
        output_file.write(f"- **Tipo:** {formatar_tipo_campo(info)}\n")
        output_file.write(f"- **Armazenado:** {'Sim' if info.get('store', True) else 'Não (calculado)'}\n")
        output_file.write(f"- **Obrigatório:** {'Sim' if info.get('required', False) else 'Não'}\n")
        output_file.write(f"- **Somente Leitura:** {'Sim' if info.get('readonly', False) else 'Não'}\n")

        if relation:
            output_file.write(f"- **Relacionamento:** `{relation}`\n")

        if selection:
            output_file.write(f"- **Opções:** {selection}\n")

        if help_text:
            output_file.write(f"- **Descrição:** {help_text}\n")

        # Valor exemplo
        if exemplo and nome_campo in exemplo:
            valor = exemplo[nome_campo]
            output_file.write(f"- **Valor Exemplo:** `{formatar_valor_exemplo(valor, info.get('type', ''))}`\n")

        output_file.write("\n")

    return resultado


def main():
    """Função principal"""
    print("="*80)
    print("DOCUMENTAÇÃO COMPLETA: TABELAS DO ODOO - CONTAS A RECEBER")
    print("="*80)
    print(f"Iniciado em: {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}")

    app = create_app()

    # Arquivo de saída
    output_path = os.path.join(os.path.dirname(__file__), 'DOCUMENTACAO_TABELAS_ODOO_CONTAS_RECEBER.md')
    json_path = os.path.join(os.path.dirname(__file__), 'documentacao_tabelas_odoo_contas_receber.json')

    with app.app_context():
        connection = get_odoo_connection()

        if not connection.authenticate():
            print("❌ Falha na autenticação com Odoo")
            return

        print("✅ Conectado ao Odoo!")

        with open(output_path, 'w', encoding='utf-8') as f:
            # Cabeçalho do documento
            f.write("# DOCUMENTAÇÃO COMPLETA: TABELAS DO ODOO - CONTAS A RECEBER\n\n")
            f.write(f"**Data de geração:** {agora_utc_naive().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Objetivo\n")
            f.write("Documentar TODAS as tabelas do Odoo relacionadas ao Contas a Receber,\n")
            f.write("com TODOS os campos, tipos, descrições e valores de exemplo.\n\n")
            f.write("## Tabelas Documentadas\n\n")

            for t in TABELAS_ODOO:
                f.write(f"1. **{t['modelo']}** - {t['descricao']}\n")

            f.write("\n---\n")

            # Documentar cada tabela
            resultados = {}

            for tabela in TABELAS_ODOO:
                try:
                    resultado = documentar_tabela(connection, tabela, f)
                    resultados[tabela['modelo']] = resultado
                except Exception as e:
                    print(f"❌ Erro ao documentar {tabela['modelo']}: {e}")
                    f.write(f"\n\n❌ ERRO ao documentar {tabela['modelo']}: {e}\n")

            # Resumo final
            f.write("\n\n---\n")
            f.write("## RESUMO\n\n")
            f.write("| Tabela | Total Campos |\n")
            f.write("|--------|-------------|\n")

            total_geral = 0
            for modelo, dados in resultados.items():
                total = dados.get('total_campos', 0)
                total_geral += total
                f.write(f"| {modelo} | {total} |\n")

            f.write(f"| **TOTAL** | **{total_geral}** |\n")

            f.write("\n\n---\n")
            f.write("## RELACIONAMENTOS ENTRE TABELAS\n\n")
            f.write("```\n")
            f.write("account.move.line (Título/Parcela)\n")
            f.write("    ├── move_id → account.move (Documento fiscal)\n")
            f.write("    ├── payment_id → account.payment (Pagamento vinculado)\n")
            f.write("    ├── matched_credit_ids → account.partial.reconcile\n")
            f.write("    ├── matched_debit_ids → account.partial.reconcile\n")
            f.write("    └── full_reconcile_id → account.full.reconcile\n")
            f.write("\n")
            f.write("account.move (Documento Fiscal)\n")
            f.write("    ├── line_ids → account.move.line (Linhas do documento)\n")
            f.write("    └── payment_id → account.payment (Se for documento de pagamento)\n")
            f.write("\n")
            f.write("account.payment (Pagamento)\n")
            f.write("    ├── move_id → account.move (Documento contábil do pagamento)\n")
            f.write("    └── reconciled_invoice_ids → account.move (Faturas reconciliadas)\n")
            f.write("\n")
            f.write("account.partial.reconcile (Reconciliação Parcial)\n")
            f.write("    ├── debit_move_id → account.move.line (Linha de débito - título)\n")
            f.write("    ├── credit_move_id → account.move.line (Linha de crédito - pagamento)\n")
            f.write("    └── full_reconcile_id → account.full.reconcile\n")
            f.write("\n")
            f.write("account.full.reconcile (Reconciliação Completa)\n")
            f.write("    ├── partial_reconcile_ids → account.partial.reconcile\n")
            f.write("    └── reconciled_line_ids → account.move.line\n")
            f.write("```\n")

        # Salvar JSON para uso programático
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n{'='*80}")
        print(f"✅ Documentação gerada com sucesso!")
        print(f"   📄 Markdown: {output_path}")
        print(f"   📊 JSON: {json_path}")
        print('='*80)


if __name__ == '__main__':
    main()
