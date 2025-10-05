"""
Service para geração de número sequencial de pedidos
Sistema MotoCHEFE
"""
from app import db
from sqlalchemy import text, func
from app.motochefe.models import PedidoVendaMoto


def gerar_proximo_numero_pedido():
    """
    Gera próximo número de pedido no formato "MC ####"
    Busca o maior número existente com máscara "MC " e adiciona 1

    Returns:
        str: Próximo número (ex: "MC 1321")
    """
    # Buscar maior número com máscara "MC "
    resultado = db.session.execute(text("""
        SELECT MAX(
            CAST(
                SUBSTRING(numero_pedido FROM 4) AS INTEGER
            )
        )
        FROM pedido_venda_moto
        WHERE numero_pedido LIKE 'MC %'
        AND SUBSTRING(numero_pedido FROM 4) ~ '^[0-9]+$'
    """)).scalar()

    # Se não encontrou nenhum, começar em 1320 (próximo será 1321)
    ultimo_numero = resultado if resultado else 1320

    # Próximo número
    proximo = ultimo_numero + 1

    return f"MC {proximo}"


def validar_numero_pedido_unico(numero_pedido, pedido_id=None):
    """
    Valida se número de pedido já existe no banco

    Args:
        numero_pedido (str): Número a validar
        pedido_id (int, optional): ID do pedido (para edição)

    Returns:
        tuple: (bool, str) - (é_valido, mensagem_erro)
    """
    query = PedidoVendaMoto.query.filter_by(numero_pedido=numero_pedido, ativo=True)

    # Se for edição, excluir próprio pedido da busca
    if pedido_id:
        query = query.filter(PedidoVendaMoto.id != pedido_id)

    existe = query.first()

    if existe:
        return False, f'Número de pedido "{numero_pedido}" já existe'

    return True, ''
