"""
Script para consultar tabelas conhecidas do Odoo
=================================================

Tabelas com campos ja mapeados e consultas otimizadas.

Tipos disponiveis:
- dfe: Documentos Fiscais Eletronicos (DFE)
  - devolucao: NF de devolucao (finnfe=4)
  - cte: Conhecimento de Transporte (is_cte=True)
  - normal: NF normal (finnfe=1)
  - complementar: NF complementar (finnfe=2)

Autor: Sistema de Fretes
Data: 02/12/2025
"""

import sys
import os
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Adiciona path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# ==============================================================================
# CONFIGURACAO DOS MODELOS CONHECIDOS
# ==============================================================================

MODELOS_CONHECIDOS = {
    'dfe': {
        'modelo_odoo': 'l10n_br_ciel_it_account.dfe',
        'modelo_linha': 'l10n_br_ciel_it_account.dfe.line',
        'subtipos': {
            'devolucao': {'filtro': ('nfe_infnfe_ide_finnfe', '=', '4')},
            'cte': {'filtro': ('is_cte', '=', True)},
            'normal': {'filtro': ('nfe_infnfe_ide_finnfe', '=', '1')},
            'complementar': {'filtro': ('nfe_infnfe_ide_finnfe', '=', '2')},
            'ajuste': {'filtro': ('nfe_infnfe_ide_finnfe', '=', '3')},
        },
        'campos_principais': [
            'id',
            'protnfe_infnfe_chnfe',      # Chave de acesso
            'nfe_infnfe_ide_nnf',         # Numero NF
            'nfe_infnfe_ide_serie',       # Serie
            'nfe_infnfe_ide_finnfe',      # Finalidade (1=normal, 2=complementar, 3=ajuste, 4=devolucao)
            'nfe_infnfe_ide_dhemi',       # Data emissao
            'nfe_infnfe_emit_cnpj',       # CNPJ emitente
            'nfe_infnfe_emit_xnome',      # Nome emitente
            'nfe_infnfe_dest_cnpj',       # CNPJ destinatario
            'nfe_infnfe_total_icmstot_vnf',  # Valor total
            'l10n_br_status',             # Status (01-07)
            'is_cte',                     # Se eh CTe
        ],
        # Campos fiscais/tributarios (opcionais via --fiscais)
        'campos_fiscais': [
            # Totais gerais
            'nfe_infnfe_total_icmstot_vprod',  # Valor produtos
            'nfe_infnfe_total_icms_vdesc',     # Valor desconto
            'nfe_infnfe_total_icms_vfrete',    # Valor frete
            'nfe_infnfe_total_icms_vseg',      # Valor seguro
            'nfe_infnfe_total_icms_voutro',    # Outras despesas
            # ICMS
            'nfe_infnfe_total_icms_vbc',       # Base calculo ICMS
            'nfe_infnfe_total_icms_vicms',     # Valor ICMS
            'nfe_infnfe_total_icms_vicmsdeson', # ICMS desonerado
            # ICMS-ST
            'nfe_infnfe_total_icms_vbcst',     # Base calculo ICMS-ST
            'nfe_infnfe_total_icms_vst',       # Valor ICMS-ST
            # PIS/COFINS/IPI
            'nfe_infnfe_total_icms_vpis',      # Valor PIS
            'nfe_infnfe_total_icms_vcofins',   # Valor COFINS
            'nfe_infnfe_total_icms_vipi',      # Valor IPI
        ],
        # Campos especificos de CTe
        'campos_cte': [
            'cte_infcte_ide_cmunini',      # Municipio origem
            'cte_infcte_ide_cmunfim',      # Municipio destino
            'cte_infcte_ide_toma3_toma',   # Tomador
        ],
        'campos_linha': [
            'id',
            'dfe_id',
            'det_prod_cprod',             # Codigo produto
            'det_prod_xprod',             # Descricao produto
            'det_prod_ncm',               # NCM
            'det_prod_cfop',              # CFOP
            'det_prod_qcom',              # Quantidade
            'det_prod_ucom',              # Unidade
            'det_prod_vprod',             # Valor produto
            'det_prod_vuncom',            # Valor unitario
        ],
        # Campos fiscais da linha (opcionais via --fiscais)
        'campos_linha_fiscais': [
            # ICMS
            'det_imposto_icms_cst',       # CST ICMS
            'det_imposto_icms_orig',      # Origem mercadoria
            'det_imposto_icms_vbc',       # Base calculo ICMS
            'det_imposto_icms_picms',     # Aliquota ICMS
            'det_imposto_icms_vicms',     # Valor ICMS
            'det_imposto_icms_predbc',    # % Reducao base
            # ICMS-ST
            'det_imposto_icms_vbcst',     # Base ICMS-ST
            'det_imposto_icms_vicmsst',   # Valor ICMS-ST
            # PIS
            'det_imposto_pis_cst',        # CST PIS
            'det_imposto_pis_vbc',        # Base PIS
            'det_imposto_pis_ppis',       # Aliquota PIS
            'det_imposto_pis_vpis',       # Valor PIS
            # COFINS
            'det_imposto_cofins_cst',     # CST COFINS
            'det_imposto_cofins_vbc',     # Base COFINS
            'det_imposto_cofins_pcofins', # Aliquota COFINS
            'det_imposto_cofins_vcofins', # Valor COFINS
            # IPI
            'det_imposto_ipi_cst',        # CST IPI
            'det_imposto_ipi_vbc',        # Base IPI
            'det_imposto_ipi_pipi',       # Aliquota IPI
            'det_imposto_ipi_vipi',       # Valor IPI
        ],
        'campo_cliente': 'nfe_infnfe_emit_cnpj',
        'campo_cliente_nome': 'nfe_infnfe_emit_xnome',
        'campo_data': 'nfe_infnfe_ide_dhemi',
        'campo_numero': 'nfe_infnfe_ide_nnf',
        'campo_chave': 'protnfe_infnfe_chnfe',
        # Modelo de pagamentos
        'modelo_pagamento': 'l10n_br_ciel_it_account.dfe.pagamento',
        'campos_pagamento': [
            'id',
            'dfe_id',
            'cobr_dup_ndup',      # Numero da parcela
            'cobr_dup_dvenc',     # Data vencimento
            'cobr_dup_vdup',      # Valor duplicata
        ],
    }
}


