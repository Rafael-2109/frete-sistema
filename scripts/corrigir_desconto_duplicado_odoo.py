#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Genérico para Corrigir Desconto Duplicado no Odoo (Título Ano 2000)

O Odoo está aplicando desconto múltiplas vezes em clientes com desconto contratual:
1. Linha contábil de desconto concedido (correto)
2. Título com vencimento 01/01/2000 (BUG - duplicação)

Este script corrige o problema zerando o título ano 2000 e ajustando os valores.

Uso:
    python scripts/corrigir_desconto_duplicado_odoo.py <MOVE_ID>
    python scripts/corrigir_desconto_duplicado_odoo.py 479591

Autor: Sistema de Fretes / Rafael Nascimento
Data: 2026-01-27
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection


def analisar_fatura(conn, move_id: int) -> dict:
    """Analisa a fatura e retorna os dados necessários para correção."""
    print("\n" + "=" * 70)
    print(f"ANÁLISE DA FATURA {move_id}")
    print("=" * 70)

    # Buscar fatura
    move = conn.search_read('account.move', [['id', '=', move_id]], [
        'name', 'state', 'amount_total', 'amount_residual', 'payment_state', 'partner_id'
    ])

    if not move:
        print(f"✗ Fatura {move_id} não encontrada!")
        return None

    m = move[0]
    partner_id = m['partner_id'][0] if m['partner_id'] else None

    print(f"\nFatura: {m['name']}")
    print(f"  Estado: {m['state']}")
    print(f"  Valor Total: R$ {m['amount_total']:.2f}")
    print(f"  Residual: R$ {m['amount_residual']:.2f}")
    print(f"  Payment State: {m['payment_state']}")

    # Buscar desconto do parceiro
    desconto_pct = 0
    if partner_id:
        partner = conn.search_read('res.partner', [['id', '=', partner_id]], [
            'name', 'x_studio_desconto_contratual', 'x_studio_desconto'
        ])
        if partner:
            p = partner[0]
            print(f"\n  Parceiro: {p['name']} (ID: {partner_id})")
            print(f"  Desconto Contratual: {p.get('x_studio_desconto_contratual', False)}")
            desconto_pct = p.get('x_studio_desconto', 0)
            print(f"  Percentual: {desconto_pct}%")

    # Buscar títulos CLIENTES com débito > 0
    titulos = conn.search_read('account.move.line', [
        ['move_id', '=', move_id],
        ['account_id.name', 'ilike', 'CLIENTES'],
        ['debit', '>', 0]
    ], ['id', 'debit', 'date_maturity', 'amount_residual'])

    titulo_valido = None
    titulos_2000 = []

    print(f"\n--- TÍTULOS A RECEBER ({len(titulos)}) ---")
    for t in titulos:
        ano = t['date_maturity'][:4] if t['date_maturity'] else 'N/A'
        if ano == '2000':
            titulos_2000.append(t)
            status = "⚠ ANO 2000 (BUG)"
        else:
            titulo_valido = t
            status = "✓ VÁLIDO"
        print(f"  ID {t['id']}: R$ {t['debit']:.2f} | Venc: {t['date_maturity']} | {status}")

    # Buscar linhas de desconto
    descontos = conn.search_read('account.move.line', [
        ['move_id', '=', move_id],
        ['account_id.name', 'ilike', 'DESCONTO']
    ], ['id', 'debit', 'credit'])

    print(f"\n--- LINHAS DE DESCONTO ({len(descontos)}) ---")
    for d in descontos:
        valor = d['debit'] if d['debit'] > 0 else d['credit']
        tipo = "D" if d['debit'] > 0 else "C"
        print(f"  ID {d['id']}: R$ {valor:.2f} ({tipo})")

    # Calcular valores
    # IMPORTANTE: O título correto é a SOMA dos títulos (válido + ano 2000)
    # O Odoo divide o valor em dois títulos quando deveria ser apenas um
    valor_titulo_correto = sum(t['debit'] for t in titulos)

    # O desconto vem da linha de DESCONTOS CONCEDIDOS existente
    valor_desconto_existente = sum(d['debit'] for d in descontos if d['debit'] > 0)

    # Alternativa: calcular desconto
    valor_desconto_calculado = valor_titulo_correto * (desconto_pct / 100) if desconto_pct > 0 else valor_desconto_existente

    print(f"\n--- CÁLCULO ---")
    print(f"  Valor Título Correto (soma): R$ {valor_titulo_correto:.2f}")
    print(f"  Desconto existente: R$ {valor_desconto_existente:.2f}")
    print(f"  Desconto calculado ({desconto_pct}%): R$ {valor_desconto_calculado:.2f}")

    if not titulos_2000:
        print("\n" + "=" * 70)
        print("✓ Fatura NÃO possui o bug (sem título ano 2000)")
        print("=" * 70)
        return None

    print("\n" + "=" * 70)
    print("⚠ FATURA POSSUI BUG DE DESCONTO DUPLICADO!")
    print("=" * 70)

    return {
        'move_id': move_id,
        'move_name': m['name'],
        'partner_id': partner_id,
        'desconto_pct': desconto_pct,
        'titulo_valido': titulo_valido,
        'titulos_2000': titulos_2000,
        'descontos': descontos,
        'valor_titulo_correto': valor_titulo_correto,
        'valor_desconto': valor_desconto_existente
    }


