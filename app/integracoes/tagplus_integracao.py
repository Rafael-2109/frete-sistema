#!/usr/bin/env python3
"""
Integração TagPlus - Script Direto e Funcional
Baseado na documentação oficial do TagPlus
"""

import requests
import json
import os
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta

class TagPlusIntegration:
    """Cliente OAuth2 para TagPlus - Versão Definitiva"""

    def __init__(self):
        # Configurações do App "Notas" cadastrado no TagPlus
        self.client_id = "8YZNqaklKj3CfIkOtkoV9ILpCllAtalT"
        self.client_secret = "MJHfk8hr3022Y1ETTwqSf0Qsb5Lj6HZe"
        self.redirect_uri = "https://sistema-fretes.onrender.com/tagplus/oauth/callback/nfe"

        # URLs OAuth2 CORRETAS da documentação
        self.authorize_url = "https://developers.tagplus.com.br/authorize"
        self.token_url = "https://api.tagplus.com.br/oauth2/token"
        self.api_base_url = "https://api.tagplus.com.br"

        # Storage de tokens
        self.token_file = "tagplus_tokens.json"
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

        # Carregar tokens salvos
        self.load_tokens()

    def load_tokens(self):
        """Carrega tokens salvos"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    if data.get('expires_at'):
                        self.expires_at = datetime.fromisoformat(data['expires_at'])
                    print("✅ Tokens carregados do arquivo")
                    return True
            except Exception as e:
                print(f"⚠️  Erro ao carregar tokens: {e}")
        return False

    def save_tokens(self):
        """Salva tokens em arquivo"""
        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
        with open(self.token_file, 'w') as f:
            json.dump(data, f, indent=2)
        print("💾 Tokens salvos")

    def step1_get_authorization_code(self):
        """Passo 1: Obter código de autorização"""

        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'scope': 'read:nfes read:clientes read:produtos write:pedidos',
            'state': 'xyz123'
        }

        auth_url = f"{self.authorize_url}?{urlencode(params)}"

        print("\n" + "="*60)
        print("🔴 PASSO 1: AUTORIZAÇÃO")
        print("="*60)
        print("\n1. Abra esta URL no navegador:")
        print(f"\n{auth_url}\n")
        print("2. Faça login no TagPlus com suas credenciais")
        print("3. Autorize o aplicativo")
        print("4. Você será redirecionado para uma URL como:")
        print("   https://sistema-fretes.onrender.com/tagplus/oauth/callback/nfe?code=XXX&state=xyz123")
        print("\n5. Cole a URL COMPLETA aqui:")

        callback_url = input("\n👉 URL de callback: ").strip()

        # Extrair código da URL
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        if 'code' not in params:
            print("❌ Código não encontrado na URL!")
            return None

        code = params['code'][0]
        print(f"\n✅ Código extraído: {code[:20]}...")
        return code

    def step2_exchange_code_for_token(self, code):
        """Passo 2: Trocar código por token"""

        print("\n" + "="*60)
        print("🔴 PASSO 2: OBTER TOKEN")
        print("="*60)

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        print(f"\n📤 Enviando para: {self.token_url}")

        try:
            response = requests.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=30
            )

            print(f"📥 Status: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()

                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                expires_in = token_data.get('expires_in', 86400)  # 24 horas
                self.expires_at = datetime.now() + timedelta(seconds=expires_in)

                self.save_tokens()

                print("\n✅ TOKEN OBTIDO COM SUCESSO!")
                print(f"Access Token: {self.access_token[:30]}...")
                print(f"Refresh Token: {self.refresh_token[:30]}..." if self.refresh_token else "")
                print(f"Expira em: {self.expires_at}")

                return True
            else:
                print(f"\n❌ Erro: {response.status_code}")
                print(f"Resposta: {response.text}")
                return False

        except Exception as e:
            print(f"\n❌ Erro na requisição: {e}")
            return False

    def refresh_token_if_needed(self):
        """Atualiza token se necessário"""

        if not self.refresh_token:
            print("❌ Sem refresh token")
            return False

        # Verifica se precisa renovar (5 min antes de expirar)
        if self.expires_at and datetime.now() < (self.expires_at - timedelta(minutes=5)):
            return True  # Token ainda válido

        print("\n🔄 Renovando token...")

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()

                self.access_token = token_data.get('access_token')
                new_refresh = token_data.get('refresh_token')
                if new_refresh:
                    self.refresh_token = new_refresh

                expires_in = token_data.get('expires_in', 86400)
                self.expires_at = datetime.now() + timedelta(seconds=expires_in)

                self.save_tokens()
                print("✅ Token renovado!")
                return True
            else:
                print(f"❌ Erro ao renovar: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Erro: {e}")
            return False

    def make_api_request(self, method, endpoint, params=None, data=None):
        """Faz requisição para a API"""

        # Garante token válido
        if not self.refresh_token_if_needed():
            print("❌ Token inválido. Execute autorização primeiro.")
            return None

        url = f"{self.api_base_url}{endpoint}"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'X-Api-Version': '2.0'
        }

        if method == 'POST' or method == 'PUT' or method == 'PATCH':
            headers['Content-Type'] = 'application/json'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                print(f"❌ Método {method} não implementado")
                return None

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print("❌ Não autorizado. Token pode ter expirado.")
                return None
            else:
                print(f"❌ Erro {response.status_code}: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
            return None

    def listar_nfes(self, filtros=None):
        """Lista notas fiscais"""

        print("\n" + "="*60)
        print("📋 LISTANDO NOTAS FISCAIS")
        print("="*60)

        params = {
            'page': 1,
            'per_page': 100
        }

        if filtros:
            params.update(filtros)

        todas_nfes = []

        while True:
            print(f"\n📥 Buscando página {params['page']}...")

            result = self.make_api_request('GET', '/nfes', params=params)

            if not result:
                break

            # TagPlus pode retornar dados de diferentes formas
            if isinstance(result, list):
                nfes = result
                tem_mais = len(nfes) == params['per_page']
            elif isinstance(result, dict):
                nfes = result.get('data', result.get('nfes', []))
                tem_mais = result.get('has_more', False)
            else:
                nfes = []
                tem_mais = False

            todas_nfes.extend(nfes)

            print(f"✅ {len(nfes)} NFs encontradas nesta página")

            if not tem_mais or len(nfes) < params['per_page']:
                break

            params['page'] += 1

        print(f"\n✅ TOTAL: {len(todas_nfes)} notas fiscais encontradas")

        return todas_nfes

    def buscar_nfe_detalhada(self, nfe_id):
        """Busca detalhes de uma NF específica"""

        print(f"\n🔍 Buscando detalhes da NF {nfe_id}...")

        result = self.make_api_request('GET', f'/nfes/{nfe_id}')

        if result:
            print("✅ Detalhes obtidos")
        else:
            print("❌ Erro ao buscar detalhes")

        return result

    def testar_api(self):
        """Testa acesso à API"""

        print("\n" + "="*60)
        print("🧪 TESTANDO API")
        print("="*60)

        # Testa endpoint de clientes
        print("\n1️⃣ Testando endpoint /clientes...")
        clientes = self.make_api_request('GET', '/clientes', params={'per_page': 1})
        if clientes:
            print("✅ Endpoint /clientes funcionando")

        # Testa endpoint de produtos
        print("\n2️⃣ Testando endpoint /produtos...")
        produtos = self.make_api_request('GET', '/produtos', params={'per_page': 1})
        if produtos:
            print("✅ Endpoint /produtos funcionando")

        # Testa endpoint de NFs
        print("\n3️⃣ Testando endpoint /nfes...")
        nfes = self.make_api_request('GET', '/nfes', params={'per_page': 1})
        if nfes:
            print("✅ Endpoint /nfes funcionando")

            # Se encontrou NF, busca detalhes
            if isinstance(nfes, list) and len(nfes) > 0:
                nfe_id = nfes[0].get('id')
                if nfe_id:
                    print(f"\n4️⃣ Testando busca detalhada de NF {nfe_id}...")
                    detalhes = self.buscar_nfe_detalhada(nfe_id)
                    if detalhes:
                        print("✅ Busca detalhada funcionando")

        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO")
        print("="*60)


def main():
    """Função principal"""

    print("\n" + "="*60)
    print("🚀 INTEGRAÇÃO TAGPLUS - IMPORTADOR DE NOTAS FISCAIS")
    print("="*60)

    client = TagPlusIntegration()

    # Verifica se já tem token válido
    if client.access_token and client.refresh_token_if_needed():
        print("\n✅ Token válido encontrado!")
        opcao = input("\nDeseja: [T]estar API, [L]istar NFs, ou [N]ova autorização? ").upper()

        if opcao == 'N':
            # Nova autorização
            code = client.step1_get_authorization_code()
            if code:
                client.step2_exchange_code_for_token(code)
        elif opcao == 'L':
            # Listar NFs
            nfes = client.listar_nfes()
            if nfes and len(nfes) > 0:
                print("\n📄 Primeiras 3 NFs:")
                for i, nfe in enumerate(nfes[:3]):
                    print(f"\n{i+1}. NF {nfe.get('numero', 'N/A')}")
                    print(f"   Cliente: {nfe.get('cliente', {}).get('nome', 'N/A')}")
                    print(f"   Data: {nfe.get('data_emissao', 'N/A')}")
                    print(f"   Valor: R$ {nfe.get('valor_total', 0):.2f}")
        else:
            # Testar API
            client.testar_api()
    else:
        print("\n⚠️  Sem token válido. Iniciando processo de autorização...")

        # Passo 1: Obter código
        code = client.step1_get_authorization_code()

        if code:
            # Passo 2: Trocar por token
            if client.step2_exchange_code_for_token(code):
                # Passo 3: Testar API
                print("\n🎯 Agora vamos testar a API...")
                client.testar_api()

                # Passo 4: Listar algumas NFs
                print("\n📋 Listando algumas notas fiscais...")
                nfes = client.listar_nfes({'per_page': 5})

                if nfes:
                    for i, nfe in enumerate(nfes[:5]):
                        print(f"\n{i+1}. NF {nfe.get('numero', 'N/A')}")
                        print(f"   Cliente: {nfe.get('cliente', {}).get('nome', 'N/A')}")
                        print(f"   Data: {nfe.get('data_emissao', 'N/A')}")


if __name__ == "__main__":
    main()