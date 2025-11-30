"""
Extrator Inteligente - PROMPT 1: CLASSIFICAÇÃO

RESPONSABILIDADE:
- Receber pergunta do usuário
- Classificar domínio, intenção e extrair entidades
- Delegar 100% ao Claude

FONTE DE DADOS (dinâmica):
- Capabilities: via ToolRegistry.formatar_para_prompt()
- Fallback: _gerar_capabilities_fallback() (gera das capabilities)
- Mínimo: _CAPABILITIES_MINIMO (só se tudo falhar)

FILOSOFIA v5.0:
- O Claude é o CÉREBRO - confiamos 100% nas decisões dele
- O Claude recebe:
  1. Lista de CAPABILITIES disponíveis (com descrição e intenções)
  2. ESTADO ESTRUTURADO da conversa (JSON) - v5 com PONTE de contexto
  3. CONHECIMENTO DO NEGÓCIO (aprendizados)
  4. HISTÓRICO DA CONVERSA (para follow-ups)
- O Claude decide:
  1. DOMÍNIO (carteira, estoque, acao, etc)
  2. INTENÇÃO (deve mapear para uma capability)
  3. ENTIDADES extraídas - INCLUINDO herança automática de contexto!

HERANÇA AUTOMÁTICA v5:
- Se REFERENCIA.consulta_ativa = true e usuário NÃO muda de assunto
- HERDA cliente_atual, dominio_atual automaticamente
- Isso resolve o problema de "o que está pendente?" após consultar cliente X

Criado em: 24/11/2025
Atualizado: 27/11/2025 - v5.6: Recebe histórico da conversa
Atualizado: 27/11/2025 - v5.7: Fallback dinâmico (nunca desincroniza)
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# CAPABILITIES FALLBACK - GERADO DINAMICAMENTE
# =============================================================================
# O fallback agora também é gerado dinamicamente para nunca desincronizar.
# Atualizado: 27/11/2025 - Removido fallback hardcoded

# Fallback MÍNIMO - só usado se TUDO falhar (capabilities não carregadas)
_CAPABILITIES_MINIMO = """
=== CAPABILITIES MÍNIMAS ===
Se você está vendo isso, houve erro no carregamento das capabilities.

DOMÍNIO: carteira
- consultar_pedido: Consulta pedidos (num_pedido, cliente)
- consulta_generica: Consultas em tabelas

DOMÍNIO: acao
- escolher_opcao: Usuário escolhendo A/B/C
- confirmar_acao: Usuário confirmando (sim, confirmo)
- cancelar: Usuário cancelando