def corrigir_fatura(conn, dados: dict, dry_run: bool = False) -> bool:
    """Executa a correção da fatura."""
    move_id = dados['move_id']

    print("\n" + "=" * 70)
    print(f"CORREÇÃO DA FATURA {move_id}")
    print("=" * 70)

    if dry_run:
        print("\n⚠ MODO DRY-RUN - Nenhuma alteração será feita")

    # PASSO 1: Despublicar
    print("\n[1/6] Despublicando fatura...")
    if not dry_run:
        try:
            conn.execute_kw('account.move', 'button_draft', [[move_id]])
            print("     ✓ Fatura despublicada")
        except Exception as e:
            if "cannot marshal None" in str(e):
                print("     ✓ Fatura despublicada")
            else:
                print(f"     ✗ Erro: {e}")
                return False

    # PASSO 2: Zerar títulos ano 2000
    print("\n[2/6] Zerando títulos ano 2000...")
    for t in dados['titulos_2000']:
        print(f"     → ID {t['id']}: R$ {t['debit']:.2f}")
        if not dry_run:
            try:
                conn.execute_kw('account.move.line', 'write', [[t['id']], {
                    'debit': 0,
                    'credit': 0
                }])
                print(f"     ✓ Zerado")
            except Exception as e:
                print(f"     ✗ Erro: {e}")

    # PASSO 3: Configurar desconto
    print("\n[3/6] Configurando linha de desconto...")
    valor_desconto = dados['valor_desconto']
    for i, d in enumerate(dados['descontos']):
        if i == 0:
            print(f"     → ID {d['id']}: Configurando para R$ {valor_desconto:.2f}")
            if not dry_run:
                try:
                    conn.execute_kw('account.move.line', 'write', [[d['id']], {
                        'debit': valor_desconto,
                        'credit': 0
                    }])
                    print(f"     ✓ Configurado")
                except Exception as e:
                    print(f"     ✗ Erro: {e}")
        else:
            print(f"     → ID {d['id']}: Zerando")
            if not dry_run:
                try:
                    conn.execute_kw('account.move.line', 'write', [[d['id']], {
                        'debit': 0,
                        'credit': 0
                    }])
                    print(f"     ✓ Zerado")
                except Exception as e:
                    print(f"     ✗ Erro: {e}")

    # PASSO 4: Ajustar título válido para o valor correto (soma dos títulos)
    print("\n[4/6] Ajustando título válido...")
    titulo_valido = dados['titulo_valido']
    valor_titulo_correto = dados['valor_titulo_correto']
    print(f"     → ID {titulo_valido['id']}: R$ {titulo_valido['debit']:.2f} → R$ {valor_titulo_correto:.2f}")
    if not dry_run:
        try:
            conn.execute_kw('account.move.line', 'write', [[titulo_valido['id']], {
                'debit': valor_titulo_correto,
                'amount_residual': valor_titulo_correto
            }])
            print(f"     ✓ Ajustado")
        except Exception as e:
            print(f"     ✗ Erro: {e}")

    # PASSO 5: Verificar equilíbrio
    print("\n[5/6] Verificando equilíbrio...")
    if not dry_run:
        lines = conn.search_read('account.move.line', [['move_id', '=', move_id]], ['debit', 'credit'])
        total_debito = sum(line['debit'] for line in lines)
        total_credito = sum(line['credit'] for line in lines)
        diferenca = abs(total_debito - total_credito)
        print(f"     Total Débito: R$ {total_debito:.2f}")
        print(f"     Total Crédito: R$ {total_credito:.2f}")
        print(f"     Diferença: R$ {diferenca:.2f}")

        if diferenca > 0.01:
            print(f"     ⚠ Fatura desbalanceada!")
            return False

        print(f"     ✓ Fatura equilibrada!")

    # PASSO 6: Republicar
    print("\n[6/6] Republicando fatura...")
    if not dry_run:
        try:
            conn.execute_kw('account.move', 'action_post', [[move_id]])
            print("     ✓ Fatura republicada")
        except Exception as e:
            if "cannot marshal None" in str(e):
                print("     ✓ Fatura republicada")
            else:
                print(f"     ✗ Erro: {e}")
                return False

    # Verificar se criou novo título ano 2000
    if not dry_run:
        print("\n[EXTRA] Verificando se Odoo criou novo título ano 2000...")
        novos_2000 = conn.search_read('account.move.line', [
            ['move_id', '=', move_id],
            ['date_maturity', '=', '2000-01-01'],
            ['debit', '>', 0]
        ], ['id', 'debit'])

        if novos_2000:
            print(f"     ⚠ Odoo criou {len(novos_2000)} novo(s) título(s) ano 2000!")
            print("     → Executando segunda rodada de correção...")

            # Despublicar novamente
            conn.execute_kw('account.move', 'button_draft', [[move_id]])

            # Zerar novos títulos
            for t in novos_2000:
                conn.execute_kw('account.move.line', 'write', [[t['id']], {
                    'debit': 0,
                    'credit': 0
                }])

            # Republicar
            conn.execute_kw('account.move', 'action_post', [[move_id]])
            print("     ✓ Segunda correção aplicada")
        else:
            print("     ✓ Nenhum novo título ano 2000 criado")

    return True


