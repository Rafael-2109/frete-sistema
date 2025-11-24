"""
Actions de Separacao - Handlers para criar/modificar separacoes via Claude AI.

Fluxo interativo:
1. Usuario pede separacao -> cria RASCUNHO
2. Usuario pode editar (incluir/excluir/alterar)
3. Usuario confirma -> efetiva a separacao
"""

from typing import Dict, Optional
import logging

from .rascunho_separacao import RascunhoService

logger = logging.getLogger(__name__)


def processar_acao_separacao(
    intencao: str,
    entidades: Dict,
    usuario: str = "Claude AI",
    usuario_id: int = None
) -> str:
    """
    Processa acoes relacionadas a separacao.

    Args:
        intencao: Tipo da intencao
        entidades: Entidades extraidas (opcao, num_pedido, item, quantidade, etc)
        usuario: Nome do usuario
        usuario_id: ID do usuario (para rascunho)

    Returns:
        Resposta formatada para o usuario
    """
    opcao = entidades.get("opcao")
    num_pedido = entidades.get("num_pedido")
    item = entidades.get("item") or entidades.get("produto")
    quantidade = entidades.get("quantidade")

    # Se não tem num_pedido, tenta buscar do contexto
    if not num_pedido and usuario_id:
        num_pedido = _buscar_pedido_do_contexto(usuario_id)

    logger.info(f"[ACTION] intencao={intencao}, pedido={num_pedido}, opcao={opcao}, item={item}")

    # === AÇÕES DE EDIÇÃO DO RASCUNHO ===

    if intencao == "incluir_item":
        return _processar_incluir_item(usuario_id, item, quantidade)

    elif intencao == "excluir_item":
        return _processar_excluir_item(usuario_id, item)

    elif intencao == "alterar_quantidade":
        return _processar_alterar_quantidade(usuario_id, item, quantidade)

    # === AÇÕES DE CRIAÇÃO DE RASCUNHO ===

    elif intencao in ("criar_separacao", "separar", "separar_disponiveis"):
        # Verifica se já tem rascunho ativo
        rascunho_existente = RascunhoService.carregar_rascunho(usuario_id) if usuario_id else None

        if rascunho_existente:
            return (
                f"Você já tem um rascunho ativo para o pedido {rascunho_existente.num_pedido}.\n\n"
                f"{RascunhoService.formatar_rascunho(rascunho_existente)}\n\n"
                "Deseja 'Confirmar' este rascunho ou 'Cancelar' e criar um novo?"
            )

        if not num_pedido:
            return (
                "Para criar uma separação, preciso saber o número do pedido.\n"
                "Exemplo: 'Criar separação do pedido VCD2564344'"
            )

        return _criar_rascunho(usuario_id, num_pedido, opcao, entidades)

    elif intencao == "escolher_opcao":
        if not opcao:
            return (
                "Qual opção você deseja?\n"
                "- Opção A = envio total (todos os itens)\n"
                "- Opção B = envio parcial\n"
                "- 'Separar disponíveis' = apenas itens em estoque"
            )

        # _criar_rascunho_opcao já busca num_pedido do contexto se não tiver
        return _criar_rascunho_opcao(usuario_id, num_pedido, opcao)

    # === AÇÕES DE CONFIRMAÇÃO ===

    elif intencao in ("confirmar_acao", "confirmar"):
        return _processar_confirmacao(usuario_id, usuario)

    elif intencao in ("cancelar_rascunho", "cancelar"):
        return _processar_cancelamento(usuario_id)

    # === VISUALIZAÇÃO ===

    elif intencao == "ver_rascunho":
        rascunho = RascunhoService.carregar_rascunho(usuario_id) if usuario_id else None
        if rascunho:
            return RascunhoService.formatar_rascunho(rascunho)
        return "Você não tem nenhum rascunho de separação ativo."

    return (
        "Posso ajudar com separações! Exemplos:\n"
        "- 'Criar separação do pedido VCD123'\n"
        "- 'Separar os itens disponíveis'\n"
        "- 'Opção A para o pedido VCD123'\n"
        "- 'Incluir [produto]' / 'Excluir [produto]'\n"
        "- 'Confirmar' para efetivar"
    )


