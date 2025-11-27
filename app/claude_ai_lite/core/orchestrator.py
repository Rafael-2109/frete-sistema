"""
Orquestrador do Claude AI Lite v5.7.

Coordena o fluxo completo:
1. Obter estado estruturado (CONDICIONAL via roteamento)
2. Carregar conhecimento do negócio (CONDICIONAL via roteamento)
3. Verificar comandos de aprendizado
4. BUSCAR HISTÓRICO INTELIGENTE (v5.7 - método v2!)
5. Extração inteligente (Claude) - COM HISTÓRICO para entender follow-ups
6. FALLBACK DE HERANÇA - Garante herança de contexto (v5.5 - inclui clarificação!)
7. Tratamento especial via HANDLERS EXTENSÍVEIS
8. AgentPlanner planeja e executa ferramentas
9. Gerar resposta
10. Registrar na memória COM CONTEXTO COMPLETO

FILOSOFIA v5.7:
- O Claude é o CÉREBRO - planeja E executa
- AgentPlanner substitui find_capability() -> cap.executar()
- Suporta múltiplas etapas (até 10 com justificativa)
- Fallback automático para AutoLoader
- Usa EstadoManager diretamente (ConversationContext removido)
- Handlers extensíveis para domínios customizados
- Fluxo flexível com roteamento (Claude decide etapas)
- Registro de contexto completo (filtros, domínio, capacidade)
- Fallback de herança trata CLARIFICAÇÃO
- NOVO v5.7: HISTÓRICO INTELIGENTE v2!
  - Busca por TEMPO (últimos 30min) ao invés de quantidade
  - Agrupa por INTERAÇÃO (nunca corta conversa pela metade)
  - Detecta INÍCIO DE CONVERSA por gap de 10min de inatividade

Criado em: 24/11/2025
Atualizado: 26/11/2025 - AgentPlanner v5.0, removido ConversationContext
Atualizado: 27/11/2025 - v5.1: Handlers extensíveis, fluxo flexível
Atualizado: 27/11/2025 - v5.2: Contexto completo para herança em follow-ups
Atualizado: 27/11/2025 - v5.3: Fallback de herança (safety net)
Atualizado: 27/11/2025 - v5.4: "detalhar" removido do follow_up, preserva tipo/total
Atualizado: 27/11/2025 - v5.5: Fallback herança trata clarificação → domínio anterior
Atualizado: 27/11/2025 - v5.6: Histórico da conversa passado para o extrator
Atualizado: 27/11/2025 - v5.7: Histórico INTELIGENTE v2 (tempo/interação/gap)
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# REGISTRY DE HANDLERS EXTENSÍVEIS
# =============================================================================

# Handlers padrão para domínios conhecidos
# Novos handlers podem ser registrados em runtime via registrar_handler()
_HANDLERS_DOMINIO: Dict[str, Callable] = {}


def registrar_handler(dominio: str, handler: Callable):
    """
    Registra handler customizado para um domínio.

    Args:
        dominio: Nome do domínio (ex: "urgente", "preview")
        handler: Função que processa o domínio

    Exemplo:
        def processar_urgente(intencao, entidades, usuario, usuario_id, texto, memoria):
            return "Processando urgente..."

        registrar_handler("urgente", processar_urgente)
    """
    _HANDLERS_DOMINIO[dominio] = handler
    logger.info(f"[ORCHESTRATOR] Handler registrado para domínio: {dominio}")


def _obter_handler(intencao: Dict) -> Optional[Callable]:
    """
    Obtém handler para o domínio/intenção.

    Prioridade:
    1. Handlers customizados da config
    2. Handlers registrados em runtime
    3. Handlers padrão internos

    Args:
        intencao: Dict com dominio e intencao

    Returns:
        Função handler ou None
    """
    from ..config import get_config

    dominio = intencao.get('dominio', '')
    intencao_tipo = intencao.get('intencao', '')
    config = get_config()

    # 1. Handlers customizados da config têm prioridade
    if dominio in config.orquestracao.handlers_customizados:
        handler_name = config.orquestracao.handlers_customizados[dominio]
        handler = globals().get(handler_name)
        if handler:
            logger.debug(f"[ORCHESTRATOR] Usando handler customizado: {handler_name}")
            return handler

    # 2. Handlers registrados em runtime
    if dominio in _HANDLERS_DOMINIO:
        logger.debug(f"[ORCHESTRATOR] Usando handler registrado: {dominio}")
        return _HANDLERS_DOMINIO[dominio]

    # 3. Handlers padrão internos (tratamento especial)
    if dominio == "clarificacao":
        return _handler_clarificacao
    # v5.4: "detalhar" REMOVIDO - deve ir pro AgentPlanner fazer nova query
    # follow_up é para perguntas sobre o MESMO resultado ("qual o maior?", "quem é o primeiro?")
    # detalhar precisa de NOVA consulta com agrupamento diferente
    if dominio == "follow_up" or intencao_tipo == "follow_up":
        return _handler_follow_up
    if dominio == "acao":
        return _handler_acao

    return None


def _handler_clarificacao(intencao: Dict, entidades: Dict, usuario: str,
                          usuario_id: int, texto: str, memoria: str) -> str:
    """Handler interno para clarificação."""
    return _processar_clarificacao(intencao, usuario_id)


def _handler_follow_up(intencao: Dict, entidades: Dict, usuario: str,
                       usuario_id: int, texto: str, memoria: str) -> str:
    """Handler interno para follow-up."""
    return _processar_follow_up(texto, memoria, usuario_id)


def _handler_acao(intencao: Dict, entidades: Dict, usuario: str,
                  usuario_id: int, texto: str, memoria: str) -> str:
    """Handler interno para ações."""
    intencao_tipo = intencao.get('intencao', '')
    return _processar_acao(intencao_tipo, entidades, usuario, usuario_id, texto)


def processar_consulta(
    consulta: str,
    usar_claude_resposta: bool = True,
    usuario: str = "Claude AI",
    usuario_id: int = None
) -> str:
    """
    Processa consulta em linguagem natural com fluxo flexível.

    O fluxo é dinâmico - etapas podem ser puladas baseado no roteamento
    retornado pela extração inteligente.

    Args:
        consulta: Texto do usuário
        usar_claude_resposta: Se deve elaborar resposta com Claude
        usuario: Nome do usuário
        usuario_id: ID do usuário (para memória)

    Returns:
        Resposta formatada
    """
    from ..config import get_config
    config = get_config()

    # 1. SEMPRE: Validação básica
    if not consulta or not consulta.strip():
        return "Por favor, informe sua consulta."

    # 2. Verificar comando de aprendizado (antes de tudo - sempre executa)
    if usuario_id:
        resultado_aprendizado = _verificar_aprendizado(consulta, usuario_id, usuario)
        if resultado_aprendizado:
            _registrar_conversa(usuario_id, consulta, resultado_aprendizado, None, None)
            return resultado_aprendizado

    # 3. CONDICIONAL: Obter ESTADO ESTRUTURADO (JSON)
    # Por padrão carrega, mas roteamento pode pular
    contexto_estruturado = ""
    if usuario_id:
        from .structured_state import obter_estado_json
        contexto_estruturado = obter_estado_json(usuario_id)
        if contexto_estruturado:
            logger.debug(f"[ORCHESTRATOR] Estado estruturado: {len(contexto_estruturado)} chars")

    # 4. CONDICIONAL: Carregar conhecimento do negócio (aprendizados)
    # Por padrão carrega, mas roteamento pode pular
    conhecimento_negocio = _carregar_conhecimento_negocio(usuario_id)
    if conhecimento_negocio:
        logger.debug(f"[ORCHESTRATOR] Conhecimento carregado: {len(conhecimento_negocio)} chars")

    # 4.1 v5.7: Busca histórico INTELIGENTE para extrator
    # Usa novo método v2 que:
    # - Busca por TEMPO (últimos 30min)
    # - Agrupa por INTERAÇÃO (nunca corta pela metade)
    # - Detecta INÍCIO DE CONVERSA (gap de 10min)
    historico_conversa = None
    if usuario_id:
        from ..memory import MemoryService
        historico_conversa = MemoryService.buscar_historico_para_extrator(usuario_id)
        if historico_conversa:
            logger.debug(f"[ORCHESTRATOR] Histórico v2 para extrator: {len(historico_conversa)} chars")

    # 5. SEMPRE: EXTRAÇÃO INTELIGENTE - Delega ao Claude
    # Retorna também roteamento para controlar fluxo
    # v5.6: Agora passa histórico da conversa para entender follow-ups
    intencao = _extrair_inteligente(consulta, contexto_estruturado, conhecimento_negocio, historico_conversa)

    dominio = intencao.get("dominio", "geral")
    intencao_tipo = intencao.get("intencao", "")
    entidades = intencao.get("entidades", {})
    roteamento = intencao.get("roteamento", {})

    # Log do roteamento se presente
    if roteamento:
        logger.debug(f"[ORCHESTRATOR] Roteamento: {roteamento}")

    logger.info(f"[ORCHESTRATOR] dominio={dominio}, intencao={intencao_tipo}, "
               f"entidades={list(entidades.keys())}")

    # 5.1 FALLBACK DE HERANÇA v5.5 - Garante que contexto seja herdado
    # Se o Claude do extrator não herdou cliente_atual, fazemos aqui
    # v5.5: Agora também trata clarificação - se há contexto válido, não pede clarificação!
    if usuario_id:
        entidades, intencao, heranca_aplicada = _aplicar_fallback_heranca(
            usuario_id, entidades, dominio, intencao
        )
        # Atualiza domínio e intenção_tipo se mudaram
        if heranca_aplicada:
            dominio = intencao.get("dominio", dominio)
            intencao_tipo = intencao.get("intencao", intencao_tipo)
            logger.debug(f"[ORCHESTRATOR] Pós-herança: dominio={dominio}, intencao={intencao_tipo}")

    # 5.2 Atualiza estado estruturado com entidades extraídas
    if usuario_id and entidades:
        from .structured_state import EstadoManager
        EstadoManager.atualizar_do_extrator(usuario_id, entidades)
        logger.debug(f"[ORCHESTRATOR] Estado atualizado com {len(entidades)} entidades")

    # 5.2 CONDICIONAL: Buscar contexto de memória (roteamento pode pular)
    contexto_memoria = None
    deve_buscar_memoria = roteamento.get('buscar_memoria', True)
    if usuario_id and deve_buscar_memoria:
        contexto_memoria = _buscar_memoria(usuario_id)
    elif not deve_buscar_memoria:
        logger.debug(f"[ORCHESTRATOR] Memória pulada: {roteamento.get('motivo', 'sem motivo')}")

    # 6. HANDLERS EXTENSÍVEIS - Tratamentos especiais
    # Usa sistema de handlers em vez de IFs hardcoded
    handler = _obter_handler(intencao)
    if handler:
        resposta = handler(intencao, entidades, usuario, usuario_id, consulta, contexto_memoria)
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

        # 7.0 NOVO: Verifica se precisa reprocessar (dados não correspondem ao contexto)
        if resposta.startswith('[REPROCESSAR]'):
            problema = resposta.replace('[REPROCESSAR]', '').replace('[/REPROCESSAR]', '')
            logger.warning(f"[ORCHESTRATOR] Reprocessando: {problema}")

            # Tenta novamente com direcionamento mais específico
            entidades_forcadas = entidades.copy()

            # Garante que entidades do estado sejam incluídas
            from .structured_state import EstadoManager
            estado = EstadoManager.obter(usuario_id)
            for campo, dados in estado.entidades.items():
                if campo not in entidades_forcadas:
                    valor = dados.get('valor') if isinstance(dados, dict) else dados
                    if valor:
                        entidades_forcadas[campo] = valor

            # Adiciona direcionamento no contexto
            consulta_direcionada = f"{consulta} [IMPORTANTE: Filtrar por {', '.join(f'{k}={v}' for k, v in entidades_forcadas.items() if k in ['raz_social_red', 'num_pedido'])}]"

            resultado_retry = plan_and_execute(
                consulta=consulta_direcionada,
                dominio=dominio,
                entidades=entidades_forcadas,
                intencao_original=intencao_tipo,
                usuario_id=usuario_id,
                usuario=usuario,
                contexto_estruturado=contexto_estruturado,
                conhecimento_negocio=conhecimento_negocio
            )

            if resultado_retry.get('sucesso') and resultado_retry.get('total_encontrado', 0) > 0:
                resultado = resultado_retry
                contexto_dados = _formatar_contexto_resultado(resultado)
                contexto_dados = _enriquecer_com_conceitos(contexto_dados, consulta)
                resposta = responder.gerar_resposta(
                    consulta, contexto_dados, dominio, contexto_memoria,
                    estado_estruturado=contexto_estruturado
                )
                logger.info("[ORCHESTRATOR] Reprocessamento bem-sucedido")
            else:
                # Se retry também falhou, informa ao usuário
                resposta = f"Não encontrei dados específicos do cliente/pedido solicitado.\n\n{problema}\n\nPoderia reformular sua pergunta?"
    else:
        resposta = contexto_dados

    # 7.1 Se resultado tem opções, salva no estado
    if usuario_id and resultado.get('opcoes'):
        _salvar_opcoes_no_estado(usuario_id, resultado['opcoes'])
        logger.info(f"[ORCHESTRATOR] {len(resultado['opcoes'])} opções salvas")

    # 7.2 Registra itens numerados e contexto completo para referência futura (v5.4)
    if usuario_id and resultado.get('dados'):
        dados = resultado['dados']
        if isinstance(dados, list) and len(dados) > 0:
            # v5: Extrai contexto completo para herança em follow-ups
            filtros_aplicados = _extrair_filtros_do_resultado(resultado, entidades)
            capacidade_usada = _extrair_capacidade_do_resultado(resultado)

            # v5.4: Extrai tipo/total do resultado (se disponível)
            tipo_consulta = resultado.get('tipo_consulta')  # capability pode informar
            total_real = resultado.get('total_encontrado', len(dados))

            _registrar_itens_no_estado(
                usuario_id,
                dados,
                dominio=dominio,
                capacidade=capacidade_usada,
                filtros_aplicados=filtros_aplicados,
                resumo=f"Consulta: {intencao_tipo or 'geral'}",
                # v5.4: Preserva tipo/total originais
                tipo=tipo_consulta,
                total_encontrado=total_real
            )
            logger.info(f"[ORCHESTRATOR] {len(dados)} itens (total_real={total_real}), "
                       f"filtros={filtros_aplicados}")

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


def _extrair_inteligente(
    consulta: str,
    contexto_estruturado: str,
    conhecimento_negocio: str = None,
    historico_conversa: str = None
) -> Dict[str, Any]:
    """
    Usa extrator inteligente com CONTEXTO ESTRUTURADO + HISTÓRICO.

    O Claude recebe:
    - Mensagem do usuário
    - Estado ESTRUTURADO em JSON
    - Conhecimento do negócio
    - v5.6: Histórico recente da conversa (CRÍTICO para follow-ups!)

    Returns:
        Dict com dominio, intencao, entidades
    """
    try:
        from .intelligent_extractor import extrair_inteligente
        from .entity_mapper import mapear_extracao

        # v5.6: Passa histórico para o extrator entender follow-ups
        extracao = extrair_inteligente(
            consulta,
            contexto_estruturado,
            conhecimento_negocio,
            historico_conversa
        )
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

    IMPORTANTE: Deve exibir TODOS os campos retornados, não apenas uma lista fixa.
    Isso permite que agregações (total_faturado, total_notas) sejam exibidas.
    Também formata OPÇÕES de envio quando presentes (analisar_disponibilidade).

    v2.0 (27/11/2025):
    - Adicionado tratamento para tipo_consulta="pedidos_abertos_disponibilidade"
    - Formatação especializada para análise de pedidos em aberto

    Args:
        resultado: Dict do AgentPlanner com dados, etapas_executadas, etc

    Returns:
        String formatada para contexto do responder
    """
    # v2.0: Se é consulta de pedidos em aberto, usa formatação especializada
    if resultado.get('tipo_consulta') == 'pedidos_abertos_disponibilidade':
        return _formatar_pedidos_abertos(resultado)

    # Se tem opções de envio, usa formatação especial
    if resultado.get('opcoes'):
        return _formatar_opcoes_envio(resultado)

    # v2.0: Se tem análise por cliente (total_pallets), formatação específica
    if resultado.get('total_pallets') is not None:
        return _formatar_analise_cliente(resultado)

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

        # Detecta se é resultado de agregação (poucos registros com campos tipo total_, sum_, etc)
        eh_agregacao = len(dados) <= 5 and any(
            any(k.startswith(('total_', 'sum_', 'count_', 'avg_', 'min_', 'max_'))
                for k in (item.keys() if isinstance(item, dict) else []))
            for item in dados
        )

        for i, item in enumerate(dados[:20], 1):
            if isinstance(item, dict):
                if eh_agregacao:
                    # Para agregação: mostra TODOS os campos
                    partes = []
                    for campo, valor in item.items():
                        if valor is not None:
                            # Formata valores numéricos grandes
                            if isinstance(valor, (int, float)) and valor > 1000:
                                if isinstance(valor, float):
                                    partes.append(f"{campo}: R$ {valor:,.2f}")
                                else:
                                    partes.append(f"{campo}: {valor:,}")
                            else:
                                partes.append(f"{campo}: {valor}")
                    linhas.append(f"{i}. {' | '.join(partes)}")
                else:
                    # Para listagens: prioriza campos mais relevantes
                    campos_prio = ['num_pedido', 'raz_social_red', 'cod_produto', 'nome_produto',
                                   'qtd_saldo', 'valor_saldo', 'expedicao', 'status', 'data_pedido',
                                   'total_qtd', 'total_itens', 'valor_total']
                    partes = []
                    for campo in campos_prio:
                        if campo in item and item[campo] is not None:
                            valor = item[campo]
                            if isinstance(valor, (int, float)) and valor > 1000:
                                if isinstance(valor, float):
                                    partes.append(f"{campo}: R$ {valor:,.2f}")
                                else:
                                    partes.append(f"{campo}: {valor:,}")
                            else:
                                partes.append(f"{campo}: {valor}")

                    # Se não encontrou campos prioritários, mostra todos
                    if not partes:
                        for campo, valor in list(item.items())[:6]:
                            if valor is not None:
                                partes.append(f"{campo}: {valor}")

                    if partes:
                        linhas.append(f"{i}. {' | '.join(partes[:6])}")
            else:
                linhas.append(f"{i}. {item}")

        if total > 20:
            linhas.append(f"\n... e mais {total - 20} itens")

    return "\n".join(linhas)


