#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relatório de DFE (Documentos Fiscais Eletrônicos) do Odoo

Extrai relatório completo de DFEs com:
- Número NF, CNPJ, Nome do fornecedor, Data
- Produtos (código, descrição, NCM)
- Quantidade, Preço unitário, Valor total
- PO vinculado

Autor: Sistema de Fretes
Data: 16/01/2026
"""

import sys
import os
import argparse
import json
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


def get_odoo_connection():
    """Obtém conexão com Odoo."""
    from app.odoo.utils.connection import get_odoo_connection as get_conn
    return get_conn()


def extrair_dfe_completo(odoo, data_inicio: str, data_fim: str = None, limit: int = None) -> Dict[str, Any]:
    """
    Extrai DFEs com todos os detalhes solicitados.

    Args:
        odoo: Conexão Odoo
        data_inicio: Data inicial (YYYY-MM-DD)
        data_fim: Data final (YYYY-MM-DD), opcional
        limit: Limite de DFEs a buscar

    Returns:
        Dict com resultados estruturados
    """
    resultado = {
        'data_extracao': datetime.now().isoformat(),
        'periodo': {'inicio': data_inicio, 'fim': data_fim or 'atual'},
        'total_dfes': 0,
        'total_itens': 0,
        'dfes': [],
        'itens_flat': [],  # Formato tabular para Excel
        'sucesso': False,
        'erro': None
    }

    try:
        # Filtros para DFE
        filtros = [
            ('nfe_infnfe_ide_dhemi', '>=', f'{data_inicio} 00:00:00'),
        ]
        if data_fim:
            filtros.append(('nfe_infnfe_ide_dhemi', '<=', f'{data_fim} 23:59:59'))

        # Buscar DFEs (cabeçalho)
        print(f"Buscando DFEs desde {data_inicio}...")

        campos_dfe = [
            'id',
            'nfe_infnfe_ide_nnf',           # Número NF
            'nfe_infnfe_ide_serie',         # Série
            'nfe_infnfe_emit_cnpj',         # CNPJ Emitente
            'nfe_infnfe_emit_xnome',        # Razão Social Emitente
            'nfe_infnfe_ide_dhemi',         # Data Emissão
            'nfe_infnfe_total_icmstot_vnf', # Valor Total NF
            'nfe_infnfe_total_icmstot_vprod', # Valor Produtos
            'nfe_infnfe_ide_finnfe',        # Finalidade (1=Normal, 4=Devolução)
            'purchase_id',                   # PO vinculado
            'lines_ids',                     # IDs das linhas
            'protnfe_infnfe_chnfe',         # Chave NF-e
            'is_cte',                        # Se é CT-e
        ]

        # Usar execute_kw para ter acesso ao parâmetro order
        kwargs = {'fields': campos_dfe}
        if limit:
            kwargs['limit'] = limit
        kwargs['order'] = 'nfe_infnfe_ide_dhemi desc'

        dfes = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'search_read',
            [filtros],
            kwargs
        )

        print(f"Encontrados {len(dfes)} DFE(s)")
        resultado['total_dfes'] = len(dfes)

        # Para cada DFE, buscar os itens
        for idx, dfe in enumerate(dfes):
            if (idx + 1) % 50 == 0:
                print(f"Processando DFE {idx + 1}/{len(dfes)}...")

            # Informações do cabeçalho
            dfe_info = {
                'id': dfe['id'],
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf'),
                'serie': dfe.get('nfe_infnfe_ide_serie'),
                'cnpj': dfe.get('nfe_infnfe_emit_cnpj'),
                'fornecedor': dfe.get('nfe_infnfe_emit_xnome'),
                'data_emissao': dfe.get('nfe_infnfe_ide_dhemi'),
                'valor_total_nf': dfe.get('nfe_infnfe_total_icmstot_vnf'),
                'valor_produtos': dfe.get('nfe_infnfe_total_icmstot_vprod'),
                'finalidade': dfe.get('nfe_infnfe_ide_finnfe'),
                'chave_nfe': dfe.get('protnfe_infnfe_chnfe'),
                'is_cte': dfe.get('is_cte', False),
                'po': None,
                'po_name': None,
                'itens': []
            }

            # PO vinculado
            if dfe.get('purchase_id'):
                po_data = dfe['purchase_id']
                if isinstance(po_data, (list, tuple)) and len(po_data) >= 2:
                    dfe_info['po'] = po_data[0]
                    dfe_info['po_name'] = po_data[1]
                elif isinstance(po_data, int):
                    dfe_info['po'] = po_data

            # Buscar itens do DFE
            if dfe.get('lines_ids'):
                campos_linha = [
                    'id',
                    'det_prod_cprod',       # Código do Produto
                    'det_prod_xprod',       # Descrição do Produto
                    'det_prod_ncm',         # NCM
                    'det_prod_cfop',        # CFOP
                    'det_prod_qcom',        # Quantidade
                    'det_prod_ucom',        # Unidade de Medida
                    'det_prod_vuncom',      # Valor Unitário
                    'det_prod_vprod',       # Valor Total do Item
                    'det_prod_vdesc',       # Desconto
                    'det_prod_xped',        # Pedido Cliente
                    'det_prod_nitemped',    # Item Pedido Cliente
                    'purchase_id',          # PO vinculado na linha
                    'purchase_line_id',     # Linha do PO
                    'product_id',           # Produto Odoo
                ]

                linhas = odoo.search_read(
                    'l10n_br_ciel_it_account.dfe.line',
                    [('id', 'in', dfe['lines_ids'])],
                    fields=campos_linha
                )

                for linha in linhas:
                    item_info = {
                        'id': linha['id'],
                        'codigo_produto': linha.get('det_prod_cprod'),
                        'descricao': linha.get('det_prod_xprod'),
                        'ncm': linha.get('det_prod_ncm'),
                        'cfop': linha.get('det_prod_cfop'),
                        'quantidade': linha.get('det_prod_qcom'),
                        'unidade': linha.get('det_prod_ucom'),
                        'preco_unitario': linha.get('det_prod_vuncom'),
                        'valor_total': linha.get('det_prod_vprod'),
                        'desconto': linha.get('det_prod_vdesc'),
                        'pedido_cliente': linha.get('det_prod_xped'),
                        'item_pedido': linha.get('det_prod_nitemped'),
                        'po_linha': None,
                        'product_id': None
                    }

                    # PO na linha (pode ser diferente do cabeçalho)
                    if linha.get('purchase_id'):
                        po_linha = linha['purchase_id']
                        if isinstance(po_linha, (list, tuple)) and len(po_linha) >= 2:
                            item_info['po_linha'] = po_linha[1]
                        elif isinstance(po_linha, int):
                            item_info['po_linha'] = po_linha

                    # Produto Odoo
                    if linha.get('product_id'):
                        prod = linha['product_id']
                        if isinstance(prod, (list, tuple)) and len(prod) >= 2:
                            item_info['product_id'] = f"{prod[0]} - {prod[1]}"

                    dfe_info['itens'].append(item_info)
                    resultado['total_itens'] += 1

                    # Formato flat (tabular) para Excel
                    flat_item = {
                        # Dados do DFE
                        'dfe_id': dfe_info['id'],
                        'numero_nf': dfe_info['numero_nf'],
                        'serie': dfe_info['serie'],
                        'cnpj': dfe_info['cnpj'],
                        'fornecedor': dfe_info['fornecedor'],
                        'data_emissao': dfe_info['data_emissao'],
                        'valor_total_nf': dfe_info['valor_total_nf'],
                        'finalidade': dfe_info['finalidade'],
                        'po_dfe': dfe_info['po_name'],
                        'chave_nfe': dfe_info['chave_nfe'],
                        # Dados do Item
                        'item_id': item_info['id'],
                        'codigo_produto': item_info['codigo_produto'],
                        'descricao': item_info['descricao'],
                        'ncm': item_info['ncm'],
                        'cfop': item_info['cfop'],
                        'quantidade': item_info['quantidade'],
                        'unidade': item_info['unidade'],
                        'preco_unitario': item_info['preco_unitario'],
                        'valor_item': item_info['valor_total'],
                        'desconto': item_info['desconto'],
                        'po_item': item_info['po_linha'] or dfe_info['po_name'],
                    }
                    resultado['itens_flat'].append(flat_item)

            resultado['dfes'].append(dfe_info)

        resultado['sucesso'] = True
        print(f"\nExtração concluída: {resultado['total_dfes']} DFE(s), {resultado['total_itens']} item(ns)")

    except Exception as e:
        resultado['erro'] = str(e)
        import traceback
        resultado['traceback'] = traceback.format_exc()
        print(f"ERRO: {e}")

    return resultado


def formatar_resumo(resultado: Dict[str, Any]) -> str:
    """Formata resumo para exibição."""
    linhas = [
        "=" * 70,
        "RELATÓRIO DE DFE - RESUMO",
        "=" * 70,
        f"Período: {resultado['periodo']['inicio']} a {resultado['periodo']['fim']}",
        f"Data extração: {resultado['data_extracao']}",
        f"Total de DFEs: {resultado['total_dfes']}",
        f"Total de Itens: {resultado['total_itens']}",
        "=" * 70,
    ]

    if resultado['sucesso'] and resultado['dfes']:
        linhas.append("\nÚLTIMOS 10 DFEs:")
        linhas.append("-" * 70)

        for dfe in resultado['dfes'][:10]:
            data_raw = dfe.get('data_emissao')
            data = data_raw[:10] if data_raw and isinstance(data_raw, str) else 'N/A'
            valor_raw = dfe.get('valor_total_nf')
            valor = f"R$ {valor_raw:,.2f}" if valor_raw and isinstance(valor_raw, (int, float)) else 'N/A'
            po = dfe.get('po_name') or 'Sem PO'
            fornecedor = dfe.get('fornecedor') or 'N/A'
            if isinstance(fornecedor, str) and len(fornecedor) > 30:
                fornecedor = fornecedor[:30]
            cnpj = dfe.get('cnpj') or 'N/A'
            numero_nf = dfe.get('numero_nf') or 'N/A'
            serie = dfe.get('serie') or '1'

            linhas.append(f"NF {numero_nf}/{serie} | {cnpj} | {fornecedor}")
            linhas.append(f"   Data: {data} | Valor: {valor} | PO: {po} | Itens: {len(dfe.get('itens', []))}")
            linhas.append("")

    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(
        description='Extrai relatório de DFE do Odoo com itens e PO vinculado',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Extrair DFEs desde 01/01/2025
  python relatorio_dfe.py --inicio 2025-01-01

  # Extrair DFEs de um período específico
  python relatorio_dfe.py --inicio 2025-01-01 --fim 2025-01-31

  # Extrair e salvar em JSON
  python relatorio_dfe.py --inicio 2025-01-01 --json --output dfe_report.json

  # Extrair formato tabular para Excel (via skill exportando-arquivos)
  python relatorio_dfe.py --inicio 2025-01-01 --excel

  # Limitar quantidade
  python relatorio_dfe.py --inicio 2025-01-01 --limit 100
        """
    )

    parser.add_argument('--inicio', required=True, help='Data inicial (YYYY-MM-DD)')
    parser.add_argument('--fim', help='Data final (YYYY-MM-DD), opcional')
    parser.add_argument('--limit', type=int, help='Limite de DFEs a buscar')
    parser.add_argument('--json', action='store_true', help='Saída em JSON')
    parser.add_argument('--excel', action='store_true', help='Saída em formato tabular (para Excel)')
    parser.add_argument('--output', '-o', help='Arquivo de saída')

    args = parser.parse_args()

    # Conectar ao Odoo
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("ERRO: Falha na autenticação com Odoo")
        sys.exit(1)

    # Extrair dados
    resultado = extrair_dfe_completo(odoo, args.inicio, args.fim, args.limit)

    # Saída
    if args.json:
        output = json.dumps(resultado, indent=2, ensure_ascii=False, default=str)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"JSON salvo em: {args.output}")
        else:
            print(output)

    elif args.excel:
        # Formato tabular para uso com skill exportando-arquivos
        output = json.dumps(resultado['itens_flat'], indent=2, ensure_ascii=False, default=str)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Dados tabulares salvos em: {args.output}")
        else:
            print(output)

    else:
        print(formatar_resumo(resultado))


if __name__ == '__main__':
    main()
