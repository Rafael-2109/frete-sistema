"""
Orquestrador do Claude AI Lite v5.0.

Coordena o fluxo completo:
1. Obter estado estruturado
2. Carregar conhecimento do negócio
3. Verificar comandos de aprendizado
4. Extração inteligente (Claude)
5. Tratamento especial (clarificação, follow-up, ação)
6. AgentPlanner planeja e executa ferramentas
7. Gerar resposta
8. Registrar na memória

FILOSOFIA v5.0:
- O Claude é o CÉREBRO - planeja E executa
- AgentPlanner substitui find_capability() -> cap.executar()
- Suporta múltiplas etapas (até 5)
- Fallback automático para AutoLoader
- Usa EstadoManager diretamente (ConversationContext removido)

Criado em: 24/11/2025
Atualizado: 26/11/2025 - AgentPlanner v5.0, removido ConversationContext
"""

import logging
from typing import Dict, Any, Optional, List

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

    # 1. Obter ESTADO ESTRUTURADO (JSON)
    contexto_estruturado = ""
    if usuario_id:
        from .structured_state import obter_estado_json
        contexto_estruturado = obter_estado_json(usuario_id)
        if contexto_estruturado:
            logger.debug(f"[ORCHESTRATOR] Estado estruturado: {len(contexto_estruturado)} chars")

    # 2. Carregar conhecimento do negócio (aprendizados)
    conhecimento_negocio = _carregar_conhecimento_negocio(usuario_id)
    if conhecimento_negocio:
        logger.debug(f"[ORCHESTRATOR] Conhecimento carregado: {len(conhecimento_negocio)} chars")

    # 3. Verificar comando de aprendizado (antes de tudo)
    if usuario_id:
        resultado_aprendizado = _verificar_aprendizado(consulta, usuario_id, usuario)
        if resultado_aprendizado:
            _registrar_conversa(usuario_id, consulta, resultado_aprendizado, None, None)
            return resultado_aprendizado

    # 4. EXTRAÇÃO INTELIGENTE - Delega ao Claude
    intencao = _extrair_inteligente(consulta, contexto_estruturado, conhecimento_negocio)

    dominio = intencao.get("dominio", "geral")
    intencao_tipo = intencao.get("intencao", "")
    entidades = intencao.get("entidades", {})

    logger.info(f"[ORCHESTRATOR] dominio={dominio}, intencao={intencao_tipo}, "
               f"entidades={list(entidades.keys())}")

    # 4.1 Atualiza estado estruturado com entidades extraídas
    if usuario_id and entidades:
        from .structured_state import EstadoManager
        EstadoManager.atualizar_do_extrator(usuario_id, entidades)
        logger.debug(f"[ORCHESTRATOR] Estado atualizado com {len(entidades)} entidades")

    # 4.2 Buscar contexto de memória
    contexto_memoria = None
    if usuario_id:
        contexto_memoria = _buscar_memoria(usuario_id)

    # 5. TRATAMENTOS ESPECIAIS (não passam pelo AgentPlanner)

    # 5.1 Clarificação (Claude detectou ambiguidade)
    if dominio == "clarificacao":
        resposta = _processar_clarificacao(intencao, usuario_id)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 5.2 Follow-up
    if dominio == "follow_up" or intencao_tipo in ("follow_up", "detalhar"):
        resposta = _processar_follow_up(consulta, contexto_memoria, usuario_id)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 5.3 Ações (separação, etc)
    if dominio == "acao":
        resposta = _processar_acao(intencao_tipo, entidades, usuario, usuario_id, consulta)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # =========================================================================
    # 6. AGENT PLANNER v5.0 - Planeja e executa ferramentas
    # =========================================================================
    from .agent_planner import plan_and_execute

    resultado = plan_and_execute(
        consulta=consulta,
        dominio=dominio,
        entidades=entidades,
        intencao_original=intencao_tipo,
        usuario_id=usuario_id,
        usuario=usuario,
        contexto_estruturado=contexto_estruturado,
        conhecimento_negocio=conhecimento_negocio
    )

    # 6.1 Se AgentPlanner usou AutoLoader (resposta experimental)
    if resultado.get('experimental') and resultado.get('resposta_auto'):
        resposta = resultado['resposta_auto']
        resposta += "\n\n_[Resposta experimental - gerada automaticamente]_"
        _registrar_conversa(usuario_id, consulta, resposta, intencao, resultado)
        return resposta

    # 6.2 Se falhou completamente
    if not resultado.get('sucesso'):
        erro = resultado.get('erro', 'Não consegui processar sua consulta')
        resposta = f"Desculpe, {erro}\n\nQuer tentar de outra forma?"
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 6.3 Se não encontrou resultados
    if resultado.get('total_encontrado', 0) == 0:
        resposta = "Não encontrei resultados para sua consulta.\n\nQuer tentar de outra forma?"
        _registrar_conversa(usuario_id, consulta, resposta, intencao, resultado)
        return resposta

    # =========================================================================
    # 7. GERAR RESPOSTA
    # =========================================================================
    contexto_dados = _formatar_contexto_resultado(resultado)
    contexto_dados = _enriquecer_com_conceitos(contexto_dados, consulta)

    if usar_claude_resposta:
        from .responder import get_responder
        responder = get_responder()
        resposta = responder.gerar_resposta(
            consulta, contexto_dados, dominio, contexto_memoria,
            estado_estruturado=contexto_estruturado
        )
    else:
        resposta = contexto_dados

    # 7.1 Se resultado tem opções, salva no estado
    if usuario_id and resultado.get('opcoes'):
        _salvar_opcoes_no_estado(usuario_id, resultado['opcoes'])
        logger.info(f"[ORCHESTRATOR] {len(resultado['opcoes'])} opções salvas")

    # 7.2 Registra itens numerados para referência futura
    if usuario_id and resultado.get('dados'):
        dados = resultado['dados']
        if isinstance(dados, list) and len(dados) > 0:
            _registrar_itens_no_estado(usuario_id, dados)
            logger.info(f"[ORCHESTRATOR] {len(dados)} itens numerados")

    # 8. Registrar na memória
    _registrar_conversa(usuario_id, consulta, resposta, intencao, resultado)

    return resposta


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _buscar_memoria(usuario_id: int, incluir_aprendizados: bool = False) -> Optional[str]:
    """Busca contexto de memória do usuário."""
    try:
        from ..memory import MemoryService
        return MemoryService.formatar_contexto_memoria(usuario_id, incluir_aprendizados=incluir_aprendizados)
    except Exception as e:
        logger.warning(f"Erro ao buscar memória: {e}")
        return None