def _formatar_opcoes_envio(resultado: Dict) -> str:
    """
    Formata opções de envio (analisar_disponibilidade).

    Args:
        resultado: Dict com opcoes, analise, num_pedido, cliente, etc

    Returns:
        String formatada para contexto do responder
    """
    opcoes = resultado.get('opcoes', [])
    analise = resultado.get('analise', {})
    num_pedido = resultado.get('num_pedido', analise.get('num_pedido', 'N/A'))
    cliente = resultado.get('cliente', {})
    valor_total = resultado.get('valor_total_pedido', analise.get('valor_total', 0))

    # Extrai nome do cliente
    if isinstance(cliente, dict):
        nome_cliente = cliente.get('razao_social', cliente.get('nome', 'N/A'))
    else:
        nome_cliente = str(cliente) if cliente else 'N/A'

    linhas = [
        f"=== ANÁLISE DE DISPONIBILIDADE - Pedido {num_pedido} ===",
        f"Cliente: {nome_cliente}",
        f"Valor Total do Pedido: R$ {valor_total:,.2f}",
        "",
        "=== OPÇÕES DE ENVIO ===",
        ""
    ]

    for opcao in opcoes:
        codigo = opcao.get("codigo", "?")
        titulo = opcao.get("titulo", "Sem título")
        data_envio = opcao.get("data_envio", "Sem previsão")
        dias = opcao.get("dias_para_envio")
        valor = opcao.get("valor", 0)
        percentual = opcao.get("percentual", 0)
        qtd_itens = opcao.get("qtd_itens", 0)

        linhas.append(f"--- OPÇÃO {codigo}: {titulo} ---")
        linhas.append(f"  Data de Envio: {data_envio}")

        if dias is not None:
            if dias == 0:
                linhas.append(f"  Disponível: HOJE")
            else:
                linhas.append(f"  Aguardar: {dias} dia(s)")

        linhas.append(f"  Valor: R$ {valor:,.2f} ({percentual:.1f}% do pedido)")
        linhas.append(f"  Itens: {qtd_itens}")

        # Lista itens incluídos (resumido)
        itens = opcao.get("itens", [])
        for item in itens[:3]:
            nome = item.get('nome_produto', item.get('nome', '?'))[:35]
            qtd = item.get('quantidade', 0)
            disponivel = item.get('disponivel_hoje', False)
            status = "OK" if disponivel else "Aguardar"
            linhas.append(f"    - {nome}: {qtd:.0f}un [{status}]")

        if len(itens) > 3:
            linhas.append(f"    ... e mais {len(itens) - 3} itens")

        # Lista itens excluídos
        excluidos = opcao.get("itens_excluidos", [])
        if excluidos:
            linhas.append(f"  ITENS NÃO INCLUÍDOS:")
            for item in excluidos[:2]:
                nome = item.get('nome_produto', '?')[:35]
                qtd = item.get('quantidade', 0)
                valor_item = item.get('valor_total', 0)
                linhas.append(f"    X {nome}: {qtd:.0f}un (R$ {valor_item:,.2f})")

        linhas.append("")

    linhas.append("Para criar separação, responda com a opção desejada (A, B ou C).")

    return "\n".join(linhas)


