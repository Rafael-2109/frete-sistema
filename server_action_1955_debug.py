# Server Action 1955 - Debug Aprimorado para CFOP
# Código para copiar e colar no Odoo (sem import, sem hasattr)
# Contexto: sale.order.line

# No Odoo, o logger já está disponível como env.logger ou usar raise UserError para debug

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
    fiscal_fields = []
    for field_name in record._fields:
        if 'fiscal' in field_name.lower() or 'cfop' in field_name.lower() or 'l10n_br' in field_name.lower():
            try:
                value = getattr(record, field_name, None)
                fiscal_fields.append(f"{field_name}: {value}")
            except Exception as e:
                fiscal_fields.append(f"{field_name}: ERRO AO LER")
    
    _logger.info("Campos fiscais encontrados:")
    for field in fiscal_fields[:15]:  # Aumentei para 15 para ver mais campos
        _logger.info(f"  - {field}")
    
    # 4. Verificar posição fiscal
    if record.order_id and record.order_id.partner_id:
        partner = record.order_id.partner_id
        fiscal_pos = partner.property_account_position_id
        _logger.info(f"Cliente: {partner.name}")
        _logger.info(f"CNPJ: {partner.l10n_br_cnpj if partner.l10n_br_cnpj else 'N/A'}")
        _logger.info(f"Posição Fiscal: {fiscal_pos.name if fiscal_pos else 'SEM POSIÇÃO FISCAL'}")
        _logger.info(f"Estado Cliente: {partner.state_id.code if partner.state_id else 'N/A'}")
        _logger.info(f"Cidade Cliente: {partner.city if partner.city else 'N/A'}")
    
    # 5. Verificar empresa
    if record.order_id:
        company = record.order_id.company_id
        _logger.info(f"Empresa: {company.name if company else 'N/A'}")
        _logger.info(f"Estado Empresa: {company.state_id.code if company and company.state_id else 'N/A'}")
    
    # 6. Tentar executar método de cálculo de impostos
    try:
        # Verificar se o método existe tentando executá-lo
        _logger.info("Tentando executar onchange_l10n_br_calcular_imposto...")
        if record.order_id:
            try:
                record.order_id.onchange_l10n_br_calcular_imposto()
                _logger.info("✅ Método onchange_l10n_br_calcular_imposto executado!")
                
                # Recarregar o record para ver mudanças
                record.refresh()
                _logger.info(f"CFOP após cálculo: {record.l10n_br_cfop_codigo or 'AINDA VAZIO'}")
                _logger.info(f"CFOP ID após cálculo: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'AINDA VAZIO'}")
            except AttributeError:
                _logger.info("❌ Método onchange_l10n_br_calcular_imposto não existe")
            except Exception as e:
                _logger.error(f"❌ Erro ao executar método: {str(e)}")
    except Exception as e:
        _logger.error(f"Erro geral: {str(e)}")
    
    # 7. Listar métodos disponíveis relacionados a fiscal/cfop
    _logger.info("Buscando métodos relacionados a fiscal/cfop...")
    methods = []
    try:
        for attr_name in dir(record):
            if 'fiscal' in attr_name.lower() or 'cfop' in attr_name.lower() or 'compute' in attr_name.lower() or 'onchange' in attr_name.lower():
                try:
                    attr = getattr(record, attr_name)
                    if callable(attr):
                        methods.append(attr_name)
                except Exception as e:
                    pass
    except Exception as e:
        _logger.error(f"Erro ao listar métodos: {str(e)}")
    
    if methods:
        _logger.info(f"Métodos encontrados ({len(methods)}):")
        for method in methods[:20]:  # Mostrar até 20 métodos
            _logger.info(f"  - {method}")
    else:
        _logger.info("Nenhum método fiscal/cfop/compute/onchange encontrado")
    
    # 8. Verificar se existe campo fiscal_operation_id ou fiscal_operation_line_id
    _logger.info("Verificando campos de operação fiscal...")
    for field_name in ['fiscal_operation_id', 'fiscal_operation_line_id', 'l10n_br_fiscal_operation_id', 'l10n_br_fiscal_operation_line_id']:
        try:
            value = getattr(record, field_name, 'CAMPO NÃO EXISTE')
            if value != 'CAMPO NÃO EXISTE':
                _logger.info(f"  ✅ {field_name}: {value}")
        except Exception as e:
            _logger.info(f"  ❌ {field_name}: não existe ou erro ao acessar")
    
    # 9. Tentar forçar recálculo de campos
    _logger.info("Tentando forçar recálculo...")
    try:
        # Tentar invalidar cache para forçar recálculo
        record.invalidate_cache()
        _logger.info("Cache invalidado")
        
        # Tentar recomputar campos
        try:
            record.recompute()
            _logger.info("Recompute executado")
        except Exception as e:
            _logger.info("Recompute não disponível ou falhou")
            
        # Verificar CFOP novamente
        _logger.info(f"CFOP após invalidação: {record.l10n_br_cfop_codigo or 'AINDA VAZIO'}")
    except Exception as e:
        _logger.error(f"Erro ao forçar recálculo: {str(e)}")
    
    _logger.info("="*60)
    _logger.info("FIM DO DEBUG CFOP")
    _logger.info("="*60)