"""
Core do Claude AI Lite.
Orquestra o fluxo: identificar intencao -> buscar dados -> gerar resposta.
Integra memória de conversa e aprendizados.

REGRA: Maximo 150 linhas (expandido para suportar memória).
"""

import logging
from typing import Dict, Any, Optional

from .claude_client import get_claude_client
from .domains import get_loader
from .actions import processar_acao_separacao

logger = logging.getLogger(__name__)


def processar_consulta(
    consulta: str,
    usar_claude_resposta: bool = True,
    usuario: str = "Claude AI",
    usuario_id: int = None
) -> str:
    """
    Processa consulta em linguagem natural.

    Fluxo:
    1. Verifica se é comando de aprendizado
    2. Claude identifica dominio e entidades
    3. Roteia para loader ou action
    4. Busca dados ou executa acao
    5. Claude elabora resposta com contexto de memória
    6. Registra conversa no histórico
    """
    if not consulta or not consulta.strip():
        return "Por favor, informe sua consulta."

    client = get_claude_client()
    contexto_memoria = None
    resultado_busca = None

    # 0. Buscar contexto de memória (se tiver usuario_id)
    if usuario_id:
        try:
            from .memory import MemoryService
            contexto_memoria = MemoryService.formatar_contexto_memoria(usuario_id)
        except Exception as e:
            logger.warning(f"Erro ao buscar memória: {e}")

    # 1. Verificar se é comando de aprendizado
    if usuario_id:
        try:
            from .learning import LearningService
            tipo_cmd, conteudo_cmd = LearningService.detectar_comando(consulta)

            if tipo_cmd:
                global_ = LearningService.verificar_comando_global(consulta)
                resultado = LearningService.processar_comando(
                    tipo=tipo_cmd,
                    conteudo=conteudo_cmd,
                    usuario_id=usuario_id,
                    usuario_nome=usuario,
                    global_=global_
                )

                resposta = resultado.get('mensagem', 'Comando processado.')

                # Registra no histórico
                _registrar_conversa(usuario_id, consulta, resposta, None, None)

                return resposta
        except Exception as e:
            logger.warning(f"Erro ao processar aprendizado: {e}")

    # 2. Identificar intencao (passando contexto para entender follow-ups)
    intencao = client.identificar_intencao(consulta, contexto_conversa=contexto_memoria)
    dominio_base = intencao.get("dominio", "geral")
    intencao_tipo = intencao.get("intencao", "")
    entidades = intencao.get("entidades", {})

    logger.info(f"Intencao: dominio={dominio_base}, tipo={intencao_tipo}, entidades={entidades}")

    # 2.1 Tratamento especial para follow-up (continuação de conversa)
    if dominio_base == "follow_up" or intencao_tipo in ("follow_up", "detalhar"):
        resposta = _processar_follow_up(consulta, contexto_memoria, usuario_id, client)
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 3. Tratamento de acoes (delega para modulo actions/)
    if dominio_base == "acao":
        # Adiciona texto original nas entidades para contexto
        entidades["texto_original"] = consulta
        resposta = processar_acao_separacao(
            intencao_tipo,
            entidades,
            usuario=usuario,
            usuario_id=usuario_id
        )
        _registrar_conversa(usuario_id, consulta, resposta, intencao, None)
        return resposta

    # 4. Rotear para loader especifico
    dominio = _rotear_dominio(dominio_base, intencao_tipo, entidades)
    loader_class = get_loader(dominio)

    if not loader_class:
        loader_class = get_loader(dominio_base)
        if not loader_class:
            return _msg_ajuda()

    loader = loader_class()

    # 5. Extrair campo e valor de busca
    campo, valor = _extrair_criterio(entidades, loader.CAMPOS_BUSCA)
    if not campo or not valor:
        return _msg_sem_criterio()

    # 6. Buscar dados
    dados = loader.buscar(valor, campo)
    resultado_busca = dados

    if not dados.get("sucesso"):
        return f"Ops, ocorreu um erro: {dados.get('erro', 'Erro desconhecido')}\n\nPosso tentar outra busca?"

    if dados["total_encontrado"] == 0:
        return f"{dados.get('mensagem', f'Não encontrei resultados para {valor}')}\n\nQuer tentar de outra forma?"

    # 7. Gerar resposta
    contexto = loader.formatar_contexto(dados)

    if usar_claude_resposta:
        resposta = client.responder_com_contexto(
            consulta, contexto, dominio_base,
            contexto_memoria=contexto_memoria
        )
    else:
        resposta = contexto

    # 8. Registrar conversa no histórico
    _registrar_conversa(usuario_id, consulta, resposta, intencao, resultado_busca)

    return resposta


