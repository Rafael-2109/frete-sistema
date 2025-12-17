"""
Script de Diagnostico para Conciliacao de Pagamentos
=====================================================

Fase 1: Diagnostico (SEM ACOES)
- Le Excel de pagamentos
- Le extratos nao conciliados do Odoo
- Tenta match por DATA+VALOR (Nivel A)
- Para duplicatas, tenta match por DATA+VALOR+FORNECEDOR (Nivel B)
- Gera relatorio de matches encontrados

Autor: Sistema de Fretes
Data: 16/12/2025
"""

import sys
import os
import re
import json
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

# Adiciona path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd


# ==============================================================================
# CONFIGURACOES
# ==============================================================================

TOLERANCIA_VALOR = Decimal("0.05")  # R$ 0,05 de tolerancia
CAMINHO_EXCEL = '/mnt/c/Users/rafael.nascimento/Downloads/contas a pagar.xlsx'


# ==============================================================================
# FUNCOES AUXILIARES
# ==============================================================================

def normalizar_valor(valor) -> Decimal:
    """Normaliza valor para Decimal com 2 casas"""
    if pd.isna(valor):
        return Decimal("0.00")
    return Decimal(str(abs(float(valor)))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalizar_data(data) -> Optional[date]:
    """Normaliza data para date"""
    if pd.isna(data):
        return None
    if isinstance(data, str):
        try:
            return datetime.strptime(data, "%Y-%m-%d").date()
        except:
            return None
    if isinstance(data, datetime):
        return data.date()
    if isinstance(data, date):
        return data
    return None


def extrair_cnpj(texto: str) -> Optional[str]:
    """Extrai CNPJ de um texto (apenas digitos)"""
    if not texto:
        return None
    # Padrao: XX.XXX.XXX/XXXX-XX ou apenas digitos
    match = re.search(r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})', str(texto))
    if match:
        return re.sub(r'\D', '', match.group(1))
    # Tentar padrao parcial (8 digitos base do CNPJ)
    match = re.search(r'(\d{8})', str(texto))
    if match:
        return match.group(1)
    return None


def valores_proximos(v1: Decimal, v2: Decimal, tolerancia: Decimal = TOLERANCIA_VALOR) -> bool:
    """Verifica se dois valores estao dentro da tolerancia"""
    return abs(v1 - v2) <= tolerancia


# ==============================================================================
# CARGA DE DADOS
# ==============================================================================

def carregar_excel() -> pd.DataFrame:
    """Carrega e processa o Excel de pagamentos"""
    print("\n[1/4] Carregando Excel de pagamentos...")

    df = pd.read_excel(CAMINHO_EXCEL)

    # Selecionar e renomear colunas
    df_limpo = df[['Fornecedor', 'Titulo', 'Parc', 'DATA PAGAMENTO', 'VALOR2']].copy()
    df_limpo.columns = ['fornecedor', 'nf', 'parcela', 'data_pagamento', 'valor']

    # Limpar dados
    df_limpo = df_limpo.dropna(subset=['data_pagamento', 'valor'])

    # Normalizar
    df_limpo['valor_decimal'] = df_limpo['valor'].apply(normalizar_valor)
    df_limpo['data_norm'] = df_limpo['data_pagamento'].apply(normalizar_data)

    # Filtrar apenas datas validas e valores positivos
    df_limpo = df_limpo[df_limpo['data_norm'].notna()]
    df_limpo = df_limpo[df_limpo['valor_decimal'] > 0]

    # Criar chave unica
    df_limpo['chave_data_valor'] = df_limpo.apply(
        lambda r: f"{r['data_norm'].isoformat()}|{r['valor_decimal']}", axis=1
    )

    print(f"    Total de registros: {len(df_limpo)}")
    print(f"    Periodo: {df_limpo['data_norm'].min()} a {df_limpo['data_norm'].max()}")

    return df_limpo


