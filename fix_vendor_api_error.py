#!/usr/bin/env python3
"""
Corrige o erro na API de vendedores disponíveis
"""
import os

print("=== CORRIGINDO ERRO NA API DE VENDEDORES ===\n")

# O erro é na linha 1196 do api.py que tenta acessar cnpj_cpf que não existe
fix_code = """
        return jsonify([{
            'id': v.id,
            'codigo': v.codigo,
            'nome': v.nome
            # 'cnpj_cpf': v.cnpj_cpf  # Campo não existe no modelo
        } for v in vendors])
"""

print("Problema identificado:")
print("- API /api/v1/permissions/vendors/available tenta acessar campo 'cnpj_cpf'")
print("- Esse campo não existe no modelo Vendedor")
print("\nSolução: Remover o campo da resposta JSON")

print("\nCódigo corrigido:")
print(fix_code)

print("\nArquivo a corrigir: app/permissions/api.py, linha ~1196")