def _extrair_inteligente(consulta: str, contexto_estruturado: str, conhecimento_negocio: str = None) -> Dict[str, Any]:
    """
    Usa extrator inteligente com CONTEXTO ESTRUTURADO.

    O Claude recebe:
    - Mensagem do usuário
    - Estado ESTRUTURADO em JSON
    - Conhecimento do negócio

    Returns:
        Dict com dominio, intencao, entidades
    """
    try:
        from .intelligent_extractor import extrair_inteligente
        from .entity_mapper import mapear_extracao

        extracao = extrair_inteligente(consulta, contexto_estruturado, conhecimento_negocio)
        resultado = mapear_extracao(extracao)

        logger.info(f"[ORCHESTRATOR] Extração: {resultado.get('intencao')} "
                   f"com {len(resultado.get('entidades', {}))} entidades")

        return resultado

    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Erro na extração: {e}")
        return {
            'dominio': 'geral',
            'intencao': 'outro',
            'entidades': {},
            'erro': str(e)
        }


def _carregar_conhecimento_negocio(usuario_id: int = None) -> str:
    """Carrega conhecimento do negócio (aprendizados)."""
    try:
        from ..prompts.intent_prompt import _carregar_aprendizados_usuario
        return _carregar_aprendizados_usuario(usuario_id)
    except Exception:
        return ""


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


def _processar_clarificacao(intencao: Dict, usuario_id: int) -> str:
    """Processa situações onde o Claude detectou ambiguidade."""
    from .structured_state import EstadoManager

    ambiguidade = intencao.get('ambiguidade', {})
    entidades = intencao.get('entidades', {})

    pergunta = ambiguidade.get('pergunta', 'Poderia esclarecer sua solicitação?')
    opcoes = ambiguidade.get('opcoes', [])

    resposta = f"🤔 **Preciso de uma clarificação:**\n\n{pergunta}"

    if opcoes:
        resposta += "\n\n**Opções:**"
        for i, opcao in enumerate(opcoes, 1):
            resposta += f"\n{i}. {opcao}"

    if entidades:
        resposta += "\n\n📋 **O que já entendi:**"
        for chave, valor in list(entidades.items())[:5]:
            if not chave.startswith('_'):
                resposta += f"\n- {chave}: {valor}"

    # Atualiza estado para aguardar clarificação
    if usuario_id:
        estado = EstadoManager.obter(usuario_id)
        estado.estado_dialogo = 'aguardando_clarificacao'
        estado.acao_atual = 'clarificacao'

    logger.info(f"[ORCHESTRATOR] Solicitando clarificação: {pergunta}")
    return resposta


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


