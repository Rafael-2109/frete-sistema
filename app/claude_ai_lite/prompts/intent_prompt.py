"""
Prompt para classificação de intenções.

Gera o prompt dinamicamente baseado nas capacidades registradas
e nos DOIS sistemas de aprendizado:
  1. ClaudeAprendizado (caderno de dicas - conhecimento conceitual)
  2. CodigoSistemaGerado (receitas prontas - código do IA Trainer)

Limite: 250 linhas
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _carregar_aprendizados_usuario(usuario_id: int = None) -> str:
    """
    Carrega aprendizados do ClaudeAprendizado (caderno de dicas).

    Inclui aprendizados globais E do usuário específico.
    Estes são conhecimentos conceituais que ajudam o classificador
    a entender melhor o contexto do negócio.

    Args:
        usuario_id: ID do usuário (opcional, para aprendizados personalizados)

    Returns:
        String formatada com aprendizados relevantes para classificação
    """
    try:
        from ..models import ClaudeAprendizado

        # Busca aprendizados ativos (globais + usuario)
        query = ClaudeAprendizado.query.filter_by(ativo=True)

        if usuario_id:
            # Globais OU do usuário específico
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    ClaudeAprendizado.usuario_id.is_(None),  # Globais
                    ClaudeAprendizado.usuario_id == usuario_id  # Do usuário
                )
            )
        else:
            # Apenas globais
            query = query.filter(ClaudeAprendizado.usuario_id.is_(None))

        aprendizados = query.order_by(
            ClaudeAprendizado.prioridade.desc(),
            ClaudeAprendizado.criado_em.desc()
        ).limit(30).all()  # Limita para não sobrecarregar o prompt

        if not aprendizados:
            return ''

        # Agrupa por categoria para melhor organização
        por_categoria = {}
        for a in aprendizados:
            cat = a.categoria.upper()
            if cat not in por_categoria:
                por_categoria[cat] = []
            por_categoria[cat].append(a.valor)

        # Formata para incluir no prompt de classificação
        linhas = ["\n=== CONHECIMENTO DO NEGOCIO (aprendido via chat) ==="]
        linhas.append("Use estas informações para entender melhor as perguntas:")
        for categoria, valores in por_categoria.items():
            linhas.append(f"\n[{categoria}]")
            for valor in valores:
                linhas.append(f"- {valor}")
        linhas.append("\n=== FIM DO CONHECIMENTO APRENDIDO ===\n")

        return "\n".join(linhas)

    except Exception as e:
        logger.debug(f"[INTENT_PROMPT] ClaudeAprendizado nao disponivel: {e}")
        return ''


def _carregar_codigos_aprendidos() -> dict:
    """
    Carrega códigos aprendidos do IA Trainer (receitas prontas).

    Returns:
        Dict com prompts, conceitos e entidades formatados
    """
    try:
        from ..ia_trainer.services.codigo_loader import (
            gerar_contexto_prompts,
            gerar_contexto_conceitos,
            gerar_contexto_entidades
        )

        return {
            'prompts': gerar_contexto_prompts(),
            'conceitos': gerar_contexto_conceitos(),
            'entidades': gerar_contexto_entidades()
        }
    except Exception as e:
        logger.debug(f"[INTENT_PROMPT] Codigos aprendidos nao disponiveis: {e}")
        return {'prompts': '', 'conceitos': '', 'entidades': ''}


def gerar_prompt_classificacao(contexto_conversa: str = None, usuario_id: int = None) -> str:
    """
    Gera o prompt de classificação de intenções.

    O prompt é gerado dinamicamente baseado nas capacidades registradas
    e nos DOIS sistemas de aprendizado:
      1. ClaudeAprendizado (caderno de dicas - conhecimento conceitual)
      2. CodigoSistemaGerado (receitas prontas - código do IA Trainer)

    Args:
        contexto_conversa: Contexto de conversa anterior (para follow-ups)
        usuario_id: ID do usuário para carregar aprendizados personalizados

    Returns:
        Prompt completo para classificação
    """
    # Importa aqui para evitar circular import
    from ..capabilities import listar_dominios, listar_intencoes, gerar_exemplos_para_prompt

    # Busca domínios e intenções das capacidades registradas
    try:
        dominios = listar_dominios()
        intencoes = listar_intencoes()
        exemplos = gerar_exemplos_para_prompt()
    except Exception:
        # Fallback se capacidades ainda não carregadas
        dominios = ["carteira", "estoque", "fretes", "embarques", "cotacao", "faturamento", "acao", "follow_up", "geral"]
        intencoes = ["consultar_status", "buscar_pedido", "analisar_disponibilidade", "outro"]
        exemplos = ""

    # 1. Carrega aprendizados do ClaudeAprendizado (caderno de dicas)
    conhecimento_aprendido = _carregar_aprendizados_usuario(usuario_id)

    # 2. Carrega códigos aprendidos pelo IA Trainer (receitas prontas)
    codigos_aprendidos = _carregar_codigos_aprendidos()

    # Adiciona domínios e intenções fixas que sempre devem existir
    dominios_fixos = ["acao", "follow_up", "geral"]
    for d in dominios_fixos:
        if d not in dominios:
            dominios.append(d)

    intencoes_fixas = ["escolher_opcao", "confirmar_acao", "cancelar", "follow_up", "detalhar", "outro"]
    for i in intencoes_fixas:
        if i not in intencoes:
            intencoes.append(i)

    # Seção de contexto para follow-ups
    secao_contexto = ""
    if contexto_conversa:
        secao_contexto = f"""
=== CONTEXTO DA CONVERSA ATUAL ===
{contexto_conversa}
=== FIM DO CONTEXTO ===

