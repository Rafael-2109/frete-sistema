#!/usr/bin/env python3
"""
ROTEIRO DE TESTES SISTEMÁTICO E SEGURO PARA CFOP
Data: 25/08/2025
Objetivo: Descobrir como preencher CFOP via API sem riscos
"""

print("=" * 80)
print("ROTEIRO DE TESTES - CFOP NO ODOO")
print("=" * 80)

print("""
PREMISSAS DE SEGURANÇA:
-----------------------
1. SEM ambiente de teste disponível
2. Testes apenas em pedido isolado criado para este fim
3. Pedido será deletado após testes
4. Métodos testados um por vez
5. Documentação completa de cada resultado
""")

# =============================================================================
# FASE 1: PREPARAÇÃO DO AMBIENTE DE TESTE
# =============================================================================

print("\n" + "=" * 80)
print("FASE 1: CRIAR PEDIDO DE TESTE ISOLADO")
print("=" * 80)

script_fase1 = """
import xmlrpc.client
from datetime import datetime

# IMPORTANTE: Ajuste estas configurações
url = 'http://SEU_IP:8069'  # SUBSTITUA
db = 'SEU_DB'               # SUBSTITUA
username = 'SEU_USER'        # SUBSTITUA
password = 'SUA_SENHA'       # SUBSTITUA

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def executar(model, method, *args):
    return models.execute_kw(db, uid, password, model, method, *args)

print("\\n=== CRIANDO PEDIDO DE TESTE ISOLADO ===")

# Dados do pedido teste
pedido_teste = {
    'partner_id': 2124,      # ATACADAO SA - LOJA 28
    'company_id': 4,         # NACOM GOYA - CD
    'warehouse_id': 3,
    'payment_provider_id': 30,
    'incoterm_id': 6,
    'fiscal_position_id': 49, # SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS
    # Nome único para identificar
    'client_order_ref': f'TESTE_CFOP_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
}

# Criar pedido
pedido_id = executar('sale.order', 'create', [pedido_teste])
print(f"✅ Pedido teste criado: ID {pedido_id}")

# Adicionar linha de teste
linha_teste = {
    'order_id': pedido_id,
    'product_id': 24,        # LIMAO TAHITI
    'product_uom_qty': 1,
    'price_unit': 100.00
}

linha_id = executar('sale.order.line', 'create', [linha_teste])
print(f"✅ Linha teste criada: ID {linha_id}")

# Verificar estado inicial
linha = executar('sale.order.line', 'read', [[linha_id]], {
    'fields': ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo', 'tax_id']
})[0]

print("\\n=== ESTADO INICIAL ===")
print(f"Produto: {linha['product_id'][1] if linha['product_id'] else 'N/A'}")
print(f"CFOP Código: {linha.get('l10n_br_cfop_codigo', 'VAZIO')}")
print(f"CFOP ID: {linha.get('l10n_br_cfop_id', 'VAZIO')}")
print(f"Impostos: {len(linha.get('tax_id', []))} impostos")

print(f"\\n📝 ANOTE ESTES IDs:")
print(f"   Pedido ID: {pedido_id}")
print(f"   Linha ID: {linha_id}")
print("\\n⚠️ IMPORTANTE: Este pedido deve ser deletado após os testes!")
"""

print("SCRIPT FASE 1:")
print(script_fase1)

# =============================================================================
# FASE 2: DESCOBERTA SEGURA DE MÉTODOS
# =============================================================================

print("\n" + "=" * 80)
print("FASE 2: SERVER ACTION - DESCOBERTA SEGURA")
print("=" * 80)

print("""
Server Action para descobrir métodos SEM EXECUTAR
Model: sale.order.line

Copie este código para uma Server Action:
""")

