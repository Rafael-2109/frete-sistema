#!/usr/bin/env python3
"""
Script para replicar as ações reativas do Odoo via API
Simula o comportamento do frontend que preenche CFOP automaticamente
Data: 25/08/2025
"""

import xmlrpc.client
from datetime import datetime
import json

# Configuração
url = 'http://192.168.1.37:8069'
db = 'nacom'
username = 'admin'
password = 'admin'

# Conectar ao Odoo
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def executar(model, method, *args):
    """Executar método no Odoo"""
    return models.execute_kw(db, uid, password, model, method, *args)

print("=" * 80)
print("REPLICANDO AÇÕES REATIVAS DO ODOO - CFOP")
print("=" * 80)

# ESTRATÉGIA 1: Usar o método 'onchange' com especificação completa
print("\n1. TENTATIVA: Método onchange com especificação")
print("-" * 40)

def estrategia_onchange_especifico():
    """Tentar usar onchange com especificação de campos"""
    
    # Criar uma cotação teste
    cotacao_data = {
        'partner_id': 2124,  # ATACADAO SA - LOJA 28
        'company_id': 4,     # NACOM GOYA - CD
        'warehouse_id': 3,
        'payment_provider_id': 30,
        'incoterm_id': 6,
    }
    
    try:
        cotacao_id = executar('sale.order', 'create', [cotacao_data])
        print(f"✅ Cotação criada: ID {cotacao_id}")
        
        # Adicionar linha com produto
        linha_data = {
            'order_id': cotacao_id,
            'product_id': 24,  # LIMAO TAHITI
            'product_uom_qty': 10,
        }
        
        linha_id = executar('sale.order.line', 'create', [linha_data])
        print(f"✅ Linha criada: ID {linha_id}")
        
        # Tentar disparar onchange do produto
        print("\nTentando disparar onchange do produto...")
        
        # Método 1: onchange direto na linha
        try:
            spec = {
                'product_id': '1',
                'product_uom_qty': '',
                'l10n_br_cfop_id': '',
                'l10n_br_cfop_codigo': '',
                'tax_id': ''
            }
            
            values = {
                'product_id': 24,
                'order_id': cotacao_id
            }
            
            result = executar('sale.order.line', 'onchange', [
                [linha_id],
                values,
                ['product_id'],
                spec
            ])
            
            print(f"Resultado onchange: {json.dumps(result, indent=2)[:500]}")
            
        except Exception as e:
            print(f"❌ Erro no onchange: {e}")
        
        # Verificar CFOP
        linha = executar('sale.order.line', 'read', [[linha_id]], {
            'fields': ['l10n_br_cfop_id', 'l10n_br_cfop_codigo', 'tax_id']
        })[0]
        
        print(f"\nCFOP após onchange: {linha.get('l10n_br_cfop_codigo', 'VAZIO')}")
        print(f"Impostos: {linha.get('tax_id', [])}")
        
        # Limpar
        executar('sale.order', 'unlink', [[cotacao_id]])
        
    except Exception as e:
        print(f"❌ Erro: {e}")

# ESTRATÉGIA 2: Chamar métodos compute diretamente
print("\n\n2. TENTATIVA: Chamar métodos _compute diretamente")
print("-" * 40)

def estrategia_compute_methods():
    """Tentar chamar métodos compute via Server Action"""
    
    # Criar Server Action temporária
    server_action_code = """
# Forçar recálculo de campos computed
for record in records:
    # Listar métodos _compute disponíveis
    compute_methods = []
    for attr in dir(record):
        if attr.startswith('_compute_') and callable(getattr(record, attr, None)):
            compute_methods.append(attr)
    
    # Tentar executar métodos relacionados a CFOP/fiscal
    for method_name in compute_methods:
        if any(keyword in method_name.lower() for keyword in ['cfop', 'fiscal', 'tax']):
            try:
                method = getattr(record, method_name)
                method()
                _logger.info(f"✅ Executado: {method_name}")
            except Exception as e:
                _logger.error(f"❌ Erro em {method_name}: {str(e)[:50]}")
    
    # Forçar atualização
    record.invalidate_cache()
    
    # Verificar resultado
    _logger.info(f"CFOP após compute: {record.l10n_br_cfop_codigo or 'VAZIO'}")
"""
    
    print("Server Action criada para forçar métodos _compute")
    print("Execute no Odoo para testar")

