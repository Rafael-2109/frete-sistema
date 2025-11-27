"""
Extrator Inteligente - Delega ao Claude a extração completa.

FILOSOFIA v5.0:
- O Claude é o CÉREBRO - confiamos 100% nas decisões dele
- O Claude recebe:
  1. Lista de CAPABILITIES disponíveis (com descrição e intenções)
  2. ESTADO ESTRUTURADO da conversa (JSON) - v5 com PONTE de contexto
  3. CONHECIMENTO DO NEGÓCIO (aprendizados)
- O Claude decide:
  1. DOMÍNIO (carteira, estoque, acao, etc)
  2. INTENÇÃO (deve mapear para uma capability)
  3. ENTIDADES extraídas - INCLUINDO herança automática de contexto!

HERANÇA AUTOMÁTICA v5:
- Se REFERENCIA.consulta_ativa = true e usuário NÃO muda de assunto
- HERDA cliente_atual, dominio_atual automaticamente
- Isso resolve o problema de "o que está pendente?" após consultar cliente X

Criado em: 24/11/2025
Atualizado: 26/11/2025 - Claude decide domínio/intenção, lista de capabilities
Atualizado: 26/11/2025 - Capabilities dinâmicas via ToolRegistry + config.py
Atualizado: 27/11/2025 - v5: Herança automática de contexto (REFERENCIA.cliente_atual)
Atualizado: 27/11/2025 - v5.6: Recebe histórico da conversa para entender follow-ups
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# CARREGAMENTO DINÂMICO DE CAPABILITIES
# =============================================================================

def _carregar_capabilities_dinamicas() -> str:
    """
    Carrega capabilities dinamicamente do ToolRegistry.

    Benefícios:
    - Sempre atualizado com novas capabilities
    - Inclui códigos gerados ativos
    - Não precisa manutenção manual

    Returns:
        String formatada com capabilities para o prompt
    """
    try:
        from .tool_registry import get_tool_registry

        registry = get_tool_registry()
        ferramentas = registry.listar_ferramentas(incluir_generica=False)

        if not ferramentas:
            logger.warning("[INTELLIGENT_EXTRACTOR] Nenhuma ferramenta encontrada, usando fallback")
            return _CAPABILITIES_FALLBACK

        return registry.formatar_para_prompt(ferramentas)

    except Exception as e:
        logger.warning(f"[INTELLIGENT_EXTRACTOR] Erro ao carregar capabilities dinâmicas: {e}")
        return _CAPABILITIES_FALLBACK


def _obter_capabilities_prompt() -> str:
    """
    Retorna capabilities para o prompt, usando config para decidir.

    Se config.extracao.carregar_capabilities_dinamicamente = True:
        Carrega do ToolRegistry
    Senão:
        Usa string fixa (fallback)
    """
    from ..config import usar_capabilities_dinamicas

    if usar_capabilities_dinamicas():
        caps = _carregar_capabilities_dinamicas()
        logger.debug("[INTELLIGENT_EXTRACTOR] Usando capabilities dinâmicas")
        return caps

    logger.debug("[INTELLIGENT_EXTRACTOR] Usando capabilities estáticas (fallback)")
    return _CAPABILITIES_FALLBACK


# =============================================================================
# CAPABILITIES FALLBACK (string fixa para quando dinâmico falhar)
# =============================================================================
# Mantido como fallback caso o carregamento dinâmico falhe.

_CAPABILITIES_FALLBACK = """
=== CAPABILITIES DISPONÍVEIS ===

Escolha a intenção que melhor se encaixa. O sistema vai executar a capability correspondente.

DOMÍNIO: carteira
- consultar_pedido
  Intenções: consultar_status, buscar_pedido
  Descrição: Consulta status e detalhes de pedidos
  Campos: num_pedido, cnpj_cpf, raz_social_red
  Exemplos: "Status do pedido VCD123", "Pedidos do cliente Atacadão"

- analisar_disponibilidade
  Intenções: analisar_disponibilidade, quando_posso_enviar, verificar_disponibilidade
  Descrição: Analisa QUANDO um pedido/cliente pode ser enviado baseado no estoque
  Campos: num_pedido, raz_social_red, qtd_saldo
  Exemplos: "Quando posso enviar o VCD123?", "Quando dá pra enviar 28 pallets pro Atacadão?"

