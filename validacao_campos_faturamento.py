"""
Script para validar campos do mapeamento_faturamento.csv vs faturamento_service.py
==================================================================================

Verifica se todos os campos estão corretamente mapeados seguindo a regra:
- Última parte após "/" no CSV deve corresponder ao campo buscado no serviço

Autor: Sistema de Fretes
Data: 2025-07-15
"""

import re

# Ler o arquivo CSV de mapeamento
mapeamentos = []
with open('projeto_carteira/mapeamento_faturamento.csv', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
    for line in lines:
        # Limpar linha
        line = line.strip()
        if not line:
            continue
            
        # Encontrar campos separados por ;
        partes = line.split(';')
        if len(partes) >= 4:
            # Extrair nome do campo do modelo (entre = e ;)
            campo_match = re.search(r'(\w+)\s*=', partes[0])
            if campo_match:
                campo_model = campo_match.group(1)
                campo_odoo = partes[3]  # Campo Odoo está na 4ª coluna
                
                mapeamentos.append({
                    'campo_model': campo_model,
                    'campo_odoo': campo_odoo,
                    'descricao': partes[2] if len(partes) > 2 else ''
                })

print("=" * 100)
print("VALIDAÇÃO DO MAPEAMENTO DO FATURAMENTO")
print("=" * 100)
print()

# Mapeamento atual no serviço (baseado no código do _mapear_item_faturamento_otimizado)
mapeamento_atual = {
    # DADOS DA NOTA
    'numero_nf': "fatura.get('name', '')",  # account.move name
    'data_fatura': "self._parse_date(linha.get('date'))",  # account.move.line date
    'origem': "fatura.get('invoice_origin', '')",
    'status_nf': "self._mapear_status(fatura.get('state', ''))",
    
    # DADOS DO CLIENTE
    'cnpj_cliente': "cliente.get('l10n_br_cnpj', '')",
    'nome_cliente': "cliente.get('name', '')",
    'municipio': "municipio_nome",  # Extraído de l10n_br_municipio_id
    'estado': "estado_uf",  # Extraído de l10n_br_municipio_id
    
    # DADOS COMERCIAIS
    'vendedor': "usuario.get('name', '')",  # invoice_user_id
    'incoterm': "incoterm_codigo",  # invoice_incoterm_id tratado
    
    # DADOS DO PRODUTO
    'cod_produto': "produto.get('default_code', '')",
    'nome_produto': "produto.get('name', '')",
    'peso_unitario_produto': "produto.get('weight', 0)",
    
    # QUANTIDADES E VALORES
    'qtd_produto_faturado': "linha.get('quantity', 0)",
    'valor_produto_faturado': "linha.get('price_total', 0)",
    'preco_produto_faturado': "linha.get('price_unit', 0)",
    'peso_total': "self._calcular_peso_total()"
}

# Validar cada campo
problemas = []
corretos = []
avisos = []

for mapeamento in mapeamentos:
    campo = mapeamento['campo_model']
    campo_odoo = mapeamento['campo_odoo']
    
    # Casos especiais ou comentários
    if campo_odoo.startswith('#'):
        avisos.append(f"ℹ️ {campo}: {campo_odoo} (campo calculado/comentário)")
        continue
    
    # Extrair última parte após /
    partes = campo_odoo.split('/')
    campo_esperado = partes[-1] if partes else ''
    
    # Verificar se está mapeado
    if campo in mapeamento_atual:
        codigo_atual = mapeamento_atual[campo]
        
        # Casos especiais de mapeamento
        casos_especiais = {
            'numero_nf': ['x_studio_nf_e', 'name'],  # NF pode vir de x_studio_nf_e ou name
            'data_fatura': ['date'],
            'cnpj_cliente': ['l10n_br_cnpj'],
            'nome_cliente': ['partner_id', 'name'],
            'municipio': ['l10n_br_municipio_id'],
            'estado': ['l10n_br_municipio_id'],
            'vendedor': ['invoice_user_id', 'name'],
            'incoterm': ['invoice_incoterm_id'],
            'cod_produto': ['code', 'default_code'],
            'nome_produto': ['name'],
            'qtd_produto_faturado': ['quantity'],
            'preco_produto_faturado': ['price_unit'],
            'valor_produto_faturado': ['l10n_br_total_nfe', 'price_total'],
            'peso_unitario_produto': ['gross_weight', 'weight'],
            'origem': ['invoice_origin'],
            'status_nf': ['state']
        }
        
        # Verificar se está correto
        campo_ok = False
        if campo in casos_especiais:
            for campo_valido in casos_especiais[campo]:
                if campo_valido in codigo_atual:
                    campo_ok = True
                    break
        
        if campo_ok:
            corretos.append(f"✅ {campo}: {campo_esperado}")
        else:
            problemas.append({
                'campo': campo,
                'esperado': campo_esperado,
                'atual': codigo_atual,
                'odoo_path': campo_odoo
            })
    else:
        # Campo não mapeado
        if campo not in ['peso_total']:  # peso_total é calculado
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
print(f"• Avisos/Calculados: {len(avisos)}")
print()

if problemas:
    print("❌ PROBLEMAS ENCONTRADOS:")
    print("-" * 100)
    for p in problemas:
        print(f"\nCampo: {p['campo']}")
        print(f"  Caminho Odoo: {p['odoo_path']}")
        print(f"  Esperado: {p['esperado']}")
        print(f"  Atual: {p['atual']}")

if avisos:
    print("\nℹ️ AVISOS:")
    for aviso in avisos:
        print(f"  {aviso}")

print("\n" + "=" * 100)
print("ANÁLISE DETALHADA:")
print("=" * 100)

# Análise dos campos
print("\n🔍 CAMPOS QUE PRECISAM ATENÇÃO:")

# numero_nf - precisa buscar x_studio_nf_e ao invés de name
if any(p['campo'] == 'numero_nf' for p in problemas):
    print("\n1. numero_nf:")
    print("   - CSV indica: invoice_line_ids/x_studio_nf_e")
    print("   - Código atual usa: fatura.get('name')")
    print("   - 💡 CORREÇÃO: Adicionar x_studio_nf_e nos campos da fatura")

# cod_produto - precisa ser 'code' não 'default_code'
print("\n2. cod_produto:")
print("   - CSV indica: product_id/code")
print("   - Código atual usa: produto.get('default_code')")
print("   - 💡 CORREÇÃO: Mudar para produto.get('code', '')")

# peso_unitario_produto - gross_weight ao invés de weight
print("\n3. peso_unitario_produto:")
print("   - CSV indica: gross_weight do product.template")
print("   - Código atual usa: produto.get('weight')")
print("   - 💡 CORREÇÃO: Buscar gross_weight do template do produto")

print("\n✅ CAMPOS CORRETAMENTE MAPEADOS:")
for correto in corretos[:5]:  # Mostrar apenas 5 exemplos
    print(f"  {correto}")
if len(corretos) > 5:
    print(f"  ... e mais {len(corretos)-5} campos") 