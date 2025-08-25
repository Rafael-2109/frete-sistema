# Server Action SEGURA - Apenas DESCOBRIR métodos (NÃO EXECUTA)
# Model: sale.order.line
# Esta action apenas LISTA métodos, não executa nenhum

debug_info = []

for record in records:
    debug_info.append("="*60)
    debug_info.append("DESCOBERTA SEGURA DE MÉTODOS - APENAS LISTAGEM")
    debug_info.append("="*60)
    
    # 1. Informações do registro
    debug_info.append(f"\nLinha ID: {record.id}")
    debug_info.append(f"Produto: {record.product_id.name if record.product_id else 'N/A'}")
    
    # 2. APENAS LISTAR métodos relacionados a CFOP/fiscal
    debug_info.append("\n=== MÉTODOS DISPONÍVEIS (NÃO EXECUTADOS) ===")
    
    metodos_encontrados = {
        'onchange': [],
        'compute': [],
        'fiscal': [],
        'outros': []
    }
    
    # Descobrir métodos SEM executar
    for attr_name in dir(record):
        try:
            attr = getattr(record, attr_name, None)
            if callable(attr) and not attr_name.startswith('__'):
                # Classificar método por tipo
                if 'onchange' in attr_name.lower():
                    metodos_encontrados['onchange'].append(attr_name)
                elif '_compute_' in attr_name.lower():
                    metodos_encontrados['compute'].append(attr_name)
                elif any(keyword in attr_name.lower() for keyword in ['fiscal', 'cfop', 'tax', 'l10n_br']):
                    metodos_encontrados['fiscal'].append(attr_name)
                elif attr_name.startswith('_'):
                    # Métodos privados que podem ser relevantes
                    if any(keyword in attr_name.lower() for keyword in ['product', 'price', 'amount']):
                        metodos_encontrados['outros'].append(attr_name)
        except:
            pass
    
    # Mostrar métodos encontrados
    debug_info.append("\nMétodos ONCHANGE (disparam ao mudar campos):")
    for metodo in metodos_encontrados['onchange'][:10]:
        debug_info.append(f"  - {metodo}")
    
    debug_info.append("\nMétodos COMPUTE (calculam campos):")
    for metodo in metodos_encontrados['compute'][:10]:
        debug_info.append(f"  - {metodo}")
    
    debug_info.append("\nMétodos FISCAIS (relacionados a impostos/CFOP):")
    for metodo in metodos_encontrados['fiscal'][:10]:
        debug_info.append(f"  - {metodo}")
    
    # 3. Verificar campos computed
    debug_info.append("\n=== CAMPOS COMPUTED/RELATED ===")
    for field_name in ['l10n_br_cfop_id', 'l10n_br_cfop_codigo', 'tax_id']:
        if field_name in record._fields:
            field = record._fields[field_name]
            debug_info.append(f"\n{field_name}:")
            if hasattr(field, 'compute') and field.compute:
                debug_info.append(f"  Compute: {field.compute}")
            if hasattr(field, 'related') and field.related:
                debug_info.append(f"  Related: {field.related}")
            if hasattr(field, 'depends') and field.depends:
                debug_info.append(f"  Depends: {field.depends[:5]}")  # Primeiros 5
    
    debug_info.append("\n" + "="*60)
    debug_info.append("DESCOBERTA CONCLUÍDA - NENHUM MÉTODO FOI EXECUTADO")

raise UserError('\n'.join(debug_info))