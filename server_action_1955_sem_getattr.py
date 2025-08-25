# Server Action 1955 - Debug CFOP (SEM getattr/hasattr)
# Copie este código para o campo "Python Code" da Server Action
# Model: sale.order.line

# Coletar informações para debug
debug_info = []

for record in records:
    debug_info.append("="*60)
    debug_info.append("CFOP DEBUG - Server Action 1955")
    debug_info.append("="*60)
    
    # 1. Informações básicas
    debug_info.append("\n=== INFORMAÇÕES BÁSICAS ===")
    debug_info.append(f"Linha ID: {record.id}")
    debug_info.append(f"Produto: {record.product_id.name if record.product_id else 'SEM PRODUTO'}")
    debug_info.append(f"Produto ID: {record.product_id.id if record.product_id else 'N/A'}")
    debug_info.append(f"Pedido: {record.order_id.name if record.order_id else 'SEM PEDIDO'}")
    
    # 2. CFOP atual
    debug_info.append("\n=== CFOP ATUAL ===")
    debug_info.append(f"l10n_br_cfop_id: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'VAZIO'}")
    debug_info.append(f"l10n_br_cfop_codigo: {record.l10n_br_cfop_codigo or 'VAZIO'}")
    
    # 3. Campos fiscais - acessar diretamente sem getattr
    debug_info.append("\n=== CAMPOS FISCAIS (acesso direto) ===")
    
    # Tentar acessar campos conhecidos diretamente
    try:
        debug_info.append(f"l10n_br_cfop_id: {record.l10n_br_cfop_id}")
    except Exception as e:
        debug_info.append("l10n_br_cfop_id: ERRO ou não existe")
    
    try:
        debug_info.append(f"l10n_br_cfop_codigo: {record.l10n_br_cfop_codigo}")
    except Exception as e:
        debug_info.append("l10n_br_cfop_codigo: ERRO ou não existe")
    
    try:
        debug_info.append(f"l10n_br_mensagem_fiscal_ids: {record.l10n_br_mensagem_fiscal_ids}")
    except Exception as e:
        debug_info.append("l10n_br_mensagem_fiscal_ids: ERRO ou não existe")
    
    # 4. Cliente e Posição Fiscal
    debug_info.append("\n=== CLIENTE E POSIÇÃO FISCAL ===")
    if record.order_id and record.order_id.partner_id:
        partner = record.order_id.partner_id
        fiscal_pos = partner.property_account_position_id
        debug_info.append(f"Cliente: {partner.name}")
        debug_info.append(f"Cliente ID: {partner.id}")
        
        try:
            debug_info.append(f"CNPJ: {partner.l10n_br_cnpj}")
        except Exception as e:
            debug_info.append("CNPJ: campo não existe ou erro")
        
        debug_info.append(f"Posição Fiscal: {fiscal_pos.name if fiscal_pos else 'SEM POSIÇÃO FISCAL'}")
        debug_info.append(f"Posição Fiscal ID: {fiscal_pos.id if fiscal_pos else 'N/A'}")
        debug_info.append(f"Estado Cliente: {partner.state_id.code if partner.state_id else 'N/A'}")
        debug_info.append(f"Cidade Cliente: {partner.city or 'N/A'}")
    
    # 5. Empresa
    debug_info.append("\n=== EMPRESA ===")
    if record.order_id:
        company = record.order_id.company_id
        debug_info.append(f"Empresa: {company.name if company else 'N/A'}")
        debug_info.append(f"Empresa ID: {company.id if company else 'N/A'}")
        debug_info.append(f"Estado Empresa: {company.state_id.code if company and company.state_id else 'N/A'}")
    
    # 6. Posição Fiscal do Pedido
    debug_info.append("\n=== POSIÇÃO FISCAL DO PEDIDO ===")
    if record.order_id:
        try:
            order_fiscal_pos = record.order_id.fiscal_position_id
            debug_info.append(f"Posição Fiscal Pedido: {order_fiscal_pos.name if order_fiscal_pos else 'VAZIO'}")
            debug_info.append(f"Posição Fiscal ID: {order_fiscal_pos.id if order_fiscal_pos else 'N/A'}")
        except Exception as e:
            debug_info.append("Erro ao acessar fiscal_position_id do pedido")
    
    # 7. Testar campos de operação fiscal conhecidos
    debug_info.append("\n=== CAMPOS DE OPERAÇÃO FISCAL (teste direto) ===")
    
    # fiscal_operation_id
    try:
        val = record.fiscal_operation_id
        debug_info.append(f"✅ fiscal_operation_id: {val.name if val else 'Vazio'} (ID: {val.id if val else 'N/A'})")
    except Exception as e:
        debug_info.append("❌ fiscal_operation_id: não existe")
    
    # fiscal_operation_line_id
    try:
        val = record.fiscal_operation_line_id
        debug_info.append(f"✅ fiscal_operation_line_id: {val.name if val else 'Vazio'} (ID: {val.id if val else 'N/A'})")
    except Exception as e:
        debug_info.append("❌ fiscal_operation_line_id: não existe")
    
    # l10n_br_fiscal_operation_id
    try:
        val = record.l10n_br_fiscal_operation_id
        debug_info.append(f"✅ l10n_br_fiscal_operation_id: {val.name if val else 'Vazio'} (ID: {val.id if val else 'N/A'})")
    except Exception as e:
        debug_info.append("❌ l10n_br_fiscal_operation_id: não existe")
    
    # l10n_br_fiscal_operation_line_id
    try:
        val = record.l10n_br_fiscal_operation_line_id
        debug_info.append(f"✅ l10n_br_fiscal_operation_line_id: {val.name if val else 'Vazio'} (ID: {val.id if val else 'N/A'})")
    except Exception as e:
        debug_info.append("❌ l10n_br_fiscal_operation_line_id: não existe")
    
    # 8. Listar campos disponíveis via _fields
    debug_info.append("\n=== CAMPOS DO MODELO (via _fields) ===")
    debug_info.append("Campos com 'fiscal', 'cfop' ou 'l10n_br':")
    count = 0
    for field_name in sorted(record._fields.keys()):
        if count >= 30:
            break
        if any(keyword in field_name.lower() for keyword in ['fiscal', 'cfop', 'l10n_br', 'operation']):
            field = record._fields[field_name]
            field_type = field.type if field else 'unknown'
            debug_info.append(f"  - {field_name} (tipo: {field_type})")
            count += 1
    
    # 9. Verificar estrutura dos campos CFOP
    debug_info.append("\n=== ESTRUTURA DOS CAMPOS CFOP ===")
    if 'l10n_br_cfop_id' in record._fields:
        field = record._fields['l10n_br_cfop_id']
        debug_info.append(f"l10n_br_cfop_id:")
        debug_info.append(f"  Tipo: {field.type}")
        try:
            debug_info.append(f"  String: {field.string}")
        except Exception as e:
            pass
    
    if 'l10n_br_cfop_codigo' in record._fields:
        field = record._fields['l10n_br_cfop_codigo']
        debug_info.append(f"l10n_br_cfop_codigo:")
        debug_info.append(f"  Tipo: {field.type}")
        try:
            debug_info.append(f"  String: {field.string}")
        except Exception as e:
            pass
    
    # 10. Tentar executar onchange
    debug_info.append("\n=== TENTATIVA DE ONCHANGE ===")
    try:
        if record.order_id:
            # Tentar chamar o método diretamente
            record.order_id.onchange_l10n_br_calcular_imposto()
            debug_info.append("✅ onchange_l10n_br_calcular_imposto executado!")
            # Não usar invalidate_cache - não existe no contexto restrito
            debug_info.append(f"CFOP após: {record.l10n_br_cfop_codigo or 'AINDA VAZIO'}")
    except Exception as e:
        debug_info.append(f"❌ Erro ou método não existe: {str(e)[:100]}")
    
    debug_info.append("\n" + "="*60)

# Mostrar resultado como UserError
raise UserError('\n'.join(debug_info))