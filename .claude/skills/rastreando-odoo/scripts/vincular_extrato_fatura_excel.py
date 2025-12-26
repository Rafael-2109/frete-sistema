#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vinculação de Extrato Bancário com Fatura (Contas a Pagar) via Excel
====================================================================

Processa planilha Excel para vincular linhas de extrato bancário com
faturas/títulos a pagar no Odoo.

REGRAS:
1. A vinculação só é válida se a pesquisa retornar EXATAMENTE 1 resultado
2. Parâmetros da fatura: FATURA (col H), CNPJ (col I), FATURA.1 (col K),
   PARCELA (col L), VALOR (col M)
3. Parâmetros do extrato: ID (col A), Movimento (col T)

FLUXO:
1. Ler Excel com dados de vinculação
2. Para cada linha:
   a. Buscar título no Odoo pelos parâmetros (deve retornar 1 resultado)
   b. Buscar linha de extrato no Odoo pelo ID ou Movimento
   c. Vincular extrato com fatura (criar payment + reconciliar)
3. Gerar relatório de processamento

Autor: Sistema de Fretes
Data: 2025-12-19
"""

import sys
import os
import argparse
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# ==============================================================================
# DATACLASSES
# ==============================================================================

@dataclass
class LinhaExcel:
    """Representa uma linha do Excel para processamento."""
    linha_num: int
    # Extrato
    extrato_id: int
    movimento: str
    # Fatura
    fatura_name: str
    cnpj: str
    fatura_id: Optional[int]
    parcela: int
    valor: float
    # Resultado
    status: str = 'PENDENTE'
    mensagem: str = ''
    titulo_odoo_id: Optional[int] = None
    extrato_odoo_id: Optional[int] = None
    payment_id: Optional[int] = None
    full_reconcile_id: Optional[int] = None


@dataclass
class ResultadoProcessamento:
    """Resultado do processamento completo."""
    total_linhas: int = 0
    processadas: int = 0
    sucesso: int = 0
    erro: int = 0
    ignoradas: int = 0
    linhas: List[Dict] = None # type: ignore

    def __post_init__(self):
        if self.linhas is None:
            self.linhas = []


# ==============================================================================
# CONEXÃO ODOO
# ==============================================================================

def get_odoo_connection():
    """Obtém conexão com Odoo."""
    from app.odoo.utils.connection import get_odoo_connection as get_conn
    return get_conn()


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def extrair_id(valor):
    """Extrai ID de campo many2one."""
    if isinstance(valor, (list, tuple)) and len(valor) > 0:
        return valor[0]
    return valor


def extrair_nome(valor):
    """Extrai nome de campo many2one."""
    if isinstance(valor, (list, tuple)) and len(valor) > 1:
        return valor[1]
    return str(valor) if valor else ''


def limpar_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ."""
    if not cnpj:
        return ''
    return re.sub(r'\D', '', str(cnpj))


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ para padrão XX.XXX.XXX/XXXX-XX."""
    cnpj_limpo = limpar_cnpj(cnpj)
    if len(cnpj_limpo) == 14:
        return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
    return cnpj_limpo


def prefixo_cnpj(cnpj: str) -> str:
    """Retorna os 8 primeiros dígitos do CNPJ (raiz)."""
    cnpj_limpo = limpar_cnpj(cnpj)
    return cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else cnpj_limpo


def chunked(lista: List, tamanho: int):
    """Divide lista em chunks de tamanho especificado."""
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]


# ==============================================================================
# FUNÇÕES DE BATCH (OTIMIZAÇÃO)
# ==============================================================================

def batch_buscar_extratos(odoo, extrato_ids: List[int]) -> Dict[int, Dict]:
    """
    Busca múltiplos extratos de uma vez.

    Returns:
        Dict mapeando extrato_id -> dados do extrato
    """
    campos = [
        'id', 'date', 'payment_ref', 'amount', 'partner_id',
        'statement_id', 'journal_id', 'move_id',
        'is_reconciled', 'amount_residual', 'company_id'
    ]

    resultado = {}

    # Buscar em chunks de 100
    for chunk in chunked(list(set(extrato_ids)), 100):
        extratos = odoo.search_read(
            'account.bank.statement.line',
            [['id', 'in', chunk]],
            fields=campos,
            limit=len(chunk)
        )
        for ext in extratos:
            resultado[ext['id']] = ext

    return resultado


def batch_buscar_titulos_por_id(odoo, titulo_ids: List[int]) -> Dict[int, Dict]:
    """
    Busca múltiplos títulos por ID de uma vez.

    Returns:
        Dict mapeando titulo_id -> dados do título
    """
    campos = [
        'id', 'name', 'debit', 'credit', 'balance',
        'amount_residual', 'amount_residual_currency',
        'reconciled', 'matched_credit_ids', 'matched_debit_ids',
        'full_reconcile_id', 'matching_number',
        'date_maturity', 'partner_id', 'move_id', 'company_id',
        'l10n_br_paga', 'l10n_br_cobranca_parcela', 'x_studio_nf_e',
        'account_id', 'account_type'
    ]

    resultado = {}

    # Filtrar IDs válidos (XML-RPC tem limite de 2^31-1)
    MAX_INT = 2147483647
    ids_validos = [tid for tid in set(titulo_ids) if tid and isinstance(tid, int) and 0 < tid < MAX_INT]

    # Buscar em chunks de 100
    for chunk in chunked(ids_validos, 100):
        titulos = odoo.search_read(
            'account.move.line',
            [
                ['id', 'in', chunk],
                ['account_type', '=', 'liability_payable'],
                ['parent_state', '=', 'posted']
            ],
            fields=campos,
            limit=len(chunk)
        )
        for tit in titulos:
            resultado[tit['id']] = tit

    return resultado


def batch_buscar_linhas_debito_extratos(odoo, move_ids: List[int]) -> Dict[int, int]:
    """
    Busca linhas de débito de múltiplos moves de extrato.

    Returns:
        Dict mapeando move_id -> line_id (linha de débito)
    """
    CONTA_TRANSITORIA = 22199
    CONTA_PENDENTES = 26868

    resultado = {}

    for chunk in chunked(list(set(move_ids)), 100):
        linhas = odoo.search_read(
            'account.move.line',
            [
                ['move_id', 'in', chunk],
                ['debit', '>', 0],
                ['reconciled', '=', False]
            ],
            fields=['id', 'move_id', 'debit', 'account_id'],
            limit=len(chunk) * 5
        )

        # Agrupar por move_id e preferir conta PENDENTES/TRANSITÓRIA
        por_move = {}
        for ln in linhas:
            move_id = extrair_id(ln.get('move_id'))
            if move_id not in por_move:
                por_move[move_id] = []
            por_move[move_id].append(ln)

        for move_id, lns in por_move.items():
            # Preferir linha na conta PENDENTES ou TRANSITÓRIA
            escolhida = None
            for ln in lns:
                account_id = extrair_id(ln.get('account_id'))
                if account_id in [CONTA_TRANSITORIA, CONTA_PENDENTES]:
                    escolhida = ln['id']
                    break
            if not escolhida and lns:
                escolhida = lns[0]['id']
            if escolhida:
                resultado[move_id] = escolhida

    return resultado


def batch_write_partner_statement_lines(odoo, updates: List[Tuple[int, int]]) -> None:
    """
    Atualiza partner_id em múltiplas statement lines.

    Args:
        updates: Lista de (statement_line_id, partner_id)
    """
    # Agrupar por partner_id para fazer menos chamadas
    por_partner = {}
    for stmt_id, partner_id in updates:
        if partner_id not in por_partner:
            por_partner[partner_id] = []
        por_partner[partner_id].append(stmt_id)

    for partner_id, stmt_ids in por_partner.items():
        try:
            odoo.execute_kw(
                'account.bank.statement.line',
                'write',
                [stmt_ids, {'partner_id': partner_id}]
            )
        except Exception as e:
            if "cannot marshal None" not in str(e):
                print(f"    [AVISO] Erro batch partner stmt: {e}")


def batch_write_conta_pendentes(odoo, line_ids: List[int]) -> None:
    """
    Atualiza conta para PENDENTES em múltiplas linhas.
    """
    CONTA_PENDENTES = 26868

    if not line_ids:
        return

    try:
        odoo.execute_kw(
            'account.move.line',
            'write',
            [line_ids, {'account_id': CONTA_PENDENTES}]
        )
    except Exception as e:
        if "cannot marshal None" not in str(e):
            print(f"    [AVISO] Erro batch conta: {e}")


def batch_write_partner_move_lines(odoo, updates: List[Tuple[int, int]]) -> None:
    """
    Atualiza partner_id em múltiplas move lines.

    Args:
        updates: Lista de (move_id, partner_id)
    """
    # Primeiro buscar todas as linhas sem partner dos moves
    move_ids = list(set([m for m, p in updates]))
    partner_por_move = {m: p for m, p in updates}

    for chunk in chunked(move_ids, 50):
        linhas = odoo.search_read(
            'account.move.line',
            [
                ['move_id', 'in', chunk],
                ['partner_id', '=', False]
            ],
            fields=['id', 'move_id'],
            limit=len(chunk) * 10
        )

        # Agrupar por partner para menos chamadas
        por_partner = {}
        for ln in linhas:
            move_id = extrair_id(ln.get('move_id'))
            partner_id = partner_por_move.get(move_id)
            if partner_id:
                if partner_id not in por_partner:
                    por_partner[partner_id] = []
                por_partner[partner_id].append(ln['id'])

        for partner_id, line_ids in por_partner.items():
            try:
                odoo.execute_kw(
                    'account.move.line',
                    'write',
                    [line_ids, {'partner_id': partner_id}]
                )
            except Exception as e:
                if "cannot marshal None" not in str(e):
                    print(f"    [AVISO] Erro batch partner lines: {e}")


# ==============================================================================
# LEITURA DO EXCEL
# ==============================================================================

def ler_excel(caminho: str) -> List[LinhaExcel]:
    """
    Lê o Excel e retorna lista de LinhaExcel.

    Mapeamento de colunas:
    - A (0): ID do extrato
    - H (7): FATURA (name)
    - I (8): CNPJ
    - K (10): FATURA.1 (ID?)
    - L (11): PARCELA
    - M (12): VALOR
    - T (19): Movimento
    """
    import pandas as pd

    print(f"\n{'='*70}")
    print(f"LENDO EXCEL: {caminho}")
    print(f"{'='*70}")

    df = pd.read_excel(caminho)

    print(f"Total de linhas: {len(df)}")
    print(f"Colunas: {list(df.columns)}")

    linhas = []

    for idx, row in df.iterrows():
        try:
            # Extrair dados
            extrato_id = int(row.iloc[0]) if pd.notna(row.iloc[0]) else None
            fatura_name = str(row.iloc[7]) if pd.notna(row.iloc[7]) else ''
            cnpj = str(row.iloc[8]) if pd.notna(row.iloc[8]) else ''
            fatura_id_raw = row.iloc[10] if pd.notna(row.iloc[10]) else None
            parcela = int(row.iloc[11]) if pd.notna(row.iloc[11]) else 1
            valor = float(row.iloc[12]) if pd.notna(row.iloc[12]) else 0.0
            movimento = str(row.iloc[19]) if pd.notna(row.iloc[19]) else ''

            # Converter fatura_id
            fatura_id = None
            if fatura_id_raw is not None:
                try:
                    fatura_id = int(fatura_id_raw)
                except (ValueError, TypeError):
                    pass

            # Validar dados mínimos
            if not extrato_id:
                continue

            if not fatura_name and not fatura_id and not cnpj:
                continue

            linha = LinhaExcel(
                linha_num=idx + 2,  # +2 porque Excel começa em 1 e tem cabeçalho # type: ignore
                extrato_id=extrato_id,
                movimento=movimento,
                fatura_name=fatura_name,
                cnpj=cnpj,
                fatura_id=fatura_id,
                parcela=parcela,
                valor=valor
            )
            linhas.append(linha)

        except Exception as e:
            print(f"  Erro na linha {idx + 2}: {e}") # type: ignore
            continue

    print(f"Linhas válidas para processar: {len(linhas)}")
    return linhas


# ==============================================================================
# BUSCA DE TÍTULO NO ODOO
# ==============================================================================

def buscar_titulo_odoo(
    odoo,
    fatura_name: str,
    cnpj: str,
    fatura_id: Optional[int],
    parcela: int,
    valor: float,
    tolerancia_valor: float = 0.05
) -> Tuple[Optional[Dict], str]:
    """
    Busca título a pagar no Odoo usando múltiplos critérios.

    Estratégias de busca (em ordem):
    1. Por ID direto (se fatura_id fornecido)
    2. Por nome da fatura + parcela
    3. Por CNPJ + parcela + valor aproximado

    Returns:
        Tuple com (titulo_dict ou None, mensagem)
    """
    campos = [
        'id', 'name', 'debit', 'credit', 'balance',
        'amount_residual', 'amount_residual_currency',
        'reconciled', 'matched_credit_ids', 'matched_debit_ids',
        'full_reconcile_id', 'matching_number',
        'date_maturity', 'partner_id', 'move_id', 'company_id',
        'l10n_br_paga', 'l10n_br_cobranca_parcela', 'x_studio_nf_e',
        'account_id', 'account_type'
    ]

    titulos_encontrados = []
    estrategia = ''

    # =========================================================================
    # ESTRATÉGIA 1: Busca por ID direto
    # =========================================================================
    MAX_INT = 2147483647  # Limite XML-RPC
    if fatura_id and isinstance(fatura_id, int) and 0 < fatura_id < MAX_INT:
        titulos = odoo.search_read(
            'account.move.line',
            [
                ['id', '=', fatura_id],
                ['account_type', '=', 'liability_payable'],
                ['parent_state', '=', 'posted']
            ],
            fields=campos,
            limit=5
        )
        if titulos:
            titulos_encontrados = titulos
            estrategia = 'ID_DIRETO'

    # =========================================================================
    # ESTRATÉGIA 2: Busca por nome da fatura + parcela (por ordem de vencimento)
    # =========================================================================
    if not titulos_encontrados and fatura_name:
        # Buscar TODOS os títulos da fatura
        titulos = odoo.search_read(
            'account.move.line',
            [
                '|',
                ['move_id.name', 'ilike', fatura_name],
                ['x_studio_nf_e', 'ilike', fatura_name],
                ['account_type', '=', 'liability_payable'],
                ['parent_state', '=', 'posted']
            ],
            fields=campos,
            limit=20
        )

        if titulos:
            # Primeiro tenta pelo campo l10n_br_cobranca_parcela (se estiver preenchido)
            titulos_parcela_exata = [t for t in titulos if t.get('l10n_br_cobranca_parcela') == parcela]
            if titulos_parcela_exata:
                titulos_encontrados = titulos_parcela_exata
                estrategia = 'FATURA_NAME_PARCELA_CAMPO'
            else:
                # Fallback: usa ordem de vencimento (parcela 1 = índice 0, parcela 2 = índice 1, etc.)
                # Ordenar por vencimento em Python
                titulos_ordenados = sorted(titulos, key=lambda t: (t.get('date_maturity') or '', t.get('id', 0)))
                indice = parcela - 1  # parcela 1 = índice 0
                if 0 <= indice < len(titulos_ordenados):
                    titulos_encontrados = [titulos_ordenados[indice]]
                    estrategia = 'FATURA_NAME_PARCELA_ORDEM'

    # =========================================================================
    # ESTRATÉGIA 3: Busca por CNPJ + valor (sem depender do campo parcela)
    # =========================================================================
    if not titulos_encontrados and cnpj:
        cnpj_limpo = limpar_cnpj(cnpj)
        cnpj_prefixo = prefixo_cnpj(cnpj)

        # Primeiro, buscar parceiro pelo CNPJ
        parceiros = odoo.search_read(
            'res.partner',
            [
                '|',
                ['l10n_br_cnpj', 'ilike', cnpj_limpo],
                ['l10n_br_cnpj', 'ilike', cnpj_prefixo]
            ],
            fields=['id', 'name', 'l10n_br_cnpj'],
            limit=10
        )

        if parceiros:
            partner_ids = [p['id'] for p in parceiros]

            # Buscar títulos do parceiro com valor aproximado
            valor_min = valor - tolerancia_valor
            valor_max = valor + tolerancia_valor

            titulos = odoo.search_read(
                'account.move.line',
                [
                    ['partner_id', 'in', partner_ids],
                    ['account_type', '=', 'liability_payable'],
                    ['parent_state', '=', 'posted'],
                    ['credit', '>=', valor_min],
                    ['credit', '<=', valor_max]
                ],
                fields=campos,
                limit=20
            )

            if titulos:
                # Primeiro tenta pelo campo l10n_br_cobranca_parcela (se estiver preenchido)
                titulos_parcela_exata = [t for t in titulos if t.get('l10n_br_cobranca_parcela') == parcela]
                if titulos_parcela_exata:
                    titulos_encontrados = titulos_parcela_exata
                    estrategia = 'CNPJ_VALOR_PARCELA_CAMPO'
                elif len(titulos) == 1:
                    # Se só tem 1 título com esse valor, usa ele
                    titulos_encontrados = titulos
                    estrategia = 'CNPJ_VALOR_UNICO'
                else:
                    # Múltiplos títulos com mesmo valor - tentar filtrar por parcela via ordem
                    # Agrupar por fatura e pegar a N-ésima parcela de cada
                    # Isso é mais complexo, então mantemos como múltiplos
                    titulos_encontrados = titulos
                    estrategia = 'CNPJ_VALOR_MULTIPLOS'

    # =========================================================================
    # VALIDAÇÃO: Deve retornar EXATAMENTE 1 resultado
    # =========================================================================
    if not titulos_encontrados:
        return None, "Nenhum título encontrado"

    if len(titulos_encontrados) > 1:
        # Tentar filtrar por valor exato
        titulos_exatos = [
            t for t in titulos_encontrados
            if abs(t.get('credit', 0) - valor) < 0.02
        ]

        if len(titulos_exatos) == 1:
            return titulos_exatos[0], f"{estrategia}+VALOR_EXATO"

        # Múltiplos resultados - não pode vincular
        ids_encontrados = [t['id'] for t in titulos_encontrados]
        return None, f"Múltiplos títulos encontrados ({len(titulos_encontrados)}): {ids_encontrados}"

    return titulos_encontrados[0], estrategia


# ==============================================================================
# BUSCA DE EXTRATO NO ODOO
# ==============================================================================

def buscar_extrato_odoo(
    odoo,
    extrato_id: int,
    movimento: str
) -> Tuple[Optional[Dict], str]:
    """
    Busca linha de extrato bancário no Odoo.

    Estratégias:
    1. Por ID direto (account.bank.statement.line.id)
    2. Por movimento (move_id.name)

    Returns:
        Tuple com (extrato_dict ou None, mensagem)
    """
    campos = [
        'id', 'date', 'payment_ref', 'amount', 'partner_id',
        'statement_id', 'journal_id', 'move_id',
        'is_reconciled', 'amount_residual', 'company_id'
    ]

    # =========================================================================
    # ESTRATÉGIA 1: Por ID direto
    # =========================================================================
    extratos = odoo.search_read(
        'account.bank.statement.line',
        [['id', '=', extrato_id]],
        fields=campos,
        limit=1
    )

    if extratos:
        return extratos[0], 'ID_DIRETO'

    # =========================================================================
    # ESTRATÉGIA 2: Por movimento (move_id.name)
    # =========================================================================
    if movimento:
        extratos = odoo.search_read(
            'account.bank.statement.line',
            [['move_id.name', '=', movimento]],
            fields=campos,
            limit=5
        )

        if len(extratos) == 1:
            return extratos[0], 'MOVIMENTO'
        elif len(extratos) > 1:
            return None, f"Múltiplos extratos pelo movimento ({len(extratos)})"

    return None, "Extrato não encontrado"


# ==============================================================================
# BUSCA DE LINHAS PARA RECONCILIAÇÃO
# ==============================================================================

def buscar_linha_debito_extrato(odoo, move_id: int) -> Optional[int]:
    """
    Busca a linha de DÉBITO do extrato (conta TRANSITÓRIA ou PENDENTES).
    Esta é a linha que será reconciliada com o payment/título.
    """
    CONTA_TRANSITORIA = 22199
    CONTA_PAGAMENTOS_PENDENTES = 26868

    linhas = odoo.search_read(
        'account.move.line',
        [
            ['move_id', '=', move_id],
            ['debit', '>', 0],
            ['reconciled', '=', False]
        ],
        fields=['id', 'debit', 'account_id', 'reconciled'],
        limit=10
    )

    # Preferir linha na conta transitória ou pendentes
    for linha in linhas:
        account_id = extrair_id(linha.get('account_id'))
        if account_id in [CONTA_TRANSITORIA, CONTA_PAGAMENTOS_PENDENTES]:
            return linha['id']

    # Se não encontrar, retornar qualquer linha de débito não reconciliada
    return linhas[0]['id'] if linhas else None


def buscar_linha_credito_titulo(odoo, titulo_id: int) -> Optional[int]:
    """
    Busca a linha de CRÉDITO do título a pagar.
    """
    titulo = odoo.search_read(
        'account.move.line',
        [['id', '=', titulo_id]],
        fields=['id', 'credit', 'reconciled', 'matched_debit_ids'],
        limit=1
    )

    if titulo and not titulo[0].get('reconciled', False):
        return titulo[0]['id']

    return None


# ==============================================================================
# VINCULAÇÃO (RECONCILIAÇÃO)
# ==============================================================================

def executar_reconciliacao(odoo, line1_id: int, line2_id: int) -> bool:
    """
    Executa a reconciliação de duas linhas no Odoo.

    Returns:
        True se sucesso, False se falha
    """
    try:
        odoo.execute_kw(
            'account.move.line',
            'reconcile',
            [[line1_id, line2_id]]
        )
        return True
    except Exception as e:
        # Ignorar erro de serialização XML-RPC (operação foi executada)
        if "cannot marshal None" in str(e):
            return True
        raise


# ==============================================================================
# PREPARAÇÃO DO EXTRATO (AJUSTES PRÉ-VINCULAÇÃO)
# ==============================================================================

# Contas por código (account.account)
CONTA_TRANSITORIA_ID = 22199       # 1110100003 TRANSITÓRIA DE VALORES
CONTA_PENDENTES_ID = 26868         # 1110100004 PAGAMENTOS/RECEBIMENTOS PENDENTES


def ajustar_conta_extrato_para_pendentes(odoo, move_id: int) -> Optional[int]:
    """
    Ajusta a linha de débito do extrato para usar conta PENDENTES.

    O extrato pode ter sido importado com conta TRANSITÓRIA (1110100003),
    mas para o link visual funcionar, precisa usar PENDENTES (1110100004).

    Args:
        odoo: Conexão Odoo
        move_id: ID do move do extrato

    Returns:
        ID da linha de débito ajustada ou None se erro
    """
    # Buscar linha de débito não reconciliada
    linhas = odoo.search_read(
        'account.move.line',
        [
            ['move_id', '=', move_id],
            ['debit', '>', 0],
            ['reconciled', '=', False]
        ],
        fields=['id', 'debit', 'account_id', 'name'],
        limit=10
    )

    if not linhas:
        return None

    # Encontrar linha candidata (preferir TRANSITÓRIA para converter)
    linha_ajustar = None
    for linha in linhas:
        account_id = extrair_id(linha.get('account_id'))
        if account_id == CONTA_TRANSITORIA_ID:
            linha_ajustar = linha
            break
        elif account_id == CONTA_PENDENTES_ID:
            # Já está na conta correta
            return linha['id']

    # Se não encontrou TRANSITÓRIA, usar primeira linha disponível
    if not linha_ajustar:
        linha_ajustar = linhas[0]

    # Verificar se precisa ajustar
    account_id = extrair_id(linha_ajustar.get('account_id'))
    if account_id == CONTA_PENDENTES_ID:
        return linha_ajustar['id']

    # Atualizar conta para PENDENTES
    try:
        odoo.execute_kw(
            'account.move.line',
            'write',
            [[linha_ajustar['id']], {'account_id': CONTA_PENDENTES_ID}]
        )
        print(f"    [AJUSTE] Conta da linha {linha_ajustar['id']} alterada para PENDENTES")
    except Exception as e:
        if "cannot marshal None" not in str(e):
            print(f"    [AVISO] Erro ao ajustar conta: {e}")

    return linha_ajustar['id']


def ajustar_partner_statement_line(odoo, statement_line_id: int, partner_id: int) -> None:
    """
    Atualiza o partner_id da statement line.

    Args:
        odoo: Conexão Odoo
        statement_line_id: ID da linha de extrato
        partner_id: ID do parceiro (fornecedor)
    """
    try:
        odoo.execute_kw(
            'account.bank.statement.line',
            'write',
            [[statement_line_id], {'partner_id': partner_id}]
        )
        print(f"    [AJUSTE] Partner {partner_id} definido na statement line {statement_line_id}")
    except Exception as e:
        if "cannot marshal None" not in str(e):
            print(f"    [AVISO] Erro ao ajustar partner: {e}")


def ajustar_name_linha_extrato(odoo, line_id: int, novo_name: str) -> None:
    """
    Atualiza o name da linha de débito do extrato para o padrão Rubbermax.

    Args:
        odoo: Conexão Odoo
        line_id: ID da linha do move
        novo_name: Novo nome no formato "Pagamento de fornecedor R$ X - NOME - DATA"
    """
    try:
        odoo.execute_kw(
            'account.move.line',
            'write',
            [[line_id], {'name': novo_name}]
        )
        print(f"    [AJUSTE] Name da linha {line_id} atualizado")
    except Exception as e:
        if "cannot marshal None" not in str(e):
            print(f"    [AVISO] Erro ao ajustar name: {e}")


def ajustar_partner_linhas_move_extrato(odoo, move_id: int, partner_id: int) -> None:
    """
    Atualiza o partner_id em todas as linhas do move do extrato.

    Args:
        odoo: Conexão Odoo
        move_id: ID do move do extrato
        partner_id: ID do parceiro (fornecedor)
    """
    # Buscar todas as linhas do move
    linhas = odoo.search_read(
        'account.move.line',
        [['move_id', '=', move_id]],
        fields=['id', 'partner_id'],
        limit=10
    )

    line_ids = [ln['id'] for ln in linhas if not ln.get('partner_id')]

    if line_ids:
        try:
            odoo.execute_kw(
                'account.move.line',
                'write',
                [line_ids, {'partner_id': partner_id}]
            )
            print(f"    [AJUSTE] Partner {partner_id} definido em {len(line_ids)} linhas do move")
        except Exception as e:
            if "cannot marshal None" not in str(e):
                print(f"    [AVISO] Erro ao ajustar partner nas linhas: {e}")


def formatar_valor_br(valor: float) -> str:
    """Formata valor monetário no padrão brasileiro (R$ 1.234,56)."""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def formatar_data_br(data: str) -> str:
    """Converte data YYYY-MM-DD para DD/MM/YYYY."""
    if not data:
        return datetime.now().strftime('%d/%m/%Y')
    try:
        dt = datetime.strptime(data, '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except ValueError:
        return data


def criar_payment_outbound(
    odoo,
    partner_id: int,
    partner_name: str,
    valor: float,
    journal_id: int,
    data: str,
    company_id: int
) -> Tuple[int, str]:
    """
    Cria um account.payment OUTBOUND (pagamento a fornecedor).

    O rótulo (ref) segue o padrão Odoo:
    "Pagamento de fornecedor R$ 1.234,56 - NOME FORNECEDOR - DD/MM/YYYY"
    """
    # Formatar rótulo no padrão Rubbermax
    valor_formatado = formatar_valor_br(valor)
    data_formatada = formatar_data_br(data)
    ref = f"Pagamento de fornecedor {valor_formatado} - {partner_name} - {data_formatada}"

    payment_data = {
        'payment_type': 'outbound',
        'partner_type': 'supplier',
        'partner_id': partner_id,
        'amount': valor,
        'journal_id': journal_id,
        'ref': ref,
        'date': data,
        'company_id': company_id
    }

    payment_id = odoo.execute_kw(
        'account.payment',
        'create',
        [payment_data]
    )

    # Buscar nome gerado
    payment = odoo.search_read(
        'account.payment',
        [['id', '=', payment_id]],
        fields=['name'],
        limit=1
    )

    payment_name = payment[0]['name'] if payment else f'Payment #{payment_id}'
    return payment_id, payment_name


def postar_payment(odoo, payment_id: int) -> None:
    """Confirma o pagamento (action_post)."""
    try:
        odoo.execute_kw(
            'account.payment',
            'action_post',
            [[payment_id]]
        )
    except Exception as e:
        if "cannot marshal None" not in str(e):
            raise


def buscar_linhas_payment(odoo, payment_id: int) -> Dict:
    """
    Busca as linhas criadas pelo payment após postar.
    """
    CONTA_PAGAMENTOS_PENDENTES = 26868

    linhas = odoo.search_read(
        'account.move.line',
        [['payment_id', '=', payment_id]],
        fields=['id', 'debit', 'credit', 'account_id', 'account_type'],
        limit=10
    )

    resultado = {
        'debit_line_id': None,   # Para reconciliar com título
        'credit_line_id': None   # Para reconciliar com extrato
    }

    for linha in linhas:
        # Linha de DÉBITO na conta de FORNECEDORES (liability_payable)
        if linha.get('account_type') == 'liability_payable' and linha.get('debit', 0) > 0:
            resultado['debit_line_id'] = linha['id']

        # Linha de CRÉDITO na conta PENDENTES
        if linha.get('credit', 0) > 0:
            account_id = extrair_id(linha.get('account_id'))
            if account_id == CONTA_PAGAMENTOS_PENDENTES:
                resultado['credit_line_id'] = linha['id']

    return resultado


# ==============================================================================
# PROCESSAMENTO PRINCIPAL
# ==============================================================================

def processar_linha(odoo, linha: LinhaExcel, dry_run: bool = False) -> LinhaExcel:
    """
    Processa uma linha do Excel.

    Segue o padrão do BaixaPagamentosService:
    - journal_id vem da linha do extrato (não é parâmetro fixo)
    - company_id vem do título

    Args:
        odoo: Conexão Odoo
        linha: LinhaExcel a processar
        dry_run: Se True, apenas simula sem executar

    Returns:
        LinhaExcel atualizada com resultado
    """
    try:
        # =====================================================================
        # 1. BUSCAR TÍTULO NO ODOO
        # =====================================================================
        titulo, estrategia_titulo = buscar_titulo_odoo(
            odoo,
            fatura_name=linha.fatura_name,
            cnpj=linha.cnpj,
            fatura_id=linha.fatura_id,
            parcela=linha.parcela,
            valor=linha.valor
        )

        if not titulo:
            linha.status = 'ERRO'
            linha.mensagem = f"Título: {estrategia_titulo}"
            return linha

        linha.titulo_odoo_id = titulo['id']

        # Verificar se título já está reconciliado
        if titulo.get('reconciled', False):
            linha.status = 'IGNORADO'
            linha.mensagem = f"Título já reconciliado (ID: {titulo['id']})"
            return linha

        # =====================================================================
        # 2. BUSCAR EXTRATO NO ODOO
        # =====================================================================
        extrato, estrategia_extrato = buscar_extrato_odoo(
            odoo,
            extrato_id=linha.extrato_id,
            movimento=linha.movimento
        )

        if not extrato:
            linha.status = 'ERRO'
            linha.mensagem = f"Extrato: {estrategia_extrato}"
            return linha

        linha.extrato_odoo_id = extrato['id']

        # Verificar se extrato já está TOTALMENTE reconciliado
        # Usa amount_residual para permitir conciliação parcial (1 extrato → N títulos)
        extrato_residual = abs(extrato.get('amount_residual', 0))
        if extrato_residual == 0 and extrato.get('is_reconciled', False):
            linha.status = 'IGNORADO'
            linha.mensagem = f"Extrato já totalmente reconciliado (ID: {extrato['id']})"
            return linha

        # Verificar se o valor da linha cabe no residual do extrato
        if extrato_residual > 0 and linha.valor > extrato_residual:
            linha.status = 'ERRO'
            linha.mensagem = f"Valor {linha.valor:.2f} > residual do extrato {extrato_residual:.2f}"
            return linha

        # Extrair journal_id da linha do extrato (padrão BaixaPagamentosService)
        journal_id = extrair_id(extrato.get('journal_id'))
        if not journal_id:
            linha.status = 'ERRO'
            linha.mensagem = "Extrato sem journal_id"
            return linha

        # =====================================================================
        # 3. EXECUTAR VINCULAÇÃO
        # =====================================================================
        if dry_run:
            linha.status = 'SIMULADO'
            linha.mensagem = (
                f"Título {titulo['id']} ({estrategia_titulo}) + "
                f"Extrato {extrato['id']} ({estrategia_extrato}) + "
                f"Journal {journal_id}"
            )
            return linha

        # Extrair dados necessários do título
        partner_id = extrair_id(titulo.get('partner_id'))
        partner_name = extrair_nome(titulo.get('partner_id'))
        company_id = extrair_id(titulo.get('company_id'))
        move = titulo.get('move_id')
        move_name = extrair_nome(move)
        extrato_move_id = extrair_id(extrato.get('move_id'))
        data_extrato = extrato.get('date', datetime.now().strftime('%Y-%m-%d'))

        # =====================================================================
        # 3.1 PREPARAR EXTRATO (ajustar conta e partner)
        # =====================================================================
        # Ajustar partner_id na statement line
        ajustar_partner_statement_line(odoo, extrato['id'], partner_id)

        # Ajustar partner_id em todas as linhas do move do extrato
        ajustar_partner_linhas_move_extrato(odoo, extrato_move_id, partner_id)

        # Ajustar conta da linha de débito do extrato para PENDENTES
        # e obter o ID da linha ajustada
        debit_line_extrato = ajustar_conta_extrato_para_pendentes(odoo, extrato_move_id)
        if not debit_line_extrato:
            linha.status = 'ERRO'
            linha.mensagem = "Linha de débito do extrato não encontrada"
            return linha

        # Ajustar name da linha de débito do extrato para padrão Rubbermax
        valor_formatado = formatar_valor_br(linha.valor)
        data_formatada = formatar_data_br(data_extrato)
        novo_name_extrato = f"Pagamento de fornecedor {valor_formatado} - {partner_name} - {data_formatada}"
        ajustar_name_linha_extrato(odoo, debit_line_extrato, novo_name_extrato)

        # =====================================================================
        # 3.2 CRIAR PAYMENT
        # =====================================================================
        payment_id, payment_name = criar_payment_outbound(
            odoo,
            partner_id=partner_id,
            partner_name=partner_name,
            valor=linha.valor,
            journal_id=journal_id,
            data=data_extrato,
            company_id=company_id
        )

        linha.payment_id = payment_id

        # Postar payment
        postar_payment(odoo, payment_id)

        # Buscar linhas do payment
        linhas_payment = buscar_linhas_payment(odoo, payment_id)

        # Reconciliar payment com título
        if linhas_payment.get('debit_line_id'):
            executar_reconciliacao(
                odoo,
                linhas_payment['debit_line_id'],
                titulo['id']
            )

        # Reconciliar payment com extrato
        if linhas_payment.get('credit_line_id') and debit_line_extrato:
            executar_reconciliacao(
                odoo,
                linhas_payment['credit_line_id'],
                debit_line_extrato
            )

        # Buscar full_reconcile_id do título
        titulo_atualizado = odoo.search_read(
            'account.move.line',
            [['id', '=', titulo['id']]],
            fields=['full_reconcile_id', 'reconciled'],
            limit=1
        )

        if titulo_atualizado and titulo_atualizado[0].get('full_reconcile_id'):
            full_rec = titulo_atualizado[0]['full_reconcile_id']
            linha.full_reconcile_id = extrair_id(full_rec)

        linha.status = 'SUCESSO'
        linha.mensagem = (
            f"Payment {payment_name} criado. "
            f"Título: {estrategia_titulo}, Extrato: {estrategia_extrato}"
        )

    except Exception as e:
        linha.status = 'ERRO'
        linha.mensagem = str(e)[:200]

    return linha


def processar_excel(
    caminho: str,
    dry_run: bool = False,
    limite: int = None,
    offset: int = 0,
    batch_size: int = None
) -> ResultadoProcessamento:
    """
    Processa o Excel completo.

    Segue o padrão do BaixaPagamentosService:
    - journal_id é extraído automaticamente de cada linha de extrato
    - Não precisa de parâmetro fixo

    Args:
        caminho: Caminho do arquivo Excel
        dry_run: Se True, apenas simula sem executar
        limite: Limite de linhas a processar (None = todas) [DEPRECATED: use batch_size]
        offset: Linha inicial (0-indexed) para processamento em lotes
        batch_size: Quantidade de linhas por lote

    Returns:
        ResultadoProcessamento com estatísticas e detalhes
    """
    # Conectar ao Odoo
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise Exception("Falha na autenticação com Odoo")

    # Ler Excel
    linhas = ler_excel(caminho)
    total_arquivo = len(linhas)

    # Aplicar offset e batch_size (ou limite para compatibilidade)
    if offset > 0:
        linhas = linhas[offset:]

    if batch_size:
        linhas = linhas[:batch_size]
    elif limite:
        linhas = linhas[:limite]

    resultado = ResultadoProcessamento(total_linhas=len(linhas))

    print(f"\n{'='*70}")
    print(f"PROCESSANDO EM BATCH")
    print(f"{'='*70}")
    print(f"Total no arquivo: {total_arquivo}")
    print(f"Offset: {offset}")
    print(f"Batch size: {batch_size or limite or 'todas'}")
    print(f"Linhas neste lote: {len(linhas)}")
    print(f"Range: {offset+1} a {offset+len(linhas)}")
    print(f"Journal: Extraído automaticamente de cada linha de extrato")
    print(f"Modo: {'SIMULAÇÃO' if dry_run else 'EXECUÇÃO'}")
    print(f"{'='*70}\n")

    for i, linha in enumerate(linhas, 1):
        print(f"[{i}/{len(linhas)}] Linha Excel {linha.linha_num}: ", end='')

        linha = processar_linha(odoo, linha, dry_run)

        resultado.processadas += 1

        if linha.status == 'SUCESSO':
            resultado.sucesso += 1
            print(f"✅ {linha.mensagem}")
        elif linha.status == 'SIMULADO':
            resultado.sucesso += 1
            print(f"🔍 {linha.mensagem}")
        elif linha.status == 'IGNORADO':
            resultado.ignoradas += 1
            print(f"⏭️ {linha.mensagem}")
        else:
            resultado.erro += 1
            print(f"❌ {linha.mensagem}")

        resultado.linhas.append(asdict(linha))

    # Resumo final
    print(f"\n{'='*70}")
    print(f"RESUMO DO PROCESSAMENTO")
    print(f"{'='*70}")
    print(f"Total de linhas: {resultado.total_linhas}")
    print(f"Processadas: {resultado.processadas}")
    print(f"Sucesso: {resultado.sucesso}")
    print(f"Ignoradas: {resultado.ignoradas}")
    print(f"Erros: {resultado.erro}")
    print(f"{'='*70}\n")

    return resultado


# ==============================================================================
# PROCESSAMENTO OTIMIZADO (BATCH)
# ==============================================================================

def processar_excel_otimizado(
    caminho: str,
    dry_run: bool = False,
    limite: int = None,
    offset: int = 0,
    batch_size: int = None
) -> ResultadoProcessamento:
    """
    Processa o Excel com otimizações de batch.

    FASES:
    1. PRÉ-CARREGAMENTO: Buscar todos extratos e títulos de uma vez
    2. PREPARAÇÃO: Batch writes (partner, conta)
    3. PROCESSAMENTO: Criar payments e reconciliar

    Reduz chamadas ao Odoo de ~12/linha para ~4/linha.
    """
    import time
    inicio_total = time.time()

    # Conectar ao Odoo
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise Exception("Falha na autenticação com Odoo")

    # Ler Excel
    linhas = ler_excel(caminho)
    total_arquivo = len(linhas)

    # Aplicar offset e batch_size
    if offset > 0:
        linhas = linhas[offset:]
    if batch_size:
        linhas = linhas[:batch_size]
    elif limite:
        linhas = linhas[:limite]

    resultado = ResultadoProcessamento(total_linhas=len(linhas))

    print(f"\n{'='*70}")
    print(f"PROCESSAMENTO OTIMIZADO (BATCH)")
    print(f"{'='*70}")
    print(f"Total no arquivo: {total_arquivo}")
    print(f"Linhas neste lote: {len(linhas)}")
    print(f"Range: {offset+1} a {offset+len(linhas)}")
    print(f"Modo: {'SIMULAÇÃO' if dry_run else 'EXECUÇÃO'}")
    print(f"{'='*70}\n")

    # =========================================================================
    # FASE 1: PRÉ-CARREGAMENTO
    # =========================================================================
    print("FASE 1: Pré-carregando dados...")
    inicio_fase1 = time.time()

    # Coletar IDs para busca batch
    extrato_ids = [ln.extrato_id for ln in linhas if ln.extrato_id]
    titulo_ids = [ln.fatura_id for ln in linhas if ln.fatura_id]

    # Buscar extratos em batch
    print(f"  Buscando {len(extrato_ids)} extratos...")
    extratos_cache = batch_buscar_extratos(odoo, extrato_ids)
    print(f"  ✓ {len(extratos_cache)} extratos encontrados")

    # Buscar títulos por ID em batch
    print(f"  Buscando {len(titulo_ids)} títulos por ID...")
    titulos_cache = batch_buscar_titulos_por_id(odoo, titulo_ids)
    print(f"  ✓ {len(titulos_cache)} títulos encontrados")

    # Buscar linhas de débito dos extratos
    move_ids = [extrair_id(ext.get('move_id')) for ext in extratos_cache.values() if ext.get('move_id')]
    print(f"  Buscando linhas de débito de {len(move_ids)} moves...")
    linhas_debito_cache = batch_buscar_linhas_debito_extratos(odoo, move_ids)
    print(f"  ✓ {len(linhas_debito_cache)} linhas de débito encontradas")

    print(f"  FASE 1 concluída em {time.time() - inicio_fase1:.1f}s")

    # =========================================================================
    # FASE 2: PREPARAÇÃO (BATCH WRITES)
    # =========================================================================
    print("\nFASE 2: Preparando dados (batch writes)...")
    inicio_fase2 = time.time()

    # Preparar listas para batch writes
    partner_stmt_updates = []  # (stmt_id, partner_id)
    partner_move_updates = []  # (move_id, partner_id)
    linhas_para_conta = []     # line_ids para atualizar conta

    # Rastrear valores consumidos por extrato (para conciliação parcial 1:N)
    extrato_consumido = {}  # extrato_id -> valor já alocado neste batch

    # Mapear dados preparados por linha
    dados_preparados = {}

    for ln in linhas:
        # Verificar extrato
        extrato = extratos_cache.get(ln.extrato_id)
        if not extrato:
            continue

        # Verificar se extrato já está TOTALMENTE reconciliado
        # Usa amount_residual para permitir conciliação parcial (1 extrato → N títulos)
        extrato_residual = abs(extrato.get('amount_residual', 0))
        consumido = extrato_consumido.get(ln.extrato_id, 0)
        residual_disponivel = extrato_residual - consumido

        if residual_disponivel <= 0 and extrato.get('is_reconciled', False):
            continue

        # Verificar se o valor da linha cabe no residual disponível
        if residual_disponivel > 0 and ln.valor > residual_disponivel:
            continue  # Será tratado na FASE 3 como erro

        # Obter título (do cache ou buscar individualmente se necessário)
        titulo = None
        estrategia = ''

        if ln.fatura_id and ln.fatura_id in titulos_cache:
            titulo = titulos_cache[ln.fatura_id]
            estrategia = 'ID_DIRETO'
        elif ln.fatura_name:
            # Fallback: buscar por nome (não otimizável facilmente)
            titulo, estrategia = buscar_titulo_odoo(
                odoo, ln.fatura_name, ln.cnpj, ln.fatura_id, ln.parcela, ln.valor
            )
            if titulo:
                titulos_cache[titulo['id']] = titulo

        if not titulo:
            continue

        # Verificar se título já reconciliado
        if titulo.get('reconciled', False):
            continue

        # Extrair dados
        partner_id = extrair_id(titulo.get('partner_id'))
        move_id = extrair_id(extrato.get('move_id'))
        debit_line = linhas_debito_cache.get(move_id)

        if not partner_id or not move_id:
            continue

        # Preparar updates
        partner_stmt_updates.append((extrato['id'], partner_id))
        partner_move_updates.append((move_id, partner_id))
        if debit_line:
            linhas_para_conta.append(debit_line)

        # Salvar dados preparados
        dados_preparados[ln.linha_num] = {
            'titulo': titulo,
            'extrato': extrato,
            'partner_id': partner_id,
            'partner_name': extrair_nome(titulo.get('partner_id')),
            'move_id': move_id,
            'debit_line': debit_line,
            'estrategia': estrategia,
            'valor_linha': ln.valor
        }

        # Atualizar valor consumido do extrato (para próximas linhas do mesmo extrato)
        extrato_consumido[ln.extrato_id] = consumido + ln.valor

    # Executar batch writes
    if not dry_run and partner_stmt_updates:
        print(f"  Atualizando partner em {len(partner_stmt_updates)} statement lines...")
        batch_write_partner_statement_lines(odoo, partner_stmt_updates)

    if not dry_run and partner_move_updates:
        print(f"  Atualizando partner em move lines de {len(partner_move_updates)} moves...")
        batch_write_partner_move_lines(odoo, partner_move_updates)

    if not dry_run and linhas_para_conta:
        print(f"  Atualizando conta PENDENTES em {len(linhas_para_conta)} linhas...")
        batch_write_conta_pendentes(odoo, linhas_para_conta)

    print(f"  FASE 2 concluída em {time.time() - inicio_fase2:.1f}s")

    # =========================================================================
    # FASE 3: PROCESSAMENTO (PAYMENTS)
    # =========================================================================
    print(f"\nFASE 3: Processando {len(linhas)} linhas...")
    inicio_fase3 = time.time()

    for i, linha in enumerate(linhas, 1):
        dados = dados_preparados.get(linha.linha_num)

        # Linha não tem dados preparados - verificar motivo
        if not dados:
            extrato = extratos_cache.get(linha.extrato_id)

            if not extrato:
                linha.status = 'ERRO'
                linha.mensagem = 'Extrato não encontrado'
            else:
                # Verificar status do extrato com suporte a conciliação parcial
                extrato_residual = abs(extrato.get('amount_residual', 0))
                consumido_antes = extrato_consumido.get(linha.extrato_id, 0) - linha.valor  # Aproximação
                residual_disponivel = extrato_residual - max(0, consumido_antes)

                if residual_disponivel <= 0 and extrato.get('is_reconciled', False):
                    linha.status = 'IGNORADO'
                    linha.mensagem = f"Extrato já totalmente reconciliado (ID: {extrato['id']})"
                    resultado.ignoradas += 1
                elif residual_disponivel > 0 and linha.valor > residual_disponivel:
                    linha.status = 'ERRO'
                    linha.mensagem = f"Valor {linha.valor:.2f} > residual disponível {residual_disponivel:.2f}"
                else:
                    # Tentar buscar título
                    titulo, estrategia = buscar_titulo_odoo(
                        odoo, linha.fatura_name, linha.cnpj, linha.fatura_id, linha.parcela, linha.valor
                    )
                    if not titulo:
                        linha.status = 'ERRO'
                        linha.mensagem = f"Título: {estrategia}"
                    elif titulo.get('reconciled', False):
                        linha.status = 'IGNORADO'
                        linha.mensagem = f"Título já reconciliado (ID: {titulo['id']})"
                        resultado.ignoradas += 1
                    else:
                        linha.status = 'ERRO'
                        linha.mensagem = 'Dados insuficientes para processar'

            if linha.status == 'ERRO':
                resultado.erro += 1

            resultado.processadas += 1
            resultado.linhas.append(asdict(linha))
            print(f"[{i}/{len(linhas)}] Linha {linha.linha_num}: ❌ {linha.mensagem}")
            continue

        # Processar linha com dados preparados
        try:
            if dry_run:
                linha.status = 'SIMULADO'
                linha.mensagem = f"Título {dados['titulo']['id']} ({dados['estrategia']})"
                resultado.sucesso += 1
            else:
                # Extrair dados
                titulo = dados['titulo']
                extrato = dados['extrato']
                partner_id = dados['partner_id']
                partner_name = dados['partner_name']
                debit_line_extrato = dados['debit_line']

                journal_id = extrair_id(extrato.get('journal_id'))
                company_id = extrair_id(titulo.get('company_id'))
                data_extrato = extrato.get('date', datetime.now().strftime('%Y-%m-%d'))

                linha.titulo_odoo_id = titulo['id']
                linha.extrato_odoo_id = extrato['id']

                # Criar payment
                payment_id, payment_name = criar_payment_outbound(
                    odoo,
                    partner_id=partner_id,
                    partner_name=partner_name,
                    valor=linha.valor,
                    journal_id=journal_id,
                    data=data_extrato,
                    company_id=company_id
                )

                linha.payment_id = payment_id

                # Postar payment
                postar_payment(odoo, payment_id)

                # Buscar linhas do payment
                linhas_payment = buscar_linhas_payment(odoo, payment_id)

                # Reconciliar payment com título
                if linhas_payment.get('debit_line_id'):
                    executar_reconciliacao(
                        odoo,
                        linhas_payment['debit_line_id'],
                        titulo['id']
                    )

                # Reconciliar payment com extrato
                if linhas_payment.get('credit_line_id') and debit_line_extrato:
                    executar_reconciliacao(
                        odoo,
                        linhas_payment['credit_line_id'],
                        debit_line_extrato
                    )

                linha.status = 'SUCESSO'
                linha.mensagem = f"Payment {payment_name} criado"
                resultado.sucesso += 1

        except Exception as e:
            linha.status = 'ERRO'
            linha.mensagem = str(e)[:200]
            resultado.erro += 1

        resultado.processadas += 1
        resultado.linhas.append(asdict(linha))

        if linha.status == 'SUCESSO':
            print(f"[{i}/{len(linhas)}] ✅ {linha.mensagem}")
        elif linha.status == 'SIMULADO':
            print(f"[{i}/{len(linhas)}] 🔍 {linha.mensagem}")
        else:
            print(f"[{i}/{len(linhas)}] ❌ {linha.mensagem}")

    print(f"  FASE 3 concluída em {time.time() - inicio_fase3:.1f}s")

    # Resumo final
    tempo_total = time.time() - inicio_total
    print(f"\n{'='*70}")
    print(f"RESUMO DO PROCESSAMENTO OTIMIZADO")
    print(f"{'='*70}")
    print(f"Total de linhas: {resultado.total_linhas}")
    print(f"Processadas: {resultado.processadas}")
    print(f"Sucesso: {resultado.sucesso}")
    print(f"Ignoradas: {resultado.ignoradas}")
    print(f"Erros: {resultado.erro}")
    print(f"Tempo total: {tempo_total:.1f}s ({tempo_total/60:.1f} min)")
    print(f"Velocidade: {resultado.processadas / tempo_total:.1f} linhas/s")
    print(f"{'='*70}\n")

    return resultado


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Vincula extrato bancário com faturas a pagar via Excel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # MODO OTIMIZADO (recomendado - 3-4x mais rápido):
  python vincular_extrato_fatura_excel.py -a planilha.xlsx --otimizado

  # Otimizado com lotes de 500:
  python vincular_extrato_fatura_excel.py -a planilha.xlsx --otimizado -o 0 -b 500
  python vincular_extrato_fatura_excel.py -a planilha.xlsx --otimizado -o 500 -b 500

  # Simular processamento (dry run)
  python vincular_extrato_fatura_excel.py --arquivo planilha.xlsx --dry-run --otimizado

  # Processar em lotes de 500 linhas (modo normal):
  python vincular_extrato_fatura_excel.py -a planilha.xlsx -o 0 -b 500

  # Testar com 10 linhas
  python vincular_extrato_fatura_excel.py --arquivo planilha.xlsx --limite 10 --otimizado

NOTA: O journal_id é extraído automaticamente de cada linha de extrato,
      seguindo o padrão do BaixaPagamentosService.
        """
    )

    parser.add_argument(
        '--arquivo', '-a',
        type=str,
        required=True,
        help='Caminho do arquivo Excel'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Apenas simula, não executa as vinculações'
    )
    parser.add_argument(
        '--limite', '-l',
        type=int,
        default=None,
        help='Limite de linhas a processar (use --batch-size para lotes)'
    )
    parser.add_argument(
        '--offset', '-o',
        type=int,
        default=0,
        help='Linha inicial para processamento em lotes (0-indexed)'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=None,
        help='Quantidade de linhas por lote'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Saída em JSON'
    )
    parser.add_argument(
        '--otimizado', '--fast',
        action='store_true',
        help='Usar processamento otimizado com batch (3-4x mais rápido)'
    )

    args = parser.parse_args()

    # Converter caminho Windows para WSL se necessário
    caminho = args.arquivo
    if caminho.startswith('C:\\') or caminho.startswith('c:\\'):
        caminho = '/mnt/c/' + caminho[3:].replace('\\', '/')

    try:
        # Escolher função de processamento
        if args.otimizado:
            resultado = processar_excel_otimizado(
                caminho=caminho,
                dry_run=args.dry_run,
                limite=args.limite,
                offset=args.offset,
                batch_size=args.batch_size
            )
        else:
            resultado = processar_excel(
                caminho=caminho,
                dry_run=args.dry_run,
                limite=args.limite,
                offset=args.offset,
                batch_size=args.batch_size
            )

        if args.json:
            print(json.dumps(asdict(resultado), indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