# ==============================================================================
# FUNCOES AUXILIARES
# ==============================================================================

def normalizar_cnpj(valor: str) -> str:
    """
    Remove pontuacao do CNPJ.
    Aceita: 93.209.765/0001-00, 93209765000100, 93209765
    Retorna: apenas numeros
    """
    if not valor:
        return valor
    return valor.replace('.', '').replace('/', '').replace('-', '').replace(' ', '')


def formatar_cnpj_parcial(numeros: str) -> str:
    """
    Formata CNPJ parcial com pontuacao para busca.
    No Odoo, emit_cnpj esta com pontuacao: 18.467.441/0001-63

    Entrada: 18467441 (8 digitos = prefixo)
    Saida: 18.467.441

    Entrada: 18467441000163 (14 digitos = completo)
    Saida: 18.467.441/0001-63
    """
    n = numeros
    if len(n) >= 2:
        resultado = n[:2]
        if len(n) >= 5:
            resultado += '.' + n[2:5]
            if len(n) >= 8:
                resultado += '.' + n[5:8]
                if len(n) >= 12:
                    resultado += '/' + n[8:12]
                    if len(n) >= 14:
                        resultado += '-' + n[12:14]
        return resultado
    return n


def eh_cnpj(valor: str) -> bool:
    """
    Verifica se valor parece ser um CNPJ (apenas numeros apos normalizacao)
    """
    normalizado = normalizar_cnpj(valor)
    return normalizado.isdigit() and len(normalizado) >= 8


# ==============================================================================
# FUNCOES DE CONSULTA
# ==============================================================================

