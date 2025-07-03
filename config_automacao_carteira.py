# 🤖 CONFIGURAÇÕES DO SISTEMA DE AUTOMAÇÃO DA CARTEIRA
# Este arquivo contém todos os parâmetros configuráveis do sistema

# =============================================================================
# 🏢 CLIENTES ESTRATÉGICOS - AJUSTAR CONFORME SEU NEGÓCIO
# =============================================================================

# ⚠️ URGENTE: Substituir pelos CNPJs dos seus clientes TOP
# Formato: 'XX.XXX.XXX/' (primeiros 10 caracteres do CNPJ)
CLIENTES_ESTRATEGICOS = {
    '06.057.223/',  # Assai (exemplo)
    '75.315.333/',  # Atacadão (exemplo)
    '45.543.915/',  # Carrefour (exemplo)
    '01.157.555/',  # Tenda (exemplo)
    # TODO: Adicionar seus clientes reais aqui
    # 'XX.XXX.XXX/',  # Seu Cliente VIP 1
    # 'XX.XXX.XXX/',  # Seu Cliente VIP 2
    # 'XX.XXX.XXX/',  # Seu Cliente VIP 3
}

# =============================================================================
# 🚛 CAPACIDADES DOS VEÍCULOS - AJUSTAR CONFORME SUA FROTA
# =============================================================================

# ⚠️ URGENTE: Configurar conforme capacidades REAIS da sua frota
CAPACIDADES_VEICULOS = {
    'peso_maximo_padrao': 25000.0,      # KG - Capacidade máxima padrão
    'volume_maximo_padrao': 80.0,       # M³ - Volume máximo padrão
    'ocupacao_minima': 0.70,            # 70% - Ocupação mínima para viabilidade
    'ocupacao_ideal': 0.85,             # 85% - Ocupação ideal para otimização
    'max_paradas_rota': 8,              # Máximo de paradas por rota
    'tolerancia_peso': 0.05,            # 5% - Tolerância sobre peso máximo
    'priorizar_agendamentos': True,     # Priorizar itens com agendamento
}

# =============================================================================
# ⏰ PRAZOS E CLASSIFICAÇÃO DE URGÊNCIA
# =============================================================================

# ⚠️ REVISAR: Ajustar conforme sua operação
PRAZOS_URGENCIA = {
    'dias_critico': 7,          # ≤ 7 dias = CRÍTICO (vermelho)
    'dias_atencao': 15,         # 8-15 dias = ATENÇÃO (amarelo)
    # > 15 dias = NORMAL (verde)
    # sem data = SEM_PRAZO (cinza)
}

# ⚠️ REVISAR: Valores para classificação especial
VALORES_ESPECIAIS = {
    'valor_alto': 50000.0,      # R$ - Pedidos de alto valor
    'qtd_alta': 1000.0,         # Quantidades altas (unidades)
    'margem_seguranca_estoque': 0.10,  # 10% - Margem de segurança estoque
    'estoque_minimo': 1.0,      # Estoque mínimo considerado
}

# =============================================================================
# 📅 CONFIGURAÇÕES DE AGENDAMENTO
# =============================================================================

# ⚠️ REVISAR: Ajustar conforme horários de funcionamento
AGENDAMENTO_CONFIG = {
    'dias_antecedencia_min': 1,         # Mínimo 1 dia de antecedência
    'dias_antecedencia_max': 7,         # Máximo 7 dias de antecedência
    'max_entregas_por_dia': 50,         # Limite diário de entregas
    'prefixo_protocolo': 'AGD',         # Prefixo dos protocolos
    'dias_uteis_apenas': True,          # Trabalha apenas dias úteis?
    'horarios_preferenciais': [         # Horários de entrega
        '08:00-12:00',  # Manhã
        '13:00-17:00'   # Tarde
    ]
}