def _buscar_pedido_do_contexto(usuario_id: int) -> Optional[str]:
    """Busca o número do pedido do contexto da última conversa."""
    try:
        from ..memory import MemoryService
        from ..core.conversation_context import ConversationContextManager

        # 1. Primeiro tenta do rascunho ativo
        rascunho = RascunhoService.carregar_rascunho(usuario_id)
        if rascunho:
            return rascunho.num_pedido

        # 2. Tenta das entidades ativas do ConversationContext
        estado = ConversationContextManager.obter_estado(usuario_id)
        if estado.entidades_ativas.get('num_pedido'):
            return estado.entidades_ativas['num_pedido']

        # 3. Tenta do último resultado
        ultimo_resultado = MemoryService.extrair_ultimo_resultado(usuario_id)
        if ultimo_resultado:
            # Tenta extrair do campo num_pedido
            num_pedido = ultimo_resultado.get('num_pedido')
            if num_pedido:
                return num_pedido

            # Tenta extrair dos dados
            dados = ultimo_resultado.get('dados', {})

            if isinstance(dados, dict):
                num_pedido = dados.get('num_pedido')
                if num_pedido:
                    return num_pedido

            # Se dados é lista, pega o primeiro
            if isinstance(dados, list) and dados:
                primeiro = dados[0] if isinstance(dados[0], dict) else {}
                num_pedido = primeiro.get('num_pedido')
                if num_pedido:
                    return num_pedido

            # Tenta do valor buscado
            valor = ultimo_resultado.get('valor_buscado')
            if valor and str(valor).upper().startswith('VCD'):
                return valor

        return None
    except Exception as e:
        logger.warning(f"[ACTION] Erro ao buscar pedido do contexto: {e}")
        return None


def _criar_rascunho(usuario_id: int, num_pedido: str, opcao: str = None, entidades: Dict = None) -> str:
    """Cria um rascunho baseado no contexto."""

    # Detecta modo pela pergunta do usuário
    if entidades:
        texto_original = str(entidades.get("texto_original", "")).lower()

        # NOVO: Detecta pedido total/completo
        padroes_total = [
            "todos os itens", "todos itens", "pedido total", "pedido completo",
            "tudo", "inteiro", "completo", "total", "todos os produtos",
            "todos produtos", "separar todo", "separar tudo"
        ]
        if any(p in texto_original for p in padroes_total):
            logger.info(f"[ACTION] Detectado pedido TOTAL para {num_pedido}")
            return _criar_rascunho_total_pedido(usuario_id, num_pedido)

        # Detecta disponíveis
        if any(p in texto_original for p in ["disponivel", "disponíveis", "o que dá", "o que da", "em estoque"]):
            return _criar_rascunho_disponiveis(usuario_id, num_pedido)

    if opcao:
        return _criar_rascunho_opcao(usuario_id, num_pedido, opcao)

    # Sem opção específica - pergunta ao usuário
    return (
        f"Para o pedido {num_pedido}, como deseja criar a separação?\n\n"
        "- **Opção A**: Pedido Total (todos os itens)\n"
        "- **Opção B**: Apenas itens disponíveis em estoque\n"
        "- **Opção C**: Análise de disponibilidade (quando posso enviar)\n\n"
        "Responda 'Opção A', 'Opção B' ou 'Opção C'"
    )


def _criar_rascunho_total_pedido(usuario_id: int, num_pedido: str) -> str:
    """Cria rascunho com TODOS os itens do pedido (independente de estoque)."""
    resultado = RascunhoService.criar_rascunho_total(num_pedido)

    if not resultado["sucesso"]:
        return f"Erro ao criar rascunho total: {resultado.get('erro')}"

    rascunho = resultado["rascunho"]

    if usuario_id:
        RascunhoService.salvar_rascunho(usuario_id, rascunho)

    return (
        f"📦 **RASCUNHO CRIADO - PEDIDO TOTAL**\n\n"
        f"{RascunhoService.formatar_rascunho(rascunho)}\n\n"
        "Este rascunho inclui TODOS os itens do pedido.\n"
        "Deseja 'Confirmar' para criar a separação ou 'Cancelar'?"
    )