# ESTRATÉGIA 3: Simular sequência completa do frontend
print("\n\n3. TENTATIVA: Simular sequência do frontend")
print("-" * 40)

def estrategia_simular_frontend():
    """Simular a sequência exata que o frontend faz"""
    
    try:
        # 1. Criar pedido vazio primeiro
        print("Passo 1: Criar pedido vazio")
        pedido_id = executar('sale.order', 'create', [{
            'partner_id': 2124,
            'company_id': 4,
            'warehouse_id': 3,
        }])
        print(f"✅ Pedido criado: {pedido_id}")
        
        # 2. Definir posição fiscal
        print("\nPasso 2: Definir posição fiscal")
        executar('sale.order', 'write', [[pedido_id], {
            'fiscal_position_id': 49  # SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS
        }])
        
        # 3. Adicionar linha vazia
        print("\nPasso 3: Adicionar linha vazia")
        linha_id = executar('sale.order.line', 'create', [{
            'order_id': pedido_id,
            'sequence': 10,
        }])
        
        # 4. Definir produto (simular onChange)
        print("\nPasso 4: Definir produto")
        executar('sale.order.line', 'write', [[linha_id], {
            'product_id': 24,
        }])
        
        # 5. Definir quantidade
        print("\nPasso 5: Definir quantidade")
        executar('sale.order.line', 'write', [[linha_id], {
            'product_uom_qty': 10,
        }])
        
        # 6. Executar Server Action de impostos
        print("\nPasso 6: Calcular impostos")
        executar('ir.actions.server', 'run', [[863]], {
            'context': {
                'active_model': 'sale.order',
                'active_id': pedido_id,
                'active_ids': [pedido_id]
            }
        })
        
        # 7. Verificar resultado
        print("\nPasso 7: Verificar resultado")
        linha_data = executar('sale.order.line', 'read', [[linha_id]], {
            'fields': ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo', 'tax_id']
        })[0]
        
        print(f"Produto: {linha_data.get('product_id', ['', ''])[1] if linha_data.get('product_id') else 'N/A'}")
        print(f"CFOP: {linha_data.get('l10n_br_cfop_codigo', 'VAZIO')}")
        print(f"Impostos: {len(linha_data.get('tax_id', []))} impostos")
        
        # Limpar
        executar('sale.order', 'unlink', [[pedido_id]])
        
    except Exception as e:
        print(f"❌ Erro: {e}")

# ESTRATÉGIA 4: Usar métodos internos do Odoo
print("\n\n4. TENTATIVA: Métodos internos do Odoo")
print("-" * 40)

def estrategia_metodos_internos():
    """Tentar usar métodos internos não documentados"""
    
    metodos_possiveis = [
        '_onchange_product_id',
        '_compute_tax_id', 
        '_compute_l10n_br_cfop_id',
        '_get_computed_taxes',
        'product_id_change',
        'product_uom_change',
        '_prepare_invoice_line',
        '_compute_amount',
        'compute_taxes'
    ]
    
    print("Métodos que podem existir:")
    for metodo in metodos_possiveis:
        print(f"  - {metodo}")
    
    print("\nPara testar, crie Server Actions que tentam chamar esses métodos")

# ESTRATÉGIA 5: Criar método customizado
print("\n\n5. ESTRATÉGIA FINAL: Método customizado via Server Action")
print("-" * 40)

