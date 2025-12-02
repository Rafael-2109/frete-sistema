#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de consulta de cadastros no Odoo.
Modelos: res.partner (parceiros) e delivery.carrier (transportadoras)

Uso:
    python consulta.py --tipo partner --subtipo fornecedor --cnpj "18467441"
    python consulta.py --tipo partner --nome "atacadao" --uf SP
    python consulta.py --tipo transportadora --nome "correios"
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

MODELOS_CONHECIDOS = {
    'partner': {
        'modelo_odoo': 'res.partner',
        'subtipos': {
            'fornecedor': {'filtro': ('supplier_rank', '>', 0)},
            'cliente': {'filtro': ('customer_rank', '>', 0)},
            'todos': {'filtro': None},
        },
        'campos_principais': [
            'id',
            'name',
            'display_name',
            'vat',                           # CNPJ/CPF sem formatacao
            'l10n_br_cnpj',                  # CNPJ
            'l10n_br_cpf',                   # CPF
            'l10n_br_razao_social',          # Razao Social
            'is_company',
            'company_type',
            'customer_rank',
            'supplier_rank',
            'email',
            'phone',
            'mobile',
            'active',
        ],
        'campos_endereco': [
            'street',                        # Logradouro
            'l10n_br_endereco_numero',       # Numero
            'street2',                       # Complemento
            'l10n_br_endereco_bairro',       # Bairro
            'city',                          # Cidade
            'state_id',                      # Estado (many2one)
            'zip',                           # CEP
            'country_id',                    # Pais (many2one)
            'l10n_br_municipio_id',          # Municipio (many2one)
        ],
        'campos_fiscais': [
            # Inscricoes e registros
            'l10n_br_ie',                    # Inscricao Estadual
            'l10n_br_im',                    # Inscricao Municipal
            'l10n_br_is',                    # Inscricao Suframa
            'l10n_br_indicador_ie',          # Indicador IE
            'l10n_br_regime_tributario',     # Regime Tributario
            'l10n_br_situacao_cadastral',    # Situacao Cadastral
            'l10n_br_crc',                   # CRC
            'l10n_br_nire',                  # NIRE
            'l10n_br_id_estrangeiro',        # Id Estrangeiro
            # Retencoes de impostos
            'l10n_br_pis_ret_valor',         # Valor Min PIS Retido
            'l10n_br_cofins_ret_valor',      # Valor Min COFINS Retido
            'l10n_br_csll_ret_valor',        # Valor Min CSLL Retido
            'l10n_br_irpj_ret_valor',        # Valor Min IRPJ Retido
            'l10n_br_inss_cprb',             # Contribuinte INSS CPRB
            # Credito ICMS
            'l10n_br_icms_credito_aliquota', # Aliquota credito Simples Nacional
            # Posicao fiscal
            'property_account_position_id',  # Posicao Fiscal
            'fiscal_tag_ids',                # Marcadores Fiscais
            # Configuracoes
            'l10n_br_compra_indcom',         # Destinacao de Uso
            'l10n_br_orgao_publico',         # Orgao Publico
            'l10n_br_receber_nfe',           # Receber NF-e
            'l10n_br_receber_boleto',        # Receber Boleto
        ],
        'campos_extras': [
            'ref',                           # Referencia
            'website',                       # Website
            'comment',                       # Observacoes
            'parent_id',                     # Empresa pai
            'credit_limit',                  # Limite de credito
            'property_payment_term_id',      # Prazo pagamento cliente
            'property_supplier_payment_term_id',  # Prazo pagamento fornecedor
            'property_delivery_carrier_id',  # Transportadora padrao
            'create_date',
            'write_date',
        ],
        'campo_cnpj': 'vat',
        'campo_nome': 'name',
    },
    'transportadora': {
        'modelo_odoo': 'delivery.carrier',
        'subtipos': {
            'todos': {'filtro': None},
        },
        'campos_principais': [
            'id',
            'name',                          # Nome do metodo
            'display_name',
            'active',
            'delivery_type',                 # Tipo (fixed, base_on_rule, etc)
            'fixed_price',                   # Preco fixo
            'margin',                        # Margem %
            'fixed_margin',                  # Margem fixa
            'free_over',                     # Frete gratis acima de
            'amount',                        # Valor para frete gratis
            'l10n_br_partner_id',            # Parceiro vinculado
            'product_id',                    # Produto de frete
            'company_id',
        ],
        'campos_extras': [
            'carrier_description',           # Descricao
            'invoice_policy',                # Politica de faturamento
            'integration_level',             # Nivel de integracao
            'country_ids',                   # Paises
            'state_ids',                     # Estados
            'zip_prefix_ids',                # Prefixos CEP
            'sequence',                      # Sequencia
            'create_date',
            'write_date',
        ],
        'campo_nome': 'name',
    }
}


