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

    # 0. NOVO: Classificar tipo de mensagem e reconstruir consulta com contexto
    from .conversation_context import (
        ConversationContextManager,
        classificar_e_reconstruir
    )

    tipo_mensagem = 'NOVA_CONSULTA'
    consulta_reconstruida = consulta
    entidades_contexto = {}

    if usuario_id:
        tipo_mensagem, consulta_reconstruida, entidades_contexto, metadados_ctx = \
            classificar_e_reconstruir(consulta, usuario_id)

        logger.info(f"[ORCHESTRATOR] Tipo mensagem: {tipo_mensagem}")

        if tipo_mensagem == 'MODIFICACAO':
            # Para modificações, usa consulta reconstruída
            logger.info(f"[ORCHESTRATOR] Consulta reconstruída: {consulta_reconstruida[:100]}...")

    # 1. Buscar contexto de memória
    if usuario_id:
        contexto_memoria = _buscar_memoria(usuario_id)
        # Adiciona contexto conversacional
        ctx_conversa = ConversationContextManager.formatar_contexto_para_prompt(usuario_id)
        if ctx_conversa:
            contexto_memoria = f"{ctx_conversa}\n\n{contexto_memoria}" if contexto_memoria else ctx_conversa

    # 2. Verificar comando de aprendizado
    if usuario_id:
        resultado_aprendizado = _verificar_aprendizado(consulta, usuario_id, usuario)
        if resultado_aprendizado:
            _registrar_conversa(usuario_id, consulta, resultado_aprendizado, None, None)
            return resultado_aprendizado

    # 3. Classificar intenção (usa consulta reconstruída para melhor classificação)
    # IMPORTANTE: Passa usuario_id para que o classificador use os aprendizados personalizados
    from .classifier import get_classifier
    classifier = get_classifier()
    intencao = classifier.classificar(consulta_reconstruida, contexto_memoria, usuario_id=usuario_id)

    # 3.0.1 Merge entidades do contexto com entidades detectadas
    if entidades_contexto:
        entidades_intencao = intencao.get('entidades', {})
        for k, v in entidades_contexto.items():
            if v and not entidades_intencao.get(k):
                entidades_intencao[k] = v
        intencao['entidades'] = entidades_intencao

    confianca = intencao.get("confianca", 0.0)

    # 3.1 Se confiança baixa, re-classificar com contexto do README
    if confianca < 0.7:
        intencao = _reclassificar_com_readme(classifier, consulta, contexto_memoria, intencao, usuario_id)

    dominio = intencao.get("dominio", "geral")
    intencao_tipo = intencao.get("intencao", "")
    entidades = intencao.get("entidades", {})

    # 3.2 Mapear entidades para nomes de campos esperados pelas capacidades
    entidades = _mapear_entidades_para_campos(entidades)

    # 3.3 NOVO: Extrair condições compostas ("sem agendamento", "atrasados", etc)
    from .composite_extractor import enriquecer_entidades
    entidades, filtros_compostos = enriquecer_entidades(consulta_reconstruida, entidades)
    if filtros_compostos:
        entidades['_filtros_compostos'] = filtros_compostos
        logger.info(f"[ORCHESTRATOR] {len(filtros_compostos)} condições compostas detectadas")

    intencao['entidades'] = entidades

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

    # 8.1 NOVO: Combinar filtros aprendidos + filtros compostos extraídos
    filtros_compostos = entidades.pop('_filtros_compostos', [])
    todos_filtros = filtros_aprendidos + filtros_compostos

    # 9. Executar capacidade com TODOS os filtros
    contexto = {
        "usuario_id": usuario_id,
        "usuario": usuario,
        "filtros_aprendidos": todos_filtros,  # Inclui filtros compostos
        "filtros_compostos": filtros_compostos  # Separado para referência
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

    # 10.1. NOVO: Se resultado tem opções (análise de disponibilidade), salva no contexto
    if usuario_id and resultado.get('opcoes'):
        from .conversation_context import ConversationContextManager
        ConversationContextManager.atualizar_estado(
            usuario_id=usuario_id,
            opcoes=resultado['opcoes'],
            aguardando_confirmacao=True,
            acao_pendente='escolher_opcao_envio'
        )
        logger.info(f"[ORCHESTRATOR] {len(resultado['opcoes'])} opções salvas no contexto")

    # 10.2. NOVO v3.4: Registra itens numerados para referência futura
    if usuario_id and resultado.get('dados'):
        dados = resultado['dados']
        if isinstance(dados, list) and len(dados) > 0:
            from .conversation_context import ConversationContextManager
            ConversationContextManager.registrar_itens_numerados(usuario_id, dados)
            logger.info(f"[ORCHESTRATOR] {len(dados)} itens numerados para referência")

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


def _mapear_entidades_para_campos(entidades: Dict) -> Dict:
    """
    Mapeia nomes de entidades do classificador para nomes de campos das capacidades.

    O classificador extrai entidades como 'cliente', mas as capacidades esperam
    'raz_social_red'. Este mapeamento faz a tradução.

    Mapeamentos organizados por categoria:
    - Cliente: cliente -> raz_social_red, cnpj/cpf -> cnpj_cpf
    - Produto: codigo/codigo_produto -> cod_produto, produto -> nome_produto
    - Localidade: uf/estado -> cod_uf, cidade -> nome_cidade
    - Datas: data_expedicao -> expedicao, data_agendamento -> agendamento
    - Quantidades: quantidade/qtd -> qtd_saldo
    - Pedido: pedido/numero_pedido -> num_pedido
    """
    if not entidades:
        return entidades

    # Mapeamento expandido com todos os campos relevantes
    mapeamento = {
        # === CLIENTE ===
        'cliente': 'raz_social_red',
        'cnpj': 'cnpj_cpf',
        'cpf': 'cnpj_cpf',
        'razao_social': 'raz_social_red',

        # === PRODUTO ===
        'codigo': 'cod_produto',
        'codigo_produto': 'cod_produto',
        'produto': 'nome_produto',  # Se não parecer código

        # === LOCALIDADE ===
        'uf': 'cod_uf',
        'estado': 'cod_uf',
        'cidade': 'nome_cidade',
        'municipio': 'nome_cidade',

        # === DATAS ===
        'data_expedicao': 'expedicao',
        'data_agendamento': 'agendamento',
        'data_entrega': 'data_entrega_pedido',

        # === QUANTIDADES ===
        'quantidade': 'qtd_saldo',
        'qtd': 'qtd_saldo',

        # === PEDIDO ===
        'pedido': 'num_pedido',
        'numero_pedido': 'num_pedido',
        'pedido_cliente': 'pedido_cliente',

        # === FRETE/EMBARQUE ===
        'transportadora': 'roteirizacao',
    }

    entidades_mapeadas = entidades.copy()

    for origem, destino in mapeamento.items():
        valor = entidades.get(origem)
        if valor and str(valor).lower() not in ('null', 'none', ''):
            # Só mapeia se o destino não tiver valor
            if not entidades_mapeadas.get(destino):
                entidades_mapeadas[destino] = valor
                logger.debug(f"[ORCHESTRATOR] Mapeado {origem}={valor} -> {destino}")

    # Tratamento especial para 'produto': verifica se parece código ou nome
    produto = entidades.get('produto')
    if produto and str(produto).lower() not in ('null', 'none', ''):
        # Se for só dígitos ou tiver formato de código (ex: "12345"), mapeia para cod_produto
        if str(produto).isdigit() or (len(str(produto)) <= 10 and str(produto).replace('-', '').isalnum()):
            if not entidades_mapeadas.get('cod_produto'):
                entidades_mapeadas['cod_produto'] = produto
                logger.debug(f"[ORCHESTRATOR] Produto '{produto}' identificado como código")
        else:
            # Senão, é nome do produto
            if not entidades_mapeadas.get('nome_produto'):
                entidades_mapeadas['nome_produto'] = produto

    return entidades_mapeadas


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
    """Registra conversa na memória e atualiza contexto conversacional."""
    if not usuario_id:
        return
    try:
        from ..memory import MemoryService
        MemoryService.registrar_conversa_completa(
            usuario_id=usuario_id, pergunta=consulta, resposta=resposta,
            intencao=intencao, resultado_busca=resultado
        )

        # NOVO: Atualiza contexto conversacional
        from .conversation_context import ConversationContextManager

        # Extrai entidades relevantes do resultado para enriquecer o contexto
        entidades = intencao.get('entidades', {}).copy() if intencao else {}

        # Se o resultado tem num_pedido, adiciona às entidades
        if resultado:
            if resultado.get('num_pedido'):
                entidades['num_pedido'] = resultado['num_pedido']
            # Se resultado.dados tem pedidos, pega o primeiro num_pedido
            dados = resultado.get('dados')
            if isinstance(dados, list) and dados:
                primeiro = dados[0] if isinstance(dados[0], dict) else {}
                if primeiro.get('num_pedido'):
                    entidades['num_pedido'] = primeiro['num_pedido']
            elif isinstance(dados, dict) and dados.get('num_pedido'):
                entidades['num_pedido'] = dados['num_pedido']

        ConversationContextManager.atualizar_estado(
            usuario_id=usuario_id,
            pergunta=consulta,
            intencao=intencao,
            resultado=resultado,
            entidades=entidades
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
    intencao_original: dict,
    usuario_id: int = None
) -> dict:
    """
    Re-classifica consulta usando contexto do README quando confiança está baixa.

    Args:
        classifier: Instância do IntentClassifier
        consulta: Texto original do usuário
        contexto_memoria: Contexto de memória
        intencao_original: Classificação original com baixa confiança
        usuario_id: ID do usuário para aprendizados personalizados

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

        # Re-classifica com contexto adicional (mantém usuario_id para aprendizados)
        nova_intencao = classifier.classificar(
            consulta,
            contexto_memoria,
            contexto_adicional=readme_contexto,
            usuario_id=usuario_id
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
