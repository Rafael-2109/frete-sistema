#!/usr/bin/env python3
"""
Script de Teste Simples - Extrai 1 cliente e 1 NF do TagPlus
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from app import create_app, db
from app.integracoes.tagplus.oauth2_v2 import TagPlusOAuth2V2
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2
from app.carteira.models import CadastroCliente
from app.faturamento.models import FaturamentoProduto

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def passo_1_verificar_tokens():
    """Passo 1: Verificar se temos tokens configurados"""
    print("\n" + "="*70)
    print("PASSO 1: VERIFICAR TOKENS")
    print("="*70)
    
    # Verifica variáveis de ambiente
    print("\n📝 Verificando configurações...")
    
    configs = {
        'Client ID (Clientes)': os.environ.get('TAGPLUS_CLIENTES_CLIENT_ID', 'FGDgfhaHfqkZLL9kLtU0wfN71c3hq7AD'),
        'Client Secret (Clientes)': os.environ.get('TAGPLUS_CLIENTES_CLIENT_SECRET', 'uNWYSWyOHGFJvJoEdw1H5xgZnCM92Ey7'),
        'Client ID (Notas)': os.environ.get('TAGPLUS_NOTAS_CLIENT_ID', '8YZNqaklKj3CfIkOtkoV9ILpCllAtalT'),
        'Client Secret (Notas)': os.environ.get('TAGPLUS_NOTAS_CLIENT_SECRET', 'MJHfk8hr3022Y1ETTwqSf0Qsb5Lj6HZe'),
    }
    
    for key, value in configs.items():
        print(f"  {key}: {'✅ Configurado' if value else '❌ Não configurado'}")
    
    return all(configs.values())

def passo_2_testar_conexao():
    """Passo 2: Testar conexão com as APIs"""
    print("\n" + "="*70)
    print("PASSO 2: TESTAR CONEXÃO")
    print("="*70)
    
    resultados = {}
    
    # Teste API de Clientes
    print("\n🔍 Testando API de Clientes...")
    oauth_clientes = TagPlusOAuth2V2(api_type='clientes')
    
    # Opção de inserir token manualmente
    print("\nVocê tem um access token para API de Clientes?")
    print("(Se já autorizou via web, deixe vazio)")
    token = input("Access Token [vazio]: ").strip()
    
    if token:
        oauth_clientes.set_tokens(token)
        print("✅ Token configurado manualmente")
    
    try:
        sucesso, info = oauth_clientes.test_connection()
        resultados['clientes'] = sucesso
        
        if sucesso:
            print("✅ API de Clientes: CONECTADA")
            print(f"   Resposta: {str(info)[:100]}...")
        else:
            print(f"❌ API de Clientes: FALHOU")
            print(f"   Erro: {info}")
    except Exception as e:
        print(f"❌ API de Clientes: ERRO - {e}")
        resultados['clientes'] = False
    
    # Teste API de Notas
    print("\n🔍 Testando API de Notas...")
    oauth_notas = TagPlusOAuth2V2(api_type='notas')
    
    print("\nVocê tem um access token para API de Notas?")
    print("(Se já autorizou via web, deixe vazio)")
    token = input("Access Token [vazio]: ").strip()
    
    if token:
        oauth_notas.set_tokens(token)
        print("✅ Token configurado manualmente")
    
    try:
        sucesso, info = oauth_notas.test_connection()
        resultados['notas'] = sucesso
        
        if sucesso:
            print("✅ API de Notas: CONECTADA")
            print(f"   Resposta: {str(info)[:100]}...")
        else:
            print(f"❌ API de Notas: FALHOU")
            print(f"   Erro: {info}")
    except Exception as e:
        print(f"❌ API de Notas: ERRO - {e}")
        resultados['notas'] = False
    
    return resultados

def passo_3_buscar_um_cliente(oauth):
    """Passo 3: Buscar 1 cliente do TagPlus"""
    print("\n" + "="*70)
    print("PASSO 3: BUSCAR 1 CLIENTE")
    print("="*70)
    
    try:
        print("\n📥 Fazendo requisição para /clientes...")
        
        response = oauth.make_request(
            'GET',
            '/clientes',
            params={
                'pagina': 1,
                'limite': 1
            }
        )
        
        if not response:
            print("❌ Sem resposta da API")
            return None
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("❌ Não autorizado - Token inválido ou expirado")
            print("\n💡 Solução:")
            print("1. Acesse: https://sistema-fretes.onrender.com/tagplus/oauth/")
            print("2. Clique em 'Autorizar API de Clientes'")
            print("3. Faça login no TagPlus e autorize")
            return None
        
        if response.status_code != 200:
            print(f"❌ Erro: {response.text[:200]}")
            return None
        
        data = response.json()
        print(f"✅ Resposta recebida: {type(data)}")
        
        # Extrai cliente da resposta
        if isinstance(data, dict):
            clientes = data.get('data', data.get('clientes', []))
        else:
            clientes = data if isinstance(data, list) else []
        
        if not clientes:
            print("⚠️  Nenhum cliente encontrado")
            return None
        
        cliente = clientes[0]
        print(f"\n📋 Cliente encontrado:")
        print(f"   Nome: {cliente.get('razao_social', cliente.get('nome', 'N/A'))}")
        print(f"   CNPJ/CPF: {cliente.get('cnpj', cliente.get('cpf', 'N/A'))}")
        print(f"   Cidade: {cliente.get('cidade', 'N/A')}")
        print(f"   UF: {cliente.get('uf', 'N/A')}")
        
        return cliente
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None

def passo_4_buscar_uma_nf(oauth):
    """Passo 4: Buscar 1 NF do TagPlus"""
    print("\n" + "="*70)
    print("PASSO 4: BUSCAR 1 NOTA FISCAL")
    print("="*70)
    
    try:
        # Define período de busca
        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=30)
        
        print(f"\n📥 Buscando NFs de {data_inicio} até {data_fim}...")
        
        response = oauth.make_request(
            'GET',
            '/nfes',
            params={
                'pagina': 1,
                'limite': 1,
                'data_emissao_inicio': data_inicio.strftime('%Y-%m-%d'),
                'data_emissao_fim': data_fim.strftime('%Y-%m-%d'),
                'status': 'autorizada'
            }
        )
        
        if not response:
            print("❌ Sem resposta da API")
            return None
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("❌ Não autorizado - Token inválido ou expirado")
            print("\n💡 Solução:")
            print("1. Acesse: https://sistema-fretes.onrender.com/tagplus/oauth/")
            print("2. Clique em 'Autorizar API de Notas'")
            print("3. Faça login no TagPlus e autorize")
            return None
        
        if response.status_code != 200:
            print(f"❌ Erro: {response.text[:200]}")
            return None
        
        data = response.json()
        print(f"✅ Resposta recebida: {type(data)}")
        
        # Extrai NF da resposta
        if isinstance(data, dict):
            nfes = data.get('data', data.get('nfes', []))
        else:
            nfes = data if isinstance(data, list) else []
        
        if not nfes:
            print("⚠️  Nenhuma NF encontrada no período")
            return None
        
        nfe = nfes[0]
        print(f"\n📋 NF encontrada:")
        print(f"   Número: {nfe.get('numero', 'N/A')}")
        print(f"   Data: {nfe.get('data_emissao', 'N/A')}")
        print(f"   Cliente: {nfe.get('cliente', {}).get('razao_social', 'N/A')}")
        print(f"   Status: {nfe.get('status', 'N/A')}")
        
        return nfe
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None

def passo_5_importar_para_banco():
    """Passo 5: Importar usando o importador completo"""
    print("\n" + "="*70)
    print("PASSO 5: IMPORTAR PARA O BANCO")
    print("="*70)
    
    resposta = input("\nDeseja importar 1 cliente e 1 NF para o banco? (s/n): ").strip().lower()
    
    if resposta != 's':
        print("Pulando importação...")
        return
    
    print("\n🚀 Iniciando importação...")
    importador = ImportadorTagPlusV2()
    
    # Importa 1 cliente
    print("\n📥 Importando 1 cliente...")
    resultado_clientes = importador.importar_clientes(limite=1)
    print(f"   Importados: {resultado_clientes['importados']}")
    print(f"   Atualizados: {resultado_clientes['atualizados']}")
    if resultado_clientes['erros']:
        print(f"   Erros: {resultado_clientes['erros']}")
    
    # Importa 1 NF
    print("\n📥 Importando 1 NF...")
    data_fim = datetime.now().date()
    data_inicio = data_fim - timedelta(days=30)
    
    resultado_nfs = importador.importar_nfs(
        data_inicio=data_inicio,
        data_fim=data_fim,
        limite=1
    )
    print(f"   NFs importadas: {resultado_nfs['nfs']['importadas']}")
    print(f"   Itens: {resultado_nfs['nfs']['itens']}")
    if resultado_nfs['nfs']['erros']:
        print(f"   Erros: {resultado_nfs['nfs']['erros']}")
    
    # Verifica no banco
    print("\n🔍 Verificando no banco de dados...")
    
    total_clientes = CadastroCliente.query.filter_by(origem='TagPlus').count()
    print(f"   Total de clientes TagPlus no banco: {total_clientes}")
    
    total_nfs = db.session.query(FaturamentoProduto.numero_nf).filter_by(
        created_by='ImportTagPlus'
    ).distinct().count()
    print(f"   Total de NFs TagPlus no banco: {total_nfs}")

def main():
    """Função principal"""
    print("="*70)
    print("TESTE SIMPLES - TAGPLUS API V2")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        # Passo 1: Verificar configurações
        if not passo_1_verificar_tokens():
            print("\n❌ Configurações incompletas!")
            return
        
        # Passo 2: Testar conexão
        resultados = passo_2_testar_conexao()
        
        if not any(resultados.values()):
            print("\n❌ Nenhuma API está funcionando!")
            print("\n💡 COMO RESOLVER:")
            print("1. Acesse: https://sistema-fretes.onrender.com/tagplus/oauth/")
            print("2. Faça login no sistema")
            print("3. Clique em 'Autorizar API de Clientes'")
            print("4. Clique em 'Autorizar API de Notas'")
            print("5. Execute este script novamente")
            return
        
        # Passo 3: Buscar 1 cliente
        if resultados.get('clientes'):
            oauth_clientes = TagPlusOAuth2V2(api_type='clientes')
            cliente = passo_3_buscar_um_cliente(oauth_clientes)
        else:
            print("\n⚠️  Pulando teste de clientes (API não conectada)")
        
        # Passo 4: Buscar 1 NF
        if resultados.get('notas'):
            oauth_notas = TagPlusOAuth2V2(api_type='notas')
            nf = passo_4_buscar_uma_nf(oauth_notas)
        else:
            print("\n⚠️  Pulando teste de NFs (API não conectada)")
        
        # Passo 5: Importar para o banco
        if resultados.get('clientes') or resultados.get('notas'):
            passo_5_importar_para_banco()
        
        print("\n" + "="*70)
        print("✅ TESTE CONCLUÍDO!")
        print("="*70)
        
        print("\n📊 RESUMO:")
        print(f"   API Clientes: {'✅ Funcionando' if resultados.get('clientes') else '❌ Não conectada'}")
        print(f"   API Notas: {'✅ Funcionando' if resultados.get('notas') else '❌ Não conectada'}")
        
        if all(resultados.values()):
            print("\n🎉 SUCESSO! Ambas as APIs estão funcionando!")
            print("\nPRÓXIMOS PASSOS:")
            print("1. Execute: python testar_tagplus_v2.py")
            print("2. Importe clientes e NFs em lote")
            print("3. Configure webhooks no TagPlus para sincronização automática")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelado pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)