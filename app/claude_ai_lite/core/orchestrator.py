"""
Orquestrador do Claude AI Lite.

Coordena o fluxo completo:
1. Verifica comandos de aprendizado
2. Classifica intenção
3. Analisa complexidade da pergunta
4. Encontra capacidade
5. Executa e gera resposta
6. Registra na memória
7. Loga perguntas não respondidas com sugestões

Limite: 200 linhas
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

    confianca = intencao.get("confianca", 0.0)

    # 3.1 Se confiança baixa, re-classificar com contexto do README
    if confianca < 0.7:
        intencao = _reclassificar_com_readme(classifier, consulta, contexto_memoria, intencao)

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
        # Tenta loaders aprendidos ou auto-gera em tempo real
        resposta = _tratar_sem_capacidade(consulta, intencao, usuario_id, usuario)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 7. Extrair critério de busca
    campo, valor = capacidade.extrair_valor_busca(entidades)
    if not campo or not valor:
        # Tenta auto-loader primeiro (pode ser pergunta complexa como "sem agendamento")
        resposta = _tratar_sem_criterio(consulta, intencao, usuario_id, usuario)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 8. Buscar e aplicar filtros aprendidos pelo IA Trainer
    filtros_aprendidos = _buscar_filtros_aprendidos(consulta, dominio)

    # 9. Executar capacidade com filtros aprendidos
    contexto = {
        "usuario_id": usuario_id,
        "usuario": usuario,
        "filtros_aprendidos": filtros_aprendidos  # Passa para a capacidade
    }
    resultado = capacidade.executar(entidades, contexto)

    if not resultado.get("sucesso"):
        return f"Ops, ocorreu um erro: {resultado.get('erro', 'Erro desconhecido')}\n\nPosso tentar outra busca?"

    if resultado.get("total_encontrado", 0) == 0:
        return f"{resultado.get('mensagem', f'Não encontrei resultados para {valor}')}\n\nQuer tentar de outra forma?"

    # 10. Gerar resposta (incluindo conceitos aprendidos no contexto)
    contexto_dados = capacidade.formatar_contexto(resultado)
    contexto_dados = _enriquecer_com_conceitos(contexto_dados, consulta)

    if usar_claude_resposta:
        from .responder import get_responder
        responder = get_responder()
        resposta = responder.gerar_resposta(consulta, contexto_dados, dominio, contexto_memoria)
    else:
        resposta = contexto_dados

    # 11. Registrar na memória
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


def _tratar_sem_capacidade(consulta: str, intencao: dict, usuario_id: int, usuario: str = "sistema") -> str:
    """
    Trata caso sem capacidade:
    1. Primeiro, tenta usar loader aprendido existente
    2. Se nao existir, tenta auto-gerar loader em tempo real
    3. Se falhar, gera sugestoes e loga
    """
    # 1. Tenta usar loader aprendido existente
    resposta_loader = _tentar_loader_aprendido(consulta, intencao)
    if resposta_loader:
        return resposta_loader

    # 2. Tenta auto-gerar loader em tempo real
    resposta_auto = _tentar_auto_gerar_loader(consulta, intencao, usuario_id, usuario)
    if resposta_auto:
        return resposta_auto

    # 3. Fallback: gera sugestoes e loga
    from .suggester import analisar_e_sugerir
    sugestao, analise = analisar_e_sugerir(consulta, intencao, 'sem_capacidade')

    _registrar_nao_respondida(
        consulta=consulta,
        intencao=intencao,
        motivo='sem_capacidade',
        sugestao=sugestao,
        analise=analise,
        usuario_id=usuario_id
    )

    if analise['tipo_pergunta'] == 'composta':
        intro = "Entendi sua pergunta, mas ela combina informações que ainda não consigo processar juntas.\n\n"
    else:
        intro = "Desculpe, ainda não consigo ajudar com isso.\n\n"

    return intro + sugestao


def _tentar_loader_aprendido(consulta: str, intencao: dict) -> Optional[str]:
    """
    Tenta usar um loader ja aprendido e ativado.
    """
    try:
        from ..ia_trainer.services.codigo_loader import buscar_por_gatilho
        from ..ia_trainer.services.loader_executor import executar_loader
        import json

        # Busca loaders ativos que correspondem aos gatilhos
        codigos = buscar_por_gatilho(consulta)

        for codigo in codigos:
            if codigo.get('tipo_codigo') != 'loader':
                continue
            if not codigo.get('ativo'):
                continue

            # Tenta executar o loader
            definicao = codigo.get('definicao_tecnica')
            if isinstance(definicao, str):
                try:
                    definicao = json.loads(definicao)
                except json.JSONDecodeError:
                    continue

            # Monta parametros a partir das entidades
            entidades = intencao.get('entidades', {})
            parametros = {f'${k}': v for k, v in entidades.items() if v}

            resultado = executar_loader(definicao, parametros)

            if resultado.get('sucesso') and resultado.get('total', 0) > 0:
                # Formata resposta
                resposta = _formatar_resposta_loader(resultado, codigo.get('descricao_claude'))
                logger.info(f"[ORCHESTRATOR] Loader aprendido usado: {codigo.get('nome')}")
                return resposta

    except Exception as e:
        logger.warning(f"[ORCHESTRATOR] Erro ao tentar loader aprendido: {e}")

    return None


def _tentar_auto_gerar_loader(consulta: str, intencao: dict, usuario_id: int, usuario: str) -> Optional[str]:
    """
    Tenta auto-gerar um loader em tempo real.
    Loader fica pendente de revisao, mas resposta eh retornada imediatamente.
    """
    try:
        logger.info(f"[ORCHESTRATOR] Tentando auto-gerar loader para: {consulta[:50]}...")

        from ..ia_trainer.services.auto_loader import tentar_responder_automaticamente

        resultado = tentar_responder_automaticamente(
            consulta=consulta,
            intencao=intencao,
            usuario_id=usuario_id,
            usuario=usuario
        )

        logger.info(f"[ORCHESTRATOR] Resultado auto-loader: sucesso={resultado.get('sucesso')}, "
                   f"tem_resposta={bool(resultado.get('resposta'))}, erro={resultado.get('erro')}")

        if resultado.get('sucesso') and resultado.get('resposta'):
            # Marca como experimental
            resposta = resultado['resposta']
            aviso = "\n\n_[Resposta experimental - gerada automaticamente]_"
            logger.info(f"[ORCHESTRATOR] Auto-loader gerado: #{resultado.get('loader_id')}")
            return resposta + aviso
        else:
            logger.warning(f"[ORCHESTRATOR] Auto-loader nao retornou resposta: {resultado.get('erro')}")

    except Exception as e:
        logger.error(f"[ORCHESTRATOR] Erro ao tentar auto-gerar loader: {e}")
        import traceback
        logger.error(traceback.format_exc())

    return None


def _formatar_resposta_loader(resultado: dict, descricao: str = None) -> str:
    """Formata resposta de um loader executado."""
    dados = resultado.get('dados', [])
    total = resultado.get('total', 0)

    linhas = []
    if descricao:
        linhas.append(f"{descricao}\n")

    linhas.append(f"Encontrei {total} resultado(s):\n")

    for i, item in enumerate(dados[:10], 1):
        if isinstance(item, dict):
            partes = [f"{k}: {v}" for k, v in item.items() if v is not None][:4]
            linhas.append(f"{i}. {' | '.join(partes)}")
        else:
            linhas.append(f"{i}. {item}")

    if total > 10:
        linhas.append(f"\n... e mais {total - 10} resultado(s)")

    return "\n".join(linhas)


def _tratar_sem_criterio(consulta: str, intencao: dict, usuario_id: int, usuario: str = "sistema") -> str:
    """
    Trata caso sem critério de busca:
    1. Primeiro tenta auto-gerar loader (pode ser pergunta complexa)
    2. Se falhar, gera sugestões e loga.
    """
    # 1. Tenta auto-gerar loader (perguntas complexas como "sem agendamento")
    resposta_auto = _tentar_auto_gerar_loader(consulta, intencao, usuario_id, usuario)
    if resposta_auto:
        return resposta_auto

    # 2. Fallback: gera sugestoes
    from .suggester import analisar_e_sugerir

    # Analisa e gera sugestões
    sugestao, analise = analisar_e_sugerir(consulta, intencao, 'sem_criterio')

    # Loga pergunta não respondida
    _registrar_nao_respondida(
        consulta=consulta,
        intencao=intencao,
        motivo='sem_criterio',
        sugestao=sugestao,
        analise=analise,
        usuario_id=usuario_id
    )

    return "Não consegui identificar o que você quer buscar.\n\n" + sugestao


def _registrar_nao_respondida(
    consulta: str,
    intencao: dict,
    motivo: str,
    sugestao: str,
    analise: dict,
    usuario_id: int = None
):
    """Registra pergunta não respondida para análise posterior."""
    try:
        from ..models import ClaudePerguntaNaoRespondida

        ClaudePerguntaNaoRespondida.registrar(
            consulta=consulta,
            motivo_falha=motivo,
            usuario_id=usuario_id,
            intencao=intencao,
            sugestao=sugestao,
            tipo_pergunta=analise.get('tipo_pergunta', 'simples'),
            dimensoes=analise.get('dimensoes')
        )
        logger.info(f"[ORCHESTRATOR] Pergunta não respondida registrada: {motivo}")
    except Exception as e:
        logger.warning(f"Erro ao registrar pergunta não respondida: {e}")


def _buscar_filtros_aprendidos(consulta: str, dominio: str) -> list:
    """
    Busca filtros aprendidos pelo IA Trainer que correspondem à consulta.

    Args:
        consulta: Texto do usuário
        dominio: Domínio da consulta (carteira, estoque, etc)

    Returns:
        Lista de filtros a serem aplicados pela capacidade
    """
    try:
        from ..ia_trainer.services.codigo_loader import (
            buscar_por_gatilho,
            buscar_filtros_para_dominio
        )

        filtros = []

        # 1. Busca filtros que correspondem aos gatilhos no texto
        codigos_gatilho = buscar_por_gatilho(consulta)
        for codigo in codigos_gatilho:
            if codigo.get('tipo_codigo') == 'filtro':
                models = codigo.get('models_referenciados') or []
                filtros.append({
                    'nome': codigo.get('nome'),
                    'filtro': codigo.get('definicao_tecnica'),
                    'modelo': models[0] if models else None,
                    'descricao': codigo.get('descricao_claude')
                })
                logger.info(f"[ORCHESTRATOR] Filtro aprendido aplicado: {codigo.get('nome')}")

        # 2. Busca filtros do domínio que não dependem de gatilho
        # (filtros automáticos para o domínio)
        filtros_dominio = buscar_filtros_para_dominio(dominio)
        for codigo in filtros_dominio:
            composicao = codigo.get('composicao') or ''
            # Só adiciona se tiver composição automática
            if composicao and 'auto' in composicao.lower():
                if codigo.get('nome') not in [f['nome'] for f in filtros]:
                    models = codigo.get('models_referenciados') or []
                    filtros.append({
                        'nome': codigo.get('nome'),
                        'filtro': codigo.get('definicao_tecnica'),
                        'modelo': models[0] if models else None,
                        'descricao': codigo.get('descricao_claude')
                    })

        return filtros

    except Exception as e:
        logger.debug(f"[ORCHESTRATOR] Filtros aprendidos não disponíveis: {e}")
        return []


def _enriquecer_com_conceitos(contexto_dados: str, consulta: str) -> str:
    """
    Enriquece o contexto de dados com conceitos aprendidos relevantes.

    Args:
        contexto_dados: Contexto formatado pela capacidade
        consulta: Texto original do usuário

    Returns:
        Contexto enriquecido com conceitos relevantes
    """
    try:
        from ..ia_trainer.services.codigo_loader import buscar_por_gatilho

        # Busca conceitos que correspondem à consulta
        codigos = buscar_por_gatilho(consulta)
        conceitos_relevantes = [c for c in codigos if c.get('tipo_codigo') == 'conceito']

        if not conceitos_relevantes:
            return contexto_dados

        # Adiciona explicação dos conceitos ao contexto
        linhas_conceito = ["\n=== CONCEITOS RELEVANTES ==="]
        for conceito in conceitos_relevantes:
            linhas_conceito.append(f"- {conceito.get('nome', '')}: {conceito.get('descricao_claude', '')}")
        linhas_conceito.append("=== FIM DOS CONCEITOS ===\n")

        return contexto_dados + "\n".join(linhas_conceito)

    except Exception as e:
        logger.debug(f"[ORCHESTRATOR] Conceitos não disponíveis: {e}")
        return contexto_dados


def _reclassificar_com_readme(
    classifier,
    consulta: str,
    contexto_memoria: str,
    intencao_original: dict
) -> dict:
    """
    Re-classifica consulta usando contexto do README quando confiança está baixa.

    Args:
        classifier: Instância do IntentClassifier
        consulta: Texto original do usuário
        contexto_memoria: Contexto de memória
        intencao_original: Classificação original com baixa confiança

    Returns:
        Nova classificação (ou original se não melhorar)
    """
    try:
        from ..cache import carregar_readme_contexto

        # Carrega contexto do README (usa cache Redis)
        readme_contexto = carregar_readme_contexto()

        if not readme_contexto:
            logger.debug("[ORCHESTRATOR] README não disponível para re-classificação")
            return intencao_original

        confianca_original = intencao_original.get("confianca", 0.0)
        logger.info(f"[ORCHESTRATOR] Confiança baixa ({confianca_original:.2f}), re-classificando com README...")

        # Re-classifica com contexto adicional
        nova_intencao = classifier.classificar(
            consulta,
            contexto_memoria,
            contexto_adicional=readme_contexto
        )

        nova_confianca = nova_intencao.get("confianca", 0.0)

        # Usa nova classificação se melhorou
        if nova_confianca > confianca_original:
            logger.info(f"[ORCHESTRATOR] Re-classificação melhorou: {confianca_original:.2f} -> {nova_confianca:.2f}")
            nova_intencao["_reclassificado"] = True
            nova_intencao["_confianca_original"] = confianca_original
            return nova_intencao
        else:
            logger.debug(f"[ORCHESTRATOR] Re-classificação não melhorou ({nova_confianca:.2f})")
            return intencao_original

    except Exception as e:
        logger.warning(f"[ORCHESTRATOR] Erro na re-classificação: {e}")
        return intencao_original