def _criar_rascunho_disponiveis(usuario_id: int, num_pedido: str) -> str:
    """Cria rascunho apenas com itens disponíveis."""
    resultado = RascunhoService.criar_rascunho_disponiveis(num_pedido)

    if not resultado["sucesso"]:
        return f"Erro ao analisar pedido: {resultado.get('erro')}"

    rascunho = resultado["rascunho"]

    if usuario_id:
        RascunhoService.salvar_rascunho(usuario_id, rascunho)

    return RascunhoService.formatar_rascunho(rascunho)


def _criar_rascunho_opcao(usuario_id: int, num_pedido: str, opcao: str) -> str:
    """
    Cria rascunho baseado em uma opção (A, B, C).

    MELHORIA: Primeiro tenta usar opções salvas no ConversationContext
    (da análise de disponibilidade anterior), evitando re-análise.
    """
    from ..core.conversation_context import ConversationContextManager

    # NOVO: Tenta buscar opções do contexto da conversa
    estado = ConversationContextManager.obter_estado(usuario_id) if usuario_id else None
    opcoes_contexto = estado.opcoes_oferecidas if estado else []

    # Se tem opções no contexto e não tem num_pedido, pega do contexto
    if not num_pedido and estado and estado.entidades_ativas.get('num_pedido'):
        num_pedido = estado.entidades_ativas['num_pedido']
        logger.info(f"[ACTION] num_pedido recuperado do contexto: {num_pedido}")

    # Se ainda não tem num_pedido, tenta novamente do contexto geral
    if not num_pedido and usuario_id:
        num_pedido = _buscar_pedido_do_contexto(usuario_id)

    if not num_pedido:
        return (
            f"Opção {opcao.upper()} escolhida, mas não encontrei o número do pedido.\n"
            "Por favor, informe: 'Opção {opcao.upper()} para pedido VCD123456'"
        )

    # Verifica se a opção existe no contexto
    opcao_encontrada = None
    if opcoes_contexto:
        for op in opcoes_contexto:
            if op.get('codigo') == opcao.upper():
                opcao_encontrada = op
                break

    # Se encontrou opção no contexto, usa diretamente (mais eficiente)
    if opcao_encontrada:
        logger.info(f"[ACTION] Usando opção {opcao.upper()} do contexto para pedido {num_pedido}")
        resultado = RascunhoService.criar_rascunho_de_opcao_contexto(
            num_pedido=num_pedido,
            opcao_dados=opcao_encontrada
        )
    elif opcao.upper() == "A":
        resultado = RascunhoService.criar_rascunho_total(num_pedido)
    else:
        resultado = RascunhoService.criar_rascunho_opcao(num_pedido, opcao)

    if not resultado["sucesso"]:
        return f"Erro ao criar rascunho: {resultado.get('erro')}"

    rascunho = resultado["rascunho"]

    if usuario_id:
        RascunhoService.salvar_rascunho(usuario_id, rascunho)
        # Limpa opções do contexto após usar
        ConversationContextManager.atualizar_estado(
            usuario_id=usuario_id,
            opcoes=[],
            aguardando_confirmacao=False,
            acao_pendente=""
        )

    return (
        f"📦 **RASCUNHO CRIADO - OPÇÃO {opcao.upper()}**\n\n"
        f"{RascunhoService.formatar_rascunho(rascunho)}\n\n"
        "Deseja 'Confirmar' para criar a separação ou 'Cancelar'?"
    )