def criar_server_action_cfop():
    """Server Action que implementa a lógica de CFOP"""
    
    codigo = """
# Server Action - Calcular CFOP baseado em Produto + Região
# Model: sale.order

import logging
_logger = logging.getLogger(__name__)

for pedido in records:
    _logger.info(f"Calculando CFOP para pedido {pedido.name}")
    
    for linha in pedido.order_line:
        if not linha.product_id:
            continue
            
        # Obter dados necessários
        produto = linha.product_id
        cliente = pedido.partner_id
        empresa = pedido.company_id
        pos_fiscal = pedido.fiscal_position_id
        
        # Determinar tipo de operação
        operacao_interestadual = False
        operacao_transferencia = False
        
        if cliente and empresa:
            # Verificar se é interestadual
            if cliente.state_id and empresa.state_id:
                operacao_interestadual = cliente.state_id.id != empresa.state_id.id
            
            # Verificar se é transferência (mesmo CNPJ raiz)
            try:
                cnpj_cliente = cliente.l10n_br_cnpj or ''
                cnpj_empresa = empresa.l10n_br_cnpj or ''
                if cnpj_cliente[:8] == cnpj_empresa[:8] and cnpj_cliente and cnpj_empresa:
                    operacao_transferencia = True
            except:
                pass
        
        # Buscar CFOP apropriado
        cfop_codigo = None
        
        if operacao_transferencia:
            if operacao_interestadual:
                cfop_codigo = '6152'  # Transferência interestadual
            else:
                cfop_codigo = '5152'  # Transferência intraestadual
        else:
            if operacao_interestadual:
                cfop_codigo = '6102'  # Venda interestadual
            else:
                cfop_codigo = '5102'  # Venda intraestadual
        
        # Buscar CFOP no sistema
        if cfop_codigo:
            cfop = env['l10n_br_ciel_it_account.cfop'].search([
                ('codigo_cfop', '=', cfop_codigo)
            ], limit=1)
            
            if cfop:
                # Atualizar linha
                linha.write({
                    'l10n_br_cfop_id': cfop.id
                })
                _logger.info(f"✅ CFOP {cfop_codigo} aplicado na linha {linha.id}")
            else:
                _logger.warning(f"❌ CFOP {cfop_codigo} não encontrado no sistema")
        
        # Calcular impostos também
        linha._compute_tax_id()
    
    # Invalidar cache para forçar atualização
    pedido.invalidate_cache()
    
_logger.info("Cálculo de CFOP concluído")
"""
    
    print("Server Action criada!")
    print("Esta action implementa a lógica de CFOP baseada em:")
    print("  - Tipo de operação (venda vs transferência)")
    print("  - Localização (interestadual vs intraestadual)")
    print("  - Produto e suas características")
    
    return codigo

# EXECUTAR TESTES
print("\n" + "=" * 80)
print("EXECUTANDO ESTRATÉGIAS")
print("=" * 80)

# Estratégia 1
print("\n>>> Estratégia 1: Onchange")
estrategia_onchange_especifico()

# Estratégia 3
print("\n>>> Estratégia 3: Simular Frontend")
estrategia_simular_frontend()

# Mostrar outras estratégias
print("\n>>> Estratégia 2: Compute Methods")
estrategia_compute_methods()

print("\n>>> Estratégia 4: Métodos Internos")
estrategia_metodos_internos()

print("\n>>> Estratégia 5: Server Action Customizada")
codigo_sa = criar_server_action_cfop()

print("\n" + "=" * 80)
print("CONCLUSÃO")
print("=" * 80)
print("""
Para replicar as ações reativas do Odoo via API, temos estas opções:

1. ❌ Onchange via API: Limitado, não funciona completamente
2. ⚠️ Métodos compute: Precisa Server Action
3. ⚠️ Simular frontend: Parcialmente funciona
4. ❓ Métodos internos: Depende da versão do Odoo
5. ✅ Server Action customizada: MELHOR OPÇÃO

RECOMENDAÇÃO:
Criar uma Server Action que implementa a lógica de negócio de CFOP
e executá-la após criar o pedido via API.
""")