- consultar_produto
  Intenções: buscar_produto
  Descrição: Busca produtos na carteira por nome ou código
  Campos: nome_produto, cod_produto
  Exemplos: "Azeitona na carteira", "Produto 12345"

- consultar_rota
  Intenções: buscar_rota, buscar_uf
  Descrição: Busca pedidos por rota, sub-rota ou UF
  Campos: rota, sub_rota, cod_uf
  Exemplos: "Pedidos da rota MG", "O que tem pra SP?"

- analisar_gargalos
  Intenções: analisar_gargalo
  Descrição: Identifica produtos que travam pedidos por falta de estoque
  Campos: num_pedido, cod_produto
  Exemplos: "O que trava o pedido VCD123?", "Gargalos do pedido"

- analisar_estoque_cliente
  Intenções: analisar_estoque_cliente, produtos_cliente_data
  Descrição: Analisa quais produtos de um cliente terão estoque disponível em uma data
  Campos: raz_social_red, data
  Exemplos: "Quais produtos do Atacadão terão estoque dia 26?"

- consulta_generica
  Intenções: consulta_generica, consultar_por_data, listar_dados, consultar_faturamento
  Descrição: Consultas genéricas em tabelas por período/filtro
  Campos: tabela, campo_filtro, data_inicio, data_fim, agregacao
  TABELAS VÁLIDAS: CarteiraPrincipal, Separacao, Pedido, FaturamentoProduto, Embarque,
                   MovimentacaoEstoque, CadastroPalletizacao, ProgramacaoProducao, Frete
  SINÔNIMOS DE TABELA:
    - "faturamento", "faturou", "NFs emitidas" → tabela="FaturamentoProduto"
    - "pedido", "pedidos" → tabela="Pedido" ou "CarteiraPrincipal"
    - "separação", "separações" → tabela="Separacao"
    - "estoque", "movimentação" → tabela="MovimentacaoEstoque"
    - "embarque" → tabela="Embarque"
    - "fretes" → tabela="Frete"

  AGREGAÇÃO (campo "agregacao"):
    - Se usuário pergunta "quanto", "total", "soma" → agregacao="sum"
    - Se usuário pergunta "quantos", "contagem" → agregacao="count"
    - Se usuário quer lista detalhada → NÃO incluir agregacao

  IMPORTANTE: Sempre extraia "tabela" como entidade quando o usuário perguntar sobre dados!
  Exemplos:
    - "O que entrou de pedido ontem?" → tabela="CarteiraPrincipal", data_inicio="ontem"
    - "Separações criadas hoje" → tabela="Separacao", data_inicio="hoje"
    - "Quanto faturou hoje?" → tabela="FaturamentoProduto", data_inicio="hoje", data_fim="hoje", agregacao="sum"
    - "Quantas NFs foram emitidas ontem?" → tabela="FaturamentoProduto", data_inicio="ontem", agregacao="count"
    - "Lista as NFs de hoje" → tabela="FaturamentoProduto", data_inicio="hoje" (sem agregacao)

DOMÍNIO: estoque
- consultar_estoque
  Intenções: consultar_estoque, consultar_ruptura
  Descrição: Consulta estoque atual, projeção e rupturas
  Campos: cod_produto, nome_produto
  Exemplos: "Estoque de azeitona", "Vai dar ruptura de azeitona?"

DOMÍNIO: acao (para modificar dados/criar coisas)
- criar_separacao
  Intenções: criar_separacao, separar, gerar_separacao
  Descrição: Cria separações para pedidos
  Campos: num_pedido, expedicao, opcao
  Exemplos: "Cria separação do VCD123", "Separa o pedido pro dia 27"

- escolher_opcao
  Intenções: escolher_opcao
  Descrição: Usuário escolhendo opção A/B/C apresentada anteriormente
  Campos: opcao
  Exemplos: "Opção A", "Quero a B", "Escolho a primeira"

