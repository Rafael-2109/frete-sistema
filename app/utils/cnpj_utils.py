"""
Utilitários para normalização e comparação de CNPJs
Centraliza a lógica de normalização para garantir consistência
"""

import re

def normalizar_cnpj(cnpj):
    """
    Remove toda formatação do CNPJ, mantendo apenas números.
    Garante que o CNPJ tenha sempre 14 dígitos, adicionando zeros à esquerda se necessário.
    
    Args:
        cnpj: String com CNPJ formatado ou não
        
    Returns:
        String contendo apenas os dígitos do CNPJ (sempre com 14 dígitos)
        
    Exemplos:
        '04.108.518/0001-02' -> '04108518000102'
        '04108518000102' -> '04108518000102'
        '8905698000104' -> '08905698000104'  # Adiciona zero à esquerda
        None -> ''
    """
    if not cnpj:
        return ""
    
    # Remove tudo exceto dígitos
    cnpj_limpo = re.sub(r'\D', '', str(cnpj))
    
    # Se tem menos de 14 dígitos, adiciona zeros à esquerda
    if cnpj_limpo and len(cnpj_limpo) < 14:
        cnpj_limpo = cnpj_limpo.zfill(14)
    
    return cnpj_limpo

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
    Garante que o CNPJ tenha 14 dígitos antes de formatar.
    
    Args:
        cnpj: String com CNPJ sem formatação
        
    Returns:
        String com CNPJ formatado (XX.XXX.XXX/XXXX-XX)
    """
    cnpj_limpo = normalizar_cnpj(cnpj)  # Já adiciona zeros à esquerda se necessário
    
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return cnpj  # Retorna como veio se não tem 14 dígitos
    
    # Aplica máscara XX.XXX.XXX/XXXX-XX
    return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"


# =============================================================================
# MAPEAMENTO DE EMPRESAS DO GRUPO
# =============================================================================

# CNPJs das empresas do grupo mapeados para seus nomes amigáveis
# Fonte de verdade centralizada - NÃO duplicar em outros arquivos
EMPRESAS_CNPJ_NOME = {
    '61724241000330': 'NACOM GOYA - CD',
    '61724241000178': 'NACOM GOYA - FB',
    '61724241000259': 'NACOM GOYA - SC',
    '18467441000163': 'LA FAMIGLIA - LF',
}


def obter_nome_empresa(cnpj: str) -> str:
    """
    Retorna o nome da empresa pelo CNPJ normalizado.

    Usa o mapeamento centralizado EMPRESAS_CNPJ_NOME para obter
    o nome amigável da empresa compradora.

    Args:
        cnpj: CNPJ formatado (XX.XXX.XXX/XXXX-XX) ou limpo (14 dígitos)

    Returns:
        Nome da empresa (ex: 'NACOM GOYA - CD') ou string vazia se desconhecida

    Exemplos:
        '61.724.241/0003-30' -> 'NACOM GOYA - CD'
        '61724241000330' -> 'NACOM GOYA - CD'
        '12345678000199' -> ''  # CNPJ desconhecido
    """
    if not cnpj:
        return ''

    cnpj_limpo = normalizar_cnpj(cnpj)
    return EMPRESAS_CNPJ_NOME.get(cnpj_limpo, '')