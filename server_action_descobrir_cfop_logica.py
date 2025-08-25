# Server Action para Descobrir a Lógica de CFOP
# Model: sale.order.line
# Copie este código para uma Server Action e execute em uma linha de pedido

debug_info = []

for record in records:
    debug_info.append("="*60)
    debug_info.append("DESCOBRINDO LÓGICA DE CFOP - PRODUTO + REGIÃO")
    debug_info.append("="*60)
    
    # 1. Dados do Contexto
    debug_info.append("\n=== CONTEXTO ATUAL ===")
    debug_info.append(f"Linha ID: {record.id}")
    debug_info.append(f"Produto: {record.product_id.name if record.product_id else 'N/A'}")
    debug_info.append(f"Pedido: {record.order_id.name if record.order_id else 'N/A'}")
    
    # 2. Produto - Campos Fiscais
    debug_info.append("\n=== PRODUTO - CAMPOS FISCAIS ===")
    if record.product_id:
        produto = record.product_id
        
        # NCM e origem
        try:
            debug_info.append(f"NCM: {produto.l10n_br_ncm_id.name if produto.l10n_br_ncm_id else 'N/A'}")
        except:
            debug_info.append("NCM: campo não existe")
            
        try:
            debug_info.append(f"Origem: {produto.l10n_br_origin or 'N/A'}")
        except:
            debug_info.append("Origem: campo não existe")
        
        # Categoria fiscal
        try:
            debug_info.append(f"Categ Fiscal: {produto.categ_id.name if produto.categ_id else 'N/A'}")
        except:
            pass
            
        # Tipo fiscal
        try:
            debug_info.append(f"Tipo Fiscal: {produto.l10n_br_fiscal_type or 'N/A'}")
        except:
            debug_info.append("Tipo Fiscal: campo não existe")
    
    # 3. Cliente - Localização
    debug_info.append("\n=== CLIENTE - LOCALIZAÇÃO ===")
    if record.order_id and record.order_id.partner_id:
        cliente = record.order_id.partner_id
        debug_info.append(f"Cliente: {cliente.name}")
        debug_info.append(f"Estado: {cliente.state_id.name if cliente.state_id else 'N/A'}")
        debug_info.append(f"UF: {cliente.state_id.code if cliente.state_id else 'N/A'}")
        debug_info.append(f"País: {cliente.country_id.name if cliente.country_id else 'N/A'}")
        
        # Verificar se é Zona Franca
        try:
            debug_info.append(f"CEP: {cliente.zip or 'N/A'}")
            if cliente.zip and cliente.zip.startswith('69'):
                debug_info.append("⚠️ POSSÍVEL ZONA FRANCA DE MANAUS")
        except:
            pass
    
    # 4. Empresa - Localização
    debug_info.append("\n=== EMPRESA - LOCALIZAÇÃO ===")
    if record.order_id:
        empresa = record.order_id.company_id
        debug_info.append(f"Empresa: {empresa.name if empresa else 'N/A'}")
        try:
            debug_info.append(f"Estado Empresa: {empresa.state_id.name if empresa.state_id else 'N/A'}")
            debug_info.append(f"UF Empresa: {empresa.state_id.code if empresa.state_id else 'N/A'}")
        except:
            debug_info.append("Estado Empresa: não disponível")
    
    # 5. Posição Fiscal
    debug_info.append("\n=== POSIÇÃO FISCAL APLICADA ===")
    try:
        # Da ordem
        fp_order = record.order_id.fiscal_position_id
        debug_info.append(f"Posição Fiscal (Pedido): {fp_order.name if fp_order else 'N/A'}")
        
        # Do cliente
        fp_partner = record.order_id.partner_id.property_account_position_id
        debug_info.append(f"Posição Fiscal (Cliente): {fp_partner.name if fp_partner else 'N/A'}")
    except:
        debug_info.append("Erro ao buscar posição fiscal")
    
    # 6. CFOP Atual
    debug_info.append("\n=== CFOP DETERMINADO ===")
    debug_info.append(f"CFOP ID: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'VAZIO'}")
    debug_info.append(f"CFOP Código: {record.l10n_br_cfop_codigo or 'VAZIO'}")
    if record.l10n_br_cfop_id:
        cfop = record.l10n_br_cfop_id
        debug_info.append(f"CFOP Nome: {cfop.name if cfop else 'N/A'}")
        try:
            debug_info.append(f"CFOP Descrição: {cfop.descricao[:50] if cfop.descricao else 'N/A'}...")
        except:
            pass
    
    # 7. Buscar Mapeamentos de CFOP
    debug_info.append("\n=== MAPEAMENTOS DE CFOP (Fiscal Position) ===")
    if fp_order:
        try:
            # Tentar buscar mapeamentos desta posição fiscal
            debug_info.append(f"Buscando mapeamentos para: {fp_order.name}")
            
            # Verificar campos da posição fiscal
            for campo in fp_order._fields:
                if 'cfop' in campo.lower():
                    valor = getattr(fp_order, campo, None)
                    debug_info.append(f"  {campo}: {valor}")
        except Exception as e:
            debug_info.append(f"Erro ao buscar mapeamentos: {str(e)[:50]}")
    
    # 8. Análise de Operação
    debug_info.append("\n=== TIPO DE OPERAÇÃO ===")
    
    # Verificar se é transferência entre filiais
    if empresa and cliente:
        try:
            # Se cliente e empresa têm mesmo CNPJ raiz
            if hasattr(cliente, 'l10n_br_cnpj') and hasattr(empresa, 'l10n_br_cnpj'):
                cnpj_cliente = cliente.l10n_br_cnpj or ''
                cnpj_empresa = empresa.l10n_br_cnpj or ''
                if cnpj_cliente[:8] == cnpj_empresa[:8] and cnpj_cliente and cnpj_empresa:
                    debug_info.append("✅ TRANSFERÊNCIA ENTRE FILIAIS (mesmo CNPJ raiz)")
                else:
                    debug_info.append("❌ VENDA NORMAL (CNPJs diferentes)")
        except:
            pass
    
    # Estados iguais ou diferentes
    try:
        if empresa.state_id and cliente.state_id:
            if empresa.state_id.id == cliente.state_id.id:
                debug_info.append("📍 OPERAÇÃO INTRAESTADUAL (mesmo estado)")
            else:
                debug_info.append("🚛 OPERAÇÃO INTERESTADUAL (estados diferentes)")
    except:
        pass
    
    # 9. Tentar descobrir método de cálculo
    debug_info.append("\n=== MÉTODOS DE CÁLCULO DISPONÍVEIS ===")
    metodos_cfop = []
    for attr in dir(record):
        if 'cfop' in attr.lower() and callable(getattr(record, attr, None)):
            metodos_cfop.append(attr)
    
    if metodos_cfop:
        debug_info.append(f"Métodos com 'cfop': {', '.join(metodos_cfop[:5])}")
    else:
        debug_info.append("Nenhum método direto de CFOP encontrado")
    
    # 10. Resumo da Lógica
    debug_info.append("\n=== RESUMO DA LÓGICA DESCOBERTA ===")
    debug_info.append("CFOP é determinado por:")
    debug_info.append("1. Tipo de Produto (NCM, origem, categoria)")
    debug_info.append("2. Localização Cliente (estado, país, zona franca)")
    debug_info.append("3. Localização Empresa (estado de origem)")
    debug_info.append("4. Tipo de Operação (venda, transferência)")
    debug_info.append("5. Posição Fiscal aplicada (regras e mapeamentos)")
    
    debug_info.append("\n" + "="*60)

# Mostrar resultado
raise UserError('\n'.join(debug_info))