- confirmar_acao
  Intenções: confirmar_acao
  Descrição: Usuário confirmando uma ação pendente
  Exemplos: "Sim", "Confirmo", "Pode fazer"

- cancelar
  Intenções: cancelar
  Descrição: Usuário cancelando ação/rascunho
  Exemplos: "Cancela", "Desisto", "Não quero mais"

- alterar_expedicao
  Intenções: alterar_expedicao, alterar_data
  Descrição: Alterar data de expedição de um rascunho
  Campos: expedicao
  Exemplos: "Muda pro dia 28", "Altera a data pra 30/11"

- ver_rascunho
  Intenções: ver_rascunho
  Descrição: Mostrar o rascunho atual
  Exemplos: "Mostra o rascunho", "Como está a separação?"

=== FIM DAS CAPABILITIES ===
"""


class IntelligentExtractor:
    """
    Extrator que delega TODO o trabalho ao Claude.

    v4.0: Claude decide domínio, intenção E entidades.
    """

    def __init__(self, claude_client):
        self._client = claude_client

    def extrair(
        self,
        texto: str,
        contexto_estruturado: str = None,
        conhecimento_negocio: str = None,
        historico_conversa: str = None
    ) -> Dict[str, Any]:
        """
        Extrai TUDO do texto usando Claude.

        O Claude recebe:
        1. Lista de capabilities disponíveis
        2. Estado estruturado da conversa
        3. Conhecimento do negócio
        4. NOVO v5.6: Histórico recente da conversa

        O Claude retorna:
        - dominio: carteira, estoque, acao, geral
        - intencao: deve mapear para uma capability
        - tipo: consulta, acao, modificacao, confirmacao, cancelamento
        - entidades: dados extraídos
        - ambiguidade: se precisa perguntar algo
        - confianca: 0.0 a 1.0

        Args:
            texto: Mensagem do usuário
            contexto_estruturado: JSON do estado da conversa
            conhecimento_negocio: Aprendizados do negócio
            historico_conversa: NOVO - Últimas mensagens da conversa

        Returns:
            Dict com extração completa
        """
        hoje = datetime.now().strftime("%d/%m/%Y")
        ano_atual = datetime.now().year

        # Seção de contexto estruturado
        secao_contexto = ""
        if contexto_estruturado and contexto_estruturado.strip():
            secao_contexto = f"""
=== ESTADO ATUAL DA CONVERSA (JSON) ===
{contexto_estruturado}
=== FIM DO ESTADO ===

REGRAS DO ESTADO (v5 - CRÍTICAS):

1. HERANÇA AUTOMÁTICA DE CONTEXTO (MAIS IMPORTANTE):
   Se REFERENCIA.consulta_ativa = true E o usuário NÃO mencionou cliente/pedido:
   - HERDE REFERENCIA.cliente_atual como raz_social_red nas entidades
   - HERDE REFERENCIA.dominio_atual como domínio
   - Exemplo: "o que está pendente?" + cliente_atual="ASSAI"
     → entidades: {{"raz_social_red": "ASSAI"}}

2. FILTROS DA ÚLTIMA CONSULTA:
   Se CONSULTA.filtros_aplicados existe:
   - Esses são os filtros usados na consulta anterior
   - Para follow-ups ("e o total?", "detalha por pedido"), HERDE esses filtros
   - Só NÃO herde se o usuário EXPLICITAMENTE mudar de assunto
     (ex: "e o Atacadão?", "agora quero ver o estoque")

3. QUANDO NÃO HERDAR (pedir clarificação):
   - Usuário muda explicitamente de assunto ("e o cliente X?", "agora quero...")
   - Não existe REFERENCIA.cliente_atual (primeira consulta)
   - Pergunta é claramente sobre OUTRO domínio

4. Se SEPARACAO.ativo = true:
   - Há um rascunho de separação em andamento
   - Menções a data são para MODIFICAR o rascunho
   - "confirmo" = confirmar_acao
   - "cancela" = cancelar

5. Se OPCOES tem lista:
   - O usuário provavelmente está escolhendo uma opção (A, B, C)
   - Use intenção: escolher_opcao

6. Se ENTIDADES tem dados:
   - Use esses valores quando disser "esse pedido", "esse cliente"
   - Não pergunte o que já está no contexto

