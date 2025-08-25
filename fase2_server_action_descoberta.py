# ============================================================================
# SERVER ACTION - FASE 2: DESCOBERTA SEGURA DE MÉTODOS
# Model: sale.order.line
# 
# COMO USAR:
# 1. No Odoo, vá em: Settings → Technical → Server Actions
# 2. Crie uma nova Server Action
# 3. Name: "Descoberta CFOP - Segura"
# 4. Model: sale.order.line
# 5. Action Type: Execute Python Code
# 6. Cole este código abaixo
# 7. Salve
# 8. Execute no registro da linha do pedido teste (use o LINHA_ID da FASE 1)
# ============================================================================

debug_info = []
debug_info.append("="*60)
debug_info.append("DESCOBERTA SEGURA DE MÉTODOS PARA CFOP")
debug_info.append("NÃO EXECUTA NENHUM MÉTODO - APENAS LISTA")
debug_info.append("="*60)

for record in records:
    # ========================================================================
    # 1. INFORMAÇÕES DO REGISTRO
    # ========================================================================
    debug_info.append(f"\n📍 ANÁLISE DA LINHA ID: {record.id}")
    debug_info.append(f"Produto: {record.product_id.name if record.product_id else 'N/A'}")
    debug_info.append(f"Pedido: {record.order_id.name if record.order_id else 'N/A'}")
    
    # Estado atual do CFOP
    debug_info.append(f"\nESTADO ATUAL:")
    debug_info.append(f"  CFOP Código: '{record.l10n_br_cfop_codigo or ''}' {'(VAZIO)' if not record.l10n_br_cfop_codigo else ''}")
    debug_info.append(f"  CFOP ID: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'False (VAZIO)'}")
    debug_info.append(f"  Impostos: {len(record.tax_id)} impostos")
    
    # ========================================================================
    # 2. DESCOBRIR MÉTODOS DISPONÍVEIS (SEM EXECUTAR)
    # ========================================================================
    debug_info.append("\n" + "="*40)
    debug_info.append("MÉTODOS DESCOBERTOS (NÃO EXECUTADOS)")
    debug_info.append("="*40)
    
    # Categorizar métodos
    metodos = {
        'onchange': [],
        'compute': [],
        'fiscal': [],
        'product': [],
        'privados_seguros': [],
        'perigosos': []
    }
    
    # Lista de palavras que indicam métodos perigosos
    PALAVRAS_PERIGOSAS = [
        'unlink', 'delete', 'remove', 'cancel', 'purge', 
        'cleanup', 'reset', 'clear', 'destroy', 'drop', 'truncate'
    ]
    
    # Descobrir todos os métodos
    todos_metodos = []
    for attr_name in dir(record):
        if not attr_name.startswith('__'):
            try:
                attr = getattr(record, attr_name, None)
                if callable(attr):
                    todos_metodos.append(attr_name)
                    
                    # Verificar se é perigoso
                    if any(perigo in attr_name.lower() for perigo in PALAVRAS_PERIGOSAS):
                        metodos['perigosos'].append(attr_name)
                        continue
                    
                    # Categorizar por tipo
                    nome_lower = attr_name.lower()
                    
                    if 'onchange' in nome_lower:
                        metodos['onchange'].append(attr_name)
                    elif '_compute_' in nome_lower or 'compute' in nome_lower:
                        metodos['compute'].append(attr_name)
                    elif any(k in nome_lower for k in ['fiscal', 'cfop', 'tax', 'l10n_br', 'imposto']):
                        metodos['fiscal'].append(attr_name)
                    elif 'product' in nome_lower:
                        metodos['product'].append(attr_name)
                    elif attr_name.startswith('_') and attr_name not in metodos['perigosos']:
                        metodos['privados_seguros'].append(attr_name)
            except:
                pass
    
    # ========================================================================
    # 3. LISTAR MÉTODOS POR CATEGORIA
    # ========================================================================
    
    debug_info.append(f"\n✅ MÉTODOS ONCHANGE ({len(metodos['onchange'])} encontrados):")
    debug_info.append("   (Disparam quando campos mudam)")
    for m in metodos['onchange'][:10]:  # Máximo 10
        debug_info.append(f"   • {m}")
    if len(metodos['onchange']) > 10:
        debug_info.append(f"   ... e mais {len(metodos['onchange']) - 10} métodos")
    
    debug_info.append(f"\n✅ MÉTODOS COMPUTE ({len(metodos['compute'])} encontrados):")
    debug_info.append("   (Calculam valores de campos)")
    for m in metodos['compute'][:10]:
        debug_info.append(f"   • {m}")
    if len(metodos['compute']) > 10:
        debug_info.append(f"   ... e mais {len(metodos['compute']) - 10} métodos")
    
    debug_info.append(f"\n⭐ MÉTODOS FISCAIS/CFOP ({len(metodos['fiscal'])} encontrados):")
    debug_info.append("   (MAIS RELEVANTES PARA NOSSO TESTE)")
    for m in metodos['fiscal']:  # Listar todos os fiscais
        debug_info.append(f"   • {m}")
    
    debug_info.append(f"\n📦 MÉTODOS DE PRODUTO ({len(metodos['product'])} encontrados):")
    for m in metodos['product'][:10]:
        debug_info.append(f"   • {m}")
    
    debug_info.append(f"\n🔒 MÉTODOS PRIVADOS SEGUROS ({len(metodos['privados_seguros'])} encontrados):")
    for m in metodos['privados_seguros'][:5]:
        debug_info.append(f"   • {m}")
    
    debug_info.append(f"\n❌ MÉTODOS PERIGOSOS ({len(metodos['perigosos'])} encontrados):")
    debug_info.append("   NUNCA EXECUTE ESTES:")
    for m in metodos['perigosos']:
        debug_info.append(f"   ⛔ {m}")
    
    # ========================================================================
    # 4. ANALISAR ESTRUTURA DOS CAMPOS CFOP
    # ========================================================================
    debug_info.append("\n" + "="*40)
    debug_info.append("ESTRUTURA DOS CAMPOS CFOP")
    debug_info.append("="*40)
    
    # Analisar campo l10n_br_cfop_id
    if hasattr(record, '_fields') and 'l10n_br_cfop_id' in record._fields:
        field_cfop = record._fields['l10n_br_cfop_id']
        debug_info.append("\n📌 Campo: l10n_br_cfop_id")
        debug_info.append(f"  Tipo: {getattr(field_cfop, 'type', 'N/A')}")
        
        if hasattr(field_cfop, 'compute'):
            compute_method = getattr(field_cfop, 'compute', None)
            debug_info.append(f"  Computed: {'SIM' if compute_method else 'NÃO'}")
            if compute_method:
                debug_info.append(f"  Método compute: {compute_method}")
        
        if hasattr(field_cfop, 'related'):
            related = getattr(field_cfop, 'related', None)
            debug_info.append(f"  Related: {related if related else 'NÃO'}")
        
        if hasattr(field_cfop, 'depends'):
            depends = getattr(field_cfop, 'depends', None)
            if depends:
                debug_info.append(f"  Depends: {', '.join(list(depends)[:5])}")
    
    # Analisar campo l10n_br_cfop_codigo
    if hasattr(record, '_fields') and 'l10n_br_cfop_codigo' in record._fields:
        field_codigo = record._fields['l10n_br_cfop_codigo']
        debug_info.append("\n📌 Campo: l10n_br_cfop_codigo")
        debug_info.append(f"  Tipo: {getattr(field_codigo, 'type', 'N/A')}")
        
        if hasattr(field_codigo, 'related'):
            related = getattr(field_codigo, 'related', None)
            debug_info.append(f"  Related: {related if related else 'NÃO'}")
            if related:
                debug_info.append("  ⚠️ Este é um campo RELATED (depende de l10n_br_cfop_id)")
    
    # ========================================================================
    # 5. SUGESTÕES DE MÉTODOS PARA TESTAR
    # ========================================================================
    debug_info.append("\n" + "="*40)
    debug_info.append("🎯 SUGESTÃO DE MÉTODOS PARA TESTAR")
    debug_info.append("="*40)
    
    # Priorizar métodos mais promissores
    metodos_prioritarios = []
    
    # 1. Métodos com 'cfop' no nome
    for m in metodos['fiscal']:
        if 'cfop' in m.lower():
            metodos_prioritarios.append((m, "Alto - Contém 'cfop' no nome"))
    
    # 2. Métodos onchange do produto
    for m in metodos['onchange']:
        if 'product' in m.lower():
            metodos_prioritarios.append((m, "Alto - Onchange de produto"))
    
    # 3. Métodos compute fiscais
    for m in metodos['compute']:
        if any(k in m.lower() for k in ['fiscal', 'tax', 'l10n_br']):
            metodos_prioritarios.append((m, "Médio - Compute fiscal"))
    
    debug_info.append("\nMÉTODOS PRIORITÁRIOS PARA TESTE:")
    for metodo, razao in metodos_prioritarios[:10]:
        debug_info.append(f"  1. {metodo}")
        debug_info.append(f"     Razão: {razao}")
    
    # ========================================================================
    # 6. TOTAL DE MÉTODOS
    # ========================================================================
    debug_info.append("\n" + "="*40)
    debug_info.append(f"TOTAL DE MÉTODOS ENCONTRADOS: {len(todos_metodos)}")
    debug_info.append("="*40)

# Exibir resultado
debug_info.append("\n⚠️ NENHUM MÉTODO FOI EXECUTADO - APENAS LISTADOS")
debug_info.append("📋 COPIE ESTA LISTA PARA ANÁLISE")

raise UserError('\n'.join(debug_info))