server_action_descoberta = """
# Server Action - DESCOBERTA SEGURA (não executa nada)
# Model: sale.order.line

debug_info = []

for record in records:
    debug_info.append("="*60)
    debug_info.append("DESCOBERTA DE MÉTODOS - ANÁLISE SEGURA")
    debug_info.append("="*60)
    
    debug_info.append(f"\\nLinha ID: {record.id}")
    debug_info.append(f"Produto: {record.product_id.name if record.product_id else 'N/A'}")
    debug_info.append(f"CFOP Atual: {record.l10n_br_cfop_codigo or 'VAZIO'}")
    
    # CATEGORIZAR métodos sem executar
    metodos = {
        'onchange': [],
        'compute': [],
        'fiscal': [],
        'seguranca': {
            'seguros': [],
            'perigosos': []
        }
    }
    
    # Métodos perigosos conhecidos (NUNCA executar)
    METODOS_PERIGOSOS = [
        'unlink', 'delete', 'purge', 'cancel', 'cleanup',
        'reset', 'clear', 'remove', 'destroy', 'drop'
    ]
    
    for attr_name in dir(record):
        if not attr_name.startswith('__'):
            try:
                attr = getattr(record, attr_name, None)
                if callable(attr):
                    # Verificar se é perigoso
                    is_perigoso = any(perigo in attr_name.lower() for perigo in METODOS_PERIGOSOS)
                    
                    if is_perigoso:
                        metodos['seguranca']['perigosos'].append(attr_name)
                    else:
                        # Classificar por tipo
                        if 'onchange' in attr_name.lower():
                            metodos['onchange'].append(attr_name)
                        elif '_compute_' in attr_name.lower():
                            metodos['compute'].append(attr_name)
                        elif any(k in attr_name.lower() for k in ['fiscal', 'cfop', 'tax', 'l10n_br']):
                            metodos['fiscal'].append(attr_name)
                        elif attr_name.startswith('_') and not is_perigoso:
                            metodos['seguranca']['seguros'].append(attr_name)
            except:
                pass
    
    # Relatório
    debug_info.append("\\n=== MÉTODOS ENCONTRADOS (NÃO EXECUTADOS) ===")
    
    debug_info.append(f"\\n✅ MÉTODOS ONCHANGE (potencialmente seguros):")
    for m in metodos['onchange'][:5]:
        debug_info.append(f"   - {m}")
    
    debug_info.append(f"\\n✅ MÉTODOS COMPUTE (potencialmente seguros):")
    for m in metodos['compute'][:5]:
        debug_info.append(f"   - {m}")
    
    debug_info.append(f"\\n✅ MÉTODOS FISCAIS (mais relevantes):")
    for m in metodos['fiscal'][:10]:
        debug_info.append(f"   - {m}")
    
    debug_info.append(f"\\n⚠️ MÉTODOS PRIVADOS SEGUROS:")
    for m in metodos['seguranca']['seguros'][:5]:
        debug_info.append(f"   - {m}")
    
    debug_info.append(f"\\n❌ MÉTODOS PERIGOSOS (NUNCA EXECUTAR):")
    for m in metodos['seguranca']['perigosos'][:5]:
        debug_info.append(f"   - {m}")
    
    # Análise de campos
    debug_info.append("\\n=== ESTRUTURA DO CAMPO CFOP ===")
    if 'l10n_br_cfop_id' in record._fields:
        field = record._fields['l10n_br_cfop_id']
        debug_info.append(f"l10n_br_cfop_id:")
        debug_info.append(f"  Tipo: {field.type if hasattr(field, 'type') else 'N/A'}")
        if hasattr(field, 'compute'):
            debug_info.append(f"  Compute: {field.compute if field.compute else 'Não'}")
        if hasattr(field, 'related'):
            debug_info.append(f"  Related: {field.related if field.related else 'Não'}")

raise UserError('\\n'.join(debug_info))
"""

print(server_action_descoberta)

# =============================================================================
# FASE 3: TESTE INDIVIDUAL DE MÉTODOS
# =============================================================================

print("\n" + "=" * 80)
print("FASE 3: TESTE INDIVIDUAL DE MÉTODOS SEGUROS")
print("=" * 80)

script_fase3 = """
# Script para testar métodos individualmente
# USE APENAS após identificar métodos na FASE 2

import xmlrpc.client

# Configurações (mesmas da FASE 1)
url = 'http://SEU_IP:8069'
db = 'SEU_DB'
username = 'SEU_USER'
password = 'SUA_SENHA'

# IDs do pedido teste (da FASE 1)
PEDIDO_TESTE_ID = 999  # SUBSTITUA pelo ID real
LINHA_TESTE_ID = 999   # SUBSTITUA pelo ID real

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def executar(model, method, *args):
    return models.execute_kw(db, uid, password, model, method, *args)

def verificar_cfop():
    '''Verifica estado atual do CFOP'''
    linha = executar('sale.order.line', 'read', [[LINHA_TESTE_ID]], {
        'fields': ['l10n_br_cfop_codigo', 'l10n_br_cfop_id', 'tax_id']
    })[0]
    return {
        'cfop_codigo': linha.get('l10n_br_cfop_codigo', 'VAZIO'),
        'cfop_id': linha.get('l10n_br_cfop_id', 'VAZIO'),
        'impostos': len(linha.get('tax_id', []))
    }

print("\\n=== TESTE DE MÉTODOS INDIVIDUAIS ===")

# Lista de métodos a testar (PREENCHA com métodos da FASE 2)
METODOS_PARA_TESTAR = [
    # Exemplo (descomente e ajuste):
    # ('_compute_tax_id', 'Calcular impostos'),
    # ('_onchange_product_id', 'Onchange do produto'),
]

for metodo_nome, descricao in METODOS_PARA_TESTAR:
    print(f"\\n📍 Testando: {metodo_nome} ({descricao})")
    
    # Estado antes
    antes = verificar_cfop()
    print(f"   Antes - CFOP: {antes['cfop_codigo']}, Impostos: {antes['impostos']}")
    
    # Criar Server Action temporária para testar o método
    server_action_teste = f'''
for record in records:
    if record.id == {LINHA_TESTE_ID}:
        try:
            if hasattr(record, '{metodo_nome}'):
                metodo = getattr(record, '{metodo_nome}')
                if callable(metodo):
                    metodo()
                    _logger.info("✅ {metodo_nome} executado com sucesso")
                else:
                    _logger.info("❌ {metodo_nome} não é callable")
            else:
                _logger.info("❌ {metodo_nome} não existe")
        except Exception as e:
            _logger.error(f"❌ Erro em {metodo_nome}: {{str(e)[:100]}}")
    '''
    
    print(f"   Execute esta Server Action (Model: sale.order.line):")
    print(f"   {server_action_teste[:200]}...")
    
    # Após executar no Odoo, verificar resultado
    input("   Pressione ENTER após executar a Server Action...")
    
    depois = verificar_cfop()
    print(f"   Depois - CFOP: {depois['cfop_codigo']}, Impostos: {depois['impostos']}")
    
    # Análise do resultado
    if depois['cfop_codigo'] != 'VAZIO' and antes['cfop_codigo'] == 'VAZIO':
        print(f"   ✅ SUCESSO! Método {metodo_nome} preencheu o CFOP!")
    elif depois['impostos'] > antes['impostos']:
        print(f"   ⚠️ Método {metodo_nome} calculou impostos mas não CFOP")
    else:
        print(f"   ❌ Método {metodo_nome} não teve efeito no CFOP")

print("\\n" + "="*60)
print("TESTES CONCLUÍDOS")
"""

