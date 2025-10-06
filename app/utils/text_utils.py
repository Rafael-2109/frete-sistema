"""
Utilit árias para manipulação de texto
"""
import logging

logger = logging.getLogger(__name__)


def truncar_observacao(observacao, max_length=700):
    """
    Trunca observação para o tamanho máximo permitido no banco (700 caracteres)

    Esta função é usada para garantir que observações longas não causem erros
    ao salvar na tabela separacao, que tem limit e VARCHAR(700) para observ_ped_1.

    Args:
        observacao: String da observação (pode ser None)
        max_length: Tamanho máximo permitido (padrão: 700)

    Returns:
        String truncada ou None se input for None

    Exemplos:
        >>> truncar_observacao(None)
        None
        >>> truncar_observacao("Texto curto")
        'Texto curto'
        >>> truncar_observacao("a" * 800)
        'aaa...aaa'  # 700 caracteres com "..." no final
    """
    if observacao is None:
        return None

    if len(observacao) <= max_length:
        return observacao

    # Trunca e adiciona indicador
    truncado = observacao[:max_length-3] + "..."
    logger.warning(
        f"Observação truncada de {len(observacao)} para {max_length} caracteres. "
        f"Primeiros 100 chars: {observacao[:100]}"
    )
    return truncado
