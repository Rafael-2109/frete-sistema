# Server Action 1955 - Debug CFOP para Odoo
# COPIE E COLE este código no campo "Python Code" da Server Action
# Model: sale.order.line

# Coletar informações de debug
debug_info = []

for record in records:
    debug_info.append("="*60)
    debug_info.append("CFOP DEBUG - Server Action 1955")
    debug_info.append("="*60)
    
    # 1. Informações básicas
    debug_info.append(f"Linha ID: {record.id}")
    debug_info.append(f"Produto: {record.product_id.name if record.product_id else 'SEM PRODUTO'}")
    debug_info.append(f"Pedido: {record.order_id.name if record.order_id else 'SEM PEDIDO'}")
    
    # 2. Campos CFOP atuais
    debug_info.append(f"CFOP ID atual: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'VAZIO'}")
    debug_info.append(f"CFOP Código atual: {record.l10n_br_cfop_codigo or 'VAZIO'}")
    
    # 3. Verificar campos fiscais disponíveis
    debug_info.append("\nCampos fiscais encontrados:")
    campo_count = 0
    for field_name in record._fields:
        if campo_count >= 15:  # Limitar para não ficar muito grande
            break
        if 'fiscal' in field_name.lower() or 'cfop' in field_name.lower() or 'l10n_br' in field_name.lower():
            try:
                value = getattr(record, field_name, None)
                # Simplificar valor para não quebrar o debug
                if value and hasattr(value, 'id'):
                    value = f"ID: {value.id}"
                elif value and hasattr(value, '__len__') and len(str(value)) > 50:
                    value = str(value)[:50] + "..."
                debug_info.append(f"  - {field_name}: {value}")
                campo_count += 1
            except:
                debug_info.append(f"  - {field_name}: ERRO AO LER")
                campo_count += 1
    
    # 4. Verificar posição fiscal
    if record.order_id and record.order_id.partner_id:
        partner = record.order_id.partner_id
        fiscal_pos = partner.property_account_position_id
        debug_info.append(f"\nCliente: {partner.name}")
        debug_info.append(f"CNPJ: {getattr(partner, 'l10n_br_cnpj', 'N/A')}")
        debug_info.append(f"Posição Fiscal: {fiscal_pos.name if fiscal_pos else 'SEM POSIÇÃO FISCAL'}")
        debug_info.append(f"Estado Cliente: {partner.state_id.code if partner.state_id else 'N/A'}")
        debug_info.append(f"Cidade Cliente: {partner.city if partner.city else 'N/A'}")
    
    # 5. Verificar empresa
    if record.order_id:
        company = record.order_id.company_id
        debug_info.append(f"\nEmpresa: {company.name if company else 'N/A'}")
        debug_info.append(f"Estado Empresa: {company.state_id.code if company and company.state_id else 'N/A'}")
    
    # 6. Tentar executar método de cálculo de impostos
    debug_info.append("\nTentando executar onchange_l10n_br_calcular_imposto...")
    try:
        if record.order_id:
            record.order_id.onchange_l10n_br_calcular_imposto()
            debug_info.append("✅ Método executado!")
            debug_info.append(f"CFOP após cálculo: {record.l10n_br_cfop_codigo or 'AINDA VAZIO'}")
    except AttributeError:
        debug_info.append("❌ Método onchange_l10n_br_calcular_imposto não existe")
    except Exception as e:
        debug_info.append(f"❌ Erro: {str(e)[:100]}")
    
    # 7. Verificar campos de operação fiscal
    debug_info.append("\nVerificando campos de operação fiscal:")
    for field_name in ['fiscal_operation_id', 'fiscal_operation_line_id', 
                       'l10n_br_fiscal_operation_id', 'l10n_br_fiscal_operation_line_id']:
        try:
            if hasattr(record, field_name):
                value = getattr(record, field_name)
                debug_info.append(f"  ✅ {field_name}: {value}")
            else:
                debug_info.append(f"  ❌ {field_name}: não existe")
        except:
            debug_info.append(f"  ❌ {field_name}: erro ao acessar")
    
    debug_info.append("="*60)
    debug_info.append("FIM DO DEBUG CFOP")
    debug_info.append("="*60)

# Mostrar resultado como erro (para aparecer na tela)
# NOTA: Isso vai PARAR a execução e mostrar o debug
# Se quiser que continue, comente a linha abaixo
raise UserError('\n'.join(debug_info))