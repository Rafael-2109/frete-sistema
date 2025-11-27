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

from app.claude_ai_lite.config import get_max_tokens

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
        self.model = "claude-opus-4-5-20251101"  # Claude Opus 4.5
        self.max_tokens = get_max_tokens('opus')  # Usa config dinâmica (16384 para opus)
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

    # NOTA: O método identificar_intencao() foi REMOVIDO (27/11/2025)
    # Motivo: Era código legado não utilizado no fluxo principal.
    # A extração de intenções é feita pelo IntelligentExtractor (intelligent_extractor.py)
    # que carrega capabilities dinamicamente do ToolRegistry.

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
