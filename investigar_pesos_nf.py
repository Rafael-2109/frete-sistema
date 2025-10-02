"""
Script para investigar inconsistência de pesos entre produto.product, product.template e account.move
Analisa NFs 140055 até 140064 do Odoo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
from tabulate import tabulate
import json

def conectar_odoo():
    """Conecta ao Odoo usando a conexão do sistema"""
    print("🔌 Conectando ao Odoo...")
    connection = get_odoo_connection()

    if not connection.authenticate():
        raise Exception("❌ Falha na autenticação do Odoo")

    print(f"✅ Conectado! UID: {connection._uid}")
    return connection

def buscar_faturas(connection, numeros_nf):
    """Busca faturas por número"""
    print(f"\n📋 Buscando faturas: {numeros_nf}")

    faturas = connection.search_read(
        'account.move',
        [['l10n_br_numero_nota_fiscal', 'in', numeros_nf], ['move_type', '=', 'out_invoice']],
        fields=[
            'id', 'name', 'l10n_br_numero_nota_fiscal', 'l10n_br_peso_bruto',
            'partner_id', 'invoice_line_ids', 'state'
        ]
    )

    print(f"✅ Encontradas {len(faturas)} faturas")
    return faturas

def buscar_linhas_fatura(connection, linha_ids):
    """Busca linhas da fatura"""
    if not linha_ids:
        return []

    linhas = connection.search_read(
        'account.move.line',
        [['id', 'in', linha_ids]],
        fields=[
            'id', 'product_id', 'quantity', 'price_unit',
            'price_total', 'l10n_br_total_nfe'
        ]
    )

    return linhas

def buscar_produto_completo(connection, product_id):
    """Busca dados completos do produto (variante)"""
    if not product_id:
        return {}

    produto = connection.search_read(
        'product.product',
        [['id', '=', product_id]],
        fields=[
            'id', 'default_code', 'name', 'weight',
            'product_tmpl_id', 'display_name'
        ]
    )

    return produto[0] if produto else {}

def buscar_template(connection, template_id):
    """Busca dados do template do produto"""
    if not template_id:
        return {}

    template = connection.search_read(
        'product.template',
        [['id', '=', template_id]],
        fields=[
            'id', 'name', 'default_code', 'gross_weight',
            'weight', 'volume'
        ]
    )

    return template[0] if template else {}

def analisar_nfs(numeros_nf):
    """Análise principal"""
    connection = conectar_odoo()

    # Buscar faturas
    faturas = buscar_faturas(connection, numeros_nf)

    resultados = []

    for fatura in faturas:
        nf_numero = fatura.get('l10n_br_numero_nota_fiscal', '')
        peso_bruto_nf = fatura.get('l10n_br_peso_bruto', 0)

        print(f"\n{'='*80}")
        print(f"📄 NF: {nf_numero}")
        print(f"🏷️  ID Odoo: {fatura.get('id')}")
        print(f"⚖️  Peso Bruto NF (l10n_br_peso_bruto): {peso_bruto_nf} kg")
        print(f"{'='*80}")

        # Buscar linhas da fatura
        linha_ids = fatura.get('invoice_line_ids', [])
        linhas = buscar_linhas_fatura(connection, linha_ids)

        peso_total_calculado_produto = 0  # Usando produto.weight
        peso_total_calculado_template = 0  # Usando template.gross_weight

        for linha in linhas:
            product_id = linha.get('product_id', [None])[0] if linha.get('product_id') else None
            quantidade = linha.get('quantity', 0)

            if not product_id:
                continue

            # Buscar dados do produto (variante)
            produto = buscar_produto_completo(connection, product_id)

            if not produto:
                continue

            cod_produto = produto.get('default_code', 'SEM CÓDIGO')
            peso_produto = produto.get('weight', 0)  # Peso da variante

            # Buscar dados do template
            template_id = produto.get('product_tmpl_id', [None])[0] if produto.get('product_tmpl_id') else None
            template = buscar_template(connection, template_id)

            peso_template = template.get('gross_weight', 0)  # Peso bruto do template

            # Calcular pesos
            peso_calc_produto = quantidade * peso_produto
            peso_calc_template = quantidade * peso_template

            peso_total_calculado_produto += peso_calc_produto
            peso_total_calculado_template += peso_calc_template

            # Armazenar resultado
            resultado = {
                'nf_numero': nf_numero,
                'cod_produto': cod_produto,
                'quantidade': quantidade,
                'peso_produto_weight': peso_produto,
                'peso_template_gross_weight': peso_template,
                'peso_total_usando_produto': peso_calc_produto,
                'peso_total_usando_template': peso_calc_template,
                'diferenca_pesos': abs(peso_produto - peso_template)
            }

            resultados.append(resultado)

            # Exibir linha
            print(f"\n  📦 Produto: {cod_produto}")
            print(f"     Quantidade: {quantidade}")
            print(f"     🔸 produto.weight: {peso_produto} kg → Total: {peso_calc_produto} kg")
            print(f"     🔹 template.gross_weight: {peso_template} kg → Total: {peso_calc_template} kg")

            if peso_produto != peso_template:
                print(f"     ⚠️  DIFERENÇA: {abs(peso_produto - peso_template)} kg")

        # Resumo da NF
        print(f"\n  {'─'*76}")
        print(f"  📊 RESUMO NF {nf_numero}:")
        print(f"     Peso Bruto NF (Odoo): {peso_bruto_nf} kg")
        print(f"     Soma usando produto.weight: {peso_total_calculado_produto:.2f} kg")
        print(f"     Soma usando template.gross_weight: {peso_total_calculado_template:.2f} kg")

        # Identificar qual está mais próximo
        diff_produto = abs(peso_bruto_nf - peso_total_calculado_produto)
        diff_template = abs(peso_bruto_nf - peso_total_calculado_template)

        if diff_produto < diff_template:
            print(f"     ✅ produto.weight está MAIS PRÓXIMO (diff: {diff_produto:.2f} kg)")
        elif diff_template < diff_produto:
            print(f"     ✅ template.gross_weight está MAIS PRÓXIMO (diff: {diff_template:.2f} kg)")
        else:
            print(f"     ✅ Ambos iguais!")

    return resultados

def gerar_relatorio(resultados):
    """Gera relatório consolidado"""
    print("\n\n")
    print("="*100)
    print(" 📊 RELATÓRIO CONSOLIDADO - ANÁLISE DE PESOS")
    print("="*100)

    # Agrupar por NF
    nfs = {}
    for r in resultados:
        nf = r['nf_numero']
        if nf not in nfs:
            nfs[nf] = []
        nfs[nf].append(r)

    # Tabela resumida
    tabela_resumo = []

    for nf, itens in nfs.items():
        total_prod = sum(i['peso_total_usando_produto'] for i in itens)
        total_temp = sum(i['peso_total_usando_template'] for i in itens)

        tabela_resumo.append([
            nf,
            f"{total_prod:.2f}",
            f"{total_temp:.2f}",
            f"{abs(total_prod - total_temp):.2f}"
        ])

    print("\n📋 Resumo por NF:")
    print(tabulate(
        tabela_resumo,
        headers=['NF', 'Total produto.weight', 'Total template.gross_weight', 'Diferença'],
        tablefmt='grid'
    ))

    # Produtos com diferença
    produtos_com_diff = [r for r in resultados if r['diferenca_pesos'] > 0]

    if produtos_com_diff:
        print(f"\n⚠️  {len(produtos_com_diff)} produtos com pesos diferentes:")

        tabela_diff = []
        for r in produtos_com_diff:
            tabela_diff.append([
                r['cod_produto'],
                r['nf_numero'],
                f"{r['peso_produto_weight']:.3f}",
                f"{r['peso_template_gross_weight']:.3f}",
                f"{r['diferenca_pesos']:.3f}"
            ])

        print(tabulate(
            tabela_diff,
            headers=['Produto', 'NF', 'produto.weight', 'template.gross_weight', 'Diferença'],
            tablefmt='grid'
        ))

    # Salvar JSON para análise
    with open('analise_pesos_nf.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print("\n💾 Dados salvos em: analise_pesos_nf.json")

if __name__ == '__main__':
    # NFs para analisar
    numeros_nf = [str(i) for i in range(140055, 140065)]  # 140055 até 140064

    print("🔍 INVESTIGAÇÃO DE PESOS - ODOO")
    print(f"📋 NFs: {', '.join(numeros_nf)}")

    try:
        resultados = analisar_nfs(numeros_nf)
        gerar_relatorio(resultados)

        print("\n✅ Análise concluída com sucesso!")

    except Exception as e:
        print(f"\n❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()
