#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalização de Entidades para Rastreamento Odoo

Transforma menções humanas em identificadores do Odoo:
- "Atacadão" → partner_id(s)
- "NF 12345" → número da NF
- "PO00789" → purchase.order
- "VCD123", "VFB456", "VSC789" → sale.order (prefixos de filial)
- "35250112345..." → chave NF-e

Autor: Sistema de Fretes
Data: 16/12/2025
"""

import sys
import os
import re
import argparse
import json
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# ==============================================================================
# PADRÕES DE IDENTIFICAÇÃO
# ==============================================================================

PATTERNS = {
    'chave_nfe': r'^[0-9]{44}$',  # Chave NF-e 44 dígitos
    'cnpj': r'^[0-9]{8,14}$',  # CNPJ (8-14 dígitos)
    'cnpj_formatado': r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',  # CNPJ formatado
    'po': r'^PO\d+$',  # Pedido de compra (PO00123)
    # Pedidos de venda: VCD (CD), VFB (FB), VSC (SC) - prefixos de filial
    'so_filial': r'^V?(CD|FB|SC)\d+$',  # VCD123, VFB456, VSC789 ou CD123, FB456
    'so_generico': r'^SO?\d+$',  # SO00456 ou S00456 (genérico)
    'nf_numero': r'^(?:NF|NFE?|NOTA)\s*:?\s*(\d+)$',  # NF 12345, NFe: 12345
    'nf_serie': r'^(\d+)[/-](\d+)$',  # 12345/1 ou 12345-1 (número/série)
    'numero_puro': r'^\d{1,9}$',  # Número puro (1-9 dígitos)
}

# Mapeamento de prefixos de filial
FILIAIS = {
    'CD': 'Centro de Distribuição',
    'FB': 'Filial FB',
    'SC': 'Filial SC',
}


# ==============================================================================
# FUNÇÕES DE DETECÇÃO
# ==============================================================================

def limpar_texto(texto: str) -> str:
    """Remove espaços extras e normaliza."""
    return texto.strip().upper()


def limpar_cnpj(valor: str) -> str:
    """Remove pontuação do CNPJ."""
    return re.sub(r'[^0-9]', '', valor)


def formatar_cnpj_parcial(numeros: str) -> str:
    """
    Formata CNPJ com pontuação para busca no Odoo.
    O Odoo armazena CNPJ formatado: 18.467.441/0001-63
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


def detectar_tipo_entrada(texto: str) -> Tuple[str, Any]:
    """
    Detecta o tipo de entrada do usuário.

    Retorna: (tipo, valor_normalizado)
    """
    texto_limpo = limpar_texto(texto)

    # Chave NF-e (44 dígitos)
    texto_numeros = re.sub(r'[^0-9]', '', texto)
    if len(texto_numeros) == 44:
        return ('chave_nfe', texto_numeros)

    # Pedido de Compra (PO00123)
    if re.match(PATTERNS['po'], texto_limpo, re.IGNORECASE):
        return ('po', texto_limpo)

    # Pedido de Venda com prefixo de filial (VCD123, VFB456, VSC789, CD123, FB456, SC789)
    match_filial = re.match(PATTERNS['so_filial'], texto_limpo, re.IGNORECASE)
    if match_filial:
        # Normaliza: se não começa com V, adiciona
        if not texto_limpo.startswith('V'):
            texto_limpo = 'V' + texto_limpo
        return ('so', texto_limpo)

    # Pedido de Venda genérico (SO00456 ou S00456) - menos comum
    if re.match(PATTERNS['so_generico'], texto_limpo, re.IGNORECASE):
        if texto_limpo.startswith('S') and not texto_limpo.startswith('SO'):
            texto_limpo = 'SO' + texto_limpo[1:]
        return ('so', texto_limpo)

    # NF com número explícito (NF 12345, NFe: 12345)
    match_nf = re.match(PATTERNS['nf_numero'], texto_limpo, re.IGNORECASE)
    if match_nf:
        return ('nf_numero', match_nf.group(1))

    # NF com série (12345/1)
    match_serie = re.match(PATTERNS['nf_serie'], texto_limpo)
    if match_serie:
        return ('nf_serie', {'numero': match_serie.group(1), 'serie': match_serie.group(2)})

    # CNPJ formatado
    if re.match(PATTERNS['cnpj_formatado'], texto):
        cnpj_limpo = limpar_cnpj(texto)
        return ('cnpj', cnpj_limpo)

    # CNPJ numérico (8-14 dígitos)
    if re.match(PATTERNS['cnpj'], texto_numeros) and len(texto_numeros) >= 8:
        return ('cnpj', texto_numeros)

    # Número puro (pode ser NF ou ID)
    if re.match(PATTERNS['numero_puro'], texto_limpo):
        return ('numero', texto_limpo)

    # Fallback: nome de parceiro
    return ('parceiro', texto)