# Configurações específicas por tipo de cliente
CONFIG_TIPOS_CLIENTE = {
    'estrategico': {
        'prioridade': 1,
        'antecedencia_max': 3,      # Até 3 dias
        'slot_reservado': True,     # Reserva slots preferenciais
        'bonus_score': 20           # Bonus na priorização
    },
    'agendamento_obrigatorio': {
        'prioridade': 2,
        'antecedencia_max': 7,      # Até 7 dias
        'slot_reservado': False,
        'bonus_score': 10
    },
    'sem_agendamento': {
        'prioridade': 3,
        'antecedencia_max': 7,
        'slot_reservado': False,
        'bonus_score': 0
    }
}

# =============================================================================
# 📊 ANÁLISE DE ESTOQUE
# =============================================================================

ESTOQUE_CONFIG = {
    'projecao_maxima': 28,              # Análise até D+28
    'dias_alerta_ruptura': 3,           # Alertar rupturas em D+3
    'considerar_reposicao': True,       # Considerar reposição programada
    'priorizar_estoque_seguro': True,   # Priorizar itens com estoque seguro
}

# Situações de estoque e ações
SITUACOES_ESTOQUE = {
    'DISPONIVEL_SEGURO': {
        'acao': 'SEPARAR_IMEDIATAMENTE',
        'prioridade': 1,
        'cor': 'success'
    },
    'DISPONIVEL_LIMITADO': {
        'acao': 'SEPARAR_COM_PRIORIZACAO',
        'prioridade': 2,
        'cor': 'warning'
    },
    'AGUARDA_REPOSICAO_CURTA': {
        'acao': 'PROGRAMAR_EXPEDICAO',
        'prioridade': 3,
        'cor': 'info'
    },
    'AGUARDA_REPOSICAO_LONGA': {
        'acao': 'REAGENDAR_ENTREGA',
        'prioridade': 4,
        'cor': 'secondary'
    },
    'RUPTURA_CRITICA': {
        'acao': 'STANDBY_COMERCIAL',
        'prioridade': 5,
        'cor': 'danger'
    }
}

# =============================================================================
# 🔄 FORMAÇÃO DE CARGAS
# =============================================================================

# ⚠️ REVISAR: Motivos para cargas parciais conforme seu negócio
MOTIVOS_CARGA_PARCIAL = {
    'ESTOQUE_INSUFICIENTE': 'Estoque insuficiente para pedido completo',
    'CAPACIDADE_VEICULO': 'Capacidade não comporta pedido completo',
    'RESTRICAO_AGENDAMENTO': 'Restrição de agendamento impede total',
    'SEPARACAO_INCOMPLETA': 'Separação não finalizada completamente',
    'CANCELAMENTO_PARCIAL': 'Cancelamento de itens do pedido',
    'INCONSISTENCIA_FATURAMENTO': 'Inconsistência detectada no faturamento',
    'CLIENTE_SOLICITOU': 'Solicitação específica do cliente',
    'URGENCIA_ENTREGA': 'Urgência - embarque parcial necessário',
    'RESTRICAO_TRANSPORTE': 'Restrição específica de transporte',
    'PRODUTO_ESPECIAL': 'Produto com características especiais'
}

# Tipos de carga e suas características
TIPOS_CARGA = {
    'TOTAL': {
        'descricao': 'Carga completa do pedido',
        'ocupacao_minima': 0.70,
        'justificativa_obrigatoria': False,
        'cor': 'success'
    },
    'PARCIAL': {
        'descricao': 'Carga parcial do pedido',
        'ocupacao_minima': 0.60,
        'justificativa_obrigatoria': True,
        'cor': 'warning'
    },
    'FRACIONADA': {
        'descricao': 'Múltiplos embarques necessários',
        'ocupacao_minima': 0.50,
        'justificativa_obrigatoria': True,
        'cor': 'info'
    }
}

# =============================================================================
# 🎯 CLASSIFICAÇÃO E PRIORIZAÇÃO
# =============================================================================