def carregar_extratos() -> List[Dict]:
    """Carrega extratos nao conciliados do Odoo"""
    print("\n[2/4] Carregando extratos do Odoo...")

    from app.odoo.utils.connection import get_odoo_connection

    odoo = get_odoo_connection()
    if not odoo.authenticate():
        raise Exception("Falha na autenticacao com Odoo")

    extratos = odoo.search_read(
        "account.bank.statement.line",
        [["is_reconciled", "=", False], ["amount", "<", 0]],
        fields=["id", "date", "amount", "partner_id", "payment_ref", "journal_id"],
        limit=50000
    )

    # Processar extratos
    for ext in extratos:
        ext['valor_decimal'] = normalizar_valor(ext['amount'])
        ext['data_norm'] = normalizar_data(ext['date'])
        ext['cnpj_extraido'] = extrair_cnpj(ext.get('payment_ref', ''))
        ext['chave_data_valor'] = f"{ext['data_norm'].isoformat()}|{ext['valor_decimal']}" if ext['data_norm'] else None
        ext['partner_name'] = ext['partner_id'][1] if ext.get('partner_id') else None

    # Filtrar apenas com data valida
    extratos = [e for e in extratos if e['data_norm']]

    print(f"    Total de extratos: {len(extratos)}")
    if extratos:
        datas = [e['data_norm'] for e in extratos]
        print(f"    Periodo: {min(datas)} a {max(datas)}")

    return extratos


# ==============================================================================
# ALGORITMO DE MATCHING
# ==============================================================================

