#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consulta Produtos - Catalogo de Produtos no Odoo

Skill: consultando-odoo-produtos
Modelos: product.product, product.template
"""

import argparse
import json
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from typing import Dict, Any, List


# ==============================================================================
# CONFIGURACAO DOS MODELOS
# ==============================================================================

MODELO_CONFIG = {
    'produtos': {
        'modelo': 'product.product',
        'modelo_template': 'product.template',
        'campos_principais': [
            'id',
            'name',                      # Nome do produto
            'display_name',              # Nome de exibicao
            'default_code',              # Codigo interno
            'barcode',                   # Codigo de barras EAN
            'barcode_nacom',             # Codigo de barras Nacom
            'categ_id',                  # Categoria
            'detailed_type',             # Tipo detalhado (product, consu, service)
            'type',                      # Tipo basico
            'list_price',                # Preco de venda
            'standard_price',            # Custo
            'uom_id',                    # Unidade de medida
            'uom_po_id',                 # Unidade de compra
            'sale_ok',                   # Pode ser vendido
            'purchase_ok',               # Pode ser comprado
            'active',                    # Ativo
            'company_id',                # Empresa
        ],
        'campos_estoque': [
            'qty_available',             # Em estoque
            'virtual_available',         # Previsto
            'incoming_qty',              # Entrando
            'outgoing_qty',              # Saindo
            'free_qty',                  # Disponivel (livre)
        ],
        'campos_detalhes': [
            'weight',                    # Peso liquido
            'gross_weight',              # Peso bruto
            'volume',                    # Volume
            'description',               # Descricao
            'description_sale',          # Descricao de venda
            'description_purchase',      # Descricao de compra
            'description_picking',       # Descricao no picking
            'tracking',                  # Rastreabilidade (none, lot, serial)
            'valuation',                 # Valorizacao estoque
            'cost_method',               # Metodo de custo
            'seller_ids',                # Fornecedores
            'product_tmpl_id',           # Template
            'product_template_attribute_value_ids',  # Atributos
        ],
        'campos_fiscais': [
            # NCM e Origem
            'l10n_br_ncm_id',            # NCM (many2one)
            'l10n_br_origem',            # Origem do produto (0-8)
            'l10n_br_tipo_produto',      # Tipo do produto BR
            'l10n_br_fci',               # FCI
            'l10n_br_cnpj_fabricante',   # CNPJ Fabricante
            'l10n_br_grupo_id',          # Grupo
            # Servicos
            'l10n_br_codigo_servico',    # Codigo Servico
            'l10n_br_codigo_tributacao_servico',  # Cod tributacao servico
            'l10n_br_exigibilidade_iss', # Exigibilidade ISS
            'l10n_br_natureza_iss',      # Natureza ISS
            # PIS/COFINS
            'l10n_br_nat_bc_cred',       # Natureza credito PIS/COFINS
            # ICMS-ST Retido
            'l10n_br_icmsst_retido_aliquota',  # Aliquota ICMS-ST
            'l10n_br_icmsst_retido_base',      # Base ICMS-ST
            'l10n_br_icmsst_retido_valor',     # Valor ICMS-ST
            'l10n_br_icmsst_substituto_valor', # Valor substituto
            # Outros
            'l10n_br_informacao_adicional',    # Info adicional
            'l10n_br_indescala',               # Ind escala relevante
            # ANP/ANVISA
            'l10n_br_farmaceutico',            # Eh farmaceutico
            'l10n_br_registro_anvisa',         # Registro ANVISA
            'l10n_br_processo_anvisa',         # Processo ANVISA
            'l10n_br_preco_maximo_anvisa',     # Preco max ANVISA
            'l10n_br_validade_processo_anvisa', # Validade ANVISA
            'l10n_br_registro_anp',            # Registro ANP
            'l10n_br_produto_anp',             # Codigo ANP
            # Energia/Gas
            'l10n_br_consumo_energia_gas',     # Consumo energia/gas
            'l10n_br_tipo_ligacao',            # Tipo ligacao
            'l10n_br_grupo_tensao',            # Grupo tensao
            # Contas contabeis
            'property_account_income_id',      # Conta de receita
            'property_account_expense_id',     # Conta de despesa
            # Impostos padrao
            'taxes_id',                        # Impostos de venda
            'supplier_taxes_id',               # Impostos de compra
            'fiscal_tag_ids',                  # Marcadores fiscais
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


def formatar_quantidade(valor):
    """Formata quantidade."""
    if valor is None:
        return "0"
    return f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def traduzir_detailed_type(tipo):
    """Traduz detailed_type para portugues."""
    tipos = {
        'product': 'Estocavel',
        'consu': 'Consumivel',
        'service': 'Servico',
    }
    return tipos.get(tipo, tipo or 'N/A')


def traduzir_origem(origem):
    """Traduz codigo de origem para descricao."""
    origens = {
        '0': 'Nacional',
        '1': 'Estrangeira - Importacao direta',
        '2': 'Estrangeira - Mercado interno',
        '3': 'Nacional - Import > 40% e <= 70%',
        '4': 'Nacional - Decreto',
        '5': 'Nacional - Import <= 40%',
        '6': 'Estrangeira - Import sem similar',
        '7': 'Estrangeira - Merc. int. sem similar',
        '8': 'Nacional - Import > 70%',
    }
    return origens.get(str(origem), str(origem) if origem else 'N/A')


def traduzir_tracking(tracking):
    """Traduz tracking para portugues."""
    rastreio = {
        'none': 'Sem rastreio',
        'lot': 'Por lote',
        'serial': 'Por numero de serie',
    }
    return rastreio.get(tracking, tracking or 'N/A')


# ==============================================================================
# FUNCAO PRINCIPAL DE CONSULTA
# ==============================================================================

def consultar_produtos(args) -> Dict[str, Any]:
    """Consulta produtos no Odoo."""
    resultado = {
        'sucesso': False,
        'tipo': 'produtos',
        'subtipo': args.subtipo,
        'total': 0,
        'produtos': [],
        'resumo': {},
        'erro': None
    }

    try:
        odoo = get_odoo_connection()
        config = MODELO_CONFIG['produtos']

        # Montar filtros base
        filtros = []

        # Filtrar por subtipo
        if args.subtipo == 'ativos':
            filtros.append(('active', '=', True))
        elif args.subtipo == 'inativos':
            filtros.append(('active', '=', False))
        elif args.subtipo == 'vendaveis':
            filtros.append(('sale_ok', '=', True))
            filtros.append(('active', '=', True))
        elif args.subtipo == 'compraveis':
            filtros.append(('purchase_ok', '=', True))
            filtros.append(('active', '=', True))
        elif args.subtipo == 'estocaveis':
            filtros.append(('detailed_type', '=', 'product'))
            filtros.append(('active', '=', True))
        elif args.subtipo == 'servicos':
            filtros.append(('detailed_type', '=', 'service'))
            filtros.append(('active', '=', True))
        elif args.subtipo == 'consumiveis':
            filtros.append(('detailed_type', '=', 'consu'))
            filtros.append(('active', '=', True))
        elif args.subtipo == 'todos':
            # Inclui ativos e inativos
            filtros.append('|')
            filtros.append(('active', '=', True))
            filtros.append(('active', '=', False))

        # Filtrar por codigo interno
        if getattr(args, 'codigo', None):
            filtros.append(('default_code', 'ilike', args.codigo))

        # Filtrar por nome
        if getattr(args, 'nome', None):
            filtros.append(('name', 'ilike', args.nome))

        # Filtrar por barcode
        if getattr(args, 'barcode', None):
            filtros.append('|')
            filtros.append(('barcode', 'ilike', args.barcode))
            filtros.append(('barcode_nacom', 'ilike', args.barcode))

        # Filtrar por categoria
        if getattr(args, 'categoria', None):
            filtros.append(('categ_id.name', 'ilike', args.categoria))

        # Filtrar por NCM
        if getattr(args, 'ncm', None):
            filtros.append(('l10n_br_ncm_id.codigo', 'ilike', args.ncm))

        # Filtrar por fornecedor
        if getattr(args, 'fornecedor', None):
            # Buscar IDs de fornecedores que correspondem
            fornecedores = odoo.search_read(
                'product.supplierinfo',
                [('partner_id.name', 'ilike', args.fornecedor)],
                fields=['product_tmpl_id'],
                limit=1000
            )
            template_ids = [f['product_tmpl_id'][0] for f in fornecedores if f.get('product_tmpl_id')]
            if template_ids:
                filtros.append(('product_tmpl_id', 'in', template_ids))
            else:
                # Nenhum fornecedor encontrado
                resultado['sucesso'] = True
                return resultado

        # Filtrar por preco
        if getattr(args, 'preco_min', None):
            filtros.append(('list_price', '>=', args.preco_min))
        if getattr(args, 'preco_max', None):
            filtros.append(('list_price', '<=', args.preco_max))

        # Filtrar por estoque
        if getattr(args, 'com_estoque', False):
            filtros.append(('qty_available', '>', 0))
        if getattr(args, 'sem_estoque', False):
            filtros.append(('qty_available', '<=', 0))

        # Montar lista de campos a buscar
        campos_busca = list(config['campos_principais'])

        # Sempre incluir campos de estoque para filtros
        campos_busca.extend(config['campos_estoque'])

        # Incluir campos de detalhes se solicitado
        if getattr(args, 'detalhes', False):
            campos_busca.extend(config['campos_detalhes'])

        # Incluir campos fiscais se solicitado
        if getattr(args, 'fiscais', False):
            campos_busca.extend(config['campos_fiscais'])

        # Executar busca
        produtos = odoo.search_read(
            config['modelo'],
            filtros,
            fields=campos_busca,
            limit=args.limit or 100
        )

        # Buscar info de fornecedores se detalhes solicitado
        if getattr(args, 'detalhes', False):
            for produto in produtos:
                template_id = produto.get('product_tmpl_id')
                if template_id:
                    tmpl_id = template_id[0] if isinstance(template_id, (list, tuple)) else template_id
                    fornecedores = odoo.search_read(
                        'product.supplierinfo',
                        [('product_tmpl_id', '=', tmpl_id)],
                        fields=['partner_id', 'price', 'min_qty', 'delay'],
                        limit=5
                    )
                    produto['fornecedores_info'] = fornecedores

        # Calcular resumo se solicitado
        if getattr(args, 'resumo', False):
            total_produtos = len(produtos)

            # Contar por tipo
            por_tipo = {}
            for produto in produtos:
                tp = produto.get('detailed_type', 'N/A')
                por_tipo[tp] = por_tipo.get(tp, 0) + 1

            # Contar por categoria
            por_categoria = {}
            for produto in produtos:
                cat = extrair_nome_many2one(produto.get('categ_id'))
                if cat:
                    por_categoria[cat] = por_categoria.get(cat, 0) + 1

            # Top 10 categorias
            top_categorias = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:10]

            # Contadores
            ativos = sum(1 for p in produtos if p.get('active'))
            inativos = total_produtos - ativos
            vendaveis = sum(1 for p in produtos if p.get('sale_ok'))
            compraveis = sum(1 for p in produtos if p.get('purchase_ok'))
            com_estoque = sum(1 for p in produtos if (p.get('qty_available') or 0) > 0)

            resultado['resumo'] = {
                'total_produtos': total_produtos,
                'ativos': ativos,
                'inativos': inativos,
                'vendaveis': vendaveis,
                'compraveis': compraveis,
                'com_estoque': com_estoque,
                'por_tipo': por_tipo,
                'top_categorias': top_categorias,
            }

        resultado['sucesso'] = True
        resultado['total'] = len(produtos)
        resultado['produtos'] = produtos

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Consulta produtos no Odoo (product.product)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Produtos ativos para venda
  python consulta.py --tipo produtos --subtipo vendaveis

  # Buscar por codigo interno
  python consulta.py --tipo produtos --codigo "PROD001"

  # Buscar por nome
  python consulta.py --tipo produtos --nome "pupunha"

  # Buscar por codigo de barras
  python consulta.py --tipo produtos --barcode "7891234567890"

  # Produtos de uma categoria
  python consulta.py --tipo produtos --categoria "conservas"

  # Produtos por NCM
  python consulta.py --tipo produtos --ncm "2008.99" --fiscais

  # Produtos de um fornecedor
  python consulta.py --tipo produtos --fornecedor "vale sul" --detalhes

  # Produtos com estoque disponivel
  python consulta.py --tipo produtos --com-estoque

  # Resumo do catalogo
  python consulta.py --tipo produtos --resumo
        """
    )

    # Argumentos obrigatorios
    parser.add_argument('--tipo', required=True, choices=['produtos'],
                        help='Tipo de consulta')

    # Subtipos
    parser.add_argument('--subtipo', default='ativos',
                        choices=['ativos', 'inativos', 'vendaveis', 'compraveis',
                                 'estocaveis', 'servicos', 'consumiveis', 'todos'],
                        help='Subtipo: ativos, inativos, vendaveis, compraveis, estocaveis, servicos, consumiveis, todos')

    # Filtros basicos
    parser.add_argument('--codigo', help='Codigo interno (default_code)')
    parser.add_argument('--nome', help='Nome do produto (busca parcial)')
    parser.add_argument('--barcode', help='Codigo de barras (busca parcial)')
    parser.add_argument('--categoria', help='Nome da categoria (busca parcial)')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados')

    # Filtros avancados
    parser.add_argument('--ncm', help='Codigo NCM (busca parcial)')
    parser.add_argument('--fornecedor', help='Nome do fornecedor (busca parcial)')
    parser.add_argument('--preco-min', type=float, help='Preco de venda minimo')
    parser.add_argument('--preco-max', type=float, help='Preco de venda maximo')
    parser.add_argument('--com-estoque', action='store_true', help='Apenas com estoque > 0')
    parser.add_argument('--sem-estoque', action='store_true', help='Apenas sem estoque')

    # Opcoes de saida
    parser.add_argument('--detalhes', action='store_true',
                        help='Incluir fornecedores, estoque e mais campos')
    parser.add_argument('--fiscais', action='store_true',
                        help='Incluir campos fiscais (NCM, origem, etc)')
    parser.add_argument('--resumo', action='store_true',
                        help='Mostrar apenas totalizadores')
    parser.add_argument('--json', action='store_true', help='Saida em JSON')

    args = parser.parse_args()

    # Executar consulta
    resultado = consultar_produtos(args)

    # Formatar saida
    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    else:
        if resultado['sucesso']:
            subtipo_nome = {
                'ativos': 'ATIVOS',
                'inativos': 'INATIVOS',
                'vendaveis': 'VENDAVEIS',
                'compraveis': 'COMPRAVEIS',
                'estocaveis': 'ESTOCAVEIS',
                'servicos': 'SERVICOS',
                'consumiveis': 'CONSUMIVEIS',
                'todos': 'TODOS'
            }.get(args.subtipo, args.subtipo.upper())

            print(f"\n=== PRODUTOS - {subtipo_nome} ===")
            print(f"Total encontrado: {resultado['total']}")

            # Mostrar resumo se solicitado
            if args.resumo and resultado['resumo']:
                r = resultado['resumo']
                print(f"\n--- RESUMO ---")
                print(f"Total: {r['total_produtos']}")
                print(f"Ativos: {r['ativos']} | Inativos: {r['inativos']}")
                print(f"Vendaveis: {r['vendaveis']} | Compraveis: {r['compraveis']}")
                print(f"Com estoque: {r['com_estoque']}")
                print(f"\nPor Tipo:")
                for tp, qtd in r['por_tipo'].items():
                    print(f"  - {traduzir_detailed_type(tp)}: {qtd}")
                if r['top_categorias']:
                    print(f"\nTop Categorias:")
                    for cat, qtd in r['top_categorias']:
                        print(f"  - {cat}: {qtd}")
                print()
            else:
                print()

                for produto in resultado['produtos'][:20]:
                    nome = produto.get('name') or 'S/N'
                    codigo = produto.get('default_code') or ''
                    barcode = produto.get('barcode') or ''
                    categoria = extrair_nome_many2one(produto.get('categ_id'))
                    tipo = traduzir_detailed_type(produto.get('detailed_type'))
                    preco_venda = produto.get('list_price') or 0
                    custo = produto.get('standard_price') or 0
                    uom = extrair_nome_many2one(produto.get('uom_id'))
                    qty = produto.get('qty_available') or 0
                    sale_ok = produto.get('sale_ok')
                    purchase_ok = produto.get('purchase_ok')
                    active = produto.get('active')

                    status_flags = []
                    if sale_ok: status_flags.append('Venda')
                    if purchase_ok: status_flags.append('Compra')
                    if not active: status_flags.append('INATIVO')

                    print(f"[{produto['id']}] {nome}")
                    if codigo:
                        print(f"  Codigo: {codigo}")
                    if barcode:
                        print(f"  Barcode: {barcode}")
                    print(f"  Categoria: {categoria} | Tipo: {tipo}")
                    print(f"  Preco Venda: {formatar_valor(preco_venda)} | Custo: {formatar_valor(custo)}")
                    print(f"  Estoque: {formatar_quantidade(qty)} {uom}")
                    if status_flags:
                        print(f"  Status: {', '.join(status_flags)}")

                    # Campos fiscais se solicitado
                    if getattr(args, 'fiscais', False):
                        ncm = extrair_nome_many2one(produto.get('l10n_br_ncm_id'))
                        origem = produto.get('l10n_br_origem')
                        tipo_br = produto.get('l10n_br_tipo_produto')
                        fci = produto.get('l10n_br_fci')
                        cnpj_fab = produto.get('l10n_br_cnpj_fabricante')

                        if ncm:
                            print(f"  NCM: {ncm}")
                        if origem:
                            print(f"  Origem: {traduzir_origem(origem)}")
                        if tipo_br:
                            print(f"  Tipo BR: {tipo_br}")
                        if fci:
                            print(f"  FCI: {fci}")
                        if cnpj_fab:
                            print(f"  CNPJ Fab: {cnpj_fab}")

                    # Detalhes se solicitado
                    if getattr(args, 'detalhes', False):
                        peso = produto.get('weight') or produto.get('gross_weight')
                        volume = produto.get('volume')
                        tracking = produto.get('tracking')
                        virtual = produto.get('virtual_available') or 0
                        incoming = produto.get('incoming_qty') or 0
                        outgoing = produto.get('outgoing_qty') or 0

                        if peso:
                            print(f"  Peso: {peso} kg")
                        if volume:
                            print(f"  Volume: {volume} m3")
                        if tracking and tracking != 'none':
                            print(f"  Rastreio: {traduzir_tracking(tracking)}")

                        print(f"  Estoque: Disponivel={formatar_quantidade(qty)} | Previsto={formatar_quantidade(virtual)}")
                        if incoming or outgoing:
                            print(f"           Entrando={formatar_quantidade(incoming)} | Saindo={formatar_quantidade(outgoing)}")

                        # Fornecedores
                        if 'fornecedores_info' in produto and produto['fornecedores_info']:
                            print(f"  Fornecedores ({len(produto['fornecedores_info'])}):")
                            for forn in produto['fornecedores_info'][:3]:
                                nome_forn = extrair_nome_many2one(forn.get('partner_id'))
                                preco_forn = forn.get('price') or 0
                                min_qty = forn.get('min_qty') or 0
                                delay = forn.get('delay') or 0
                                print(f"    - {nome_forn}: {formatar_valor(preco_forn)} (min:{min_qty}, prazo:{delay}d)")

                    print()

                if resultado['total'] > 20:
                    print(f"... e mais {resultado['total'] - 20} produto(s)")
        else:
            print(f"\nERRO: {resultado['erro']}")


if __name__ == '__main__':
    main()
