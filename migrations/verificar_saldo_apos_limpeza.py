"""
Script de Verificação Pós-Limpeza

Objetivo:
- Verificar se não há mais duplicatas
- Confirmar que o saldo está correto
- Validar que o extrato está consistente
- Comparar com valores esperados do Excel

USO:
    python migrations/verificar_saldo_apos_limpeza.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text
from decimal import Decimal

# VALORES ESPERADOS DO EXCEL (conforme informado pelo usuário)
VALOR_ESPERADO_MONTAGENS = Decimal('127560.58')
VALOR_ESPERADO_COMISSOES = Decimal('1181982.56')  # Baseado no relatório anterior
QTD_ESPERADA_MONTAGENS = 1779

def main():
    app = create_app()

    with app.app_context():
        print("\n" + "=" * 120)
        print("✅ VERIFICAÇÃO PÓS-LIMPEZA - VALIDAÇÃO COMPLETA")
        print("=" * 120)

        erros = []
        avisos = []

        # 1. VERIFICAR DUPLICATAS DE MOVIMENTAÇÕES DE MONTAGEM
        print("\n1️⃣  VERIFICANDO DUPLICATAS DE MOVIMENTAÇÕES DE MONTAGEM...")
        print("=" * 120)

        duplicatas_mov = db.session.execute(text("""
            SELECT COUNT(*)
            FROM (
                SELECT pedido_id, UPPER(numero_chassi) as chassi_upper
                FROM movimentacao_financeira
                WHERE categoria = 'Montagem'
                  AND tipo = 'PAGAMENTO'
                  AND empresa_origem_id = (SELECT id FROM empresa_venda_moto WHERE empresa = 'SOGIMA')
                GROUP BY pedido_id, UPPER(numero_chassi)
                HAVING COUNT(*) > 1
            ) duplicatas
        """)).scalar()

        if duplicatas_mov > 0:
            erros.append(f"❌ ERRO: Ainda existem {duplicatas_mov} grupos com movimentações duplicadas!")
            print(f"   ❌ ERRO: {duplicatas_mov} grupos com duplicatas encontrados")
        else:
            print("   ✅ Nenhuma duplicata de movimentação encontrada")

        # 2. VERIFICAR QUANTIDADE E VALOR TOTAL DE MONTAGENS
        print("\n2️⃣  VERIFICANDO MONTAGENS...")
        print("=" * 120)

        totais_montagem = db.session.execute(text("""
            SELECT
                COUNT(*) as qtd,
                SUM(valor) as total
            FROM movimentacao_financeira
            WHERE categoria = 'Montagem'
              AND tipo = 'PAGAMENTO'
              AND empresa_origem_id = (SELECT id FROM empresa_venda_moto WHERE empresa = 'SOGIMA')
        """)).fetchone()

        qtd_mov_montagem = totais_montagem[0]
        valor_mov_montagem = Decimal(str(totais_montagem[1] or 0))

        print(f"   Quantidade esperada:     {QTD_ESPERADA_MONTAGENS}")
        print(f"   Quantidade no banco:     {qtd_mov_montagem}")
        print(f"   Valor esperado:          R$ {float(VALOR_ESPERADO_MONTAGENS):,.2f}")
        print(f"   Valor no banco:          R$ {float(valor_mov_montagem):,.2f}")

        diferenca_qtd = qtd_mov_montagem - QTD_ESPERADA_MONTAGENS
        diferenca_valor = valor_mov_montagem - VALOR_ESPERADO_MONTAGENS

        if diferenca_qtd != 0:
            erros.append(f"❌ ERRO: Diferença de {diferenca_qtd} movimentações de montagem")
            print(f"   ❌ DIFERENÇA: {diferenca_qtd} movimentações")
        else:
            print(f"   ✅ Quantidade correta")

        if abs(diferenca_valor) > Decimal('0.10'):  # Tolerância de 10 centavos
            erros.append(f"❌ ERRO: Diferença de R$ {float(diferenca_valor):,.2f} no valor de montagens")
            print(f"   ❌ DIFERENÇA: R$ {float(diferenca_valor):,.2f}")
        else:
            print(f"   ✅ Valor correto")

        # 3. VERIFICAR COMISSÕES
        print("\n3️⃣  VERIFICANDO COMISSÕES...")
        print("=" * 120)

        # Soma das comissões individuais (não dos lotes)
        totais_comissao = db.session.execute(text("""
            SELECT
                COUNT(*) as qtd,
                SUM(valor) as total
            FROM movimentacao_financeira
            WHERE categoria = 'Comissão'
              AND tipo = 'PAGAMENTO'
              AND empresa_origem_id = (SELECT id FROM empresa_venda_moto WHERE empresa = 'SOGIMA')
        """)).fetchone()

        qtd_comissoes = totais_comissao[0]
        valor_comissoes = Decimal(str(totais_comissao[1] or 0))

        print(f"   Quantidade de comissões individuais: {qtd_comissoes}")
        print(f"   Valor total comissões:               R$ {float(valor_comissoes):,.2f}")
        print(f"   Valor esperado (Excel):              R$ {float(VALOR_ESPERADO_COMISSOES):,.2f}")

        diferenca_comissoes = valor_comissoes - VALOR_ESPERADO_COMISSOES

        if abs(diferenca_comissoes) > Decimal('0.10'):
            avisos.append(f"⚠️  AVISO: Diferença de R$ {float(diferenca_comissoes):,.2f} em comissões")
            print(f"   ⚠️  DIFERENÇA: R$ {float(diferenca_comissoes):,.2f}")
        else:
            print(f"   ✅ Valor correto")

        # 4. VERIFICAR SALDO DA SOGIMA
        print("\n4️⃣  VERIFICANDO SALDO DA SOGIMA...")
        print("=" * 120)

        sogima = db.session.execute(text("""
            SELECT saldo FROM empresa_venda_moto WHERE empresa = 'SOGIMA'
        """)).fetchone()

        saldo_atual = Decimal(str(sogima[0]))
        saldo_esperado = -(VALOR_ESPERADO_MONTAGENS + VALOR_ESPERADO_COMISSOES)

        print(f"   Saldo esperado (Excel):    R$ {float(saldo_esperado):,.2f}")
        print(f"   Saldo no banco:            R$ {float(saldo_atual):,.2f}")

        diferenca_saldo = saldo_atual - saldo_esperado

        if abs(diferenca_saldo) > Decimal('1.00'):  # Tolerância de R$ 1,00
            erros.append(f"❌ ERRO: Diferença de R$ {float(diferenca_saldo):,.2f} no saldo")
            print(f"   ❌ DIFERENÇA: R$ {float(diferenca_saldo):,.2f}")
        else:
            print(f"   ✅ Saldo correto (diferença: R$ {float(diferenca_saldo):,.2f})")

        # 5. VERIFICAR CONSISTÊNCIA DO EXTRATO
        print("\n5️⃣  VERIFICANDO CONSISTÊNCIA DO EXTRATO...")
        print("=" * 120)

        totais_extrato = db.session.execute(text("""
            SELECT
                tipo,
                COUNT(*) as qtd,
                SUM(valor) as total
            FROM movimentacao_financeira
            WHERE empresa_origem_id = (SELECT id FROM empresa_venda_moto WHERE empresa = 'SOGIMA')
               OR empresa_destino_id = (SELECT id FROM empresa_venda_moto WHERE empresa = 'SOGIMA')
            GROUP BY tipo
        """)).fetchall()

        total_recebimentos = Decimal('0')
        total_pagamentos = Decimal('0')

        for row in totais_extrato:
            valor = Decimal(str(row[2]))
            print(f"   {row[0]:15} | Qtd: {row[1]:6} | Total: R$ {float(valor):15,.2f}")

            if row[0] == 'RECEBIMENTO':
                total_recebimentos += valor
            elif row[0] == 'PAGAMENTO':
                total_pagamentos += valor

        saldo_calculado = total_recebimentos - total_pagamentos

        print(f"\n   📊 Saldo calculado (Recebimentos - Pagamentos): R$ {float(saldo_calculado):,.2f}")
        print(f"   📊 Saldo registrado no banco:                   R$ {float(saldo_atual):,.2f}")

        diferenca_calc = saldo_atual - saldo_calculado

        if abs(diferenca_calc) > Decimal('0.10'):
            erros.append(f"❌ ERRO: Saldo não bate com movimentações (diferença: R$ {float(diferenca_calc):,.2f})")
            print(f"   ❌ INCONSISTÊNCIA: R$ {float(diferenca_calc):,.2f}")
        else:
            print(f"   ✅ Saldo consistente com movimentações")

        # RESUMO FINAL
        print("\n" + "=" * 120)
        print("📊 RESUMO DA VERIFICAÇÃO")
        print("=" * 120)

        if erros:
            print("\n❌ ERROS ENCONTRADOS:")
            for erro in erros:
                print(f"   {erro}")

        if avisos:
            print("\n⚠️  AVISOS:")
            for aviso in avisos:
                print(f"   {aviso}")

        if not erros and not avisos:
            print("\n✅✅✅ TUDO CORRETO! SISTEMA VALIDADO! ✅✅✅")
            print("\n   O saldo e o extrato estão consistentes com os valores do Excel.")
            print("   Não há duplicatas ou inconsistências.")
        elif not erros:
            print("\n✅ VALIDAÇÃO OK (com avisos)")
        else:
            print("\n❌ VALIDAÇÃO FALHOU - Corrija os erros acima")

        print("\n" + "=" * 120)


if __name__ == '__main__':
    main()