# Scores base por urgência
SCORES_URGENCIA = {
    'CRITICO': 100,
    'ATENCAO': 70,
    'NORMAL': 50,
    'SEM_PRAZO': 30,
    'ERRO': 10
}

# Bonus por características
BONUS_CARACTERISTICAS = {
    'CLIENTE_ESTRATEGICO': 20,
    'ALTO_VALOR': 15,
    'ALTA_QUANTIDADE': 10,
    'COM_SEPARACAO': 10,
    'COM_PROTOCOLO': 5,
    'PRODUTO_ESPECIAL': 5,
    'AGENDAMENTO_NECESSARIO': 30,
    'ESTOQUE_SEGURO': 10
}

# Níveis de prioridade final
NIVEIS_PRIORIDADE = {
    'MAXIMA': {'min_score': 90, 'cor': 'danger'},
    'ALTA': {'min_score': 70, 'cor': 'warning'},
    'MEDIA': {'min_score': 50, 'cor': 'info'},
    'BAIXA': {'min_score': 0, 'cor': 'secondary'}
}

# =============================================================================
# 🚨 DETECÇÃO DE INCONSISTÊNCIAS
# =============================================================================

# Inconsistências críticas que impedem processamento
INCONSISTENCIAS_CRITICAS = {
    'QUANTIDADE_ZERADA': 'Quantidade do produto zerada ou negativa',
    'PRECO_ZERADO': 'Preço do produto zerado ou negativo',
    'CRITICO_SEM_DATA': 'Pedido crítico sem data de entrega',
    'DATA_VENCIDA': 'Data de entrega já vencida',
    'RUPTURA_CRITICA': 'Produto em ruptura crítica de estoque',
    'CLIENTE_INVALIDO': 'Cliente não cadastrado ou inválido',
    'PRODUTO_INVALIDO': 'Produto não cadastrado ou inválido'
}

# =============================================================================
# 🔧 CONFIGURAÇÕES TÉCNICAS
# =============================================================================

# Performance e limites
PERFORMANCE_CONFIG = {
    'max_itens_por_lote': 1000,         # Máximo itens por lote
    'timeout_processamento': 300,       # 5 minutos timeout
    'max_tentativas': 3,                # Máximo tentativas em erro
    'log_detalhado': True,              # Logs detalhados
    'backup_antes_alteracao': True,     # Backup antes alterar dados
}

# Campos que podem ser atualizados automaticamente
CAMPOS_ATUALIZAVEIS = {
    'menor_estoque_produto_d7',
    'saldo_estoque_pedido',
    'expedicao',
    'protocolo',
    'agendamento',
    'data_entrega_pedido',
    'observ_ped_1'  # Para logs de automação
}

# =============================================================================
# 📋 EXEMPLO DE PERSONALIZAÇÃO
# =============================================================================

"""
EXEMPLO DE COMO PERSONALIZAR PARA SEU NEGÓCIO:

1. CLIENTES ESTRATÉGICOS:
   - Substituir CNPJs exemplo pelos seus clientes TOP
   - Adicionar/remover conforme necessário

2. CAPACIDADES VEÍCULOS:
   - Ajustar peso_maximo_padrao (ex: 15000 para truck, 40000 para carreta)
   - Ajustar volume_maximo_padrao conforme baú
   - Definir ocupacao_minima adequada

3. PRAZOS:
   - dias_critico: Seu prazo crítico (ex: 3 dias, 5 dias, 10 dias)
   - dias_atencao: Seu prazo de atenção
   - valor_alto: Seu ticket alto (ex: R$ 20.000, R$ 100.000)

4. HORÁRIOS:
   - horarios_preferenciais: Seus horários reais
   - dias_uteis_apenas: Se trabalha finais de semana

5. MOTIVOS CARGA PARCIAL:
   - Adicionar motivos específicos do seu negócio
   - Remover motivos que não se aplicam

IMPORTANTE: Após personalizar, teste com carteira pequena primeiro!
"""