"""

        # Carrega capabilities (dinâmico ou fallback baseado na config)
        capabilities_prompt = _obter_capabilities_prompt()

        # v5.6: Seção do histórico de conversa (CRÍTICO para entender follow-ups)
        secao_historico = ""
        if historico_conversa and historico_conversa.strip():
            # Limita histórico para não sobrecarregar (últimas 5 interações aprox)
            historico_limitado = historico_conversa[:3000]
            secao_historico = f"""
=== HISTÓRICO RECENTE DA CONVERSA ===
{historico_limitado}
=== FIM DO HISTÓRICO ===

REGRAS DO HISTÓRICO (v5.6 - CRÍTICAS):
1. O histórico mostra as últimas mensagens trocadas
2. Se o usuário pedir "mais informação" ou "detalhar", OLHE o que foi mostrado antes
3. Se VOCÊ SUGERIU algo antes ("Posso ajudar com..."), e o usuário aceita, FAÇA
4. "Qual valor de cada?" após lista de pedidos = valores DOS PEDIDOS já mostrados
5. NUNCA peça clarificação se a resposta está no histórico!

"""

        # Prompt completo
        system_prompt = f"""Você é o cérebro de um sistema de logística de uma INDÚSTRIA DE ALIMENTOS.

DATA DE HOJE: {hoje}

{capabilities_prompt}

{secao_contexto}

{secao_historico}

{f"CONHECIMENTO DO NEGÓCIO:{chr(10)}{conhecimento_negocio}{chr(10)}" if conhecimento_negocio else ""}

=== SUA TAREFA ===

Analise a mensagem do usuário e retorne um JSON com:

{{
    "dominio": "carteira|estoque|acao|geral",
    "intencao": "nome_da_intencao (DEVE ser uma das listadas nas capabilities)",
    "tipo": "consulta|acao|modificacao|confirmacao|cancelamento|clarificacao",
    "entidades": {{
        // Use nomes de negócio ou técnicos, tanto faz:
        // "num_pedido" ou "pedido": "VCD123456",
        // "raz_social_red" ou "cliente": "ATACADAO",
        // "expedicao" ou "data_expedicao": "2025-11-27" (ISO),
        // "cod_produto" ou "produto": "azeitona",
        // "opcao": "A" (se escolheu opção),
        // ... extraia TUDO relevante
    }},
    "ambiguidade": {{
        "existe": false,
        "pergunta": "pergunta para esclarecer (se existe=true)",
        "opcoes": ["opção 1", "opção 2"]
    }},
    "confianca": 0.0 a 1.0,

    // CAMPOS OPCIONAIS - adicione se relevante:
    "roteamento": {{
        "carregar_conhecimento": true,  // false se não precisa de aprendizados
        "buscar_memoria": true,         // false se consulta é independente
        "usar_estado": true             // false se contexto anterior não é relevante
    }},
    "contexto_adicional": "informação extra que você quer passar ao sistema",
    "avisos": ["aviso 1", "aviso 2"],    // alertas sobre a consulta
    "sugestao_alternativa": "se detectou que usuário pode querer algo diferente"
}}

=== REGRAS ===

1. DOMÍNIO:
   - "carteira" = consultas sobre pedidos, clientes, produtos na carteira
   - "estoque" = consultas sobre estoque, rupturas, projeção
   - "acao" = criar/modificar/confirmar/cancelar algo
   - "geral" = não se encaixa em nenhum

2. INTENÇÃO:
   - DEVE ser uma das listadas nas capabilities
   - Escolha a que melhor se encaixa
   - Se não souber, use a mais próxima ou retorne ambiguidade

3. DATAS:
   - Retorne em formato ISO (YYYY-MM-DD)
   - "dia 27/11" → "2025-11-27"
   - "amanhã" → calcule baseado em hoje ({hoje})
   - Ano padrão: {ano_atual}