def _formatar_pedidos_abertos(resultado: Dict) -> str:
    """
    v2.0: Formata resultado de pedidos em aberto com análise de disponibilidade.

    Mostra:
    - Resumo geral (total, disponíveis, valor)
    - Lista de pedidos ordenados (disponíveis primeiro)
    - Detalhe de itens por pedido
    - Gargalos e data de disponibilidade total para pedidos parciais
    """
    resumo = resultado.get('resumo', resultado.get('analise', {}))
    pedidos = resultado.get('dados', [])

    linhas = [
        f"=== PEDIDOS EM ABERTO - {resumo.get('cliente', 'Cliente')} ===",
        "",
        f"📊 RESUMO:",
        f"   Total de pedidos em aberto: {resumo.get('total_pedidos_abertos', len(pedidos))}",
        f"   ✅ Disponíveis para envio TOTAL: {resumo.get('pedidos_disponiveis', 0)}",
        f"   ⚠️ Parcialmente disponíveis: {resumo.get('pedidos_parciais', 0)}",
        "",
        f"💰 VALORES:",
        f"   Valor total em aberto: R$ {resumo.get('valor_total_aberto', 0):,.2f}",
        f"   Valor disponível hoje: R$ {resumo.get('valor_disponivel', 0):,.2f}",
        f"   Peso total: {resumo.get('peso_total', 0):,.0f} kg",
        f"   Pallets total: {resumo.get('pallets_total', 0):.1f}",
        "",
        "=" * 60,
        ""
    ]

    # Lista de pedidos (limita a 10)
    for i, p in enumerate(pedidos[:10], 1):
        todos_disp = p.get("todos_disponiveis", False)
        percentual = p.get('percentual_disponivel', 0)
        status = "✅ DISPONÍVEL" if todos_disp else f"⚠️ PARCIAL ({percentual}%)"
        linhas.append(f"--- {i}. Pedido: {p.get('num_pedido', 'N/A')} | {status} ---")
        linhas.append(f"   Cliente: {p.get('raz_social_red', 'N/A')}")
        linhas.append(f"   Valor: R$ {p.get('valor_total', 0):,.2f}")
        linhas.append(f"   Peso: {p.get('peso_total', 0):,.0f}kg | Pallets: {p.get('pallets_total', 0):.2f}")
        linhas.append(f"   Itens: {p.get('itens_disponiveis', 0)}/{p.get('total_itens', 0)} disponíveis")

        # Se tem data de disponibilidade total (pedido parcial)
        if not todos_disp and p.get('data_disponibilidade_total'):
            linhas.append(f"   📅 Previsão todos disponíveis: {p['data_disponibilidade_total']}")

        # Mostra gargalos (itens que impedem envio hoje)
        gargalos = p.get('gargalos', [])
        if gargalos:
            linhas.append(f"   🔴 GARGALOS ({len(gargalos)} item(ns)):")
            for g in gargalos[:3]:
                linhas.append(
                    f"      - {g.get('nome_produto', 'N/A')[:30]}: "
                    f"faltam {g.get('falta', 0):.0f}un "
                    f"(previsão: {g.get('data_disponivel', 'N/A')})"
                )
            if len(gargalos) > 3:
                linhas.append(f"      ... e mais {len(gargalos) - 3} gargalos")

        # Mostra itens resumidos (apenas se poucos gargalos)
        itens = p.get("itens", [])
        if len(gargalos) < 2:
            for item in itens[:3]:
                disp = "✅" if item.get("disponivel") else "❌"
                linhas.append(
                    f"      {disp} {item.get('nome_produto', 'N/A')[:35]}: "
                    f"{item.get('saldo_real', 0):.0f}un (estoque: {item.get('estoque_atual', 0):.0f})"
                )
            if len(itens) > 3:
                linhas.append(f"      ... e mais {len(itens) - 3} itens")

        linhas.append("")

    if len(pedidos) > 10:
        linhas.append(f"... e mais {len(pedidos) - 10} pedidos")
        linhas.append("")

    # Mensagem de ajuda
    linhas.append("=" * 60)
    linhas.append("💡 AÇÕES DISPONÍVEIS:")
    linhas.append("   - 'Qual o valor desses pedidos?' → Mostra valores")
    linhas.append("   - 'Qual o maior?' → Mostra o pedido de maior valor disponível")
    linhas.append("   - 'Programe o pedido X pro dia DD/MM' → Cria separação")

    return "\n".join(linhas)


