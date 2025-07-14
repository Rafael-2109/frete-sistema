#!/usr/bin/env python3
"""
Script de teste para API Odoo
"""

import requests
import json
from datetime import datetime
from app.api.odoo.auth import create_test_token

# Configurações
BASE_URL = "http://localhost:5000"
API_KEY = "odoo-integration-key-2024"

def test_authentication():
    """Testa autenticação com API Key e JWT"""
    print("🔐 Testando autenticação...")
    
    # Gerar token de teste
    token = create_test_token()
    print(f"Token gerado: {token}")
    
    headers = {
        'X-API-Key': API_KEY,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Testar rota de conectividade
    response = requests.get(f"{BASE_URL}/api/v1/odoo/test", headers=headers)
    
    if response.status_code == 200:
        print("✅ Autenticação funcionando!")
        print(f"Resposta: {response.json()}")
        return True
    else:
        print(f"❌ Erro na autenticação: {response.status_code}")
        print(f"Resposta: {response.text}")
        return False

def test_carteira_bulk_update():
    """Testa atualização em lote da carteira"""
    print("\n📋 Testando bulk update da carteira...")
    
    token = create_test_token()
    headers = {
        'X-API-Key': API_KEY,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Dados de teste
    test_data = {
        "items": [
            {
                "num_pedido": "TEST001",
                "cod_produto": "PROD001",
                "nome_produto": "Produto Teste 1",
                "qtd_produto_pedido": 100.0,
                "qtd_saldo_produto_pedido": 80.0,
                "cnpj_cpf": "12345678901234",
                "preco_produto_pedido": 10.50,
                "raz_social": "Cliente Teste LTDA",
                "municipio": "São Paulo",
                "estado": "SP",
                "vendedor": "Vendedor Teste"
            },
            {
                "num_pedido": "TEST002",
                "cod_produto": "PROD002",
                "nome_produto": "Produto Teste 2",
                "qtd_produto_pedido": 50.0,
                "qtd_saldo_produto_pedido": 30.0,
                "cnpj_cpf": "12345678901234",
                "preco_produto_pedido": 25.75,
                "raz_social": "Cliente Teste LTDA",
                "municipio": "Rio de Janeiro",
                "estado": "RJ",
                "vendedor": "Vendedor Teste 2"
            }
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/odoo/carteira/bulk-update",
        headers=headers,
        json=test_data
    )
    
    if response.status_code == 200:
        print("✅ Bulk update da carteira funcionando!")
        result = response.json()
        print(f"Processados: {result.get('processed', 0)}")
        print(f"Criados: {result.get('created', 0)}")
        print(f"Atualizados: {result.get('updated', 0)}")
        print(f"Erros: {len(result.get('errors', []))}")
        return True
    else:
        print(f"❌ Erro no bulk update da carteira: {response.status_code}")
        print(f"Resposta: {response.text}")
        return False

def test_faturamento_bulk_update():
    """Testa atualização em lote do faturamento"""
    print("\n💰 Testando bulk update do faturamento...")
    
    token = create_test_token()
    headers = {
        'X-API-Key': API_KEY,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Dados de teste - faturamento consolidado
    test_data = {
        "tipo": "consolidado",
        "items": [
            {
                "numero_nf": "NF001",
                "data_fatura": "2024-01-15",
                "cnpj_cliente": "12345678901234",
                "nome_cliente": "Cliente Teste LTDA",
                "valor_total": 1500.75,
                "origem": "TEST001",
                "peso_bruto": 100.5,
                "municipio": "São Paulo",
                "estado": "SP",
                "vendedor": "Vendedor Teste"
            },
            {
                "numero_nf": "NF002",
                "data_fatura": "2024-01-16",
                "cnpj_cliente": "12345678901234",
                "nome_cliente": "Cliente Teste LTDA",
                "valor_total": 850.25,
                "origem": "TEST002",
                "peso_bruto": 75.0,
                "municipio": "Rio de Janeiro",
                "estado": "RJ",
                "vendedor": "Vendedor Teste 2"
            }
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/odoo/faturamento/bulk-update",
        headers=headers,
        json=test_data
    )
    
    if response.status_code == 200:
        print("✅ Bulk update do faturamento funcionando!")
        result = response.json()
        print(f"Processados: {result.get('processed', 0)}")
        print(f"Criados: {result.get('created', 0)}")
        print(f"Atualizados: {result.get('updated', 0)}")
        print(f"Erros: {len(result.get('errors', []))}")
        return True
    else:
        print(f"❌ Erro no bulk update do faturamento: {response.status_code}")
        print(f"Resposta: {response.text}")
        return False

def test_validation_errors():
    """Testa validação de erros"""
    print("\n🚨 Testando validação de erros...")
    
    token = create_test_token()
    headers = {
        'X-API-Key': API_KEY,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Dados inválidos (faltando campos obrigatórios)
    test_data = {
        "items": [
            {
                "num_pedido": "TEST001",
                # faltando cod_produto
                "nome_produto": "Produto Teste 1",
                "qtd_produto_pedido": -100.0,  # valor negativo
                "qtd_saldo_produto_pedido": 80.0,
                "cnpj_cpf": "123",  # CNPJ inválido
                "preco_produto_pedido": 10.50
            }
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/odoo/carteira/bulk-update",
        headers=headers,
        json=test_data
    )
    
    if response.status_code == 400:
        print("✅ Validação de erros funcionando!")
        result = response.json()
        print(f"Erros detectados: {len(result.get('errors', []))}")
        for error in result.get('errors', []):
            print(f"  - {error}")
        return True
    else:
        print(f"❌ Validação de erros não funcionou: {response.status_code}")
        print(f"Resposta: {response.text}")
        return False

def test_authentication_failure():
    """Testa falha na autenticação"""
    print("\n🔒 Testando falha na autenticação...")
    
    # Headers sem API Key
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f"{BASE_URL}/api/v1/odoo/test", headers=headers)
    
    if response.status_code == 401:
        print("✅ Falha na autenticação funcionando!")
        return True
    else:
        print(f"❌ Falha na autenticação não funcionou: {response.status_code}")
        print(f"Resposta: {response.text}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 INICIANDO TESTES DA API ODOO")
    print("=" * 50)
    
    tests = [
        ("Autenticação", test_authentication),
        ("Bulk Update Carteira", test_carteira_bulk_update),
        ("Bulk Update Faturamento", test_faturamento_bulk_update),
        ("Validação de Erros", test_validation_errors),
        ("Falha na Autenticação", test_authentication_failure)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Erro no teste {test_name}: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RESUMO DOS TESTES")
    print(f"✅ Passou: {passed}")
    print(f"❌ Falhou: {failed}")
    print(f"📈 Taxa de sucesso: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print(f"\n⚠️ {failed} teste(s) falharam. Verifique os logs acima.")

if __name__ == "__main__":
    main() 