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
        self.max_tokens = 1024
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

    def identificar_intencao(self, texto: str) -> Dict[str, Any]:
        """
        Usa Claude para identificar intenção e extrair entidades.

        Args:
            texto: Texto do usuário

        Returns:
            Dict com dominio, intencao e entidades
        """
        system_prompt = """Voce e um analisador de intencoes para um sistema de logistica de uma INDUSTRIA DE ALIMENTOS.

Analise a mensagem e retorne APENAS um JSON valido com:
{
    "dominio": "carteira|fretes|embarques|cotacoes|faturamento|geral",
    "intencao": "consultar_status|buscar_pedido|buscar_produto|analisar_disponibilidade|listar|calcular|relatorio|outro",
    "entidades": {
        "num_pedido": "valor ou null",
        "cnpj": "valor ou null",
        "cliente": "valor ou null",
        "pedido_cliente": "valor ou null",
        "produto": "nome do produto ou null",
        "cod_produto": "codigo do produto ou null",
        "data": "valor ou null"
    },
    "confianca": 0.0 a 1.0
}

CONTEXTO - INDUSTRIA DE ALIMENTOS:
- Produtos: Pessego, Ketchup, Azeitona, Cogumelo, Shoyu, Oleo Misto
- Variacoes: cor (verde, preta), forma (inteira, fatiada, sem caroco, metades)
- Embalagens: BD 6x2 (caixa 6 baldes 2kg), Pouch 18x150 (caixa 18 pouchs 150g), Lata, Vidro

REGRAS PARA INTENCAO:
- Se pergunta "quando posso enviar/embarcar/despachar" = analisar_disponibilidade
- Se pergunta "quando e possivel enviar" = analisar_disponibilidade
- Se pergunta "tem estoque para" = analisar_disponibilidade
- Se menciona alimento/produto sem contexto de envio = buscar_produto
- Se pergunta status de pedido especifico = consultar_status

REGRAS PARA PRODUTO:
- Se menciona alimento = colocar em "produto"
- Incluir variacao se mencionada: "azeitona verde" = produto: "azeitona verde"

Exemplos:
- "Pedido VCD2509030 tem separacao?" -> carteira, consultar_status, {num_pedido: "VCD2509030"}
- "Quando posso enviar o pedido VCD2564344?" -> carteira, analisar_disponibilidade, {num_pedido: "VCD2564344"}
- "Quando e possivel embarcar o pedido VCD123?" -> carteira, analisar_disponibilidade, {num_pedido: "VCD123"}
- "Quando da pra despachar o pedido X?" -> carteira, analisar_disponibilidade, {num_pedido: "X"}
- "O pessego ja foi programado?" -> carteira, buscar_produto, {produto: "pessego"}
- "Quanto tem de azeitona verde na carteira?" -> carteira, buscar_produto, {produto: "azeitona verde"}
- "Azeitona preta fatiada BD 6x2 tem separacao?" -> carteira, buscar_produto, {produto: "azeitona preta fatiada BD 6x2"}
- "Ketchup pouch ainda tem na carteira?" -> carteira, buscar_produto, {produto: "ketchup pouch"}
- "Cliente CERATTI tem pedido?" -> carteira, consultar_status, {cliente: "CERATTI"}

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
        dominio: str = "logistica"
    ) -> str:
        """
        Gera resposta usando contexto de dados do sistema.

        Args:
            pergunta: Pergunta do usuário
            contexto: Dados relevantes do banco (já formatados)
            dominio: Domínio da consulta

        Returns:
            Resposta elaborada pelo Claude
        """
        system_prompt = f"""Você é um assistente especializado em {dominio} para um sistema de gestão de fretes.

REGRAS:
1. Responda APENAS com base nos dados fornecidos no CONTEXTO
2. Se a informação não estiver no contexto, diga que não tem essa informação
3. Seja direto e objetivo
4. Use formatação clara (listas, bullets)
5. Não invente dados

CONTEXTO DOS DADOS:
{contexto}

Responda a pergunta do usuário de forma clara e profissional."""

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