def _formatar_analise_cliente(resultado: Dict) -> str:
    """
    v2.0: Formata análise de disponibilidade por CLIENTE com pallets calculados.
    """
    analise = resultado.get("analise", {})
    itens = resultado.get("dados", [])
    carga = resultado.get("carga_sugerida", {})

    linhas = [
        f"=== ANÁLISE DE DISPONIBILIDADE - Cliente: {analise.get('cliente', 'N/A')} ===",
        "",
        f"📦 RESUMO DE PALLETS:",
        f"   Total na carteira: {analise.get('total_pallets', 0):.1f} pallets",
        f"   Disponível HOJE: {analise.get('pallets_disponiveis_hoje', 0):.1f} pallets",
        f"   Total de itens: {analise.get('itens_total', 0)}",
        f"   Itens disponíveis hoje: {analise.get('itens_disponiveis_hoje', 0)}",
        f"   Peso total: {analise.get('total_peso', 0):,.0f} kg",
    ]

    if analise.get('excluiu_separados'):
        linhas.append(f"   (Excluídos itens já separados)")

    # Mensagem principal se pediu quantidade específica
    if analise.get('mensagem'):
        linhas.append("")
        linhas.append(f"🎯 {analise['mensagem']}")

    # === CARGA SUGERIDA (se existe) ===
    if carga.get("pode_montar") and carga.get("itens"):
        linhas.append("")
        linhas.append("=" * 50)
        linhas.append("📋 CARGA SUGERIDA")
        linhas.append("=" * 50)
        linhas.append(f"   Total: {carga.get('total_pallets', 0):.1f} pallets")
        linhas.append(f"   Peso: {carga.get('total_peso', 0):,.0f} kg")
        linhas.append(f"   Valor: R$ {carga.get('total_valor', 0):,.2f}")
        linhas.append(f"   Itens: {len(carga.get('itens', []))}")

        if carga.get("todos_disponiveis_hoje"):
            linhas.append(f"   Status: ✅ TODOS DISPONÍVEIS HOJE")
        else:
            linhas.append(f"   Status: ⏳ {carga.get('itens_aguardar', 0)} item(ns) aguardando estoque")

        linhas.append("")
        linhas.append("--- ITENS DA CARGA ---")

        for i, item in enumerate(carga.get("itens", []), 1):
            status = "✅" if item.get('disponivel_hoje') else "⏳"
            fracionado = item.get('fracionado', False)

            if fracionado:
                linhas.append(
                    f"  {i}. [{status}] {item.get('nome_produto', 'N/A')[:40]} ✂️ PARCIAL"
                )
                linhas.append(
                    f"      Pedido: {item.get('num_pedido', 'N/A')} | "
                    f"{item.get('quantidade', 0):.0f} de {item.get('quantidade_original', 0):.0f} un "
                    f"({item.get('percentual_usado', 0):.0f}%) = {item.get('pallets', 0):.2f} pallets | "
                    f"R$ {item.get('valor', 0):,.2f}"
                )
            else:
                linhas.append(
                    f"  {i}. [{status}] {item.get('nome_produto', 'N/A')[:40]}"
                )
                linhas.append(
                    f"      Pedido: {item.get('num_pedido', 'N/A')} | "
                    f"{item.get('quantidade', 0):.0f} un = {item.get('pallets', 0):.2f} pallets | "
                    f"R$ {item.get('valor', 0):,.2f}"
                )

        linhas.append("")
        linhas.append("💬 Para criar separação com estes itens, responda: 'CONFIRMAR CARGA'")
        linhas.append("   ou ajuste a quantidade e pergunte novamente.")

    else:
        # Sem carga sugerida, mostra lista geral de itens
        linhas.append("")
        linhas.append("--- ITENS DETALHADOS ---")

        for i, item in enumerate(itens[:15], 1):
            status = "✅ OK" if item.get('disponivel_hoje') else "⏳ Aguardar"
            linhas.append(
                f"{i}. {item.get('nome_produto', 'N/A')[:35]} | "
                f"Pedido: {item.get('num_pedido', 'N/A')} | "
                f"{item.get('quantidade', 0):.0f} un = {item.get('pallets', 0):.2f} pallets | "
                f"[{status}]"
            )

        if len(itens) > 15:
            linhas.append(f"... e mais {len(itens) - 15} itens")

    return "\n".join(linhas)


