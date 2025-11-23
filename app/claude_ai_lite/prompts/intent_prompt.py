"""
Prompt para classificação de intenções.

Gera o prompt dinamicamente baseado nas capacidades registradas.
Limite: 150 linhas
"""

from typing import Optional


def gerar_prompt_classificacao(contexto_conversa: str = None) -> str:
    """
    Gera o prompt de classificação de intenções.

    O prompt é gerado dinamicamente baseado nas capacidades registradas,
    garantindo que novas capacidades sejam automaticamente incluídas.

    Args:
        contexto_conversa: Contexto de conversa anterior (para follow-ups)

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
- "quando posso enviar/embarcar" = analisar_disponibilidade
- "tem estoque para" = analisar_disponibilidade
- "status do pedido" = consultar_status
- "opcao A/B/C" ou "quero A" = escolher_opcao (dominio=acao)
- "sim", "confirmo" = confirmar_acao (dominio=acao)
- "criar separacao" = criar_separacao (dominio=acao)
- "o que esta travando" = analisar_gargalo
- "qual estoque de" = consultar_estoque
- "vai dar ruptura" = consultar_ruptura

REGRAS PARA ROTA/SUB-ROTA:
- "rota MG", "rota NE" = rota principal (campo: rota)
- "rota A", "rota B", "rota CAP" = sub-rota (campo: sub_rota)
- "pedidos para SP" = UF (campo: uf)

{f"EXEMPLOS DAS CAPACIDADES:{chr(10)}{exemplos}" if exemplos else ""}

Retorne SOMENTE o JSON, sem explicacoes."""

    return prompt