print("SCRIPT FASE 3:")
print(script_fase3)

# =============================================================================
# FASE 4: LIMPEZA
# =============================================================================

print("\n" + "=" * 80)
print("FASE 4: LIMPEZA DO PEDIDO TESTE")
print("=" * 80)

script_limpeza = """
# Script para deletar o pedido teste após conclusão

import xmlrpc.client

# Configurações
url = 'http://SEU_IP:8069'
db = 'SEU_DB'
username = 'SEU_USER'
password = 'SUA_SENHA'

PEDIDO_TESTE_ID = 999  # SUBSTITUA pelo ID real

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def executar(model, method, *args):
    return models.execute_kw(db, uid, password, model, method, *args)

print("\\n=== LIMPEZA DO AMBIENTE ===")

# Verificar antes de deletar
pedido = executar('sale.order', 'read', [[PEDIDO_TESTE_ID]], {
    'fields': ['name', 'client_order_ref']
})[0]

print(f"Pedido a deletar: {pedido['name']}")
print(f"Referência: {pedido.get('client_order_ref', 'N/A')}")

confirmacao = input("\\nConfirma exclusão? (digite 'SIM'): ")

if confirmacao == 'SIM':
    executar('sale.order', 'unlink', [[PEDIDO_TESTE_ID]])
    print("✅ Pedido teste deletado com sucesso!")
else:
    print("❌ Exclusão cancelada")
"""

print("SCRIPT LIMPEZA:")
print(script_limpeza)

# =============================================================================
# RESUMO DO ROTEIRO
# =============================================================================

print("\n" + "=" * 80)
print("RESUMO DO ROTEIRO DE TESTES")
print("=" * 80)

print("""
SEQUÊNCIA DE EXECUÇÃO:
----------------------

1️⃣ FASE 1 - Preparação
   - Execute o script para criar pedido teste isolado
   - Anote os IDs gerados
   - Confirme que CFOP está vazio

2️⃣ FASE 2 - Descoberta
   - Crie Server Action com o código fornecido
   - Execute na linha do pedido teste
   - Analise lista de métodos disponíveis
   - Identifique candidatos seguros

3️⃣ FASE 3 - Testes Individuais
   - Teste um método por vez
   - Documente ANTES e DEPOIS
   - Identifique qual método preenche CFOP

4️⃣ FASE 4 - Limpeza
   - Delete o pedido teste
   - Confirme exclusão completa

CRITÉRIOS DE SUCESSO:
--------------------
✅ Método identificado que preenche CFOP
✅ Sem efeitos colaterais no sistema
✅ Reproduzível em múltiplos pedidos
✅ Performance aceitável (< 5 segundos)

EVIDÊNCIAS A COLETAR:
--------------------
📸 Screenshot do CFOP antes/depois
📝 Logs do servidor Odoo
📊 Lista completa de métodos
✅ Confirmação visual no Odoo

SEGURANÇA:
----------
⚠️ NUNCA execute métodos com: unlink, delete, cancel, purge
⚠️ SEMPRE teste em pedido isolado primeiro
⚠️ SEMPRE delete o pedido teste após conclusão
""")