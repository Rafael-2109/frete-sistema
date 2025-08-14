#!/usr/bin/env python3
"""
Script para identificar valores que causam overflow em campos NUMERIC(15,2)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal

def verificar_overflow_em_dados():
    """Verifica valores que podem causar overflow"""
    
    print("=" * 80)
    print("VERIFICAÇÃO DE VALORES PARA OVERFLOW NUMERIC(15,2)")
    print("Limite máximo: 9.999.999.999.999,99")
    print("=" * 80)
    
    # Limite para NUMERIC(15,2)
    limite = Decimal('9999999999999.99')
    
    # Simular alguns valores que podem estar vindo do Odoo
    valores_teste = [
        114.58,  # Normal
        17100.0,  # Quantidade grande mas OK
        17100.0 * 114.58,  # Valor total calculado
        999999999999999.99,  # Valor no limite (15 dígitos)
        10000000000000.00,  # Valor que causa overflow (14 dígitos)
    ]
    
    print("\nTestando valores:")
    for valor in valores_teste:
        decimal_valor = Decimal(str(valor))
        if abs(decimal_valor) > limite:
            print(f"❌ OVERFLOW: {valor:,.2f} (excede limite)")
        else:
            print(f"✅ OK: {valor:,.2f}")
    
    # Verificar multiplicação de quantidade * preço
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO DE CÁLCULOS QUANTIDADE * PREÇO")
    print("=" * 80)
    
    exemplos = [
        (17100.0, 114.58),  # Do log de erro
        (1000000, 10000),    # 10 bilhões
        (10000000, 1000),    # 10 bilhões
        (100000000, 100),    # 10 bilhões
        (1000000000, 10),    # 10 bilhões
        (10000000000, 1),    # 10 bilhões
    ]
    
    for qtd, preco in exemplos:
        total = Decimal(str(qtd)) * Decimal(str(preco))
        if abs(total) > limite:
            print(f"❌ OVERFLOW: {qtd:,.0f} × {preco:,.2f} = {total:,.2f}")
        else:
            print(f"✅ OK: {qtd:,.0f} × {preco:,.2f} = {total:,.2f}")

if __name__ == "__main__":
    verificar_overflow_em_dados()