"""
Script para validar campos do mapeamento_carteira.csv vs carteira_service.py
===========================================================================

Verifica se todos os campos estão corretamente mapeados seguindo a regra:
- Última parte após "/" no CSV deve corresponder ao campo buscado no serviço

Autor: Sistema de Fretes
Data: 2025-07-15
"""

import csv
import re

# Ler o arquivo CSV de mapeamento
mapeamentos = []
with open('projeto_carteira/mapeamento_carteira.csv', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    headers = lines[0].strip().split(';')
    
    for line in lines[1:]:  # Pular cabeçalho
        cols = line.strip().split(';')
        if len(cols) >= 4:
            mapeamentos.append({
                'campo_model': cols[0],
                'campo_odoo': cols[2],
                'descricao': cols[1]
            })

print("=" * 100)
print("VALIDAÇÃO DO MAPEAMENTO DA CARTEIRA")
print("=" * 100)
print()

# Mapeamento atual no serviço (com base no código)
mapeamento_atual = {
    # IDENTIFICAÇÃO
    'num_pedido': "pedido.get('name', '')",
    'cod_produto': "extrair_relacao(linha.get('product_id'), 1)",
    'pedido_cliente': "pedido.get('l10n_br_pedido_compra', '')",
    
    # DATAS
    'data_pedido': "self._format_date(pedido.get('create_date'))",
    'data_atual_pedido': "self._format_date(pedido.get('date_order'))",
    'data_entrega_pedido': "self._format_date(pedido.get('commitment_date'))",
    
    # CLIENTE
    'cnpj_cpf': "cliente.get('l10n_br_cnpj', '')",
    'raz_social': "cliente.get('l10n_br_razao_social', '')",  # CORRIGIDO
    'raz_social_red': "cliente.get('name', '')[:30]",  # CORRIGIDO
    'municipio': "municipio_nome",  # Extraído de l10n_br_municipio_id
    'estado': "estado_uf",  # Extraído de state_id/code
    'vendedor': "extrair_relacao(pedido.get('user_id'), 1)",
    'equipe_vendas': "extrair_relacao(pedido.get('team_id'), 1)",
    
    # PRODUTO
    'nome_produto': "extrair_relacao(linha.get('product_id'), 1)",
    'unid_medida_produto': "extrair_relacao(linha.get('product_uom'), 1)",
    'embalagem_produto': "''",  # FALTANDO!
    'materia_prima_produto': "''",  # Campo removido do modelo?
    'categoria_produto': "''",  # FALTANDO!
    
    # QUANTIDADES
    'qtd_produto_pedido': "linha.get('product_uom_qty', 0)",
    'qtd_saldo_produto_pedido': "linha.get('qty_saldo', 0)",
    'qtd_cancelada_produto_pedido': "linha.get('qty_cancelado', 0)",
    'preco_produto_pedido': "linha.get('price_unit', 0)",
    
    # COMERCIAL
    'cond_pgto_pedido': "extrair_relacao(pedido.get('payment_term_id'), 1)",
    'forma_pgto_pedido': "extrair_relacao(pedido.get('payment_provider_id'), 1)",
    'incoterm': "incoterm_codigo",  # Extraído e tratado
    'metodo_entrega_pedido': "extrair_relacao(pedido.get('carrier_id'), 1)",
    'cliente_nec_agendamento': "cliente.get('agendamento', '')",
    'observ_ped_1': "str(pedido.get('picking_note', ''))",
    
    # ENDEREÇO ENTREGA
    'cnpj_endereco_ent': "endereco.get('l10n_br_cnpj', '')",
    'empresa_endereco_ent': "endereco.get('name', '')",  # self = name
    'cep_endereco_ent': "endereco.get('l10n_br_cep', '')",  # zip = l10n_br_cep
    'nome_cidade': "municipio_entrega_nome",  # Extraído
    'cod_uf': "estado_entrega_uf",  # Extraído
    'bairro_endereco_ent': "endereco.get('l10n_br_endereco_bairro', '')",
    'rua_endereco_ent': "endereco.get('street', '')",
    'endereco_ent': "endereco.get('l10n_br_endereco_numero', '')",
    'telefone_endereco_ent': "endereco.get('phone', '')"
}

# Validar cada campo
problemas = []
corretos = []

for mapeamento in mapeamentos:
    campo = mapeamento['campo_model']
    campo_odoo = mapeamento['campo_odoo']
    
    # Extrair última parte após /
    partes = campo_odoo.split('/')
    campo_esperado = partes[-1] if partes else ''
    
    # Casos especiais
    if campo_esperado == 'self':
        campo_esperado = 'name'
    elif campo == 'estado':
        campo_esperado = 'code'  # state_id/code
    elif campo in ['municipio', 'nome_cidade', 'cod_uf']:
        # Campos extraídos de l10n_br_municipio_id
        campo_esperado = 'l10n_br_municipio_id'
    
    # Verificar se está mapeado
    if campo in mapeamento_atual:
        codigo_atual = mapeamento_atual[campo]
        
        # Verificar se contém o campo esperado
        if campo_esperado in codigo_atual or campo in ['municipio', 'nome_cidade', 'cod_uf', 'estado', 'incoterm']:
            corretos.append(f"✅ {campo}: {campo_esperado}")
        elif codigo_atual == "''" or 'None' in codigo_atual:
            problemas.append({
                'campo': campo,
                'esperado': campo_esperado,
                'atual': 'VAZIO/FALTANDO',
                'odoo_path': campo_odoo
            })
        else:
            problemas.append({
                'campo': campo,
                'esperado': campo_esperado,
                'atual': codigo_atual,
                'odoo_path': campo_odoo
            })
    else:
        problemas.append({
            'campo': campo,
            'esperado': campo_esperado,
            'atual': 'NÃO MAPEADO',
            'odoo_path': campo_odoo
        })

# Resultado
print(f"📊 RESUMO:")
print(f"• Total de campos: {len(mapeamentos)}")
print(f"• Campos corretos: {len(corretos)}")
print(f"• Campos com problemas: {len(problemas)}")
print()

if problemas:
    print("❌ PROBLEMAS ENCONTRADOS:")
    print("-" * 100)
    for p in problemas:
        print(f"\nCampo: {p['campo']}")
        print(f"  Caminho Odoo: {p['odoo_path']}")
        print(f"  Esperado: {p['esperado']}")
        print(f"  Atual: {p['atual']}")
        
        # Sugerir correção
        if p['campo'] == 'embalagem_produto':
            print(f"  💡 Correção: categoria.get('name', '')")
        elif p['campo'] == 'categoria_produto':
            print(f"  💡 Correção: categoria_grandparent.get('name', '')")
        elif p['campo'] == 'cep_endereco_ent':
            print(f"  💡 Correção: endereco.get('zip', '')")

print("\n" + "=" * 100)
print("CORREÇÕES NECESSÁRIAS NO CÓDIGO:")
print("=" * 100)

# Gerar código de correção
if problemas:
    print("\n# Adicionar estas correções no método _mapear_item_otimizado:")
    for p in problemas:
        if p['campo'] == 'embalagem_produto':
            print(f"'embalagem_produto': categoria.get('name', ''),  # Categoria do produto")
        elif p['campo'] == 'categoria_produto':
            print(f"'categoria_produto': categoria_grandparent.get('name', ''),  # Categoria principal")
        elif p['campo'] == 'cep_endereco_ent':
            print(f"'cep_endereco_ent': endereco.get('zip', ''),  # CEP") 