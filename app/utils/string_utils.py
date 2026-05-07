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


def colapsar_espacos(texto):
    """
    Remove espacos no inicio/fim e colapsa espacos internos consecutivos
    em um unico espaco. Preserva acentos e caixa original.

    Exemplos:
        '  WANDERLEI   DA   CONCEICAO  ' -> 'WANDERLEI DA CONCEICAO'
        'TABELA  AB' -> 'TABELA AB'
        None -> None
    """
    if texto is None:
        return None
    s = str(texto)
    if not s:
        return s
    return ' '.join(s.split())


def normalizar_nome_corporativo(texto):
    """
    Normaliza um nome corporativo (transportadora, tabela de frete, etc.)
    para uso consistente em comparacoes e armazenamento.

    Regras:
    1. Trim (remove espacos no inicio/fim)
    2. Colapsa espacos internos consecutivos em um unico espaco
    3. Converte para MAIUSCULO

    Mantem acentos e caracteres especiais (cedilha, etc.) — para
    comparacao insensivel a acento, usar `f_unaccent` no SQL ou
    `remover_acentos` no Python.

    Exemplos:
        '  Wanderlei  da   Conceicao  ' -> 'WANDERLEI DA CONCEICAO'
        'Tabela 408' -> 'TABELA 408'
        None -> None
        '' -> ''
    """
    if texto is None:
        return None
    s = str(texto).strip()
    if not s:
        return s
    return ' '.join(s.split()).upper()


def chave_comparacao_nome(texto):
    """
    Gera chave canonica para comparar nomes corporativos:
    1. Trim + colapsa espacos
    2. Remove acentos
    3. Converte para MAIUSCULO

    Usar APENAS para comparacao em memoria (Python). Para SQL, prefira
    `func.f_unaccent(coluna).ilike(func.f_unaccent(valor))`.

    Exemplos:
        'WANDERLEI DA CONCEIÇÂO' -> 'WANDERLEI DA CONCEICAO'
        'wanderlei  da  conceiçao' -> 'WANDERLEI DA CONCEICAO'
    """
    if texto is None:
        return ''
    s = ' '.join(str(texto).split())
    if not s:
        return ''
    return remover_acentos(s)

def normalizar_nome_cidade(nome, rota=None):
    """
    Normaliza o nome da cidade seguindo as regras:
    1. Se rota FOB -> None (será tratado separadamente)
    2. Se cidade SP -> SAO PAULO
    3. Se cidade RJ -> RIO DE JANEIRO
    4. Outros casos -> Remove acentos e converte para maiúsculo
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