def _registrar_conversa(usuario_id: int, consulta: str, resposta: str, intencao: dict, resultado: dict):
    """Registra a conversa no histórico (se tiver usuario_id)."""
    if not usuario_id:
        return

    try:
        from .memory import MemoryService
        MemoryService.registrar_conversa_completa(
            usuario_id=usuario_id,
            pergunta=consulta,
            resposta=resposta,
            intencao=intencao,
            resultado_busca=resultado
        )
    except Exception as e:
        logger.warning(f"Erro ao registrar conversa: {e}")


def _msg_ajuda() -> str:
    return (
        "Desculpe, ainda não consigo ajudar com esse tipo de consulta.\n\n"
        "Posso te ajudar com:\n"
        "- Consultar pedidos (ex: 'Status do pedido VCD123')\n"
        "- Verificar quando enviar (ex: 'Quando posso enviar o pedido VCD123?')\n"
        "- Buscar produtos na carteira (ex: 'Tem azeitona na carteira?')\n"
        "- Criar separações (ex: 'Criar separação opção A do pedido VCD123')\n"
        "- Consultar por rota/UF (ex: 'Pedidos para SP')\n"
        "- Verificar estoque (ex: 'Qual estoque de ketchup?')\n"
        "- Memorizar informações (ex: 'Lembre que cliente X é VIP')\n\n"
        "Como posso te ajudar?"
    )


def _msg_sem_criterio() -> str:
    return (
        "Não consegui identificar o que você quer buscar.\n\n"
        "Tente informar:\n"
        "- Número do pedido (ex: 'Pedido VCD2564344')\n"
        "- Nome do cliente (ex: 'Pedidos do cliente Atacadão')\n"
        "- Nome do produto (ex: 'Azeitona verde na carteira')\n"
        "- Rota ou UF (ex: 'Pedidos para rota B' ou 'Pedidos para SP')\n\n"
        "Como posso te ajudar?"
    )


def _rotear_dominio(dominio_base: str, intencao: str, entidades: Dict) -> str:
    """Roteia para subdominio correto baseado na intencao."""
    if dominio_base == "estoque":
        return "estoque"

    if dominio_base != "carteira":
        return dominio_base

    if intencao == "buscar_rota" or entidades.get("rota") or entidades.get("sub_rota"):
        return "carteira_rota"
    elif intencao == "buscar_uf" or entidades.get("uf"):
        return "carteira_rota"
    elif intencao == "consultar_estoque" or intencao == "consultar_ruptura":
        return "estoque"
    elif intencao == "analisar_saldo":
        return "carteira_saldo"
    elif intencao == "analisar_gargalo":
        return "carteira_gargalo"
    elif intencao == "buscar_produto" or entidades.get("produto"):
        return "carteira_produto"
    elif intencao == "analisar_disponibilidade" or "quando" in str(entidades).lower():
        return "carteira_disponibilidade"

    return "carteira"


