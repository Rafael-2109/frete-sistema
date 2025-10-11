"""
Service para gestão de devoluções de motos avariadas
Sistema MotoCHEFE
"""
from app import db
from sqlalchemy import text
from app.motochefe.models import Moto


def gerar_proximo_documento_devolucao():
    """
    Gera próximo número de documento de devolução no formato "DEV-###"
    Busca o maior número existente e adiciona 1

    Returns:
        str: Próximo número (ex: "DEV-001", "DEV-002"...)
    """
    # Buscar maior número com máscara "DEV-"
    resultado = db.session.execute(text("""
        SELECT MAX(
            CAST(
                SUBSTRING(documento_devolucao FROM 5) AS INTEGER
            )
        )
        FROM moto
        WHERE documento_devolucao LIKE 'DEV-%'
        AND SUBSTRING(documento_devolucao FROM 5) ~ '^[0-9]+$'
    """)).scalar()

    # Se não encontrou nenhum, começar em 0 (próximo será 1)
    ultimo_numero = resultado if resultado else 0

    # Próximo número com zero padding (3 dígitos)
    proximo = ultimo_numero + 1

    return f"DEV-{proximo:03d}"


def listar_devolucoes_abertas():
    """
    Lista documentos de devolução que ainda têm motos no status AVARIADO
    (ou seja, devoluções que ainda podem receber mais motos)

    Returns:
        list: Lista de dict com {documento_devolucao, qtd_motos, motos}
    """
    # Buscar devoluções existentes com motos DEVOLVIDO ou AVARIADO
    devolucoes = db.session.execute(text("""
        SELECT
            documento_devolucao,
            COUNT(*) as qtd_motos,
            STRING_AGG(numero_chassi, ', ' ORDER BY numero_chassi) as motos
        FROM moto
        WHERE documento_devolucao IS NOT NULL
        AND status IN ('DEVOLVIDO', 'AVARIADO')
        AND ativo = true
        GROUP BY documento_devolucao
        ORDER BY documento_devolucao DESC
    """)).fetchall()

    return [{
        'documento_devolucao': d[0],
        'qtd_motos': d[1],
        'motos': d[2]
    } for d in devolucoes]


def obter_motos_por_documento_devolucao(documento_devolucao):
    """
    Busca todas as motos de um documento de devolução

    Args:
        documento_devolucao (str): Número do documento (ex: "DEV-001")

    Returns:
        list: Lista de objetos Moto
    """
    return Moto.query.filter_by(
        documento_devolucao=documento_devolucao,
        ativo=True
    ).order_by(Moto.numero_chassi).all()


def devolver_moto_individual(chassi, documento_devolucao, observacao_adicional=None, usuario=None):
    """
    Devolve uma moto individual ao fornecedor

    Args:
        chassi (str): Número do chassi
        documento_devolucao (str): Número do documento (DEV-###)
        observacao_adicional (str, optional): Observação adicional
        usuario (str, optional): Nome do usuário que fez a devolução

    Raises:
        Exception: Se moto não estiver avariada ou não existir
    """
    moto = Moto.query.get(chassi)

    if not moto:
        raise Exception(f'Moto {chassi} não encontrada')

    if moto.status != 'AVARIADO':
        raise Exception(f'Moto {chassi} não está avariada (status atual: {moto.status})')

    # Atualizar observação se fornecida
    if observacao_adicional:
        if moto.observacao:
            moto.observacao += f"\n\nDevolução ({documento_devolucao}): {observacao_adicional}"
        else:
            moto.observacao = f"Devolução ({documento_devolucao}): {observacao_adicional}"

    # Atualizar status e documento
    moto.status = 'DEVOLVIDO'
    moto.documento_devolucao = documento_devolucao
    moto.atualizado_por = usuario or 'Sistema'


def devolver_motos_lote(chassis_list, documento_devolucao, observacao_adicional=None, usuario=None):
    """
    Devolve múltiplas motos em lote para o mesmo documento de devolução

    Args:
        chassis_list (list): Lista de números de chassi
        documento_devolucao (str): Número do documento (DEV-###)
        observacao_adicional (str, optional): Observação adicional
        usuario (str, optional): Nome do usuário que fez a devolução

    Returns:
        dict: {sucesso: int, erros: list}
    """
    sucesso = 0
    erros = []

    for chassi in chassis_list:
        try:
            devolver_moto_individual(chassi, documento_devolucao, observacao_adicional, usuario)
            sucesso += 1
        except Exception as e:
            erros.append(f'{chassi}: {str(e)}')

    # Commit apenas se houver pelo menos 1 sucesso
    if sucesso > 0:
        db.session.commit()

    return {
        'sucesso': sucesso,
        'erros': erros
    }