def _processar_incluir_item(usuario_id: int, item: str, quantidade: float = None) -> str:
    """Processa inclusão de item no rascunho."""
    if not usuario_id:
        return "Erro: sessão não identificada."

    rascunho = RascunhoService.carregar_rascunho(usuario_id)
    if not rascunho:
        return (
            "Você não tem um rascunho ativo.\n"
            "Primeiro, crie um rascunho: 'Criar separação do pedido VCD123'"
        )

    if not item:
        return "Qual item você deseja incluir? Informe o nome ou código do produto."

    resultado = RascunhoService.incluir_item(rascunho, item, quantidade)
    RascunhoService.salvar_rascunho(usuario_id, rascunho)

    return f"{resultado}\n\n{RascunhoService.formatar_rascunho(rascunho)}"


def _processar_excluir_item(usuario_id: int, item: str) -> str:
    """Processa exclusão de item do rascunho."""
    if not usuario_id:
        return "Erro: sessão não identificada."

    rascunho = RascunhoService.carregar_rascunho(usuario_id)
    if not rascunho:
        return (
            "Você não tem um rascunho ativo.\n"
            "Primeiro, crie um rascunho: 'Criar separação do pedido VCD123'"
        )

    if not item:
        return "Qual item você deseja excluir? Informe o nome ou código do produto."

    resultado = RascunhoService.excluir_item(rascunho, item)
    RascunhoService.salvar_rascunho(usuario_id, rascunho)

    return f"{resultado}\n\n{RascunhoService.formatar_rascunho(rascunho)}"


def _processar_alterar_quantidade(usuario_id: int, item: str, quantidade: float) -> str:
    """Processa alteração de quantidade no rascunho."""
    if not usuario_id:
        return "Erro: sessão não identificada."

    rascunho = RascunhoService.carregar_rascunho(usuario_id)
    if not rascunho:
        return (
            "Você não tem um rascunho ativo.\n"
            "Primeiro, crie um rascunho: 'Criar separação do pedido VCD123'"
        )

    if not item:
        return "Qual item você deseja alterar? Informe o nome ou código."

    if quantidade is None:
        return f"Qual a nova quantidade para '{item}'?"

    resultado = RascunhoService.alterar_quantidade(rascunho, item, float(quantidade))
    RascunhoService.salvar_rascunho(usuario_id, rascunho)

    return f"{resultado}\n\n{RascunhoService.formatar_rascunho(rascunho)}"


def _processar_confirmacao(usuario_id: int, usuario_nome: str) -> str:
    """Processa confirmação do rascunho."""
    if not usuario_id:
        return "Erro: sessão não identificada."

    rascunho = RascunhoService.carregar_rascunho(usuario_id)
    if not rascunho:
        return (
            "Você não tem um rascunho para confirmar.\n"
            "Primeiro, crie uma separação: 'Criar separação do pedido VCD123'"
        )

    itens_incluidos = rascunho.itens_incluidos
    if not itens_incluidos:
        return "Não há itens incluídos no rascunho. Adicione pelo menos um item."

    resultado = RascunhoService.confirmar_rascunho(usuario_id, usuario_nome)

    if resultado["sucesso"]:
        return (
            f"✅ SEPARAÇÃO CRIADA COM SUCESSO!\n\n"
            f"📦 Pedido: {rascunho.num_pedido}\n"
            f"🏷️ Lote: {resultado.get('lote_id', 'N/A')}\n"
            f"📝 Itens: {resultado.get('itens_criados', len(itens_incluidos))}\n"
            f"💰 Valor: R$ {rascunho.valor_total:,.2f}\n"
            f"👤 Criado por: {usuario_nome}\n\n"
            "A separação foi registrada no sistema."
        )
    else:
        return f"❌ Erro ao criar separação: {resultado.get('erro', 'Erro desconhecido')}"


def _processar_cancelamento(usuario_id: int) -> str:
    """Processa cancelamento do rascunho."""
    if not usuario_id:
        return "Erro: sessão não identificada."

    rascunho = RascunhoService.carregar_rascunho(usuario_id)
    if not rascunho:
        return "Você não tem um rascunho ativo para cancelar."

    RascunhoService.limpar_rascunho(usuario_id)
    return f"✅ Rascunho do pedido {rascunho.num_pedido} foi cancelado."
