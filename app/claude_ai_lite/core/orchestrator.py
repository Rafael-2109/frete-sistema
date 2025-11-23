"""
Orquestrador do Claude AI Lite.

Coordena o fluxo completo:
1. Verifica comandos de aprendizado
2. Classifica intenção
3. Encontra capacidade
4. Executa e gera resposta
5. Registra na memória

Limite: 150 linhas
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def processar_consulta(
    consulta: str,
    usar_claude_resposta: bool = True,
    usuario: str = "Claude AI",
    usuario_id: int = None
) -> str:
    """
    Processa consulta em linguagem natural.

    Args:
        consulta: Texto do usuário
        usar_claude_resposta: Se deve elaborar resposta com Claude
        usuario: Nome do usuário
        usuario_id: ID do usuário (para memória)

    Returns:
        Resposta formatada
    """
    if not consulta or not consulta.strip():
        return "Por favor, informe sua consulta."

    contexto_memoria = None

    # 1. Buscar contexto de memória
    if usuario_id:
        contexto_memoria = _buscar_memoria(usuario_id)

    # 2. Verificar comando de aprendizado
    if usuario_id:
        resultado_aprendizado = _verificar_aprendizado(consulta, usuario_id, usuario)
        if resultado_aprendizado:
            _registrar_conversa(usuario_id, consulta, resultado_aprendizado, None, None)
            return resultado_aprendizado

    # 3. Classificar intenção
    from .classifier import get_classifier
    classifier = get_classifier()
    intencao = classifier.classificar(consulta, contexto_memoria)

    dominio = intencao.get("dominio", "geral")
    intencao_tipo = intencao.get("intencao", "")
    entidades = intencao.get("entidades", {})

    logger.info(f"[ORCHESTRATOR] dominio={dominio}, intencao={intencao_tipo}")

    # 4. Tratamento de follow-up
    if dominio == "follow_up" or intencao_tipo in ("follow_up", "detalhar"):
        resposta = _processar_follow_up(consulta, contexto_memoria, usuario_id)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 5. Tratamento de ações (separação, etc)
    if dominio == "acao":
        resposta = _processar_acao(intencao_tipo, entidades, usuario, usuario_id, consulta)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 6. Encontrar capacidade para processar
    from ..capabilities import find_capability
    capacidade = find_capability(intencao_tipo, entidades)

    if not capacidade:
        return _msg_ajuda()

    # 7. Extrair critério de busca
    campo, valor = capacidade.extrair_valor_busca(entidades)
    if not campo or not valor:
        return _msg_sem_criterio()

    # 8. Executar capacidade
    contexto = {"usuario_id": usuario_id, "usuario": usuario}
    resultado = capacidade.executar(entidades, contexto)

    if not resultado.get("sucesso"):
        return f"Ops, ocorreu um erro: {resultado.get('erro', 'Erro desconhecido')}\n\nPosso tentar outra busca?"

    if resultado.get("total_encontrado", 0) == 0:
        return f"{resultado.get('mensagem', f'Não encontrei resultados para {valor}')}\n\nQuer tentar de outra forma?"

    # 9. Gerar resposta
    contexto_dados = capacidade.formatar_contexto(resultado)

    if usar_claude_resposta:
        from .responder import get_responder
        responder = get_responder()
        resposta = responder.gerar_resposta(consulta, contexto_dados, dominio, contexto_memoria)
    else:
        resposta = contexto_dados

    # 10. Registrar na memória
    _registrar_conversa(usuario_id, consulta, resposta, intencao, resultado)

    return resposta


def _buscar_memoria(usuario_id: int) -> Optional[str]:
    """Busca contexto de memória do usuário."""
    try:
        from ..memory import MemoryService
        return MemoryService.formatar_contexto_memoria(usuario_id)
    except Exception as e:
        logger.warning(f"Erro ao buscar memória: {e}")
        return None


def _verificar_aprendizado(consulta: str, usuario_id: int, usuario: str) -> Optional[str]:
    """Verifica se é comando de aprendizado e processa."""
    try:
        from ..learning import LearningService
        tipo_cmd, conteudo_cmd = LearningService.detectar_comando(consulta)

        if tipo_cmd:
            global_ = LearningService.verificar_comando_global(consulta)
            resultado = LearningService.processar_comando(
                tipo=tipo_cmd, conteudo=conteudo_cmd,
                usuario_id=usuario_id, usuario_nome=usuario, global_=global_
            )
            return resultado.get('mensagem', 'Comando processado.')
        return None
    except Exception as e:
        logger.warning(f"Erro ao processar aprendizado: {e}")
        return None


def _processar_follow_up(consulta: str, contexto_memoria: str, usuario_id: int) -> str:
    """Processa perguntas de follow-up."""
    from ..memory import MemoryService
    from .responder import get_responder

    ultimo_resultado = MemoryService.extrair_ultimo_resultado(usuario_id) if usuario_id else None
    dados_reais = _formatar_dados_reais(ultimo_resultado) if ultimo_resultado else ""

    if not ultimo_resultado and not contexto_memoria:
        return "Não encontrei contexto anterior. Poderia reformular sua pergunta?"

    responder = get_responder()
    return responder.gerar_resposta_follow_up(consulta, dados_reais, contexto_memoria)


def _processar_acao(intencao: str, entidades: Dict, usuario: str, usuario_id: int, texto: str) -> str:
    """Processa ações (criar separação, etc)."""
    from ..actions import processar_acao_separacao
    entidades["texto_original"] = texto
    return processar_acao_separacao(intencao, entidades, usuario=usuario, usuario_id=usuario_id)


def _formatar_dados_reais(resultado: Dict) -> str:
    """Formata dados reais do último resultado para follow-up."""
    dados = resultado.get('dados', [])
    if not dados:
        return ""

    linhas = ["=== DADOS DO ÚLTIMO RESULTADO ==="]
    if isinstance(dados, list):
        for item in dados[:20]:
            if isinstance(item, dict):
                nome = item.get('nome_produto') or item.get('nome', '')
                cod = item.get('cod_produto') or item.get('codigo', '')
                if nome or cod:
                    linhas.append(f"- {nome} (Cód: {cod})")
    return "\n".join(linhas)


def _registrar_conversa(usuario_id: int, consulta: str, resposta: str, intencao: dict, resultado: dict):
    """Registra conversa na memória."""
    if not usuario_id:
        return
    try:
        from ..memory import MemoryService
        MemoryService.registrar_conversa_completa(
            usuario_id=usuario_id, pergunta=consulta, resposta=resposta,
            intencao=intencao, resultado_busca=resultado
        )
    except Exception as e:
        logger.warning(f"Erro ao registrar conversa: {e}")


def _msg_ajuda() -> str:
    """Mensagem de ajuda quando não encontra capacidade."""
    return (
        "Desculpe, ainda não consigo ajudar com isso.\n\n"
        "Posso te ajudar com:\n"
        "- Consultar pedidos (ex: 'Pedido VCD123')\n"
        "- Verificar quando enviar (ex: 'Quando posso enviar VCD123?')\n"
        "- Buscar produtos (ex: 'Azeitona na carteira')\n"
        "- Criar separações (ex: 'Criar separação opção A')\n"
        "- Consultar estoque (ex: 'Estoque de ketchup')\n\n"
        "Como posso te ajudar?"
    )


def _msg_sem_criterio() -> str:
    """Mensagem quando não identifica critério de busca."""
    return (
        "Não consegui identificar o que você quer buscar.\n\n"
        "Tente informar:\n"
        "- Número do pedido (ex: 'Pedido VCD123')\n"
        "- Nome do cliente (ex: 'Pedidos do Atacadão')\n"
        "- Nome do produto (ex: 'Azeitona verde')\n"
    )