=== FIM ===
"""


def _gerar_capabilities_fallback() -> str:
    """
    Gera fallback de capabilities dinamicamente (sem ToolRegistry).

    Usado quando ToolRegistry falha - gera direto das capabilities.
    Isso garante que NUNCA haja desincronização.
    """
    try:
        from ..capabilities import get_all_capabilities

        caps = get_all_capabilities()
        if not caps:
            return _CAPABILITIES_MINIMO

        linhas = ["=== CAPABILITIES DISPONÍVEIS ===", ""]

        # Agrupa por domínio
        por_dominio = {}
        for cap in caps:
            d = cap.DOMINIO or 'geral'
            if d not in por_dominio:
                por_dominio[d] = []
            por_dominio[d].append(cap)

        for dominio, lista in sorted(por_dominio.items()):
            linhas.append(f"DOMÍNIO: {dominio}")
            for cap in lista:
                linhas.append(f"- {cap.NOME}")
                if cap.INTENCOES:
                    linhas.append(f"  Intenções: {', '.join(cap.INTENCOES)}")
                if cap.DESCRICAO:
                    linhas.append(f"  Descrição: {cap.DESCRICAO}")
                if cap.CAMPOS_BUSCA:
                    linhas.append(f"  Campos: {', '.join(cap.CAMPOS_BUSCA)}")
                if cap.EXEMPLOS:
                    linhas.append(f"  Exemplos: {'; '.join(cap.EXEMPLOS)}")
                linhas.append("")

        linhas.append("=== FIM DAS CAPABILITIES ===")
        return "\n".join(linhas)

    except Exception as e:
        logger.warning(f"[INTELLIGENT_EXTRACTOR] Fallback dinâmico falhou: {e}")
        return _CAPABILITIES_MINIMO


# =============================================================================
# CARREGAMENTO DINÂMICO DE CAPABILITIES (via ToolRegistry)
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
            logger.warning("[INTELLIGENT_EXTRACTOR] Nenhuma ferramenta encontrada, usando fallback dinâmico")
            return _gerar_capabilities_fallback()

        return registry.formatar_para_prompt(ferramentas)

    except Exception as e:
        logger.warning(f"[INTELLIGENT_EXTRACTOR] Erro ao carregar capabilities dinâmicas: {e}")
        return _gerar_capabilities_fallback()


def _obter_capabilities_prompt() -> str:
    """
    Retorna capabilities para o prompt, usando config para decidir.

    Se config.extracao.carregar_capabilities_dinamicamente = True:
        Carrega do ToolRegistry
    Senão:
        Gera fallback dinâmico (nunca desincroniza)
    """
    from ..config import usar_capabilities_dinamicas

    if usar_capabilities_dinamicas():
        caps = _carregar_capabilities_dinamicas()
        logger.debug("[INTELLIGENT_EXTRACTOR] Usando capabilities dinâmicas")
        return caps

    logger.debug("[INTELLIGENT_EXTRACTOR] Usando capabilities fallback dinâmico")
    return _gerar_capabilities_fallback()


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

=== CONTEXTO DA INDÚSTRIA ===
Produtos: Pêssego, Ketchup, Azeitona, Cogumelo, Shoyu, Óleo Misto
Variações: cor (verde, preta), forma (inteira, fatiada, sem caroço, recheada)
Embalagens: BD 6x2 (caixa 6 baldes 2kg), Pouch 18x150 (18 pouchs 150g), Lata, Vidro
Rotas principais: BA, MG, ES, NE, NE2, NO, MS-MT, SUL, SP, RJ
Sub-rotas: CAP, INT, INT 2, A, B, C, 0, 1, 2 (baseadas em cidade/região interna)

=== INTERPRETAÇÃO DE FILTROS IMPLÍCITOS ===
Quando o usuário diz:
- "sem agendamento" → agendamento IS NULL
- "sem expedição" → expedicao IS NULL
- "sem protocolo" → protocolo IS NULL
- "sem transportadora" → roteirizacao IS NULL
- "atrasados" → expedicao < hoje
- "pendentes" → sincronizado_nf = False
- "abertos" → status = 'ABERTO'
- "hoje" → expedicao = data atual
- "amanhã" → expedicao = data atual + 1
- "já foi programado" → tem expedicao definida
- "ainda tem na carteira" → qtd_saldo > 0 (não separado)

=== INTERPRETAÇÃO DE LOCALIZAÇÃO ===
- "rota MG", "rota NE" → rota principal (campo: rota)
- "rota A", "rota B", "rota CAP" → sub-rota (campo: sub_rota)
- "pedidos para SP", "o que tem pra MG" → UF (campo: cod_uf)

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
        "opcoes": ["opção 1", "opção 2"],
        "tipo_faltante": "cliente|pedido|produto|data|acao",  // O QUE está faltando
        "motivo": "por que precisa de clarificação"
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

4. AMBIGUIDADE (v6 - HERANÇA PRIMEIRO, CLARIFICAÇÃO ÚTIL):
   - ANTES de pedir clarificação, VERIFIQUE se REFERENCIA.consulta_ativa = true
   - Se sim E a pergunta é sobre o MESMO domínio → HERDE cliente_atual
   - Só pergunte se:
     a) Não existe cliente_atual no contexto (primeira consulta)
     b) Usuário EXPLICITAMENTE mudou de assunto ("e o Atacadão?")
     c) A pergunta é claramente sobre OUTRO domínio
   - NUNCA pergunte "de qual cliente?" se cliente_atual existe e a pergunta é compatível

   QUANDO PEDIR CLARIFICAÇÃO (v6 - SEJA ESPECÍFICO):
   - SEMPRE informe tipo_faltante = qual campo está faltando (cliente, pedido, produto, data)
   - A pergunta deve ser ESPECÍFICA: "Qual cliente?" não "Poderia esclarecer?"
   - Opções devem ter formato útil (não invente nomes de clientes)
   - O sistema irá buscar opções REAIS para mostrar ao usuário

   EXEMPLOS DE CLARIFICAÇÃO BOA:
   - tipo_faltante="cliente", pergunta="Qual cliente você quer consultar?"
   - tipo_faltante="pedido", pergunta="Qual número do pedido?"
   - tipo_faltante="data", pergunta="Para qual data deseja programar?"

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
