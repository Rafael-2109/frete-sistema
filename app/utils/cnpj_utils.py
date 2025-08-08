"""
Utilitários para normalização e comparação de CNPJs
Centraliza a lógica de normalização para garantir consistência
"""

import re

def normalizar_cnpj(cnpj):
    """
    Remove toda formatação do CNPJ, mantendo apenas números.
    
    Args:
        cnpj: String com CNPJ formatado ou não
        
    Returns:
        String contendo apenas os dígitos do CNPJ
        
    Exemplos:
        '04.108.518/0001-02' -> '04108518000102'
        '04108518000102' -> '04108518000102'
        None -> ''
    """
    if not cnpj:
        return ""
    
    # Remove tudo exceto dígitos
    return re.sub(r'\D', '', str(cnpj))

def cnpjs_iguais(cnpj1, cnpj2):
    """
    Compara dois CNPJs ignorando formatação.
    
    Args:
        cnpj1: Primeiro CNPJ
        cnpj2: Segundo CNPJ
        
    Returns:
        True se os CNPJs são iguais (ignorando formatação), False caso contrário
    """
    return normalizar_cnpj(cnpj1) == normalizar_cnpj(cnpj2)

def formatar_cnpj(cnpj):
    """
    Formata um CNPJ adicionando pontuação padrão.
    
    Args:
        cnpj: String com CNPJ sem formatação
        
    Returns:
        String com CNPJ formatado (XX.XXX.XXX/XXXX-XX)
    """
    cnpj_limpo = normalizar_cnpj(cnpj)
    
    if len(cnpj_limpo) != 14:
        return cnpj  # Retorna como veio se não tem 14 dígitos
    
    # Aplica máscara XX.XXX.XXX/XXXX-XX
    return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"