# =============================================================================
# 🎛️ CONFIGURAÇÃO CONSOLIDADA
# =============================================================================

# Configuração principal que será importada pelos módulos
AUTOMACAO_CONFIG = {
    'clientes_estrategicos': CLIENTES_ESTRATEGICOS,
    'capacidades': CAPACIDADES_VEICULOS,
    'prazos': PRAZOS_URGENCIA,
    'valores': VALORES_ESPECIAIS,
    'agendamento': AGENDAMENTO_CONFIG,
    'tipos_cliente': CONFIG_TIPOS_CLIENTE,
    'estoque': ESTOQUE_CONFIG,
    'situacoes_estoque': SITUACOES_ESTOQUE,
    'motivos_carga_parcial': MOTIVOS_CARGA_PARCIAL,
    'tipos_carga': TIPOS_CARGA,
    'scores_urgencia': SCORES_URGENCIA,
    'bonus_caracteristicas': BONUS_CARACTERISTICAS,
    'niveis_prioridade': NIVEIS_PRIORIDADE,
    'inconsistencias': INCONSISTENCIAS_CRITICAS,
    'performance': PERFORMANCE_CONFIG,
    'campos_atualizaveis': CAMPOS_ATUALIZAVEIS
}

# Função para validar configuração
def validar_configuracao():
    """
    Valida se a configuração está adequada para uso
    """
    erros = []
    
    # Validar clientes estratégicos
    if not CLIENTES_ESTRATEGICOS:
        erros.append("❌ CLIENTES_ESTRATEGICOS vazio - adicione seus clientes TOP")
    
    # Validar capacidades
    if CAPACIDADES_VEICULOS['peso_maximo_padrao'] <= 0:
        erros.append("❌ peso_maximo_padrao deve ser > 0")
    
    # Validar prazos
    if PRAZOS_URGENCIA['dias_critico'] >= PRAZOS_URGENCIA['dias_atencao']:
        erros.append("❌ dias_critico deve ser < dias_atencao")
    
    # Validar horários
    if not AGENDAMENTO_CONFIG['horarios_preferenciais']:
        erros.append("❌ horarios_preferenciais vazio - definir horários de entrega")
    
    if erros:
        print("🚨 ERROS NA CONFIGURAÇÃO:")
        for erro in erros:
            print(f"  {erro}")
        return False
    
    print("✅ Configuração validada com sucesso!")
    return True

# =============================================================================
# 🧪 MODO TESTE
# =============================================================================

# Configuração para testes (valores reduzidos)
TESTE_CONFIG = {
    'max_itens_por_lote': 10,
    'timeout_processamento': 30,
    'log_detalhado': True,
    'backup_antes_alteracao': False,
    'modo_simulacao': True,  # Não altera dados reais
}

# Para usar em testes:
# from config_automacao_carteira import TESTE_CONFIG
# config = TESTE_CONFIG if ambiente == 'teste' else AUTOMACAO_CONFIG

if __name__ == "__main__":
    print("🤖 CONFIGURAÇÃO DO SISTEMA DE AUTOMAÇÃO DA CARTEIRA")
    print("="*60)
    validar_configuracao()
    print("\n📋 Configuração atual:")
    print(f"  • Clientes estratégicos: {len(CLIENTES_ESTRATEGICOS)}")
    print(f"  • Peso máximo padrão: {CAPACIDADES_VEICULOS['peso_maximo_padrao']:,.0f} kg")
    print(f"  • Dias crítico: {PRAZOS_URGENCIA['dias_critico']}")
    print(f"  • Valor alto: R$ {VALORES_ESPECIAIS['valor_alto']:,.2f}")
    print(f"  • Horários: {AGENDAMENTO_CONFIG['horarios_preferenciais']}")
    print("\n⚠️  Lembre-se de personalizar os parâmetros conforme seu negócio!") 