def consultar_dfe(args) -> Dict[str, Any]:
    """
    Consulta DFE (Documentos Fiscais Eletronicos) no Odoo
    """
    from app.odoo.utils.connection import get_odoo_connection

    config = MODELOS_CONHECIDOS['dfe']
    resultado = {
        'sucesso': False,
        'tipo': 'dfe',
        'subtipo': args.subtipo,
        'total': 0,
        'documentos': [],
        'erro': None
    }

    try:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            resultado['erro'] = 'Falha na autenticacao com Odoo'
            return resultado

        # Montar filtros base
        filtros = [
            '|',
            ('active', '=', True),
            ('active', '=', False),
        ]

        # Filtrar por subtipo
        if args.subtipo and args.subtipo != 'todos':
            if args.subtipo in config['subtipos']:
                filtros.append(config['subtipos'][args.subtipo]['filtro'])
            else:
                resultado['erro'] = f"Subtipo invalido: {args.subtipo}. Opcoes: {list(config['subtipos'].keys())}"
                return resultado

        # Filtrar por cliente (CNPJ ou nome)
        if args.cliente:
            cliente = args.cliente.strip()
            if eh_cnpj(cliente):
                # Normaliza e formata com pontuacao para busca
                cnpj_numeros = normalizar_cnpj(cliente)
                cnpj_formatado = formatar_cnpj_parcial(cnpj_numeros)
                # Busca pelo CNPJ formatado (como esta no Odoo)
                filtros.append((config['campo_cliente'], 'ilike', cnpj_formatado))
            else:
                # Buscar por nome
                filtros.append((config['campo_cliente_nome'], 'ilike', cliente))

        # Filtrar por numero NF
        if args.numero_nf:
            filtros.append((config['campo_numero'], '=', args.numero_nf))

        # Filtrar por chave de acesso
        if args.chave:
            filtros.append((config['campo_chave'], '=', args.chave))

        # Filtrar por data
        if args.data_inicio:
            filtros.append((config['campo_data'], '>=', args.data_inicio))
        if args.data_fim:
            filtros.append((config['campo_data'], '<=', args.data_fim + ' 23:59:59'))

        # Filtrar por valor (min/max)
        if getattr(args, 'valor_min', None):
            filtros.append(('nfe_infnfe_total_icmstot_vnf', '>=', args.valor_min))
        if getattr(args, 'valor_max', None):
            filtros.append(('nfe_infnfe_total_icmstot_vnf', '<=', args.valor_max))

        # Filtrar por ICMS-ST > 0 (no Odoo)
        if getattr(args, 'com_icms_st', False):
            filtros.append(('nfe_infnfe_total_icms_vst', '>', 0))

        # Filtrar por IPI > 0 (no Odoo)
        if getattr(args, 'com_ipi', False):
            filtros.append(('nfe_infnfe_total_icms_vipi', '>', 0))

        # Montar lista de campos a buscar
        campos_busca = list(config['campos_principais'])

        # Incluir campos fiscais se solicitado
        incluir_fiscais = getattr(args, 'fiscais', False)
        if incluir_fiscais:
            campos_busca.extend(config.get('campos_fiscais', []))
            # Se for CTe, incluir campos especificos
            if args.subtipo == 'cte':
                campos_busca.extend(config.get('campos_cte', []))

        # Buscar documentos
        documentos = odoo.search_read(
            config['modelo_odoo'],
            filtros,
            fields=campos_busca,
            limit=args.limit or 100
        )

        # Montar campos de linha a buscar
        campos_linha_busca = list(config['campos_linha'])
        if incluir_fiscais:
            campos_linha_busca.extend(config.get('campos_linha_fiscais', []))

        # Verificar se precisa filtrar por campos das linhas
        filtrar_linhas = (args.produto or args.quantidade or
                         getattr(args, 'ncm', None) or getattr(args, 'cfop', None))

        if filtrar_linhas:
            docs_filtrados = []
            for doc in documentos:
                linhas = odoo.search_read(
                    config['modelo_linha'],
                    [('dfe_id', '=', doc['id'])],
                    fields=campos_linha_busca,
                    limit=200
                )

                # Filtrar por produto
                if args.produto:
                    termo = args.produto.lower()
                    linhas = [linha for linha in linhas if termo in (linha.get('det_prod_xprod') or '').lower()]

                # Filtrar por NCM
                if getattr(args, 'ncm', None):
                    ncm_busca = args.ncm.replace('.', '')  # Remove pontos do NCM
                    linhas = [linha for linha in linhas
                             if ncm_busca in (linha.get('det_prod_ncm') or '').replace('.', '')]

                # Filtrar por CFOP
                if getattr(args, 'cfop', None):
                    cfop_busca = args.cfop
                    linhas = [linha for linha in linhas
                             if cfop_busca in (linha.get('det_prod_cfop') or '')]

                # Filtrar por quantidade
                if args.quantidade and linhas:
                    qtd_total = sum(float(linha.get('det_prod_qcom') or 0) for linha in linhas)
                    # Tolerancia de 5% na quantidade
                    tolerancia = args.quantidade * 0.05
                    if abs(qtd_total - args.quantidade) > tolerancia:
                        continue

                if linhas:
                    doc['linhas'] = linhas
                    doc['qtd_total'] = sum(float(linha.get('det_prod_qcom') or 0) for linha in linhas)
                    docs_filtrados.append(doc)

            documentos = docs_filtrados

        # Se pediu detalhes, buscar linhas de todos os documentos
        elif args.detalhes:
            for doc in documentos:
                linhas = odoo.search_read(
                    config['modelo_linha'],
                    [('dfe_id', '=', doc['id'])],
                    fields=campos_linha_busca,
                    limit=200
                )
                doc['linhas'] = linhas
                doc['qtd_total'] = sum(float(linha.get('det_prod_qcom') or 0) for linha in linhas)

        # Se pediu pagamentos, buscar informacoes de vencimento
        if getattr(args, 'pagamentos', False):
            for doc in documentos:
                pagamentos = odoo.search_read(
                    config['modelo_pagamento'],
                    [('dfe_id', '=', doc['id'])],
                    fields=config['campos_pagamento'],
                    limit=50
                )
                doc['pagamentos'] = pagamentos

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
        description='Consulta tabelas conhecidas do Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Buscar devolucao por cliente
  python consulta.py --tipo dfe --subtipo devolucao --cliente "atacadao"

  # Buscar devolucao por quantidade
  python consulta.py --tipo dfe --subtipo devolucao --quantidade 784 --detalhes

  # Buscar CTe por chave
  python consulta.py --tipo dfe --subtipo cte --chave 3525...

  # Buscar por NCM (ex: 21069090 = preparacoes alimenticias)
  python consulta.py --tipo dfe --subtipo normal --ncm 21069090 --detalhes

  # Buscar por CFOP (ex: 5102 = venda producao)
  python consulta.py --tipo dfe --subtipo normal --cfop 5102

  # Buscar notas com ICMS-ST
  python consulta.py --tipo dfe --subtipo normal --com-icms-st --fiscais

  # Buscar notas com IPI
  python consulta.py --tipo dfe --subtipo normal --com-ipi --fiscais

  # Buscar por faixa de valor
  python consulta.py --tipo dfe --valor-min 1000 --valor-max 5000

  # Buscar com informacoes de pagamento/vencimento
  python consulta.py --tipo dfe --subtipo normal --cliente "fornecedor" --pagamentos
        """
    )

    # Argumentos obrigatorios
    parser.add_argument('--tipo', required=True, choices=['dfe'],
                        help='Tipo de consulta (dfe)')

    # Argumentos para DFE
    parser.add_argument('--subtipo', default='todos',
                        choices=['devolucao', 'cte', 'normal', 'complementar', 'ajuste', 'todos'],
                        help='Subtipo do DFE')
    parser.add_argument('--cliente', help='CNPJ ou nome do emitente')
    parser.add_argument('--produto', help='Nome do produto nas linhas')
    parser.add_argument('--quantidade', type=float, help='Quantidade aproximada')
    parser.add_argument('--chave', help='Chave de acesso (44 digitos)')
    parser.add_argument('--numero-nf', help='Numero da NF')
    parser.add_argument('--data-inicio', help='Data inicial (YYYY-MM-DD)')
    parser.add_argument('--data-fim', help='Data final (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados')
    parser.add_argument('--detalhes', action='store_true', help='Incluir linhas/produtos')
    parser.add_argument('--fiscais', action='store_true',
                        help='Incluir campos fiscais/tributarios (ICMS, PIS, COFINS, IPI, ST)')

    # Filtros avancados (Fase 1)
    parser.add_argument('--ncm', help='NCM do produto (busca nas linhas)')
    parser.add_argument('--cfop', help='CFOP da operacao (busca nas linhas)')
    parser.add_argument('--com-icms-st', action='store_true',
                        help='Apenas documentos com ICMS-ST > 0')
    parser.add_argument('--com-ipi', action='store_true',
                        help='Apenas documentos com IPI > 0')
    parser.add_argument('--valor-min', type=float, help='Valor minimo do documento')
    parser.add_argument('--valor-max', type=float, help='Valor maximo do documento')
    parser.add_argument('--pagamentos', action='store_true',
                        help='Incluir informacoes de pagamento/vencimento')

    # Formato de saida
    parser.add_argument('--json', action='store_true', help='Saida em JSON')

    args = parser.parse_args()

    # Executar consulta
    if args.tipo == 'dfe':
        resultado = consultar_dfe(args)
    else:
        resultado = {'sucesso': False, 'erro': f'Tipo nao implementado: {args.tipo}'}

    # Saida
    if args.json:
        print(json.dumps(resultado, indent=2, default=str, ensure_ascii=False))
    else:
        if resultado['sucesso']:
            print(f"\n{'='*60}")
            print(f"RESULTADO: {resultado['total']} documento(s) encontrado(s)")
            print(f"{'='*60}\n")

            for doc in resultado['documentos'][:20]:
                nf = doc.get('nfe_infnfe_ide_nnf', 'N/A')
                serie = doc.get('nfe_infnfe_ide_serie', '')
                data = doc.get('nfe_infnfe_ide_dhemi', 'N/A')
                emitente = doc.get('nfe_infnfe_emit_xnome', 'N/A')
                cnpj = doc.get('nfe_infnfe_emit_cnpj', 'N/A')
                valor = doc.get('nfe_infnfe_total_icmstot_vnf', 0)
                chave = doc.get('protnfe_infnfe_chnfe', 'N/A')

                print(f"NF: {nf}-{serie}")
                print(f"  Data: {data}")
                print(f"  Emitente: {emitente}")
                print(f"  CNPJ: {cnpj}")
                print(f"  Valor: R$ {valor:,.2f}" if valor else "  Valor: N/A")
                print(f"  Chave: {chave}")

                # Exibir campos fiscais se solicitado
                if args.fiscais:
                    print(f"  --- TOTAIS FISCAIS ---")
                    vprod = doc.get('nfe_infnfe_total_icmstot_vprod', 0)
                    vfrete = doc.get('nfe_infnfe_total_icms_vfrete', 0)
                    vdesc = doc.get('nfe_infnfe_total_icms_vdesc', 0)

                    print(f"  Valor Produtos: R$ {vprod:,.2f}" if vprod else "  Valor Produtos: -")
                    print(f"  Frete: R$ {vfrete:,.2f}" if vfrete else "  Frete: -")
                    print(f"  Desconto: R$ {vdesc:,.2f}" if vdesc else "  Desconto: -")

                    # ICMS
                    vbc_icms = doc.get('nfe_infnfe_total_icms_vbc', 0)
                    vicms = doc.get('nfe_infnfe_total_icms_vicms', 0)
                    if vbc_icms or vicms:
                        print(f"  ICMS: BC R$ {vbc_icms:,.2f} | Valor R$ {vicms:,.2f}")

                    # ICMS-ST
                    vbcst = doc.get('nfe_infnfe_total_icms_vbcst', 0)
                    vst = doc.get('nfe_infnfe_total_icms_vst', 0)
                    if vbcst or vst:
                        print(f"  ICMS-ST: BC R$ {vbcst:,.2f} | Valor R$ {vst:,.2f}")

                    # PIS/COFINS/IPI
                    vpis = doc.get('nfe_infnfe_total_icms_vpis', 0)
                    vcofins = doc.get('nfe_infnfe_total_icms_vcofins', 0)
                    vipi = doc.get('nfe_infnfe_total_icms_vipi', 0)
                    if vpis or vcofins or vipi:
                        print(f"  PIS: R$ {vpis:,.2f} | COFINS: R$ {vcofins:,.2f} | IPI: R$ {vipi:,.2f}")

                if 'qtd_total' in doc:
                    print(f"  Qtd Total: {doc['qtd_total']:,.0f}")

                if 'linhas' in doc and doc['linhas']:
                    print(f"  Produtos ({len(doc['linhas'])}):")
                    for linha in doc['linhas'][:5]:
                        prod = linha.get('det_prod_xprod', 'N/A')
                        qtd = linha.get('det_prod_qcom', 0)
                        ncm = linha.get('det_prod_ncm', '')
                        cfop = linha.get('det_prod_cfop', '')
                        vprod_linha = linha.get('det_prod_vprod', 0)

                        info_fiscal = ""
                        if args.fiscais:
                            cst_icms = linha.get('det_imposto_icms_cst', '')
                            aliq_icms = linha.get('det_imposto_icms_picms', 0)
                            info_fiscal = f" [NCM:{ncm} CFOP:{cfop} CST:{cst_icms} ICMS:{aliq_icms}%]"

                        print(f"    - {prod}: {qtd:,.0f} x R$ {vprod_linha:,.2f}{info_fiscal}")
                    if len(doc['linhas']) > 5:
                        print(f"    ... e mais {len(doc['linhas']) - 5} produtos")

                # Exibir pagamentos se solicitado
                if 'pagamentos' in doc and doc['pagamentos']:
                    print(f"  Pagamentos ({len(doc['pagamentos'])}):")
                    for pag in doc['pagamentos']:
                        parcela = pag.get('cobr_dup_ndup', 'N/A')
                        vencimento = pag.get('cobr_dup_dvenc', 'N/A')
                        valor_pag = pag.get('cobr_dup_vdup', 0)
                        print(f"    - Parcela {parcela}: R$ {valor_pag:,.2f} (venc: {vencimento})")

                print()

            if resultado['total'] > 20:
                print(f"... e mais {resultado['total'] - 20} documento(s)")
        else:
            print(f"\nERRO: {resultado['erro']}")


if __name__ == '__main__':
    main()
