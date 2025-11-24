"""
Cliente da API Claude - Wrapper simples e direto
Limite: 300 linhas (REGRA DE OURO)
"""

import os
import logging
import hashlib
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache simples em memória (produção: usar Redis)
_cache: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 300  # 5 minutos


class ClaudeClient:
    """
    Cliente para API do Claude (Anthropic).
    Responsabilidade única: enviar prompts e receber respostas.
    """

    def __init__(self):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.model = "claude-sonnet-4-5-20250929"  # Claude Sonnet 4.5
        self.max_tokens = 8192
        self._client = None

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY nao configurada")

    def _get_client(self):
        """Lazy loading do cliente Anthropic"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.error("Biblioteca 'anthropic' nao instalada. Execute: pip install anthropic")
                raise
        return self._client

    def completar(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> str:
        """
        Envia prompt para Claude e retorna resposta.

        Args:
            prompt: Pergunta/instrução do usuário
            system_prompt: Contexto do sistema (opcional)
            use_cache: Se deve usar cache (default: True)

        Returns:
            Resposta do Claude como string
        """
        if not self.api_key:
            return "Erro: API do Claude nao configurada. Verifique ANTHROPIC_API_KEY."

        # Verifica cache
        if use_cache:
            cache_key = self._gerar_cache_key(prompt, system_prompt)
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit para consulta")
                return cached

        try:
            client = self._get_client()

            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)

            # Extrai texto da resposta
            resultado = response.content[0].text

            # Salva no cache
            if use_cache:
                self._save_to_cache(cache_key, resultado)

            logger.info(f"Claude respondeu com {len(resultado)} caracteres")
            return resultado

        except Exception as e:
            logger.error(f"Erro ao chamar Claude API: {e}")
            return f"Erro na comunicacao com Claude: {str(e)}"

    def identificar_intencao(self, texto: str, contexto_conversa: str = None) -> Dict[str, Any]:
        """
        Usa Claude para identificar intenção e extrair entidades.

        Args:
            texto: Texto do usuário
            contexto_conversa: Histórico recente da conversa (para entender follow-ups)

        Returns:
            Dict com dominio, intencao e entidades
        """
        # Seção de contexto para perguntas de follow-up
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

        system_prompt = f"""{secao_contexto}Voce e um analisador de intencoes para um sistema de logistica de uma INDUSTRIA DE ALIMENTOS.

