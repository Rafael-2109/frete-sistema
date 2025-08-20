# BACKUP DA FUNÇÃO ORIGINAL - CRIADO EM 2025-01-19
# Este arquivo contém o backup da lógica original de cálculo de frete
# do frete_simulador.py antes da integração com a calculadora centralizada

def calcular_fretes_possiveis_ORIGINAL(
    cidade_destino_id=None,
    peso_utilizado=None,
    valor_carga=None,
    uf_origem=None,
    uf_destino=None,
    cidade_destino=None,
    peso=None,
    valor=None,
    veiculo_forcado=None,
    rota=None,
    tipo_carga=None,
):
    """
    BACKUP DA FUNÇÃO ORIGINAL - linhas 161-197 do cálculo de frete
    """
    # ... código anterior mantém igual ...
    
    # ✅ LÓGICA ÚNICA DE CÁLCULO DE FRETE (ORIGINAL)
    
    # 1. Determinar peso para cálculo (peso real vs peso mínimo)
    peso_para_calculo = max(peso_final, tf.frete_minimo_peso or 0)
    
    # 2. Calcular frete base SOMANDO peso + valor
    frete_peso = (tf.valor_kg or 0) * peso_para_calculo
    frete_valor = (tf.percentual_valor or 0) * valor_final / 100
    frete_base = frete_peso + frete_valor  # SOMA peso + valor
    
    # 3. Calcular adicionais sobre valor da mercadoria
    gris = (tf.percentual_gris or 0) * valor_final / 100
    adv = (tf.percentual_adv or 0) * valor_final / 100
    rca = (tf.percentual_rca or 0) * valor_final / 100
    
    # 4. Calcular pedágio sobre peso para cálculo (por frações de 100kg)
    if tf.pedagio_por_100kg and peso_para_calculo > 0:
        fracoes_100kg = int((peso_para_calculo - 1) // 100) + 1  # Arredonda para cima
        pedagio = fracoes_100kg * tf.pedagio_por_100kg
    else:
        pedagio = 0
    
    # 5. Somar valores fixos
    fixos = (tf.valor_despacho or 0) + (tf.valor_cte or 0) + (tf.valor_tas or 0)
    
    # 6. Total líquido SEM ICMS
    frete_liquido = frete_base + gris + adv + rca + pedagio + fixos
    
    # 7. Aplicar frete mínimo VALOR no frete líquido
    frete_final_liquido = max(frete_liquido, tf.frete_minimo_valor or 0)
    
    # 8. Aplicar ICMS apenas no final (se não estiver incluso)
    frete_com_icms = frete_final_liquido
    if not tf.icms_incluso:
        if cidade_icms < 1 and cidade_icms > 0:
            frete_com_icms = frete_final_liquido / (1 - cidade_icms)

    # ... resto do código ...