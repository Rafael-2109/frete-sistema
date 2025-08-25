# Server Action 1955 - Debug CFOP Final
# Copie este código para o campo "Python Code" da Server Action
# Model: sale.order.line

# Variáveis já disponíveis no Odoo:
# - _logger: para logs
# - records: registros selecionados
# - UserError: para mostrar erros
# - env: ambiente do Odoo

for record in records:
    _logger.info("="*60)
    _logger.info("CFOP DEBUG - Server Action 1955")
    _logger.info("="*60)
    
    # 1. Informações básicas
    _logger.info(f"Linha ID: {record.id}")
    _logger.info(f"Produto: {record.product_id.name if record.product_id else 'SEM PRODUTO'}")
    _logger.info(f"Pedido: {record.order_id.name if record.order_id else 'SEM PEDIDO'}")
    
    # 2. Campos CFOP atuais
    _logger.info(f"CFOP ID atual: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'VAZIO'}")
    _logger.info(f"CFOP Código atual: {record.l10n_br_cfop_codigo or 'VAZIO'}")
    
    # 3. Verificar campos fiscais disponíveis
    _logger.info("Campos fiscais encontrados:")
    campo_count = 0
    for field_name in record._fields:
        if campo_count >= 20:  # Mostrar até 20 campos
            break
        if 'fiscal' in field_name.lower() or 'cfop' in field_name.lower() or 'l10n_br' in field_name.lower():
            try:
                value = getattr(record, field_name, None)
                # Simplificar valores para log
                if value and hasattr(value, 'id'):
                    value = f"ID: {value.id}"
                elif value and hasattr(value, 'ids'):
                    value = f"IDs: {value.ids}"
                elif value and len(str(value)) > 100:
                    value = str(value)[:100] + "..."
                _logger.info(f"  - {field_name}: {value}")
                campo_count += 1
            except Exception as e:
                _logger.info(f"  - {field_name}: ERRO - {str(e)[:50]}")
                campo_count += 1
    
    # 4. Verificar posição fiscal
    if record.order_id and record.order_id.partner_id:
        partner = record.order_id.partner_id
        fiscal_pos = partner.property_account_position_id
        _logger.info(f"Cliente: {partner.name}")
        _logger.info(f"CNPJ: {getattr(partner, 'l10n_br_cnpj', 'Campo não existe')}")
        _logger.info(f"Posição Fiscal: {fiscal_pos.name if fiscal_pos else 'SEM POSIÇÃO FISCAL'}")
        _logger.info(f"Estado Cliente: {partner.state_id.code if partner.state_id else 'N/A'}")
        _logger.info(f"Cidade Cliente: {partner.city or 'N/A'}")
    
    # 5. Verificar empresa
    if record.order_id:
        company = record.order_id.company_id
        _logger.info(f"Empresa: {company.name if company else 'N/A'}")
        _logger.info(f"Estado Empresa: {company.state_id.code if company and company.state_id else 'N/A'}")
    
    # 6. Verificar campos de operação fiscal específicos
    _logger.info("Verificando campos de operação fiscal:")
    campos_operacao = [
        'fiscal_operation_id',
        'fiscal_operation_line_id', 
        'l10n_br_fiscal_operation_id',
        'l10n_br_fiscal_operation_line_id',
        'fiscal_position_id',
        'l10n_br_operacao_consumidor',
        'l10n_br_tipo_operacao'
    ]
    
    for field_name in campos_operacao:
        try:
            if hasattr(record, field_name):
                value = getattr(record, field_name)
                if value:
                    _logger.info(f"  ✅ {field_name}: {value}")
                else:
                    _logger.info(f"  ⚠️ {field_name}: existe mas está vazio")
            else:
                _logger.info(f"  ❌ {field_name}: campo não existe")
        except Exception as e:
            _logger.info(f"  ❌ {field_name}: erro - {str(e)[:50]}")
    
    # 7. Tentar executar método de cálculo de impostos
    _logger.info("Tentando executar onchange_l10n_br_calcular_imposto...")
    try:
        if record.order_id and hasattr(record.order_id, 'onchange_l10n_br_calcular_imposto'):
            record.order_id.onchange_l10n_br_calcular_imposto()
            _logger.info("✅ Método onchange_l10n_br_calcular_imposto executado!")
            
            # Recarregar registro para ver mudanças
            record.invalidate_cache()
            _logger.info(f"CFOP após cálculo: {record.l10n_br_cfop_codigo or 'AINDA VAZIO'}")
            _logger.info(f"CFOP ID após cálculo: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'AINDA VAZIO'}")
        else:
            _logger.info("❌ Método onchange_l10n_br_calcular_imposto não existe no pedido")
    except Exception as e:
        _logger.error(f"❌ Erro ao executar método: {str(e)}")
    
    # 8. Listar métodos disponíveis relacionados
    _logger.info("Buscando métodos relacionados a CFOP/fiscal:")
    method_count = 0
    try:
        for attr_name in dir(record):
            if method_count >= 15:
                break
            if any(keyword in attr_name.lower() for keyword in ['cfop', 'fiscal', 'compute', 'onchange']):
                try:
                    attr = getattr(record, attr_name)
                    if callable(attr):
                        _logger.info(f"  - {attr_name} (método)")
                        method_count += 1
                except:
                    pass
    except Exception as e:
        _logger.error(f"Erro ao listar métodos: {str(e)}")
    
    # 9. Verificar se há compute fields
    _logger.info("Verificando campos computed:")
    for field_name, field in record._fields.items():
        if 'cfop' in field_name.lower() or 'fiscal' in field_name.lower():
            if hasattr(field, 'compute') and field.compute:
                _logger.info(f"  - {field_name} tem compute: {field.compute}")
            if hasattr(field, 'related') and field.related:
                _logger.info(f"  - {field_name} é related: {field.related}")
    
    _logger.info("="*60)
    _logger.info("FIM DO DEBUG CFOP")
    _logger.info("="*60)

# Log final
_logger.info(f"Debug executado para {len(records)} linha(s)")

# Se quiser ver o resultado como popup (vai parar a execução):
# raise UserError(f"Debug executado! Verifique os logs do servidor para detalhes.")