# Server Action 1955 - Debug CFOP Completo
# Copie este código para o campo "Python Code" da Server Action
# Model: sale.order.line

# Coletar TODAS as informações em uma lista para mostrar de uma vez
debug_info = []

for record in records:
    debug_info.append("="*60)
    debug_info.append("CFOP DEBUG COMPLETO - Server Action 1955")
    debug_info.append("="*60)
    
    # 1. Informações básicas
    debug_info.append(f"\n=== INFORMAÇÕES BÁSICAS ===")
    debug_info.append(f"Linha ID: {record.id}")
    debug_info.append(f"Produto: {record.product_id.name if record.product_id else 'SEM PRODUTO'}")
    debug_info.append(f"Produto ID: {record.product_id.id if record.product_id else 'N/A'}")
    debug_info.append(f"Pedido: {record.order_id.name if record.order_id else 'SEM PEDIDO'}")
    
    # 2. CFOP atual
    debug_info.append(f"\n=== CFOP ATUAL ===")
    debug_info.append(f"l10n_br_cfop_id: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'VAZIO'}")
    debug_info.append(f"l10n_br_cfop_codigo: {record.l10n_br_cfop_codigo or 'VAZIO'}")
    
    # 3. TODOS os campos fiscais/CFOP
    debug_info.append(f"\n=== CAMPOS FISCAIS/CFOP ENCONTRADOS ===")
    for field_name in sorted(record._fields.keys()):
        if any(keyword in field_name.lower() for keyword in ['fiscal', 'cfop', 'l10n_br', 'operation']):
            try:
                value = getattr(record, field_name, 'N/A')
                # Simplificar para log
                if value and hasattr(value, 'id'):
                    if hasattr(value, 'name'):
                        value = f"{value.name} (ID: {value.id})"
                    else:
                        value = f"ID: {value.id}"
                elif value and hasattr(value, 'ids'):
                    value = f"IDs: {value.ids[:5]}..." if len(value.ids) > 5 else f"IDs: {value.ids}"
                elif value and isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                debug_info.append(f"  {field_name}: {value}")
            except Exception as e:
                debug_info.append(f"  {field_name}: ERRO - {str(e)[:50]}")
    
    # 4. Informações do Cliente e Posição Fiscal
    debug_info.append(f"\n=== CLIENTE E POSIÇÃO FISCAL ===")
    if record.order_id and record.order_id.partner_id:
        partner = record.order_id.partner_id
        fiscal_pos = partner.property_account_position_id
        debug_info.append(f"Cliente: {partner.name}")
        debug_info.append(f"Cliente ID: {partner.id}")
        debug_info.append(f"CNPJ: {getattr(partner, 'l10n_br_cnpj', 'Campo não existe')}")
        debug_info.append(f"Posição Fiscal: {fiscal_pos.name if fiscal_pos else 'SEM POSIÇÃO FISCAL'}")
        debug_info.append(f"Posição Fiscal ID: {fiscal_pos.id if fiscal_pos else 'N/A'}")
        debug_info.append(f"Estado Cliente: {partner.state_id.code if partner.state_id else 'N/A'}")
        debug_info.append(f"Cidade Cliente: {partner.city or 'N/A'}")
    
    # 5. Informações da Empresa
    debug_info.append(f"\n=== EMPRESA ===")
    if record.order_id:
        company = record.order_id.company_id
        debug_info.append(f"Empresa: {company.name if company else 'N/A'}")
        debug_info.append(f"Empresa ID: {company.id if company else 'N/A'}")
        debug_info.append(f"Estado Empresa: {company.state_id.code if company and company.state_id else 'N/A'}")
    
    # 6. Posição Fiscal do Pedido
    debug_info.append(f"\n=== POSIÇÃO FISCAL DO PEDIDO ===")
    if record.order_id:
        order_fiscal_pos = record.order_id.fiscal_position_id
        debug_info.append(f"Posição Fiscal do Pedido: {order_fiscal_pos.name if order_fiscal_pos else 'VAZIO'}")
        debug_info.append(f"Posição Fiscal ID: {order_fiscal_pos.id if order_fiscal_pos else 'N/A'}")
    
    # 7. Verificar se existem campos de operação fiscal
    debug_info.append(f"\n=== CAMPOS DE OPERAÇÃO FISCAL ===")
    operation_fields = [
        'fiscal_operation_id',
        'fiscal_operation_line_id',
        'l10n_br_fiscal_operation_id',
        'l10n_br_fiscal_operation_line_id',
        'l10n_br_operacao_id',
        'l10n_br_tipo_operacao',
        'l10n_br_operacao_consumidor',
        'operation_id',
        'operation_line_id'
    ]
    
    for field_name in operation_fields:
        try:
            if hasattr(record, field_name):
                value = getattr(record, field_name)
                if value:
                    if hasattr(value, 'name'):
                        debug_info.append(f"  ✅ {field_name}: {value.name} (ID: {value.id})")
                    else:
                        debug_info.append(f"  ✅ {field_name}: {value}")
                else:
                    debug_info.append(f"  ⚠️ {field_name}: campo existe mas está VAZIO")
        except:
            pass  # Campo não existe, pular
    
    # 8. Verificar estrutura dos campos (compute, related, etc)
    debug_info.append(f"\n=== ESTRUTURA DOS CAMPOS CFOP ===")
    for field_name in ['l10n_br_cfop_id', 'l10n_br_cfop_codigo']:
        if field_name in record._fields:
            field = record._fields[field_name]
            debug_info.append(f"\nCampo: {field_name}")
            debug_info.append(f"  Tipo: {field.type}")
            if hasattr(field, 'compute') and field.compute:
                debug_info.append(f"  Compute: {field.compute}")
            if hasattr(field, 'related') and field.related:
                debug_info.append(f"  Related: {field.related}")
            if hasattr(field, 'depends') and field.depends:
                debug_info.append(f"  Depends: {field.depends}")
    
    # 9. Listar TODOS os métodos relacionados
    debug_info.append(f"\n=== MÉTODOS DISPONÍVEIS ===")
    methods_found = []
    for attr_name in dir(record):
        if any(keyword in attr_name.lower() for keyword in ['cfop', 'fiscal', 'operation', 'compute', 'onchange']):
            try:
                attr = getattr(record, attr_name)
                if callable(attr):
                    methods_found.append(attr_name)
            except:
                pass
    
    if methods_found:
        debug_info.append(f"Total de métodos encontrados: {len(methods_found)}")
        for method in sorted(methods_found)[:30]:  # Mostrar até 30
            debug_info.append(f"  - {method}")
    else:
        debug_info.append("Nenhum método relacionado encontrado")
    
    # 10. Tentar executar onchange
    debug_info.append(f"\n=== TENTATIVA DE EXECUÇÃO DE MÉTODOS ===")
    
    # Tentar onchange_l10n_br_calcular_imposto no pedido
    try:
        if record.order_id and hasattr(record.order_id, 'onchange_l10n_br_calcular_imposto'):
            debug_info.append("Executando order.onchange_l10n_br_calcular_imposto()...")
            record.order_id.onchange_l10n_br_calcular_imposto()
            record.invalidate_cache()
            debug_info.append(f"  ✅ Executado! CFOP após: {record.l10n_br_cfop_codigo or 'AINDA VAZIO'}")
        else:
            debug_info.append("  ❌ order.onchange_l10n_br_calcular_imposto não existe")
    except Exception as e:
        debug_info.append(f"  ❌ Erro: {str(e)[:100]}")
    
    # Tentar _compute_tax_id se existir
    try:
        if hasattr(record, '_compute_tax_id'):
            debug_info.append("Executando record._compute_tax_id()...")
            record._compute_tax_id()
            debug_info.append(f"  ✅ Executado!")
    except Exception as e:
        debug_info.append(f"  ❌ _compute_tax_id: {str(e)[:50]}")
    
    debug_info.append("\n" + "="*60)

# Mostrar TUDO como UserError para ver na tela
raise UserError('\n'.join(debug_info))