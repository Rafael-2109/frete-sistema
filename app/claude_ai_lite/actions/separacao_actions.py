"""
Actions de Separacao - Handlers para criar/modificar separacoes via Claude AI.
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


def processar_acao_separacao(intencao: str, entidades: Dict) -> str:
    """
    Processa acoes relacionadas a separacao.

    Args:
        intencao: Tipo da intencao (escolher_opcao, criar_separacao, confirmar_acao)
        entidades: Entidades extraidas (opcao, num_pedido, etc)

    Returns:
        Resposta formatada para o usuario
    """
    opcao = entidades.get("opcao")
    num_pedido = entidades.get("num_pedido")

    if intencao == "escolher_opcao":
        return _processar_escolha_opcao(opcao, num_pedido)

    elif intencao == "criar_separacao":
        return _processar_criar_separacao(opcao, num_pedido)

    elif intencao == "confirmar_acao":
        return (
            "Para criar a separacao, use o comando:\n"
            "'Criar separacao opcao X do pedido XXXXX'"
        )

    return "Nao entendi a acao solicitada."


def _processar_escolha_opcao(opcao: str, num_pedido: str) -> str:
    """Processa quando usuario escolhe uma opcao (A, B, C)."""
    if not opcao:
        return (
            "Entendi que voce quer escolher uma opcao, mas nao identifiquei qual.\n"
            "Por favor, informe: 'Opcao A para o pedido XXXXX' ou 'Quero a opcao B do pedido XXXXX'"
        )

    if not num_pedido:
        return (
            f"Voce escolheu a Opcao {opcao.upper()}, mas preciso saber de qual pedido.\n"
            f"Por favor, informe o numero do pedido junto com a opcao.\n"
            f"Exemplo: 'Opcao {opcao.upper()} para o pedido VCD2564344'"
        )

    # Tem opcao e pedido - mostrar confirmacao
    from ..domains.carteira.services import OpcoesEnvioService, CriarSeparacaoService

    analise = OpcoesEnvioService.analisar_pedido(num_pedido)
    if not analise["sucesso"]:
        return f"Erro ao buscar pedido: {analise.get('erro')}"

    opcao_escolhida = None
    for op in analise["opcoes"]:
        if op["codigo"] == opcao.upper():
            opcao_escolhida = op
            break

    if not opcao_escolhida:
        return f"Opcao {opcao.upper()} nao disponivel para o pedido {num_pedido}"

    return CriarSeparacaoService.formatar_confirmacao(opcao_escolhida, analise["num_pedido"])


def _processar_criar_separacao(opcao: str, num_pedido: str) -> str:
    """Processa criacao efetiva da separacao."""
    if not opcao or not num_pedido:
        return (
            "Para criar separacao, informe a opcao e o pedido.\n"
            "Exemplo: 'Criar separacao opcao A do pedido VCD2564344'"
        )

    from ..domains.carteira.services import CriarSeparacaoService

    resultado = CriarSeparacaoService.criar_separacao_opcao(
        num_pedido=num_pedido,
        opcao_codigo=opcao.upper(),
        usuario="Claude AI"
    )

    if resultado["sucesso"]:
        return (
            f"Separacao criada com sucesso!\n\n"
            f"Lote: {resultado['lote_id']}\n"
            f"Itens: {resultado['itens_criados']}\n"
            f"Valor: R$ {resultado['valor_total']:,.2f} ({resultado['percentual']:.1f}%)\n"
            f"Data Expedicao: {resultado['data_expedicao']}"
        )
    else:
        return f"Erro ao criar separacao: {resultado['mensagem']}"