def _salvar_opcoes_no_estado(usuario_id: int, opcoes: List[Dict]):
    """Salva opções no estado estruturado usando EstadoManager."""
    try:
        from .structured_state import EstadoManager
        from ..config import get_config

        config = get_config()
        max_opcoes = config.resposta.max_opcoes  # Usa config (default: 5)

        # Formata opções para o EstadoManager (agora flexível: 2-5 opções)
        lista_formatada = []
        for i, opcao in enumerate(opcoes[:max_opcoes]):
            letra = chr(65 + i)  # A, B, C, D, E...
            descricao = str(opcao.get('descricao', opcao)) if isinstance(opcao, dict) else str(opcao)
            lista_formatada.append({"letra": letra, "descricao": descricao})

        # Gera string de opções válidas para feedback
        opcoes_str = ", ".join([op["letra"] for op in lista_formatada])

        EstadoManager.definir_opcoes(
            usuario_id,
            motivo="Opções oferecidas",
            lista=lista_formatada,
            esperado_do_usuario=f"Escolher uma opção ({opcoes_str})"
        )

        logger.debug(f"[ORCHESTRATOR] {len(lista_formatada)} opções salvas: {opcoes_str}")

    except Exception as e:
        logger.warning(f"Erro ao salvar opções: {e}")


