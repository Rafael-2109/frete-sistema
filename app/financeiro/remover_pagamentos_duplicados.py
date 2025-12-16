#!/usr/bin/env python3
"""
Script para remover pagamentos duplicados no Odoo
=================================================

Este script remove os pagamentos (account.payment) que foram criados
duplicadamente por um usuário antes da correção de duplicidade.

Uso:
    python remover_pagamentos_duplicados.py --verificar  # Apenas verifica
    python remover_pagamentos_duplicados.py --remover    # Remove de fato

Autor: Rafael
Data: 2025-12-16
"""

import sys
import os
import argparse
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.odoo.utils.connection import get_odoo_connection

def extrair_ids_do_arquivo():
    """Extrai os IDs de pagamento do arquivo ids_remover.md"""
    arquivo = Path(__file__).parent / "ids_remover.md"

    ids = []
    with open(arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    # Pula o cabeçalho (primeira linha)
    for i, linha in enumerate(linhas[1:], start=2):
        if not linha.strip():
            continue

        partes = linha.strip().split('\t')
        if len(partes) >= 1:
            try:
                id_pagamento = int(partes[0])
                ids.append(id_pagamento)
            except ValueError:
                print(f"[AVISO] Linha {i}: Não foi possível extrair ID de '{partes[0]}'")

    return ids


def verificar_pagamentos(connection, ids_para_verificar):
    """Verifica uma amostra de pagamentos no Odoo"""
    print(f"\n{'='*60}")
    print("VERIFICAÇÃO DE AMOSTRA DE PAGAMENTOS")
    print(f"{'='*60}\n")

    # Pega uma amostra de 5 IDs
    amostra = ids_para_verificar[:5]

    print(f"Verificando {len(amostra)} pagamentos de amostra...")

    pagamentos = connection.read(
        'account.payment',
        amostra,
        ['id', 'name', 'date', 'amount', 'state', 'ref', 'partner_id', 'payment_type']
    )

    if not pagamentos:
        print("❌ Nenhum pagamento encontrado com esses IDs!")
        return False

    print(f"\n✅ Encontrados {len(pagamentos)} pagamentos:\n")

    for pag in pagamentos:
        partner_name = pag.get('partner_id', [None, 'N/A'])
        if isinstance(partner_name, (list, tuple)) and len(partner_name) > 1:
            partner_name = partner_name[1]
        else:
            partner_name = 'N/A'

        print(f"  ID: {pag['id']}")
        print(f"    Nome: {pag.get('name', 'N/A')}")
        print(f"    Data: {pag.get('date', 'N/A')}")
        print(f"    Valor: R$ {pag.get('amount', 0):,.2f}")
        print(f"    Estado: {pag.get('state', 'N/A')}")
        print(f"    Tipo: {pag.get('payment_type', 'N/A')}")
        print(f"    Ref: {pag.get('ref', 'N/A')}")
        print(f"    Parceiro: {partner_name}")
        print()

    return True


def contar_pagamentos_por_estado(connection, ids):
    """Conta quantos pagamentos existem por estado"""
    print(f"\n{'='*60}")
    print("CONTAGEM DE PAGAMENTOS POR ESTADO")
    print(f"{'='*60}\n")

    # Busca todos os pagamentos com seus estados
    # Fazemos em lotes para não sobrecarregar
    LOTE = 500
    estados = {}
    total_encontrados = 0

    for i in range(0, len(ids), LOTE):
        lote_ids = ids[i:i+LOTE]
        pagamentos = connection.read(
            'account.payment',
            lote_ids,
            ['id', 'state']
        )

        if pagamentos:
            total_encontrados += len(pagamentos)
            for pag in pagamentos:
                estado = pag.get('state', 'desconhecido')
                estados[estado] = estados.get(estado, 0) + 1

    print(f"Total de IDs fornecidos: {len(ids)}")
    print(f"Total encontrados no Odoo: {total_encontrados}")
    print(f"Diferença (não encontrados): {len(ids) - total_encontrados}")
    print()

    if estados:
        print("Contagem por estado:")
        for estado, qtd in sorted(estados.items()):
            print(f"  - {estado}: {qtd}")

    return estados, total_encontrados


def remover_pagamentos(connection, ids, modo_dry_run=True):
    """Remove os pagamentos em lotes"""
    print(f"\n{'='*60}")
    if modo_dry_run:
        print("SIMULAÇÃO DE REMOÇÃO (DRY RUN)")
    else:
        print("EXECUTANDO REMOÇÃO DE PAGAMENTOS")
    print(f"{'='*60}\n")

    LOTE = 50  # Remove em lotes de 50
    total = len(ids)
    removidos = 0
    erros = []

    for i in range(0, total, LOTE):
        lote_ids = ids[i:i+LOTE]
        lote_num = (i // LOTE) + 1
        total_lotes = (total + LOTE - 1) // LOTE

        print(f"Lote {lote_num}/{total_lotes}: Processando {len(lote_ids)} pagamentos (IDs {lote_ids[0]} a {lote_ids[-1]})...")

        if modo_dry_run:
            # Apenas verifica se existem
            pagamentos = connection.read(
                'account.payment',
                lote_ids,
                ['id', 'name', 'state']
            )
            if pagamentos:
                removidos += len(pagamentos)
                print(f"  ✓ {len(pagamentos)} pagamentos seriam removidos")
            else:
                print(f"  ⚠ Nenhum pagamento encontrado neste lote")
        else:
            try:
                # Primeiro tenta colocar em draft se estiverem posted
                # Depois remove

                # Verifica estados atuais
                pagamentos = connection.read(
                    'account.payment',
                    lote_ids,
                    ['id', 'name', 'state']
                )

                if not pagamentos:
                    print(f"  ⚠ Nenhum pagamento encontrado neste lote")
                    continue

                ids_encontrados = [p['id'] for p in pagamentos]

                # Para pagamentos posted, precisamos cancelar primeiro
                ids_posted = [p['id'] for p in pagamentos if p.get('state') == 'posted']

                if ids_posted:
                    print(f"  → Cancelando {len(ids_posted)} pagamentos posted...")
                    try:
                        connection.execute_kw(
                            'account.payment',
                            'action_draft',
                            [ids_posted]
                        )
                    except Exception as e:
                        print(f"  ⚠ Aviso ao cancelar: {e}")
                        # Tenta cancelar um por um
                        for id_pag in ids_posted:
                            try:
                                connection.execute_kw(
                                    'account.payment',
                                    'action_cancel',
                                    [[id_pag]]
                                )
                            except Exception as e2:
                                print(f"    ⚠ ID {id_pag}: {e2}")

                # Agora remove usando unlink
                print(f"  → Removendo {len(ids_encontrados)} pagamentos...")
                connection.execute_kw(
                    'account.payment',
                    'unlink',
                    [ids_encontrados]
                )

                removidos += len(ids_encontrados)
                print(f"  ✓ {len(ids_encontrados)} removidos com sucesso")

            except Exception as e:
                erro_msg = f"Erro no lote {lote_num}: {e}"
                erros.append(erro_msg)
                print(f"  ❌ {erro_msg}")

    print(f"\n{'='*60}")
    print("RESUMO")
    print(f"{'='*60}")
    print(f"Total de IDs fornecidos: {total}")
    print(f"Total removidos: {removidos}")
    if erros:
        print(f"Total de erros: {len(erros)}")
        for erro in erros[:10]:  # Mostra só os primeiros 10
            print(f"  - {erro}")

    return removidos, erros


def main():
    parser = argparse.ArgumentParser(
        description='Remove pagamentos duplicados do Odoo'
    )
    parser.add_argument(
        '--verificar',
        action='store_true',
        help='Apenas verifica os pagamentos sem remover'
    )
    parser.add_argument(
        '--remover',
        action='store_true',
        help='Remove os pagamentos (AÇÃO DESTRUTIVA!)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula a remoção sem executar de fato'
    )

    args = parser.parse_args()

    if not args.verificar and not args.remover and not args.dry_run:
        parser.print_help()
        print("\n⚠ Você deve especificar --verificar, --dry-run ou --remover")
        sys.exit(1)

    # Extrai IDs do arquivo
    print("Extraindo IDs do arquivo ids_remover.md...")
    ids = extrair_ids_do_arquivo()
    print(f"✓ {len(ids)} IDs extraídos\n")

    if not ids:
        print("❌ Nenhum ID encontrado!")
        sys.exit(1)

    # Conecta ao Odoo
    print("Conectando ao Odoo...")
    connection = get_odoo_connection()

    if not connection.authenticate():
        print("❌ Falha na autenticação com Odoo!")
        sys.exit(1)

    print("✓ Conectado ao Odoo\n")

    if args.verificar:
        # Apenas verifica
        verificar_pagamentos(connection, ids)
        contar_pagamentos_por_estado(connection, ids)

    elif args.dry_run:
        # Simula remoção
        verificar_pagamentos(connection, ids)
        estados, total = contar_pagamentos_por_estado(connection, ids)
        remover_pagamentos(connection, ids, modo_dry_run=True)

    elif args.remover:
        # Remove de fato
        print("\n" + "!"*60)
        print("ATENÇÃO: Esta ação é IRREVERSÍVEL!")
        print("!"*60 + "\n")

        verificar_pagamentos(connection, ids)
        estados, total = contar_pagamentos_por_estado(connection, ids)

        resposta = input(f"\nDeseja REALMENTE remover {total} pagamentos? (digite 'SIM' para confirmar): ")

        if resposta.strip().upper() == 'SIM':
            remover_pagamentos(connection, ids, modo_dry_run=False)
        else:
            print("\n❌ Operação cancelada pelo usuário")


if __name__ == '__main__':
    main()