# ==============================================================================
# FUNCOES AUXILIARES
# ==============================================================================

def formatar_cnpj_cpf(valor: str) -> str:
    """Remove formatacao de CNPJ/CPF para busca."""
    if not valor:
        return ''
    return ''.join(c for c in valor if c.isdigit())


def extrair_nome_many2one(valor) -> str:
    """Extrai nome de campo many2one (retorna tupla [id, nome])."""
    if isinstance(valor, (list, tuple)) and len(valor) >= 2:
        return valor[1]
    return str(valor) if valor else ''


def extrair_id_many2one(valor) -> int:
    """Extrai ID de campo many2one."""
    if isinstance(valor, (list, tuple)) and len(valor) >= 1:
        return valor[0]
    return valor if isinstance(valor, int) else 0


# ==============================================================================
# FUNCAO DE CONSULTA - PARTNER
# ==============================================================================

def consultar_partner(args) -> Dict[str, Any]:
    """
    Consulta parceiros (res.partner) no Odoo.
    """
    from app.odoo.utils.connection import get_odoo_connection

    config = MODELOS_CONHECIDOS['partner']
    resultado = {
        'sucesso': False,
        'tipo': 'partner',
        'subtipo': args.subtipo,
        'total': 0,
        'parceiros': [],
        'erro': None
    }

    try:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            resultado['erro'] = 'Falha na autenticacao com Odoo'
            return resultado

        # Montar filtros
        filtros = []

        # Filtro de subtipo
        if args.subtipo and args.subtipo != 'todos':
            subtipo_config = config['subtipos'].get(args.subtipo)
            if subtipo_config and subtipo_config['filtro']:
                filtros.append(subtipo_config['filtro'])

        # Filtro de CNPJ
        if args.cnpj:
            cnpj_limpo = formatar_cnpj_cpf(args.cnpj)
            # Buscar em vat (sem formatacao) ou l10n_br_cnpj (com formatacao)
            filtros.append('|')
            filtros.append(('vat', 'ilike', cnpj_limpo))
            filtros.append(('l10n_br_cnpj', 'ilike', args.cnpj))

        # Filtro de nome
        if args.nome:
            filtros.append('|')
            filtros.append(('name', 'ilike', args.nome))
            filtros.append(('l10n_br_razao_social', 'ilike', args.nome))

        # Filtro de UF
        if args.uf:
            filtros.append(('state_id.code', '=', args.uf.upper()))

        # Filtro de cidade
        if getattr(args, 'cidade', None):
            filtros.append(('city', 'ilike', args.cidade))

        # Filtro de IE
        if getattr(args, 'ie', None):
            filtros.append(('l10n_br_ie', 'ilike', args.ie))

        # Filtro de email
        if getattr(args, 'email', None):
            filtros.append(('email', 'ilike', args.email))

        # Filtro de ativos/inativos
        if not getattr(args, 'inativos', False):
            filtros.append(('active', '=', True))
        else:
            # Incluir ativos e inativos
            filtros.append('|')
            filtros.append(('active', '=', True))
            filtros.append(('active', '=', False))

        # Montar lista de campos a buscar
        campos_busca = list(config['campos_principais'])

        # Incluir campos de endereco se solicitado
        if getattr(args, 'endereco', False):
            campos_busca.extend(config['campos_endereco'])

        # Incluir campos fiscais se solicitado
        if getattr(args, 'fiscal', False):
            campos_busca.extend(config['campos_fiscais'])

        # Incluir campos extras se detalhes solicitado
        if getattr(args, 'detalhes', False):
            campos_busca.extend(config['campos_endereco'])
            campos_busca.extend(config['campos_fiscais'])
            campos_busca.extend(config['campos_extras'])

        # Remover duplicados mantendo ordem
        campos_busca = list(dict.fromkeys(campos_busca))

        # Buscar parceiros
        parceiros = odoo.search_read(
            config['modelo_odoo'],
            filtros,
            fields=campos_busca,
            limit=args.limit or 100
        )

        resultado['sucesso'] = True
        resultado['total'] = len(parceiros)
        resultado['parceiros'] = parceiros

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# FUNCAO DE CONSULTA - TRANSPORTADORA
# ==============================================================================