# ==============================================================================
# FUNÇÕES DE RESOLUÇÃO (BUSCAM NO ODOO)
# ==============================================================================

def get_odoo_connection():
    """Obtém conexão com Odoo."""
    from app.odoo.utils.connection import get_odoo_connection as get_conn
    return get_conn()


def resolver_parceiro(odoo, termo: str, limit: int = 10) -> Dict[str, Any]:
    """
    Resolve nome de parceiro para IDs.

    Busca por nome OU CNPJ parcial.
    """
    resultado = {
        'tipo': 'parceiro',
        'termo_original': termo,
        'encontrados': [],
        'total': 0,
        'sucesso': False,
        'erro': None
    }

    try:
        # Tentar buscar por nome
        parceiros = odoo.search_read(
            'res.partner',
            [('name', 'ilike', termo)],
            fields=['id', 'name', 'l10n_br_cnpj', 'is_company', 'customer_rank', 'supplier_rank'],
            limit=limit
        )

        if not parceiros:
            # Tentar buscar por CNPJ parcial
            termo_numeros = re.sub(r'[^0-9]', '', termo)
            if len(termo_numeros) >= 4:
                parceiros = odoo.search_read(
                    'res.partner',
                    [('l10n_br_cnpj', 'ilike', termo_numeros)],
                    fields=['id', 'name', 'l10n_br_cnpj', 'is_company', 'customer_rank', 'supplier_rank'],
                    limit=limit
                )

        resultado['encontrados'] = parceiros
        resultado['total'] = len(parceiros)
        resultado['sucesso'] = True

        if parceiros:
            resultado['ids'] = [p['id'] for p in parceiros]
            resultado['filtro'] = [('partner_id', 'in', resultado['ids'])]

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def resolver_cnpj(odoo, cnpj: str, limit: int = 10) -> Dict[str, Any]:
    """
    Resolve CNPJ para parceiro(s).
    """
    resultado = {
        'tipo': 'cnpj',
        'termo_original': cnpj,
        'cnpj_formatado': formatar_cnpj_parcial(cnpj),
        'encontrados': [],
        'total': 0,
        'sucesso': False,
        'erro': None
    }

    try:
        # Buscar parceiro pelo CNPJ
        parceiros = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', 'ilike', resultado['cnpj_formatado'])],
            fields=['id', 'name', 'l10n_br_cnpj', 'is_company'],
            limit=limit
        )

        resultado['encontrados'] = parceiros
        resultado['total'] = len(parceiros)
        resultado['sucesso'] = True

        if parceiros:
            resultado['ids'] = [p['id'] for p in parceiros]
            resultado['filtro'] = [('partner_id', 'in', resultado['ids'])]

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def resolver_po(odoo, numero_po: str) -> Dict[str, Any]:
    """
    Resolve número de PO para purchase.order.
    """
    resultado = {
        'tipo': 'po',
        'termo_original': numero_po,
        'encontrados': [],
        'total': 0,
        'sucesso': False,
        'erro': None
    }

    try:
        pos = odoo.search_read(
            'purchase.order',
            [('name', 'ilike', numero_po)],
            fields=['id', 'name', 'partner_id', 'state', 'date_order', 'amount_total',
                   'requisition_id', 'invoice_ids', 'invoice_status'],
            limit=10
        )

        resultado['encontrados'] = pos
        resultado['total'] = len(pos)
        resultado['sucesso'] = True

        if pos:
            resultado['ids'] = [p['id'] for p in pos]

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def resolver_so(odoo, numero_so: str) -> Dict[str, Any]:
    """
    Resolve número de SO para sale.order.

    Suporta:
    - VCD123, VFB456, VSC789 (prefixos de filial)
    - SO00456 (genérico)
    """
    resultado = {
        'tipo': 'so',
        'termo_original': numero_so,
        'encontrados': [],
        'total': 0,
        'sucesso': False,
        'erro': None
    }

    try:
        sos = odoo.search_read(
            'sale.order',
            [('name', 'ilike', numero_so)],
            fields=['id', 'name', 'partner_id', 'state', 'date_order', 'amount_total',
                   'picking_ids', 'invoice_ids', 'invoice_status'],
            limit=10
        )

        resultado['encontrados'] = sos
        resultado['total'] = len(sos)
        resultado['sucesso'] = True

        if sos:
            resultado['ids'] = [s['id'] for s in sos]

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def resolver_chave_nfe(odoo, chave: str) -> Dict[str, Any]:
    """
    Resolve chave NF-e para DFE e/ou account.move.
    """
    resultado = {
        'tipo': 'chave_nfe',
        'termo_original': chave,
        'dfe': None,
        'fatura': None,
        'sucesso': False,
        'erro': None
    }

    try:
        # Buscar no DFE
        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [('protnfe_infnfe_chnfe', '=', chave)],
            fields=['id', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_emit_xnome',
                   'nfe_infnfe_ide_finnfe', 'nfe_infnfe_total_icmstot_vnf',
                   'purchase_id', 'invoice_ids', 'is_cte'],
            limit=1
        )

        if dfes:
            resultado['dfe'] = dfes[0]

        # Buscar na fatura (account.move)
        faturas = odoo.search_read(
            'account.move',
            [('l10n_br_chave_nf', '=', chave)],
            fields=['id', 'name', 'partner_id', 'move_type', 'amount_total',
                   'invoice_origin', 'state', 'payment_state'],
            limit=1
        )

        if faturas:
            resultado['fatura'] = faturas[0]

        resultado['sucesso'] = True

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def resolver_nf_numero(odoo, numero: str, serie: str = None) -> Dict[str, Any]:
    """
    Resolve número de NF para DFE e/ou account.move.
    """
    resultado = {
        'tipo': 'nf_numero',
        'termo_original': numero,
        'serie': serie,
        'dfe': [],
        'faturas': [],
        'sucesso': False,
        'erro': None
    }

    try:
        # Filtros para DFE
        filtros_dfe = [('nfe_infnfe_ide_nnf', '=', numero)]
        if serie:
            filtros_dfe.append(('nfe_infnfe_ide_serie', '=', serie))

        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtros_dfe,
            fields=['id', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                   'nfe_infnfe_emit_xnome', 'nfe_infnfe_emit_cnpj',
                   'nfe_infnfe_ide_finnfe', 'nfe_infnfe_total_icmstot_vnf',
                   'nfe_infnfe_ide_dhemi', 'protnfe_infnfe_chnfe',
                   'purchase_id', 'invoice_ids', 'is_cte'],
            limit=20
        )
        resultado['dfe'] = dfes

        # Buscar faturas pelo número no name ou ref
        faturas = odoo.search_read(
            'account.move',
            ['|', ('name', 'ilike', numero), ('ref', 'ilike', numero)],
            fields=['id', 'name', 'ref', 'partner_id', 'move_type',
                   'amount_total', 'invoice_origin', 'state', 'l10n_br_chave_nf'],
            limit=20
        )
        resultado['faturas'] = faturas

        resultado['sucesso'] = True
        resultado['total'] = len(dfes) + len(faturas)

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