def _registrar_itens_no_estado(
    usuario_id: int,
    dados: List[Dict],
    # v5: Contexto completo para herança em follow-ups
    dominio: str = None,
    capacidade: str = None,
    filtros_aplicados: Dict[str, Any] = None,
    agrupamento: str = None,
    resumo: str = None,
    # v5.4: Preservar tipo/total originais do resultado
    tipo: str = None,
    total_encontrado: int = None
):
    """
    Registra itens e contexto completo no estado (v5.4).

    Isso é CRÍTICO para que follow-ups funcionem corretamente.
    Quando o usuário pergunta "o que está pendente?", o estado
    preserva o contexto da consulta anterior (cliente, domínio, etc).

    v5.4: Agora preserva tipo/total originais do resultado (se fornecidos).
    Isso evita perder informação de consultas agregadas.

    O limite de itens para serialização está em EstadoManager.definir_consulta.
    """
    try:
        from .structured_state import EstadoManager

        # v5.4: Usa tipo/total fornecidos ou fallback para valores padrão
        tipo_final = tipo or "itens"
        total_final = total_encontrado if total_encontrado is not None else len(dados)

        EstadoManager.definir_consulta(
            usuario_id,
            tipo=tipo_final,
            total=total_final,
            itens=dados,  # Passa todos; limite aplicado em definir_consulta
            # v5: Contexto completo
            dominio=dominio,
            capacidade=capacidade,
            filtros_aplicados=filtros_aplicados,
            agrupamento=agrupamento,
            resumo=resumo
        )

        logger.debug(f"[ORCHESTRATOR] Estado atualizado: {len(dados)} itens, "
                    f"dominio={dominio}, filtros={filtros_aplicados}")

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