Analise a mensagem e retorne APENAS um JSON valido com:
{{
    "dominio": "carteira|estoque|fretes|embarques|cotacoes|faturamento|acao|follow_up|geral",
    "intencao": "consultar_status|buscar_pedido|buscar_produto|analisar_disponibilidade|analisar_estoque_cliente|buscar_rota|buscar_uf|consultar_estoque|consultar_ruptura|analisar_saldo|analisar_gargalo|escolher_opcao|criar_separacao|separar_disponiveis|incluir_item|excluir_item|alterar_quantidade|confirmar_acao|cancelar|ver_rascunho|listar|calcular|relatorio|follow_up|detalhar|outro",
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
- UFs: SP, RJ, MG, PR, SC, RS, BA, etc

IMPORTANTE - DIFERENCA ENTRE ROTA E SUB-ROTA:
- ROTA principal usa siglas de UF ou regiao: BA, MG, NE, NO, SUL, MS-MT
- SUB-ROTA usa letras/numeros simples ou nomes curtos: A, B, C, CAP, INT, INT 2
- Se usuario diz "rota A", "rota B", "rota C" = provavelmente e SUB-ROTA (colocar em sub_rota)
- Se usuario diz "rota SP", "rota MG", "rota NE" = e ROTA principal (colocar em rota)

REGRAS PARA INTENCAO:
- Se pergunta "quando posso enviar/embarcar/despachar" = analisar_disponibilidade
- Se pergunta "quando e possivel enviar" = analisar_disponibilidade
- Se pergunta "tem estoque para" = analisar_disponibilidade
- Se menciona alimento/produto sem contexto de envio = buscar_produto
- Se pergunta status de pedido especifico = consultar_status
- Se usuario responde "opcao A", "A", "quero A", "escolho B" = escolher_opcao (dominio=acao)
- Se usuario responde "sim", "confirmo", "pode criar" = confirmar_acao (dominio=acao)

REGRAS PARA SEPARACAO (IMPORTANTE - dominio=acao):
- "criar separacao", "fazer separacao", "separar pedido" = criar_separacao
- "separar disponiveis", "separar o que da", "separar itens em estoque" = separar_disponiveis
- "incluir item X", "adicionar X", "colocar X na separacao" = incluir_item (item=X)
- "excluir item X", "remover X", "tirar X" = excluir_item (item=X)
- "alterar quantidade de X para Y", "mudar qtd de X" = alterar_quantidade (item=X, quantidade=Y)
- "confirmo", "pode criar", "sim", "ok" = confirmar_acao
- "cancelar", "desistir", "nao quero mais" = cancelar
- "ver rascunho", "mostrar separacao" = ver_rascunho

REGRAS PARA ROTA/SUB-ROTA/UF:
- Se pergunta "pedidos na rota MG" ou "rota NE" = buscar_rota (rota principal)
- Se pergunta "rota A", "rota B", "sub-rota CAP" = buscar_rota com sub_rota
- Se pergunta "pedidos para SP" ou "o que tem para MG" = buscar_uf
- ATENCAO: "rota" seguida de letra unica (A, B, C) = SUB-ROTA, nao rota principal!

REGRAS PARA ESTOQUE:
- Se pergunta "qual o estoque de X" ou "tem estoque de" = consultar_estoque (dominio=estoque)
- Se pergunta "vai dar ruptura" ou "produtos com ruptura" = consultar_ruptura (dominio=estoque)
- Se pergunta "projecao de estoque" = consultar_estoque (dominio=estoque)

REGRAS PARA SALDO:
- Se pergunta "quanto falta separar" ou "saldo do pedido" = analisar_saldo
- Se pergunta "quantidade separada vs original" = analisar_saldo

REGRAS PARA GARGALO:
- Se pergunta "o que esta travando" ou "gargalo" = analisar_gargalo
- Se pergunta "produtos que travam pedidos" = analisar_gargalo
- Se pergunta "por que nao consigo enviar" = analisar_gargalo

REGRAS PARA PERGUNTAS COMPOSTAS (CLIENTE + DATA + ESTOQUE) - IMPORTANTE:
- "quais produtos do [CLIENTE] terao estoque" = analisar_estoque_cliente
- "o que posso enviar para o cliente [X]" = analisar_estoque_cliente
- "produtos disponiveis do [CLIENTE]" = analisar_estoque_cliente
- "o que tem estoque para enviar ao [CLIENTE]" = analisar_estoque_cliente
- "quais produtos do [CLIENTE] estao disponiveis dia [DATA]" = analisar_estoque_cliente
- IMPORTANTE: Se menciona CLIENTE + (estoque OU disponivel OU enviar OU data sem num_pedido), use analisar_estoque_cliente
- DIFERENCA: "quando posso enviar o PEDIDO VCD123" = analisar_disponibilidade (tem num_pedido)
- DIFERENCA: "o que posso enviar para o CLIENTE Atacadao" = analisar_estoque_cliente (tem cliente, sem num_pedido)

REGRAS PARA PRODUTO:
- Se menciona alimento = colocar em "produto"
- Incluir variacao se mencionada: "azeitona verde" = produto: "azeitona verde"

Exemplos:
- "Pedido VCD2509030 tem separacao?" -> carteira, consultar_status, {{num_pedido: "VCD2509030"}}
- "Quando posso enviar o pedido VCD2564344?" -> carteira, analisar_disponibilidade, {{num_pedido: "VCD2564344"}}
- "O pessego ja foi programado?" -> carteira, buscar_produto, {{produto: "pessego"}}
- "Cliente CERATTI tem pedido?" -> carteira, consultar_status, {{cliente: "CERATTI"}}
- "Opcao A" -> acao, escolher_opcao, {{opcao: "A"}}
- "Pedidos na rota MG" -> carteira, buscar_rota, {{rota: "MG"}}
- "O que tem na rota NE?" -> carteira, buscar_rota, {{rota: "NE"}}
- "Tem mais algo pra rota B?" -> carteira, buscar_rota, {{sub_rota: "B"}}
- "Pedidos da sub-rota CAP" -> carteira, buscar_rota, {{sub_rota: "CAP"}}
- "O que tem pra rota A?" -> carteira, buscar_rota, {{sub_rota: "A"}}
- "Rota INT tem pedidos?" -> carteira, buscar_rota, {{sub_rota: "INT"}}
- "O que tem para Sao Paulo?" -> carteira, buscar_uf, {{uf: "SP"}}
- "Pedidos para MG" -> carteira, buscar_uf, {{uf: "MG"}}
- "Qual o estoque de azeitona verde?" -> estoque, consultar_estoque, {{produto: "azeitona verde"}}
- "Tem ruptura de ketchup?" -> estoque, consultar_ruptura, {{produto: "ketchup"}}
- "Quais produtos vao dar ruptura?" -> estoque, consultar_ruptura, {{}}
- "Quanto falta separar do VCD123?" -> carteira, analisar_saldo, {{num_pedido: "VCD123"}}
- "Saldo do pedido VCD456" -> carteira, analisar_saldo, {{num_pedido: "VCD456"}}
- "O que esta travando o pedido VCD789?" -> carteira, analisar_gargalo, {{num_pedido: "VCD789"}}
- "Quais produtos sao gargalo?" -> carteira, analisar_gargalo, {{}}
- "Por que nao consigo enviar o VCD111?" -> carteira, analisar_gargalo, {{num_pedido: "VCD111"}}
- "Preciso dos nomes completos desses itens" -> follow_up, detalhar, {{}} (usar contexto anterior)
- "Mais detalhes sobre esses produtos" -> follow_up, detalhar, {{}} (usar contexto anterior)

EXEMPLOS DE PERGUNTAS COMPOSTAS (CLIENTE + DATA + ESTOQUE):
- "Quais produtos do Atacadao 183 terao estoque no dia 26/11?" -> carteira, analisar_estoque_cliente, {{cliente: "Atacadao 183", data: "26/11"}}
- "O que posso enviar para o cliente Ceratti?" -> carteira, analisar_estoque_cliente, {{cliente: "Ceratti"}}
- "Produtos disponiveis do Carrefour para semana que vem" -> carteira, analisar_estoque_cliente, {{cliente: "Carrefour", data: "semana que vem"}}
- "O que tem estoque para enviar ao Pao de Acucar?" -> carteira, analisar_estoque_cliente, {{cliente: "Pao de Acucar"}}
- "Quais itens do cliente Extra posso despachar dia 28?" -> carteira, analisar_estoque_cliente, {{cliente: "Extra", data: "28"}}

EXEMPLOS DE SEPARACAO (dominio=acao):
- "Criar separacao do pedido VCD123" -> acao, criar_separacao, {{num_pedido: "VCD123"}}
- "Separar os itens disponiveis" -> acao, separar_disponiveis, {{}}
- "Separar o que da do pedido VCD123" -> acao, separar_disponiveis, {{num_pedido: "VCD123"}}
- "Voce consegue gerar separacao dos 3 itens disponiveis?" -> acao, separar_disponiveis, {{}}
- "Incluir o cogumelo" -> acao, incluir_item, {{item: "cogumelo"}}
- "Adicionar azeitona verde com 5 unidades" -> acao, incluir_item, {{item: "azeitona verde", quantidade: 5}}
- "Excluir o pepino" -> acao, excluir_item, {{item: "pepino"}}
- "Remover oleo da separacao" -> acao, excluir_item, {{item: "oleo"}}
- "Alterar quantidade de azeitona para 10" -> acao, alterar_quantidade, {{item: "azeitona", quantidade: 10}}
- "Mudar qtd do cogumelo para 3" -> acao, alterar_quantidade, {{item: "cogumelo", quantidade: 3}}
- "Confirmo" -> acao, confirmar_acao, {{}}
- "Sim, pode criar" -> acao, confirmar_acao, {{}}
- "Cancelar" -> acao, cancelar, {{}}
- "Ver rascunho" -> acao, ver_rascunho, {{}}

Retorne SOMENTE o JSON, sem explicacoes."""

        resposta = self.completar(texto, system_prompt, use_cache=True)

        try:
            # Tenta extrair JSON da resposta
            resposta_limpa = resposta.strip()
            if resposta_limpa.startswith("```"):
                # Remove blocos de código markdown
                linhas = resposta_limpa.split("\n")
                resposta_limpa = "\n".join(linhas[1:-1])

            return json.loads(resposta_limpa)

        except json.JSONDecodeError:
            logger.warning(f"Falha ao parsear JSON do Claude: {resposta[:100]}")
            return {
                "dominio": "geral",
                "intencao": "outro",
                "entidades": {},
                "confianca": 0.0,
                "erro": "Falha ao interpretar resposta"
            }

    def responder_com_contexto(
        self,
        pergunta: str,
        contexto: str,
        dominio: str = "logistica",
        contexto_memoria: str = None
    ) -> str:
        """
        Gera resposta usando contexto de dados do sistema.

        Args:
            pergunta: Pergunta do usuário
            contexto: Dados relevantes do banco (já formatados)
            dominio: Domínio da consulta
            contexto_memoria: Histórico de conversa + aprendizados (opcional)

        Returns:
            Resposta elaborada pelo Claude
        """
        # Monta seção de memória se houver
        secao_memoria = ""
        if contexto_memoria:
            secao_memoria = f"""

MEMÓRIA E HISTÓRICO:
{contexto_memoria}

IMPORTANTE SOBRE MEMÓRIA:
- Use o histórico para entender referências como "esses pedidos", "o pedido 2 da lista"
- Se o usuário perguntar "quais pedidos você falou?", consulte o histórico
- Respeite os conhecimentos permanentes salvos
- Se o usuário usar "Lembre que...", confirme que você memorizou
"""

        system_prompt = f"""Você é um assistente amigável e prestativo especializado em {dominio} para um sistema de gestão de fretes de uma indústria de alimentos.
{secao_memoria}

PERSONALIDADE:
- Seja acolhedor e profissional
- Use linguagem clara e acessível
- Sempre ofereça ajuda adicional ao final da resposta

REGRAS DE RESPOSTA:
1. Responda APENAS com base nos dados fornecidos no CONTEXTO
2. Se a informação não estiver no contexto, diga que não tem essa informação
3. Seja direto mas cordial
4. Use formatação clara (listas, bullets)
5. Não invente dados
6. Se o contexto contiver OPCOES DE ENVIO (A, B, C), apresente TODAS as opções de forma clara
7. Quando apresentar opcoes, pergunte qual opcao o usuario deseja

ORIENTAÇÃO AO USUÁRIO:
- Ao final de cada resposta, sugira 1-2 perguntas relacionadas que você pode responder
- Exemplos de sugestões:
  * "Posso ajudar com algo mais sobre este pedido?"
  * "Quer que eu verifique a disponibilidade de estoque?"
  * "Deseja criar uma separação para este pedido?"
  * "Precisa consultar outro pedido ou cliente?"

CAPACIDADES QUE VOCÊ TEM:

**Consultas de Pedidos:**
- Consultar pedidos por número, cliente ou CNPJ
- Analisar saldo de pedido (original vs separado)

**Análise de Disponibilidade (Quando Posso Enviar?):**
- Pergunta: "Quando posso enviar o pedido VCD123?"
- Analisa o estoque atual vs quantidade necessária de cada item
- Gera até 3 OPÇÕES DE ENVIO:
  * Opção A: Envio TOTAL - aguarda todos os itens terem estoque
  * Opção B: Envio PARCIAL - exclui 1 item gargalo (se houver)
  * Opção C: Envio PARCIAL - exclui 2 itens gargalo (se houver)
- Mostra data prevista, valor, percentual e itens de cada opção

**Análise de Gargalos (O que está travando?):**
- Pergunta: "O que está travando o pedido VCD123?" ou "Quais produtos são gargalo?"
- Identifica produtos com estoque insuficiente para atender demanda
- Mostra: quantidade necessária, estoque atual, quanto falta
- Para gargalos gerais: ranking dos produtos que mais travam pedidos
- Calcula severidade (1-10) baseado em cobertura e pedidos afetados

**Ações:**
- Criar separações para pedidos (escolher opção A, B ou C após análise)

**Consultas de Produtos e Estoque:**
- Buscar produtos na carteira
- Verificar estoque atual e projeção de até 14 dias
- Identificar produtos com ruptura prevista (próximos 7 dias)

**Consultas por Localização:**
- Por rota principal: "rota MG", "rota NE", "rota SUL"
- Por sub-rota: "rota B", "rota CAP", "rota INT"
- Por UF/estado: "pedidos para SP", "o que tem pra MG?"

**Memória e Aprendizado:**
- Memorizar: "Lembre que o cliente X é VIP"
- Memorizar global: "Lembre que código 123 é Azeitona (global)"
- Esquecer: "Esqueça que o cliente X é especial"
- Listar: "O que você sabe?"

SE O USUÁRIO PEDIR AJUDA OU PERGUNTAR O QUE VOCÊ FAZ:
Explique suas capacidades de forma amigável e dê exemplos práticos:
"Posso te ajudar com várias coisas! Por exemplo:
- 'Pedido VCD123 tem separação?' - consulto o status
- 'Quando posso enviar o pedido VCD456?' - analiso estoque e dou opções A/B/C
- 'O que está travando o pedido X?' - identifico os gargalos de estoque
- 'O que tem pra rota B?' - listo pedidos da sub-rota
- 'Qual o estoque de azeitona?' - mostro estoque e projeção
- 'Quais produtos vão dar ruptura?' - listo produtos críticos
- 'Lembre que o cliente Ceratti é VIP' - memorizo para você
O que você gostaria de saber?"

CONTEXTO DOS DADOS:
{contexto}

Responda de forma clara, profissional e sempre oferecendo ajuda adicional."""

        return self.completar(pergunta, system_prompt, use_cache=False)

    def _gerar_cache_key(self, prompt: str, system_prompt: Optional[str]) -> str:
        """Gera chave única para cache"""
        conteudo = f"{prompt}:{system_prompt or ''}"
        return hashlib.md5(conteudo.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Recupera do cache se não expirou"""
        if key in _cache:
            item = _cache[key]
            if datetime.now() < item['expira']:
                return item['valor']
            else:
                del _cache[key]
        return None

    def _save_to_cache(self, key: str, valor: str):
        """Salva no cache com TTL"""
        _cache[key] = {
            'valor': valor,
            'expira': datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)
        }

        # Limpa cache antigo (máximo 100 itens)
        if len(_cache) > 100:
            self._limpar_cache_antigo()

    def _limpar_cache_antigo(self):
        """Remove itens expirados do cache"""
        agora = datetime.now()
        chaves_expiradas = [k for k, v in _cache.items() if agora >= v['expira']]
        for k in chaves_expiradas:
            del _cache[k]


# Instância global (singleton)
_cliente_global: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Retorna instância global do cliente Claude"""
    global _cliente_global
    if _cliente_global is None:
        _cliente_global = ClaudeClient()
    return _cliente_global