def consultar_transportadora(args) -> Dict[str, Any]:
    """
    Consulta transportadoras (delivery.carrier) no Odoo.
    """
    from app.odoo.utils.connection import get_odoo_connection

    config = MODELOS_CONHECIDOS['transportadora']
    resultado = {
        'sucesso': False,
        'tipo': 'transportadora',
        'total': 0,
        'transportadoras': [],
        'erro': None
    }

    try:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            resultado['erro'] = 'Falha na autenticacao com Odoo'
            return resultado

        # Montar filtros
        filtros = []

        # Filtro de nome
        if args.nome:
            filtros.append(('name', 'ilike', args.nome))

        # Filtro de ativos/inativos
        if not getattr(args, 'inativos', False):
            filtros.append(('active', '=', True))
        else:
            filtros.append('|')
            filtros.append(('active', '=', True))
            filtros.append(('active', '=', False))

        # Montar lista de campos a buscar
        campos_busca = list(config['campos_principais'])

        # Incluir campos extras se detalhes solicitado
        if getattr(args, 'detalhes', False):
            campos_busca.extend(config['campos_extras'])

        # Remover duplicados mantendo ordem
        campos_busca = list(dict.fromkeys(campos_busca))

        # Buscar transportadoras
        transportadoras = odoo.search_read(
            config['modelo_odoo'],
            filtros,
            fields=campos_busca,
            limit=args.limit or 100
        )

        resultado['sucesso'] = True
        resultado['total'] = len(transportadoras)
        resultado['transportadoras'] = transportadoras

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Consulta cadastros no Odoo (parceiros e transportadoras)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Buscar fornecedor por CNPJ
  python consulta.py --tipo partner --subtipo fornecedor --cnpj "18467441"

  # Buscar cliente por nome
  python consulta.py --tipo partner --subtipo cliente --nome "atacadao" --uf SP

  # Buscar parceiro com dados fiscais
  python consulta.py --tipo partner --cnpj "12345678" --fiscal --detalhes

  # Listar transportadoras ativas
  python consulta.py --tipo transportadora

  # Buscar transportadora por nome
  python consulta.py --tipo transportadora --nome "correios"

  # Buscar parceiro com endereco completo
  python consulta.py --tipo partner --nome "empresa" --endereco
        """
    )

    # Argumentos obrigatorios
    parser.add_argument('--tipo', required=True, choices=['partner', 'transportadora'],
                        help='Tipo de consulta (partner, transportadora)')

    # Argumentos para Partner
    parser.add_argument('--subtipo', choices=['fornecedor', 'cliente', 'todos'],
                        default='todos', help='Subtipo do parceiro')
    parser.add_argument('--cnpj', help='CNPJ ou CPF (aceita parcial)')
    parser.add_argument('--nome', help='Nome ou razao social (parcial)')
    parser.add_argument('--uf', help='Estado (UF)')
    parser.add_argument('--cidade', help='Cidade')
    parser.add_argument('--ie', help='Inscricao Estadual')
    parser.add_argument('--email', help='Email (parcial)')

    # Filtros gerais
    parser.add_argument('--inativos', action='store_true',
                        help='Incluir inativos na busca')
    parser.add_argument('--limit', type=int, default=100, help='Limite de resultados')

    # Opcoes de saida
    parser.add_argument('--endereco', action='store_true',
                        help='Incluir campos de endereco')
    parser.add_argument('--fiscal', action='store_true',
                        help='Incluir dados fiscais (IE, IM, regime)')
    parser.add_argument('--detalhes', action='store_true',
                        help='Incluir todos os campos mapeados')
    parser.add_argument('--json', action='store_true', help='Saida em JSON')

    args = parser.parse_args()

    # Executar consulta
    if args.tipo == 'partner':
        resultado = consultar_partner(args)
    elif args.tipo == 'transportadora':
        resultado = consultar_transportadora(args)
    else:
        resultado = {'sucesso': False, 'erro': f'Tipo desconhecido: {args.tipo}'}

    # Exibir resultado
    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    else:
        if resultado['sucesso']:
            print(f"\n{'='*60}")
            print(f"CONSULTA DE {args.tipo.upper()}")
            print(f"Total encontrado: {resultado['total']}")
            print(f"{'='*60}\n")

            if args.tipo == 'partner':
                for parceiro in resultado['parceiros'][:20]:
                    # Dados basicos
                    nome = parceiro.get('name', 'N/A')
                    cnpj = parceiro.get('l10n_br_cnpj') or parceiro.get('vat') or 'N/A'
                    email = parceiro.get('email') or ''
                    telefone = parceiro.get('phone') or parceiro.get('mobile') or ''
                    customer_rank = parceiro.get('customer_rank', 0)
                    supplier_rank = parceiro.get('supplier_rank', 0)

                    # Tipo
                    tipos = []
                    if customer_rank and customer_rank > 0:
                        tipos.append('Cliente')
                    if supplier_rank and supplier_rank > 0:
                        tipos.append('Fornecedor')
                    tipo_str = '/'.join(tipos) if tipos else 'Parceiro'

                    print(f"[{parceiro.get('id')}] {nome}")
                    print(f"  CNPJ/CPF: {cnpj} | Tipo: {tipo_str}")
                    if email:
                        print(f"  Email: {email}")
                    if telefone:
                        print(f"  Telefone: {telefone}")

                    # Endereco se solicitado
                    if getattr(args, 'endereco', False) or getattr(args, 'detalhes', False):
                        rua = parceiro.get('street') or ''
                        numero = parceiro.get('l10n_br_endereco_numero') or ''
                        bairro = parceiro.get('l10n_br_endereco_bairro') or ''
                        cidade = parceiro.get('city') or ''
                        uf = extrair_nome_many2one(parceiro.get('state_id'))
                        cep = parceiro.get('zip') or ''
                        if rua or cidade:
                            endereco_parts = [p for p in [rua, numero, bairro, cidade, uf, cep] if p]
                            print(f"  Endereco: {', '.join(endereco_parts)}")

                    # Dados fiscais se solicitado
                    if getattr(args, 'fiscal', False) or getattr(args, 'detalhes', False):
                        ie = parceiro.get('l10n_br_ie') or ''
                        im = parceiro.get('l10n_br_im') or ''
                        is_suframa = parceiro.get('l10n_br_is') or ''
                        regime = parceiro.get('l10n_br_regime_tributario') or ''
                        indicador_ie = parceiro.get('l10n_br_indicador_ie') or ''
                        situacao = parceiro.get('l10n_br_situacao_cadastral') or ''
                        posicao_fiscal = extrair_nome_many2one(parceiro.get('property_account_position_id'))

                        # Retencoes
                        pis_ret = parceiro.get('l10n_br_pis_ret_valor', 0)
                        cofins_ret = parceiro.get('l10n_br_cofins_ret_valor', 0)
                        csll_ret = parceiro.get('l10n_br_csll_ret_valor', 0)
                        irpj_ret = parceiro.get('l10n_br_irpj_ret_valor', 0)
                        icms_cred = parceiro.get('l10n_br_icms_credito_aliquota', 0)

                        if ie:
                            print(f"  IE: {ie}")
                        if im:
                            print(f"  IM: {im}")
                        if is_suframa:
                            print(f"  Suframa: {is_suframa}")
                        if regime:
                            regimes = {'1': 'Simples Nacional', '2': 'SN Exc', '3': 'Lucro Presumido/Real'}
                            regime_nome = regimes.get(str(regime), regime)
                            print(f"  Regime: {regime_nome}")
                        if indicador_ie:
                            ind_nomes = {'1': 'Contribuinte', '2': 'Isento', '9': 'Nao Contribuinte'}
                            ind_nome = ind_nomes.get(str(indicador_ie), indicador_ie)
                            print(f"  Indicador IE: {ind_nome}")
                        if posicao_fiscal:
                            print(f"  Posicao Fiscal: {posicao_fiscal}")
                        if icms_cred and icms_cred > 0:
                            print(f"  Aliq. Credito ICMS (SN): {icms_cred}%")
                        # Retencoes (apenas se houver valor)
                        retencoes = []
                        if pis_ret and pis_ret > 0:
                            retencoes.append(f"PIS:{pis_ret}")
                        if cofins_ret and cofins_ret > 0:
                            retencoes.append(f"COFINS:{cofins_ret}")
                        if csll_ret and csll_ret > 0:
                            retencoes.append(f"CSLL:{csll_ret}")
                        if irpj_ret and irpj_ret > 0:
                            retencoes.append(f"IRPJ:{irpj_ret}")
                        if retencoes:
                            print(f"  Retencoes Min: {', '.join(retencoes)}")

                    print()

                if resultado['total'] > 20:
                    print(f"... e mais {resultado['total'] - 20} parceiro(s)")

            elif args.tipo == 'transportadora':
                for transp in resultado['transportadoras'][:20]:
                    nome = transp.get('name', 'N/A')
                    ativo = 'Ativo' if transp.get('active') else 'Inativo'
                    tipo = transp.get('delivery_type', 'N/A')
                    preco = transp.get('fixed_price', 0)
                    margem = transp.get('margin', 0)
                    parceiro = extrair_nome_many2one(transp.get('l10n_br_partner_id'))

                    print(f"[{transp.get('id')}] {nome}")
                    print(f"  Status: {ativo} | Tipo: {tipo}")
                    if preco:
                        print(f"  Preco fixo: R$ {preco:,.2f}")
                    if margem:
                        print(f"  Margem: {margem}%")
                    if parceiro:
                        print(f"  Parceiro: {parceiro}")

                    # Detalhes se solicitado
                    if getattr(args, 'detalhes', False):
                        desc = transp.get('carrier_description') or ''
                        if desc:
                            print(f"  Descricao: {desc[:100]}...")

                    print()

                if resultado['total'] > 20:
                    print(f"... e mais {resultado['total'] - 20} transportadora(s)")

        else:
            print(f"\nERRO: {resultado['erro']}")


if __name__ == '__main__':
    main()