def executar_matching(df_excel: pd.DataFrame, extratos: List[Dict]) -> Dict[str, Any]:
    """
    Executa o algoritmo de matching em 2 niveis:

    Nivel A: DATA + VALOR unicos em ambos os lados
    Nivel B: DATA + VALOR + FORNECEDOR (quando A tem duplicatas)
    """
    print("\n[3/4] Executando algoritmo de matching...")

    resultado = {
        'total_excel': len(df_excel),
        'total_extratos': len(extratos),
        'matches_nivel_a': [],
        'matches_nivel_b': [],
        'excel_sem_match': [],
        'extratos_sem_match': [],
        'estatisticas': {}
    }

    # Indexar Excel por chave DATA+VALOR
    excel_por_chave = defaultdict(list)
    for idx, row in df_excel.iterrows():
        chave = row['chave_data_valor']
        excel_por_chave[chave].append({
            'idx': idx,
            'fornecedor': row['fornecedor'],
            'nf': row['nf'],
            'parcela': row['parcela'],
            'data': row['data_norm'],
            'valor': row['valor_decimal']
        })

    # Indexar Extratos por chave DATA+VALOR
    extrato_por_chave = defaultdict(list)
    for ext in extratos:
        chave = ext['chave_data_valor']
        if chave:
            extrato_por_chave[chave].append(ext)

    # Conjuntos para rastrear matches
    excel_matched = set()
    extratos_matched = set()

    # =========================================================================
    # NIVEL A: Match por DATA + VALOR unicos
    # =========================================================================
    print("    Nivel A: Matching por DATA + VALOR unicos...")

    for chave, excels in excel_por_chave.items():
        extratos_chave = extrato_por_chave.get(chave, [])

        # So processa se houver exatamente 1 de cada lado
        if len(excels) == 1 and len(extratos_chave) == 1:
            excel = excels[0]
            extrato = extratos_chave[0]

            # Verificar tolerancia de valor
            if valores_proximos(excel['valor'], extrato['valor_decimal']):
                match = {
                    'nivel': 'A',
                    'confianca': 'ALTA',
                    'excel': {
                        'fornecedor': excel['fornecedor'],
                        'nf': excel['nf'],
                        'parcela': excel['parcela'],
                        'data': excel['data'].isoformat(),
                        'valor': float(excel['valor'])
                    },
                    'extrato': {
                        'id': extrato['id'],
                        'data': extrato['data_norm'].isoformat(),
                        'valor': float(extrato['valor_decimal']),
                        'payment_ref': extrato.get('payment_ref', ''),
                        'journal': extrato['journal_id'][1] if extrato.get('journal_id') else None
                    },
                    'diferenca_valor': float(abs(excel['valor'] - extrato['valor_decimal']))
                }
                resultado['matches_nivel_a'].append(match)
                excel_matched.add(excel['idx'])
                extratos_matched.add(extrato['id'])

    print(f"        Matches Nivel A: {len(resultado['matches_nivel_a'])}")

    # =========================================================================
    # NIVEL B: Match por DATA + VALOR + FORNECEDOR (para duplicatas)
    # =========================================================================
    print("    Nivel B: Matching por DATA + VALOR + FORNECEDOR...")

    # Tentar match para itens nao matchados ainda
    for chave, excels in excel_por_chave.items():
        # Filtrar apenas os nao matchados
        excels_pendentes = [e for e in excels if e['idx'] not in excel_matched]
        if not excels_pendentes:
            continue

        extratos_chave = extrato_por_chave.get(chave, [])
        extratos_pendentes = [e for e in extratos_chave if e['id'] not in extratos_matched]
        if not extratos_pendentes:
            continue

        # Tentar match por fornecedor
        for excel in excels_pendentes:
            fornecedor = excel['fornecedor'] or ''

            for extrato in extratos_pendentes:
                if extrato['id'] in extratos_matched:
                    continue

                # Verificar se fornecedor aparece no extrato
                payment_ref = extrato.get('payment_ref', '') or ''
                partner_name = extrato.get('partner_name', '') or ''
                cnpj_extrato = extrato.get('cnpj_extraido', '')

                # Criterios de match por fornecedor
                match_encontrado = False
                motivo_match = ''

                # 1. Partner name contem fornecedor
                if fornecedor and partner_name:
                    # Comparar primeiras palavras
                    palavras_forn = fornecedor.upper().split()[:2]
                    if palavras_forn and all(p in partner_name.upper() for p in palavras_forn):
                        match_encontrado = True
                        motivo_match = 'partner_name contem fornecedor'

                # 2. CNPJ no payment_ref
                if not match_encontrado and cnpj_extrato:
                    # Verificar se CNPJ aparece no nome do fornecedor
                    cnpj_forn = extrair_cnpj(fornecedor)
                    if cnpj_forn and cnpj_forn[:8] == cnpj_extrato[:8]:
                        match_encontrado = True
                        motivo_match = 'CNPJ coincide'

                # 3. Nome do fornecedor aparece no payment_ref
                if not match_encontrado and fornecedor and payment_ref:
                    palavras_forn = fornecedor.upper().split()[:2]
                    if palavras_forn and len(palavras_forn[0]) > 3:
                        if palavras_forn[0] in payment_ref.upper():
                            match_encontrado = True
                            motivo_match = 'nome fornecedor em payment_ref'

                if match_encontrado:
                    match = {
                        'nivel': 'B',
                        'confianca': 'MEDIA',
                        'motivo': motivo_match,
                        'excel': {
                            'fornecedor': excel['fornecedor'],
                            'nf': excel['nf'],
                            'parcela': excel['parcela'],
                            'data': excel['data'].isoformat(),
                            'valor': float(excel['valor'])
                        },
                        'extrato': {
                            'id': extrato['id'],
                            'data': extrato['data_norm'].isoformat(),
                            'valor': float(extrato['valor_decimal']),
                            'payment_ref': extrato.get('payment_ref', ''),
                            'journal': extrato['journal_id'][1] if extrato.get('journal_id') else None
                        },
                        'diferenca_valor': float(abs(excel['valor'] - extrato['valor_decimal']))
                    }
                    resultado['matches_nivel_b'].append(match)
                    excel_matched.add(excel['idx'])
                    extratos_matched.add(extrato['id'])
                    break

    print(f"        Matches Nivel B: {len(resultado['matches_nivel_b'])}")

    # =========================================================================
    # IDENTIFICAR ITENS SEM MATCH
    # =========================================================================

    # Excel sem match
    for idx, row in df_excel.iterrows():
        if idx not in excel_matched:
            resultado['excel_sem_match'].append({
                'fornecedor': row['fornecedor'],
                'nf': row['nf'],
                'parcela': row['parcela'],
                'data': row['data_norm'].isoformat() if row['data_norm'] else None,
                'valor': float(row['valor_decimal'])
            })

    # Extratos sem match
    for ext in extratos:
        if ext['id'] not in extratos_matched:
            resultado['extratos_sem_match'].append({
                'id': ext['id'],
                'data': ext['data_norm'].isoformat() if ext['data_norm'] else None,
                'valor': float(ext['valor_decimal']),
                'payment_ref': ext.get('payment_ref', ''),
                'journal': ext['journal_id'][1] if ext.get('journal_id') else None
            })

    # Estatisticas
    total_matches = len(resultado['matches_nivel_a']) + len(resultado['matches_nivel_b'])
    resultado['estatisticas'] = {
        'total_matches': total_matches,
        'matches_nivel_a': len(resultado['matches_nivel_a']),
        'matches_nivel_b': len(resultado['matches_nivel_b']),
        'excel_sem_match': len(resultado['excel_sem_match']),
        'extratos_sem_match': len(resultado['extratos_sem_match']),
        'taxa_match_excel': round(total_matches / len(df_excel) * 100, 2) if len(df_excel) > 0 else 0,
        'taxa_match_extrato': round(total_matches / len(extratos) * 100, 2) if len(extratos) > 0 else 0
    }

    return resultado


