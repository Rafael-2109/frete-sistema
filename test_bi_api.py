#!/usr/bin/env python3
"""
Script para testar as APIs do BI e validar retorno de dados reais
"""
import requests
import json
from datetime import datetime

# Configuração - ajuste conforme necessário
BASE_URL = "http://localhost:5000"
USERNAME = "admin"  # Substitua com credenciais válidas
PASSWORD = "admin"   # Substitua com credenciais válidas

def fazer_login(session):
    """Faz login no sistema"""
    login_url = f"{BASE_URL}/auth/login"
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }

    # Faz o GET primeiro para pegar o CSRF token (se necessário)
    response = session.get(login_url)

    # Faz o POST de login
    response = session.post(login_url, data=login_data, allow_redirects=False)

    if response.status_code in [302, 200]:
        print("✅ Login realizado com sucesso")
        return True
    else:
        print("❌ Falha no login")
        return False

def testar_api(session, endpoint, nome):
    """Testa um endpoint da API"""
    url = f"{BASE_URL}/bi/api/{endpoint}"

    try:
        response = session.get(url)

        # Debug: mostra o que retornou
        if response.status_code != 200:
            print(f"❌ {nome}: Erro HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

        # Verifica se é JSON
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            print(f"❌ {nome}: Resposta não é JSON (tipo: {content_type})")
            print(f"   Response: {response.text[:200]}")
            return False

        data = response.json()

        # Verifica se há dados
        if data and (isinstance(data, list) and len(data) > 0 or isinstance(data, dict) and data):
            print(f"✅ {nome}: OK - {len(data) if isinstance(data, list) else 'dados'} registros")

            # Mostra amostra dos dados
            if isinstance(data, list):
                print(f"   Amostra: {json.dumps(data[0] if data else {}, indent=2)[:200]}...")
            else:
                print(f"   Amostra: {json.dumps(data, indent=2)[:200]}...")

            return True
        else:
            print(f"⚠️ {nome}: Sem dados")
            return False

    except Exception as e:
        print(f"❌ {nome}: Erro - {str(e)}")
        return False

def main():
    """Função principal"""
    print("=" * 60)
    print("TESTE DAS APIs DO MÓDULO BI")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"URL Base: {BASE_URL}")
    print()

    # Cria sessão para manter cookies
    session = requests.Session()

    # Faz login
    if not fazer_login(session):
        print("Não foi possível fazer login. Verifique as credenciais.")
        return

    print()
    print("TESTANDO ENDPOINTS DO BI:")
    print("-" * 40)

    # Lista de endpoints para testar
    endpoints = [
        ("indicadores-principais", "Indicadores Principais"),
        ("evolucao-mensal", "Evolução Mensal"),
        ("ranking-transportadoras", "Ranking Transportadoras"),
        ("analise-regional", "Análise Regional"),
        ("despesas-por-tipo", "Despesas por Tipo"),
        ("custo-por-kg-uf", "Custo por KG/UF"),
        ("status-etl", "Status ETL")
    ]

    total = len(endpoints)
    sucesso = 0

    for endpoint, nome in endpoints:
        if testar_api(session, endpoint, nome):
            sucesso += 1

    print()
    print("=" * 60)
    print(f"RESULTADO: {sucesso}/{total} endpoints funcionando")

    if sucesso == total:
        print("✅ TODOS OS ENDPOINTS ESTÃO RETORNANDO DADOS!")
    elif sucesso > 0:
        print("⚠️ ALGUNS ENDPOINTS PRECISAM DE VERIFICAÇÃO")
    else:
        print("❌ NENHUM ENDPOINT ESTÁ FUNCIONANDO")

    print("=" * 60)

if __name__ == "__main__":
    main()