# ==============================================================================
# FUNÇÃO PRINCIPAL DE NORMALIZAÇÃO
# ==============================================================================

def normalizar_entidade(odoo, entrada: str) -> Dict[str, Any]:
    """
    Normaliza uma entrada do usuário para identificadores do Odoo.

    Exemplos:
    - "Atacadão" → parceiros com esse nome
    - "18467441" → parceiros com esse CNPJ
    - "NF 12345" → DFE/faturas com esse número
    - "PO00789" → purchase.order
    - "VCD123", "VFB456", "VSC789" → sale.order (filiais CD, FB, SC)
    - "3525..." → chave NF-e
    """
    tipo, valor = detectar_tipo_entrada(entrada)

    if tipo == 'parceiro':
        return resolver_parceiro(odoo, valor)

    elif tipo == 'cnpj':
        return resolver_cnpj(odoo, valor)

    elif tipo == 'po':
        return resolver_po(odoo, valor)

    elif tipo == 'so':
        return resolver_so(odoo, valor)

    elif tipo == 'chave_nfe':
        return resolver_chave_nfe(odoo, valor)

    elif tipo == 'nf_numero':
        return resolver_nf_numero(odoo, valor)

    elif tipo == 'nf_serie':
        return resolver_nf_numero(odoo, valor['numero'], valor['serie'])

    elif tipo == 'numero':
        # Número puro: tentar como NF primeiro, depois como ID
        resultado = resolver_nf_numero(odoo, valor)
        if resultado['total'] == 0:
            # Tentar como parceiro (ID)
            resultado = resolver_parceiro(odoo, valor)
        return resultado

    return {
        'tipo': 'desconhecido',
        'termo_original': entrada,
        'sucesso': False,
        'erro': f'Não foi possível identificar o tipo de entrada: {entrada}'
    }


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Normaliza entidades do usuário para identificadores Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Normalizar nome de cliente
  python normalizar.py "Atacadão"

  # Normalizar CNPJ
  python normalizar.py "18467441"
  python normalizar.py "18.467.441/0001-63"

  # Normalizar número de NF
  python normalizar.py "NF 12345"
  python normalizar.py "12345/1"

  # Normalizar PO
  python normalizar.py "PO00789"

  # Normalizar SO (com prefixo de filial)
  python normalizar.py "VCD123"   # Filial CD
  python normalizar.py "VFB456"   # Filial FB
  python normalizar.py "VSC789"   # Filial SC

  # Normalizar chave NF-e
  python normalizar.py "35251218467441000163550010000123451000000017"
        """
    )

    parser.add_argument('entrada', help='Termo a normalizar (nome, CNPJ, NF, PO, SO, chave)')
    parser.add_argument('--json', action='store_true', help='Saída em JSON')
    parser.add_argument('--detectar', action='store_true', help='Apenas detectar tipo (sem buscar)')

    args = parser.parse_args()

    if args.detectar:
        tipo, valor = detectar_tipo_entrada(args.entrada)
        resultado = {
            'entrada': args.entrada,
            'tipo_detectado': tipo,
            'valor_normalizado': valor
        }
    else:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            print("ERRO: Falha na autenticação com Odoo")
            sys.exit(1)

        resultado = normalizar_entidade(odoo, args.entrada)

    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    else:
        if args.detectar:
            print(f"\nEntrada: {resultado['entrada']}")
            print(f"Tipo detectado: {resultado['tipo_detectado']}")
            print(f"Valor normalizado: {resultado['valor_normalizado']}")
        else:
            print(f"\n{'='*60}")
            print(f"NORMALIZAÇÃO: {args.entrada}")
            print(f"Tipo: {resultado.get('tipo', 'N/A')}")
            print(f"{'='*60}\n")

            if resultado.get('sucesso'):
                total = resultado.get('total', len(resultado.get('encontrados', [])))
                print(f"Encontrados: {total} resultado(s)")

                for item in resultado.get('encontrados', [])[:10]:
                    nome = item.get('name', 'N/A')
                    if isinstance(nome, (list, tuple)):
                        nome = nome[1] if len(nome) > 1 else nome[0]
                    cnpj = item.get('l10n_br_cnpj', '')
                    print(f"  [{item.get('id')}] {nome}" + (f" - {cnpj}" if cnpj else ""))

                if resultado.get('dfe'):
                    dfe = resultado['dfe']
                    if isinstance(dfe, list):
                        for d in dfe[:5]:
                            print(f"  DFE [{d.get('id')}] NF {d.get('nfe_infnfe_ide_nnf')} - {d.get('nfe_infnfe_emit_xnome')}")
                    else:
                        print(f"  DFE [{dfe.get('id')}] NF {dfe.get('nfe_infnfe_ide_nnf')} - {dfe.get('nfe_infnfe_emit_xnome')}")

                if resultado.get('fatura'):
                    fat = resultado['fatura']
                    print(f"  Fatura [{fat.get('id')}] {fat.get('name')} - {fat.get('move_type')}")

                if resultado.get('faturas'):
                    for fat in resultado['faturas'][:5]:
                        print(f"  Fatura [{fat.get('id')}] {fat.get('name')} - {fat.get('move_type')}")
            else:
                print(f"ERRO: {resultado.get('erro', 'Nenhum resultado encontrado')}")


if __name__ == '__main__':
    main()
