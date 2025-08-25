#!/usr/bin/env python3
"""
TESTE CFOP - FASE 1: Criar Pedido Isolado
Objetivo: Criar pedido teste para descobrir como preencher CFOP
"""

import xmlrpc.client
from datetime import datetime

# ============================================================================
# CONFIGURAÇÕES DO ODOO (de odoo_config.py)
# ============================================================================
url = 'https://odoo.nacomgoya.com.br'
db = 'odoo-17-ee-nacomgoya-prd'
username = 'rafael@conservascampobelo.com.br'
api_key = '67705b0986ff5c052e657f1c0ffd96ceb191af69'

print("📌 Usando configurações de odoo_config.py")
print(f"   URL: {url}")
print(f"   Database: {db}")
print(f"   Usuário: {username}")

# ============================================================================
# CONEXÃO
# ============================================================================
print("\n" + "="*60)
print("TESTE CFOP - CRIANDO PEDIDO ISOLADO")
print("="*60)

try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, api_key, {})
    
    if not uid:
        print("❌ Erro na autenticação. Verifique usuário e senha.")
        exit(1)
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print("✅ Conectado ao Odoo com sucesso")
    
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")
    exit(1)

def executar(model, method, *args):
    """Executar método no Odoo"""
    return models.execute_kw(db, uid, api_key, model, method, *args)

# ============================================================================
# CRIAR PEDIDO TESTE
# ============================================================================
print("\n📝 CRIANDO PEDIDO DE TESTE...")

# Identificador único para este teste
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
referencia_teste = f"TESTE_CFOP_{timestamp}"

# Dados do pedido teste
pedido_teste = {
    'partner_id': 2124,      # ATACADAO SA - LOJA 28
    'company_id': 4,         # NACOM GOYA - CD
    'warehouse_id': 3,       # Armazém CD
    'payment_provider_id': 30,  # Transferência Bancária CD
    'incoterm_id': 6,        # CIF
    'fiscal_position_id': 49,  # SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS
    'client_order_ref': referencia_teste  # Referência única
}

try:
    # Criar pedido
    pedido_id = executar('sale.order', 'create', [pedido_teste])
    print(f"✅ Pedido teste criado com sucesso!")
    print(f"   ID do Pedido: {pedido_id}")
    print(f"   Referência: {referencia_teste}")
    
    # Buscar nome do pedido
    pedido_info = executar('sale.order', 'read', [[pedido_id]], {
        'fields': ['name', 'partner_id', 'fiscal_position_id']
    })[0]
    
    print(f"   Nome: {pedido_info['name']}")
    print(f"   Cliente: {pedido_info['partner_id'][1] if pedido_info['partner_id'] else 'N/A'}")
    print(f"   Posição Fiscal: {pedido_info['fiscal_position_id'][1] if pedido_info['fiscal_position_id'] else 'N/A'}")
    
except Exception as e:
    print(f"❌ Erro ao criar pedido: {e}")
    exit(1)

# ============================================================================
# ADICIONAR LINHA DE TESTE
# ============================================================================
print("\n📦 ADICIONANDO PRODUTO DE TESTE...")

linha_teste = {
    'order_id': pedido_id,
    'product_id': 24,        # LIMAO TAHITI CX 27KG
    'product_uom_qty': 1,    # Quantidade mínima
    'price_unit': 100.00     # Preço teste
}

try:
    # Criar linha
    linha_id = executar('sale.order.line', 'create', [linha_teste])
    print(f"✅ Linha de produto adicionada!")
    print(f"   ID da Linha: {linha_id}")
    
    # Verificar estado inicial
    linha_info = executar('sale.order.line', 'read', [[linha_id]], {
        'fields': [
            'product_id', 
            'l10n_br_cfop_id', 
            'l10n_br_cfop_codigo', 
            'tax_id',
            'price_subtotal'
        ]
    })[0]
    
    print(f"   Produto: {linha_info['product_id'][1] if linha_info['product_id'] else 'N/A'}")
    
    # ============================================================================
    # EVIDÊNCIA DO ESTADO INICIAL
    # ============================================================================
    print("\n" + "="*60)
    print("📸 EVIDÊNCIA - ESTADO INICIAL DO CFOP")
    print("="*60)
    
    cfop_inicial = linha_info.get('l10n_br_cfop_codigo', '')
    cfop_id_inicial = linha_info.get('l10n_br_cfop_id', False)
    impostos_inicial = len(linha_info.get('tax_id', []))
    
    print(f"CFOP Código: '{cfop_inicial}' {'(VAZIO)' if not cfop_inicial else ''}")
    print(f"CFOP ID: {cfop_id_inicial if cfop_id_inicial else 'False (VAZIO)'}")
    print(f"Impostos: {impostos_inicial} impostos aplicados")
    print(f"Subtotal: R$ {linha_info.get('price_subtotal', 0):.2f}")
    
    # ============================================================================
    # SALVAR IDs PARA PRÓXIMAS FASES
    # ============================================================================
    print("\n" + "="*60)
    print("⚠️ IMPORTANTE - ANOTE ESTES DADOS:")
    print("="*60)
    print(f"PEDIDO_ID = {pedido_id}")
    print(f"LINHA_ID = {linha_id}")
    print(f"REFERENCIA = '{referencia_teste}'")
    
    # Salvar em arquivo para facilitar
    with open('teste_cfop_ids.txt', 'w') as f:
        f.write(f"PEDIDO_ID={pedido_id}\n")
        f.write(f"LINHA_ID={linha_id}\n")
        f.write(f"REFERENCIA={referencia_teste}\n")
        f.write(f"CFOP_INICIAL={cfop_inicial or 'VAZIO'}\n")
    
    print("\n✅ IDs salvos em 'teste_cfop_ids.txt'")
    
    print("\n" + "="*60)
    print("PRÓXIMO PASSO:")
    print("="*60)
    print("1. O pedido teste foi criado com sucesso")
    print("2. CFOP está VAZIO (como esperado via API)")
    print("3. Agora vamos descobrir quais métodos podem preencher o CFOP")
    print("4. Execute a FASE 2 para descobrir os métodos disponíveis")
    
except Exception as e:
    print(f"❌ Erro ao adicionar linha: {e}")
    # Tentar deletar pedido se houver erro
    try:
        executar('sale.order', 'unlink', [[pedido_id]])
        print("🧹 Pedido teste removido devido ao erro")
    except:
        pass
    exit(1)

print("\n⚠️ LEMBRE-SE: Este pedido deve ser deletado após os testes!")
print("="*60)