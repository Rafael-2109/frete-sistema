"""
Script para corrigir o bug de desconto duplo nos títulos a receber existentes.
=============================================================================

PROBLEMA:
O Odoo aplica o desconto comercial 2 vezes: VALOR * (1-desc) * (1-desc)
Isso resultava em:
- valor_original = saldo_total (valor com desconto 1x - incorretamente usado como original)
- valor_titulo = valor_original - desconto (valor com desconto 2x - errado!)

CORREÇÃO:
- valor_titulo = saldo antigo (que era o valor com desconto 1x - CORRETO para valor a pagar)
- valor_original = valor_titulo / (1 - desconto_percentual) (valor sem desconto)
- desconto = valor_original - valor_titulo (recalculado)

Data: 2025-12-15
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.financeiro.models import ContasAReceber
from sqlalchemy import text
from decimal import Decimal


def corrigir_desconto_duplo(dry_run: bool = True):
    """
    Corrige os valores de títulos que foram importados com desconto duplicado.

    O problema era:
    - valor_original = saldo_total (que já era o valor com desconto aplicado 1x)
    - valor_titulo = valor_original - desconto (aplicando desconto novamente = 2x)

    A correção:
    - valor_titulo ATUAL (errado, com desconto 2x) + desconto = valor com desconto 1x
    - valor_titulo NOVO = valor_atual + desconto (valor correto a pagar)
    - valor_original NOVO = valor_titulo_novo / (1 - desconto_pct)
    - desconto NOVO = valor_original_novo - valor_titulo_novo

    Args:
        dry_run: Se True, apenas mostra o que seria alterado sem salvar
    """
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("CORREÇÃO DE DESCONTO DUPLO EM TÍTULOS A RECEBER")
        print("=" * 70)

        if dry_run:
            print("🔍 MODO DRY-RUN: Nenhuma alteração será salva")
        else:
            print("⚠️  MODO EXECUÇÃO: As alterações serão salvas no banco!")

        print()

        # Buscar títulos com desconto_percentual > 0
        titulos = ContasAReceber.query.filter(
            ContasAReceber.desconto_percentual > 0,
            ContasAReceber.parcela_paga == False
        ).all()

        print(f"📊 Encontrados {len(titulos)} títulos com desconto comercial para verificar")
        print()

        corrigidos = 0
        erros = 0

        for titulo in titulos:
            try:
                # Valores atuais (potencialmente errados)
                valor_titulo_atual = float(titulo.valor_titulo or 0)
                valor_original_atual = float(titulo.valor_original or 0)
                desconto_atual = float(titulo.desconto or 0)
                desconto_pct = float(titulo.desconto_percentual or 0)

                if desconto_pct <= 0 or desconto_pct >= 1:
                    continue

                # O valor_original_atual é na verdade o valor com desconto 1x (correto para valor_titulo)
                # O valor_titulo_atual tem desconto aplicado 2x (ERRADO)

                # Valores corretos:
                # valor_titulo CORRETO = valor_original_atual (que é o saldo_total do Odoo = desconto 1x)
                valor_titulo_novo = valor_original_atual

                # valor_original CORRETO = valor_titulo / (1 - desconto_pct)
                valor_original_novo = valor_titulo_novo / (1 - desconto_pct)

                # desconto CORRETO = valor_original - valor_titulo
                desconto_novo = valor_original_novo - valor_titulo_novo

                # Verificar se há diferença significativa (mais de R$ 0.01)
                diff_titulo = abs(valor_titulo_novo - valor_titulo_atual)
                diff_original = abs(valor_original_novo - valor_original_atual)

                if diff_titulo < 0.01 and diff_original < 0.01:
                    # Já está correto ou diferença insignificante
                    continue

                print(f"NF {titulo.titulo_nf} - P{titulo.parcela} ({titulo.raz_social_red or titulo.raz_social[:30]}...)")
                print(f"  Desconto: {desconto_pct * 100:.1f}%")
                print(f"  ANTES:")
                print(f"    valor_original: R$ {valor_original_atual:,.2f}")
                print(f"    desconto:       R$ {desconto_atual:,.2f}")
                print(f"    valor_titulo:   R$ {valor_titulo_atual:,.2f}")
                print(f"  DEPOIS:")
                print(f"    valor_original: R$ {valor_original_novo:,.2f} (diferença: +R$ {valor_original_novo - valor_original_atual:,.2f})")
                print(f"    desconto:       R$ {desconto_novo:,.2f} (diferença: +R$ {desconto_novo - desconto_atual:,.2f})")
                print(f"    valor_titulo:   R$ {valor_titulo_novo:,.2f} (diferença: +R$ {valor_titulo_novo - valor_titulo_atual:,.2f})")
                print()

                if not dry_run:
                    titulo.valor_original = valor_original_novo
                    titulo.desconto = desconto_novo
                    titulo.valor_titulo = valor_titulo_novo

                corrigidos += 1

            except Exception as e:
                print(f"❌ Erro no título {titulo.titulo_nf}-{titulo.parcela}: {e}")
                erros += 1
                continue

        if not dry_run and corrigidos > 0:
            db.session.commit()
            print(f"✅ Commit realizado!")

        print()
        print("=" * 70)
        print("RESUMO")
        print("=" * 70)
        print(f"📊 Títulos analisados: {len(titulos)}")
        print(f"✅ Títulos corrigidos: {corrigidos}")
        print(f"❌ Erros: {erros}")

        if dry_run and corrigidos > 0:
            print()
            print("⚠️  Execute novamente com --execute para aplicar as correções")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Corrigir bug de desconto duplo em títulos a receber')
    parser.add_argument('--execute', action='store_true', help='Executar correções (sem este flag, apenas mostra o que seria alterado)')

    args = parser.parse_args()

    corrigir_desconto_duplo(dry_run=not args.execute)
