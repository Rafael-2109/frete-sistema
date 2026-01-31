#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Corrigir Desconto Concedido Zerado na NF 134244

Fatura: VND/2025/00085 (Odoo ID 253885)
Parceiro: REDE ASSAI LJ 25 (ID 206603)
Problema: Linha de desconto concedido (ID 1670513) existe mas esta zerada.
          O titulo a receber (ID 1670512) esta com valor bruto (sem desconto).

EXECUTADO EM 2026-01-30 - CORRECAO APLICADA COM SUCESSO:
- Titulo: R$ 9.275,32 -> R$ 9.228,94 (liquido com desconto 0,5%)
- Desconto: R$ 0,00 -> R$ 46,38 (debito na conta DESCONTOS CONCEDIDOS)
- Fatura republicada e equilibrada (D=C=R$ 12.169,28)
- NOTA: O Odoo criou um titulo ano 2000 durante o process que foi zerado.

Uso:
    python scripts/corrigir_nf_134244.py --dry-run       # Simular
    python scripts/corrigir_nf_134244.py --force          # Executar sem confirmacao

Autor: Sistema de Fretes / Rafael Nascimento
Data: 2026-01-30
"""

import sys
import os
import argparse
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection


# =============================================================================
# DADOS CONHECIDOS DA FATURA
# =============================================================================
MOVE_ID = 253885
MOVE_NAME = 'VND/2025/00085'
PARTNER_ID = 206603
TITULO_ID = 1670512
DESCONTO_LINE_ID = 1670513


def analisar_fatura(conn) -> dict:
    """Analisa a fatura e retorna os dados necessarios para correcao."""
    print("\n" + "=" * 70)
    print(f"ANALISE DA FATURA {MOVE_ID} ({MOVE_NAME})")
    print("=" * 70)

    # 1. Buscar fatura
    move = conn.search_read('account.move', [['id', '=', MOVE_ID]], [
        'name', 'state', 'amount_total', 'amount_residual', 'payment_state', 'partner_id'
    ])

    if not move:
        print(f"ERRO: Fatura {MOVE_ID} nao encontrada!")
        return None

    m = move[0]
    print(f"\nFatura: {m['name']}")
    print(f"  Estado: {m['state']}")
    print(f"  Valor Total: R$ {m['amount_total']:.2f}")
    print(f"  Residual: R$ {m['amount_residual']:.2f}")
    print(f"  Payment State: {m['payment_state']}")

    if m['state'] != 'posted':
        print(f"\n  ATENCAO: Fatura nao esta 'posted' (esta '{m['state']}')")
        print(f"  Pode ser necessario ajustar a estrategia.")

    # 2. Buscar desconto do parceiro
    partner = conn.search_read('res.partner', [['id', '=', PARTNER_ID]], [
        'name', 'x_studio_desconto_contratual', 'x_studio_desconto'
    ])

    desconto_pct = Decimal('0')
    if partner:
        p = partner[0]
        print(f"\n  Parceiro: {p['name']} (ID: {PARTNER_ID})")
        print(f"  Desconto Contratual: {p.get('x_studio_desconto_contratual', False)}")
        raw_pct = p.get('x_studio_desconto', 0) or 0
        desconto_pct = Decimal(str(raw_pct))
        print(f"  Percentual: {desconto_pct}%")
    else:
        print(f"\n  ERRO: Parceiro {PARTNER_ID} nao encontrado!")
        return None

    if desconto_pct <= 0:
        print(f"\n  ERRO: Parceiro nao possui desconto contratual!")
        return None

    # 3. Buscar TODAS as linhas da fatura para analise completa
    all_lines = conn.search_read('account.move.line', [
        ['move_id', '=', MOVE_ID]
    ], ['id', 'name', 'account_id', 'debit', 'credit', 'date_maturity', 'amount_residual'])

    total_debito = sum(l['debit'] for l in all_lines)
    total_credito = sum(l['credit'] for l in all_lines)

    print(f"\n--- TODAS AS LINHAS ({len(all_lines)}) ---")
    print(f"  Total Debito: R$ {total_debito:.2f}")
    print(f"  Total Credito: R$ {total_credito:.2f}")
    print(f"  Diferenca: R$ {abs(total_debito - total_credito):.2f}")

    # 4. Buscar titulo a receber
    titulo = None
    for l in all_lines:
        if l['id'] == TITULO_ID:
            titulo = l
            break

    if not titulo:
        print(f"\n  ERRO: Titulo ID {TITULO_ID} nao encontrado!")
        return None

    print(f"\n--- TITULO A RECEBER ---")
    print(f"  ID: {titulo['id']}")
    print(f"  Debito: R$ {titulo['debit']:.2f}")
    print(f"  Residual: R$ {titulo['amount_residual']:.2f}")
    print(f"  Vencimento: {titulo['date_maturity']}")
    print(f"  Conta: {titulo['account_id'][1] if titulo['account_id'] else 'N/A'}")

    # 5. Buscar linha de desconto
    desconto_line = None
    for l in all_lines:
        if l['id'] == DESCONTO_LINE_ID:
            desconto_line = l
            break

    if not desconto_line:
        print(f"\n  ERRO: Linha de desconto ID {DESCONTO_LINE_ID} nao encontrada!")
        return None

    print(f"\n--- LINHA DE DESCONTO ---")
    print(f"  ID: {desconto_line['id']}")
    print(f"  Debito: R$ {desconto_line['debit']:.2f}")
    print(f"  Credito: R$ {desconto_line['credit']:.2f}")
    print(f"  Conta: {desconto_line['account_id'][1] if desconto_line['account_id'] else 'N/A'}")

    if desconto_line['debit'] > 0 or desconto_line['credit'] > 0:
        print(f"\n  ATENCAO: Linha de desconto NAO esta zerada!")
        print(f"  Desconto ja pode estar aplicado.")

    # 6. Verificar se existem titulos ano 2000
    titulos_2000 = [l for l in all_lines
                    if l.get('date_maturity') and l['date_maturity'][:4] == '2000'
                    and l['debit'] > 0]
    if titulos_2000:
        print(f"\n  ATENCAO: Existem {len(titulos_2000)} titulo(s) ano 2000!")
        for t in titulos_2000:
            print(f"    ID {t['id']}: R$ {t['debit']:.2f}")

    # 7. Calcular valores
    # O titulo atual contem o valor BRUTO (sem desconto, pois desconto esta zerado)
    valor_titulo_atual = Decimal(str(titulo['debit']))

    # O desconto eh sobre o valor bruto do titulo
    valor_desconto = (valor_titulo_atual * desconto_pct / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    valor_titulo_novo = valor_titulo_atual - valor_desconto

    print(f"\n--- CALCULO ---")
    print(f"  Titulo atual (bruto): R$ {valor_titulo_atual:.2f}")
    print(f"  Desconto ({desconto_pct}%): R$ {valor_desconto:.2f}")
    print(f"  Titulo novo (liquido): R$ {valor_titulo_novo:.2f}")

    # Verificar se o desconto faz sentido
    if valor_desconto <= 0:
        print(f"\n  ERRO: Desconto calculado eh zero ou negativo!")
        return None

    # Verificar se apos a correcao a fatura ficara equilibrada
    # Debito atual = X, Credito atual = X (equilibrado)
    # Mudanca: titulo -D (valor_desconto), desconto +D (valor_desconto)
    # Resultado: Debito = X - valor_desconto + valor_desconto = X (equilibrado)
    print(f"\n--- VERIFICACAO DE EQUILIBRIO (PRE) ---")
    print(f"  Debito pos-correcao: R$ {total_debito - float(valor_desconto) + float(valor_desconto):.2f}")
    print(f"  Credito pos-correcao: R$ {total_credito:.2f}")
    print(f"  A correcao MANTEM o equilibrio (move debito do titulo para desconto)")

    print("\n" + "=" * 70)
    print("CORRECAO NECESSARIA:")
    print(f"  1. Titulo {TITULO_ID}: R$ {valor_titulo_atual:.2f} -> R$ {valor_titulo_novo:.2f} (-R$ {valor_desconto:.2f})")
    print(f"  2. Desconto {DESCONTO_LINE_ID}: R$ 0,00 -> R$ {valor_desconto:.2f} (debito)")
    print("=" * 70)

    return {
        'move_id': MOVE_ID,
        'move_name': m['name'],
        'move_state': m['state'],
        'partner_id': PARTNER_ID,
        'desconto_pct': desconto_pct,
        'titulo_id': TITULO_ID,
        'titulo_valor_atual': valor_titulo_atual,
        'titulo_valor_novo': valor_titulo_novo,
        'desconto_line_id': DESCONTO_LINE_ID,
        'valor_desconto': valor_desconto,
        'total_debito': total_debito,
        'total_credito': total_credito,
        'titulos_2000': titulos_2000,
    }


def corrigir_fatura(conn, dados: dict, dry_run: bool = False) -> bool:
    """Executa a correcao da fatura."""
    move_id = dados['move_id']
    move_state = dados['move_state']

    print("\n" + "=" * 70)
    print(f"CORRECAO DA FATURA {move_id}")
    if dry_run:
        print("*** MODO DRY-RUN - Nenhuma alteracao sera feita ***")
    print("=" * 70)

    # PASSO 1: Despublicar (se estiver posted)
    print(f"\n[1/6] Despublicando fatura...")
    if move_state == 'posted':
        if not dry_run:
            try:
                conn.execute_kw('account.move', 'button_draft', [[move_id]])
                print("     OK: Fatura despublicada")
            except Exception as e:
                if "cannot marshal None" in str(e):
                    print("     OK: Fatura despublicada (ignorando erro de serializacao)")
                else:
                    print(f"     ERRO: {e}")
                    return False
        else:
            print("     [DRY-RUN] Despublicaria fatura")
    elif move_state == 'draft':
        print("     Fatura ja esta em draft, pulando...")
    else:
        print(f"     ATENCAO: Estado inesperado '{move_state}'")
        return False

    # PASSO 2: Configurar linha de desconto
    valor_desconto = float(dados['valor_desconto'])
    print(f"\n[2/6] Configurando linha de desconto ID {dados['desconto_line_id']}...")
    print(f"     -> debit = R$ {valor_desconto:.2f}, credit = R$ 0.00")
    if not dry_run:
        try:
            conn.execute_kw('account.move.line', 'write', [[dados['desconto_line_id']], {
                'debit': valor_desconto,
                'credit': 0
            }])
            print("     OK: Linha de desconto configurada")
        except Exception as e:
            print(f"     ERRO: {e}")
            return False
    else:
        print("     [DRY-RUN] Configuraria desconto")

    # PASSO 3: Ajustar titulo
    valor_titulo_novo = float(dados['titulo_valor_novo'])
    print(f"\n[3/6] Ajustando titulo ID {dados['titulo_id']}...")
    print(f"     -> debit = R$ {valor_titulo_novo:.2f}")
    print(f"     -> amount_residual = R$ {valor_titulo_novo:.2f}")
    if not dry_run:
        try:
            conn.execute_kw('account.move.line', 'write', [[dados['titulo_id']], {
                'debit': valor_titulo_novo,
                'amount_residual': valor_titulo_novo
            }])
            print("     OK: Titulo ajustado")
        except Exception as e:
            print(f"     ERRO: {e}")
            return False
    else:
        print("     [DRY-RUN] Ajustaria titulo")

    # PASSO 4: Zerar titulos ano 2000 (se existirem)
    titulos_2000 = dados.get('titulos_2000', [])
    if titulos_2000:
        print(f"\n[4/6] Zerando {len(titulos_2000)} titulo(s) ano 2000...")
        for t in titulos_2000:
            print(f"     -> ID {t['id']}: R$ {t['debit']:.2f} -> R$ 0.00")
            if not dry_run:
                try:
                    conn.execute_kw('account.move.line', 'write', [[t['id']], {
                        'debit': 0,
                        'credit': 0
                    }])
                    print(f"     OK: Zerado")
                except Exception as e:
                    print(f"     ERRO: {e}")
    else:
        print(f"\n[4/6] Sem titulos ano 2000 para corrigir")

    # PASSO 5: Verificar equilibrio
    print(f"\n[5/6] Verificando equilibrio...")
    if not dry_run:
        lines = conn.search_read('account.move.line', [['move_id', '=', move_id]], ['debit', 'credit'])
        total_debito = sum(l['debit'] for l in lines)
        total_credito = sum(l['credit'] for l in lines)
        diferenca = abs(total_debito - total_credito)

        print(f"     Total Debito: R$ {total_debito:.2f}")
        print(f"     Total Credito: R$ {total_credito:.2f}")
        print(f"     Diferenca: R$ {diferenca:.2f}")

        if diferenca > 0.01:
            print(f"     ERRO: Fatura desbalanceada! Diferenca de R$ {diferenca:.2f}")
            print(f"     NAO republicando. Verifique manualmente.")
            return False

        print(f"     OK: Fatura equilibrada!")
    else:
        # No dry-run, calcular o equilibrio esperado
        print(f"     [DRY-RUN] Debito esperado: R$ {dados['total_debito']:.2f}")
        print(f"     [DRY-RUN] Credito esperado: R$ {dados['total_credito']:.2f}")
        print(f"     [DRY-RUN] A correcao transfere debito entre linhas, equilibrio mantido")

    # PASSO 6: Republicar
    print(f"\n[6/6] Republicando fatura...")
    if not dry_run:
        try:
            conn.execute_kw('account.move', 'action_post', [[move_id]])
            print("     OK: Fatura republicada")
        except Exception as e:
            if "cannot marshal None" in str(e):
                print("     OK: Fatura republicada (ignorando erro de serializacao)")
            else:
                print(f"     ERRO: {e}")
                return False
    else:
        print("     [DRY-RUN] Republicaria fatura")

    # EXTRA: Verificar se Odoo criou novo titulo ano 2000 apos republicacao
    if not dry_run:
        print(f"\n[EXTRA] Verificando se Odoo criou novo titulo ano 2000...")
        novos_2000 = conn.search_read('account.move.line', [
            ['move_id', '=', move_id],
            ['date_maturity', '=', '2000-01-01'],
            ['debit', '>', 0]
        ], ['id', 'debit'])

        if novos_2000:
            print(f"     ATENCAO: Odoo criou {len(novos_2000)} novo(s) titulo(s) ano 2000!")
            print("     -> Executando segunda rodada de correcao...")

            # Despublicar novamente
            try:
                conn.execute_kw('account.move', 'button_draft', [[move_id]])
            except Exception as e:
                if "cannot marshal None" not in str(e):
                    print(f"     ERRO ao despublicar: {e}")
                    return False

            # Recalcular: titulo precisa absorver o valor dos 2000
            valor_extra = sum(t['debit'] for t in novos_2000)
            print(f"     Valor extra nos titulos 2000: R$ {valor_extra:.2f}")

            # Zerar os novos 2000
            for t in novos_2000:
                conn.execute_kw('account.move.line', 'write', [[t['id']], {
                    'debit': 0,
                    'credit': 0
                }])

            # Ajustar titulo: somar o valor que estava nos 2000
            titulo_atual = conn.search_read('account.move.line', [
                ['id', '=', dados['titulo_id']]
            ], ['debit'])
            if titulo_atual:
                novo_debit = titulo_atual[0]['debit'] + valor_extra
                conn.execute_kw('account.move.line', 'write', [[dados['titulo_id']], {
                    'debit': novo_debit,
                    'amount_residual': novo_debit
                }])
                print(f"     Titulo ajustado: R$ {novo_debit:.2f}")

            # Verificar equilibrio novamente
            lines = conn.search_read('account.move.line', [['move_id', '=', move_id]], ['debit', 'credit'])
            total_d = sum(l['debit'] for l in lines)
            total_c = sum(l['credit'] for l in lines)
            if abs(total_d - total_c) > 0.01:
                print(f"     ERRO: Desbalanceado apos segunda correcao! D={total_d:.2f} C={total_c:.2f}")
                return False

            # Republicar
            try:
                conn.execute_kw('account.move', 'action_post', [[move_id]])
            except Exception as e:
                if "cannot marshal None" not in str(e):
                    print(f"     ERRO ao republicar: {e}")
                    return False

            print("     OK: Segunda correcao aplicada e fatura republicada")
        else:
            print("     OK: Nenhum novo titulo ano 2000 criado")

    return True


def verificar_resultado(conn):
    """Verifica o resultado final da correcao."""
    print("\n" + "=" * 70)
    print(f"RESULTADO FINAL - FATURA {MOVE_ID}")
    print("=" * 70)

    # Buscar fatura
    move = conn.search_read('account.move', [['id', '=', MOVE_ID]], [
        'name', 'state', 'amount_total', 'amount_residual', 'payment_state'
    ])
    if move:
        m = move[0]
        print(f"\nFatura: {m['name']}")
        print(f"  Estado: {m['state']}")
        print(f"  Valor Total: R$ {m['amount_total']:.2f}")
        print(f"  Residual: R$ {m['amount_residual']:.2f}")
        print(f"  Payment State: {m['payment_state']}")

    # Buscar titulo
    titulo = conn.search_read('account.move.line', [['id', '=', TITULO_ID]], [
        'debit', 'credit', 'date_maturity', 'amount_residual'
    ])
    if titulo:
        t = titulo[0]
        print(f"\n  Titulo (ID {TITULO_ID}):")
        print(f"    Debito: R$ {t['debit']:.2f}")
        print(f"    Residual: R$ {t['amount_residual']:.2f}")
        print(f"    Vencimento: {t['date_maturity']}")

    # Buscar desconto
    desconto = conn.search_read('account.move.line', [['id', '=', DESCONTO_LINE_ID]], [
        'debit', 'credit', 'account_id'
    ])
    if desconto:
        d = desconto[0]
        print(f"\n  Desconto (ID {DESCONTO_LINE_ID}):")
        print(f"    Debito: R$ {d['debit']:.2f}")
        print(f"    Credito: R$ {d['credit']:.2f}")
        print(f"    Conta: {d['account_id'][1] if d['account_id'] else 'N/A'}")

    # Verificar equilibrio
    lines = conn.search_read('account.move.line', [['move_id', '=', MOVE_ID]], ['debit', 'credit'])
    total_d = sum(l['debit'] for l in lines)
    total_c = sum(l['credit'] for l in lines)
    print(f"\n  Equilibrio: D=R$ {total_d:.2f} | C=R$ {total_c:.2f} | Dif=R$ {abs(total_d - total_c):.2f}")

    # Verificar titulos ano 2000
    titulos_2000 = conn.search_read('account.move.line', [
        ['move_id', '=', MOVE_ID],
        ['date_maturity', '=', '2000-01-01'],
        ['debit', '>', 0]
    ], ['id', 'debit'])

    if titulos_2000:
        print(f"\n  ATENCAO: Existe(m) {len(titulos_2000)} titulo(s) ano 2000!")
        for t in titulos_2000:
            print(f"    ID {t['id']}: R$ {t['debit']:.2f}")
    else:
        print(f"\n  OK: Sem titulos ano 2000")

    sucesso = (move and move[0]['state'] == 'posted' and not titulos_2000
               and desconto and desconto[0]['debit'] > 0)

    if sucesso:
        print("\n" + "=" * 70)
        print("CORRECAO CONCLUIDA COM SUCESSO!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("ATENCAO: Verifique o resultado manualmente!")
        print("=" * 70)

    return sucesso


def main():
    parser = argparse.ArgumentParser(
        description='Corrige desconto concedido zerado na NF 134244 (Odoo ID 253885)'
    )
    parser.add_argument('--dry-run', action='store_true', help='Simular sem fazer alteracoes')
    parser.add_argument('--force', action='store_true', help='Executar sem confirmacao')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("CORRECAO DE DESCONTO CONCEDIDO - NF 134244")
    print(f"Fatura: {MOVE_NAME} (Odoo ID: {MOVE_ID})")
    print(f"Parceiro: REDE ASSAI LJ 25 (ID: {PARTNER_ID})")
    print("=" * 70)

    # Conectar ao Odoo
    print("\nConectando ao Odoo...")
    conn = get_odoo_connection()
    print("OK: Conectado")

    # Analisar fatura
    dados = analisar_fatura(conn)

    if not dados:
        print("\nNenhuma correcao possivel. Verifique os erros acima.")
        return

    # Confirmar execucao
    if not args.force and not args.dry_run:
        print("\n" + "=" * 70)
        print("ATENCAO: Esta operacao ira modificar a fatura no Odoo!")
        print("=" * 70)
        resposta = input("\nDigite 'SIM' para continuar: ")
        if resposta.upper() != 'SIM':
            print("Operacao cancelada.")
            return

    # Executar correcao
    sucesso = corrigir_fatura(conn, dados, dry_run=args.dry_run)

    if sucesso and not args.dry_run:
        verificar_resultado(conn)
    elif args.dry_run:
        print("\n" + "=" * 70)
        print("DRY-RUN CONCLUIDO - Nenhuma alteracao foi feita")
        print("Para executar de verdade: python scripts/corrigir_nf_134244.py --force")
        print("=" * 70)

    print("\nProcesso finalizado!")


if __name__ == '__main__':
    main()