def verificar_resultado(conn, move_id: int):
    """Verifica o resultado final da correção."""
    print("\n" + "=" * 70)
    print(f"RESULTADO FINAL - FATURA {move_id}")
    print("=" * 70)

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

    # Buscar títulos
    titulos = conn.search_read('account.move.line', [
        ['move_id', '=', move_id],
        ['account_id.name', 'ilike', 'CLIENTES'],
        ['debit', '>', 0]
    ], ['id', 'debit', 'date_maturity', 'amount_residual'])

    print(f"\n--- TÍTULOS A RECEBER ({len(titulos)}) ---")
    tem_2000 = False
    for t in titulos:
        ano = t['date_maturity'][:4] if t['date_maturity'] else 'N/A'
        if ano == '2000':
            tem_2000 = True
            status = "⚠ ANO 2000 (BUG)"
        else:
            status = "✓ VÁLIDO"
        print(f"  ID {t['id']}: R$ {t['debit']:.2f} | Venc: {t['date_maturity']} | {status}")

    # Buscar descontos
    descontos = conn.search_read('account.move.line', [
        ['move_id', '=', move_id],
        ['account_id.name', 'ilike', 'DESCONTO'],
        ['debit', '>', 0]
    ], ['id', 'debit'])

    print(f"\n--- LINHAS DE DESCONTO ({len(descontos)}) ---")
    for d in descontos:
        print(f"  ID {d['id']}: R$ {d['debit']:.2f}")

    if not tem_2000:
        print("\n" + "=" * 70)
        print("✓ CORREÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        return True
    else:
        print("\n" + "=" * 70)
        print("⚠ ATENÇÃO: Ainda existe título ano 2000!")
        print("=" * 70)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Corrige desconto duplicado (título ano 2000) no Odoo'
    )
    parser.add_argument('move_id', type=int, help='ID da fatura (account.move)')
    parser.add_argument('--dry-run', action='store_true', help='Simular sem fazer alterações')
    parser.add_argument('--force', action='store_true', help='Executar sem confirmação')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("CORREÇÃO DE DESCONTO DUPLICADO - ODOO")
    print("=" * 70)

    # Conectar ao Odoo
    print("\nConectando ao Odoo...")
    conn = get_odoo_connection()
    print("✓ Conectado")

    # Analisar fatura
    dados = analisar_fatura(conn, args.move_id)

    if not dados:
        print("\nNenhuma correção necessária.")
        return

    # Confirmar execução
    if not args.force and not args.dry_run:
        print("\n" + "=" * 70)
        print("ATENÇÃO: Esta operação irá modificar a fatura no Odoo!")
        print("=" * 70)
        resposta = input("\nDigite 'SIM' para continuar: ")
        if resposta.upper() != 'SIM':
            print("Operação cancelada.")
            return

    # Executar correção
    sucesso = corrigir_fatura(conn, dados, dry_run=args.dry_run)

    if sucesso and not args.dry_run:
        verificar_resultado(conn, args.move_id)

    print("\n✓ Processo finalizado!")


if __name__ == '__main__':
    main()
