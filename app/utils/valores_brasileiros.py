from typing import Tuple, Union

def converter_valor_brasileiro(valor_str: Union[str, None]) -> float:
    """
    Converte valor em formato brasileiro (1.234,56) para float
    
    Args:
        valor_str (str): Valor em formato brasileiro
        
    Returns:
        float: Valor convertido
        
    Raises:
        ValueError: Se o valor não puder ser convertido
    """
    if not valor_str:
        return 0.0
    
    # Remove espaços
    valor_limpo = str(valor_str).strip()
    
    if not valor_limpo:
        return 0.0
    
    try:
        # Remove pontos (milhares) e substitui vírgula por ponto (decimal)
        valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
        valor_float = float(valor_limpo)
        
        if valor_float < 0:
            raise ValueError("Valor deve ser positivo")
            
        return valor_float
        
    except (ValueError, TypeError) as e:
        raise ValueError(f'Valor inválido: {valor_str}. Use formato: 1.234,56') from e


def formatar_valor_brasileiro(valor_float: Union[float, None], decimais: int = 2) -> str:
    """
    Formata um float para o padrão brasileiro (1.234,56)

    Args:
        valor_float (float): Valor a ser formatado
        decimais (int): Número de casas decimais (padrão: 2)

    Returns:
        str: Valor formatado em padrão brasileiro
    """
    if valor_float is None:
        return f"0,{'0' * decimais}"

    try:
        # Formata com N casas decimais e separadores brasileiros
        formato = f",.{decimais}f"
        return f"{valor_float:{formato}}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return f"0,{'0' * decimais}"


def validar_valor_brasileiro(valor_str: Union[str, None]) -> Tuple[bool, str]:
    """
    Valida se um valor está em formato brasileiro válido
    
    Args:
        valor_str (str): Valor a ser validado
        
    Returns:
        tuple: (bool, str) - (é_válido, mensagem_erro)
    """
    if not valor_str:
        return True, ""
    
    try:
        converter_valor_brasileiro(valor_str)
        return True, ""
    except ValueError as e:
        return False, str(e) 