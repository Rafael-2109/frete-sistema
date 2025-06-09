def normalizar_nome_veiculo(nome):
    """
    Normaliza o nome do veículo para um formato padrão
    """
    if not nome:
        return None
        
    nome = nome.upper().strip()
    
    # Mapeamento de nomes alternativos para o padrão
    mapeamento = {
        'FIORINO': 'FIORINO',
        'HR': 'VAN/HR',
        'VAN': 'VAN/HR',
        'VAN/HR': 'VAN/HR',
        'HR/VAN': 'VAN/HR',
        'IVECO': 'IVECO',
        '3/4': '3/4',
        'TOCO': 'TOCO',
        'TRUCK': 'TRUCK',
        'CARRETA': 'CARRETA'
    }
    
    # Procura o nome mais próximo no mapeamento
    for padrao, normalizado in mapeamento.items():
        if padrao in nome:
            return normalizado
            
    return nome 