def _aplicar_fallback_heranca(
    usuario_id: int,
    entidades: Dict,
    dominio: str,
    intencao: Dict
) -> Tuple[Dict, Dict, bool]:
    """
    Fallback de herança v5.5 - Garante que contexto seja herdado.

    Se o Claude do extrator NÃO incluiu raz_social_red nas entidades,
    mas existe REFERENCIA.cliente_atual no estado E consulta_ativa=true,
    então herdamos automaticamente.

    v5.5: Agora também aplica para domínio "clarificacao"!
    Isso evita que o Claude pergunte "de qual cliente?" quando
    já existe um cliente_atual válido no contexto.
    Quando herda em clarificação, MUDA o domínio para o domínio anterior!

    Isso é um SAFETY NET caso o Claude "esqueça" de herdar.

    Args:
        usuario_id: ID do usuário
        entidades: Dict de entidades extraídas pelo Claude
        dominio: Domínio da consulta
        intencao: Dict completo da intenção (será modificado se necessário)

    Returns:
        Tuple (entidades, intencao_modificada, heranca_aplicada)
        - entidades: Dict de entidades (possivelmente enriquecido com herança)
        - intencao: Dict de intenção (possivelmente com domínio alterado)
        - heranca_aplicada: True se herança foi aplicada
    """
    heranca_aplicada = False

    try:
        from .structured_state import EstadoManager

        estado = EstadoManager.obter(usuario_id)
        ref = estado.referencia

        # Verifica condições para herança:
        # 1. consulta_ativa = True (há contexto válido)
        # 2. cliente_atual existe
        # 3. raz_social_red NÃO está nas entidades (Claude não herdou)
        # 4. Domínio é compatível OU é clarificação (v5.5)
        dominios_compativeis = ['carteira', 'geral', 'clarificacao', None, '']

        if (ref.get('consulta_ativa') and
            ref.get('cliente_atual') and
            not entidades.get('raz_social_red') and
            dominio in dominios_compativeis):

            # Aplica herança
            entidades = entidades.copy()  # Não modifica original
            entidades['raz_social_red'] = ref['cliente_atual']
            heranca_aplicada = True

            # v5.5: Se era clarificação, muda para o domínio anterior
            # Isso evita que o handler de clarificação seja chamado
            if dominio == 'clarificacao':
                dominio_anterior = ref.get('dominio_atual', 'carteira')
                intencao = intencao.copy()
                intencao['dominio'] = dominio_anterior
                # Se a intenção era pedir clarificação, muda para consulta genérica
                if intencao.get('intencao') in ['pedir_cliente', 'pedir_clarificacao', 'clarificacao']:
                    intencao['intencao'] = 'consultar_pendentes'  # Intenção padrão

                logger.info(f"[ORCHESTRATOR] FALLBACK HERANÇA (clarificacao→{dominio_anterior}): "
                           f"herdou raz_social_red='{ref['cliente_atual']}' do contexto")
            else:
                logger.info(f"[ORCHESTRATOR] FALLBACK HERANÇA: "
                           f"herdou raz_social_red='{ref['cliente_atual']}' do contexto")

        return entidades, intencao, heranca_aplicada

    except Exception as e:
        logger.warning(f"[ORCHESTRATOR] Erro no fallback de herança: {e}")
        return entidades, intencao, False


