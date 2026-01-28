#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir desconto duplicado na NF 479610

O Odoo está aplicando desconto múltiplas vezes:
1. Linha contábil de desconto concedido (correto)
2. Título com vencimento 01/01/2000 (BUG - duplicação)

Estratégia:
1. Despublicar fatura (button_draft)
2. Deletar título ano 2000
3. Deletar TODAS as linhas de desconto
4. Republicar (action_post)
5. O Odoo deve gerar o desconto APENAS 1 vez

Autor: Sistema de Fretes
Data: 2026-01-27
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection


# =============================================================================
# DADOS DA FATURA
# =============================================================================
MOVE_ID = 479610

# Título válido (manter)
TITULO_VALIDO_ID = 3012812

# Título ano 2000 (deletar)
TITULO_ANO_2000_ID = 3013311

# Linhas de desconto (todas a deletar)
LINHAS_DESCONTO = [3012813, 3012994, 3013037, 3013153, 3013154]


def mostrar_estado_atual(conn, move_id: int):
    """Mostra o estado atual da fatura."""
    print("\n" + "=" * 60)
    print("ESTADO ATUAL DA FATURA")
    print("=" * 60)

    # Buscar fatura
    move = conn.search_read('account.move', [['id', '=', move_id]], [
        'name', 'state', 'amount_total', 'amount_residual', 'payment_state'
    ])
    if move:
        m = move[0]
        print(f"\nFatura: {m['name']}")
        print(f"  Estado: {m['state']}")
        print(f"  Valor Total: R$ {m['amount_total']:.2f}")
        print(f"  Residual: R$ {m['amount_residual']:.2f}")
        print(f"  Payment State: {m['payment_state']}")

    # Buscar linhas
    lines = conn.search_read('account.move.line', [['move_id', '=', move_id]], [
        'id', 'name', 'account_id', 'debit', 'credit', 'date_maturity', 'amount_residual'
    ])

    # Separar por tipo
    titulos = []
    descontos = []
    outras = []

    for line in lines:
        account_name = line['account_id'][1] if line['account_id'] else ''
        if 'CLIENTES' in account_name.upper() and line['debit'] > 0:
            titulos.append(line)
        elif 'DESCONTO' in account_name.upper():
            descontos.append(line)
        else:
            outras.append(line)

    print(f"\n--- TÍTULOS A RECEBER ({len(titulos)}) ---")
    for t in titulos:
        print(f"  ID {t['id']}: R$ {t['debit']:.2f} | Venc: {t['date_maturity']} | Residual: {t['amount_residual']:.2f}")

    print(f"\n--- LINHAS DE DESCONTO ({len(descontos)}) ---")
    for d in descontos:
        print(f"  ID {d['id']}: Débito R$ {d['debit']:.2f} | Crédito R$ {d['credit']:.2f}")

    print(f"\n--- OUTRAS LINHAS ({len(outras)}) ---")
    print(f"  (omitidas para brevidade)")

    return lines


def passo_1_despublicar(conn, move_id: int):
    """Passo 1: Despublicar a fatura."""
    print("\n" + "=" * 60)
    print("PASSO 1: DESPUBLICAR FATURA")
    print("=" * 60)

    try:
        result = conn.execute_kw('account.move', 'button_draft', [[move_id]])
        print(f"✓ Fatura {move_id} despublicada com sucesso")
        return True
    except Exception as e:
        if "cannot marshal None" in str(e):
            print(f"✓ Fatura {move_id} despublicada (ignorando erro de serialização)")
            return True
        print(f"✗ Erro ao despublicar: {e}")
        return False


def passo_2_deletar_titulo_ano_2000(conn, titulo_id: int):
    """Passo 2: Deletar título ano 2000."""
    print("\n" + "=" * 60)
    print("PASSO 2: DELETAR TÍTULO ANO 2000")
    print("=" * 60)

    # Verificar se existe
    titulo = conn.search_read('account.move.line', [['id', '=', titulo_id]], ['id', 'debit'])
    if not titulo:
        print(f"⚠ Título {titulo_id} não encontrado (pode já ter sido deletado)")
        return True

    try:
        result = conn.execute_kw('account.move.line', 'unlink', [[titulo_id]])
        print(f"✓ Título {titulo_id} deletado com sucesso")
        return True
    except Exception as e:
        print(f"✗ Erro ao deletar título: {e}")
        # Tentar zerar ao invés de deletar
        print("  Tentando zerar valores ao invés de deletar...")
        try:
            conn.execute_kw('account.move.line', 'write', [[titulo_id], {
                'debit': 0,
                'credit': 0,
                'amount_residual': 0
            }])
            print(f"✓ Título {titulo_id} zerado com sucesso")
            return True
        except Exception as e2:
            print(f"✗ Erro ao zerar: {e2}")
            return False


