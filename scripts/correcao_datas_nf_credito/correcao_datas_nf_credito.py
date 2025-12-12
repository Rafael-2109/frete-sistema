#!/usr/bin/env python3
"""
CORREÇÃO - NFs de Crédito com Data de Lançamento Incorreta
===========================================================

Este script corrige as datas de lançamento das NFs de Crédito que foram
alteradas incorretamente.

TABELAS AFETADAS:
- account_move.date: Data de lançamento do documento
- account_move_line.date: Data das linhas do lançamento (sincronizada com cabeçalho)

IMPORTANTE:
- Execute primeiro o script de diagnóstico para gerar o arquivo de correções
- Este script NÃO altera invoice_date (data de emissão da NF)
- Backup será criado antes de qualquer alteração

Autor: Sistema de Fretes - Análise CIEL IT
Data: 11/12/2025
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.odoo.utils.connection import get_odoo_connection


def carregar_diagnostico():
    """Carrega o resultado do diagnóstico"""
    arquivo = os.path.join(os.path.dirname(__file__), 'diagnostico_resultado.json')
    if not os.path.exists(arquivo):
        print("ERRO: Arquivo de diagnóstico não encontrado.")
        print("Execute primeiro: python diagnostico_datas_nf_credito.py")
        return None

    with open(arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def criar_backup(odoo, correcoes):
    """
    Cria backup dos dados antes da correção
    """
    backup_file = os.path.join(
        os.path.dirname(__file__),
        f"backup_antes_correcao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    move_ids = [c['id'] for c in correcoes]

    # Buscar dados atuais
    moves = odoo.execute_kw(
        'account.move', 'search_read',
        [[['id', 'in', move_ids]]],
        {'fields': ['id', 'name', 'date', 'invoice_date', 'state']}
    )

    # Buscar linhas
    lines = odoo.execute_kw(
        'account.move.line', 'search_read',
        [[['move_id', 'in', move_ids]]],
        {'fields': ['id', 'move_id', 'date', 'name']}
    )

    backup = {
        'data_backup': datetime.now().isoformat(),
        'account_move': moves,
        'account_move_line': lines
    }

    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)

    print(f"✓ Backup criado: {backup_file}")
    return backup_file


def corrigir_documento(odoo, move_id, data_original, dry_run=True):
    """
    Corrige a data de lançamento de um documento

    Args:
        odoo: Conexão Odoo
        move_id: ID do account.move
        data_original: Data correta a ser restaurada (YYYY-MM-DD)
        dry_run: Se True, apenas simula a correção

    Returns:
        dict com resultado da operação
    """
    resultado = {
        'move_id': move_id,
        'data_original': data_original,
        'sucesso': False,
        'erro': None,
        'linhas_atualizadas': 0
    }

    try:
        if dry_run:
            # Apenas verificar
            resultado['sucesso'] = True
            resultado['modo'] = 'dry_run'
            return resultado

        # 1. Atualizar account_move.date
        # IMPORTANTE: Em Odoo 17, ao alterar um documento posted,
        # precisamos colocá-lo em draft primeiro
        move = odoo.execute_kw(
            'account.move', 'read',
            [[move_id]],
            {'fields': ['state']}
        )

        if move and move[0]['state'] == 'posted':
            # Voltar para draft
            odoo.execute_kw('account.move', 'button_draft', [[move_id]])

        # 2. Atualizar a data
        odoo.execute_kw(
            'account.move', 'write',
            [[move_id], {'date': data_original}]
        )

        # 3. Atualizar as linhas (account_move_line.date)
        line_ids = odoo.execute_kw(
            'account.move.line', 'search',
            [[['move_id', '=', move_id]]]
        )

        if line_ids:
            odoo.execute_kw(
                'account.move.line', 'write',
                [line_ids, {'date': data_original}]
            )
            resultado['linhas_atualizadas'] = len(line_ids)

        # 4. Re-postar o documento
        if move and move[0]['state'] == 'posted':
            odoo.execute_kw('account.move', 'action_post', [[move_id]])

        resultado['sucesso'] = True
        resultado['modo'] = 'executado'

    except Exception as e:
        resultado['erro'] = str(e)

    return resultado


def executar_correcao(dry_run=True, limite=None):
    """
    Executa a correção das datas

    Args:
        dry_run: Se True, apenas simula sem alterar dados
        limite: Limite de documentos a corrigir (None = todos)
    """
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("ERRO: Falha na autenticação com Odoo")
        return

    # Carregar diagnóstico
    diagnostico = carregar_diagnostico()
    if not diagnostico:
        return

    correcoes = diagnostico['correcoes']

    # Filtrar apenas as que precisam de correção
    precisam_correcao = [
        c for c in correcoes
        if c['date_original'] and c['date_original'] != c['date_atual']
    ]

    if limite:
        precisam_correcao = precisam_correcao[:limite]

    print("=" * 120)
    print("CORREÇÃO - NFs de Crédito com Data de Lançamento Incorreta")
    print(f"Data de execução: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: {'DRY RUN (simulação)' if dry_run else 'EXECUÇÃO REAL'}")
    print("=" * 120)

    print(f"\nTotal de NFs a corrigir: {len(precisam_correcao)}")

    if not precisam_correcao:
        print("\nNenhuma NF precisa de correção.")
        return

    # Criar backup se for execução real
    if not dry_run:
        print("\n[1/3] Criando backup...")
        criar_backup(odoo, precisam_correcao)
    else:
        print("\n[1/3] Backup (pulado em dry_run)")

    # Executar correções
    print(f"\n[2/3] {'Simulando' if dry_run else 'Executando'} correções...")
    print("-" * 120)

    resultados = []
    sucesso = 0
    erro = 0

    for idx, c in enumerate(precisam_correcao):
        resultado = corrigir_documento(
            odoo,
            c['id'],
            c['date_original'],
            dry_run=dry_run
        )
        resultados.append(resultado)

        status = "✓" if resultado['sucesso'] else "✗"
        if resultado['sucesso']:
            sucesso += 1
        else:
            erro += 1

        print(f"  {status} [{idx+1}/{len(precisam_correcao)}] ID {c['id']} ({c['name']}): {c['date_atual']} -> {c['date_original']}")

        if resultado.get('erro'):
            print(f"      ERRO: {resultado['erro']}")

    # Resumo
    print("\n" + "=" * 120)
    print("[3/3] RESUMO")
    print("=" * 120)
    print(f"Total processado: {len(resultados)}")
    print(f"Sucesso: {sucesso}")
    print(f"Erro: {erro}")

    if dry_run:
        print("\n⚠️  MODO DRY RUN - Nenhuma alteração foi realizada")
        print("    Para executar a correção real, use: python correcao_datas_nf_credito.py --executar")

    # Salvar log
    log_file = os.path.join(
        os.path.dirname(__file__),
        f"log_correcao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'data_execucao': datetime.now().isoformat(),
            'modo': 'dry_run' if dry_run else 'executado',
            'total': len(resultados),
            'sucesso': sucesso,
            'erro': erro,
            'resultados': resultados
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Log salvo em: {log_file}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Corrige datas de lançamento de NFs de Crédito',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Simular correção (dry run)
  python correcao_datas_nf_credito.py

  # Executar correção real
  python correcao_datas_nf_credito.py --executar

  # Corrigir apenas as primeiras 10
  python correcao_datas_nf_credito.py --executar --limite 10
        """
    )

    parser.add_argument(
        '--executar',
        action='store_true',
        help='Executa a correção real (sem essa flag, apenas simula)'
    )
    parser.add_argument(
        '--limite',
        type=int,
        default=None,
        help='Limite de documentos a corrigir'
    )

    args = parser.parse_args()

    executar_correcao(dry_run=not args.executar, limite=args.limite)