def _extrair_filtros_do_resultado(resultado: Dict, entidades: Dict) -> Dict[str, Any]:
    """
    Extrai filtros aplicados do resultado e entidades (v5).

    Esses filtros são CRÍTICOS para herança de contexto em follow-ups.
    Quando o usuário pergunta "e o que está pendente?", os filtros
    permitem saber que é "pendente DO ASSAI" (do contexto anterior).
    """
    filtros = {}

    # 1. Extrai de entidades (fonte mais confiável)
    campos_filtro = ['raz_social_red', 'num_pedido', 'cod_produto', 'cod_uf', 'rota', 'vendedor']
    for campo in campos_filtro:
        if entidades.get(campo):
            filtros[campo] = entidades[campo]

    # 2. Extrai de resultado.cliente (algumas capabilities retornam isso)
    if resultado.get('cliente'):
        cliente = resultado['cliente']
        if isinstance(cliente, dict):
            filtros['raz_social_red'] = cliente.get('razao_social') or cliente.get('nome')
        elif isinstance(cliente, str):
            filtros['raz_social_red'] = cliente

    # 3. Extrai de dados[0] se não tiver nos outros
    if not filtros.get('raz_social_red'):
        dados = resultado.get('dados', [])
        if dados and isinstance(dados[0], dict):
            primeiro = dados[0]
            if primeiro.get('raz_social_red'):
                filtros['raz_social_red'] = primeiro['raz_social_red']

    return filtros


def _extrair_capacidade_do_resultado(resultado: Dict) -> Optional[str]:
    """
    Extrai nome da capacidade/ferramenta usada (v5).
    """
    etapas = resultado.get('etapas_executadas', [])
    if etapas:
        # Retorna a primeira ferramenta que teve sucesso
        for etapa in etapas:
            if etapa.get('sucesso') and etapa.get('ferramenta'):
                return etapa['ferramenta']
    return None


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