def _formatar_contexto_resultado(resultado: Dict) -> str:
    """
    Formata resultado do AgentPlanner para o responder.

    Args:
        resultado: Dict do AgentPlanner com dados, etapas_executadas, etc

    Returns:
        String formatada para contexto do responder
    """
    dados = resultado.get('dados', [])
    total = resultado.get('total_encontrado', 0)
    etapas = resultado.get('etapas_executadas', [])

    linhas = [f"=== RESULTADO DA CONSULTA ({total} itens) ==="]

    # Info sobre etapas executadas
    if len(etapas) > 1:
        linhas.append(f"\nExecutadas {len(etapas)} etapas:")
        for e in etapas:
            status = "✓" if e.get('sucesso') else "✗"
            linhas.append(f"  {status} {e.get('ferramenta')}: {e.get('total', 0)} resultados")
        linhas.append("")

    # Dados
    if dados:
        linhas.append("\nDADOS:")
        for i, item in enumerate(dados[:20], 1):
            if isinstance(item, dict):
                # Prioriza campos mais relevantes
                partes = []
                for campo in ['num_pedido', 'raz_social_red', 'cod_produto', 'nome_produto',
                              'qtd_saldo', 'expedicao', 'status']:
                    if campo in item and item[campo] is not None:
                        partes.append(f"{campo}: {item[campo]}")
                if partes:
                    linhas.append(f"{i}. {' | '.join(partes[:5])}")
            else:
                linhas.append(f"{i}. {item}")

        if total > 20:
            linhas.append(f"\n... e mais {total - 20} itens")

    return "\n".join(linhas)


def _salvar_opcoes_no_estado(usuario_id: int, opcoes: List[Dict]):
    """Salva opções no estado estruturado usando EstadoManager."""
    try:
        from .structured_state import EstadoManager

        # Formata opções para o EstadoManager
        lista_formatada = []
        for i, opcao in enumerate(opcoes[:3]):
            letra = chr(65 + i)  # A, B, C
            descricao = str(opcao.get('descricao', opcao)) if isinstance(opcao, dict) else str(opcao)
            lista_formatada.append({"letra": letra, "descricao": descricao})

        EstadoManager.definir_opcoes(
            usuario_id,
            motivo="Opções oferecidas",
            lista=lista_formatada,
            esperado_do_usuario="Escolher uma opção"
        )

    except Exception as e:
        logger.warning(f"Erro ao salvar opções: {e}")


def _registrar_itens_no_estado(usuario_id: int, dados: List[Dict]):
    """Registra itens numerados no estado para referência futura."""
    try:
        from .structured_state import EstadoManager

        EstadoManager.definir_consulta(
            usuario_id,
            tipo="itens",
            total=len(dados),
            itens=dados[:10]  # Limita a 10 itens
        )

    except Exception as e:
        logger.warning(f"Erro ao registrar itens: {e}")


def _registrar_conversa(usuario_id: int, consulta: str, resposta: str, intencao: dict, resultado: dict):
    """Registra conversa na memória e atualiza contexto."""
    if not usuario_id:
        return
    try:
        from ..memory import MemoryService
        from .structured_state import EstadoManager, FonteEntidade

        # Registra na memória
        MemoryService.registrar_conversa_completa(
            usuario_id=usuario_id, pergunta=consulta, resposta=resposta,
            intencao=intencao, resultado_busca=resultado
        )

        # Atualiza entidades no estado
        entidades = intencao.get('entidades', {}).copy() if intencao else {}

        if resultado:
            if resultado.get('num_pedido'):
                entidades['num_pedido'] = resultado['num_pedido']
            dados = resultado.get('dados')
            if isinstance(dados, list) and dados:
                primeiro = dados[0] if isinstance(dados[0], dict) else {}
                if primeiro.get('num_pedido'):
                    entidades['num_pedido'] = primeiro['num_pedido']

        # Atualiza cada entidade no EstadoManager
        for campo, valor in entidades.items():
            if valor and str(valor).lower() not in ('null', 'none', ''):
                EstadoManager.atualizar_entidade(
                    usuario_id, campo, valor, FonteEntidade.CONSULTA.value
                )

    except Exception as e:
        logger.warning(f"Erro ao registrar conversa: {e}")


def _enriquecer_com_conceitos(contexto_dados: str, consulta: str) -> str:
    """Enriquece o contexto com conceitos aprendidos relevantes."""
    try:
        from ..ia_trainer.services.codigo_loader import buscar_por_gatilho

        codigos = buscar_por_gatilho(consulta)
        conceitos_relevantes = [c for c in codigos if c.get('tipo_codigo') == 'conceito']

        if not conceitos_relevantes:
            return contexto_dados

        linhas_conceito = ["\n=== CONCEITOS RELEVANTES ==="]
        for conceito in conceitos_relevantes:
            linhas_conceito.append(f"- {conceito.get('nome', '')}: {conceito.get('descricao_claude', '')}")
        linhas_conceito.append("=== FIM DOS CONCEITOS ===\n")

        return contexto_dados + "\n".join(linhas_conceito)

    except Exception as e:
        logger.debug(f"[ORCHESTRATOR] Conceitos não disponíveis: {e}")
        return contexto_dados