IMPORTANTE - PERGUNTAS DE FOLLOW-UP:
Se o usuário usa termos como "esses itens", "esse pedido", "desses produtos", "mais detalhes",
"nomes completos", "especificações", você DEVE:
1. Buscar no CONTEXTO qual pedido/itens foram discutidos
2. Extrair o num_pedido do contexto se não foi mencionado explicitamente
3. Definir intencao como "follow_up" se é uma continuação/detalhamento
4. Copiar as entidades relevantes do contexto (especialmente num_pedido)

"""

    prompt = f"""{secao_contexto}Voce e um analisador de intencoes para um sistema de logistica de uma INDUSTRIA DE ALIMENTOS.

Analise a mensagem e retorne APENAS um JSON valido com:
{{
    "dominio": "{"|".join(sorted(dominios))}",
    "intencao": "{"|".join(sorted(intencoes))}",
    "entidades": {{
        "num_pedido": "valor ou null",
        "cnpj": "valor ou null",
        "cliente": "valor ou null",
        "pedido_cliente": "valor ou null",
        "produto": "nome do produto ou null",
        "cod_produto": "codigo do produto ou null",
        "item": "nome ou codigo do item a incluir/excluir/alterar ou null",
        "quantidade": "quantidade numerica ou null",
        "rota": "nome da rota ou null",
        "sub_rota": "nome da sub-rota ou null",
        "uf": "sigla do estado (SP, RJ, MG, etc) ou null",
        "data": "valor ou null",
        "opcao": "A, B ou C se usuario escolher opcao"
    }},
    "confianca": 0.0 a 1.0
}}

CONTEXTO - INDUSTRIA DE ALIMENTOS:
- Produtos: Pessego, Ketchup, Azeitona, Cogumelo, Shoyu, Oleo Misto
- Variacoes: cor (verde, preta), forma (inteira, fatiada, sem caroco, recheada)
- Embalagens: BD 6x2 (caixa 6 baldes 2kg), Pouch 18x150 (caixa 18 pouchs 150g), Lata, Vidro
- Rotas principais: BA, MG, ES, NE, NE2, NO, MS-MT, SUL, SP, RJ (baseadas em UF/regiao)
- Sub-rotas: CAP, INT, INT 2, A, B, C, 0, 1, 2 (baseadas em cidade/regiao interna)

REGRAS PARA INTENCAO:
- "quando posso enviar/embarcar" + num_pedido especifico = analisar_disponibilidade
- "tem estoque para" + num_pedido = analisar_disponibilidade
- "status do pedido" = consultar_status
- "opcao A/B/C" ou "quero A" = escolher_opcao (dominio=acao)
- "sim", "confirmo" = confirmar_acao (dominio=acao)
- "criar separacao" = criar_separacao (dominio=acao)
- "o que esta travando" = analisar_gargalo
- "qual estoque de" = consultar_estoque
- "vai dar ruptura" = consultar_ruptura

REGRAS PARA PERGUNTAS COMPOSTAS (CLIENTE + DATA + ESTOQUE):
- "quais produtos do [CLIENTE] terao estoque" = analisar_estoque_cliente
- "o que posso enviar para o cliente [X]" = analisar_estoque_cliente
- "produtos disponiveis do [CLIENTE]" = analisar_estoque_cliente
- "o que tem estoque para [CLIENTE]" = analisar_estoque_cliente
- IMPORTANTE: Se menciona CLIENTE + (estoque OU disponivel OU enviar OU data), use analisar_estoque_cliente

REGRAS PARA ROTA/SUB-ROTA:
- "rota MG", "rota NE" = rota principal (campo: rota)
- "rota A", "rota B", "rota CAP" = sub-rota (campo: sub_rota)
- "pedidos para SP" = UF (campo: uf)

REGRAS PARA CONDICOES COMPOSTAS (FILTROS IMPLICITOS):
Quando o usuario menciona essas condicoes, o sistema SABE aplicar o filtro automaticamente:
- "sem agendamento" = agendamento IS NULL (filtro automatico)
- "sem expedicao" = expedicao IS NULL (filtro automatico)
- "sem protocolo" = protocolo IS NULL (filtro automatico)
- "sem transportadora" = roteirizacao IS NULL (filtro automatico)
- "com agendamento" / "agendados" = agendamento IS NOT NULL
- "atrasados" = expedicao < hoje
- "pendentes" = sincronizado_nf = False
- "abertos" = status = 'ABERTO'
- "hoje" = expedicao = data atual
- "amanha" = expedicao = data atual + 1

IMPORTANTE: Perguntas como "pedidos do cliente X sem agendamento" DEVEM ser processadas:
- Extraia cliente = X
- O filtro "sem agendamento" sera aplicado AUTOMATICAMENTE pelo sistema
- Use intencao = "buscar_pedido" ou "consultar_status"

CAMPOS DISPONIVEIS NOS MODELOS:
- Separacao/CarteiraPrincipal: num_pedido, cnpj_cpf, raz_social_red, cod_produto, nome_produto, qtd_saldo, valor_saldo, expedicao, agendamento, protocolo, roteirizacao, rota, sub_rota, cod_uf, nome_cidade, status, sincronizado_nf
- Datas: expedicao (data expedição), agendamento (data agendamento), data_pedido
- Status: ABERTO, PREVISAO, COTADO, EMBARCADO, FATURADO

{f"EXEMPLOS DAS CAPACIDADES:{chr(10)}{exemplos}" if exemplos else ""}

{conhecimento_aprendido}{codigos_aprendidos['prompts']}{codigos_aprendidos['conceitos']}{codigos_aprendidos['entidades']}Retorne SOMENTE o JSON, sem explicacoes."""

    return prompt
