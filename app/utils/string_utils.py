import unicodedata

def remover_acentos(texto):
    """
    Remove acentos e caracteres especiais de um texto.
    Exemplo: 'São Paulo' -> 'SAO PAULO'
    """
    if not texto:
        return texto
        
    # Normaliza para forma NFKD e remove diacríticos
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    
    # Remove caracteres especiais e converte para maiúsculo
    texto = ''.join(c for c in texto if c.isalnum() or c.isspace() or c == '-')
    texto = ' '.join(texto.split())  # Remove espaços extras
    return texto.upper()

def normalizar_nome_cidade(nome, rota=None):
    """
    Normaliza o nome da cidade seguindo as regras:
    1. Se rota FOB -> None (será tratado separadamente)
    2. Se rota RED -> GUARULHOS/SP
    3. Se cidade SP -> SAO PAULO
    4. Se cidade RJ -> RIO DE JANEIRO
    5. Outros casos -> Remove acentos e converte para maiúsculo
    """
    if not nome:
        return None
        
    # Remove espaços extras e converte para maiúsculo
    nome = nome.strip().upper()
    
    # Verifica rota primeiro
    if rota:
        rota = rota.strip().upper()
        if rota == 'FOB':
            return None
        if rota == 'RED':
            return 'GUARULHOS'
    
    # Casos especiais de cidade
    if nome in ['SP', 'SAO PAULO', 'SÃO PAULO', 'S PAULO', 'S. PAULO']:
        return 'SAO PAULO'
    if nome in ['RJ', 'RIO DE JANEIRO', 'R JANEIRO', 'R. JANEIRO']:
        return 'RIO DE JANEIRO'
    
    # Para outros casos, remove acentos e retorna em maiúsculo
    return remover_acentos(nome)

def normalizar_nome_cidade_excel(nome):
    """
    Alias para normalizar_nome_cidade para manter compatibilidade.
    """
    return normalizar_nome_cidade(nome)

def comparar_nomes_cidade(nome_excel, nome_banco):
    """
    Compara o nome da cidade do Excel com o nome no banco,
    considerando variações de acentuação.
    
    Ambos os nomes são normalizados:
    1. Removendo acentos
    2. Convertendo para maiúsculo
    """
    if not nome_excel or not nome_banco:
        return False
        
    # Normaliza os nomes (remove acentos e converte para maiúsculo)
    nome_excel_norm = remover_acentos(nome_excel.strip().upper())
    nome_banco_norm = remover_acentos(nome_banco.strip().upper())
    
    return nome_excel_norm == nome_banco_norm

def normalizar_cidade_abreviada(cidade):
    """
    Alias para normalizar_nome_cidade para manter compatibilidade.
    """
    return normalizar_nome_cidade(cidade) 