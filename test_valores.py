#!/usr/bin/env python
"""Teste simples para verificar valores de cálculo"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simulação dos dados
peso_real = 1000
valor_mercadoria = 50000

# Dados da tabela (valores de exemplo)
tabela_dados = {
    'valor_kg': 0.50,
    'percentual_valor': 1.0,
    'percentual_gris': 0.20,
    'gris_minimo': 50,
    'percentual_adv': 0.10,
    'adv_minimo': 25,
    'percentual_rca': 0.05,
    'pedagio_por_100kg': 15,
    'frete_minimo_peso': 100,
    'frete_minimo_valor': 175,
    'valor_tas': 10,
    'valor_despacho': 20,
    'valor_cte': 5
}

print("=" * 60)
print("TESTE DE CÁLCULO DE FRETE")
print("=" * 60)
print()

# 1. Peso para cálculo
peso_minimo = tabela_dados.get('frete_minimo_peso', 0)
peso_considerado = max(peso_real, peso_minimo)
print(f"1. PESO CONSIDERADO:")
print(f"   Peso real: {peso_real} kg")
print(f"   Peso mínimo: {peso_minimo} kg")
print(f"   → Peso usado: {peso_considerado} kg")
print()

# 2. Frete base
frete_peso = peso_considerado * tabela_dados.get('valor_kg', 0)
frete_valor = valor_mercadoria * (tabela_dados.get('percentual_valor', 0) / 100)
frete_base = frete_peso + frete_valor
print(f"2. FRETE BASE:")
print(f"   Frete Peso: {peso_considerado} × {tabela_dados.get('valor_kg', 0)} = R$ {frete_peso:.2f}")
print(f"   Frete Valor: {valor_mercadoria} × {tabela_dados.get('percentual_valor', 0)}% = R$ {frete_valor:.2f}")
print(f"   → Base Total: R$ {frete_base:.2f}")
print()

# 3. GRIS
gris_calculado = valor_mercadoria * (tabela_dados.get('percentual_gris', 0) / 100)
gris_minimo = tabela_dados.get('gris_minimo', 0)
gris_final = max(gris_calculado, gris_minimo)
print(f"3. GRIS:")
print(f"   Calculado: {valor_mercadoria} × {tabela_dados.get('percentual_gris', 0)}% = R$ {gris_calculado:.2f}")
print(f"   Mínimo: R$ {gris_minimo:.2f}")
print(f"   → GRIS Final: R$ {gris_final:.2f}")
print()

# 4. ADV
adv_calculado = valor_mercadoria * (tabela_dados.get('percentual_adv', 0) / 100)
adv_minimo = tabela_dados.get('adv_minimo', 0)
adv_final = max(adv_calculado, adv_minimo)
print(f"4. ADV:")
print(f"   Calculado: {valor_mercadoria} × {tabela_dados.get('percentual_adv', 0)}% = R$ {adv_calculado:.2f}")
print(f"   Mínimo: R$ {adv_minimo:.2f}")
print(f"   → ADV Final: R$ {adv_final:.2f}")
print()

# 5. RCA
rca_final = valor_mercadoria * (tabela_dados.get('percentual_rca', 0) / 100)
print(f"5. RCA:")
print(f"   Calculado: {valor_mercadoria} × {tabela_dados.get('percentual_rca', 0)}% = R$ {rca_final:.2f}")
print()

# 6. Pedágio
fracoes_100kg = int((peso_considerado - 1) // 100) + 1
pedagio_final = fracoes_100kg * tabela_dados.get('pedagio_por_100kg', 0)
print(f"6. PEDÁGIO:")
print(f"   Peso: {peso_considerado} kg = {fracoes_100kg} frações de 100kg")
print(f"   Cálculo: {fracoes_100kg} × R$ {tabela_dados.get('pedagio_por_100kg', 0):.2f} = R$ {pedagio_final:.2f}")
print()

# 7. Valores fixos
tas = tabela_dados.get('valor_tas', 0)
despacho = tabela_dados.get('valor_despacho', 0)
cte = tabela_dados.get('valor_cte', 0)
print(f"7. VALORES FIXOS:")
print(f"   TAS: R$ {tas:.2f}")
print(f"   Despacho: R$ {despacho:.2f}")
print(f"   CT-e: R$ {cte:.2f}")
print()

# 8. Componentes antes do mínimo (todos aplicados antes)
componentes_antes = gris_final + adv_final + rca_final + pedagio_final + tas + despacho + cte
print(f"8. COMPONENTES ANTES DO MÍNIMO:")
print(f"   GRIS: R$ {gris_final:.2f}")
print(f"   ADV: R$ {adv_final:.2f}")
print(f"   RCA: R$ {rca_final:.2f}")
print(f"   Pedágio: R$ {pedagio_final:.2f}")
print(f"   TAS: R$ {tas:.2f}")
print(f"   Despacho: R$ {despacho:.2f}")
print(f"   CT-e: R$ {cte:.2f}")
print(f"   → Total Componentes: R$ {componentes_antes:.2f}")
print()

# 9. Subtotal antes do mínimo
subtotal_antes_minimo = frete_base + componentes_antes
print(f"9. SUBTOTAL ANTES DO MÍNIMO:")
print(f"   Base: R$ {frete_base:.2f}")
print(f"   + Componentes: R$ {componentes_antes:.2f}")
print(f"   → Subtotal: R$ {subtotal_antes_minimo:.2f}")
print()

# 10. Aplicação do frete mínimo
frete_minimo_valor = tabela_dados.get('frete_minimo_valor', 0)
frete_apos_minimo = max(subtotal_antes_minimo, frete_minimo_valor)
ajuste_minimo = frete_apos_minimo - subtotal_antes_minimo
print(f"10. APLICAÇÃO DO FRETE MÍNIMO:")
print(f"    Subtotal: R$ {subtotal_antes_minimo:.2f}")
print(f"    Mínimo: R$ {frete_minimo_valor:.2f}")
print(f"    → Valor após mínimo: R$ {frete_apos_minimo:.2f}")
print(f"    Ajuste aplicado: R$ {ajuste_minimo:.2f}")
print()

# 11. Total líquido (sem ICMS)
total_liquido = frete_apos_minimo  # Sem componentes pós-mínimo
print(f"11. TOTAL LÍQUIDO (sem ICMS):")
print(f"    → R$ {total_liquido:.2f}")
print()

print("=" * 60)
print("RESUMO FINAL:")
print(f"  Frete Base: R$ {frete_base:.2f}")
print(f"  GRIS: R$ {gris_final:.2f}")
print(f"  ADV: R$ {adv_final:.2f}")
print(f"  RCA: R$ {rca_final:.2f}")
print(f"  Pedágio: R$ {pedagio_final:.2f}")
print(f"  Fixos: R$ {tas + despacho + cte:.2f}")
print(f"  Subtotal antes mínimo: R$ {subtotal_antes_minimo:.2f}")
print(f"  TOTAL LÍQUIDO: R$ {total_liquido:.2f}")
print("=" * 60)