def passo_3_deletar_linhas_desconto(conn, linhas_ids: list):
    """Passo 3: Deletar linhas de desconto."""
    print("\n" + "=" * 60)
    print("PASSO 3: DELETAR LINHAS DE DESCONTO")
    print("=" * 60)

    sucesso = True
    for linha_id in linhas_ids:
        # Verificar se existe
        linha = conn.search_read('account.move.line', [['id', '=', linha_id]], ['id', 'debit', 'credit'])
        if not linha:
            print(f"⚠ Linha {linha_id} não encontrada")
            continue

        try:
            result = conn.execute_kw('account.move.line', 'unlink', [[linha_id]])
            print(f"✓ Linha {linha_id} deletada")
        except Exception as e:
            print(f"⚠ Não foi possível deletar linha {linha_id}: {e}")
            # Tentar zerar
            try:
                conn.execute_kw('account.move.line', 'write', [[linha_id], {
                    'debit': 0,
                    'credit': 0
                }])
                print(f"✓ Linha {linha_id} zerada")
            except Exception as e2:
                print(f"✗ Erro ao zerar linha {linha_id}: {e2}")
                sucesso = False

    return sucesso


def passo_4_republicar(conn, move_id: int):
    """Passo 4: Republicar a fatura."""
    print("\n" + "=" * 60)
    print("PASSO 4: REPUBLICAR FATURA")
    print("=" * 60)

    try:
        result = conn.execute_kw('account.move', 'action_post', [[move_id]])
        print(f"✓ Fatura {move_id} republicada com sucesso")
        return True
    except Exception as e:
        if "cannot marshal None" in str(e):
            print(f"✓ Fatura {move_id} republicada (ignorando erro de serialização)")
            return True
        print(f"✗ Erro ao republicar: {e}")
        return False


def main():
    """Executa a correção."""
    print("\n" + "=" * 60)
    print("CORREÇÃO DE DESCONTO DUPLICADO - NF 479610")
    print("=" * 60)

    # Conectar ao Odoo
    print("\nConectando ao Odoo...")
    conn = get_odoo_connection()
    print("✓ Conectado")

    # Mostrar estado atual
    mostrar_estado_atual(conn, MOVE_ID)

    # Confirmar execução
    print("\n" + "=" * 60)
    print("ATENÇÃO: Esta operação irá modificar a fatura no Odoo!")
    print("=" * 60)
    resposta = input("\nDigite 'SIM' para continuar: ")
    if resposta.upper() != 'SIM':
        print("Operação cancelada.")
        return

    # Executar passos
    if not passo_1_despublicar(conn, MOVE_ID):
        print("\n✗ Falha no passo 1. Abortando.")
        return

    if not passo_2_deletar_titulo_ano_2000(conn, TITULO_ANO_2000_ID):
        print("\n✗ Falha no passo 2. Continuando mesmo assim...")

    if not passo_3_deletar_linhas_desconto(conn, LINHAS_DESCONTO):
        print("\n⚠ Algumas linhas de desconto não puderam ser processadas.")

    if not passo_4_republicar(conn, MOVE_ID):
        print("\n✗ Falha no passo 4. A fatura pode estar em estado inconsistente!")
        return

    # Mostrar resultado final
    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    mostrar_estado_atual(conn, MOVE_ID)

    print("\n✓ Correção concluída!")
    print("Verifique no Odoo se:")
    print("  1. Não existe mais título com vencimento 01/01/2000")
    print("  2. Existe apenas 1 linha de desconto com R$ 55,05")
    print("  3. O título válido tem o valor correto")


if __name__ == '__main__':
    main()