4. AMBIGUIDADE (v5 - HERANÇA PRIMEIRO):
   - ANTES de pedir clarificação, VERIFIQUE se REFERENCIA.consulta_ativa = true
   - Se sim E a pergunta é sobre o MESMO domínio → HERDE cliente_atual
   - Só pergunte se:
     a) Não existe cliente_atual no contexto (primeira consulta)
     b) Usuário EXPLICITAMENTE mudou de assunto ("e o Atacadão?")
     c) A pergunta é claramente sobre OUTRO domínio
   - NUNCA pergunte "de qual cliente?" se cliente_atual existe e a pergunta é compatível

5. CONTEXTO (v5 - PONTE):
   - REFERENCIA.cliente_atual = cliente da conversa atual (HERDAR em follow-ups)
   - REFERENCIA.consulta_ativa = true significa "há contexto válido para herança"
   - CONSULTA.filtros_aplicados = filtros da última consulta (herdar se for follow-up)
   - Se tem SEPARACAO ativa, ações são sobre ela
   - Se tem OPCOES, usuário provavelmente está escolhendo
   - Use ENTIDADES do contexto quando disser "esse", "aquele"

6. EXEMPLOS DE HERANÇA:
   - Contexto: cliente_atual="ASSAI", consulta_ativa=true
   - "o que está pendente?" → entidades: {{"raz_social_red": "ASSAI"}}
   - "detalha por pedido" → entidades: {{"raz_social_red": "ASSAI"}}
   - "e o Atacadão?" → entidades: {{"raz_social_red": "ATACADAO"}} (mudou!)

Retorne APENAS o JSON, sem explicações."""

        try:
            resposta = self._client.completar(texto, system_prompt, use_cache=False)
            return self._parse_resposta(resposta)
        except Exception as e:
            logger.error(f"[INTELLIGENT_EXTRACTOR] Erro: {e}")
            return self._fallback(texto)

    def _parse_resposta(self, resposta: str) -> Dict[str, Any]:
        """Parseia resposta JSON do Claude."""
        try:
            resposta_limpa = resposta.strip()

            # Remove blocos markdown
            if resposta_limpa.startswith("```"):
                linhas = resposta_limpa.split("\n")
                resposta_limpa = "\n".join(
                    linhas[1:-1] if linhas[-1].strip() == "```" else linhas[1:]
                )

            resultado = json.loads(resposta_limpa)

            # Normaliza entidades (remove nulls)
            if 'entidades' in resultado:
                resultado['entidades'] = {
                    k: v for k, v in resultado['entidades'].items()
                    if v is not None and str(v).lower() not in ('null', 'none', '')
                }

            logger.info(
                f"[INTELLIGENT_EXTRACTOR] Extraído: "
                f"dominio={resultado.get('dominio')}, "
                f"intencao={resultado.get('intencao')}, "
                f"tipo={resultado.get('tipo')}, "
                f"entidades={list(resultado.get('entidades', {}).keys())}"
            )

            return resultado

        except json.JSONDecodeError as e:
            logger.warning(f"[INTELLIGENT_EXTRACTOR] JSON inválido: {e}")
            logger.debug(f"Resposta recebida: {resposta[:500]}")
            return self._fallback("")

    def _fallback(self, texto: str) -> Dict[str, Any]:
        """Resposta padrão quando extração falha."""
        return {
            "dominio": "geral",
            "intencao": "outro",
            "tipo": "outro",
            "entidades": {"texto_original": texto},
            "confianca": 0.0,
            "erro": "Falha na extração inteligente"
        }


# Singleton
_extractor: Optional[IntelligentExtractor] = None


def get_intelligent_extractor() -> IntelligentExtractor:
    """Retorna instância do extrator inteligente."""
    global _extractor
    if _extractor is None:
        from ..claude_client import get_claude_client
        _extractor = IntelligentExtractor(get_claude_client())
    return _extractor


def extrair_inteligente(
    texto: str,
    contexto: str = None,
    conhecimento: str = None,
    historico: str = None
) -> Dict[str, Any]:
    """
    Função de conveniência para extração inteligente.

    Args:
        texto: Mensagem do usuário
        contexto: JSON do estado estruturado
        conhecimento: Aprendizados do negócio
        historico: NOVO v5.6 - Histórico recente da conversa
    """
    return get_intelligent_extractor().extrair(texto, contexto, conhecimento, historico)