def _processar_follow_up(consulta: str, contexto_memoria: str, usuario_id: int, client) -> str:
    """
    Processa perguntas de follow-up usando o contexto da conversa anterior.

    Quando o usuário faz perguntas como "Preciso dos nomes completos desses itens",
    busca os DADOS REAIS do último resultado para responder com precisão.
    """
    from .memory import MemoryService

    # 1. Busca o último resultado REAL da busca (com dados completos)
    ultimo_resultado = MemoryService.extrair_ultimo_resultado(usuario_id) if usuario_id else None

    if not ultimo_resultado and not contexto_memoria:
        return (
            "Não encontrei contexto de conversa anterior.\n\n"
            "Poderia reformular sua pergunta incluindo mais detalhes?\n"
            "Por exemplo: 'Quais são os nomes completos dos produtos do pedido VCD123?'"
        )

    # 2. Formata os dados REAIS do último resultado para o Claude usar
    dados_reais = ""
    if ultimo_resultado:
        dados = ultimo_resultado.get('dados', [])
        if dados:
            dados_reais = "\n=== DADOS REAIS DO ÚLTIMO RESULTADO (USE ESTES!) ===\n"

            # Se for uma lista de pedidos/gargalos
            if isinstance(dados, list):
                for item in dados[:20]:  # Máximo 20 itens
                    if isinstance(item, dict):
                        # Extrai informações detalhadas do item
                        nome = item.get('nome_produto') or item.get('nome') or ''
                        cod = item.get('cod_produto') or item.get('codigo') or ''
                        qtd = item.get('qtd_necessaria') or item.get('qtd_saldo') or item.get('quantidade', '')
                        falta = item.get('falta', '')
                        estoque = item.get('estoque_atual', '')

                        if nome or cod:
                            dados_reais += f"- {nome} (Cód: {cod})"
                            if qtd:
                                dados_reais += f" | Qtd: {qtd}"
                            if falta:
                                dados_reais += f" | Falta: {falta}"
                            if estoque:
                                dados_reais += f" | Estoque: {estoque}"
                            dados_reais += "\n"

            # Se for um dict com estrutura de gargalos
            elif isinstance(dados, dict):
                # Gargalos tem estrutura especial
                gargalos = dados.get('gargalos', [])
                itens_ok = dados.get('itens_ok', [])

                if gargalos:
                    dados_reais += "\nITENS COM PROBLEMA (GARGALOS):\n"
                    for g in gargalos:
                        nome = g.get('nome_produto', '')
                        cod = g.get('cod_produto', '')
                        qtd = g.get('qtd_necessaria', '')
                        falta = g.get('falta', '')
                        estoque = g.get('estoque_atual', '')
                        dados_reais += f"- {nome} (Cód: {cod}) | Necessário: {qtd} | Estoque: {estoque} | Falta: {falta}\n"

                if itens_ok:
                    dados_reais += "\nITENS DISPONÍVEIS:\n"
                    for i in itens_ok:
                        nome = i.get('nome_produto', '')
                        cod = i.get('cod_produto', '')
                        qtd = i.get('qtd_necessaria', '')
                        dados_reais += f"- {nome} (Cód: {cod}) | Qtd: {qtd}\n"

            dados_reais += "=== FIM DOS DADOS REAIS ===\n"

    # 3. Usa o Claude para responder com base nos dados REAIS
    system_prompt = f"""Você é um assistente de logística respondendo uma pergunta de FOLLOW-UP.

O usuário quer MAIS DETALHES sobre algo discutido anteriormente.

REGRA CRÍTICA: Use APENAS os dados fornecidos abaixo. NÃO INVENTE nomes de produtos, códigos ou quantidades!

{dados_reais}

CONTEXTO DA CONVERSA:
{contexto_memoria or 'Sem histórico'}

INSTRUÇÕES:
1. Use SOMENTE os nomes de produtos que aparecem nos DADOS REAIS acima
2. Se pedirem "nomes completos", liste exatamente como está nos dados (campo nome_produto)
3. NUNCA invente informações - se não tiver o dado, diga que não tem
4. Se os dados não tiverem a informação solicitada, sugira ao usuário fazer uma consulta específica
"""

    try:
        resposta = client.completar(consulta, system_prompt, use_cache=False)
        return resposta
    except Exception as e:
        logger.error(f"Erro ao processar follow-up: {e}")
        return (
            "Desculpe, tive dificuldade em processar sua pergunta.\n\n"
            "Poderia reformular incluindo mais detalhes?\n"
            "Por exemplo: 'Quais são os nomes completos dos produtos do pedido VCD123?'"
        )


def _extrair_criterio(entidades: Dict, campos_aceitos: list) -> tuple:
    """Extrai campo e valor das entidades identificadas."""
    mapeamento = {
        "num_pedido": "num_pedido",
        "cnpj": "cnpj_cpf",
        "cliente": "raz_social_red",
        "pedido_cliente": "pedido_cliente",
        "produto": "nome_produto",
        "cod_produto": "cod_produto",
        "rota": "rota",
        "sub_rota": "sub_rota",
        "uf": "cod_uf",
    }

    for entidade, campo in mapeamento.items():
        if campo not in campos_aceitos:
            continue
        valor = entidades.get(entidade)
        if valor and str(valor).lower() not in ("null", "none", ""):
            return campo, str(valor)

    if "ruptura" in campos_aceitos:
        return "ruptura", "7"

    if "geral" in campos_aceitos and not entidades.get("num_pedido"):
        return "geral", "geral"

    return None, None