# ==============================================================================
# RELATORIO
# ==============================================================================

def gerar_relatorio(resultado: Dict[str, Any]) -> None:
    """Gera relatorio de diagnostico"""
    print("\n[4/4] Gerando relatorio...")

    stats = resultado['estatisticas']

    print("\n" + "=" * 70)
    print("RELATORIO DE DIAGNOSTICO - CONCILIACAO DE PAGAMENTOS")
    print("=" * 70)

    print(f"""
RESUMO GERAL:
-------------
Total Excel:          {resultado['total_excel']:,} registros
Total Extratos:       {resultado['total_extratos']:,} registros

MATCHES ENCONTRADOS:
--------------------
Nivel A (DATA+VALOR): {stats['matches_nivel_a']:,} matches (confianca ALTA)
Nivel B (DATA+VALOR+FORNECEDOR): {stats['matches_nivel_b']:,} matches (confianca MEDIA)
TOTAL:                {stats['total_matches']:,} matches

PENDENTES:
----------
Excel sem match:      {stats['excel_sem_match']:,} registros
Extratos sem match:   {stats['extratos_sem_match']:,} registros

TAXAS:
------
Taxa match Excel:     {stats['taxa_match_excel']}%
Taxa match Extrato:   {stats['taxa_match_extrato']}%
""")

    # Amostra de matches Nivel A
    if resultado['matches_nivel_a']:
        print("\n" + "-" * 70)
        print("AMOSTRA: MATCHES NIVEL A (primeiros 10)")
        print("-" * 70)
        for m in resultado['matches_nivel_a'][:10]:
            print(f"""
  Excel:   {m['excel']['fornecedor'][:40]} | NF: {m['excel']['nf']} | R$ {m['excel']['valor']:,.2f}
  Extrato: ID {m['extrato']['id']} | {m['extrato']['journal']} | R$ {m['extrato']['valor']:,.2f}
  Data:    {m['excel']['data']}
  Dif:     R$ {m['diferenca_valor']:.2f}
""")

    # Amostra de matches Nivel B
    if resultado['matches_nivel_b']:
        print("\n" + "-" * 70)
        print("AMOSTRA: MATCHES NIVEL B (primeiros 10)")
        print("-" * 70)
        for m in resultado['matches_nivel_b'][:10]:
            print(f"""
  Excel:   {m['excel']['fornecedor'][:40]} | NF: {m['excel']['nf']} | R$ {m['excel']['valor']:,.2f}
  Extrato: ID {m['extrato']['id']} | {m['extrato']['journal']} | R$ {m['extrato']['valor']:,.2f}
  Data:    {m['excel']['data']}
  Motivo:  {m['motivo']}
  Dif:     R$ {m['diferenca_valor']:.2f}
""")

    # Salvar resultado completo em JSON
    arquivo_json = '/tmp/conciliacao_diagnostico.json'
    with open(arquivo_json, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n[OK] Resultado completo salvo em: {arquivo_json}")
    print("=" * 70)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 70)
    print("DIAGNOSTICO DE CONCILIACAO DE PAGAMENTOS")
    print("Fase 1: Analise (SEM ACOES no Odoo)")
    print("=" * 70)

    try:
        # Carregar dados
        df_excel = carregar_excel()
        extratos = carregar_extratos()

        # Executar matching
        resultado = executar_matching(df_excel, extratos)

        # Gerar relatorio
        gerar_relatorio(resultado)

    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
